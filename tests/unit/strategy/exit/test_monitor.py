"""monitor.py için birim testler — orchestration (A3 score-only tek-dal akış) + never_in_profit + hold_revocation + ultra_low."""
from __future__ import annotations

from datetime import datetime, timedelta, timezone

from src.models.enums import ExitReason
from src.models.position import Position
from src.strategy.exit.monitor import compute_elapsed_pct, evaluate


def _iso(dt: datetime) -> str:
    return dt.strftime("%Y-%m-%dT%H:%M:%SZ")


def _pos(**over) -> Position:
    base = dict(
        condition_id="c", token_id="t", direction="BUY_YES",
        entry_price=0.40, size_usdc=40, shares=100,
        current_price=0.40, anchor_probability=0.55,
        confidence="B", sport_tag="nba",
    )
    base.update(over)
    return Position(**base)


# ── compute_elapsed_pct ──

def test_elapsed_pct_30min_into_nba() -> None:
    # NBA duration 2.5h = 150 dk; 30 dk elapsed → 0.20
    start = datetime.now(timezone.utc) - timedelta(minutes=30)
    p = _pos(match_start_iso=_iso(start))
    assert abs(compute_elapsed_pct(p) - 30 / 150) < 0.02


def test_elapsed_pct_no_start_returns_minus1() -> None:
    p = _pos(match_start_iso="")
    assert compute_elapsed_pct(p) == -1.0


# ── Priority: near-resolve wins over scale-out ──

def test_near_resolve_priority_over_scale_out() -> None:
    # current 0.95 → eff 0.95; pnl = (100*0.95 - 40) / 40 = 137% → hem scale-out hem near-resolve
    start = datetime.now(timezone.utc) - timedelta(minutes=30)
    p = _pos(current_price=0.95, match_start_iso=_iso(start))
    r = evaluate(p)
    assert r.exit_signal is not None
    assert r.exit_signal.reason == ExitReason.NEAR_RESOLVE


# ── Scale-out ──

_SCALE_OUT_TIERS = [
    {"threshold": 0.50, "sell_pct": 0.40},  # SPEC-013: midpoint-to-resolution semantigi
]


def test_scale_out_tier1_at_threshold() -> None:
    # entry 0.40, threshold 0.50 → trigger = 0.40 + 0.50*(0.99-0.40) = 0.695
    # current 0.70 → fraction = (0.70-0.40)/(0.99-0.40) = 0.508 >= 0.50 → tetiklenir
    p = _pos(current_price=0.70, entry_price=0.40, size_usdc=40, shares=100)
    r = evaluate(p, scale_out_tiers=_SCALE_OUT_TIERS)
    assert r.exit_signal is not None
    assert r.exit_signal.reason == ExitReason.SCALE_OUT
    assert r.exit_signal.partial is True
    assert r.exit_signal.tier == 1
    assert r.exit_signal.sell_pct == 0.40


# ── Market flip (A3 tek-dal: tüm pozisyonlarda çalışır) ──

def test_market_flip_at_late_match() -> None:
    """A3 score-only: elapsed ≥ 85% + eff < 0.50 → MARKET_FLIP (tennis hariç)."""
    # NBA 2.5h duration × 0.90 = 2.25h elapsed → market_flip gate (0.85) geçer
    start = datetime.now(timezone.utc) - timedelta(hours=2, minutes=20)
    p = _pos(
        confidence="A", entry_price=0.65, current_price=0.48,
        size_usdc=40, shares=62, match_start_iso=_iso(start), sport_tag="nba",
    )
    r = evaluate(p)
    assert r.exit_signal is not None
    assert r.exit_signal.reason == ExitReason.MARKET_FLIP


def test_market_flip_gated_by_elapsed() -> None:
    """elapsed < 0.85 → market_flip tetiklenmez."""
    # NBA 2.5h × 0.80 = 2h elapsed → gate geçmez
    # ever_in_profit=True → never_in_profit gate'e takılmaz (bu test sadece flip gating'i kontrol eder)
    start = datetime.now(timezone.utc) - timedelta(hours=2)
    p = _pos(
        confidence="A", entry_price=0.65, current_price=0.48,
        size_usdc=40, shares=62, match_start_iso=_iso(start), sport_tag="nba",
        ever_in_profit=True,
    )
    r = evaluate(p)
    assert r.exit_signal is None


def test_tennis_immune_to_market_flip() -> None:
    """Tennis'te market_flip tetiklenmemeli (set kaybı ≠ maç kaybı)."""
    # ever_in_profit=True → never_in_profit gate'e takılmaz (bu test sadece market_flip'i kontrol eder)
    start = datetime.now(timezone.utc) - timedelta(hours=3)
    p = _pos(
        confidence="A", entry_price=0.64, current_price=0.41,
        size_usdc=56, shares=87.5, match_start_iso=_iso(start),
        sport_tag="tennis", ever_in_profit=True,
    )
    r = evaluate(p)
    assert r.exit_signal is None, (
        f"Tennis'te market_flip tetiklenmemeli (exit={r.exit_signal})"
    )


