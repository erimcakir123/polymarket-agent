"""nba_score_exit.check() unit testleri."""
from __future__ import annotations

from src.strategy.exit.nba_score_exit import check
from src.models.enums import ExitReason


def _si(
    period_number: int = 4,
    clock_seconds: int = 300,
    deficit: int = 10,
    available: bool = True,
) -> dict:
    return {
        "available": available,
        "period_number": period_number,
        "clock_seconds": clock_seconds,
        "deficit": deficit,
        "our_score": 90,
        "opp_score": 90 + deficit,
    }


_M = 0.861


def test_period_3_always_hold():
    """Q1-Q3'te skor ne olursa olsun HOLD."""
    result = check(
        score_info=_si(period_number=3, clock_seconds=60, deficit=20),
        elapsed_pct=0.75,
        sport_tag="basketball_nba",
        bid_price=0.40,
        entry_price=0.60,
        bill_james_multiplier=_M,
    )
    assert result is None


def test_math_dead_q4_triggers():
    """Q4, Bill James eşiği aşıldı → MATH_DEAD."""
    # 0.861 * sqrt(240) = 13.33 → deficit=17 geçer
    result = check(
        score_info=_si(period_number=4, clock_seconds=240, deficit=17),
        elapsed_pct=0.90,
        sport_tag="basketball_nba",
        bid_price=0.30,
        entry_price=0.60,
        bill_james_multiplier=_M,
    )
    assert result is not None
    assert result.reason == ExitReason.SCORE_EXIT
    assert "MATH_DEAD" in result.detail


def test_empirical_q4_blowout():
    """Q4, 12 dk kala 20 fark → EMPIRICAL_DEAD (predictive devre dışı — empirical'ı izole test)."""
    result = check(
        score_info=_si(period_number=4, clock_seconds=720, deficit=20),
        elapsed_pct=0.90,
        sport_tag="basketball_nba",
        bid_price=0.25,
        entry_price=0.60,
        bill_james_multiplier=_M,
        predictive_enabled=False,
    )
    assert result is not None
    assert result.reason == ExitReason.SCORE_EXIT
    assert "EMPIRICAL" in result.detail


def test_empirical_q4_endgame():
    """Q4, son 60s, 6 fark → EMPIRICAL_DEAD (predictive devre dışı — empirical'ı izole test)."""
    result = check(
        score_info=_si(period_number=4, clock_seconds=60, deficit=6),
        elapsed_pct=0.95,
        sport_tag="basketball_nba",
        bid_price=0.20,
        entry_price=0.55,
        bill_james_multiplier=_M,
        predictive_enabled=False,
    )
    assert result is not None
    assert "EMPIRICAL" in result.detail


def test_overtime_dead():
    """OT, son 60s, 8 fark → OT_DEAD."""
    si = {**_si(period_number=5, clock_seconds=60, deficit=8), "available": True}
    result = check(
        score_info=si,
        elapsed_pct=1.1,
        sport_tag="basketball_nba",
        bid_price=0.15,
        entry_price=0.55,
        bill_james_multiplier=_M,
    )
    assert result is not None
    assert "OT_DEAD" in result.detail


def test_q4_small_deficit_alive():
    """Q4, 5 dakika kala, 5 fark → geri dönülebilir, hold."""
    # 0.861 * sqrt(300) = 14.9 → 5 < 14.9 → MATH: geçmez
    # Empirical: 300s > 180s eşiği (endgame değil) → blowout: 5 < 20 → geçmez
    result = check(
        score_info=_si(period_number=4, clock_seconds=300, deficit=5),
        elapsed_pct=0.90,
        sport_tag="basketball_nba",
        bid_price=0.45,
        entry_price=0.60,
        bill_james_multiplier=_M,
    )
    assert result is None


def test_structural_damage_last_resort():
    """Q4, fiyat entry'nin %30'unun altına düştü + math dead → STRUCTURAL_DAMAGE."""
    # entry=0.60, bid=0.17 → 0.17/0.60 = 0.283 < 0.30
    # 0.861 * sqrt(120) = 9.43 → deficit=15 geçer
    result = check(
        score_info=_si(period_number=4, clock_seconds=120, deficit=15),
        elapsed_pct=0.95,
        sport_tag="basketball_nba",
        bid_price=0.17,
        entry_price=0.60,
        bill_james_multiplier=_M,
    )
    assert result is not None
    assert "STRUCTURAL" in result.detail


def test_unavailable_score_returns_none():
    """score_info available=False → hold (skor yok)."""
    result = check(
        score_info={"available": False},
        elapsed_pct=0.90,
        sport_tag="basketball_nba",
        bid_price=0.30,
        entry_price=0.60,
        bill_james_multiplier=_M,
    )
    assert result is None


def test_ot_small_deficit_alive():
    """OT, son 120s, 4 fark → OT_DEAD eşiği aşılmadı, hold."""
    si = {**_si(period_number=5, clock_seconds=120, deficit=4), "available": True}
    result = check(
        score_info=si,
        elapsed_pct=1.05,
        sport_tag="basketball_nba",
        bid_price=0.40,
        entry_price=0.60,
        bill_james_multiplier=_M,
    )
    assert result is None
