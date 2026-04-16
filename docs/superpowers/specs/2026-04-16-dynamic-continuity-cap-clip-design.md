# Dynamic Continuity via Cap Clipping + Match-Start Priority — Design

**Tarih:** 2026-04-16
**Durum:** DRAFT → user review
**Amaç:** Cap doluyken yüksek-edge yakın maçların kaybolmamasını, erken biten maçların slot açarak yeni maçlara yer vermesini sağlamak.

---

## Problem

Gate'te `_would_exceed_exposure_cap` bir signal cap'i aştığında pozisyonu **tamamen reddediyor**. Sonuç:

1. Kelly size büyük (yüksek-edge live MLB) → cap'i aşar → komple skip → kaçan fırsat.
2. Kelly size küçük (KBO 10h sonrası) → cap'e sığar → açılır.

Bu dinamik sürekliliği kırıyor: bot yakın yüksek-edge'li maçı atıyor, uzak düşük-size'lı maça tutunuyor. Log kanıtı (2026-04-15 23:01 UTC): SF Giants vs Cincinnati live-edge `exposure_cap_reached`, aynı cycle'da KBO Lotte $26.25 açıldı.

Ayrıca gate'e gelen signal'ler match_start'a göre sıralanmıyor — uzak maç cap'te yer alıp yakın olanı engelleyebilir.

## Hedef

1. Cap aşımında size'ı kırp, yine gir (transaction-cost floor'un altına inmedikçe).
2. Her cycle'da gate'e gelen signal listesini match_start ASC sırala — yakın maçlar cap'ten yerini önce alsın.

---

## Tasarım

### 1. Soft cap + hard cap buffer + size clipping

**Config (`config.yaml`, `risk:` altında yeni alanlar):**

```yaml
risk:
  max_exposure_pct: 0.50          # soft cap (mevcut)
  hard_cap_overflow_pct: 0.02     # YENİ: soft cap üstüne +%2 buffer
  min_entry_size_pct: 0.015       # YENİ: minimum pozisyon = bankroll × %1.5
```

**Eşik semantiği (bankroll = B):**
- `soft_cap = B × max_exposure_pct`
- `hard_cap = B × (max_exposure_pct + hard_cap_overflow_pct)`
- `min_size = B × min_entry_size_pct`

Default değerlerle (`B = $1000`): soft=$500, hard=$520, min=$15.

**Gate davranışı (`src/strategy/entry/gate.py`, mevcut cap kontrolü `_would_exceed_exposure_cap`):**

```
intended_size = signal.size_usdc  # Kelly çıktısı
current_exp = sum(p.size_usdc for p in portfolio.positions.values())
available = hard_cap - current_exp

if available <= 0:
    return GateResult(..., "exposure_cap_reached")  # skip
if available < min_size:
    return GateResult(..., "exposure_cap_reached")  # skip (tx-cost floor)

final_size = min(intended_size, available)
if final_size < intended_size:
    # clipped — log'la analiz için
    skip_detail = f"clipped:{intended_size:.2f}->{final_size:.2f}"
signal = signal.model_copy(update={"size_usdc": round(final_size, 2)})
return GateResult(..., approved=signal)
```

**Önemli**: `min_entry_size_pct` **clip sonrası** final_size için de kontrol edilir (yukarıdaki `available < min_size` kontrolü bunu zaten yakalıyor çünkü `final_size ≤ available`).

### 2. Match-start priority in gate evaluation

**Yer:** `src/orchestration/agent.py`, signal'ler gate'e gönderilmeden önceki nokta (mevcut ~line 220).

**Değişiklik:** Signal listesi gate'e **tek tek** gönderiliyor (sıralı). Gate her signal için cap kontrolü yapıyor. Sıralama:

```
signals_sorted = sorted(
    signals,
    key=lambda s: (
        s.match_start_iso or "9999-99-99",   # None/boş en sona
        -s.market.volume_24h,                 # tie-break: yüksek likit önce
    ),
)
for signal in signals_sorted:
    result = gate.evaluate(signal)
    # cap kontrolü gate'in içinde, current_exp her iterasyonda güncellenir
```

**Etki:** Erken başlayan maçlar cap'ten yerini önce alır. Kalan yer (varsa) geç maçlara gider. 10h sonraki KBO ancak tüm yakın maçlar değerlendirildikten sonra cap'e bakar.

### 3. Logging