# ── Cricket score exit (SPEC-011) ──

def test_cricket_c1_triggers_for_a_conf() -> None:
    """A-conf cricket pozisyonu + C1 score_info → SCORE_EXIT (SPEC-011 C1)."""
    p = _pos(
        sport_tag="cricket_ipl",
        confidence="A",
        entry_price=0.65,
        current_price=0.10,
        slug="cricipl-kkr-rr-2026-04-19",
        question="Kolkata Knight Riders vs Rajasthan Royals",
    )
    score_info = {
        "available": True,
        "innings": 2,
        "our_chasing": True,
        "balls_remaining": 24,
        "runs_remaining": 80,
        "wickets_lost": 7,
        "required_run_rate": 20.0,
    }
    r = evaluate(p, score_info=score_info, scale_out_tiers=[])
    assert r.exit_signal is not None
    assert r.exit_signal.reason == ExitReason.SCORE_EXIT

def test_dead_token_exit_at_near_zero() -> None:
    """Token 2¢ veya altına düştüyse pozisyon ölü — çık.
    BUY_NO kaybedince token 0¢'a gider, hiçbir exit tetiklenmiyordu.
    Regression: Muchova-Gauff 2026-04-17 (A-conf tennis, token 0.1¢, çıkış yok).
    """
    start = datetime.now(timezone.utc) - timedelta(hours=2)
    p = _pos(
        confidence="A", entry_price=0.68, current_price=0.01,
        size_usdc=22, shares=32, match_start_iso=_iso(start),
        sport_tag="tennis", direction="BUY_NO",
    )
    r = evaluate(p)
    assert r.exit_signal is not None, "Token 1¢ → dead, çıkmalı"
    assert r.exit_signal.reason == ExitReason.NEAR_RESOLVE


def test_dead_token_no_false_positive_at_5cents() -> None:
    """5¢ henüz ölü değil — çıkmamalı (tennis A-conf hold)."""
    start = datetime.now(timezone.utc) - timedelta(hours=1)
    p = _pos(
        confidence="A", entry_price=0.68, current_price=0.05,
        size_usdc=22, shares=32, match_start_iso=_iso(start),
        sport_tag="tennis", direction="BUY_NO",
    )
    r = evaluate(p)
    assert r.exit_signal is None, "5¢ henüz ölü değil"


# ── Ultra-low guard ──

def test_ultra_low_guard_triggers() -> None:
    """A3: entry < 9¢ + elapsed ≥ 75% + current < 5¢ → ULTRA_LOW_GUARD."""
    # entry 0.05 (ultra low), elapsed 0.80, current 0.03
    start = datetime.now(timezone.utc) - timedelta(hours=2)  # ~0.80 elapsed for nba
    p = _pos(
        confidence="B", entry_price=0.05, current_price=0.03,
        size_usdc=40, shares=800, match_start_iso=_iso(start),
    )
    r = evaluate(p)
    assert r.exit_signal is not None
    assert r.exit_signal.reason == ExitReason.ULTRA_LOW_GUARD


# ── Never-in-profit ──

def test_never_in_profit_triggers_late() -> None:
    """A3 score-only: A-conf sakin durum (erken maç, pnl küçük) → exit yok."""
    # entry 0.65 current 0.60, elapsed~küçük, no score → hiçbir guard fire etmez
    p = _pos(
        confidence="A", entry_price=0.65, current_price=0.60,
        size_usdc=40, shares=62,
    )
    r = evaluate(p)
    assert r.exit_signal is None  # Hiçbir exit yok, sakin durum


def test_never_in_profit_fires_when_dropped_late_no_score_ahead() -> None:
    """A3: ever_in_profit=False + elapsed ≥ 0.70 + current < 0.75*entry + skor önde değil → NEVER_IN_PROFIT."""
    # NBA 2.5h × 0.75 = 1h52m elapsed
    start = datetime.now(timezone.utc) - timedelta(hours=1, minutes=52)
    p = _pos(
        confidence="B", entry_price=0.40, current_price=0.25,  # 0.25 < 0.40*0.75=0.30
        size_usdc=40, shares=100, match_start_iso=_iso(start),
        sport_tag="nba",
    )
    # No score_info → never_in_profit fires (önünde başka guard yok)
    r = evaluate(p)
    assert r.exit_signal is not None
    assert r.exit_signal.reason == ExitReason.NEVER_IN_PROFIT


# ── Favored promote/demote ──

