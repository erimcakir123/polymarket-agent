"""2026-05-31 Adım 2: Hold-to-resolve — Sackmann güven yüksekse SL muaf.

Kullanıcı verisi: anchor < %30 deep dog 21 trade %81 isabet AMA -$29 kayıp.
Tahmin doğru AMA SL'ye takılıp pozisyonu kaybediyoruz. Yüksek güvende
fiyat dalgalanması mı doğru sonuç mu — sonuç kazanıyor → pozisyonu tut.

Eşik: |anchor - 0.50| > 0.20 → SL muaf
- anchor < 0.30 (Sackmann "kazanamaz" dedi) → BUY_NO için yüksek güven
- anchor > 0.70 (Sackmann "kesin kazanır") → BUY_YES için yüksek güven
- 0.30 ≤ anchor ≤ 0.70 → orta güven → normal SL

Sadece tennis için (basket SL kuralı korunur — %67 WR kanıtlı).
"""
from src.strategy.exit.stop_loss import compute_stop_loss_pct
from src.models.position import Position


def _mk_pos(sport_tag: str, market_type: str, anchor: float, entry: float = 0.50) -> Position:
    return Position(
        condition_id="0xa", token_id="ty", direction="BUY_YES",
        entry_price=entry, size_usdc=50.0, shares=100.0, current_price=entry,
        anchor_probability=anchor, entry_reason="consensus", confidence="A",
        sport_tag=sport_tag, event_id="e1", slug="x-y-2026-05-31",
        entry_timestamp="2026-05-31T00:00:00Z",
        sports_market_type=market_type,
    )


def test_tennis_strong_favorite_anchor_high_sl_exempt():
    """Tennis moneyline, anchor 0.85 (>%70 favori) → SL MUAF (hold-to-resolve)."""
    pos = _mk_pos("tennis", "moneyline", anchor=0.85)
    sl = compute_stop_loss_pct(pos)
    assert sl is None


def test_tennis_strong_dog_anchor_low_sl_exempt():
    """Tennis moneyline, anchor 0.15 (%15 köpek, Sackmann çok güveniyor karşıya) → MUAF."""
    pos = _mk_pos("tennis", "moneyline", anchor=0.15)
    sl = compute_stop_loss_pct(pos)
    assert sl is None


def test_tennis_medium_confidence_anchor_normal_sl():
    """Tennis moneyline, anchor 0.55 (orta) → SL normal (%50 tennis gevşek)."""
    pos = _mk_pos("tennis", "moneyline", anchor=0.55)
    sl = compute_stop_loss_pct(pos)
    assert sl == 0.50


def test_tennis_threshold_boundary_exact_30():
    """Sınır: anchor 0.30 → SL aktif (eşik dahil değil, sıkı yorum)."""
    pos = _mk_pos("tennis", "moneyline", anchor=0.30)
    sl = compute_stop_loss_pct(pos)
    assert sl == 0.50  # SL aktif, henüz muaf değil


def test_tennis_threshold_boundary_below_30():
    """Sınır: anchor 0.29 → SL muaf (hold-to-resolve aktif)."""
    pos = _mk_pos("tennis", "moneyline", anchor=0.29)
    sl = compute_stop_loss_pct(pos)
    assert sl is None


def test_basket_hold_to_resolve_disabled():
    """Basket: hold-to-resolve YOK (sport-specific kuralı korunur)."""
    pos = _mk_pos("wnba", "totals", anchor=0.85)
    sl = compute_stop_loss_pct(pos)
    assert sl == 0.35  # WNBA SL korunur


def test_basket_strong_dog_normal_sl():
    pos = _mk_pos("nba", "moneyline", anchor=0.15)
    sl = compute_stop_loss_pct(pos)
    assert sl == 0.35  # NBA SL korunur
