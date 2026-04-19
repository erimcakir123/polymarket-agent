# SPEC-010: Score Matching Fix + Baseball Symmetry + Partial Rollback

> **Durum**: IMPLEMENTED
> **Tarih**: 2026-04-19
> **Katman**: orchestration (score_enricher) + strategy (baseball_score_exit yeni, baseball guard sil) + config
> **Scope**: Phantom matchup bug fix + A-conf symmetry + kontrollu rollback

---

## 1. Kok Neden

### 1a. Score Matching Bug

`src/orchestration/score_enricher.py` kendi basit `_team_match()` fonksiyonunu kullaniyor:
```python
if p in a or a in p: return True  # substring
```

**Sorun**: Projede zaten sophisticated `pair_matcher` modulu var
(`src/domain/matching/pair_matcher.py`) ama score enricher onu **IGNORE ediyor**.

Basit matcher:
- Substring match yaniltici: "Tampa Bay" → "Tampa Bay Rays" AND "Tampa Bay Lightning"
- Alias yok: "NYR" → Rangers bulamaz
- Abbrev yok: "tor" → Toronto bulamaz
- Swap order yok
- Confidence threshold yok

### 1b. A-conf Asimetri

| Branş | Forced Exit | A-conf'ta Aktif |
|---|---|---|
| Tennis | T1/T2 (tennis_score_exit) | ✅ |
| Hockey | K1-K4 (hockey_score_exit) | ✅ |
| **Baseball** | SPEC-008 defensive guard (stop_loss icinde) | ❌ |

Baseball SPEC-008 icin iki kritik sorun:
1. `stop_loss.py` icinde → A-conf pozisyonlar stop_loss'u komple atliyor → guard devre disi
2. **Defensive** (SL ertele) degil, **offensive** (skor kotu, cik) gerekli

### 1c. Parametre Drift

17 Nis 22:09 sonrasi yapilan bazi degisiklikler kayip tarafini buyuttu:
- A-conf edge %6 → %4 (daha marjinal trade)
- Scale-out Tier 1 +%25/%40 → +%35/%25 (daha az erken kilit)
- max_single_bet_usdc: $75 kaldirildi (tavan yok, $67 bet gorduk)

---

## 2. Cozum

### 2a. Score Matching — pair_matcher Wire

`score_enricher.py` basit matcher yerine `pair_matcher` kullanir:

**Silinecek fonksiyonlar:**
- `_team_match(pos_team, api_team) -> bool`
- `_find_espn_match(pos, scores)` 
- `_find_match(pos, scores)`

**Yeni yaklasim:**
```python
from src.domain.matching.pair_matcher import match_pair, match_team
from src.strategy.enrichment.question_parser import extract_teams

def _find_match_via_pair(pos: Position, scores: list) -> object | None:
    """pair_matcher kullanarak ESPN/Odds API scores icinden eslesen event'i bul."""
    team_a, team_b = extract_teams(pos.question)
    if not team_a:
        return None
    
    best_match = None
    best_conf = 0.0
    for ms in scores:
        home = getattr(ms, "home_name", None) or getattr(ms, "home_team", "")
        away = getattr(ms, "away_name", None) or getattr(ms, "away_team", "")
        
        if team_b:
            # Pair matching: HER IKI takim da eslemeli
            is_match, conf = match_pair((team_a, team_b), (home, away))
            if is_match and conf > best_conf:
                best_match = ms
                best_conf = conf
        else:
            # Single team fallback (nadir case — question'da tek takim)
            mh, ch, _ = match_team(team_a, home)
            ma, ca, _ = match_team(team_a, away)
            best_side = max(ch, ca)
            if (mh or ma) and best_side > best_conf:
                best_match = ms
                best_conf = best_side
    
    return best_match if best_conf >= 0.80 else None
```

**Etki**:
- `Tampa Bay vs Pittsburgh` phantom slug + ESPN'de yoksa → **None** doner (safe, yanlis baglanti yok)
- `NYR` abbrev, `Man City` alias gibi varyasyonlar dogru bulunur
- Fuzzy matching (Swiatek vs Şwiatek) calisir
- Hem ESPN hem Odds API icin ayni API

