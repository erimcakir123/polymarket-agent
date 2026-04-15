"""Polymarket market question'ından takım adlarını çıkarır — pure.

Desteklenen formlar:
  - 'Team A vs Team B'
  - 'Will Team A beat Team B?'
  - 'Who will win: Team A or Team B?'
  - 'Winner of Team A or Team B'
  - 'Will Team A to beat Team B?'
  - 'Will Team A win?' (single-team, Team B None)
"""
from __future__ import annotations

import re

_PREFIXES: tuple[str, ...] = (
    "ATP:", "WTA:", "MLB:", "NBA:", "NHL:", "NFL:", "MMA:", "UFC:", "Boxing:",
    "Cricket:", "Rugby:", "Formula 1:", "F1:", "Golf:", "PGA:", "LPGA:",
    "KBO:", "NPB:", "CFL:", "AFL:", "NRL:",
    "Serie A:", "La Liga:", "EPL:", "Bundesliga:", "Ligue 1:",
    "Premier League:", "Champions League:", "Europa League:",
    "Will",
)


def _strip_prefix(q: str) -> str:
    for pfx in _PREFIXES:
        if q.startswith(pfx):
            return q[len(pfx):].strip()
        if q.lower().startswith(pfx.lower()):
            return q[len(pfx):].strip()
    return q


def extract_teams(question: str) -> tuple[str | None, str | None]:
    """Question'dan (team_a, team_b) veya (team_a, None) çıkar."""
    if not question:
        return None, None
    q = _strip_prefix(question.strip())

    # 1. 'vs' split (en yaygın)
    for sep in (" vs. ", " vs ", " versus "):
        low = q.lower()
        if sep in low:
            idx = low.index(sep)
            a = q[:idx].strip()
            b = q[idx + len(sep):].strip()
            # Turnuva/şehir prefix (ör. "Porsche Tennis Grand Prix: Eva Lys") —
            # team_a'da ":" varsa son ":"'den sonrasını al.
            if ":" in a:
                a = a.rsplit(":", 1)[-1].strip()
            # Parantez / dash ile biten kısımları temizle
            for ch in ("(", " -"):
                if ch in a:
                    a = a[:a.index(ch)].strip()
                if ch in b:
                    b = b[:b.index(ch)].strip()
            if a.lower().startswith("will "):
                a = a[5:].strip()
            # Bitişteki '?'
            b = b.rstrip("?").strip()
            return a, b

    # 2. 'Who will win: X or Y?' / 'Winner of X or Y'
    m = re.search(
        r'(?:who\s+will\s+win[:\s]+|winner\s+of\s+)(.+?)\s+or\s+(.+?)[\s?]*$',
        q, re.IGNORECASE,
    )
    if m:
        return m.group(1).strip().rstrip(","), m.group(2).strip().rstrip("?")

    # 3. 'X to beat Y' / 'Will X to beat Y'
    m = re.search(
        r'(?:will\s+)?(?:the\s+)?(.+?)\s+to\s+(?:beat|defeat)\s+(?:the\s+)?(.+?)[\s?]*$',
        q, re.IGNORECASE,
    )
    if m:
        return m.group(1).strip(), m.group(2).rstrip("?").strip()

    # 4. 'Will X beat/defeat/win against/win over Y'
    m = re.search(
        r'(?:will\s+)?(?:the\s+)?(.+?)\s+(?:beat|defeat|win against|win over)\s+(?:the\s+)?(.+?)[\s?]*$',
        q, re.IGNORECASE,
    )
    if m:
        return m.group(1).strip(), m.group(2).rstrip("?").strip()

    # 5. 'Will X win' (single-team)
    m = re.search(r'(?:will\s+)?(?:the\s+)?(.+?)\s+win\b', q, re.IGNORECASE)
    if m:
        team = m.group(1).strip()
        if len(team) >= 3:
            return team, None

    return None, None
