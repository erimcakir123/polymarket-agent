# Exit Event Integrity: Realized PnL Reconciliation + Scale-Out Log

**Tarih:** 2026-04-15
**Kapsam:** Orchestration (startup reconcile) + infrastructure (trade_logger partial exit) + agent scale-out branch

---

## 1. Problem

İki bağlantılı bug tespit edildi:

**Bug A — Realized PnL tutarsızlığı:**
- `trade_history.jsonl` (append-only log): 5 kapanmış trade, toplam = **-$82.15**
- `positions.json::realized_pnl` (snapshot): **-$46.08**
- Fark: **$36.07** — bot crash + restart sırasında snapshot güncellenmeden öldü, ilk 2 exit'in realized_pnl'i kaybedildi.

**Bug B — Scale-out görünmezliği:**
- Scale-out partial exit'leri `trade_history.jsonl`'e yazılmıyor (`agent.py::_execute_exit` scale-out branch'ında `apply_partial_exit` portfolio state'ine yazar ama logger çağrılmaz).
- Sonuç: Pozisyonun `scale_out_tier=2` olsa bile dashboard/history'de iz yok. Kullanıcı "scale-out yapmamış" zanneder.
- Reconciliation'da da partial PnL'ler kaybolur → Bug A'yı başka şekilde geri getirir.

---

## 2. Hedef

1. Bootstrap'te realized_pnl'i `trade_history.jsonl`'dan **reconcile** et (log = ground truth).
2. Scale-out partial exit'leri de `trade_history.jsonl`'e yaz — bir pozisyonun tüm yaşam döngüsü tek yerde görünür.
3. Reconciliation partial exit'leri hesaba katar → gelecekte scale-out çalışan bot crash'larında da doğru restore.

---

## 3. Tasarım

### 3.1 TradeRecord şema genişletmesi

`src/infrastructure/persistence/trade_logger.py::TradeRecord` — yeni alan:

```python
partial_exits: list[dict] = []
# Her item: {"tier": int, "sell_pct": float, "realized_pnl_usdc": float, "timestamp": str}
```

**Neden burası:** TradeRecord zaten "bir pozisyonun tüm yaşam döngüsü" için tasarlanmış (entry + optional exit + resolution). Scale-out partial exit'ler de yaşam döngüsünün parçası.

Backward-compat: Varsayılan `[]`, eski kayıtlar eksiksiz çalışır.

### 3.2 TradeHistoryLogger.log_partial_exit (yeni metod)

```python
def log_partial_exit(self, condition_id: str, tier: int,
                     sell_pct: float, realized_pnl_usdc: float,
                     timestamp: str) -> bool:
    """En son açık (exit_price=None) kaydın partial_exits listesine ekle.
    Atomic rewrite (update_on_exit pattern'i).
    Return: kayıt bulunup güncellendi mi?
    """
```

**İmplementasyon:** `update_on_exit`'e benzer — `read_all` → matching record → `partial_exits.append(...)` → atomic rewrite.

**DRY — zorunlu refactor:** İki metot arasındaki ortak "atomic rewrite" pattern'i private helper'a çekilir:

```python
def _rewrite_matching(self, condition_id: str, mutator: Callable[[dict], None]) -> bool:
    """En son açık (exit_price=None) kaydı bul, mutator uygula, atomic rewrite et."""
```

`update_on_exit` ve `log_partial_exit` ikisi de bu helper'ı kullanır. Aynı atomic rewrite iki farklı yerde yazılmaz.

### 3.3 Agent scale-out branch güncellemesi

`src/orchestration/agent.py::_execute_exit` mevcut scale-out bloğu:

```python
if signal.partial:
    shares_to_sell = pos.shares * signal.sell_pct
    realized = pos.unrealized_pnl_usdc * signal.sell_pct
    pos.shares -= shares_to_sell
    pos.size_usdc *= (1 - signal.sell_pct)
    pos.scale_out_tier = signal.tier or pos.scale_out_tier
    pos.scale_out_realized_usdc += realized
    self.deps.state.portfolio.apply_partial_exit(pos.condition_id, realized_usdc=realized)
    logger.info("SCALE-OUT %s: ...")
    return
```

**Ekleme — sadece 1 çağrı:**
```python
    self.deps.trade_logger.log_partial_exit(
        condition_id=pos.condition_id,
        tier=signal.tier or pos.scale_out_tier,
        sell_pct=signal.sell_pct,
        realized_pnl_usdc=realized,
        timestamp=datetime.now(timezone.utc).isoformat(),
    )
```

**Satır etkisi:** agent.py şu an tam 400 satır. Bu ekleme 7 satır → 407. **ARCH_GUARD ihlali.**

**Çözüm:** Scale-out bloğu zaten okunması zor, `_execute_partial_exit(pos, signal)` adıyla ayrı bir metoda extract edilir. Bu hem limit sorununu çözer hem de okunabilirliği artırır. Yeni metod ~15 satır, ama `_execute_exit` ana metodu ~20 satır kısalır → net +5 satır, limit içi kalır (~405 → refactor ile 395).

### 3.4 Portfolio.recalculate_bankroll() (DRY için yeni metod)

`portfolio.from_dict`'te zaten şu formül var (satır 47):
```python
mgr.bankroll = initial_bankroll + mgr.realized_pnl - invested
```

Reconciliation'ın da ihtiyacı aynı formül. **DRY:** Bu mantık `PortfolioManager.recalculate_bankroll(initial_bankroll: float) -> None` adında public metoda çekilir; `from_dict` ve reconciliation ikisi de onu çağırır. Formül tek yerde tutulur.