### 2b. Baseball Score Exit — Yeni Dosya

`src/strategy/exit/baseball_score_exit.py` (yeni, ~80 satir):

```python
"""Baseball inning-based score exit (SPEC-010) — pure.

A-conf pozisyonlar icin FORCED exit kurallari. Tennis T1/T2 ve
hockey K1-K4 ile simetrik.

M1: 7. inning+ ve >= 5 run deficit (blowout, dönülemez)
M2: 8. inning+ ve >= 3 run deficit (late big deficit)
M3: 9. inning+ ve >= 1 run deficit (final inning)
"""
from __future__ import annotations

from dataclasses import dataclass

from src.config.sport_rules import get_sport_rule
from src.models.enums import ExitReason


@dataclass
class BaseballExitResult:
    reason: ExitReason
    detail: str


def check(
    score_info: dict,
    current_price: float,
    sport_tag: str = "mlb",
) -> BaseballExitResult | None:
    """Baseball M1/M2/M3 exit kontrolu.
    
    Returns BaseballExitResult → cik; None → tetiklenmedi.
    """
    if not score_info.get("available"):
        return None
    
    # parse_baseball_inning logic (stop_loss.py'den tasinabilir)
    period = score_info.get("period", "")
    inning = _parse_inning(period)
    if inning is None:
        return None
    
    deficit = score_info.get("deficit", 0)
    if deficit <= 0:
        return None  # ondeyiz veya esit
    
    # Config thresholds (sport_rules.py)
    m1_inning = int(get_sport_rule(sport_tag, "score_exit_m1_inning", 7))
    m1_deficit = int(get_sport_rule(sport_tag, "score_exit_m1_deficit", 5))
    m2_inning = int(get_sport_rule(sport_tag, "score_exit_m2_inning", 8))
    m2_deficit = int(get_sport_rule(sport_tag, "score_exit_m2_deficit", 3))
    m3_inning = int(get_sport_rule(sport_tag, "score_exit_m3_inning", 9))
    m3_deficit = int(get_sport_rule(sport_tag, "score_exit_m3_deficit", 1))
    
    # M1: blowout
    if inning >= m1_inning and deficit >= m1_deficit:
        return BaseballExitResult(
            reason=ExitReason.SCORE_EXIT,
            detail=f"M1: inning={inning} deficit={deficit} threshold={m1_deficit}",
        )
    
    # M2: late big deficit
    if inning >= m2_inning and deficit >= m2_deficit:
        return BaseballExitResult(
            reason=ExitReason.SCORE_EXIT,
            detail=f"M2: inning={inning} deficit={deficit} threshold={m2_deficit}",
        )
    
    # M3: final inning, any deficit
    if inning >= m3_inning and deficit >= m3_deficit:
        return BaseballExitResult(
            reason=ExitReason.SCORE_EXIT,
            detail=f"M3: inning={inning} deficit={deficit} threshold={m3_deficit}",
        )
    
    return None


def _parse_inning(period: str) -> int | None:
    """ESPN period stringini inning numarasina cevir (stop_loss.py'den).
    "Top 1st" → 1, "Bot 5th" → 5, "Mid 9th" → 9.
    """
    import re
    if not period:
        return None
    m = re.search(r"(\d+)(?:st|nd|rd|th)", period)
    return int(m.group(1)) if m else None
```

### 2c. Monitor Wire

`src/strategy/exit/monitor.py` — a_conf_hold branch'ine ekle (tennis/hockey'den sonra):

```python
# Mevcut hockey check'ten sonra:
if _normalize(pos.sport_tag) in ("mlb", "kbo", "npb", "baseball") and score_info.get("available"):
    b_result = baseball_score_exit.check(
        score_info=score_info,
        current_price=pos.current_price,
        sport_tag=pos.sport_tag,
    )
    if b_result is not None:
        return MonitorResult(
            exit_signal=ExitSignal(reason=b_result.reason, detail=b_result.detail),
            fav_transition=_fav_transition(pos),
            elapsed_pct=elapsed_pct,
        )
```

