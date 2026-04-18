# SPEC-008: Payoff Ratio Fix + Trade Silme Protokolu + Score Exit Isimlendirme

> **Durum**: IMPLEMENTED
> **Tarih**: 2026-04-19
> **Katman**: strategy (scale_out, exit) + domain (position_sizer) + config + protokol
> **Scope**: risk parametreleri + operasyonel protokol + dosya isimlendirme

---

## 1. Problem

56 trade verisinden ortaya cikan tablo:

| Metrik | Deger |
|---|---|
| Win rate | %62.5 (35/56) |
| Ort. kazanc | $9.20 |
| Ort. kayip | $25.35 |
| Payoff ratio | 0.363 |
| EV/trade | **-$3.76** |

**EV negatif.** %62.5 win rate'e ragmen bot para kaybediyor cunku kayiplar
kazancin 2.75 kati.

### Kok Neden Analizi

**1. Scale-out Tier 1 kazanci kesiyor:**
- Tier 1 (+%25'te %40 sat) winning pozisyonlarin karini erken kilitliyor
- Near_resolve (94c) pozisyonu cok daha yuksek karda kapatirdi
- Ama Tier 1 ondan once devreye girip karin yarisini aliyor
- Sonuc: kazanc bankroll buyuse de ~$9'da sabit kaliyor

**2. Kayip tarafi sinirlanmiyor:**
- A-conf pozisyonlar flat SL'den muaf (tasarim geregi)
- Kayip tarafinda "erken kes" mekanizmasi yok
- Bankroll buyudukce bet buyuyor, kayiplar da buyuyor
- Sonuc: grafikteki makas — yesil barlar sabit, kirmizi barlar buyuyor

**3. Asimetri bankroll ile aciliyor:**
- Tier 1 kazanci sabit tutuyor (artmiyor)
- Bet boyutu bankroll ile lineerly buyuyor (kayip artiyor)
- Bu asimetri Tier 1'in yapisi yuzunden — yuzde bazli bahsin degil

### Neden Tier 1 Kaldirmak Sorunu Cozer

Tier 1 kaldiginda:
- Kazanc = (near_resolve_price - entry_price) / entry_price x bet
- Kayip = loss_pct x bet

**Ikisi de bet'in yuzdesi.** Bankroll buyudukce ikisi de orantili buyur.
Asimetri ortadan kalkar. Exponential buyume mumkun hale gelir.

---

## 2. Degisiklikler

### 2a. Scale-out Tier 1 Kaldir + ARCH_GUARD Kural 6 Fix

**Dosya**: `src/strategy/exit/scale_out.py` + `config.yaml`

Mevcut (ARCH_GUARD Kural 6 ihlali — hardcoded sabitler):
```python
TIER1_TRIGGER_PNL = 0.25   # magic number!
TIER1_SELL_PCT = 0.40       # magic number!
TIER2_TRIGGER_PNL = 0.50   # magic number!
TIER2_SELL_PCT = 0.50       # magic number!
```

Yeni: Sabitleri KALDIR, config'den oku.

**config.yaml degisikligi:**
```yaml
scale_out:
  enabled: true
  tiers:
    - threshold: 0.35    # Tier 1: eski 0.25 → 0.35 (daha gec tetikle)
      sell_pct: 0.25     # eski 0.40 → 0.25 (daha az sat)
    - threshold: 0.50    # Tier 2: ayni
      sell_pct: 0.50     # ayni
```

**scale_out.py degisikligi:**
```python
def check_scale_out(
    scale_out_tier: int,
    unrealized_pnl_pct: float,
    tiers: list[dict],          # config'den gelen tier listesi
) -> ScaleOutDecision | None:
    for i, tier in enumerate(tiers):
        if scale_out_tier <= i and unrealized_pnl_pct >= tier["threshold"]:
            return ScaleOutDecision(
                tier=i + 1,
                sell_pct=tier["sell_pct"],
                reason=f"Tier {i+1} at +{unrealized_pnl_pct:.0%}",
            )
    return None
```

**Not**: Tier config'den okundugu icin ileride tier eklemek/cikarmmak
sadece config.yaml degisikligi gerektirir — kod degismez.

**Degisiklik ozeti**: Tier 1 daha gec tetiklenir (+%35 vs +%25) ve daha
az satar (%25 vs %40). Kazancin buyuk kismi maç sonuna kadar kosar,
ama küçük bir pay erken kilitlenir (sigorta).

### 2b. Position Sizing: max_single_bet Kaldir + ARCH_GUARD Kural 6 Fix

**Dosya**: `src/domain/risk/position_sizer.py` + `config.yaml`

**Sorun 1 — Sabit tavan:**
```python
size = min(size, max_bet_usdc, bankroll * max_bet_pct, bankroll)
#                 ^^^^^^^^^^ $75 sabit tavan → exponential buyumeyi oldurur
```

**Sorun 2 — Hardcoded confidence yuzdeleri (ARCH_GUARD Kural 6 ihlali):**
```python
CONF_BET_PCT: dict[str, float] = {
    "A": 0.05,   # magic number!
    "B": 0.04,   # magic number!
}
```

Config'de per-confidence bet_pct tanimli degil. Bunlar config'e tasinmali.

**config.yaml degisikligi:**
```yaml
risk:
  # max_single_bet_usdc: 75  ← KALDIRILDI
  max_bet_pct: 0.05
  confidence_bet_pct:
    A: 0.05
    B: 0.04
```

**position_sizer.py degisikligi:**
```python
def confidence_position_size(
    confidence: str,
    bankroll: float,
    confidence_bet_pct: dict[str, float],  # config'den
    max_bet_pct: float = 0.05,
    is_reentry: bool = False,
) -> float:
    bet_pct = confidence_bet_pct.get(confidence, 0.0)
    if bet_pct == 0.0:
        return 0.0  # C confidence → entry blocked
    if is_reentry:
        bet_pct *= REENTRY_MULTIPLIER
    size = bankroll * bet_pct
    size = min(size, bankroll * max_bet_pct, bankroll)
    return max(0.0, round(size, 2))
```

**Etkilenen dosyalar:**
- `position_sizer.py`: hardcoded CONF_BET_PCT kaldir, config'den al; max_bet_usdc kaldir
- `config.yaml`: `max_single_bet_usdc` sil, `confidence_bet_pct` ekle
- `settings.py`: `max_single_bet_usdc` field sil, `confidence_bet_pct` field ekle
- `gate.py`: `max_single_bet_usdc` kullanimi kaldir
- `factory.py`: `max_single_bet_usdc` gecisi kaldir, `confidence_bet_pct` gecisi ekle

### 2c. Score Exit Dosya Isimlendirme

Mevcut score-based exit dosyalari tutarsiz isimlendirilmis:

| Mevcut | Yeni | Icerik |
|---|---|---|
| `score_exit.py` | `hockey_score_exit.py` | NHL K1-K4 kurallari |
| `tennis_exit.py` | `tennis_score_exit.py` | Tennis T1/T2 kurallari |
| (yeni, kullanici yapiyor) | `baseball_score_exit.py` | MLB inning bazli kurallar |

**Neden**: Tutarli isimlendirme — hepsi `{sport}_score_exit.py` formatinda.
Fonksiyon isimleri degismez (`check()`), sadece dosya adi degisir.

**Etkilenen importlar:**
- `monitor.py`: `from ... import score_exit` → `hockey_score_exit`
- `monitor.py`: `from ... import tennis_exit` → `tennis_score_exit`
- Ilgili test dosyalari

### 2d. Trade Silme Protokolu (Manuel)

Bot icinde endpoint/buton YOK. Kullanici "su trade'i sil" veya
"su trade'de X olsaydi ne olurdu, onu yansit" dediginde Claude
asagidaki protokolu uygular.

#### Etkilenen Dosyalar (tam liste)

Bir trade silindiginde veya degistirildiginde BU DOSYALARIN HEPSI
guncellenir. Eksik birakilan dosya = drift = restart'ta hatali veri.

| # | Dosya | Ne yapilir |
|---|---|---|
| 1 | `logs/positions.json` | Acik pozisyonsa: pozisyonu sil. `realized_pnl` degerini trade'in PnL'i kadar dusur. |
| 2 | `logs/trade_history.jsonl` | Ilgili satiri sil (slug + entry_timestamp ile esle). |
| 3 | `logs/equity_history.jsonl` | Trade'in entry_timestamp'inden sonraki TUM snapshot'larda `realized_pnl`'i duzelt. Eger trade acik pozisyondaysa `invested` ve `unrealized_pnl` da duzeltilir. |
| 4 | `logs/positions.json` → `high_water_mark` | HWM, duzeltilmis equity snapshot'larindan yeniden hesaplanir. |
| 5 | `logs/circuit_breaker_state.json` | Trade'in PnL'i gunluk/saatlik toplama dahil olduysa cikartilir. |
| 6 | `logs/bot.log` / `bot.log.1` | Log'lar DEGISTIRILMEZ (audit trail). |

#### Iki Islem Turu

**A) Tam Silme** ("bu trade'i sil, hic olmamis gibi"):
1. trade_history.jsonl'den satiri sil
2. positions.json'dan pozisyonu sil (aciksa)
3. positions.json realized_pnl'den trade'in toplam PnL'ini (exit + partial) cikar
4. equity_history.jsonl'de trade'in entry_timestamp'inden itibaren
   her snapshot'ta realized_pnl'i duzelt, invested/unrealized guncelle
