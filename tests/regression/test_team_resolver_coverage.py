"""Regression: Polymarket'ten bilinen basket lig slug'ları resolver'da çözülür.

SPEC-AUDIT-001 Task 4: WNBA resolver fix sadece WNBA'ya uygulandı — diğer ligler
(NBA, NCAAB, Euroleague) için aynı tip eksiklik riski vardı. Yeni takımlar
(WNBA Toronto Tempo 2026, NBA expansion söylentileri, vs.) için bu test her
sezon güncellenmeli.

Slug listesi: 2026-06-02 tarihinde gamma_api.polymarket.com/events?tag_slug=X
sorgusundan çekildi (game-pattern slug). Sezon dışı ligler için (NCAAB Haziran)
liste boş — test skip.
"""
from __future__ import annotations

import pytest

from src.domain.matching.basketball_team_resolver import resolve_team_pair

# 2026-06-02 itibariyle aktif Polymarket basket lig slug'ları (gamma API).
# Game-pattern: <lig>-<team1>-<team2>-YYYY-MM-DD
_KNOWN_NBA_SLUGS = [
    # NBA finals 2026 — NYK vs SAS (Knicks-Spurs)
    "nba-nyk-sas-2026-06-03",
    "nba-nyk-sas-2026-06-05",
    "nba-sas-nyk-2026-06-08",
]

_KNOWN_WNBA_SLUGS = [
    # 2026 sezonu — mevcut + 2 ekspansiyon (GSV Golden State Valkyries, POR Portland Fire)
    # + 1 yeni 2026 (TOR Toronto Tempo)
    "wnba-atl-ind-2026-06-04",
    "wnba-chi-wsh-2026-06-02",
    "wnba-conn-atl-2026-06-02",
    "wnba-conn-chi-2026-06-05",
    "wnba-dal-la-2026-06-05",
    "wnba-gsv-las-2026-06-06",
    "wnba-gsv-min-2026-06-04",
    "wnba-ind-nyl-2026-06-06",
    "wnba-las-la-2026-06-02",
    "wnba-phx-por-2026-06-05",
    "wnba-phx-sea-2026-06-03",
    "wnba-por-gsv-2026-06-02",
    "wnba-sea-min-2026-06-06",
    "wnba-tor-nyl-2026-06-03",  # Toronto Tempo (2026 yeni ekspansiyon)
    "wnba-wsh-atl-2026-06-06",
]

# NCAAB ve Euroleague: 2026-06-02 itibariyle sezon dışı (gamma 0 maç)
# Sezon başlayınca buraya gerçek slug'lar eklenmeli + test reaktive.
_KNOWN_NCAAB_SLUGS: list[str] = []
_KNOWN_EUROLEAGUE_SLUGS: list[str] = []


@pytest.mark.parametrize("slug", _KNOWN_NBA_SLUGS)
def test_nba_known_slugs_resolve(slug: str) -> None:
    r = resolve_team_pair(slug, league="nba")
    assert r.ok, (
        f"NBA resolve fail: {slug} (home={r.home}, away={r.away}, "
        f"fail_reason={r.fail_reason}). "
        "Çözüm: _NBA_TEAMS dict'ine eksik takım kısaltmasını ekle."
    )


@pytest.mark.parametrize("slug", _KNOWN_WNBA_SLUGS)
def test_wnba_known_slugs_resolve(slug: str) -> None:
    r = resolve_team_pair(slug, league="wnba")
    assert r.ok, (
        f"WNBA resolve fail: {slug} (home={r.home}, away={r.away}, "
        f"fail_reason={r.fail_reason}). "
        "Çözüm: _WNBA_TEAMS dict'ine eksik takım kısaltmasını ekle "
        "(yeni ekspansiyon takımı olabilir)."
    )


@pytest.mark.skipif(not _KNOWN_NCAAB_SLUGS, reason="NCAAB sezon dışı, gamma 0 maç")
@pytest.mark.parametrize("slug", _KNOWN_NCAAB_SLUGS or [""])
def test_ncaab_known_slugs_resolve(slug: str) -> None:
    r = resolve_team_pair(slug, league="ncaab")
    assert r.ok, f"NCAAB resolve fail: {slug}"


@pytest.mark.skipif(not _KNOWN_EUROLEAGUE_SLUGS, reason="Euroleague sezon dışı")
@pytest.mark.parametrize("slug", _KNOWN_EUROLEAGUE_SLUGS or [""])
def test_euroleague_known_slugs_resolve(slug: str) -> None:
    r = resolve_team_pair(slug, league="euroleague")
    assert r.ok, f"Euroleague resolve fail: {slug}"
