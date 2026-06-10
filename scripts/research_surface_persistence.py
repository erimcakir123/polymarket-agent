"""PLAN-DATA2: Zemin becerisi kalıcılık testi — geçen yılın çimi bayat mı?

Walk-forward (ileri yürüyüş): 2024+2025 maçları kronolojik işlenir; her 2025 ÇİM
maçı, sonucu öğrenilmeden ÖNCE üç tahminciyle öngörülür, sonra reytingler güncellenir:
  A) GENEL    — sadece genel karne (zemin bilgisi yok sayılır)
  B) ANAHTAR  — çim karnesi güvenilirse (phi<100) o, değilse genel (bugünkü/V2 mantığı)
  C) HARMAN   — çim + genel, ters-varyans ağırlıklı karışım (kullanıcı önerisi)

2025 çim sezonu başında çim karnesi = SAF 2024 çim bilgisi → "erken pencere"
sonuçları doğrudan 'geçen yıl çimi hâlâ geçerli mi?' sorusunu cevaplar.

Salt-okunur; üretim cache'ine dokunmaz (2024 ayrı klasöre indirilir).
Çalıştırma: PYTHONUTF8=1 python -m scripts.research_surface_persistence
"""
from __future__ import annotations

import logging
import math
from dataclasses import dataclass, field
from pathlib import Path

from src.domain.pricing.tennis.glicko import Rating, update_rating, win_probability
from src.domain.pricing.tennis.match_record import MatchRecord
from src.infrastructure.data.sackmann_csv_loader import load_matches_from_path
from src.infrastructure.data.sackmann_refresher import refresh_cache

logger = logging.getLogger(__name__)

_PROD_CACHE = Path("data/sackmann_cache")        # 2025-26 mevcut (salt-okunur)
_RESEARCH_CACHE = Path("data/sackmann_research")  # 2024 buraya iner (üretim dışı)
_RESEARCH_YEAR = 2024
_EVAL_YEAR_PREFIX = "2025"
_EVAL_SURFACE = "Grass"
_MIN_PHI_FOR_EVAL = 150.0   # iki oyuncu da en az bu kadar tanıdıksa maç değerlendirilir
_SWITCH_PHI = 100.0         # ANAHTAR tahmincinin çim-karne güven eşiği (bot ile aynı)
_EARLY_WINDOW_DAYS = 14     # "erken pencere" = 2025 çim sezonunun ilk 14 günü
_PROB_FLOOR = 1e-9          # log-loss'ta log(0) koruması


def _blend(rs: Rating, ro: Rating) -> Rating:
    """Ters-varyans harman: belirsizliği az olan karne daha çok konuşur."""
    ws, wo = 1.0 / (rs.phi ** 2), 1.0 / (ro.phi ** 2)
    return Rating(mu=(ws * rs.mu + wo * ro.mu) / (ws + wo),
                  phi=math.sqrt(1.0 / (ws + wo)), sigma=ro.sigma)


@dataclass
class _Tally:
    n: int = 0
    correct: int = 0
    logloss_sum: float = 0.0

    def add(self, p_winner: float) -> None:
        self.n += 1
        self.correct += 1 if p_winner > 0.5 else 0
        self.logloss_sum += -math.log(max(p_winner, _PROB_FLOOR))

    @property
    def accuracy(self) -> float:
        return self.correct / self.n if self.n else 0.0

    @property
    def logloss(self) -> float:
        return self.logloss_sum / self.n if self.n else 0.0


@dataclass
class WalkForwardResult:
    overall: _Tally = field(default_factory=_Tally)
    switch: _Tally = field(default_factory=_Tally)
    blend: _Tally = field(default_factory=_Tally)
    early_overall: _Tally = field(default_factory=_Tally)
    early_switch: _Tally = field(default_factory=_Tally)
    early_blend: _Tally = field(default_factory=_Tally)
    first_eval_date: str = ""


def walk_forward_grass_eval(
    matches: list[MatchRecord],
    eval_keys: set[tuple[str, str, str]] | None = None,
) -> WalkForwardResult:
    """Kronolojik yürüyüş: 2025 çim maçlarında 3 tahminciyi yarıştır (saf fonksiyon).

    eval_keys verilirse yalnız o (tarih, kazanan, kaybeden) maçları DEĞERLENDİRİLİR
    (örn. sadece tur-seviyesi — botun gerçekten oynadığı evren); güncelleme her
    maçla yine yapılır.
    """
    overall: dict[str, Rating] = {}
    grass: dict[str, Rating] = {}
    res = WalkForwardResult()
    for m in sorted(matches, key=lambda x: x.tourney_date):
        is_eval = (
            m.surface == _EVAL_SURFACE
            and m.tourney_date.startswith(_EVAL_YEAR_PREFIX)
            and (eval_keys is None
                 or (m.tourney_date, m.winner_name, m.loser_name) in eval_keys)
        )
        if is_eval:
            ow, ol = overall.get(m.winner_name), overall.get(m.loser_name)
            if ow is not None and ol is not None and ow.phi < _MIN_PHI_FOR_EVAL and ol.phi < _MIN_PHI_FOR_EVAL:
                if not res.first_eval_date:
                    res.first_eval_date = m.tourney_date
                early = _days_between(res.first_eval_date, m.tourney_date) < _EARLY_WINDOW_DAYS
                gw, gl = grass.get(m.winner_name), grass.get(m.loser_name)
                # A) GENEL
                p = win_probability(ow, ol)
                res.overall.add(p)
                if early:
                    res.early_overall.add(p)
                # B) ANAHTAR: çim phi<100 ise çim karnesi, yoksa genel (oyuncu başına)
                sw = gw if (gw is not None and gw.phi < _SWITCH_PHI) else ow
                sl = gl if (gl is not None and gl.phi < _SWITCH_PHI) else ol
                p = win_probability(sw, sl)
                res.switch.add(p)
                if early:
                    res.early_switch.add(p)
                # C) HARMAN: çim karnesi varsa karışım, yoksa genel
                bw = _blend(gw, ow) if gw is not None else ow
                bl = _blend(gl, ol) if gl is not None else ol
                p = win_probability(bw, bl)
                res.blend.add(p)
                if early:
                    res.early_blend.add(p)
        # Tahmin SONRASI güncelle (gelecek bilgisi sızmaz)
        w_o = overall.get(m.winner_name, Rating())
        l_o = overall.get(m.loser_name, Rating())
        overall[m.winner_name] = update_rating(w_o, [l_o], [1.0])
        overall[m.loser_name] = update_rating(l_o, [w_o], [0.0])
        if m.surface == _EVAL_SURFACE:
            w_g = grass.get(m.winner_name, Rating())
            l_g = grass.get(m.loser_name, Rating())
            grass[m.winner_name] = update_rating(w_g, [l_g], [1.0])
            grass[m.loser_name] = update_rating(l_g, [w_g], [0.0])
    return res


