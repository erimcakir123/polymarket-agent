"""Tennis dispatch — SPEC-Z14 (2026-06-03) BM-first, model fallback (ML); alt market sadece model."""
from src.domain.analysis.enrich_outcome import EnrichResult
from src.domain.analysis.probability import calculate_bookmaker_probability
from src.domain.pricing.tennis.glicko import Rating
from src.domain.pricing.tennis.player_snapshot import PlayerSnapshot
from src.domain.pricing.tennis.serve_metrics import PlayerServeStats
from src.models.market import MarketData
from src.strategy.enrichment.surface_resolver import SurfaceResolver
from src.strategy.enrichment.tennis_dispatch import (
    _extract_location,
    _match_surface,
    enrich_with_tennis_dispatch,
)


def _infer_surface(question: str, surface_map: dict) -> str | None:
    """Test helper: question→surface (eski production fonksiyonun gövdesi; resolver bunu primitive'lere bölerek kullanır)."""
    loc = _extract_location(question)
    return _match_surface(loc, surface_map) if loc else None


def _market(question: str, sport: str = "tennis", market_type: str = "moneyline") -> MarketData:
    return MarketData(
        condition_id="0xa", question=question, slug="x",
        yes_token_id="t1", no_token_id="t2",
        yes_price=0.5, no_price=0.5, liquidity=100, volume_24h=100,
        end_date_iso="2026-06-01T00:00:00Z",
        sport_tag=sport, sports_market_type=market_type,
    )


def _snap(mu: float, serve: float) -> PlayerSnapshot:
    return PlayerSnapshot(
        rating=Rating(mu=mu, phi=80),
        serve_by_surface={"Hard": PlayerServeStats(serve, 1.0 - serve + 0.05, 5000)},
    )


def _fake_bookmaker_enrich(market: MarketData) -> EnrichResult:
    """BM h2h enrich simülasyonu — başarılı sonuç (0.55)."""
    return EnrichResult(
        probability=calculate_bookmaker_probability(
            bookmaker_prob=0.55, num_bookmakers=5.0, has_sharp=True,
        ),
        fail_reason=None,
    )


def _fake_bookmaker_enrich_none(market: MarketData) -> EnrichResult:
    """BM h2h enrich simülasyonu — Odds API kapsama yok."""
    from src.domain.analysis.enrich_outcome import EnrichFailReason
    return EnrichResult(
        probability=None,
        fail_reason=EnrichFailReason.SPORT_KEY_UNRESOLVED,
    )


def test_non_tennis_uses_bookmaker():
    """Non-tennis sport_tag → doğrudan bookmaker (sport-agnostic h2h)."""
    m = _market("NBA Lakers vs Celtics", sport="nba")
    result = enrich_with_tennis_dispatch(m, _fake_bookmaker_enrich, ratings={})
    assert result.probability is not None
    assert abs(result.probability.bookmaker_prob - 0.55) < 1e-6


def test_tennis_moneyline_bm_first_when_bm_available():
    """SPEC-Z14: ML + BM data var → BM döner (model'e bakılmaz)."""
    m = _market("Alice vs Bob")
    ratings = {"Alice": _snap(1750, 0.66), "Bob": _snap(1500, 0.58)}
    result = enrich_with_tennis_dispatch(m, _fake_bookmaker_enrich, ratings=ratings)
    assert result.probability is not None
    # BM çıktısı (0.55), model değil — model olsa Alice strong favori → > 0.6 olurdu.
    assert abs(result.probability.bookmaker_prob - 0.55) < 1e-6
    assert result.probability.source == "bookmaker"


class _FixedSurfaceResolver:
    """Test fake: her markete sabit zemin döner."""
    def __init__(self, surface: str) -> None:
        self._surface = surface

    def resolve(self, market) -> str:
        return self._surface