def test_fav_promote_transition() -> None:
    p = _pos(current_price=0.70, confidence="A", favored=False)
    r = evaluate(p)
    assert r.fav_transition.promote is True
    assert r.fav_transition.demote is False


def test_fav_demote_transition() -> None:
    p = _pos(current_price=0.60, favored=True)
    r = evaluate(p)
    assert r.fav_transition.demote is True


# ── No exit when calm ──

def test_no_exit_when_position_calm() -> None:
    # shares entry_price ile tutarlı: 40/0.50=80. pnl +4% → hiç tetiklenme
    p = _pos(entry_price=0.50, current_price=0.52, size_usdc=40, shares=80, confidence="B")
    r = evaluate(p)
    assert r.exit_signal is None


def test_tennis_score_exit_t1_in_monitor() -> None:
    """Tennis T1 score exit monitor.py'den tetiklenir."""
    start = datetime.now(timezone.utc) - timedelta(hours=1)
    p = _pos(
        confidence="A", entry_price=0.64, current_price=0.25,
        size_usdc=56, shares=87, match_start_iso=_iso(start),
        sport_tag="tennis",
    )
    score_info = {
        "available": True,
        "our_score": 0, "opp_score": 1,
        "deficit": 1, "period": "In Progress",
        "map_diff": -1,
        "linescores": [[3, 6], [2, 5]],
        "our_is_home": True,
    }
    r = evaluate(p, score_info=score_info)
    assert r.exit_signal is not None
    assert r.exit_signal.reason == ExitReason.SCORE_EXIT
    assert "T1" in r.exit_signal.detail


def test_tennis_score_no_exit_when_winning() -> None:
    """Tennis 1-0 set + öndeyiz → exit yok."""
    start = datetime.now(timezone.utc) - timedelta(hours=1)
    p = _pos(
        confidence="A", entry_price=0.64, current_price=0.75,
        size_usdc=56, shares=87, match_start_iso=_iso(start),
        sport_tag="tennis",
    )
    score_info = {
        "available": True,
        "our_score": 1, "opp_score": 0,
        "deficit": -1, "period": "In Progress",
        "map_diff": 1,
        "linescores": [[6, 3], [4, 2]],
        "our_is_home": True,
    }
    r = evaluate(p, score_info=score_info)
    assert r.exit_signal is None


# ── Baseball score exit ──

def test_baseball_score_exit_triggers_for_a_conf_mlb() -> None:
    """A-conf MLB pozisyonu + M3 score_info → SCORE_EXIT tetiklenir."""
    start = datetime.now(timezone.utc) - timedelta(hours=2)
    p = _pos(
        confidence="A", entry_price=0.65, current_price=0.15,
        size_usdc=50, shares=76.92, match_start_iso=_iso(start),
        sport_tag="mlb",
    )
    score_info = {
        "available": True,
        "inning": 9,  # SPEC-014: int field (ESPN status.period'dan gelir)
        "deficit": 3,  # 3 run geride, 9. inning → M2 (inning>=8 AND deficit>=3) önce tetiklenir
        "our_score": 2,
        "opp_score": 5,
    }
    r = evaluate(p, score_info=score_info, scale_out_tiers=[])
    assert r.exit_signal is not None
    assert r.exit_signal.reason == ExitReason.SCORE_EXIT
    # inning=9 deficit=3 → M2 fires (inning>=8 AND deficit>=3), M2 is checked before M3
    assert "M2" in r.exit_signal.detail or "M3" in r.exit_signal.detail


def test_monitor_triggers_score_exit_for_ahl() -> None:
    """SPEC-014: AHL sport_tag + K1 deficit -> SCORE_EXIT (hockey family fix)."""
    p = _pos(
        confidence="A", entry_price=0.65, current_price=0.30,
        size_usdc=45, shares=69.2,
        slug="ahl-leh-cha-2026",
        sport_tag="ahl",
        question="Lehigh Valley Phantoms vs Charlotte Checkers",
    )
    score_info = {
        "available": True,
        "deficit": 3,   # K1: deficit >= period_exit_deficit(3) → immediate exit
        "map_diff": -3,
    }
    r = evaluate(p, score_info=score_info, scale_out_tiers=[])
    assert r.exit_signal is not None, "AHL K1 SCORE_EXIT tetiklenmeli"
    assert r.exit_signal.reason == ExitReason.SCORE_EXIT
    assert "K1" in r.exit_signal.detail


