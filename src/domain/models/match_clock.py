"""Sport-agnostic match clock — pozisyonun maçta nerede olduğunu özetler.

Domain modeli: I/O yok, saf veri.
"""
from __future__ import annotations

from dataclasses import dataclass


@dataclass
class MatchClock:
    """Sport-agnostic match clock.

    Tüm alanlar optional — veri yoksa None, elapsed_pct her zaman var.
    """
    # Wall-clock fallback — her zaman hesaplanır
    elapsed_pct: float  # 0.0=başlangıç, 1.0=bitiş, >1.0 OT/extra innings mümkün

    # Period bazlı sporlar (NBA, NFL, NHL, Rugby, AFL, Handball)
    period_number: int | None = None       # 1-4 normal, 5+=OT
    clock_seconds: int | None = None       # periyotta kalan saniye (countdown)
    regulation_periods: int | None = None  # normal sürede kaç periyot

    # Dakika bazlı sporlar (Soccer, Rugby, AFL, Handball)
    match_minute: int | None = None        # 0-90+ (countup)

    # İnning bazlı sporlar (MLB)
    inning: int | None = None              # 1-9+
    inning_half: str | None = None         # "top" | "bottom"

    # Set bazlı sporlar (Tennis)
    sets_won_us: int | None = None         # bizim kazandığımız set
    sets_won_them: int | None = None       # rakibin kazandığı set
    current_set: int | None = None         # kaçıncı set oynandı (1-5)
    games_us: int | None = None            # bu setteki game skorumuz
    games_them: int | None = None          # bu setteki rakip game skoru

    # Durum flag'leri
    is_overtime: bool = False
    is_finished: bool = False
    is_pregame: bool = False


def build_match_clock(
    espn_score: "ESPNMatchScore | None",  # duck-typed: domain infrastructure import etmez
    match_start_iso: str | None,
    sport_tag: str,
    sport_config: dict,
) -> MatchClock:
    """ESPNMatchScore + config'den MatchClock üretir.

    espn_score None ise sadece elapsed_pct ile döner.
    sport_config: {"espn_sport": str, "match_duration_hours": float}
    """
    elapsed_pct = _calc_elapsed_pct(match_start_iso, sport_config)

    if espn_score is None:
        return MatchClock(elapsed_pct=elapsed_pct)

    is_finished = bool(getattr(espn_score, "is_completed", False))
    is_live = bool(getattr(espn_score, "is_live", False))
    is_pregame = not is_live and not is_finished

    espn_sport = sport_config.get("espn_sport", "")

    if espn_sport == "basketball":
        pn = getattr(espn_score, "period_number", None)
        return MatchClock(
            elapsed_pct=elapsed_pct,
            period_number=pn,
            clock_seconds=getattr(espn_score, "clock_seconds", None),
            regulation_periods=4,
            is_overtime=bool(pn and pn > 4),
            is_finished=is_finished,
            is_pregame=is_pregame,
        )

    if espn_sport == "football":
        pn = getattr(espn_score, "period_number", None)
        return MatchClock(
            elapsed_pct=elapsed_pct,
            period_number=pn,
            clock_seconds=getattr(espn_score, "clock_seconds", None),
            regulation_periods=4,
            is_overtime=bool(pn and pn > 4),
            is_finished=is_finished,
            is_pregame=is_pregame,
        )

    if espn_sport == "hockey":
        pn = getattr(espn_score, "period_number", None)
        return MatchClock(
            elapsed_pct=elapsed_pct,
            period_number=pn,
            clock_seconds=getattr(espn_score, "clock_seconds", None),
            regulation_periods=3,
            is_overtime=bool(pn and pn > 3),
            is_finished=is_finished,
            is_pregame=is_pregame,
        )

    if espn_sport == "soccer":
        m = getattr(espn_score, "minute", None)
        return MatchClock(
            elapsed_pct=elapsed_pct,
            match_minute=m,
            regulation_periods=2,
            is_overtime=bool(m and m > 90),
            is_finished=is_finished,
            is_pregame=is_pregame,
        )

    if espn_sport == "baseball":
        inn = getattr(espn_score, "inning", None)
        return MatchClock(
            elapsed_pct=elapsed_pct,
            inning=inn,
            inning_half=getattr(espn_score, "inning_half", None),
            regulation_periods=9,
            is_overtime=bool(inn and inn > 9),
            is_finished=is_finished,
            is_pregame=is_pregame,
        )

    if espn_sport == "tennis":
        return MatchClock(
            elapsed_pct=elapsed_pct,
            sets_won_us=getattr(espn_score, "sets_won_home", None),
            sets_won_them=getattr(espn_score, "sets_won_away", None),
            current_set=getattr(espn_score, "current_set", None),
            games_us=getattr(espn_score, "games_home", None),
            games_them=getattr(espn_score, "games_away", None),
            is_finished=is_finished,
            is_pregame=is_pregame,
        )

    if espn_sport in ("rugby", "aussierules", "handball"):
        pn = getattr(espn_score, "period_number", None)
        return MatchClock(
            elapsed_pct=elapsed_pct,
            match_minute=getattr(espn_score, "minute", None),
            period_number=pn,
            regulation_periods=2,
            is_finished=is_finished,
            is_pregame=is_pregame,
        )

    # Fallback — yalnızca elapsed_pct
    return MatchClock(elapsed_pct=elapsed_pct)


def _calc_elapsed_pct(match_start_iso: str | None, sport_config: dict) -> float:
    """Wall-clock fallback — her zaman hesaplanır."""
    if not match_start_iso:
        return 0.0
    from datetime import datetime, timezone
    try:
        start = datetime.fromisoformat(match_start_iso.replace("Z", "+00:00"))
        now = datetime.now(timezone.utc)
        duration_hours = sport_config.get("match_duration_hours", 2.0)
        elapsed = (now - start).total_seconds() / 3600
        return min(elapsed / duration_hours, 2.0)
    except Exception:
        return 0.0