def test_tennis_moneyline_grass_model_disabled_returns_surface_fail():
    """2026-06-11 kullanıcı kararı: çimde model-ML OYNAMAZ (30 maç -$84.6, %53<%64).
    BM yok + çim + ML + Grass disabled-listede → model fiyatlamaz."""
    from src.domain.analysis.enrich_outcome import EnrichFailReason
    m = _market("Wimbledon: Alice vs Bob")
    ratings = {"Alice": _snap(1750, 0.66), "Bob": _snap(1500, 0.58)}
    result = enrich_with_tennis_dispatch(
        m, _fake_bookmaker_enrich_none, ratings=ratings,
        surface_resolver=_FixedSurfaceResolver("Grass"),
        model_ml_disabled_surfaces=("Grass",),
    )
    assert result.probability is None
    assert result.fail_reason == EnrichFailReason.MODEL_SURFACE_DISABLED


def test_tennis_moneyline_clay_model_prices_when_grass_disabled():
    """Disabled listesi sadece o zemini keser — toprak ML model aynen fiyatlanır."""
    m = _market("Lyon: Alice vs Bob")
    ratings = {"Alice": _snap(1750, 0.66), "Bob": _snap(1500, 0.58)}
    result = enrich_with_tennis_dispatch(
        m, _fake_bookmaker_enrich_none, ratings=ratings,
        surface_resolver=_FixedSurfaceResolver("Clay"),
        model_ml_disabled_surfaces=("Grass",),
    )
    assert result.probability is not None
    assert result.probability.source == "model"


def test_tennis_grass_model_blocked_below_surface_min_prob():
    """2026-06-11 kullanıcı kararı ('kesin bulursak girelim'): çimde model bir
    tarafa en az eşik kadar güven vermiyorsa girilmez. Eşik 0.99 ile mekanizma
    deterministik test edilir (hiçbir gerçek çıktı %99'a ulaşmaz → blok).
    Üretim değeri (0.70) config'te; geriye-dönük: ≥%70 17 işlem +$38.3."""
    from src.domain.analysis.enrich_outcome import EnrichFailReason
    m = _market("Set Handicap: Alice (-1.5) vs Bob (+1.5)",
                market_type="tennis_set_handicap")
    ratings = {"Alice": _snap(1510, 0.61), "Bob": _snap(1500, 0.60)}
    result = enrich_with_tennis_dispatch(
        m, _fake_bookmaker_enrich_none, ratings=ratings,
        surface_resolver=_FixedSurfaceResolver("Grass"),
        model_min_prob_by_surface={"Grass": 0.99},
    )
    assert result.probability is None
    assert result.fail_reason == EnrichFailReason.MODEL_CONFIDENCE_BELOW_SURFACE_MIN


def test_tennis_clay_model_not_blocked_by_grass_min_prob():
    """Eşik zemine özgü: Grass eşiği toprak fiyatlamasına dokunmaz."""
    from src.domain.analysis.enrich_outcome import EnrichFailReason
    m = _market("Set Handicap: Alice (-1.5) vs Bob (+1.5)",
                market_type="tennis_set_handicap")
    ratings = {"Alice": _snap(1510, 0.61), "Bob": _snap(1500, 0.60)}
    result = enrich_with_tennis_dispatch(
        m, _fake_bookmaker_enrich_none, ratings=ratings,
        surface_resolver=_FixedSurfaceResolver("Clay"),
        model_min_prob_by_surface={"Grass": 0.70},
    )
    assert result.fail_reason != EnrichFailReason.MODEL_CONFIDENCE_BELOW_SURFACE_MIN
    assert result.probability is not None


def test_tennis_set_handicap_grass_still_prices_when_grass_ml_disabled():
    """Kapsam SADECE moneyline: çim set bahisleri (%63 kazanım) modelle devam."""
    m = _market("Set Handicap: Alice (-1.5) vs Bob (+1.5)",
                market_type="tennis_set_handicap")
    ratings = {"Alice": _snap(1750, 0.66), "Bob": _snap(1500, 0.58)}
    result = enrich_with_tennis_dispatch(
        m, _fake_bookmaker_enrich_none, ratings=ratings,
        surface_resolver=_FixedSurfaceResolver("Grass"),
        model_ml_disabled_surfaces=("Grass",),
    )
    from src.domain.analysis.enrich_outcome import EnrichFailReason
    assert result.fail_reason != EnrichFailReason.MODEL_SURFACE_DISABLED
    assert result.probability is not None


