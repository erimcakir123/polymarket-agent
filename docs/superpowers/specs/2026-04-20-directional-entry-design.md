# SPEC-017 — Directional Entry (Remove Edge-Based Filtering)

**Status:** IMPLEMENTED (2026-04-20)
**Author:** Erim + Claude Opus 4.7
**Date:** 2026-04-20

---

## Problem

Mevcut sistem 3 entry stratejisine sahip, hepsi edge (olasılık farkı) tabanlı:
- **Normal**: `bookmaker - market >= %6`
- **Early**: `bookmaker - market >= %10` + 6h+ önce
- **Consensus**: bookmaker + market aynı favori + 60-80¢ aralığı

Market efficient olduğunda (Polymarket bookmaker'a yakın) neredeyse hiç maç eşiği geçmiyor. 3 saatte sadece 2-5 pozisyon açılıyor. Market efficient olması bizim sistemik problemimiz haline geldi.

## Hedef

Tek "directional entry" stratejisi. Edge hesabını tamamen kaldır. **"Kazananı tespit et ve gir"** mantığı. Bookmaker'ın güvendiği favoriye, fiyat makul aralıktaysa, doğrudan giriş.

## Yeni Entry Logic

```
1. Bookmaker anchor probability'yi al (zaten Odds API'den geliyor)
2. Direction belirle:
   - anchor >= 0.50  → BUY_YES, win_prob = anchor
   - anchor <  0.50  → BUY_NO,  win_prob = 1 - anchor
3. win_prob >= min_favorite_probability (0.55) ? (güçlü favori şartı)
4. effective_entry_price hesapla:
   - BUY_YES → yes_price
   - BUY_NO  → 1 - yes_price
5. min_entry_price (0.60) <= effective_entry_price <= max_entry_price (0.85) ?
6. Diğer guards (event, liquidity, manipulation, exposure cap) — değişmez
7. Stake hesapla (SPEC-016: bankroll × bet_pct × win_prob)
8. Enter
```

Edge hesabı yok. Eşik yok. Sadece: "favori + makul fiyat → giriş".

## Silinecek Kavramlar

| Kavram | Konum | Durum |
|---|---|---|
| `calculate_edge()` | `src/domain/analysis/edge.py` | **DELETE** |
| Normal entry | `src/strategy/entry/normal.py` | **DELETE** |
| Early entry | `src/strategy/entry/early_entry.py` | **DELETE** |
| Consensus entry | `src/strategy/entry/consensus.py` | **DELETE** |
| `Signal.edge` field | `src/models/signal.py` | **DELETE** |
| `EdgeConfig` | `src/config/settings.py` | **DELETE** |
| `EarlyEntryConfig` | `src/config/settings.py` | **DELETE** |
| `ConsensusConfig` | `src/config/settings.py` | **DELETE** |
| `edge:` yaml bloğu | `config.yaml` | **DELETE** |
| `early:` yaml bloğu | `config.yaml` | **DELETE** |
| `consensus:` yaml bloğu | `config.yaml` | **DELETE** |
| `three_way_entry.evaluate()` min_edge param | `src/strategy/entry/three_way.py` | **REMOVE arg** |
| TDD §6.3 Edge hesabı | `TDD.md` | **DELETE** |
| TDD §6.4 Consensus | `TDD.md` | **DELETE** |
| TDD §6.4b 3-Way edge | `TDD.md` | **UPDATE** (edge refs kaldır) |
| PRD edge bahisleri | `PRD.md` | **DELETE / UPDATE** |

## Eklenen Yapılar

### Yeni dosya: `src/strategy/entry/directional.py`

Tek entry stratejisi. ~60 satır tahmini:

```python
"""Directional entry (SPEC-017) — bookmaker favoriye fiyat aralığında giriş.

Edge yok. Favori + fiyat aralığı + guards.
"""
from dataclasses import dataclass
from src.models.enums import Direction
from src.models.position import effective_win_prob
from src.models.signal import Signal


def evaluate(
    anchor: float,
    market_yes_price: float,
    confidence: str,
    min_favorite_probability: float = 0.55,
    min_entry_price: float = 0.60,
    max_entry_price: float = 0.85,
) -> Signal | None:
    """Directional entry decision.

    Returns Signal if eligible, None otherwise.
    """
    # Direction from bookmaker favorite
    direction = Direction.BUY_YES if anchor >= 0.50 else Direction.BUY_NO
    win_prob = effective_win_prob(anchor, direction.value)

    if win_prob < min_favorite_probability:
        return None

    effective_price = (
        market_yes_price if direction == Direction.BUY_YES
        else 1.0 - market_yes_price
    )
    if not (min_entry_price <= effective_price <= max_entry_price):
        return None

    return Signal(
        direction=direction.value,
        probability=anchor,
        confidence=confidence,
        market_price=market_yes_price,
        # ... standard fields
    )
```

### Yeni config: `EntryConfig`

```python
class EntryConfig(BaseModel):
    model_config = ConfigDict(extra="ignore")
    min_favorite_probability: float = 0.55
    min_entry_price: float = 0.60
    max_entry_price: float = 0.85
```

### Yeni yaml:

```yaml
entry:
  min_favorite_probability: 0.55
  min_entry_price: 0.60
  max_entry_price: 0.85
```

## Değişecek Kavramlar (RENAME, SILINMEZ)

| Eski | Yeni | Sebep |
|---|---|---|
| `no_edge_attempts` | `stale_attempts` | stock_queue.py — "peş peşe skip edildi" counter'ı, anlamsal güncelleme |
| `skip_reason="no_edge"` | `skip_reason="below_fav_prob"` veya `"price_out_of_range"` | skipped_trade_logger — yeni sebep taksonomisi |
| `consensus.py` | Silinir (yerine yok) | Tek directional path, consensus senaryosu zaten directional'de |
| `three_way.py` `min_edge` | Silinir (arg kaldırılır) | 3-way de edge-free olacak; direction + favorite + price range |

## Korunan Sistemler

- **Position sizing (SPEC-016)**: `stake = bankroll × bet_pct × win_prob` aynen.
- **Exit kuralları**: stop-loss, scale-out, score-exit, catastrophic drop, near-resolve — hepsi aynen.
- **Risk kontrolleri**: event guard, exposure cap (%52), max_positions, blacklist — aynen.
- **Manipulation/liquidity filters**: aynen.
- **Stock queue/scanner**: aynen, sadece `no_edge_attempts` → `stale_attempts` rename.
- **Score enricher, match lifecycle**: aynen.
- **Dashboard, notifier**: aynen (sadece edge gösterimi kaldırılır).
- **3-way (SPEC-015)**: favorite filter (0.40 absolute + 7pp margin) korunur, edge kaldırılır.

## Güvenlik Ağı

1. **min_entry_size_pct (%1.5)**: korunur, çok küçük stake bloklanır.
2. **max_entry_price (0.85)**: önceki 0.88'den sıkı (aşırı pahalı entry'ler bloklu).
3. **min_entry_price (0.60)**: yeni — underdog BUY_YES girişini engeller (underdog favori → 0.40 yes_price = 0.60 NO side, giriyoruz zaten).
4. **min_favorite_probability (0.55)**: eskiden 0.52 idi, şimdi 0.55 (toss-up'lar bloklu).
5. **Exit kuralları aynen**: kötü giriş yapsak bile stop-loss + score-exit kurtarır.
6. **Bankroll-weighted stake (SPEC-016)**: kazanma olasılığı düşükse stake de düşük → kayıp sınırlı.

## Ekonomik Varsayım

Market efficient değilse (Polymarket retail vs bookmaker pro), bu sistem:
- **Pozitif EV** — Polymarket sistematik olarak favori tarafı underpricing yapar → bizim girişler bookmaker gerçeğine yakınsadıkça kâr.
- **Sıfır EV** — Market fair → ortalama break-even, fee'ler nedeniyle hafif eksi.
- **Negatif EV** — Polymarket sistematik olarak favori tarafı overpricing yapar → bizim girişler erir.

3 saatlik dry_run ile hangisi olduğunu göreceğiz. Dry run riskli değil (sanal para).

## Out of Scope

- Edge mantığını kısmi koruma (örn "hafif edge check") — tamamen siliniyor
- Yeni entry modları (momentum, mean-reversion, vb) — başka SPEC
- Early/consensus'un rehabilitasyonu — tamamen kaldırılıyor

## Self-Review

- ✓ ARCH_GUARD Kural 5 (magic number): tüm sayılar config'den gelir
- ✓ ARCH_GUARD Kural 9 (5-katman): directional.py strategy katmanında, domain temiz
- ✓ ARCH_GUARD Kural 3 (<400 satır): directional.py ~60 satır tahmini
- ✓ ARCH_GUARD Kural 1 (DRY): 3 entry → 1, duplikasyon azalıyor
- ✓ ARCH_GUARD Kural 6 (utils/helpers yok): yeni katman yok
- ✓ Backwards-compat: ROLLBACK git revert ile
- ✓ Test coverage: silinen dosyaların testleri de silinir, yeni directional.py için unit tests
- ✓ Docs: TDD + PRD sync

## Status Transition

DRAFT → APPROVED (user onayı) → IMPLEMENTED (code + test + doc merge)

## Soru / Belirsizlik

**S1: Early entry'nin özelliği (6h+ önce giriş) kaybolur mu?**
Cevap: Scanner zaten `max_hours_to_start=24.0` ile zaman penceresi yönetiyor. Early path'in yaptığı ekstra şey sadece "yüksek edge" aramaktı, o da gidiyor. Early'nin öngörüsü yok oluyor ama directional zaten match 6-24h arası da çalışıyor. Kayıp yok.

**S2: Consensus'un "bookmaker+market aynı favori" garantisi kayboluyor mu?**
Cevap: Directional'de zaten bookmaker favori yönünde gidiyoruz. Market'ın aynı yönde olması şart değil (bookmaker lider varsayımı). Consensus'un sunduğu tek şey "60-80¢ fiyat aralığı"ydı, yeni min/max entry price kuralları bunu 0.60-0.85'e genelliyor.

## Implementation Commits

- T1: `afd7c97` feat(entry): add directional strategy + EntryConfig + boundary tests
- T2: `3c2d82f` refactor(entry): gate uses directional only, three_way edge-free
- T3: `8461ea4` refactor(entry): delete edge/normal/early/consensus, cleanup references
- T3 polish: `4f4f510` polish(spec-017): migration comment + notifier P(book) + stronger gate assertion
- T4: `274b057` docs(tdd/prd): sync docs with SPEC-017
