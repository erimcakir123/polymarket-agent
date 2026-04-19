# TODO — v2 Post-MVP Eklemeleri

> Bu dosya **tek** TODO listesidir. Aktif planlar `PLAN.md`'de, aktif spec'ler `SPEC.md`'de.
> Burası: v2 MVP dışı, sonradan eklenecek işler.
>
> Kullanıcı "TODO'YA YAZ" dediğinde → bu dosyaya eklenir, başka yere değil.
> Sıra ile ilerlenir — kullanıcı bir branş için "kurallarını ekleyelim" dediğinde o başlığa özel kural seti hazırlanır.

---

## TODO-001: Draw-Possible Sports — Her Branş için Ayrı Kural Yazılacak

- **Durum**: DEFERRED — v2 MVP dışı
- **Tarih**: 2026-04-13
- **Öncelik**: P1 — çok fırsat var (özellikle Draw market'leri underpriced)
- **Yaklaşım**: Her branş kendine özgü kurallar gerektirir. MVP stabil olduğunda **sırayla** her branşa özel strateji geliştirilecek.

### Genel Prensipler (her branş için geçerli)
- Polymarket 3 ayrı binary market açıyor (örn. Home YES/NO, Draw YES/NO, Away YES/NO)
- Odds API 3-way probability veriyor (P_home + P_draw + P_away = 1.0)
- Bot 3 market'in her birinde edge hesaplar, en büyük edge'e girer (1 maç = 1 pozisyon)
- Scanner'da "end in a draw" keyword bloğu kaldırılmalı
- Matching sistemi aynı event_id altında 3 tarafı eşleştirmeli

### Sırayla Ele Alınacak Branşlar (Her birine ayrı kural seti)

| Sıra | Branş | Draw Sıklığı | Lig / Turnuva Listesi (Odds API) |
|---|---|---|---|
| 1 | **Soccer** | %25-30 | EPL, La Liga, Serie A, Bundesliga, Ligue 1, Eredivisie, Primeira Liga, Süper Lig, Scottish Premiership, Belgian First Div, Danish Superliga, Eliteserien, Allsvenskan, Swiss Superleague, Greek Super League, Austrian Bundesliga, Russian PL, Saudi Pro League, K League, J League, A-League, Liga MX, Brasileirão (+Série B), Argentine Primera División, Chilean Campeonato, Colombian Primera A, Peruvian Liga 1, Paraguayan Primera, Uruguayan Primera, Ecuadorian LigaPro, Venezuelan Primera, Bolivian Primera, Chinese Super League, Thai League, Indonesian Liga 1, Indian Super League, Egyptian Premier League, Moroccan Botola Pro, Polish Ekstraklasa, Czech First League, Romanian Liga 1, Ukrainian Premier League, Croatian HNL, Slovakian Super Liga, Cypriot First Division, Turkish Süper Lig, Finnish Veikkausliiga, League of Ireland, Swedish Superettan, Italian Serie B, French Ligue 2, Spanish La Liga 2, English Championship, EFL League One/Two, Bundesliga 2, MLS, UEFA Champions League (+Qualification), UEFA Europa League, UEFA Conference League, UEFA Nations League, UEFA Euro (+Qualification), FIFA World Cup (+Qualifiers), FIFA Club World Cup, FIFA Women's World Cup, UEFA Women's CL, Copa América, Copa Libertadores, Copa Sudamericana, CONCACAF Gold Cup, CONCACAF Leagues Cup, Africa Cup of Nations, FA Cup, EFL Cup, DFB-Pokal, Copa del Rey, Coppa Italia, Coupe de France, Frauen-Bundesliga |
| 2 | **Cricket Test** | %20-30 (zaman dolma) | Test Matches (ICC International) |
| 3 | **Cricket Limited Overs** | Nadir (Super Over) | IPL, Big Bash (BBL), Caribbean Premier League (CPL), Pakistan Super League (PSL), SA20, T20 Blast, The Hundred, ODI, Asia Cup, ICC Champions Trophy, ICC World Cup, ICC Women's World Cup, International T20 |
| 4 | **Rugby League** | Nadir | NRL, NRL State of Origin |
| 5 | **Rugby Union** | Nadir | Six Nations, Premiership (UK) |
| 6 | **Boxing** | %3-5 (judges' draw) | Boxing (all events) |
| 7 | **MMA / UFC** | %1-2 (draw + no contest) | MMA (all promotions) |
| 8 | **AFL** | %1-2 | AFL |
| 9 | **NFL (Regular Season)** | %0.2 (OT tie) | NFL, NFL Preseason |
| 10 | **Handball** | Yaygın regular time | Handball-Bundesliga (Germany) |
| 11 | **Lacrosse** | Nadir | Premier Lacrosse League (PLL), NCAA Lacrosse |

### Önkoşullar (hepsi geçerli)
- [ ] v2 MVP en az **2 ay** stabil çalışmalı
- [ ] Non-draw sporlardan ≥ **100 resolved trade** verisi toplanmalı
- [ ] Bot pozitif EV veya breakeven göstermeli
- [ ] Scanner'da "end in a draw" bloğu kaldırılmalı (Faz 2 giriş)
- [ ] Matching sistemi 3 tarafı tanımalı (Faz 2 giriş)

### Not
- Her branşın kuralları ayrı bir SPEC olarak yazılacak (TODO-001/1 Soccer, TODO-001/2 Cricket Test, vb.)
- Kullanıcı "Soccer'in draw kurallarını ekleyelim" dediğinde → yukarıdaki liste çıkartılır, kural çalışması başlar
- Pozisyon boyutlama: tüm branşlarda **confidence bazlı** (A=%5, B=%4) — Kelly YOK

---

## TODO-002: Sharp-Only Anchor — Non-Sharp Dilution Kuralı (Veri Bekliyor)

- **Durum**: DEFERRED — veri biriktirilecek, sonra karar verilecek
- **Tarih**: 2026-04-19
- **Öncelik**: P2 — potansiyel edge keskinleştirmesi, ama hacim kaybı riski var

### Kullanıcı Hipotezi

Polymarket anchor şu an tüm bookmaker'lardan weighted consensus ile hesaplanıyor
(sharp 3.0×, reputable 1.5×, standard 1.0× — bkz. TDD §6.2). Kullanıcı sezgisi:
**sharp book'lar (Pinnacle, Betfair Exchange, Matchbook, Smarkets) en isabetli
forecaster'lar; reputable+standard bookmaker'lar "public bias" taşıyor ve sharp
sinyalini dilute ediyor olabilir**. Özellikle sharp book sayısı azken (tek sharp +
birkaç reputable karışımı), non-sharp dilution sharp edge'ini bozuyor olabilir.

### Önerilen Kural

| Sharp book sayısı | Anchor hesabı |
|---|---|
| ≥3 | Normal consensus (herkes dahil, mevcut davranış) |
| 2 | Sadece sharp anchor (reputable/standard yok sayılır) |
| 1 | **Skip** (tek-book outlier riski yüksek) |
| 0 | TBD — ya mevcut B-tier akışı ya skip (kullanıcıya sorulacak) |

### Neden Beklemede

Kural mantıklı ama **veriyle doğrulama şart**. Tradeoff net değil:

- **Lehine**: 2-sharp maçlarda anchor keskinleşir → bazı yeni edge'ler açılabilir.
  Ayrıca 1-sharp maçlarda outlier trade riski azalır.
- **Aleyhine**: Polymarket'te 1-sharp maçlar çok yaygın (niş turnuvalar,
  küçük ligler). Skip kuralı trade hacmini ciddi düşürebilir. Ayrıca ≥3 sharp
  durumunda non-sharp'lar hâlâ outlier koruması sağlıyor — tamamen çıkarmak
  yılda 2-3 hatalı trade'e açık hale getirebilir.

### Karar İçin Gereken Analiz (trade_history + skipped_trades biriktiğinde)

1. Şu ana kadar trade'lerin sharp-sayısı dağılımı (1, 2, ≥3)?
2. 2-sharp maçlarda non-sharp dilution ortalama kaç basis-point anchor'ı kaydırmış?
3. **Kritik**: 1-sharp maçlarda PnL pozitif mi negatif mi? Pozitifse skip kuralı
   para kaybettirir; negatifse kural net kazanç.
4. 2-sharp maçlarda "sharp-only anchor" ile "mevcut consensus anchor" arasındaki
   edge farkının işareti ve dağılımı?

### Önkoşullar

- [ ] En az **50 resolved trade** biriktirilmeli (şu an yeterli değil)
- [ ] Analiz scripti yazılıp 4 soruya sayısal cevap üretilmeli
- [ ] Sonuçlara göre: kuralı spec'e yaz / modifiye et / iptal et

### İlgili Dosyalar (kural uygulanırsa değişecekler)

- `src/domain/bookmaker_probability.py` — anchor hesaplama mantığı
- `src/domain/confidence_grading.py` — sharp-sayısı bazlı tier kuralı
- `src/strategy/entry_gate.py` — 1-sharp skip kuralı
- `TDD.md` §6.1, §6.2 — formül + "neden" notu güncelleme
- `config.yaml` — varsa yeni eşik parametresi

---

## TODO-003: CricAPI Paid Tier Upgrade

- **Durum**: DEFERRED — v1 cricket ile free tier (100/gün) ile başlanıyor
- **Tarih**: 2026-04-19
- **Öncelik**: P2 — cricket hacmi arttığında, özellikle ODI eklerken gerekli

### Bağlam

SPEC-011 cricket integration CricAPI free tier (100 hit/gün) ile başladı.
T20 için yeterli (1 maç ≈ 42 poll), ama:
- ODI (8 saat maç): tek maç ≈ 96 poll — limit dolar
- 3+ eşzamanlı T20: limit aşılır
- Limit dolduğunda: cricket entry'ler o günlük skip (skip_reason: `cricapi_limit_exhausted`)

### Opsiyonlar

1. **CricAPI Standard — ~$10/ay, 1000+ hit/gün**
   - ODI dahil rahatça 7 cricket ligi
   - Return on investment: ~1-2 cricket trade/ay + 10$ kapatır

2. **CricAPI Basic — ~$5/ay** (fiyat/quota kontrol gerekli)
   - Mid-tier. $5/500 hit gibi olabilir. Site'da kontrol edilecek.

### Önkoşul
- Cricket v1 (SPEC-011) 2-4 hafta canlı çalıştıktan sonra
- Günlük `cricapi_limit_exhausted` skip sayısı > 2 ise upgrade zorunlu
- Aylık cricket profit > $20 ise upgrade kendini öder

### Uygulama
- `config.yaml` → `cricket.api_key` env'den okunuyor, sadece key değişiyor
- Daily limit config'i güncelle (1000 veya 500 hit)
- Kod değişikliği minimal (hit tracking zaten var)

---

## TODO-004: [sonraki eklenecekler]
