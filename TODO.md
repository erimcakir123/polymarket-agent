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

## TODO-002: [sonraki eklenecekler]