5. HWM'i yeniden hesapla
6. circuit_breaker_state guncelleyerek PnL'den cikar

**B) What-If Duzeltme** ("SL tetiklenseydi / farkli fiyattan ciksaydi"):
1. trade_history.jsonl'deki exit_price ve exit_pnl_usdc'yi yeni degere guncelle
2. PnL farkini hesapla: delta = yeni_pnl - eski_pnl
3. positions.json realized_pnl'e delta ekle
4. equity_history.jsonl'de exit_timestamp'inden itibaren
   her snapshot'ta realized_pnl'i delta kadar duzelt
5. HWM'i yeniden hesapla
6. circuit_breaker_state guncelle

#### Dogrulama (her islemden sonra)

```
1. positions.json realized_pnl dogrula:
   SUM(trade_history'deki tum exit_pnl_usdc + partial_exit pnl'ler) == realized_pnl

2. equity_history son snapshot ile positions.json uyumlu mu?

3. grep ile silinen trade'in slug'i hicbir json'da kalmadigindan emin ol
   (bot.log haric — log'lar degismez)
```

#### Ornek Kullanim

Kullanici: "mlb-cin-min-2026-04-17 trade'ini sil"
Claude:
1. trade_history.jsonl'de `slug=mlb-cin-min-2026-04-17` satirini bulur
2. exit_pnl_usdc = -55.45, partial_exits toplami = 0 → toplam PnL = -55.45
3. trade_history'den satiri siler
4. positions.json realized_pnl'den -55.45 cikarir (yani +55.45 ekler)
5. equity_history'de entry_timestamp'inden sonraki snapshot'lari duzeltir
6. HWM yeniden hesaplanir
7. Dogrulama calistirilir
8. Rapor: "Trade silindi. realized_pnl $X → $Y. HWM $A → $B."