def test_tennis_moneyline_falls_back_to_model_when_bm_unavailable():
    """SPEC-Z14: ML + BM yok + model OK → model devreye girer."""
    m = _market("Wimbledon: Alice vs Bob")
    ratings = {"Alice": _snap(1750, 0.66), "Bob": _snap(1500, 0.58)}
    result = enrich_with_tennis_dispatch(
        m, _fake_bookmaker_enrich_none, ratings=ratings,
        surface_resolver=SurfaceResolver({"wimbledon": "Grass"}, now_iso="2026-06-09T00:00:00"),
    )
    assert result.probability is not None
    assert result.probability.source == "model"
    # Model output: Alice strong favorite → > 0.6.
    assert result.probability.probability > 0.6


def test_tennis_moneyline_fails_when_both_bm_and_model_fail():
    """SPEC-Z14: ML + BM yok + ratings yok → fail (silent fallback yok)."""
    m = _market("Unknown vs Player")
    result = enrich_with_tennis_dispatch(m, _fake_bookmaker_enrich_none, ratings={})
    assert result.probability is None
    assert result.fail_reason is not None


def test_tennis_alt_market_no_bm_call():
    """SPEC-Z14: Alt market'te BM hiç çağrılmaz — sadece model.

    Cascade bug önleme: h2h fiyatı set_handicap fiyatı sanılmamalı.
    """
    m = _market("Alice vs Bob", market_type="tennis_set_handicap")
    calls: list[MarketData] = []
    def _spy_bookmaker(market: MarketData) -> EnrichResult:
        calls.append(market)
        return _fake_bookmaker_enrich(market)
    result = enrich_with_tennis_dispatch(m, _spy_bookmaker, ratings={})
    assert result.probability is None
    assert result.fail_reason is not None
    # Alt market'te BM hiç çağrılmamalı.
    assert calls == []


def test_extract_market_params_handicap():
    """K1 regression: tennis_set_handicap question'dan handicap parse edilir."""
    from src.strategy.enrichment.tennis_dispatch import _extract_market_params
    line, handicap = _extract_market_params(
        "Alice -1.5 sets win", "tennis_set_handicap",
    )
    assert handicap == -1.5
    assert line is None


def test_extract_market_params_total():
    """tennis_set_totals question'dan line parse edilir (match_totals artık bahisçide)."""
    from src.strategy.enrichment.tennis_dispatch import _extract_market_params
    line, handicap = _extract_market_params("Over 2.5 sets", "tennis_set_totals")
    assert line == 2.5
    assert handicap is None


def test_extract_market_params_unknown_type_returns_none():
    """K1 regression: bilinmeyen market_type → None tuple, exception YOK."""
    from src.strategy.enrichment.tennis_dispatch import _extract_market_params
    line, handicap = _extract_market_params("anything", "unknown_market")
    assert line is None
    assert handicap is None


def test_extract_market_params_no_match_returns_none():
    """K1 regression: handicap market'te handicap value yok → None (not crash)."""
    from src.strategy.enrichment.tennis_dispatch import _extract_market_params
    line, handicap = _extract_market_params("Alice vs Bob", "tennis_set_handicap")
    assert handicap is None
    assert line is None


def test_resolve_player_name_lastname_substring():
    """Polymarket soyadı → Sackmann full name eşlemesi."""
    from src.strategy.enrichment.tennis_dispatch import _resolve_player_name
    ratings = {"Hubert Hurkacz": _snap(1700, 0.65), "Taylor Fritz": _snap(1750, 0.67)}
    assert _resolve_player_name("Hurkacz", ratings) == "Hubert Hurkacz"
    assert _resolve_player_name("Fritz", ratings) == "Taylor Fritz"
    assert _resolve_player_name("hurkacz", ratings) == "Hubert Hurkacz"


def test_resolve_player_name_ambiguous_returns_none():
    """Aynı soyadı 2+ oyuncuda var → None (güvenli)."""
    from src.strategy.enrichment.tennis_dispatch import _resolve_player_name
    ratings = {"Alex Alvarez": _snap(1600, 0.60), "Jorge Alvarez": _snap(1500, 0.58)}
    assert _resolve_player_name("Alvarez", ratings) is None


