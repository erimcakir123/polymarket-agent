"""tennis_dispatch_surface testleri — yetki-dışı markette zemin aranmaz (gürültü fix)."""
from src.models.market import MarketData
from src.strategy.enrichment.tennis_dispatch_surface import make_surface_aware_dispatch


def _mkt(question: str, slug: str, sport: str = "tennis") -> MarketData:
    return MarketData(
        condition_id="c", question=question, slug=slug, yes_token_id="y",
        no_token_id="n", yes_price=0.5, no_price=0.5, liquidity=1.0,
        volume_24h=1.0, end_date_iso="2026-06-11", sport_tag=sport,
    )


class _CountingResolver:
    def __init__(self) -> None:
        self.calls = 0

    def resolve(self, market) -> str | None:
        self.calls += 1
        return None


def _bm_fail(_market):
    from src.domain.analysis.enrich_outcome import EnrichFailReason, EnrichResult
    return EnrichResult(probability=None, fail_reason=EnrichFailReason.EMPTY_BOOKMAKERS)


def test_low_tier_itf_market_does_not_trigger_surface_resolve():
    """ITF (yetki dışı) market: bot oynamaz → zemin çözücü HİÇ çağrılmamalı
    (2026-06-10 03:22 SURFACE_UNKNOWN_itf madrid sahte alarmı)."""
    resolver = _CountingResolver()
    enrich = make_surface_aware_dispatch({"Hard": {}, "Clay": {}, "Grass": {}})
    res = enrich(
        _mkt("ITF Madrid: A vs B", "itf-a-b-2026-06-10"),
        _bm_fail, {}, surface_resolver=resolver,
    )
    assert res.probability is None
    assert resolver.calls == 0


def test_non_tennis_market_does_not_trigger_surface_resolve():
    resolver = _CountingResolver()
    enrich = make_surface_aware_dispatch({"Hard": {}, "Clay": {}, "Grass": {}})
    enrich(
        _mkt("Lakers vs Celtics", "nba-lal-bos-2026-06-10", sport="basketball"),
        _bm_fail, {}, surface_resolver=resolver,
    )
    assert resolver.calls == 0
