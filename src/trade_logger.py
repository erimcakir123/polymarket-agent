"""Append-only JSONL trade logger with edge source tracking."""
from __future__ import annotations
import json
import logging
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional

logger = logging.getLogger(__name__)

# Minimum samples before judging an edge source
EDGE_SOURCE_MIN_SAMPLES = 30
# Win rate below this → kill the source
EDGE_SOURCE_KILL_THRESHOLD = 0.52


class TradeLogger:
    def __init__(self, file_path: str) -> None:
        self.path = Path(file_path)
        self.path.parent.mkdir(parents=True, exist_ok=True)

    def log(self, data: dict[str, Any]) -> None:
        data = {**data}  # Don't mutate caller's dict
        if "timestamp" not in data:
            data["timestamp"] = datetime.now(timezone.utc).isoformat()
        with open(self.path, "a", encoding="utf-8") as f:
            f.write(json.dumps(data, default=str) + "\n")

    def read_recent(self, n: int = 50) -> list[dict[str, Any]]:
        if not self.path.exists():
            return []
        # Read from end of file — avoids loading entire file into memory
        try:
            with open(self.path, "rb") as f:
                f.seek(0, 2)
                size = f.tell()
                # Read last chunk (generous: ~500 bytes per line)
                chunk_size = min(size, n * 500)
                f.seek(size - chunk_size)
                data = f.read().decode("utf-8", errors="replace")
            lines = [l for l in data.strip().split("\n") if l.strip()]
            # If we didn't read from the start, first line may be partial
            if chunk_size < size:
                lines = lines[1:]
            result = []
            for l in lines[-n:]:
                try:
                    result.append(json.loads(l))
                except json.JSONDecodeError:
                    continue
            return result
        except OSError:
            return []

    def read_all(self) -> list[dict[str, Any]]:
        if not self.path.exists():
            return []
        lines = self.path.read_text(encoding="utf-8").strip().split("\n")
        result = []
        for l in lines:
            if not l.strip():
                continue
            try:
                result.append(json.loads(l))
            except json.JSONDecodeError:
                continue
        return result


class EdgeSourceTracker:
    """Track win/loss per edge source. Kill sources with <52% win rate after 30 samples.

    Edge sources: "ai_standard", "ai_anchored", "bond_farming", "live_momentum",
                  "penny_alpha", "fav_time_gate", "volatility_swing", "farming_reentry"
    """

    def __init__(self, stats_path: str = "logs/edge_source_stats.json") -> None:
        self.stats_path = Path(stats_path)
        self._stats: dict[str, dict[str, int]] = {}  # source → {"wins": N, "losses": N}
        self._killed_sources: set[str] = set()
        self._load()

    def _load(self) -> None:
        if not self.stats_path.exists():
            return
        try:
            data = json.loads(self.stats_path.read_text(encoding="utf-8"))
            self._stats = data.get("stats", {})
            self._killed_sources = set(data.get("killed", []))
        except (json.JSONDecodeError, OSError):
            logger.warning("Could not load edge source stats — starting fresh")

    def _save(self) -> None:
        self.stats_path.parent.mkdir(parents=True, exist_ok=True)
        tmp = self.stats_path.with_suffix(".tmp")
        tmp.write_text(json.dumps({
            "stats": self._stats,
            "killed": list(self._killed_sources),
            "updated_at": datetime.now(timezone.utc).isoformat(),
        }), encoding="utf-8")
        tmp.replace(self.stats_path)

    def record_outcome(self, source: str, won: bool) -> None:
        """Record a win or loss for an edge source."""
        if source not in self._stats:
            self._stats[source] = {"wins": 0, "losses": 0}
        if won:
            self._stats[source]["wins"] += 1
        else:
            self._stats[source]["losses"] += 1

        # Check kill threshold
        s = self._stats[source]
        total = s["wins"] + s["losses"]
        if total >= EDGE_SOURCE_MIN_SAMPLES:
            win_rate = s["wins"] / total
            if win_rate < EDGE_SOURCE_KILL_THRESHOLD:
                if source not in self._killed_sources:
                    self._killed_sources.add(source)
                    logger.warning(
                        "EDGE SOURCE KILLED: %s — win rate %.1f%% (%d/%d) < %.0f%% threshold",
                        source, win_rate * 100, s["wins"], total,
                        EDGE_SOURCE_KILL_THRESHOLD * 100,
                    )
            elif source in self._killed_sources:
                # Rehabilitated — win rate recovered above threshold
                self._killed_sources.discard(source)
                logger.info(
                    "EDGE SOURCE REHABILITATED: %s — win rate %.1f%% (%d/%d)",
                    source, win_rate * 100, s["wins"], total,
                )

        self._save()

    def is_source_killed(self, source: str) -> bool:
        """Check if an edge source has been killed for poor performance."""
        return source in self._killed_sources

    def get_source_stats(self, source: Optional[str] = None) -> dict:
        """Get stats for one source or all sources."""
        if source:
            s = self._stats.get(source, {"wins": 0, "losses": 0})
            total = s["wins"] + s["losses"]
            return {
                "source": source,
                "wins": s["wins"],
                "losses": s["losses"],
                "total": total,
                "win_rate": round(s["wins"] / total, 3) if total > 0 else 0.0,
                "killed": source in self._killed_sources,
            }
        # All sources
        result = {}
        for src, s in self._stats.items():
            total = s["wins"] + s["losses"]
            result[src] = {
                "wins": s["wins"],
                "losses": s["losses"],
                "total": total,
                "win_rate": round(s["wins"] / total, 3) if total > 0 else 0.0,
                "killed": src in self._killed_sources,
            }
        return result

    @property
    def killed_sources(self) -> set[str]:
        return set(self._killed_sources)
