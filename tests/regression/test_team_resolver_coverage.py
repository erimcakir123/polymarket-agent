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

# SPEC-EUROBASKET-001 (2026-06-02): Avrupa basket lig slug regression.
# ACB: gamma API'den DOĞRULANMIŞ (bkligend-rea-la-2026-06-02 vs).
# BSL/Lega/VTB: slug prefix tahmin, sezon devam ederse runtime'da doğrulanır.
_KNOWN_ACB_SLUGS = [
    # /teams?league=bkligend endpoint'ten 18 takım TAMAMI doğrulanmış (2026-06-03).
    "bkligend-rea-la-2026-06-02",        # Real Madrid vs La Laguna Tenerife
    "bkligend-val-bil-2026-06-03",       # Valencia vs Bilbao Basket
    "bkligend-bas2-val-2026-05-13",      # Basket Zaragoza vs Valencia
    "bkligend-cb2-bar-2026-06-02",       # CB Murcia vs FC Barcelona
    "bkligend-sas-jov-2026-06-03",       # Baskonia (sas) vs Joventut
    "bkligend-bas-rea-2026-04-01",       # Basquet Girona (bas, NOT Baskonia)
    "bkligend-uni-man-2026-04-01",       # Unicaja (uni) vs Manresa
    "bkligend-bas3-bar-2026-04-01",      # Andorra (bas3) vs Barcelona
    "bkligend-cb-gra-2026-04-01",        # CB Breogán Lugo (cb) vs Granada
    "bkligend-gra2-bur-2026-04-01",      # Gran Canaria (gra2) vs Burgos
    "bkligend-for-jov-2026-04-01",       # Força Lleida (for) vs Joventut
]

# BSL: gamma API tag_id=104347 DOĞRULANMIŞ slug seti.
# Tüm 16 takım kapsanır (mer/mer2 ayrımı dahil).
_KNOWN_BSL_SLUGS = [
    "bkbsl-bes-bah-2026-06-02",        # Besiktas vs Bahcesehir Koleji
    "bkbsl-fen-ana-2026-06-03",        # Fenerbahce vs Anadolu Efes
    "bkbsl-ana-fen-2026-06-05",        # Anadolu Efes vs Fenerbahce
    "bkbsl-bah-bes-2026-06-06",        # Bahcesehir vs Besiktas
    "bkbsl-gal-bur-2026-04-04",        # Galatasaray vs Bursaspor
    "bkbsl-tur-ese-2026-04-04",        # Turk Telekom vs Esenler Erokspor
    "bkbsl-mer-buy-2026-04-04",        # Mersin BSB vs Buyukcekmece
    "bkbsl-pet-ana-2026-04-04",        # Petkim Spor vs Anadolu Efes
    "bkbsl-tof-tra-2026-04-04",        # Tofas vs Trabzonspor
    "bkbsl-bah-man-2026-04-04",        # Bahcesehir vs Manisa BB → BAH/MNS
    "bkbsl-bes-kar-2026-04-04",        # Besiktas vs Karsiyaka
    "bkbsl-fen-mer2-2026-04-04",       # Fenerbahce vs Merkezefendi → FEN/MER2
    "bkbsl-mer2-gal-2026-04-11",       # Merkezefendi vs Galatasaray (mer2 ayrımı)
]

# Lega Serie A: gamma series_id=10877 DOĞRULANMIŞ (bkseriea-* prefix).
# 100+ slug analiz edildi; pal/pal2-5 ayrımı + aqu/oli/vir/rey + tra/der
# token'larını kapsayan 9 slug seçildi — 16 takımın tümü dolaylı kapsanır.
_KNOWN_LEGA_SLUGS = [
    "bkseriea-oli-pal2-2026-06-03",    # Olimpia Milano vs Pallacanestro Brescia
    "bkseriea-rey-vir-2026-06-06",     # Reyer Venezia vs Virtus Bologna
    "bkseriea-pal5-pal-2026-01-11",    # Pallacanestro Trieste vs Pallacanestro Cantu
    "bkseriea-uni-pal3-2026-01-11",    # Universo Treviso vs Pallacanestro Varese
    "bkseriea-pal4-din-2026-01-10",    # Pallacanestro Reggiana vs Dinamo Sassari
    "bkseriea-ami-van-2026-01-11",     # Amici Udinese vs Vanoli Cremona
    "bkseriea-nap-oli-2026-01-12",     # Napoli Basket vs Olimpia Milano
    "bkseriea-tra-aqu-2026-01-10",     # Trapani vs Aquila Trento
    "bkseriea-der-oli-2026-01-17",     # Derthona vs Olimpia Milano
]

