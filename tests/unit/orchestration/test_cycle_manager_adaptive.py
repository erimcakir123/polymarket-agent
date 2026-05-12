"""SPEC-M Adaptive cycle testleri — nearest_match_hours kontrolü."""
from __future__ import annotations

from datetime import datetime, timezone

from src.config.settings import CycleConfig
from src.orchestration.cycle_manager import CycleManager


def _make(now_ts: float = 10_000.0, utc_hour: int = 15, **over) -> CycleManager:
    """Default config: heavy=30, near=15, imminent=10, near_th=3h, imminent_th=1h."""
    cfg = CycleConfig(
        heavy_interval_min=30,
        light_interval_sec=5,
        night_interval_min=60,
        night_hours=[8, 9, 10, 11, 12, 13],
        near_interval_min=15,
        imminent_interval_min=10,
        near_threshold_hours=3.0,
        imminent_threshold_hours=1.0,
        **over,
    )
    return CycleManager(
        config=cfg,
        now_fn=lambda: now_ts,
        utc_now_fn=lambda: datetime(2026, 5, 12, utc_hour, tzinfo=timezone.utc),
    )


# ── Edge Case 1: Hiç maç yok → default davranış ──

def test_no_matches_default_30min() -> None:
    """Gündüz + maç yok → 30dk default."""
    cm = _make(utc_hour=15)
    cm.update_nearest_match_hours(None)
    assert cm._current_heavy_interval_sec() == 30 * 60


def test_no_matches_night_60min() -> None:
    """Gece (UTC 08-13) + maç yok → 60dk."""
    cm = _make(utc_hour=10)  # gece
    cm.update_nearest_match_hours(None)
    assert cm._current_heavy_interval_sec() == 60 * 60


# ── Edge Case 2: Yakın maç (1-3h) → 15dk ──

def test_near_match_2h_uses_15min() -> None:
    """Maç 2 saat sonra → near_interval (15dk)."""
    cm = _make(utc_hour=15)
    cm.update_nearest_match_hours(2.0)
    assert cm._current_heavy_interval_sec() == 15 * 60


def test_near_match_boundary_3h_uses_default() -> None:
    """Tam 3 saat (threshold) → strict < kontrolü, default heavy 30dk."""
    cm = _make(utc_hour=15)
    cm.update_nearest_match_hours(3.0)
    assert cm._current_heavy_interval_sec() == 30 * 60


def test_near_match_just_under_3h_uses_15min() -> None:
    """2.99 saat → near_interval (15dk)."""
    cm = _make(utc_hour=15)
    cm.update_nearest_match_hours(2.99)
    assert cm._current_heavy_interval_sec() == 15 * 60


# ── Edge Case 3: Imminent maç (<1h) → 10dk ──

def test_imminent_match_30min_uses_10min() -> None:
    """Maç 30dk sonra → imminent_interval (10dk)."""
    cm = _make(utc_hour=15)
    cm.update_nearest_match_hours(0.5)
    assert cm._current_heavy_interval_sec() == 10 * 60


def test_imminent_match_boundary_1h_uses_near() -> None:
    """Tam 1 saat (threshold) → strict < kontrolü, near_interval (15dk)."""
    cm = _make(utc_hour=15)
    cm.update_nearest_match_hours(1.0)
    assert cm._current_heavy_interval_sec() == 15 * 60


def test_imminent_just_under_1h_uses_10min() -> None:
    """0.99 saat → imminent (10dk)."""
    cm = _make(utc_hour=15)
    cm.update_nearest_match_hours(0.99)
    assert cm._current_heavy_interval_sec() == 10 * 60


# ── Edge Case 4: Gece + imminent → adaptive kazanir ──

def test_night_with_imminent_match_adaptive_wins() -> None:
    """Gece saati + imminent maç → adaptive (10dk) override night (60dk)."""
    cm = _make(utc_hour=10)  # gece
    cm.update_nearest_match_hours(0.5)  # imminent
    assert cm._current_heavy_interval_sec() == 10 * 60


def test_night_with_near_match_adaptive_wins() -> None:
    """Gece saati + near maç → adaptive (15dk) override night (60dk)."""
    cm = _make(utc_hour=10)
    cm.update_nearest_match_hours(2.0)
    assert cm._current_heavy_interval_sec() == 15 * 60


