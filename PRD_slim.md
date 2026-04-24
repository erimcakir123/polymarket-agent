# PRD.md — Polymarket Agent 2.0
> v2.0 | 2026-04-22 | Iron rules + glossary only.
> Implementation detayları → DECISIONS.md ve TDD.md.

---

## 1. One-Line

Bookmaker consensus (20+ book) + Polymarket price opportunity → size → open → monitor → exit.

---

## 2. Iron Rules (Non-Negotiable)

### 2.1 P(YES) Anchor
`anchor_probability = P(YES)` her zaman, direction ne olursa olsun.
Direction-adjusted probability karar anında hesaplanır, asla saklanmaz.
→ ARCHITECTURE_GUARD Kural 7

### 2.2 Event-Level Guard
Aynı `event_id` → iki pozisyon imkânsız.
"City wins" BUY_YES açıksa → "Brighton wins" BUY_NO açılamaz.
`entry/gate.py`'de enforce edilir.
→ ARCHITECTURE_GUARD Kural 8

### 2.3 Confidence-Based Sizing
A = bankroll × 5% | B = bankroll × 4% | C = blocked
→ DECISIONS.md (sizing section)

### 2.4 Circuit Breaker — Devre Dışı Bırakılamaz
Daily -%8 / Hourly -%5 / 4 consecutive loss → entry halt.
Her entry'de kontrol edilir, disable edilemez.
→ DECISIONS.md (circuit breaker section)

### 2.5 Bookmaker-Derived Probability
Odds API weighted avg. Sharp books 3.0×.
Exchange'ler vig-free → normalize edilmez.
→ DECISIONS.md (bookmaker tier section)

### 2.6 Exposure Cap — Devre Dışı Bırakılamaz
Soft %50 / Hard %52. Denominator = cash + invested.
→ DECISIONS.md (exposure cap section)

---

## 3. Run Modes

- `dry_run` — live API, order yok (default test)
- `paper` — mock fills, bankroll simülasyonu
- `live` — gerçek order + gerçek USDC

---

## 4. Glossary

| Terim | Tanım |
|---|---|
| `anchor_probability` | Bookmaker consensus P(YES). Direction-independent. |
| `win_prob` | Direction-adjusted: BUY_YES=anchor, BUY_NO=1−anchor |
| `direction` | BUY_YES / BUY_NO |
| `confidence` | A (sharp veya ≥5 book) / B (≥5 book, sharp yok) / C (yetersiz) |
| `favored` | eff_price ≥ 0.65 + conf ∈ {A,B} |
| `elapsed_pct` | Wall clock ilerleme oranı (0.0=start, 1.0=end) — fallback |
| `scale-out` | Kısmi kâr alma: eşikte %40 sat |
| `event_id` | Polymarket event identifier — guard için kullanılır |
