# SPEC-005: ESPN Score Client + Agent Loop Wire

> **Tarih:** 2026-04-17
> **Durum:** DRAFT
> **Bağımlılık:** Yok (bağımsız altyapı)
> **Bağımlı:** SPEC-006 (Tennis Score-Based Exit) bu altyapıyı kullanacak

---

## Amaç

Canlı maç skorlarını agent loop'a bağlamak. ESPN API primary skor kaynağı, Odds API fallback. Bu tamamlandığında:

1. Hockey K1-K4 score exit kuralları **aktif** olur (kod zaten var, veri yoktu)
2. Tennis/MLB/NBA için score_info populate edilir (gelecek exit kuralları için hazır)
3. Tek skor kaynağına bağımlılık riski ortadan kalkar (ESPN primary + Odds API fallback)

---

## Mimari

```
Infrastructure                    Orchestration              Strategy
─────────────                    ─────────────              ────────
espn_client.py ──┐
                 ├─→ score_enricher.py ──→ exit_processor.py ──→ monitor.py
odds_client.py ──┘    (sport-dispatch)      (score_map inject)    (score_exit)
```

### Katman Sorumlulukları

| Katman | Dosya | Sorumluluk |
|---|---|---|
| Infrastructure | `espn_client.py` | ESPN HTTP çağrısı + JSON parse |
| Orchestration | `score_enricher.py` | Sport-dispatch, polling throttle, fallback |
| Orchestration | `factory.py` | ESPNClient + ScoreEnricher oluşturma |
| Orchestration | `agent.py` | Light cycle'da score_map inject |
| Config | `sport_rules.py` | Per-sport score_source + ESPN mapping |
| Config | `config.yaml` | Poll intervals + kill switch |

---

## Bileşen 1: ESPN Client (`infrastructure/apis/espn_client.py`)

### Endpoint

```
GET https://site.api.espn.com/apis/site/v2/sports/{sport}/{league}/scoreboard?dates={YYYYMMDD}
```

- Ücretsiz, API key gerektirmez
- Rate limit: belgelenmemiş ama public API, dakikada 1 call güvenli
- Kapsam: NHL, MLB, NBA, ATP, WTA (tüm MVP sporlarımız)

### Veri Modeli

```python
@dataclass
class ESPNMatchScore:
    event_id: str           # ESPN competition ID
    home_name: str          # "Ben Shelton"
    away_name: str          # "Joao Fonseca"
    home_score: int | None  # Toplam (hockey: gol, tennis: set kazanma)
    away_score: int | None
    period: str             # "3rd", "Final", "In Progress", ""
    is_completed: bool
    is_live: bool
    last_updated: str       # ISO timestamp
    linescores: list[list[int]]  # [[home_games, away_games], ...] per set/period
```

### Parse Mantığı

ESPN response yapısı:
```
events[] → groupings[] → competitions[] → competitors[] → linescores[]
```

Her competition = 1 maç. Competitor'dan `athlete.displayName` + `linescores[].value` çıkarılır.

**Tennis linescores örneği:**
```python
# Muchova bt Gauff 6-3, 5-7, 6-3
# competitors[0].linescores = [{"value": 6}, {"value": 5}, {"value": 6}]
# competitors[1].linescores = [{"value": 3}, {"value": 7}, {"value": 3}]
# → linescores = [[6,3], [5,7], [6,3]]  (pair per set)
```

**Hockey linescores:** Periyot bazlı gol — şu an kullanılmıyor, `home_score/away_score` yeterli.

### Hata Davranışı

ESPN 4xx/5xx/timeout → `None` dön. Çağıran (ScoreEnricher) fallback'e geçer.

---

## Bileşen 2: ScoreEnricher Refactor (`orchestration/score_enricher.py`)

### Sport-Dispatch

Her sport için hangi skor kaynağını kullanacağı `sport_rules.py`'den gelir:

```python
"nhl": {
    "score_source": "espn",
    "espn_sport": "hockey",
    "espn_league": "nhl",
}
"tennis": {
    "score_source": "espn",
    "espn_sport": "tennis",
    "espn_league": "atp",  # wta → slug'dan resolve
}
"mlb": {
    "score_source": "espn",
    "espn_sport": "baseball",
    "espn_league": "mlb",
}
"nba": {
    "score_source": "espn",
    "espn_sport": "basketball",
    "espn_league": "nba",
}
```