def test_night_with_far_match_night_used() -> None:
    """Gece saati + uzak maç (>3h) → night (60dk) kullanılır."""
    cm = _make(utc_hour=10)
    cm.update_nearest_match_hours(8.0)  # uzak
    assert cm._current_heavy_interval_sec() == 60 * 60


# ── Edge Case 5: Negative hours (geçmiş maç) → ignore ──

def test_negative_hours_treated_as_no_match() -> None:
    """Negatif saat (geçmiş maç) → None gibi davranılır, default kullanılır.
    NOT: caller (agent._compute_nearest_match_hours) zaten filter ediyor, ama
    cycle_manager içinde defansif kontrol."""
    cm = _make(utc_hour=15)
    cm.update_nearest_match_hours(-1.0)
    assert cm._current_heavy_interval_sec() == 30 * 60  # default


def test_zero_hours_treated_as_no_match() -> None:
    """Tam 0 saat → None gibi davranılır."""
    cm = _make(utc_hour=15)
    cm.update_nearest_match_hours(0.0)
    assert cm._current_heavy_interval_sec() == 30 * 60


# ── Edge Case 6: next_heavy_at_iso adaptive interval'i kullanır ──

def test_next_heavy_iso_uses_adaptive_interval() -> None:
    """next_heavy_at_iso adaptive interval'i kullanır (dashboard countdown doğru)."""
    cm = _make(now_ts=1000.0, utc_hour=15)
    cm.tick(has_positions=True)  # cold start için pozisyon True → periyodik path
    cm._last_heavy_ts = 1000.0  # son heavy 1000 saniyede oldu
    # Imminent maç → 10 dk = 600 saniye
    cm.update_nearest_match_hours(0.5)
    iso = cm.next_heavy_at_iso()
    # next_ts = 1000 + 600 = 1600
    assert datetime.fromisoformat(iso).timestamp() == 1600.0


# ── Edge Case 7: tick() ile heavy çekme ──

def test_adaptive_imminent_shortens_heavy_trigger() -> None:
    """Imminent maç var → heavy 10dk'da bir tetiklenir."""
    cm = _make(now_ts=1000.0, utc_hour=15)
    cm.tick(has_positions=True)  # cold start engellemek için True
    cm._last_heavy_ts = 1000.0
    cm.update_nearest_match_hours(0.5)  # imminent → 10dk interval
    # 10dk = 600 sn — tam threshold'da heavy tetiklenmeli
    cm._now = lambda: 1600.0
    t = cm.tick(has_positions=True)
    assert t.run_heavy is True
    assert t.reason == "periodic_heavy"


def test_adaptive_far_does_not_shorten() -> None:
    """Uzak maç → 30dk (default) interval'inde heavy tetiklenir."""
    cm = _make(now_ts=1000.0, utc_hour=15)
    cm.tick(has_positions=True)
    cm._last_heavy_ts = 1000.0
    cm.update_nearest_match_hours(8.0)  # uzak
    # 20dk sonra → henüz heavy tetiklenmez (30dk gerek)
    cm._now = lambda: 1000.0 + 20 * 60
    t = cm.tick(has_positions=True)
    assert t.run_heavy is False
    assert t.reason == "light"


# ── Edge Case 8: Backward compatibility — update çağrılmadan eski davranış ──

def test_default_behavior_without_update() -> None:
    """update_nearest_match_hours hiç çağrılmamış → mevcut davranış (geriye uyumlu)."""
    cm = _make(utc_hour=15)
    # update CALLED DEGIL
    assert cm._current_heavy_interval_sec() == 30 * 60  # default heavy


# ── Edge Case 9: Exit-triggered heavy preserved ──

def test_exit_triggered_overrides_adaptive_timing() -> None:
    """Exit-triggered heavy adaptive ile çakışmaz — anlık tetikleme."""
    cm = _make(now_ts=1000.0, utc_hour=15)
    cm.tick(has_positions=True)
    cm._last_heavy_ts = 1000.0
    cm.update_nearest_match_hours(8.0)  # uzak — normal cycle 30dk
    # Exit oldu, hemen heavy
    cm.signal_exit_happened()
    cm._now = lambda: 1100.0  # sadece 100 saniye gectikten sonra
    t = cm.tick(has_positions=True)
    assert t.run_heavy is True
    assert t.reason == "exit_triggered_heavy"
    assert t.prefer_eligible_queue is True