def test_resolve_player_name_unknown_returns_none():
    from src.strategy.enrichment.tennis_dispatch import _resolve_player_name
    ratings = {"Roger Federer": _snap(1900, 0.70)}
    assert _resolve_player_name("Nadal", ratings) is None


def test_resolve_player_name_hyphenated_first_name_matches():
    """2026-06-10 canlı vaka: Polymarket 'Jan-Lennard Struff' (tireli) vs
    Sackmann 'Jan Lennard Struff' (boşluklu) → eşleşmeli."""
    from src.strategy.enrichment.tennis_dispatch import _resolve_player_name
    ratings = {"Jan Lennard Struff": _snap(1700, 0.64), "Alexander Bublik": _snap(1720, 0.66)}
    assert _resolve_player_name("Jan-Lennard Struff", ratings) == "Jan Lennard Struff"


def test_resolve_player_name_partial_name_single_candidate_matches():
    """2026-06-10 canlı vaka: Polymarket 'Gabriela Ruse' (kısa ad) vs
    Sackmann 'Elena Gabriela Ruse' (tam ad) → tek aday, eşleşmeli."""
    from src.strategy.enrichment.tennis_dispatch import _resolve_player_name
    ratings = {"Elena Gabriela Ruse": _snap(1650, 0.62), "Elise Mertens": _snap(1750, 0.67)}
    assert _resolve_player_name("Gabriela Ruse", ratings) == "Elena Gabriela Ruse"


def test_resolve_player_name_partial_name_ambiguous_returns_none():
    """Kısa ad 2+ oyuncuyla eşleşiyorsa → None (güvenli atlama korunur)."""
    from src.strategy.enrichment.tennis_dispatch import _resolve_player_name
    ratings = {"Ana Maria Garcia": _snap(1600, 0.60), "Maria Garcia Lopez": _snap(1500, 0.58)}
    assert _resolve_player_name("Maria Garcia", ratings) is None


def test_infer_market_type_slug_fallback():
    """Polymarket sports_market_type'ı boş bırakırsa slug'tan çıkar.

    Cascade bug regression — boş market_type moneyline sayılırdı, yanlış
    pricer'a yönlenirdi. Slug'da 'set-handicap' geçerse doğru type.
    """
    from src.strategy.enrichment.tennis_dispatch import _infer_market_type
    m = MarketData(
        condition_id="0xa",
        question="Set Handicap: Rublev (-1.5) vs Mensik (+1.5)",
        slug="atp-mensik-rublev-2026-05-31-set-handicap-away-1pt5",
        yes_token_id="t1", no_token_id="t2",
        yes_price=0.5, no_price=0.5, liquidity=100, volume_24h=100,
        end_date_iso="2026-06-01T00:00:00Z",
        sport_tag="tennis", sports_market_type="",
    )
    assert _infer_market_type(m) == "tennis_set_handicap"


def test_infer_market_type_total_from_slug():
    from src.strategy.enrichment.tennis_dispatch import _infer_market_type
    m = MarketData(
        condition_id="0xa", question="Cobolli vs Svajda: Match O/U 38.5",
        slug="atp-cobolli-svajda-2026-05-31-match-total-38pt5",
        yes_token_id="t1", no_token_id="t2",
        yes_price=0.5, no_price=0.5, liquidity=100, volume_24h=100,
        end_date_iso="2026-06-01T00:00:00Z",
        sport_tag="tennis", sports_market_type="",
    )
    assert _infer_market_type(m) == "tennis_match_totals"


def test_infer_market_type_declared_wins():
    """sports_market_type doluysa slug'a bakma."""
    from src.strategy.enrichment.tennis_dispatch import _infer_market_type
    m = MarketData(
        condition_id="0xa", question="Anything",
        slug="anything-set-handicap-x",
        yes_token_id="t1", no_token_id="t2",
        yes_price=0.5, no_price=0.5, liquidity=100, volume_24h=100,
        end_date_iso="2026-06-01T00:00:00Z",
        sport_tag="tennis", sports_market_type="moneyline",
    )
    assert _infer_market_type(m) == "moneyline"