---

## 3. Etkilenen Dosyalar

### Scale-out + Sizing

| Dosya | Islem | Detay |
|---|---|---|
| `src/strategy/exit/scale_out.py` | GUNCELLE | Hardcoded sabitler kaldir, config'den oku, Tier 1 kaldir |
| `src/strategy/exit/monitor.py` | GUNCELLE | `check_scale_out`'a tiers parametresi gecir |
| `src/domain/risk/position_sizer.py` | GUNCELLE | CONF_BET_PCT kaldir, config'den al; max_bet_usdc kaldir |
| `config.yaml` | GUNCELLE | max_single_bet_usdc sil, confidence_bet_pct ekle, scale_out tier 1 sil |
| `src/config/settings.py` | GUNCELLE | max_single_bet_usdc sil, confidence_bet_pct ekle |
| `src/strategy/entry/gate.py` | GUNCELLE | max_single_bet_usdc kullanimi kaldir |
| `src/orchestration/factory.py` | GUNCELLE | max_single_bet_usdc gecisi kaldir, confidence_bet_pct gecisi ekle |
| `tests/unit/strategy/test_scale_out.py` | GUNCELLE | Tier 1 testleri kaldir/guncelle |
| `tests/unit/domain/test_position_sizer.py` | GUNCELLE | max_bet_usdc testleri kaldir, config-driven testler ekle |
| `TDD.md` | GUNCELLE | §6.5 (sizing) + §6.6 (scale-out) guncelle |
| `PRD.md` | GUNCELLE | Ilgili risk parametreleri guncelle |