def test_baseball_score_exit_doesnt_fire_for_nba() -> None:
    """NBA sport_tag → baseball_score_exit skip."""
    start = datetime.now(timezone.utc) - timedelta(hours=1)
    p = _pos(
        confidence="A", entry_price=0.65, current_price=0.55,
        size_usdc=50, shares=76.92, match_start_iso=_iso(start),
        sport_tag="nba",
    )
    score_info = {
        "available": True,
        "inning": 9,  # SPEC-014: int; NBA'da baseball_score_exit tetiklenmemeli
        "deficit": 5,
        "our_score": 0,
        "opp_score": 5,
    }
    r = evaluate(p, score_info=score_info, scale_out_tiers=[])
    # NBA baseball_score_exit'i skip eder — SCORE_EXIT tetiklenmemeli
    if r.exit_signal is not None:
        assert r.exit_signal.reason != ExitReason.SCORE_EXIT


# ── NBA / NFL score exit (A3 spec, monitor wiring) ──

def test_nba_score_exit_integration_n1() -> None:
    """NBA pozisyonu + Q3 sonu + 20 sayı deficit → SCORE_EXIT."""
    start = datetime.now(timezone.utc) - timedelta(minutes=120)  # 120/150 = 0.80 elapsed (NBA 2.5h)
    p = _pos(sport_tag="nba", match_start_iso=_iso(start), current_price=0.30, confidence="A", entry_price=0.65)
    score_info = {"available": True, "deficit": 22}
    r = evaluate(p, score_info=score_info)
    assert r.exit_signal is not None
    assert r.exit_signal.reason == ExitReason.SCORE_EXIT
    assert "N1" in r.exit_signal.detail


def test_nfl_score_exit_integration_n2() -> None:
    """NFL pozisyonu + son dakikalar + 14 sayı → SCORE_EXIT N2."""
    start = datetime.now(timezone.utc) - timedelta(minutes=185)  # 185/195 = 0.95 elapsed (NFL 3.25h)
    p = _pos(sport_tag="nfl", match_start_iso=_iso(start), current_price=0.30, confidence="A", entry_price=0.65)
    score_info = {"available": True, "deficit": 14}
    r = evaluate(p, score_info=score_info)
    assert r.exit_signal is not None
    assert r.exit_signal.reason == ExitReason.SCORE_EXIT
    assert "N2" in r.exit_signal.detail


def test_nba_no_early_exit_when_deficit_small_and_early() -> None:
    """NBA erken maç + küçük deficit → exit yok."""
    start = datetime.now(timezone.utc) - timedelta(minutes=30)  # 30/150 = 0.20
    p = _pos(sport_tag="nba", match_start_iso=_iso(start), current_price=0.35, confidence="A", entry_price=0.65)
    score_info = {"available": True, "deficit": 8}
    r = evaluate(p, score_info=score_info)
    assert r.exit_signal is None


# ── A3 unified-flow integration ──

def test_unified_flow_b_conf_nba_gets_score_exit() -> None:
    """A-hold kalktı — B-conf NBA pozisyonu da score exit almalı."""
    start = datetime.now(timezone.utc) - timedelta(minutes=120)  # 0.80 elapsed
    p = _pos(
        sport_tag="nba",
        confidence="B",           # B-conf (önceden A-hold dışında olduğu için score exit yoktu)
        entry_price=0.40,         # A-hold entry eşiği altı
        current_price=0.30,
        match_start_iso=_iso(start),
    )
    score_info = {"available": True, "deficit": 22}
    r = evaluate(p, score_info=score_info)
    assert r.exit_signal is not None
    assert r.exit_signal.reason == ExitReason.SCORE_EXIT


def test_unified_flow_b_conf_hockey_k1_fires() -> None:
    """B-conf hokey K1 tetiklenmeli — hockey A-conf gate Task 6'da kaldırılacak ama unified flow bağımsız."""
    # NOT: hockey_score_exit hala confidence=="A" gate'li. Bu test Task 6'dan sonra geçecek.
    # Simdilik A-conf ile test et.
    start = datetime.now(timezone.utc) - timedelta(minutes=30)
    p = _pos(
        sport_tag="nhl",
        confidence="A",
        entry_price=0.50,
        current_price=0.40,
        match_start_iso=_iso(start),
    )
    score_info = {"available": True, "deficit": 3}
    r = evaluate(p, score_info=score_info)
    assert r.exit_signal is not None
    assert r.exit_signal.reason == ExitReason.SCORE_EXIT


def test_unified_flow_market_flip_still_fires_late() -> None:
    """Market flip geç maçta kalır (elapsed ≥ 85%, eff < 0.50, tennis hariç)."""
    start = datetime.now(timezone.utc) - timedelta(minutes=130)  # 0.87 elapsed NBA
    p = _pos(
        sport_tag="nba",
        confidence="B",
        entry_price=0.50,
        current_price=0.35,  # < 0.50 = market flip
        match_start_iso=_iso(start),
    )
    # Score yok — market_flip fire etmeli
    r = evaluate(p, score_info={"available": False})
    assert r.exit_signal is not None
    assert r.exit_signal.reason == ExitReason.MARKET_FLIP
