# SPEC — Spesifikasyonlar

> Bu dosya aktif teknik spesifikasyonları içerir.
> Bir spec entegre edilip onaylandıktan sonra bu dosyadan **SİLİNİR**.
> Sadece aktif, henüz koda dönüşmemiş spec'ler burada durur.

---

## Nasıl Kullanılır

### Spec Ekleme
```
1. Bir özellik veya modül için detaylı spec yaz (aşağıdaki formata uy)
2. Durum: DRAFT
3. Review + onay → durum: APPROVED
4. Kod yazılıp test edildikten sonra → durum: IMPLEMENTED → sil
```

### Spec Formatı
```
### SPEC-XXX: [Modül/Özellik adı]
- **Durum**: DRAFT | APPROVED | IMPLEMENTED
- **Tarih**: YYYY-MM-DD
- **İlgili Plan**: PLAN-XXX
- **Katman**: domain | strategy | infrastructure | orchestration | presentation
- **Dosya**: src/katman/modul.py

#### Amaç
Modülün ne yaptığı, tek cümle.

#### Girdi/Çıktı
- Girdi: ...
- Çıktı: ...

#### Davranış Kuralları
1. ...
2. ...

#### Sınır Durumları (Edge Cases)
- ...

#### Test Senaryoları
- ...
```

---

## Aktif Spesifikasyonlar

### SPEC-004: NHL Score-Based Exit System
- **Durum**: IMPLEMENTED
- **Tarih**: 2026-04-17
- **İlgili Plan**: PLAN-010
- **Katmanlar**: infrastructure (score client) → orchestration (score enrichment + exit entegrasyonu) → strategy/exit (score exit kuralları)
- **Dosyalar**:
  - `src/infrastructure/apis/score_client.py` (YENİ)
  - `src/orchestration/score_enricher.py` (YENİ)
  - `src/strategy/exit/score_exit.py` (YENİ)
  - `src/strategy/exit/monitor.py` (GÜNCELLEME)
  - `src/orchestration/exit_processor.py` (GÜNCELLEME)
  - `src/models/position.py` (GÜNCELLEME — catastrophic watch state)
  - `src/config/sport_rules.py` (GÜNCELLEME — score exit config)
  - `config.yaml` (GÜNCELLEME — score polling ayarları)

#### Amaç
Hockey (NHL/AHL) maçlarında canlı skor verisi kullanarak A-conf hold pozisyonlardaki felaket kayıpları önlemek. Mevcut sistemde A-conf hold aktifken flat SL devre dışı kalıyor ve market_flip sadece elapsed >= %85'te tetikleniyor — bu 9 trade'lik backtest'te $87 kayıp üretti. Skor bazlı çıkış bu kayıbın ~$27'sini kurtarır, kazançlara ($76.84) sıfır dokunur.

#### Arka Plan (Backtest Özeti)

9 hockey trade analiz edildi (5W / 4L). Mevcut net: **-$23.24**.

