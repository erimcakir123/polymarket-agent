# Tasarım: Zarar-kes çıkışında gerçekçi piyasa davranışı

**Tarih:** 2026-06-08
**Durum:** DRAFT (onay bekliyor)
**Tetikleyen olay:** İki PAPER pozisyonu (Maria–Rakhimova tenis ML, Zverev–Cobolli set handikabı) zarar-kes eşiklerini geçtikleri halde kapanmadı; sırasıyla -%94 ve gerçek-%99'a sürüklendi.

---

## 1. Yön ilkesi

> **PAPER bot, gerçek bir Polymarket "piyasa emri"nin yapacağını birebir taklit etmeli.**
> Ne fazla iyimser (olmayan alıcıya hayali dolum), ne fazla korkak (gerçek alıcı varken satmama).

Bu ilke hem doğru zarar yönetimi hem de "çalışsaydı ne olurdu" rakamının güvenilir olması için gerekli.

---

## 2. Kök neden (kanıtlanmış — audit + log)

### A. Kayma koruması zarar-kesi öldürüyor (Maria)
`max_sell_slippage_pct = 0.05`. `walk_sell` yalnızca `bid >= referans × (1 - %5)` seviyelerini yürüyor.
Düşen bir pozisyonda en iyi alıcı her zaman referansın altındadır → satış reddedilir (`no_bids_above_slippage`).

Audit kanıtı (UTC):
| Saat | Hedef | Zarar | Defterdeki alıcılar | Sonuç |
|---|---|---|---|---|
| 16:27 | 0.52 | giriş | sağlıklı | DOLDU $50 |
| 17:39 | 0.30 | -42% | 0.27×48, **0.26×6483**, 0.25×136 | ❌ no_bids_above_slippage |
| 17:53 | 0.26 | -50% | 0.21×5696 | ❌ no_bids_above_slippage |
| 18:01 | 0.10 | -81% | 0.07×2114, 0.06×5959 | ❌ no_bids_above_slippage |
| 18:13 | 0.03 | -94% | BOŞ | ❌ below_min_order_usdc |

17:39'da 26¢'te **6.483 hisse** gerçek alıcı vardı; satılacak miktar ~29 hisse. Kayma kuralı engelledi.
Reddedildiğinde `exit_processor` kademeyi ilerletmez → `partial_sl_tier` 0'da kaldı, pozisyon sıfıra sürüklendi.

### B. Sıçrama koruması fiyatı donduruyor (Zverev)
`price_feed` tek tickte `|Δ| > %50` hareketi "sahte" sayıp reddediyor (SPEC-M / KBO bug 2026-05-19).
Maç bitince 0.48 → ~0 çöküşü %50'yi aştığı için reddedildi (token için **6.058 kez**).
İç fiyat 0.48'de dondu → monitör -%25 görüyor → tier 2 eşiği (-%35) hiç tetiklenmiyor.

---

## 3. Tasarım

### Parça A — Zarar-kes satışı = gerçek piyasa emri
- **Değişiklik:** Kayıp tarafı çıkışlarında (`PARTIAL_SL` ve tam stop-loss) `walk_sell` kayma tabanı **uygulanmaz** → tüm gerçek bid defteri yürünür (market emri), oradaki **gerçek miktar** kadar, **gerçek fiyattan** doldurulur. Kötü fiyat kabul edilir.
- Mekanik olarak: kayıp-tarafı çıkış için `walk_sell` market modunda çağrılır (kayma tabanı = 0; `min_acceptable = 0`). `walk_sell` zaten yalnızca her seviyedeki gerçek `size` kadar dolduruyor → hayalet dolum yok.
- **Kapsam:** Yalnızca kayıp-tarafı (`PARTIAL_SL`/stop-loss). `SCALE_OUT` (kâr tarafı) ve `BUY` giriş kayma kuralları **aynen kalır** (orada gerçekçi olan kayma kontrolüdür).

### Parça B — Sıçrama reddi defterle doğrulanır
- **Değişiklik:** `price_feed`, `|Δ| > %50` bir hareketi **körü körüne reddetmez**; canlı defterle teyit eder. Yeni fiyat gerçek en-iyi-alıcı/satıcı seviyesiyle uyuşuyorsa (piyasa gerçekten orada) **kabul eder**. Sadece defterle doğrulanamayan hareket reddedilir (orijinal KBO senaryosu: bayat cache → defterde karşılığı olmayan sahte sıçrama).
- Doğrulama biçiminin tam mekaniği (canlı best-bid karşılaştırması vs. N-tick kalıcılık) uygulama planında netleşecek; ilke: **defterde karşılığı olan hareket gerçektir.**

### Değişmeyen, çünkü zaten gerçekçi
- **`min_order_usdc = 1.0`** — Polymarket'in gerçek kuralı. Pozisyon $1 altına düştüyse gerçek yatırımcı da satamaz. Sonuç (tasarlanan): pozisyon likidite varken erkenden kesilir; dibe inerse `below_min` ile takılı kalması doğru/gerçekçidir.
- **Gerçek-derinlik dolumu** — `walk_sell` her seviyede yalnızca gerçek `size` kadar doldurur; minik hayalet alıcı yalnızca o miktar kadar kısmi dolum üretir.
- **Reddedilince kademe ilerletmeme** — gerçek satış olmadan defter mutasyonu yok kuralı korunur.

---

## 4. Beklenen etki (geriye dönük)
- **Maria:** 17:39'da derin alıcıya kesilirdi → kademeli ~$23–25 geri kazanım, sonuç ~-$25 (gerçekleşen -$47 yerine).
- **Zverev:** Çöküş görülür, tier 2/3 ateşler; ancak gerçek değer zaten dipte olduğundan kurtarılan tutar küçük — asıl kazanç gelecekteki benzer pozisyonlarda erken kesim.

---

## 5. Etkilenen katmanlar (ARCH uyumu)
- `src/domain/execution/paper_fill.py` — `walk_sell` market modu (domain, pure, I/O yok). ✓ katman
- `src/orchestration/paper_executor.py` — `partial_sell`'e kayıp-tarafı/market bayrağı.
- `src/orchestration/exit_processor.py` — `PARTIAL_SL`/stop-loss çıkışında market modu iste.
- `src/infrastructure/websocket/price_feed.py` — sıçrama reddini defterle doğrula (infrastructure).
- Layering ihlali yok; üst→alt çağrı korunur.

## 6. Test
- Birim: kayıp-tarafı satış derin bid'e dolar (FILLED); ince/hayalet bid gerçek kısmi-dolum verir; kâr-tarafı + giriş kayma kuralı değişmez (regresyon).
- Birim: defterle doğrulanan sıçrama kabul; doğrulanamayan (KBO tipi) reddedilir.
- Fixture: gerçek audit defter görüntüleri (paper_executions.jsonl) gerçekçi test verisi olarak.

## 7. Kapsam dışı (YAGNI)
- LIVE executor değişikliği (bot PAPER kilitli; SPEC-Z25).
- Kademe eşikleri/yüzdeleri (config.partial_sl) — değişmez.
- Çalışan bota reload/reboot — ayrı, açık kullanıcı onayıyla.