### Score Exit Isimlendirme

| Dosya | Islem | Detay |
|---|---|---|
| `src/strategy/exit/score_exit.py` | RENAME | → `hockey_score_exit.py` |
| `src/strategy/exit/tennis_exit.py` | RENAME | → `tennis_score_exit.py` |
| `src/strategy/exit/monitor.py` | GUNCELLE | import isimleri guncelle |
| `tests/unit/strategy/test_score_exit.py` | RENAME | → `test_hockey_score_exit.py` |
| `tests/unit/strategy/test_tennis_exit.py` | RENAME | → `test_tennis_score_exit.py` |

### Trade Silme Protokolu

Kod degisikligi yok — manuel protokol. CLAUDE.md'ye referans eklenir.

---

## 4. Sinir Durumlari

| Durum | Davranis |
|---|---|
| Mevcut acik pozisyonlar (scale_out_tier=1) | Eski Tier 1 zaten tetiklenmis, Tier 2 bekleniyor → yeni kodda tier=1 = max tier, daha fazla scale-out olmaz. Kalan near_resolve'a kadar kosar. |
| Cok yuksek bankroll ($50,000) | %5 x $50,000 = $2,500 → liquidity check (entry_min_depth_usdc) devreye girer |
| max_single_bet_usdc kalktiktan sonra | Tek koruma: max_bet_pct (%5) + liquidity check. Sabit tavan yok. |
| Score exit dosya rename sonrasi | Import'lar guncellenir. Fonksiyon isimleri ayni kalir (check()). |
| Trade silme: partial exit'li trade | Partial exit PnL'leri de realized_pnl'den cikarilir |
| Trade silme: acik pozisyon | positions.json'dan pozisyon silnir + invested/unrealized guncellenir |

---

## 5. Test Senaryolari

### Scale-out (unit — `tests/unit/strategy/test_scale_out.py`)

- `test_scale_out_tier0_below_threshold_returns_none`: PnL < +%50 → tetiklenmez
- `test_scale_out_tier0_at_threshold_returns_tier1`: PnL >= +%50 → Tier 1 (sell %50)
- `test_scale_out_tier1_returns_none`: Zaten Tier 1 tetiklenmis → None (max tier)
- `test_scale_out_old_tier1_threshold_no_trigger`: PnL = +%25 → tetiklenmez (eski Tier 1 yok)

### Position sizer (unit — `tests/unit/domain/test_position_sizer.py`)