def _days_between(d1_yyyymmdd: str, d2_yyyymmdd: str) -> int:
    from datetime import date
    try:
        a = date(int(d1_yyyymmdd[:4]), int(d1_yyyymmdd[4:6]), int(d1_yyyymmdd[6:8]))
        b = date(int(d2_yyyymmdd[:4]), int(d2_yyyymmdd[4:6]), int(d2_yyyymmdd[6:8]))
        return (b - a).days
    except (ValueError, IndexError):
        return 10**6  # bozuk tarih → erken pencere dışı say


# ── I/O (script seviyesi) ──

def _load_all() -> tuple[list[MatchRecord], set[tuple[str, str, str]]]:
    """Tüm maçlar + tur-seviyesi anahtar seti (atp_matches_/wta_matches_ ana dosyaları).

    Bot yalnız tur seviyesini oynar (ITF/Challenger yetki dışı) — değerlendirme
    botun gerçek evreninde yapılmalı; güncellemeler yine tüm maçlarla.
    """
    if not any(_RESEARCH_CACHE.glob("*2024*.csv")):
        print(f"2024 CSV'leri indiriliyor → {_RESEARCH_CACHE} (üretim cache'ine dokunulmaz)...")
        counts = refresh_cache(_RESEARCH_CACHE, years=[_RESEARCH_YEAR])
        print(f"  indirilen kategori sayıları: {counts}")
    matches: list[MatchRecord] = []
    tour_keys: set[tuple[str, str, str]] = set()
    for d in (_RESEARCH_CACHE, _PROD_CACHE):
        for csv in sorted(d.glob("*.csv")):
            try:
                batch = load_matches_from_path(csv)
            except OSError as exc:
                logger.warning("CSV okunamadı: %s (%s)", csv, exc)
                continue
            matches.extend(batch)
            # Ana dosyalar: atp_matches_YYYY / wta_matches_YYYY (qual_chall/futures DEĞİL)
            name = csv.name
            if ("matches" in name and "qual" not in name and "futures" not in name):
                tour_keys.update((m.tourney_date, m.winner_name, m.loser_name) for m in batch)
    return matches, tour_keys


def _row(label: str, t: _Tally) -> str:
    return f"  {label:<28} n={t.n:<5} doğruluk %{t.accuracy*100:5.1f}   log-loss {t.logloss:.4f}"


def main() -> None:
    logging.basicConfig(level=logging.WARNING)
    matches, tour_keys = _load_all()
    n2024 = sum(1 for m in matches if m.tourney_date.startswith("2024"))
    print(f"Toplam maç: {len(matches)} (2024: {n2024}); 2025 çim maçları değerlendiriliyor...")
    for label, keys in (("TÜM SEVİYELER", None), ("SADECE TUR SEVİYESİ (botun oynadığı evren)", tour_keys)):
        res = walk_forward_grass_eval(matches, eval_keys=keys)
        print("=" * 74)
        print(f"ZEMİN KALICILIK TESTİ — 2025 çim, {label} — tahmin-sonra-öğren (sızıntısız)")
        print(f"İlk değerlendirme tarihi: {res.first_eval_date} (erken pencere = ilk {_EARLY_WINDOW_DAYS} gün)")
        print("-" * 74)
        print("ERKEN PENCERE (çim karnesi ≈ saf geçen-yıl bilgisi → 'bayat mı?' cevabı):")
        print(_row("A) Genel karne", res.early_overall))
        print(_row("B) Anahtar (bugünkü mantık)", res.early_switch))
        print(_row("C) Harman (öneri)", res.early_blend))
        print("-" * 74)
        print("TÜM 2025 ÇİM SEZONU:")
        print(_row("A) Genel karne", res.overall))
        print(_row("B) Anahtar (bugünkü mantık)", res.switch))
        print(_row("C) Harman (öneri)", res.blend))
    print("=" * 74)
    print("Okuma: log-loss DÜŞÜK = iyi. B/C, A'dan iyiyse geçen yıl çimi BAYAT DEĞİL.")


if __name__ == "__main__":
    main()
