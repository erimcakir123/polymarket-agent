"""2026-05-31 Adım 1: Tennis SL gevşek + bimodal flat-SL muaf.

Kanıt (kullanıcı analizi):
- Sackmann moneyline %70 doğru AMA -$62 kayıp
- Anchor < %30 (deep dog) → bot ters girer → %81 doğru → -$29 kayıp
- Sebep: tennis SL %30 → fiyat dalgalanması bu aralıkta → erken SL fire
- Çözüm: tennis SL %30 → %50 + bimodal market'ler (set_handicap, totals)
  flat SL'den muaf (graduated SL aktif kalır)
"""
from src.strategy.exit.stop_loss import compute_stop_loss_pct
from src.models.position import Position


def _mk_pos(sport_tag: str, market_type: str, entry: float = 0.50) -> Position:
    return Position(
        condition_id="0xa", token_id="ty", direction="BUY_YES",
        entry_price=entry, size_usdc=50.0, shares=100.0, current_price=entry,
        anchor_probability=0.5, entry_reason="consensus", confidence="A",
        sport_tag=sport_tag, event_id="e1", slug="x-y-2026-05-31",
        entry_timestamp="2026-05-31T00:00:00Z",
        sports_market_type=market_type,
    )


def test_tennis_moneyline_sl_loosened_to_50():
    """Tennis moneyline: SL %30 → %50 (Sackmann doğru çıkmadan SL fire'i engelle)."""
    pos = _mk_pos("tennis", "moneyline")
    sl = compute_stop_loss_pct(pos)
    assert sl == 0.50


def test_tennis_set_handicap_flat_sl_exempt():
    """Tennis set_handicap (bimodal): flat SL MUAF — graduated SL aktif kalır.

    Sebep: set bittiğinde fiyat 99¢/1¢ sıçrar. Flat SL %50 fire eder, bot satar,
    sonra fiyat geri uçar → kâr kaybedilir. Hold-to-resolve daha kazançlı.
    """
    pos = _mk_pos("tennis", "tennis_set_handicap")
    sl = compute_stop_loss_pct(pos)
    assert sl is None  # MUAF


def test_tennis_match_totals_flat_sl_exempt():
    """Tennis match_totals: aynı sebep, flat SL muaf."""
    pos = _mk_pos("tennis", "tennis_match_totals")
    sl = compute_stop_loss_pct(pos)
    assert sl is None


def test_basket_sl_unchanged():
    """Basket SL DEĞERLERİ KORUNUR — hepsi 0.35 (NBA mirası, BASKETBALL_TAGS)."""
    for sport in ("nba", "wnba", "ncaab", "cbb", "euroleague", "nbl"):
        pos = _mk_pos(sport, "totals")
        sl = compute_stop_loss_pct(pos)
        assert sl == 0.35, f"{sport} SL bozulmuş: {sl}"


def test_nba_moneyline_sl_unchanged_035():
    pos = _mk_pos("nba", "moneyline")
    sl = compute_stop_loss_pct(pos)
    assert sl == 0.35  # NBA tarihsel


def test_low_entry_graduated_still_overrides_sport_sl():
    """Low entry (9-20¢) graduated SL sport_rules SL'i ÖNCELERİ var (mevcut davranış)."""
    pos = _mk_pos("tennis", "moneyline", entry=0.15)  # 15¢ low entry
    sl = compute_stop_loss_pct(pos)
    # Tennis moneyline non-bimodal → None DEĞİL
    assert sl is not None
    # Linear interp 9¢→60%, 20¢→40%, 15¢ ≈ 49.1%
    assert 0.45 < sl < 0.55