# /teams?league=bkvtb endpoint'ten 11 takım TAMAMI doğrulanmış (2026-06-03).
# Polymarket konvansiyon: 3-harf alias ("csk" NOT "cska", "par" NOT "parma").
# Minsk listede YOK (eski tahmini "min": "MNSK" kaldırıldı).
_KNOWN_VTB_SLUGS = [
    "bkvtb-zen-lok-2026-06-03",        # BC Zenit vs Lokomotiv Kuban (finals)
    "bkvtb-lok-zen-2026-06-07",        # Lokomotiv Kuban vs BC Zenit (rematch)
    "bkvtb-uni-csk-2026-06-08",        # UNICS Kazan vs CSKA Moscow
    "bkvtb-par-mba-2026-04-01",        # Parma Perm (par, NOT parma) vs MBA Moscow
    "bkvtb-avt-niz-2026-04-01",        # Avtodor vs Nizhny Novgorod
    "bkvtb-sam-eni-2026-04-01",        # Samara vs Enisey
    "bkvtb-ura-csk-2026-04-01",        # Uralmash vs CSKA
]


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


@pytest.mark.parametrize("slug", _KNOWN_ACB_SLUGS)
def test_liga_acb_known_slugs_resolve(slug: str) -> None:
    """SPEC-EUROBASKET-001: Liga Endesa slug → ACB takım kısaltması."""
    r = resolve_team_pair(slug, league="liga_acb")
    assert r.ok, (
        f"ACB resolve fail: {slug} (home={r.home}, away={r.away}, "
        f"fail_reason={r.fail_reason}). "
        "Çözüm: _ACB_TEAMS dict'ine eksik takım kısaltmasını ekle."
    )


@pytest.mark.parametrize("slug", _KNOWN_BSL_SLUGS)
def test_turkey_bsl_known_slugs_resolve(slug: str) -> None:
    """SPEC-EUROBASKET-001: BSL gamma slug → BSL takım kısaltması."""
    r = resolve_team_pair(slug, league="turkey_bsl")
    assert r.ok, (
        f"BSL resolve fail: {slug} (home={r.home}, away={r.away}, "
        f"fail_reason={r.fail_reason}). "
        "Çözüm: _BSL_TEAMS dict'ine eksik takım kısaltmasını ekle."
    )


@pytest.mark.parametrize("slug", _KNOWN_LEGA_SLUGS)
def test_italy_lega_known_slugs_resolve(slug: str) -> None:
    """SPEC-EUROBASKET-001: Lega Serie A slug → Lega takım kısaltması."""
    r = resolve_team_pair(slug, league="italy_lega")
    assert r.ok, (
        f"Lega resolve fail: {slug} (home={r.home}, away={r.away}, "
        f"fail_reason={r.fail_reason}). "
        "Çözüm: _LEGA_TEAMS dict'ine eksik takım kısaltmasını ekle "
        "(Pallacanestro kümesi pal/pal2-5 ayrımına dikkat)."
    )


@pytest.mark.parametrize("slug", _KNOWN_VTB_SLUGS)
def test_vtb_known_slugs_resolve(slug: str) -> None:
    """SPEC-EUROBASKET-001: VTB United League slug → VTB takım kısaltması."""
    r = resolve_team_pair(slug, league="vtb")
    assert r.ok, (
        f"VTB resolve fail: {slug} (home={r.home}, away={r.away}, "
        f"fail_reason={r.fail_reason}). "
        "Çözüm: _VTB_TEAMS dict'ine eksik takım kısaltmasını ekle "
        "(Polymarket 'csk' kullanıyor, 'cska' DEĞİL)."
    )
