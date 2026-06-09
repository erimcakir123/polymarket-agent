"""Sackmann maçlarından turnuva→zemin haritası (saf domain, I/O yok)."""
from __future__ import annotations

import re
from collections import Counter, defaultdict
from collections.abc import Iterable

from src.domain.pricing.tennis.match_record import MatchRecord

_VALID_SURFACES = {"Hard", "Clay", "Grass", "Carpet"}
_LEVEL_TOKEN = re.compile(r"^[mw]\d+$")          # ITF seviye: m15, m25, w75...
_DROP_TOKENS = {"ch", "125", "250", "500", "1000", "2", "3", "4"}  # round/seviye etiketleri


def normalize_name(name: str) -> str:
    """lowercase + kesme işaretleri sil, diğer noktalama → boşluk + sıkıştır.

    'Queen's Club' → 'queens club'.
    Kesme işareti (', ‘, ’) önce silindi, sonra kalan noktalama boşluğa dönüşür.
    """
    s = (name or "").lower()
    s = re.sub(r"['‘’]", "", s)          # kesme işaretleri → yok
    s = re.sub(r"[^a-z0-9 ]", " ", s)              # kalan noktalama → boşluk
    return " ".join(s.split())


def core_name(name: str) -> str:
    """Normalize + seviye/round etiketlerini (m25, ch, 125...) ayıkla → çekirdek şehir.

    'M25 Cattolica' → 'cattolica'; 'Ilkley CH' → 'ilkley'.
    """
    toks = [t for t in normalize_name(name).split()
            if not _LEVEL_TOKEN.fullmatch(t) and t not in _DROP_TOKENS]
    return " ".join(toks).strip()


def build_surface_map(matches: Iterable[MatchRecord]) -> dict[str, str]:
    """{core_city: surface}. Etiketler ayıklanır; bir şehir TEK zeminde görülürse
    eklenir; birden çok zemin (örn. Nottingham grass+hard) BELİRSİZ → dışlanır
    (caller skip+uyar). Geçersiz/Unknown surface veya boş isim atlanır."""
    counts: dict[str, Counter] = defaultdict(Counter)
    for m in matches:
        if m.surface not in _VALID_SURFACES:
            continue
        c = core_name(m.tourney_name or "")
        if not c:
            continue
        counts[c][m.surface] += 1
    # Sadece tek-zeminli (kesin) çekirdekler
    return {c: next(iter(cnt)) for c, cnt in counts.items() if len(cnt) == 1}