Tennis league resolve: slug `wta-*` → `"wta"`, slug `atp-*` → `"atp"`.

### Fallback Zinciri

```
1. ESPN çağır (primary)
2. ESPN başarısız → Odds API çağır (fallback)
   - Tennis: Odds API skor vermiyor → fallback yok, None dön
   - Hockey/MLB/NBA: Odds API skor veriyor → fallback çalışır
3. İkisi de başarısız → score_info = {} (mevcut davranış, exit kuralları skip)
```

### Adaptif Polling

| Koşul | Interval | Config key |
|---|---|---|
| Fiyat > `critical_price_threshold` | `poll_normal_sec` (60) | `score.poll_normal_sec` |
| Fiyat ≤ `critical_price_threshold` | `poll_critical_sec` (30) | `score.poll_critical_sec` |

Threshold: `score.critical_price_threshold: 0.35` (config.yaml).

Polling throttle pozisyon bazlı: en düşük fiyatlı pozisyonun durumu interval'ı belirler.

### score_info Çıktı Formatı (değişmiyor)

```python
{
    "available": True,
    "our_score": 2,
    "opp_score": 3,
    "deficit": 1,
    "map_diff": -1,
    "period": "3rd",
    "linescores": [[6,3],[2,5]]  # SPEC-006 için (tennis)
}
```

`linescores` field'ı SPEC-005'te populate edilir ama tüketilmez. Mevcut `score_exit.py` (K1-K4) sadece `deficit`, `period`, `available` kullanır — kırılma yok.

---

## Bileşen 3: Agent Loop Wire

### factory.py

```python
# Yeni:
espn_client = ESPNClient()
score_enricher = ScoreEnricher(
    espn_client=espn_client,
    odds_client=odds_client,          # mevcut
    poll_normal_sec=cfg.score.poll_normal_sec,
    poll_critical_sec=cfg.score.poll_critical_sec,
    critical_price_threshold=cfg.score.critical_price_threshold,
)
# deps'e ekle
```

### agent.py

```python
# Mevcut:
exit_processor.run_light(score_map=None)

# Yeni:
score_map = self.deps.score_enricher.get_scores_if_due(
    positions=self.deps.state.portfolio.positions,
)
exit_processor.run_light(score_map=score_map)
```

### Kill Switch

`config.yaml → score.enabled: false` → ScoreEnricher.get_scores_if_due() hemen `{}` döner. Mevcut davranış korunur.

---

## Bileşen 4: Config Değişiklikleri

### config.yaml

```yaml
score:
  enabled: true
  poll_normal_sec: 60
  poll_critical_sec: 30
  critical_price_threshold: 0.35
```

### sport_rules.py

Her MVP sport'a `score_source`, `espn_sport`, `espn_league` eklenir.

Tennis için `espn_league` slug'dan runtime resolve edilir (atp/wta).

---

## Test Stratejisi

### Yeni testler

| Test dosyası | Kapsam |
|---|---|
| `tests/unit/infrastructure/apis/test_espn_client.py` | ESPN JSON parse: hockey gol, tennis set, hatalı response → None |
| `tests/unit/orchestration/test_score_enricher.py` (genişlet) | Sport-dispatch, ESPN→fallback Odds API, adaptif polling |

### Mevcut testler — kırılmamalı

- `test_score_exit.py` — score_info formatı aynı
- `test_monitor.py` — score_map inject mekanizması aynı
- `test_catastrophic_watch.py` — bağımsız

### Integration test (manuel)

`tests/integration/test_espn_live.py` — gerçek ESPN API'ye tek call, smoke test.

---

## Tamamlanma Kriterleri

1. `pytest tests/ -q` → tümü green
2. Bot dry_run → light cycle'da score poll logları görülür
3. Canlı NHL maçında score_info populate (deficit/period dolu)
4. ESPN mock fail → Odds API fallback çalışır (hockey/mlb/nba)
5. Tennis ESPN fail → fallback yok, score_info boş (log uyarısı)
6. `config.yaml → score.enabled: false` → eski davranış, score_map boş
7. Mevcut 753 test kırılmaz

---

## Kapsam Dışı

- Tennis T1-T2-T3 exit kuralları → SPEC-006
- `linescores` tüketimi → SPEC-006
- Golf/Soccer skor entegrasyonu → gelecek
- ESPN WebSocket/push → gereksiz, polling yeterli