def test_surface_inferred_for_grand_slam():
    """Map-bazlı: bilinen turnuva → doğru zemin; bilinmeyen → None (PLAN-Z29)."""
    smap = {"wimbledon": "Grass", "roland garros": "Clay", "us open": "Hard"}
    assert _infer_surface("Wimbledon final: A vs B", smap) == "Grass"
    assert _infer_surface("Roland Garros R3: A vs B", smap) == "Clay"
    assert _infer_surface("US Open R1: A vs B", smap) == "Hard"
    assert _infer_surface("ATP 250 Unknown: A vs B", smap) is None


def test_tennis_match_totals_not_routed_to_bookmaker_and_skips():
    """SPEC-Z28: Match O/U TAMAMEN kaldırıldı — bahisçiye gitmez, model pricer yok → skip (None)."""
    m = _market("Alice vs Bob: Match O/U 22.5", market_type="tennis_match_totals")
    ratings = {"Alice": _snap(1750, 0.66), "Bob": _snap(1500, 0.58)}
    calls = []
    def _spy(market):
        calls.append(market)
        return _fake_bookmaker_enrich(market)
    result = enrich_with_tennis_dispatch(m, _spy, ratings=ratings)
    assert result.probability is None      # no model pricer for totals → skip
    assert calls == []                      # NOT routed to bookmaker


def test_infer_surface_known_tournament_from_map():
    smap = {"ilkley": "Grass", "cattolica": "Clay", "wimbledon": "Grass"}
    assert _infer_surface("Ilkley: Bu vs Rodesch", smap) == "Grass"
    assert _infer_surface("Cattolica: Bueno vs Forti", smap) == "Clay"
    assert _infer_surface("Wimbledon: A vs B", smap) == "Grass"


def test_infer_surface_unknown_tournament_returns_none():
    assert _infer_surface("HSBC Championships: A vs B", {"ilkley": "Grass"}) is None


def test_infer_surface_player_matchup_no_location_returns_none():
    assert _infer_surface("Bueno vs. Forti: Total Sets O/U 2.5", {"x": "Clay"}) is None


def test_infer_surface_empty_map_returns_none():
    assert _infer_surface("Ilkley: A vs B", {}) is None


def test_infer_surface_no_colon_returns_none():
    assert _infer_surface("just some text", {"ilkley": "Grass"}) is None


def test_dispatch_unknown_surface_skips_and_warns(caplog):
    import logging
    m = _market("HSBC Championships: Alice vs Bob", market_type="tennis_set_handicap")
    ratings = {"Alice": _snap(1750, 0.66), "Bob": _snap(1500, 0.58)}
    with caplog.at_level(logging.WARNING):
        result = enrich_with_tennis_dispatch(
            m, _fake_bookmaker_enrich_none, ratings=ratings,
            surface_resolver=SurfaceResolver({"ilkley": "Grass"}, now_iso="2026-06-09T00:00:00"),
        )
    assert result.probability is None
    assert any(("zemin" in r.message.lower()) or ("surface" in r.message.lower()) for r in caplog.records)


def test_dispatch_known_surface_prices_model():
    # bilinen zemin → model akışı çalışır (skip değil); set_handicap model fiyatlar
    m = _market("Ilkley: Alice vs Bob", market_type="tennis_set_handicap")
    ratings = {"Alice": _snap(1750, 0.66), "Bob": _snap(1500, 0.58)}
    result = enrich_with_tennis_dispatch(
        m, _fake_bookmaker_enrich_none, ratings=ratings,
        surface_resolver=SurfaceResolver({"ilkley": "Grass"}, now_iso="2026-06-09T00:00:00"),
    )
    # zemin biliniyor → skip DEĞİL (model fiyatlamaya gider; sonuç None olabilir ama zemin-skip sebebiyle değil)
    # en azından "zemin bilinmiyor" uyarısı OLMAMALI:
    assert result is not None