### 3.5 Startup reconciliation

`src/orchestration/startup.py` — yeni fonksiyon + bootstrap çağrısı:

```python
def _reconcile_realized_pnl(portfolio, trade_logger, initial_bankroll) -> None:
    """trade_history.jsonl'dan true realized hesapla, portfolio snapshot'ıyla
    uyumsuzsa düzelt + bankroll'u yeniden türet.

    True realized = sum(full_exit.exit_pnl_usdc) + sum(partial_exits.realized_pnl_usdc).
    """
    records = trade_logger.read_all()
    true_realized = 0.0
    for rec in records:
        for pe in rec.get("partial_exits", []):
            true_realized += float(pe.get("realized_pnl_usdc", 0.0))
        if rec.get("exit_price") is not None:
            true_realized += float(rec.get("exit_pnl_usdc", 0.0))

    delta = true_realized - portfolio.realized_pnl
    if abs(delta) < 0.01:  # floating noise
        return

    logger.warning(
        "Realized PnL reconciliation: snapshot=%.2f, log=%.2f, delta=%+.2f — using log",
        portfolio.realized_pnl, true_realized, delta,
    )
    portfolio.realized_pnl = true_realized
    portfolio.recalculate_bankroll(initial_bankroll)
```

`bootstrap()` içinde portfolio yüklendikten sonra çağrılır. Trade_logger tek yeni dependency.

### 3.5 Data flow

```
Heavy cycle exit:
  agent._execute_exit
    ├─ partial? → _execute_partial_exit (yeni)
    │    ├─ portfolio.apply_partial_exit (mevcut — realized_pnl biriktir)
    │    └─ trade_logger.log_partial_exit (YENİ — log'a yaz)
    └─ full? → existing path
         ├─ portfolio.remove_position
         └─ trade_logger.update_on_exit (mevcut)

Bootstrap:
  bootstrap(cfg)
    ├─ portfolio.from_dict (mevcut)
    └─ _reconcile_realized_pnl (YENİ — log vs snapshot, log kazanır)
```

---

## 4. Etkilenen Dosyalar

**Backend:**
- `src/infrastructure/persistence/trade_logger.py` — TradeRecord `partial_exits` field + `log_partial_exit` metod + `_rewrite_matching` private helper (DRY: update_on_exit ile paylaşılır)
- `src/domain/portfolio/manager.py` — `recalculate_bankroll(initial_bankroll)` public metod (DRY: from_dict ve reconcile paylaşır)
- `src/orchestration/agent.py` — `_execute_partial_exit` extract + log çağrısı
- `src/orchestration/startup.py` — `_reconcile_realized_pnl` + bootstrap çağrısı

**Tests:**
- `tests/unit/infrastructure/persistence/test_trade_logger.py` — `log_partial_exit` testleri (happy, missing record, backward-compat)
- `tests/unit/domain/portfolio/test_manager.py` — `recalculate_bankroll` testleri (positions yok, multiple positions, realized değişimi)
- `tests/unit/orchestration/test_startup_reconcile.py` (yeni) — reconcile senaryoları (snapshot eşit, snapshot düşük, empty log, partial dahil)
- `tests/unit/orchestration/test_agent_scale_out_log.py` (yeni) — partial exit'te logger çağrıldığını doğrula

**Mevcut testler:** Agent, portfolio, startup testleri geçmeye devam etmeli (yeni field varsayılan `[]` olduğu için parse etkilenmez).

---

## 5. Hata Toleransı

- Trade history bozuk satır: `read_all` zaten `json.JSONDecodeError` yutar — reconcile etkilenmez
- Trade history boş/eksik: `true_realized=0`, `portfolio.realized_pnl=0` ise delta=0, noop
- `log_partial_exit` matching record bulamazsa: `False` döner, agent log warning, trade diskte unsalı oturmuş kalır (ama portfolio state güncellenmiş olur — mevcut davranış)
- Atomic rewrite fail (OSError): hata log, retry yok (eksik log kabul, sonra reconcile düzeltir)

---

## 6. Yapılmayacaklar (Scope Out)

- `Position.volatility_swing` flag bug'ı (VS entry'de False kalıyor). Ayrı iş, kullanıcı onayladı.
- Dashboard exit event'ları için yeni UI (scale-out timeline gibi). Mevcut exited tab partial exit'leri zaten okumaz, bu ayrı iş.
- Retroactive data fix: Mevcut `positions.json`'daki yanlış realized_pnl bootstrap'te otomatik düzeltilecek, manuel migration gerek yok.
- **Dead code temizliği:** `Position.partial_exits` (hiç doldurulmuyor) ve `Position.scale_out_realized_usdc` (yazılıyor ama hiç okunmuyor) field'ları YAGNI ile şimdilik bırakılır. Bu spec single-source-of-truth olarak `TradeRecord.partial_exits`'i kullanır; Position field'ları geriye dönük dokunulmaz. Ayrı bir cleanup task'ı olarak TODO'ya alınabilir.

---

## 7. Başarı Kriterleri

- [ ] Bot restart sonrası `portfolio.realized_pnl` = `trade_history` toplamı (±0.01 noise)
- [ ] Scale-out partial exit trade_history'e `partial_exits` array'i olarak yazılır
- [ ] Bootstrap log: eğer delta varsa warning yazar ve düzeltir
- [ ] Yeni 3 test suite geçer (trade_logger, reconcile, scale_out_log)
- [ ] Mevcut 619 test geçer
- [ ] `agent.py` satır sayısı < 400 (refactor ile)
- [ ] ARCH_GUARD 8 anti-pattern ihlali yok