**Kaybedenler**:
- Rangers 4-2 Lightning: -$42.95 (deficit 2P'de 3'e ulaştı, fiyat 0.086'ya düştü)
- Sharks 6-1 Jets: -$30.71 (deficit 2P'de 3'e ulaştı, fiyat 0.001'e düştü)
- Kings 1-3 Flames: -$13.52 (deficit max 1, sıkı maç — skor kuralı kurtaramaz)
- AHL Hershey 5-1 WB: -$12.90 (B-conf, mevcut SL zaten çalıştı)

**Kazananlar (5 trade, toplam +$76.84)**:
Hiçbirinde bizim tarafımız maç boyunca geride kalmadı (max deficit = 0). Skor kuralları bu trade'lerin hiçbirini etkilemez.

**Simülasyon sonucu (5 kural ile)**: Net **+$3.70** (mevcut -$23.24'ten +$26.94 iyileşme).

#### Kapsam: Sadece Hockey

Bu SPEC sadece `nhl` ve `hockey` sport_tag'li pozisyonlar için geçerlidir. Diğer sporlar (MLB inning_exit, NBA halftime_exit, Tennis set_exit) gelecek SPEC'lerde ele alınacak — aynı score_client altyapısını kullanabilirler.

#### Bileşen 1: Score Client (`infrastructure/apis/score_client.py`)

**Amaç**: Odds API `/v4/sports/{sport}/scores` endpoint'inden canlı skor çekmek.

**Girdi**: `sport_key: str` (ör. `"icehockey_nhl"`)
**Çıktı**: `list[MatchScore]`

```python
@dataclass
class MatchScore:
    event_id: str           # Odds API event ID
    home_team: str
    away_team: str
    home_score: int | None  # None = maç başlamadı
    away_score: int | None
    period: str             # "1st", "2nd", "3rd", "OT", "Final", ""
    is_completed: bool
    last_updated: str       # ISO timestamp
```

**Davranış kuralları**:
1. Odds API `?daysFrom=1` parametresiyle sadece bugünkü maçları çeker
2. API hatası → `[]` döner, WARNING loglar (sessiz hata yutmaz, boş liste döner)
3. Rate limit: çağıran taraf kontrol eder (client kendi rate limit yapmaz)
4. API key config.yaml'dan gelir (mevcut `odds_api.api_key`)

#### Bileşen 2: Score Enricher (`orchestration/score_enricher.py`)

**Amaç**: Açık pozisyonların canlı skorlarını periyodik olarak çekip `score_info` dict oluşturmak.

**Çağrılma**: Light cycle içinde, **her 120 saniyede bir** (config'den: `score.poll_interval_sec: 120`)

**Davranış kuralları**:
1. Sadece `match_live=True` VEYA `match_start_iso` geçmişte olan pozisyonlar için skor çeker
2. Pozisyonun `event_id`'sini Odds API event_id ile eşleştirir (slug + team matching)
3. Score bilgisini `score_info: dict` formatında döner:
   ```python
   {
       "available": True,
       "our_score": 2,        # bizim tarafın skoru
       "opp_score": 4,        # rakibin skoru
       "deficit": 2,          # opp_score - our_score (pozitif = gerideyiz)
       "period": "2nd",       # mevcut periyot
       "map_diff": -2,        # mevcut graduated_sl score_adj ile uyumlu
   }
   ```
4. Eşleşme bulunamazsa → `{"available": False}` döner
5. Direction-aware: BUY_YES ise home/away'den biri "bizim", BUY_NO ise tersi. Eşleştirme `question` parse'ından yapılır (mevcut `question_parser.py` kullanılır)
6. Birden fazla pozisyon aynı sporu oynuyorsa → **tek API çağrısı** ile tüm skorlar çekilir (sport_key bazında grupla)

#### Bileşen 3: Score Exit Kuralları (`strategy/exit/score_exit.py`)

**Amaç**: Skor + süre + fiyat kombinasyonuyla exit sinyali üretmek. Pure fonksiyon — I/O yok.

**Girdi**: `pos: Position, score_info: dict, elapsed_pct: float`
**Çıktı**: `ExitSignal | None`

**5 Kural (öncelik sırasıyla)**:

Tüm eşikler config'den okunur — magic number yasak (ARCH K6).

```
KURAL 1 — Ağır Yenilgi
  Koşul: deficit >= config[period_exit_deficit]  (sport_rules.py, default 3)
  Aksiyon: HEMEN ÇIK
  Config: sport_rules.py → "nhl" → "period_exit_deficit": 3
  Gerekçe: NHL'de 3+ gol geriden dönme ihtimali %5. 
           Backtest: Rangers (dk 25'te deficit=3, fiyat 0.28) ve 
           Sharks (dk 38'de deficit=3, fiyat 0.22) yakalanırdı.

KURAL 2 — Geç Maç Dezavantajı
  Koşul: deficit >= config[late_deficit]  VE  elapsed >= config[late_elapsed_gate]
  Aksiyon: ÇIK
  Config: sport_rules.py → "nhl" → "late_deficit": 2, "late_elapsed_gate": 0.67
  Gerekçe: 1 periyot kaldı + 2 gol geri = %10-12 dönme ihtimali.
           Backtest: Kings (dk 59'da deficit=2) çok geç yakalardı, 
           ama daha erken 2-gol açılsa yakalardı.

KURAL 3 — Skor + Fiyat Teyidi
  Koşul: deficit >= config[late_deficit]  VE  fiyat < config[score_price_confirm]
  Aksiyon: ÇIK
  Config: sport_rules.py → "nhl" → "score_price_confirm": 0.35
  Gerekçe: Hem skor geride hem piyasa ölü diyor — çifte teyit.

KURAL 4 — Son Dakika Çıkışı
  Koşul: deficit >= 1  VE  elapsed >= config[final_elapsed_gate]
  Aksiyon: ÇIK
  Config: sport_rules.py → "nhl" → "final_elapsed_gate": 0.92
  Gerekçe: 1 gol bile geri + 5 dk kaldı = dönme ihtimali çok düşük.
           False positive riski: GK maçında deficit=1 olan an elapsed %37'de → tetiklenmez ✓

KURAL 5 — Catastrophic Watch (Dead Cat Bounce Detector) [TÜM SPORLAR]
  Koşul: fiyat < config[catastrophic_trigger]  → WATCH moduna gir
  Davranış:
    a. Fiyat yükselirse → recovery_peak'i güncelle
    b. Fiyat recovery_peak'ten config[catastrophic_drop_pct]+ düşerse 
       VE recovery_peak > config[catastrophic_trigger] → ÇIK
    c. Fiyat config[catastrophic_cancel] üzerine çıkarsa → watch iptal (gerçek comeback)
  Config (config.yaml → exit bölümü):
    catastrophic_trigger: 0.25
    catastrophic_drop_pct: 0.10
    catastrophic_cancel: 0.50
  Gerekçe: Skor verisi olmasa bile (API çökerse, AHL gibi küçük lig) 
           fiyat bazlı safety net. Bounce+drop pattern'i sahte toparlanmayı yakalar.
```

**Kapsam sınırı**: Bu kurallar SADECE `nhl` ve `hockey` sport_tag'li, A-conf hold pozisyonlara uygulanır. B-conf pozisyonlarda mevcut flat SL zaten aktif — skor çıkışı override etmez.

**Kural 5 (catastrophic watch) istisnası**: Kural 5 tüm sport_tag'ler ve tüm confidence seviyeleri için geçerlidir (universal safety net). A-conf hold olmasına gerek yok.

#### Bileşen 4: Monitor Entegrasyonu (`strategy/exit/monitor.py` güncelleme)

Mevcut `evaluate()` fonksiyonuna `score_info` parametresi zaten var ama hiç doldurulmuyor. Değişiklik:

```python
# MEVCUT (satır 161-168):
a_hold = a_conf_hold.is_a_conf_hold(pos) or pos.favored
if a_hold:
    if elapsed_pct >= 0 and a_conf_hold.market_flip_exit(pos, elapsed_pct):
        return MonitorResult(exit_signal=..., ...)

# YENİ — score exit, a_hold dalında market_flip'ten ÖNCE eklenir:
a_hold = a_conf_hold.is_a_conf_hold(pos) or pos.favored
if a_hold:
    # Score-based exit (NHL/hockey A-conf only)
    if _is_hockey(pos.sport_tag) and score_info.get("available"):
        score_signal = score_exit.check(pos, score_info, elapsed_pct)
        if score_signal is not None:
            return MonitorResult(exit_signal=score_signal, ...)
    # Mevcut market_flip (değişmez)
    if elapsed_pct >= 0 and a_conf_hold.market_flip_exit(pos, elapsed_pct):
        return MonitorResult(exit_signal=..., ...)
```

**Kural 5 (catastrophic watch)** tüm pozisyonlara uygulanır — a_hold dalından ÖNCE, near_resolve ve scale_out'tan SONRA eklenir.

#### Bileşen 5: Position Model Güncelleme

`Position` modeline catastrophic watch state eklenir:

```python
# Yeni alanlar
catastrophic_watch: bool = False
catastrophic_recovery_peak: float = 0.0
```

Bu alanlar `positions.json`'a persist edilir. **Backward compatibility**: Mevcut `positions.json`'da bu alanlar yok — Pydantic default değerleri (`False`, `0.0`) otomatik kullanır, migration gerekmez. Mevcut pozisyonlar sorunsuz yüklenir.

Ayrıca mevcut `match_score` ve `match_period` alanları (Position'da zaten var, hep boş string) bu SPEC kapsamında **doldurulmaz** — score_info dict olarak enricher'dan geçer, Position'a yazılmaz. Bu alanlar gelecek bir SPEC'te kullanılabilir.

#### Bileşen 6: Exit Processor Güncelleme

`exit_processor.py` `run_light()` içinde:
1. Score enricher'ı periyodik çağır (son çağrıdan 120+ sn geçtiyse)
2. `score_info` dict'ini `exit_monitor.evaluate(pos, score_info=score_info)` olarak geçir

```python
def run_light(self) -> None:
    # Score verisi güncelle (periyodik)
    score_map = self.deps.score_enricher.get_scores_if_due()  # {} veya {cid: score_info}
    
    for cid in list(state.portfolio.positions.keys()):
        pos = state.portfolio.positions.get(cid)
        if pos is None:
            continue
        tick_position_state(pos)
        score_info = score_map.get(cid, {})
        result: MonitorResult = exit_monitor.evaluate(pos, score_info=score_info)
        ...
```

#### Bileşen 7: Config Değişiklikleri

**config.yaml**:
```yaml
score:
  poll_interval_sec: 120    # light cycle içinde skor polling aralığı
  enabled: true             # false = skor sistemi tamamen devre dışı
```

**sport_rules.py** — mevcut `period_exit_deficit` korunur, yeni score exit eşikleri eklenir:
```python
"nhl": {
    "stop_loss_pct": 0.30,
    "match_duration_hours": 2.5,
    "period_exit": True,
    "period_exit_deficit": 3,       # K1 tarafından kullanılır (MEVCUT)
    "late_deficit": 2,              # K2: geç maçta çıkış deficit eşiği (YENİ)
    "late_elapsed_gate": 0.67,      # K2: 2P sonu elapsed eşiği (YENİ)
    "score_price_confirm": 0.35,    # K3: skor+fiyat teyit eşiği (YENİ)
    "final_elapsed_gate": 0.92,     # K4: son 5dk elapsed eşiği (YENİ)
}
```

**config.yaml** — catastrophic watch (tüm sporlar) + score polling:
```yaml
score:
  poll_interval_sec: 120
  enabled: true
  match_window_hours: 4     # maç saati ± bu süre dışında API çağrısı yapılmaz

exit:
  catastrophic_trigger: 0.25
  catastrophic_drop_pct: 0.10
  catastrophic_cancel: 0.50
```

#### TDD Güncelleme Notu

Implementasyon sonrası TDD §6.9 tablosu güncellenir:

```
MEVCUT:
  A-conf hold elapsed < 0.85:
    Aktif: Scale-out, Near-resolve
  A-conf hold elapsed >= 0.85:
    Aktif: Scale-out, Near-resolve, market_flip

GÜNCEL (hockey only):
  A-conf hold (tüm elapsed):
    Aktif: Scale-out, Near-resolve, SCORE_EXIT (K1-K4)
  A-conf hold elapsed >= 0.85:
    Aktif: Scale-out, Near-resolve, SCORE_EXIT, market_flip

  A-conf hold (diğer sporlar): DEĞİŞMEZ
```

TDD §7.2 tablosuna NHL satırındaki "Özel exit" sütunu güncellenir:
```
MEVCUT:  period_exit @ -3 goals after P2
GÜNCEL:  score_exit (K1-K4: deficit/elapsed/price combo) + catastrophic_watch (K5)
```

#### Sınır Durumları (Edge Cases)

1. **Odds API skor dönmüyor** (maç bulunamadı): `score_info = {"available": False}` → skor kuralları atlanır, mevcut market_flip + Kural 5 (catastrophic watch) devrede
2. **Event ID eşleşmiyor**: Polymarket event_id ile Odds API event_id farklı formatlar — slug + team name matching ile eşleştirilir. Eşleşme yoksa → `available: False`
3. **Maç overtime'a gidiyor**: elapsed_pct > 1.0 olabilir — kurallar yine çalışır (deficit >= 1 + son 5dk mantığı OT'de de geçerli)
4. **Maç henüz başlamadı**: `home_score = None` → `available: False`
5. **Birden fazla hockey ligi**: Aynı anda NHL + AHL + SHL pozisyonlar olabilir — score_client sport_key bazında gruplar, tek çağrıda tüm ligin skorlarını çeker
6. **Fiyat 0.25'e düşüp hemen geri çıkıyor** (Kural 5): watch aktif olur ama recovery 0.50+ geçerse iptal — false exit yok
7. **Score enricher API rate limit**: Odds API ücretsiz plan 500 req/ay. Her 120 sn'de 1 çağrı = günde 720 çağrı — fazla. **Çözüm (zorunlu)**:
   - Enricher sadece `match_start_iso ± config[match_window_hours]` (default 4 saat) içindeki pozisyonlar için skor çeker
   - Hiç live/yakın pozisyon yoksa → **API çağrısı yapılmaz** (sıfır istek)
   - Aynı sport_key için birden fazla pozisyon varsa → **tek çağrı** (grupla)
   - Bu günde ~50-100 çağrıya düşürür, aylık ~1500-3000 (paid plan gerekebilir)
8. **B-conf hockey pozisyonu**: Skor kuralları (K1-K4) uygulanmaz, mevcut flat SL aktif. Kural 5 (catastrophic watch) uygulanır (universal)

#### Test Senaryoları

**score_exit.py testleri (strategy, unit)**:
- `test_score_exit_deficit_3_immediate_exit`: deficit=3 → ExitSignal döner
- `test_score_exit_deficit_2_late_game_exit`: deficit=2 + elapsed=0.70 → ExitSignal
- `test_score_exit_deficit_2_early_game_hold`: deficit=2 + elapsed=0.30 → None (çıkma)
- `test_score_exit_deficit_2_low_price_exit`: deficit=2 + price=0.30 → ExitSignal
- `test_score_exit_deficit_1_last_5min_exit`: deficit=1 + elapsed=0.93 → ExitSignal
- `test_score_exit_deficit_1_midgame_hold`: deficit=1 + elapsed=0.50 → None
- `test_score_exit_no_score_no_exit`: available=False → None
- `test_score_exit_ahead_no_exit`: deficit=-2 (önde) → None
- `test_score_exit_not_hockey_no_exit`: sport_tag="mlb" → None (sadece hockey)
- `test_score_exit_b_conf_no_exit`: confidence="B" → None (sadece A-conf)

**catastrophic_watch testleri (strategy, unit)**:
- `test_catastrophic_watch_trigger_below_025`: price=0.22 → watch=True
- `test_catastrophic_watch_bounce_then_drop_exit`: 0.22 → 0.35 → 0.30 → ExitSignal
- `test_catastrophic_watch_genuine_comeback_cancel`: 0.22 → 0.55 → watch=False
- `test_catastrophic_watch_all_sports`: sport_tag="mlb" + price=0.22 → watch=True (universal)

**score_client.py testleri (infrastructure, unit + integration)**:
- `test_score_client_parses_response`: mock API response → MatchScore listesi
- `test_score_client_api_error_returns_empty`: HTTP 500 → []
- `test_score_client_no_scores_returns_empty`: boş response → []

**score_enricher.py testleri (orchestration, unit)**:
- `test_enricher_polls_only_when_due`: 120 sn geçmeden → API çağrılmaz
- `test_enricher_groups_by_sport`: 3 NHL + 2 AHL pozisyon → 2 API çağrısı
- `test_enricher_matches_event_by_team_name`: "Rangers vs Lightning" → doğru event eşleşir
- `test_enricher_no_match_returns_unavailable`: eşleşme yok → available=False

**monitor.py entegrasyon testleri**:
- `test_monitor_score_exit_overrides_market_flip`: deficit=3 + elapsed=0.50 → score_exit tetiklenir (market_flip beklemez)
- `test_monitor_no_score_falls_back_to_market_flip`: available=False → mevcut market_flip davranışı

#### ExitReason Enum Güncellemesi

`src/models/enums.py`'ye eklenir:
```python
SCORE_EXIT = "score_exit"          # K1-K4 score-based exit
CATASTROPHIC_BOUNCE = "catastrophic_bounce"  # K5 dead cat bounce
```

#### Değişiklik Özeti

| Dosya | Değişiklik | Satır Tahmini |
|---|---|---|
| `infrastructure/apis/score_client.py` | YENİ | ~60 satır |
| `orchestration/score_enricher.py` | YENİ | ~100 satır |
| `strategy/exit/score_exit.py` | YENİ | ~80 satır |
| `strategy/exit/monitor.py` | GÜNCELLEME (+score exit dalı) | +20 satır |
| `orchestration/exit_processor.py` | GÜNCELLEME (+score polling) | +10 satır |
| `models/position.py` | GÜNCELLEME (+2 alan) | +3 satır |
| `models/enums.py` | GÜNCELLEME (+2 enum) | +2 satır |
| `config/sport_rules.py` | değişiklik yok | 0 |
| `config.yaml` | GÜNCELLEME (+score section) | +3 satır |
| **Testler** | ~15 test | ~250 satır |

Tüm yeni dosyalar 400 satır altında. Katman kuralları korunuyor (infra → orch → strategy).

#### Yan Etki: Mevcut Dead Code → Live Code

Score enricher `score_info` dict'ini `monitor.evaluate()`'e geçirmeye başladığında, şu **mevcut ama hiç çalışmayan** kodlar otomatik aktif olur:

1. **`graduated_sl._score_adjustment()`** (TDD §6.8): `map_diff > 0` → SL %25 gevşer, `map_diff < 0` → SL %25 sıkışır. Bu non-A-conf pozisyonlar için geçerli — ek test gerekmez (mevcut testler score_info ile zaten çalışıyor).

2. **`monitor._never_in_profit_exit()`**: `score_ahead = True` ise never-in-profit exit bloklanır. Bu doğru davranış — takım skorda öndeyse erken çıkışı engeller.

3. **`monitor._hold_revocation_exit()`**: `score_ahead` kontrolü burada da aktif olur.

Bu yan etkiler **tasarımla uyumlu** — TDD §6.8/6.10/6.14 zaten bu davranışı tanımlıyor, sadece veri eksikliğinden çalışmıyordu. Yeni bir şey eklenmemiyor, mevcut tasarım hayata geçiyor.

#### Drift Kontrol Listesi (Implementasyon Sonrası)

- [ ] TDD §6.9 tablosu güncellendi mi?
- [ ] TDD §7.2 NHL satırı güncellendi mi?
- [ ] sport_rules.py'ye yeni config key'ler eklendi mi?
- [ ] config.yaml'a score + exit bölümleri eklendi mi?
- [ ] Mevcut testler hâlâ geçiyor mu? (`pytest -q`)
- [ ] `positions.json` backward compat doğrulandı mı?
- [ ] Eski `match_score`/`match_period` Position alanları boş kalıyor mu?