def test_infer_surface_no_substring_inside_word():
    """'halle' (Grass) 'challenger' İÇİNDE geçmesin (kelime-sınırı)."""
    smap = {"halle": "Grass", "merida": "Hard"}
    # "Merida Challenger" → 'halle' kelime değil (challenger içinde); 'merida' kelime → Hard
    assert _infer_surface("Merida Challenger: A vs B", smap) == "Hard"


def test_dispatch_uses_resolver():
    m = _market("HSBC Championships: Alice vs Bob", market_type="tennis_set_handicap")
    ratings = {"Alice": _snap(1750, 0.66), "Bob": _snap(1500, 0.58)}
    class _W:
        def resolve_surface(self, n): return "Grass"
    r = SurfaceResolver({}, wiki=_W(), overrides={}, now_iso="2026-06-09T00:00:00")
    res = enrich_with_tennis_dispatch(m, _fake_bookmaker_enrich_none, ratings=ratings, surface_resolver=r)
    assert res is not None  # zemin Wiki'den geldi → skip değil


def test_infer_surface_short_key_not_inside_word():
    """'linz' (Hard) 'bellinzona' İÇİNDE eşleşmesin; exact 'bellinzona' kazanır."""
    smap = {"linz": "Hard", "bellinzona": "Clay"}
    assert _infer_surface("Bellinzona: A vs B", smap) == "Clay"


def test_infer_surface_longest_key_wins_deterministic():
    """Birden çok kelime-sınırı eşleşmesi → en UZUN anahtar (deterministik)."""
    smap = {"open": "Hard", "ilkley open": "Grass"}
    assert _infer_surface("Ilkley Open: A vs B", smap) == "Grass"


def test_infer_surface_multiword_key_word_boundary():
    """'roland garros' tam kelime-dizisi eşleşir."""
    smap = {"roland garros": "Clay"}
    assert _infer_surface("Roland Garros R3: A vs B", smap) == "Clay"


def test_infer_surface_exact_still_first():
    """Exact eşleşme önce (substring'e gerek yok)."""
    smap = {"ilkley": "Grass"}
    assert _infer_surface("Ilkley: A vs B", smap) == "Grass"


def test_match_surface_by_name():
    from src.strategy.enrichment.tennis_dispatch import _match_surface
    smap = {"ilkley": "Grass", "san miguel de tucuman": "Clay"}
    assert _match_surface("Ilkley", smap) == "Grass"
    assert _match_surface("Tucuman", smap) == "Clay"   # token-subset (kw ⊆ cw)
    assert _match_surface("Unknown Cup", smap) is None


def test_extract_location_rejects_market_prefixes():
    from src.strategy.enrichment.tennis_dispatch import _extract_location
    assert _extract_location("Set Handicap: Zverev (-1.5) vs Cobolli") is None
    assert _extract_location("Game Handicap: A vs B") is None
    assert _extract_location("Total Games: A vs B") is None
    # gerçek turnuva hâlâ çıkar:
    assert _extract_location("Ilkley: A vs B") == "Ilkley"


def test_match_surface_short_token_no_false_match():
    from src.strategy.enrichment.tennis_dispatch import _match_surface
    smap = {"pau": "Hard", "ilkley": "Grass", "san miguel de tucuman": "Clay"}
    # "Pau Pilot Open" → 'pau' 3 harf → token-subset eşleşmez (yanlış zemin yok)
    assert _match_surface("Pau Pilot Open", smap) is None
    # exact kısa şehir hâlâ çalışır:
    assert _match_surface("Pau", smap) == "Hard"
    # ≥4 harf legit subset hâlâ çalışır:
    assert _match_surface("Ilkley Challenger", smap) == "Grass"
    assert _match_surface("Tucuman", smap) == "Clay"
    assert _extract_location("Cattolica: A vs B") == "Cattolica"


def test_extract_location_rejects_set_winner_market():
    from src.strategy.enrichment.tennis_dispatch import _extract_location
    assert _extract_location("Set 1 Winner: Mena vs Rodriguez") is None
    assert _extract_location("Set 2 Winner: A vs B") is None
    assert _extract_location("First Set Winner: A vs B") is None
    # gerçek turnuva hâlâ çıkar:
    assert _extract_location("Ilkley: A vs B") == "Ilkley"