- `test_sizing_no_hard_cap`: A-conf $10,000 → $500 (eski $75 cap yok, %5 x $10,000)
- `test_sizing_reads_from_config`: confidence_bet_pct dict'ten dogru okuyor
- `test_sizing_unknown_confidence_returns_zero`: config'de olmayan confidence → $0
- `test_sizing_bankroll_pct_still_caps`: bankroll x max_bet_pct asilmaz
- `test_sizing_min_order_still_works`: $80 bankroll x %5 = $4 < $5 min → caller blocked

### Scale-out config-driven (unit)

- `test_scale_out_reads_tiers_from_config`: config'den tier listesi geciriliyor
- `test_scale_out_empty_tiers_returns_none`: bos tier listesi → tetiklenmez
- `test_scale_out_single_tier_works`: tek tier (0.50/0.50) dogru calisir

---

## 6. Tahmini Etki

Tier 1 kalktiktan sonra (56 trade'lik veri uzerinden projeksiyon):

| Metrik | Oncesi | Sonrasi |
|---|---|---|
| Ort. kazanc | $9.20 | ~$13-14 |
| Ort. kayip | $25.35 | $25.35 (degismez) |
| Payoff ratio | 0.363 | ~0.53-0.55 |
| EV/trade | -$3.76 | ~-$1 ile +$1 |

max_single_bet_usdc kaldirilmasi EV'yi degistirmez — sadece bankroll
buyudugunde buyumenin onunu acar (exponential growth).

Not: Tam pozitif EV icin MLB score exit (ayri SPEC, kullanici yapiyor)
de gerekli. Bu SPEC payoff ratio yapisal duzeltme + operasyonel
iyilestirmeleri kapsar.

---

## 7. Uygulama Notu — Mevcut Pozisyonlar

Bot restart sirasinda mevcut pozisyonlarin `scale_out_tier` degerleri:
- `tier=0`: Hic scale-out olmamis → yeni kodda degisiklik yok
- `tier=1`: Eski Tier 1 tetiklenmis → yeni kodda bu "Tier 1 = eski Tier 2"
  demek, ama eski tier 1 +%25'teydi, yeni tier 1 +%50'de tetikleniyor.
  
  Sorun: tier=1 olan pozisyonlar yeni kodda "zaten Tier 1 gecmis" olarak
  gorulur → Tier 2 beklenecek ama Tier 2 yok → daha fazla scale-out olmaz.
  Bu **istenen davranis**: eski partial exit zaten yapildi, kalan near_resolve'a
  kadar kosar.

---

## 8. Rollback Plani

Degisiklik config + pure fonksiyonlarda. Rollback:
1. `config.yaml` scale_out.tiers: eski iki tier'i geri ekle (0.25/0.40 + 0.50/0.50)
2. `position_sizer.py`: max_bet_usdc parametresini geri ekle
3. `config.yaml`: max_single_bet_usdc: 75 geri ekle
4. `settings.py` + `gate.py` + `factory.py`: max_single_bet_usdc field/param geri ekle
5. Score exit dosya isimleri: rename geri al

Bot restart gerektirir (config reload).

---

## 9. Degisiklik Ozeti (Teknik Olmayan)

1. **Kazananları erken satmayi birak** — Bot kar edince hemen yarisini
   satiyordu. Artik mac sonuna kadar tutacak. Kazanc artar.

2. **Sabit bahis tavanini kaldir** — $75 sabit tavan buyumeyi engelliyordu.
   Artik sadece yuzde bazli (%5). Bankroll buyudukce bahisler de buyur,
   hem kazanc hem kayip orantili kalir.

3. **Score exit dosyalarini duzelt** — Hockey, tennis ve baseball icin
   ayri ayri skor bazli cikis dosyalari var ama isimleri tutarsiz.
   Hepsini `{sport}_score_exit.py` formatina getir.

4. **Trade silme protokolu** — Bir trade silindiginde veya degistirildiginde
   TUM dosyalar (positions, trade_history, equity_history, circuit_breaker)
   guncellenir. Eksik dosya = veri tutarsizligi. Log dosyalari degismez
   (audit trail).
