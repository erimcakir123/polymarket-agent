"""Polymarket tennis slug → tier + surface + format. Pure, no I/O."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Literal


@dataclass(frozen=True)
class TournamentInfo:
    tier: Literal["grand_slam", "masters_1000", "atp_500", "atp_250", "wta_500", "wta_250"]
    surface: Literal["clay", "hard", "grass"]
    format: Literal["BO3", "BO5"]


def resolve_tournament(
    slug: str,
    tournaments: dict[str, dict[str, str]],
    excluded_tiers: list[str],
    question: str = "",
) -> TournamentInfo | None:
    """Polymarket slug + question → TournamentInfo. None = not eligible.

    Slug typically lacks tournament name on Polymarket (format
    'atp-{p1}-{p2}-{date}'); fall back to question text which
    H2H markets carry as 'Tournament Name: Player1 vs Player2'.
    """
    if not slug:
        return None
    s = slug.lower()
    parts = s.split("-")
    if len(parts) < 3:
        return None
    if parts[0] not in ("atp", "wta"):
        return None
    is_wta = parts[0] == "wta"

    excluded = {t.lower() for t in excluded_tiers}
    for excl in excluded:
        if excl in s:
            return None

    # Combined search corpus: slug + question (lowercased). Polymarket H2H
    # slugs are 'atp-{p1}-{p2}-{date}' and never carry tournament name; only
    # the question text has it ("Madrid Open: Player1 vs Player2").
    # Normalize spaces to hyphens so question text "Madrid Open" matches
    # tournament key "madrid-open".
    q = (question or "").lower().replace(" ", "-")
    corpus = f"{s} {q}"

    for tier_name, surface_map in tournaments.items():
        for tournament_key, surface in surface_map.items():
            normalized_key = tournament_key.replace("_", "-")
            if normalized_key in corpus:
                fmt = "BO5" if (tier_name == "grand_slam" and not is_wta) else "BO3"
                return TournamentInfo(
                    tier=tier_name,
                    surface=surface,
                    format=fmt,
                )
    return None
