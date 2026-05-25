"""Retroactive replay orchestration pipeline.

Bu modül `scripts/apply_retroactive_replay.py` tarafından kullanılır. Script
sadece CLI argümanları + dosya I/O + print yapar; gerçek iş akışı burada.

Sorumluluklar:
  - sport_rules + strategy.exit sabitlerinden ExitRulesConfig topla
  - açık pozisyonları replay engine'e besle
  - mevcut audit kayıtlarını gözden geçir (retroactive correction)
  - simulated exit'leri trade_history.jsonl yapısına çevir
  - özet satırları hazırla

Tam side-effect (yazma): scripts/apply_retroactive_replay.py'da.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Any, Callable

from src.config.settings import ScaleOutConfig
from src.config.sport_rules import (
    get_match_duration_hours,
    get_sport_rule,
    get_stop_loss,
)
from src.domain.replay.replay_engine import (
    ExitRulesConfig,
    ReplayResult,
    SimulatedExit,
    replay_position,
)
from src.infrastructure.persistence.price_history_fetcher import fetch_price_history
from src.strategy.exit.resolved import LOST_THRESHOLD, WON_THRESHOLD

# Closed-record retroactive correction guard: yakın kayıtlara dokunma.
MIN_HOURS_FOR_CORRECTION = 2.0


def rules_for(sport_tag: str) -> ExitRulesConfig:
    """Strategy modüllerinden + sport_rules'tan canlı eşikleri topla.

    Scale-out: production ile aynı distance-based eşikler — ScaleOutConfig()
    defaults [tier1=0.40/0.40, tier2=0.70/0.50]. Replay tier'i progress
    (= (current-entry)/(1-entry)) üzerinden tetikler.
    """
    so_cfg = ScaleOutConfig()
    tier1 = so_cfg.tiers[0]
    tier2 = so_cfg.tiers[1]
    return ExitRulesConfig(
        tier1_threshold=tier1.threshold,
        tier1_sell_pct=tier1.sell_pct,
        tier2_threshold=tier2.threshold,
        tier2_sell_pct=tier2.sell_pct,
        lost_threshold=LOST_THRESHOLD,
        won_threshold=WON_THRESHOLD,
        near_resolve_threshold=int(
            get_sport_rule(sport_tag, "near_resolve_threshold_cents", 94)
        ) / 100.0,
        near_resolve_guard_minutes=int(
            get_sport_rule(sport_tag, "near_resolve_guard_min", 5)
        ),
        stop_loss_pct=get_stop_loss(sport_tag),
        match_duration_hours=get_match_duration_hours(sport_tag),
    )


@dataclass
class SummaryRow:
    slug: str
    original_label: str
    simulated_label: str
    diff_label: str


@dataclass
class OpenReplayOutcome:
    summary_rows: list[SummaryRow]
    new_audit_lines: list[dict]
    closed_condition_ids: list[str]
    total_simulated_pnl: float


@dataclass
class ClosedReplayOutcome:
    summary_rows: list[SummaryRow]
    rewritten_records: list[dict]
    total_delta_pnl: float


def _hours_since(iso: str, now: datetime) -> float:
    try:
        ts = datetime.fromisoformat(iso.replace("Z", "+00:00"))
    except (ValueError, TypeError):
        return -1.0
    return (now - ts).total_seconds() / 3600.0


def _format_simulated_exit(
    pos: dict, exit_obj: SimulatedExit, original_size: float,
) -> dict:
    """SimulatedExit → trade_history.jsonl yapısına çevir (simulated:true flag)."""
    invested = original_size * exit_obj.sell_pct_of_original
    pnl_pct = (exit_obj.realized_pnl_usdc / invested) if invested > 0 else 0.0
    return {
        "slug": pos.get("slug", ""),
        "condition_id": pos.get("condition_id", ""),
        "event_id": pos.get("event_id", ""),
        "token_id": pos.get("token_id", ""),
        "question": pos.get("question", ""),
        "sport_tag": pos.get("sport_tag", ""),
        "direction": pos.get("direction", ""),
        "entry_price": pos.get("entry_price"),
        "size_usdc": original_size,
        "shares": pos.get("shares", 0.0),
        "confidence": pos.get("confidence", ""),
        "anchor_probability": pos.get("anchor_probability"),
        "entry_reason": pos.get("entry_reason", ""),
        "entry_timestamp": pos.get("entry_timestamp", ""),
        "exit_price": exit_obj.price,
        "exit_reason": exit_obj.reason,
        "exit_pnl_usdc": round(exit_obj.realized_pnl_usdc, 4),
        "exit_pnl_pct": round(pnl_pct, 4),
        "exit_timestamp": exit_obj.timestamp_iso,
        "partial_exits": [],
        "partial": exit_obj.tier is not None,
        "sell_pct": exit_obj.sell_pct,
        "tier": exit_obj.tier,
        "simulated": True,
        "simulated_detail": exit_obj.detail,
    }


def simulate_open_position(
    pos: dict,
    http_get: Callable[..., Any] | None = None,
) -> ReplayResult:
    """Bir açık pozisyon için CLOB history çek + replay.

    direction parametresi ENGINE açısından her zaman "BUY_YES":
    token_id zaten doğru tarafın id'si (BUY_NO için NO token id) → CLOB onun
    raw fiyatını döner ve entry_price token-native saklanır.
    """
    entry_iso = pos.get("entry_timestamp", "")
    fetch_kwargs: dict[str, Any] = {
        "token_id": pos["token_id"], "start_iso": entry_iso,
    }
    if http_get is not None:
        fetch_kwargs["http_get"] = http_get
    history = fetch_price_history(**fetch_kwargs)
    rules = rules_for(pos.get("sport_tag", ""))
    return replay_position(
        entry_price=float(pos["entry_price"]),
        direction="BUY_YES",
        size_usdc=float(pos["size_usdc"]),
        shares=float(pos["shares"]),
        match_start_iso=pos.get("match_start_iso", ""),
        price_history=history,
        rules=rules,
        initial_scale_out_tier=int(pos.get("scale_out_tier", 0) or 0),
        initial_partial_exits=pos.get("partial_exits") or [],
    )


def process_open_positions(
    positions_state: dict,
    http_get: Callable[..., Any] | None = None,
) -> OpenReplayOutcome:
    """Tüm açık pozisyonları sırayla simüle et."""
    outcome = OpenReplayOutcome(
        summary_rows=[], new_audit_lines=[], closed_condition_ids=[],
        total_simulated_pnl=0.0,
    )
    positions = positions_state.get("positions", {}) or {}
    for cid, pos in positions.items():
        slug = pos.get("slug", "?")
        original_size = float(
            pos.get("original_size_usdc") or pos.get("size_usdc", 0.0)
        )
        try:
            res = simulate_open_position(pos, http_get=http_get)
        except Exception as e:  # noqa: BLE001 — script-level guard, raporla devam
            outcome.summary_rows.append(SummaryRow(
                slug=slug, original_label="(open)",
                simulated_label=f"err: {e!s:.30}", diff_label="-",
            ))
            continue
        if not res.fired_any:
            outcome.summary_rows.append(SummaryRow(
                slug=slug, original_label="(open)",
                simulated_label="(no change)", diff_label="-",
            ))
            continue
        outcome.total_simulated_pnl += res.realized_pnl_total
        for ex in res.exits:
            outcome.new_audit_lines.append(_format_simulated_exit(pos, ex, original_size))
        last = res.exits[-1]
        outcome.summary_rows.append(SummaryRow(
            slug=slug,
            original_label="(open)",
            simulated_label=f"${res.realized_pnl_total:+.2f} {last.reason}",
            diff_label=f"${res.realized_pnl_total:+.2f} (new)",
        ))
        if res.closed:
            outcome.closed_condition_ids.append(cid)
    return outcome


def process_closed_records(
    audit_records: list[dict],
    now: datetime,
    http_get: Callable[..., Any] | None = None,
) -> ClosedReplayOutcome:
    """Eski 'resolved' kayıtları retroactive partial'lar için gözden geçir."""
    outcome = ClosedReplayOutcome(
        summary_rows=[], rewritten_records=[], total_delta_pnl=0.0,
    )
    for rec in audit_records:
        if rec.get("exit_reason") != "resolved":
            continue
        if rec.get("partial_exits"):
            continue
        entry_iso = rec.get("entry_timestamp", "")
        if _hours_since(entry_iso, now) < MIN_HOURS_FOR_CORRECTION:
            continue
        slug = rec.get("slug", "?")
        end_iso = rec.get("exit_timestamp", "") or ""
        fetch_kwargs: dict[str, Any] = {
            "token_id": rec.get("token_id", ""),
            "start_iso": entry_iso, "end_iso": end_iso,
        }
        if http_get is not None:
            fetch_kwargs["http_get"] = http_get
        history = fetch_price_history(**fetch_kwargs)
        rules = rules_for(rec.get("sport_tag", ""))
        res = replay_position(
            entry_price=float(rec.get("entry_price", 0.0)),
            direction="BUY_YES",
            size_usdc=float(rec.get("size_usdc", 0.0)),
            shares=float(rec.get("shares", 0.0)),
            match_start_iso=entry_iso,
            price_history=history,
            rules=rules,
        )
        partials_found = [ex for ex in res.exits if ex.tier is not None]
        if not partials_found:
            continue
        original_pnl = float(rec.get("exit_pnl_usdc", 0.0))
        new_pnl = res.realized_pnl_total
        outcome.total_delta_pnl += (new_pnl - original_pnl)
        new_rec = dict(rec)
        new_rec["partial_exits"] = [
            {
                "tier": ex.tier, "sell_pct": ex.sell_pct,
                "realized_pnl_usdc": round(ex.realized_pnl_usdc, 4),
                "timestamp": ex.timestamp_iso, "price": ex.price,
                "simulated": True,
            }
            for ex in partials_found
        ]
        last = res.exits[-1]
        new_rec["exit_pnl_usdc"] = round(last.realized_pnl_usdc, 4)
        new_rec["exit_price"] = last.price
        new_rec["exit_timestamp"] = last.timestamp_iso
        new_rec["simulated_correction"] = True
        outcome.rewritten_records.append(new_rec)
        outcome.summary_rows.append(SummaryRow(
            slug=slug,
            original_label=f"${original_pnl:+.2f}",
            simulated_label=f"${new_pnl:+.2f}",
            diff_label=f"${(new_pnl - original_pnl):+.2f}",
        ))
    return outcome
