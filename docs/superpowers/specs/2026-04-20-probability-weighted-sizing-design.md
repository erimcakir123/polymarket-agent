# SPEC-016 — Probability-Weighted Position Sizing

**Status:** IMPLEMENTED (2026-04-20)
**Author:** Erim + Claude Opus 4.7
**Date:** 2026-04-20

---

## Problem

Mevcut sizing formülü: `stake = bankroll × bet_pct` (capped by $50).

Heavy cycle boyunca girişler zaman sırasına göre işleniyor → her girişten sonra `remaining_bankroll` düştüğü için sonraki girişlerin stake'i de küçülüyor. Sonuç:

| Pozisyon (gerçek data) | Win prob | Stake |
|---|---|---|
| arg-ban-riv1 (underdog) | 0.43 | $50 |
| wta-ribera-kalinin (favori) | 0.80 | $12 |

**Mantık hatası:** Kaybetme ihtimali yüksek olana daha çok, kazanma ihtimali yüksek olana daha az para gidiyor.

**Ana sebep:** Stake zaman-sıralı. İlk girilen $50, son girilen $11. Cap (%52) sadece duruş noktası — küçülmenin sebebi değil.

## Hedef

Stake'i **win_probability ile doğrudan orantılı** yap: yüksek-olasılıklı girişler daha büyük, düşük-olasılıklı girişler daha küçük.

Odds API'nin verdiği bookmaker konsensüs olasılığı direkt ağırlık olarak kullanılır (Odds API zaten anchor probability veriyor — yeni veri kaynağı gerekmez).

## Formül

```
stake = bankroll × bet_pct × win_prob
  → capped by max_bet_usdc
  → capped by bankroll × max_bet_pct
  → floored by Polymarket $5 min-order
```

`win_prob`:
- `BUY_YES` → `signal.probability` (anchor)
- `BUY_NO` → `1 - signal.probability`

P(YES) her zaman anchor olarak saklı (ARCH_GUARD Kural 8). Direction-adjustment sadece sizing hesabında uygulanır.

## Davranış

Config $1000 bankroll, A-conf %5, max $50:

| Win prob | Yeni stake | Eski stake |
|---|---|---|
| 0.43 | $21.50 | $50 |
| 0.60 | $30.00 | $50 |
| 0.70 | $35.00 | $50 |
| 0.80 | $40.00 | $50 |
| 0.95 | $47.50 | $50 |

Ortalama stake ~%30 düşer (tipik portföy avg_prob ~0.65). Exposure düşer → bot daha çok pozisyon alma alanı bulur → diversification artar.

## Güvenlik Ağı

1. **min_entry_size_pct = 0.015** (bankroll × %1.5 = $15): çok düşük prob'ta ($15 altı) giriş bloklanır. Mevcut kontrol zaten var, değişmez.
2. **Polymarket $5 min-order floor**: `POLYMARKET_MIN_ORDER_USDC` sabiti korunur.
3. **probability_weighted config flag**: `RiskConfig.probability_weighted: bool = True`. `false` → eski davranış (rollback için).
4. **Exposure cap (%50+%2) aynen**: formül değişikliği total exposure'ı sadece düşürür, cap kontrolü kaldırılmaz.
5. **Manipulation halving aynen**: `adjust_position_size()` formülden sonra uygulanır.

## Değişecek Dosyalar

| Dosya | Değişiklik |
|---|---|
| `src/domain/risk/position_sizer.py` | `win_probability: float` param ekle, `size = bankroll × bet_pct × win_probability` |
| `src/strategy/entry/gate.py` | 2 çağrı noktasında `win_probability=effective_win_prob(signal)` geçir |
| `src/config/settings.py` | `RiskConfig.probability_weighted: bool = True` |
| `config.yaml` | `risk.probability_weighted: true` |
| `tests/domain/risk/test_position_sizer.py` | Yeni case'ler (win_prob=0.5, 0.8, boundaries) |
| `tests/strategy/entry/test_gate.py` | Gate'in win_prob geçirdiğini doğrula |
| `TDD.md §6.5` | Formül + "neden" notu |
| `PRD.md` | Yeni "Probability-Weighted Sizing" bölümü |

## Test Senaryoları

- **Giriş parametresi:** win_prob=0.5 → stake = base × 0.5
- **Boundary:** win_prob=0.0 → stake = 0 (ama bu case asla oluşmaz, min_favorite_probability = 0.52)
- **Boundary:** win_prob=1.0 → stake = base (eski davranış)
- **BUY_NO:** direction=BUY_NO, anchor=0.20 → win_prob = 0.80 → stake = base × 0.80
- **Cap etkileşimi:** base × win_prob > max_bet_usdc → max_bet_usdc'ye clip
- **Floor:** base × win_prob < $5 → return 0 (entry bloklanır)
- **Flag off:** `probability_weighted=False` → stake = base (eski formül)

## Out of Scope

- Kelly formula (edge / odds ratio) — SPEC-017 ileri aşama
- Cycle-level ranking / batch sizing — SPEC-017
- Stake dinamik rebalancing — SPEC-017

## Self-Review

- ✓ ARCH_GUARD: domain'de I/O yok (pure function değişikliği), config-driven (magic number yok), <400 satır
- ✓ Backwards-compat: flag ile rollback kolay
- ✓ Test coverage: 7 boundary case
- ✓ DRY: `effective_win_prob()` helper `effective_price()` paterniyle uyumlu

## Status Transition

DRAFT → APPROVED (user onayı sonrası) → IMPLEMENTED (code + test + doc merge sonrası)

## Implementation Commits

- T1: `704a44c` feat(sizing): add effective_win_prob direction helper
- T1 fix: `81fce3b` test(sizing): complete effective_win_prob boundary matrix
- T2: `646cdef` feat(sizing): probability-weighted stake in position_sizer
- T2 fix: `c82bfa3` refactor(sizing): remove dead max guard + add floor-boundary test
- T3: `bc3bee2` feat(sizing): probability_weighted config flag
- T4: `cb03b4b` feat(sizing): gate wires win_prob to sizer
- T5: `e641283` docs(tdd/prd): SPEC-016 probability-weighted sizing
