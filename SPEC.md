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

---

## SPEC-C: 3-Way Bookmaker Sanity (LOW PRIORITY — Bekliyor)

> **Tarih:** 2026-05-08
> **Durum:** PARKLA — futbol kapatılana kadar etkisiz

Soccer için draw outcome eksik bookmaker silent skip + 3-way prob sum sanity (0.95-1.05) yok. Futbol açılmadan etkisiz, **futbol açılmadan ÖNCE** bu spec yazılır.

---

## SPEC-SIM: Geriye Dönük Gerçekçi Çıkış Simülasyonu (Faz 1 — salt-okunur döküm)

- **Durum**: DRAFT
- **Tarih**: 2026-06-08
- **Katman**: `scripts/` (üretim-dışı araç — `src/` HİÇ değiştirilmez)
- **Dosya**: `scripts/sim_realistic_replay.py` + `tests/unit/scripts/test_sim_realistic_replay.py`

### Amaç
Bugünün tüm pozisyonlarını (16 açık + bağlanınca tek seferde ~1.00'a satılan 3 kazanan = 19) gerçek dakika-dakika fiyat geçmişine karşı yeniden oynatıp, bağlı olunsaydı tetiklenecek **kademeli kâr-alma / stop / final** olaylarını ortaya çıkarmak; "gerçekte olan" ile "gerçekçi olan"ı yan yana göstermek. Salt-okunur.

### Girdi/Çıktı
- **Girdi**:
  - Açık 16 pozisyon: `data/positions.json`.
  - Kapanan 3 pozisyon: giriş durumu en güncel positions yedeğinden (`data/positions.json.bak.realistic_close_20260608_025345` — 3'ünü de içerir) okunur.
  - Eşik/config: gerçek bot config'i (`config.yaml`) → scale_out tier'ları, partial_sl tier+enabled, graduated_sl enabled, near_resolve eşikleri, high_entry sınırları.
  - Fiyat geçmişi: Polymarket `prices-history` (her `token_id` için, fidelity=60s).
- **Çıktı**: pozisyon başı olay zaman çizelgesi (gerçekte-olan vs gerçekçi-olan) + toplam: gerçek realized $327.89 vs gerçekçi realized $X + fark. Konsola yazılır (bot state dosyalarına YAZILMAZ).

### Davranış Kuralları
1. **Botun kendi beyni çağrılır (DRY)**: her tick'te `lifecycle.tick_position_state(pos)` + `strategy.exit.monitor.evaluate(pos, <config eşikleri>)`. Çıkış mantığı kopyalanmaz.
2. **Pozisyon giriş anına sıfırlanır**: `current_price=entry_price`, peak/ever_in_profit/momentum sayaçları=0, tier'lar=0, shares/size_usdc=orijinal.
3. **Fiyat tabanı**: `prices-history` `market=token_id` ile çekilir → sahip olunan jetonun (BUY_NO ise NO) fiyat serisi. `entry_price`/`current_price` ile aynı taban; realized her iki yön için tek formülle çalışır.
4. **Realized formülü** (`exit_processor._book_sale` ile birebir): `realized = satılan_hisse × (fiyat − entry_price)`. Tek satırlık formül; metodun kendisi `ExitProcessor`/deps'e bağlı olduğu için sim içinde inline kopyalanır, kaynak yorumda belirtilir.
5. **Tetiklenen her çıkış bir olaydır**: partial → hisse küçült + tier artır + olay kaydet; full → kalanı sat + final olay + dur.
6. **Saat enjeksiyonu**: `monitor.evaluate` içindeki `compute_elapsed_pct` gerçek saate bakar. Sim sürecinde monitor modülünün saat kaynağı geçici olarak o tick'in zamanına sabitlenir (yalnızca sim sürecinin belleğinde). Çalışan bot ayrı süreç → etkilenmez, üretim dosyası değişmez.
7. **Çözülme**: seri ~0/~1'e ulaşıp pozisyon hâlâ açıksa, son fiyattan final çıkış (payout) işlenir.

### Sınır Durumları
- Fiyat geçmişi boş/çekilemezse: o pozisyon "veri yok — atlandı" olarak loglanır (sessiz yutma yok), diğerleri devam eder.
- Maçı henüz başlamamış açık pozisyon: seri kısa → muhtemelen hiç tetik yok → "olay yok, hâlâ açık" gösterilir.
- Fill yaklaşıklığı: satış o dakikanın fiyatından modellenir (gerçek emir defteri yok); kayıp-kesme satışları gerçek botta bid/market'ten ~1 tık daha kötü olabilir. Rapor bunu "±~1 tık iyimser" notuyla belirtir.

### Test Senaryoları (pure `replay_position` fonksiyonu, ağ yok)
- `test_replay_rising_curve_triggers_scaleout_tiers_in_order`
- `test_replay_realized_matches_book_sale_formula`
- `test_replay_winner_staged_sum_not_greater_than_single_dump`
- `test_replay_falling_curve_triggers_partial_sl`
- `test_replay_flat_curve_near_entry_no_exit`

### Güvenlik Sınırı (DEMİR)
`positions.json`, `trade_events.jsonl`, `equity_history.jsonl`, `paper_executions.jsonl` ve diğer bot-state dosyalarına **YAZMAZ**. Ağ erişimi yalnızca `prices-history` GET. Çalışan bota dokunmaz. (Faz 2 = uygula; ayrı spec + yedek + onay.)