- Gate skip (`exposure_cap_reached`): mevcut, değişmiyor.
- Yeni: clipped entry → `skipped_trades.jsonl` log yerine yeni bir log? **Hayır** — clipped olan açıldı (skip değil), normal entry log'u yeterli. Ama position entry log'una `original_size_usdc` alanı eklenebilir (post-launch analiz için). **Kapsam dışı**: bu spec'te değil, TODO olarak not düşülür.

---

## Dosya değişiklikleri

| Dosya | Değişiklik |
|---|---|
| `config.yaml` | 2 yeni alan (`hard_cap_overflow_pct`, `min_entry_size_pct`) |
| `src/models/config.py` | `RiskConfig` pydantic modeline 2 yeni alan |
| `src/strategy/entry/gate.py` | Cap kontrolü skip → clip mantığına dönüşür |
| `src/orchestration/agent.py` | Gate'e signal gönderme döngüsü match_start ASC sıralı |
| `tests/unit/strategy/entry/test_gate.py` | Yeni test case'ler |
| `tests/unit/orchestration/test_agent.py` | Priority sıralama testi |
| `TDD.md` | §6 (risk formülleri) veya §13 (entry_gate) güncellenir |
| `PRD.md` | Dokunulmaz. Bu bir demir kural değişikliği değil, davranış düzeltmesi. |

## ARCH_GUARD uyum kontrolü

- **Kural 1 (katman)**: strategy/gate.py + orchestration/agent.py — üst katman alt katmanı çağırıyor. ✓
- **Kural 2 (domain I/O)**: değişiklik strategy+orchestration. Domain dokunulmuyor. ✓
- **Kural 3 (400 satır)**: gate.py şu an ~200 satır, ~20 satır eklenir. ✓
- **Kural 6 (magic number)**: eşikler config'den okunuyor. ✓
- **Kural 7 (P(YES))**: olasılık akışı değişmiyor. ✓
- **Kural 8 (event-guard)**: event_id kontrolü gate'te mevcut, değişmiyor. ✓
- **Kural 11 (test)**: yeni karar noktaları için unit test yazılır. ✓
- **Kural 12 (error handling)**: strategy sessiz skip yerine skip_reason loglu. ✓

## Testler (yazılacak)

1. `test_gate_clips_size_when_cap_partially_full` — $497 exposure, Kelly $50 → $23'e kırpılsın, approved.
2. `test_gate_skips_when_available_below_min_size` — $512 exposure (hard=$520), Kelly $50 → $8 available, min $15 → skip.
3. `test_gate_skips_when_hard_cap_fully_used` — $520 exposure → available=0 → skip.
4. `test_gate_passes_through_when_under_soft_cap` — $100 exposure, Kelly $50 → full $50 approved (soft cap altında, clipping yok).
5. `test_gate_clipping_exactly_at_hard_cap_boundary` — $500 exposure, Kelly $30, hard=$520 → $20'ye kırpılır.
6. `test_agent_evaluates_signals_in_match_start_asc_order` — 3 signal verilir (match_start'ları T+10h, T+1h, T+3h); gate.evaluate çağrı sırası T+1h, T+3h, T+10h olmalı.
7. `test_agent_priority_tiebreak_by_volume` — aynı match_start, farklı volume_24h → yüksek likit önce.

## Kapsam dışı (YAGNI)

- Sport-tag bucket cap (brainstorm'da B3 olarak reddedildi)
- Pozisyon early-close / slot recycle (brainstorm'da C olarak reddedildi)
- Live entry ayrımı (ayrı konu, mevcut davranış korunur)
- `original_size_usdc` log alanı (post-launch analiz için, şimdi değil)

## Risk / edge cases

- **Circuit breaker**: cap değişmiyor, CB mantığı etkilenmiyor.
- **Max bet pct**: `max_bet_pct: 0.05` (mevcut) hâlâ uygulanıyor — Kelly size önce bet_pct ile sınırlanır, sonra cap'e göre kırpılır.
- **Scale-out**: pozisyon size'ı azaldığında cap'te yer açılır (mevcut davranış); yeni spec'te ek etki yok.
- **Bankroll değişkenliği**: bankroll her cycle baz alınır (high-water mark veya current equity, mevcut davranış). Eşikler dinamik olarak yeniden hesaplanır.

---

## Onay

Spec onaylanınca:
1. `writing-plans` skill ile detaylı implementation plan yazılır (`docs/superpowers/plans/2026-04-16-*.md`).
2. Plan onaylanınca kod yazımı başlar (gate → test → agent → test → config → TDD.md güncelleme).