### 2d. Baseball Inning Guard Sil

`src/strategy/exit/stop_loss.py`:
- `parse_baseball_inning()` kaldir (baseball_score_exit'e tasindi)
- `is_baseball_alive()` kaldir
- `compute_stop_loss_pct()` icindeki 2.5 numarali baseball block'unu kaldir
- `score_info` parametresini kaldir (default None olarak zaten vardi, ama baska yerde kullanilmiyor)

`src/strategy/exit/monitor.py`:
- `stop_loss.check(pos, score_info)` → `stop_loss.check(pos)` (score_info param kaldir)

`src/config/sport_rules.py`:
- `mlb` icin `comeback_thresholds` kaldir
- `mlb` icin `extra_inning_threshold` kaldir
- `mlb` icin `score_exit_m1_inning: 7, m1_deficit: 5, m2_inning: 8, m2_deficit: 3, m3_inning: 9, m3_deficit: 1` EKLE

`tests/unit/strategy/exit/test_baseball_guard.py` → **SIL** (mekanizma degisti)

### 2e. Config Rollback (Partial)

`config.yaml`:
```yaml
edge:
  min_edge: 0.06
  confidence_multipliers:
    A: 1.00   # eski 0.67 → 1.00 (eşik %4 → %6)
    B: 1.00

risk:
  max_bet_pct: 0.05
  max_single_bet_usdc: 50   # YENI — bet tavani (eski $75 degil, $50)
  confidence_bet_pct:
    A: 0.05
    B: 0.04

scale_out:
  enabled: true
  tiers:
    - threshold: 0.25    # SPEC-008 oncesi
      sell_pct: 0.40
    - threshold: 0.50
      sell_pct: 0.50
```

`src/domain/risk/position_sizer.py` — `max_bet_usdc` param geri ekle:
```python
def confidence_position_size(
    confidence: str,
    bankroll: float,
    confidence_bet_pct: dict[str, float],
    max_bet_pct: float = 0.05,
    max_bet_usdc: float = 50.0,  # YENI
    is_reentry: bool = False,
) -> float:
    bet_pct = confidence_bet_pct.get(confidence, 0.0)
    if bet_pct == 0.0: return 0.0
    if is_reentry: bet_pct *= REENTRY_MULTIPLIER
    size = bankroll * bet_pct
    size = min(size, max_bet_usdc, bankroll * max_bet_pct, bankroll)  # 3-way cap
    return max(0.0, round(size, 2))
```

`src/strategy/entry/gate.py` + `src/orchestration/factory.py`: `max_single_bet_usdc` parametresini geri ekle ve `confidence_position_size`'a gecir.

---

## 3. Etkilenen Dosyalar

### Yeni
| Dosya | Boyut |
|---|---|
| `src/strategy/exit/baseball_score_exit.py` | ~80 satir |
| `tests/unit/strategy/exit/test_baseball_score_exit.py` | ~100 satir |

### Guncelleme
| Dosya | Islem |
|---|---|
| `src/orchestration/score_enricher.py` | `_team_match`, `_find_espn_match`, `_find_match` sil → `pair_matcher` wire |
| `src/strategy/exit/monitor.py` | baseball_score_exit import + a_conf_hold branch'ine ekle; stop_loss.check() score_info param kaldir |
| `src/strategy/exit/stop_loss.py` | `parse_baseball_inning`, `is_baseball_alive`, baseball block sil; score_info param kaldir |
| `src/config/sport_rules.py` | mlb `comeback_thresholds` kaldir, `score_exit_*` thresholds ekle |
| `config.yaml` | edge.confidence_multipliers.A: 0.67→1.00, risk.max_single_bet_usdc: 50 ekle, scale_out tiers original |
| `src/domain/risk/position_sizer.py` | `max_bet_usdc` param geri ekle |
| `src/strategy/entry/gate.py` | `max_single_bet_usdc` field geri ekle, sizing call'da gecir |
| `src/orchestration/factory.py` | `max_single_bet_usdc=cfg.risk.max_single_bet_usdc` gecis |
| `src/config/settings.py` | RiskConfig.max_single_bet_usdc field geri ekle (default 50) |

### Testler
| Dosya | Islem |
|---|---|
| `tests/unit/strategy/exit/test_baseball_score_exit.py` | YENI |
| `tests/unit/strategy/exit/test_baseball_guard.py` | SIL |
| `tests/unit/orchestration/test_score_enricher.py` | Matching testlerini pair_matcher ile yeniden yaz |
| `tests/unit/strategy/exit/test_monitor.py` | Baseball score exit wire testi ekle |
| `tests/unit/strategy/exit/test_stop_loss.py` | Baseball block testlerini kaldir |
| `tests/unit/domain/risk/test_position_sizer.py` | max_bet_usdc cap testlerini geri ekle |

### Silinecek
- `logs/*.bak*` ve `logs/*backup*` zaten silinmisti, tekrar ihtiyac yok

### Dokuman
- `TDD.md` §6.7 stop_loss — baseball guard'i kaldir
- `TDD.md` §6 — baseball score exit ekle (yeni bolum, tennis T1/T2 ve hockey K1-K4 gibi)
- `PRD.md` F-madde — baseball score exit eklendigi belirt
- `CLAUDE.md` — degisiklik yok
- `docs/superpowers/specs/2026-04-18-baseball-inning-guard-design.md` → durum `SUPERSEDED_BY: SPEC-010`

---

## 4. Sinir Durumlari

| Durum | Davranis |
|---|---|
| ESPN'de phantom matchup (Tampa vs Pitt) | pair_matcher confidence < 0.80 → None → score_info.available=False → forced exit tetiklenmez (safe) |
| Alias (NYR vs New York Rangers) | canonicalize + L1 match → dogru eslesme |
| Tennis score_exit icin ESPN ayni matcher | pair_matcher tennis icin de dogru calisir |
| Baseball score_info yok | baseball_score_exit None doner, stop_loss zaten A-conf'ta kapali → pozisyon near_resolve'a gider (eskisi gibi) |
| Baseball M3 9. inning 1 run deficit | exit tetiklenir, price 0.001 yerine muhtemelen 0.10-0.20'de cikariz |
| Mevcut trade'ler (reboot sonrasi 0 pozisyon) | etkilenmez, yeni trade'lerde yeni kod |
| max_single_bet_usdc: 50 + bankroll $2000 | bet = min(100, 50, bankroll × 5%) = $50 → tavan devreye |
| A-conf edge multiplier 1.00 | min_edge 0.06 × 1.00 = 0.06 (%6 eşik) — iyi dönem değeri |
| Eski test dosyasi (test_baseball_guard) | silnir — ilgili fonksiyonlar artik yok |

---

## 5. Test Senaryolari

### score_enricher (unit — integration)
- `test_find_match_via_pair_matcher_exact`: tam isim eşleşmesi
- `test_find_match_via_pair_matcher_alias`: NYR → New York Rangers
- `test_find_match_via_pair_matcher_swapped_order`: home/away ters olsa bile eşleşir
- `test_find_match_phantom_no_match`: Tampa vs Pittsburgh phantom slug → None
- `test_find_match_single_team_fallback`: question'da tek takim var → home/away'den birine eşlesin
- `test_find_match_low_confidence_rejected`: 0.70 confidence < 0.80 threshold → None
- `test_score_change_still_logs_to_archive`: refactor'a ragmen archive log'lari calisir

### baseball_score_exit (unit)
- `test_parse_inning_various_formats`: Top 1st, Bot 5th, Mid 9th
- `test_m1_blowout_7th_5run`: 7. inning, 5 run geride → exit (M1)
- `test_m1_blowout_7th_4run_no_exit`: 7. inning, 4 run geride → None
- `test_m2_late_deficit_8th_3run`: 8. inning, 3 run geride → exit (M2)
- `test_m3_final_inning_1run`: 9. inning, 1 run geride → exit (M3)
- `test_deficit_zero_or_negative_no_exit`: önde veya eşit → None
- `test_score_info_unavailable_no_exit`: score_info.available=False → None
- `test_period_unparseable_no_exit`: "In Progress" gibi → None
- `test_kbo_sport_tag_works`: kbo için de aynı kurallar (config'den)

### monitor integration
- `test_baseball_score_exit_triggers_for_a_conf_mlb`: A-conf MLB + score_info → M1 tetiklenir
- `test_baseball_score_exit_doesnt_fire_for_nba`: NBA → skip (sport_tag check)

### stop_loss (revert)
- `test_stop_loss_no_baseball_block`: MLB pozisyon, score_info verilmis → stop_loss normal calisir (baseball block yok)

### position_sizer (revert)
- `test_max_bet_usdc_cap_applied`: bankroll $10_000 + %5 = $500, cap $50 → $50
- `test_max_bet_usdc_below_cap`: bankroll $500 + %5 = $25 → $25

---

## 6. Tahmini Etki

### 1. Matching fix
- Tennis/hockey score exit **daha guvenilir**: alias'lar, fuzzy, swap destegi
- Phantom matchup'larda **yanlis baglanti yok** (safe)
- Gerçekten eşleşen maçlarda **eksik eşleşme azalır**

### 2. Baseball symmetry
- A-conf MLB pozisyonlari **forced exit korumasi** kazanir
- Ornek retrospektif: mlb-lad-col (A-conf, -$50 wipeout) → eger ESPN maçı bulduysa ve 9. inning'de açık büyükse M3 tetiklerdi → -$10-20 olurdu (tahminen)

### 3. Config rollback
- A-conf edge %4 → %6: daha az ama kaliteli trade
- max_single_bet $50: $67 bet → $50 bet (%25 daha az hasar)
- Scale-out orjinal: +%25'te %40 kilit = iyi dönem davranışı

### Toplam tahmini
17 Nis 22:09 - 19 Nis arasi -$210 net kayıp:
- Matching fix: belki 1-2 kayip orta büyüklükte exit'e donusurdu
- Baseball score exit: 3-4 MLB kayipi $30-40 azalirdi
- Config rollback: bet boyutu azalma + daha kaliteli trade + daha erken kilit

**Tahmini kurtarma: $70-120** (orjinal zarar $210'dan)

---

## 7. Rollback Plani

Degisiklik tersine alinabilir commit'ler halinde. Her biri ayri commit + test:

1. Score enricher pair_matcher wire revert → eski substring match'e dön (basit git revert)
2. Baseball score exit sil → stop_loss guard geri yukle
3. Config degerleri eski haline dondur (edge, scale_out, max_bet)

Reboot gerekir sadece config icin (kod degisikliklerinde reload yeterli).

---

## 8. Degisiklik Ozeti (Teknik Olmayan)

1. **Asil bug fix**: Skor eşleme sistemindeki basit matcher yerine sophisticated matcher kullanılır. Alias (NYR → Rangers), fuzzy (Şwiatek), swap (home/away ters) destekli. Phantom matchup'larda yanlış eşleşme olmaz.

2. **Baseball'a da tennis/hockey koruması**: Baseball'da 7., 8., 9. inning'lerde geride olunca otomatik çıkış kuralı gelir. A-conf pozisyonlarda da çalışır (mevcut guard A-conf'ta çalışmıyordu).

3. **İyi dönem config**: A-conf eşiği %4 → %6, bet tavanı $50, scale-out erken kilitleme +%25'te %40 — 17 Nis öğleden sonraki iyi dönem davranışı.

4. **Değişmeyen**: Dashboard, Archive, ESPN saat/live tespiti, Tennis/Hockey score exit kuralları, 88¢ bug fix, tüm diğer iyileştirmeler korunur.
