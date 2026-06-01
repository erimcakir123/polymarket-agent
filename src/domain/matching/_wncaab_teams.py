"""NCAA Division I Women's Basketball — full team lookup (auto-generated).

~351 D1 women's teams across all conferences (2024-25 season).
Slug pattern: lowercase team name variants -> ESPN abbreviation.
Multiple key variants per team (full name, nickname, common abbrevs).

Saf domain — I/O yok, sabit lookup tablosu. ARCH_GUARD §3 nedeniyle iki
parçaya bölündü (P1 = ACC...Big West, P2 = Colonial...MVC).
"""
from __future__ import annotations

from src.domain.matching._wncaab_teams_p1 import WNCAAB_TEAMS_P1
from src.domain.matching._wncaab_teams_p2 import WNCAAB_TEAMS_P2

WNCAAB_TEAMS: dict[str, str] = {**WNCAAB_TEAMS_P1, **WNCAAB_TEAMS_P2}
