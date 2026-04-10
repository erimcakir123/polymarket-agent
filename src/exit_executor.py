"""exit_executor.py -- Exit execution logic extracted from agent.py.

Handles position exits, scale-outs, stock demotions, and hold revokes.
All methods operate on Agent instance (ctx) for shared state access.
"""
from __future__ import annotations

import logging
from datetime import datetime, timezone
from pathlib import Path
import json

from src.models import effective_price
from src.reentry import get_blacklist_rule

logger = logging.getLogger(__name__)

# Exits that should never be demoted to stock (permanent skip)
_NEVER_STOCK_EXITS = frozenset({
    "hard_halt_drawdown", "hard_halt", "stop_loss", "esports_halftime",
    "resolved", "near_resolve", "near_resolve_profit",
})
_NEVER_STOCK_PREFIXES = ("match_exit_", "election_reeval", "early_penny_")


class ExitExecutor:
    """Executes position exits, scale-outs, and stock demotions."""

    def __init__(self, ctx) -> None:
        self.ctx = ctx

    def exit_position(self, condition_id: str, reason: str, cooldown_cycles: int = 1) -> None:
        """Execute exit: remove from portfolio, add to reentry pool or blacklist, log.

        This is the ONLY place that calls executor.exit(). ExitMonitor detects,
        Agent executes.
        """
        self.ctx.exit_monitor.mark_exiting(condition_id)
        try:
            pos = self.ctx.portfolio.remove_position(condition_id)
        finally:
            self.ctx.exit_monitor.unmark_exiting(condition_id)
        if not pos:
            return

        self.ctx._exit_cooldowns[condition_id] = self.ctx.cycle_count + cooldown_cycles

        # Execute via executor — if live sell fails, restore position
        sell_result = self.ctx.executor.exit_position(pos, reason=reason, mode=self.ctx.config.mode)
        if sell_result.get("status") == "error":
            logger.error("EXIT SELL FAILED for %s — restoring position: %s",
                         pos.slug[:35], sell_result.get("reason", "unknown"))
            self.ctx.portfolio.positions[condition_id] = pos
            self.ctx.portfolio.bankroll -= pos.size_usdc
            self.ctx.portfolio._save_positions()
            return

        # Record realized PnL
        realized_pnl = pos.unrealized_pnl_usdc
        self.ctx.portfolio.record_realized(realized_pnl)

        # Profitable exit -> add to farming re-entry pool
        profitable_reasons = {
            "take_profit", "trailing_tp", "spike_exit",
            "edge_tp", "scale_out_final", "vs_take_profit",
        }
        if any(reason.startswith(r) for r in profitable_reasons) and realized_pnl > 0:
            existing_pool = self.ctx.reentry_pool.get(condition_id)
            original_entry = existing_pool.original_entry_price if existing_pool else pos.entry_price
            self.ctx.reentry_pool.add(
                condition_id=condition_id,
                event_id=getattr(pos, "event_id", "") or "",
                slug=pos.slug,
                question=getattr(pos, "question", ""),
                direction=pos.direction,
                token_id=pos.token_id,
                ai_probability=pos.ai_probability,
                confidence=pos.confidence,
                original_entry_price=original_entry,
                exit_price=pos.current_price,
                exit_cycle=self.ctx.cycle_count,
                end_date_iso=getattr(pos, "end_date_iso", ""),
                match_start_iso=getattr(pos, "match_start_iso", ""),
                sport_tag=getattr(pos, "sport_tag", ""),
                number_of_games=getattr(pos, "number_of_games", 0),
                was_scouted=getattr(pos, "scouted", False),
                realized_pnl=realized_pnl,
            )
        elif reason == "stop_loss":
            # Lossy re-entry: SL exits can rejoin pool under strict conditions
            _sl_count = getattr(pos, 'sl_reentry_count', 0)
            if _sl_count >= 1:
                # 2nd SL after lossy re-entry = permanent blacklist
                self.ctx.blacklist.add(
                    condition_id,
                    exit_reason="stop_loss_2nd",
                    blacklist_type="permanent",
                    expires_at_cycle=None,
                    exit_data={"slug": pos.slug},
                )
                logger.info("BLACKLIST: 2nd SL after lossy re-entry, permanent ban: %s", pos.slug[:40])
            elif pos.ai_probability >= 0.65:
                # AI still believes in the market -- add to pool for potential recovery
                existing_pool = self.ctx.reentry_pool.get(condition_id)
                original_entry = existing_pool.original_entry_price if existing_pool else pos.entry_price
                self.ctx.reentry_pool.add(
                    condition_id=condition_id,
                    event_id=getattr(pos, "event_id", "") or "",
                    slug=pos.slug,
                    question=getattr(pos, "question", ""),
                    direction=pos.direction,
                    token_id=pos.token_id,
                    ai_probability=pos.ai_probability,
                    confidence=pos.confidence,
                    original_entry_price=original_entry,
                    exit_price=pos.current_price,
                    exit_cycle=self.ctx.cycle_count,
                    end_date_iso=getattr(pos, "end_date_iso", ""),
                    match_start_iso=getattr(pos, "match_start_iso", ""),
                    sport_tag=getattr(pos, "sport_tag", ""),
                    number_of_games=getattr(pos, "number_of_games", 0),
                    was_scouted=getattr(pos, "scouted", False),
                    realized_pnl=realized_pnl,
                    exit_reason="stop_loss",
                    sl_reentry_count=0,
                )
                logger.info("REENTRY_POOL: SL exit added (AI=%.0f%%): %s",
                            pos.ai_probability * 100, pos.slug[:40])
            else:
                # AI prob < 65% -- normal blacklist for SL
                btype, duration = get_blacklist_rule("stop_loss")
                if btype and duration:
                    self.ctx.blacklist.add(
                        condition_id,
                        exit_reason=reason,
                        blacklist_type=btype,
                        expires_at_cycle=self.ctx.cycle_count + duration if duration else None,
                        exit_data={"slug": pos.slug},
                    )
        else:
            # Non-profitable -> demote to stock or blacklist
            _is_never_stock = (
                reason in _NEVER_STOCK_EXITS
                or any(reason.startswith(p) for p in _NEVER_STOCK_PREFIXES)
            )
            demoted = False
            if not _is_never_stock:
                demoted = self.try_demote_to_stock(pos, reason)
            if not demoted:
                # Blacklist
                bl_reason = reason
                for prefix in ("match_exit_", "early_penny_"):
                    if bl_reason.startswith(prefix):
                        # Preserve the layer name after the prefix so BLACKLIST_RULES
                        # can match it (e.g. "match_exit_catastrophic_floor" →
                        # "catastrophic_floor" → permanent blacklist).
                        bl_reason = bl_reason[len(prefix):]
                        break
                # Elapsed_pct for graduated_sl dynamic cooldown: compute from pos timing
                _elapsed_for_bl = 0.0
                _ms = getattr(pos, "match_start_iso", "") or ""
                if _ms:
                    try:
                        from src.match_exit import get_game_duration
                        _start_dt = datetime.fromisoformat(_ms.replace("Z", "+00:00"))
                        _elapsed_min = (datetime.now(timezone.utc) - _start_dt).total_seconds() / 60
                        _dur = get_game_duration(
                            pos.slug or "", getattr(pos, "number_of_games", 0),
                            getattr(pos, "sport_tag", "") or "",
                        )
                        if _dur > 0:
                            _elapsed_for_bl = _elapsed_min / _dur
                    except (ValueError, TypeError, ImportError):
                        _elapsed_for_bl = 0.0
                btype, duration = get_blacklist_rule(bl_reason, _elapsed_for_bl)
                # "none" type means no blacklist; "permanent" has duration=None but
                # must still be recorded (expires_at_cycle=None encodes permanent).
                if btype and btype != "none":
                    self.ctx.blacklist.add(
                        condition_id,
                        exit_reason=reason,
                        blacklist_type=btype,
                        expires_at_cycle=self.ctx.cycle_count + duration if duration else None,
                        exit_data={"slug": pos.slug},
                    )

        # Net PnL includes prior scale-out proceeds so dashboard/notifier show
        # the true per-position result (e.g. scale-out +$2.56 then final -$0.64
        # = net +$1.92, instead of just the final leg -$0.64).
        scale_out_pnl = getattr(pos, "scale_out_realized_usdc", 0.0) or 0.0
        total_pnl = realized_pnl + scale_out_pnl

        # Log exit
        self.ctx.trade_log.log({
            "market": pos.slug, "action": "EXIT",
            "reason": reason, "pnl": realized_pnl,
            "scale_out_pnl": scale_out_pnl,
            "total_pnl": total_pnl,
            "price": pos.entry_price, "exit_price": pos.current_price,
            "size": pos.size_usdc,
            "direction": pos.direction,
        })
        # Display prices must reflect the direction-effective side (NO vs YES),
        # otherwise BUY_NO exits look like wins when they're actually losses.
        # PnL/arşiv/price_history ham YES-side saklanmaya devam eder.
        _eff_entry = effective_price(pos.entry_price, pos.direction)
        _eff_exit = effective_price(pos.current_price, pos.direction)
        _side_tag = "NO" if pos.direction == "BUY_NO" else "YES"
        logger.info(
            "EXIT: %s | reason=%s | pnl=$%.2f (scale_out=$%.2f, net=$%.2f) | entry=%.2f exit=%.2f (%s)",
            pos.slug[:40], reason, realized_pnl, scale_out_pnl, total_pnl,
            _eff_entry, _eff_exit, _side_tag,
        )
        _pnl_emoji = "🟢" if total_pnl >= 0 else "🔴"
        _scale_line = f" (scale-out +${scale_out_pnl:.2f})" if scale_out_pnl > 0 else ""
        self.ctx.notifier.send(
            f"{_pnl_emoji} *EXIT*: {pos.slug[:40]}\n\n"
            f"📋 Reason: {reason}\n"
            f"💵 Net PnL: ${total_pnl:+.2f}{_scale_line}\n"
            f"📊 Entry: {_eff_entry:.2f} -> Exit: {_eff_exit:.2f} ({_side_tag})"
        )

        # Mark permanently exited if resolved
        if reason in ("resolved", "near_resolve", "near_resolve_profit"):
            self.save_exited_market(condition_id)

        # Post-exit: save CLOB price history for calibration
        try:
            from src.price_history import save_price_history
            save_price_history(
                slug=pos.slug, token_id=pos.token_id,
                entry_price=pos.entry_price, exit_price=pos.current_price,
                exit_reason=reason, exit_layer="agent",
                match_start_iso=getattr(pos, "match_start_iso", ""),
                number_of_games=getattr(pos, "number_of_games", 0),
                ever_in_profit=pos.peak_pnl_pct > 0,
                peak_pnl_pct=pos.peak_pnl_pct,
                match_score=getattr(pos, "match_score", ""),
            )
        except Exception:
            pass

        # Track for post-exit resolution (did we exit too early/late?)
        try:
            self.ctx.outcome_tracker.track(
                condition_id=condition_id,
                token_id=pos.token_id,
                slug=pos.slug,
                question=getattr(pos, "question", ""),
                direction=pos.direction,
                ai_probability=pos.ai_probability,
                confidence=pos.confidence,
                entry_price=pos.entry_price,
                exit_price=pos.current_price,
                exit_reason=reason,
                pnl=total_pnl,
                size=pos.size_usdc,
                sport_tag=getattr(pos, "sport_tag", ""),
                entry_reason=getattr(pos, "entry_reason", ""),
                scouted=getattr(pos, "scouted", False),
                peak_pnl_pct=pos.peak_pnl_pct,
                match_score=getattr(pos, "match_score", ""),
                cycles_held=getattr(pos, "cycles_held", 0),
                bookmaker_prob=getattr(pos, "bookmaker_prob", 0.0),
            )
        except Exception:
            pass

    def process_scale_outs(self) -> None:
        """Check and execute partial scale-out exits for all positions."""
        from src.scale_out import apply_partial_exit, SCALE_OUT_TIERS

        # --- WS force-execute block: honour flags set by WS price-spike detection ---
        for cid, pos in list(self.ctx.portfolio.positions.items()):
            tier = getattr(pos, 'force_scale_out_tier', None)
            if tier is None:
                continue
            # Clear immediately to prevent re-fire
            pos.force_scale_out_tier = None

            if self.ctx.exit_monitor.is_exiting(cid):
                continue

            tier_info = SCALE_OUT_TIERS.get(tier)
            if not tier_info:
                logger.warning("WS FORCE SCALE-OUT: unknown tier %s for %s", tier, cid)
                continue

            sell_pct = tier_info["sell_pct"]
            shares_to_sell = pos.shares * sell_pct
            if shares_to_sell < 1.0:
                continue

            eff_sell_price = effective_price(pos.current_price, pos.direction)
            result = self.ctx.executor.place_order(
                pos.token_id, "SELL", eff_sell_price,
                shares_to_sell * eff_sell_price, use_hybrid=False,
            )
            if not result or result.get("status") == "error":
                logger.warning("WS FORCE SCALE-OUT failed: %s | tier=%s", pos.slug[:35], tier)
                continue

            _sell_fill = result.get("price", eff_sell_price)
            fill_price = _sell_fill if pos.direction == "BUY_YES" else (1.0 - _sell_fill)
            partial = apply_partial_exit(
                shares=pos.shares,
                size_usdc=pos.size_usdc,
                entry_price=pos.entry_price,
                direction=pos.direction,
                shares_sold=shares_to_sell,
                fill_price=fill_price,
                tier=tier,
                original_shares=getattr(pos, "original_shares", None),
                original_size_usdc=getattr(pos, "original_size_usdc", None),
                scale_out_tier=pos.scale_out_tier,
            )

            pos.shares = partial["remaining_shares"]
            pos.size_usdc = partial["remaining_size_usdc"]
            pos.scale_out_tier = partial["new_scale_out_tier"]
            if not hasattr(pos, "original_shares") or pos.original_shares is None:
                pos.original_shares = partial["original_shares"]
            if not hasattr(pos, "original_size_usdc") or pos.original_size_usdc is None:
                pos.original_size_usdc = partial["original_size_usdc"]

            self.ctx.portfolio.record_realized(partial["realized_pnl"])
            pos.scale_out_realized_usdc += partial["realized_pnl"]

            logger.info("WS FORCE SCALE-OUT: %s | %s | sold %.0f shares | pnl=$%.2f",
                        pos.slug[:35], tier, shares_to_sell, partial["realized_pnl"])

        scale_outs = self.ctx.portfolio.check_scale_outs()
        for so in scale_outs:
            cid = so["condition_id"]
            pos = self.ctx.portfolio.positions.get(cid)
            if not pos or self.ctx.exit_monitor.is_exiting(cid):
                continue

            shares_to_sell = pos.shares * so["sell_pct"]
            if shares_to_sell < 1.0:
                continue

            # pos.current_price is stored YES-side for consistency across the
            # codebase. But we're selling a specific token (YES or NO), and the
            # executor's stale-price guard will fetch the live fill price for
            # THAT token — so we must pass the direction-effective price, not
            # the YES-side price. Otherwise BUY_NO scale-outs hit a ~(1 - price)
            # drift vs reality and get silently rejected by the guard.
            eff_sell_price = effective_price(pos.current_price, pos.direction)

            # Execute partial sell (disable hybrid to preserve exact share count)
            result = self.ctx.executor.place_order(
                pos.token_id, "SELL", eff_sell_price,
                shares_to_sell * eff_sell_price, use_hybrid=False,
            )
            if not result or result.get("status") == "error":
                continue

            # Use executor's actual fill price (may have been adjusted by the
            # stale-price guard); fall back to our effective price.
            _sell_fill = result.get("price", eff_sell_price)
            # Convert back to YES-side for downstream bookkeeping (apply_partial_exit
            # expects fill_price in the same space as entry_price, which is YES-side).
            fill_price = _sell_fill if pos.direction == "BUY_YES" else (1.0 - _sell_fill)
            partial = apply_partial_exit(
                shares=pos.shares,
                size_usdc=pos.size_usdc,
                entry_price=pos.entry_price,
                direction=pos.direction,
                shares_sold=shares_to_sell,
                fill_price=fill_price,
                tier=so["tier"],
                original_shares=getattr(pos, "original_shares", None),
                original_size_usdc=getattr(pos, "original_size_usdc", None),
                scale_out_tier=pos.scale_out_tier,
            )

            # Update position in-place
            pos.shares = partial["remaining_shares"]
            pos.size_usdc = partial["remaining_size_usdc"]
            pos.scale_out_tier = partial["new_scale_out_tier"]
            if not hasattr(pos, "original_shares") or pos.original_shares is None:
                pos.original_shares = partial["original_shares"]
            if not hasattr(pos, "original_size_usdc") or pos.original_size_usdc is None:
                pos.original_size_usdc = partial["original_size_usdc"]

            # Record proceeds and realized PnL
            self.ctx.portfolio.record_realized(partial["realized_pnl"])
            # Accumulate on position for net-PnL display at final exit
            pos.scale_out_realized_usdc += partial["realized_pnl"]

            # Close dust remainder
            if partial["status"] == "CLOSE_REMAINDER":
                self.exit_position(cid, "scale_out_final")
                continue

            self.ctx.trade_log.log({
                "market": pos.slug, "action": "SCALE_OUT",
                "tier": so["tier"], "sell_pct": so["sell_pct"],
                "shares_sold": shares_to_sell,
                "realized_pnl": partial["realized_pnl"],
                "remaining_shares": partial["remaining_shares"],
            })
            logger.info(
                "SCALE_OUT: %s | %s | sold %.0f shares | pnl=$%.2f | remaining=%.0f",
                pos.slug[:35], so["tier"], shares_to_sell,
                partial["realized_pnl"], partial["remaining_shares"],
            )

        # Persist position changes to disk
        if scale_outs:
            self.ctx.portfolio._save_positions()

    def try_demote_to_stock(self, pos, reason: str) -> bool:
        """Demote exited position back to candidate stock queue for re-entry.

        Accepts if stock has room (< 10) OR score beats the worst existing entry.
        Returns True if demoted, False if rejected (-> caller will blacklist instead).
        """
        from src.models import MarketData
        from src.ai_analyst import AIEstimate

        _CONF_SCORE: dict[str, int] = {"A": 4, "B+": 3, "B-": 2, "C": 1}
        STOCK_MAX = 10

        # Calculate ranking score from saved position data
        pos_edge = max(0.0, abs(pos.ai_probability - pos.current_price))
        pos_score = pos_edge * _CONF_SCORE.get(getattr(pos, "confidence", "C"), 1)

        stock = self.ctx.entry_gate._candidate_stock

        # Decide whether to accept
        if len(stock) < STOCK_MAX:
            accept = True
        else:
            worst_score = min((c.get("score", 0.0) for c in stock), default=0.0)
            accept = pos_score > worst_score
            if accept:
                # Evict worst entry to make room
                worst_idx = min(range(len(stock)), key=lambda i: stock[i].get("score", 0.0))
                stock.pop(worst_idx)

        if not accept:
            return False

        # Reconstruct MarketData from position fields
        is_buy_yes = pos.direction == "BUY_YES"
        try:
            market = MarketData(
                condition_id=pos.condition_id,
                question=getattr(pos, "question", ""),
                yes_price=pos.current_price,
                no_price=round(1.0 - pos.current_price, 4),
                yes_token_id=pos.token_id if is_buy_yes else "",
                no_token_id=pos.token_id if not is_buy_yes else "",
                slug=pos.slug,
                sport_tag=getattr(pos, "sport_tag", "") or "",
                event_id=getattr(pos, "event_id", "") or "",
                end_date_iso=getattr(pos, "end_date_iso", "") or "",
                match_start_iso=getattr(pos, "match_start_iso", "") or "",
            )
        except Exception as exc:
            logger.warning("Could not reconstruct MarketData for stock demotion: %s", exc)
            return False

        estimate = AIEstimate(
            ai_probability=pos.ai_probability,
            confidence=getattr(pos, "confidence", "B-"),
            reasoning_pro="(demoted -- re-evaluate at entry)",
            reasoning_con="",
        )

        candidate = {
            "score": pos_score,
            "condition_id": pos.condition_id,
            "market": market,
            "estimate": estimate,
            "direction": pos.direction,
            "edge": pos_edge,
            "adjusted_size": 0.0,  # recalculated at execution time
            "entry_reason": "demoted",
            "is_consensus": False,
            "is_early": False,
            "sanity": None,
            "manip_check": None,
        }

        self.ctx.entry_gate.push_to_stock(candidate)
        logger.info(
            "DEMOTED to stock: %s | score=%.3f | reason=%s | stock_size=%d",
            pos.slug[:35], pos_score, reason, len(self.ctx.entry_gate._candidate_stock),
        )
        return True

    def handle_hold_revokes(self) -> None:
        """Apply match_exit hold-revoke and hold-restore mutations to positions."""
        for mexr in self.ctx.exit_monitor.match_exit_hold_revokes():
            cid = mexr["condition_id"]
            if mexr.get("revoke_hold") and cid in self.ctx.portfolio.positions:
                pos = self.ctx.portfolio.positions[cid]
                if pos.scouted:
                    pos.hold_was_original = True
                    pos.scouted = False
                    pos.hold_revoked_at = datetime.now(timezone.utc)
                    logger.info("Hold REVOKED: %s -- %s", pos.slug[:40], mexr.get("reason", ""))
            if mexr.get("restore_hold") and cid in self.ctx.portfolio.positions:
                pos = self.ctx.portfolio.positions[cid]
                pos.scouted = True
                pos.hold_revoked_at = None
                logger.info("Hold RESTORED: %s", pos.slug[:40])

    def save_exited_market(self, cid: str) -> None:
        self.ctx._exited_markets.add(cid)
        self.ctx._pre_match_prices.pop(cid, None)  # Clean stale cache entry
        try:
            Path("logs/exited_markets.json").write_text(json.dumps(list(self.ctx._exited_markets)), encoding="utf-8")
        except Exception:
            pass
