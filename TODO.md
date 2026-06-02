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

## TODO-002: Tennis Re-Enable Test Restoration

- **Durum**: PARKED
- **Tarih**: 2026-05-05
- **Sebep**: SPEC-A5 (tennis kapatma) sırasında `_TENNIS_SPONSOR_ALIASES` için 4 test silindi:
  BMW Open / Porsche / Barcelona / sponsor→city eşleştirmeleri.
  Tennis tekrar açılırsa bu testler restore edilmeden SPEC-A5 erken-return'u kaldırılmamalı —
  yoksa sponsor-aliasing regresyonu sessizce kayar.
- **Önkoşul**: Tennis re-enable kararı verildiğinde:
  1. `git show 5b56500^ -- tests/unit/strategy/enrichment/` ile silinen testleri çıkar
     (parent commit `5b56500`'in bir öncesi).
  2. Testleri restore et, yeşile çek.
  3. Sonra `src/strategy/enrichment/sport_key_resolver.py` içindeki erken-return'u kaldır.

---

## TODO-003: scripts/reboot.py 415 satır — ARCH_GUARD Kural 3 (max 400) ihlali

**Durum:** DEFERRED
**Sebep:** Pre-existing ihlal (2026-05-22'de fark edildi). Reboot fix kapsamında 5 satır azaltıldı (420→415) ama hâlâ üzerinde.
**Önkoşul:** Yok, ne zaman olsa bölünebilir.
**Öneri:** `scripts/reboot.py`'i ikiye böl — örn `scripts/reboot_actions.py` (kill/clear/archive/start) + `scripts/reboot.py` (CLI + main, ince ana dosya). Mevcut testler patch yollarını günceller.

---

## TODO-004: MLB Bullpen Rates Aggregation (Statcast → leverage tier)

- **Durum**: DEFERRED — SPEC-S Faz B kapsamı dışı bırakıldı
- **Tarih**: 2026-05-23
- **Önkoşul**: Statcast pybaseball erişimi (var); MLB Stats API team roster fetch (yeni method gerek)

### Bağlam
SPEC-S Faz B'de engine'e opt-in bullpen interface eklendi (`team_bullpen_rates: dict | None`, default `None`). Engine interface hazır ama factory `None` geçiyor — yani bullpen seçimi şu an aktif değil. Bullpen rates'i gerçek veriyle doldurmak için takım-bazlı leverage tier aggregation gerek.

### Yapılacak
1. **Statcast aggregation method** — `StatcastClient.get_team_bullpen_rates(team_id, season) -> dict[str, dict[str, float]]` (her leverage tier için PA outcome rates: middle/setup/closer)
2. **Stats API team roster** — `StatsApiClient.get_team_roster(team_id, season) -> list[pitcher_ids_with_role]` — Stats API'de team roster endpoint var; her pitcher'ın "Reliever" rolü ve leverage tier (CSW%/leverage index) filtre edilir
3. **Bullpen rates cache** — pahalı fetch (her takım × her sezon × 3-4 leverage pitcher), günlük TTL cache gerek
4. **Factory'de wiring** — `MlbSubmarketEngine(team_bullpen_rates=BullpenRatesProvider(statcast, statsapi))` lazy loader veya pre-loaded dict

### Etki
Bullpen aktive olunca inning 6+'da gerçekçi pitcher rotasyonu → totals/run-line/moneyline edge'leri %3-7 daha doğru olmalı. Şu an starter 9 inning varsayımı altında engine bullpen-iyi takımları (Phillies, Yankees) underestimate, bullpen-zayıf takımları (Rockies) overestimate ediyor olabilir.

### Tahmini Süre
1-2 hafta (data fetch + cache + integration test).

---

## TODO-005: `mlb_submarket_engine.py` 400+ satır — slug parser'ı ayrı modüle çıkar

- **Durum**: DEFERRED
- **Tarih**: 2026-05-24
- **Önkoşul**: Yok

### Bağlam
SPEC-X Task 2 sonrası `src/strategy/entry/mlb_submarket_engine.py` 412 satır (ARCH_GUARD Kural 3 — 400 satır limiti aşıldı). Pre-existing ihlal, SPEC-X +7 satır eklemiş. Code-reviewer (Task 2) bu konuyu işaret etti.

### Öneri
Slug parser'ı yeni modüle çıkar: `src/strategy/entry/mlb_slug_parser.py` — `_parse_slug_static` + üç regex sabiti. Pure static. Engine import eder.

### Tahmini Süre
30 dakika (saf refactor + test path güncellemesi).

---

## TODO-006: SPEC-Y7/Y8 dokümantasyon yarım — DECISIONS güncellemesi ve `test_repo_config_yaml_parses` fix

- **Durum**: DEFERRED — kullanıcının diğer in-flight SPEC'i
- **Tarih**: 2026-05-24
- **Önkoşul**: SPEC-Y7/Y8 kararlarının tamamlanması

### Bağlam
Session başında `config.yaml` + `DECISIONS.md` + bazı kod dosyaları M durumda idi (SPEC-Y7 `mlb_submarket.enabled: false` + SPEC-Y8 `scanner.max_markets_per_cycle: 300 → 500` + tennis allowed_sport_tags kaldırma). Bu değişiklikler hâlâ uncommitted. Ayrıca `tests/unit/config/test_settings.py::test_repo_config_yaml_parses` tennis tag silinmesinden dolayı FAIL veriyor.

### Yapılacak
- SPEC-Y7/Y8 kararlarını DECISIONS.md'ye temiz commit
- `test_repo_config_yaml_parses` testini güncelle (tennis assertion'ı kaldır veya conditional yap)

---

## TODO-007: archive_audit_logs trigger forensic logger — ✅ KATMAN A+B+C DONE 2026-06-03

- **Durum**: KATMAN A+B+C DONE (kalıcı çözüm uygulandı). Forensic gözlem aşaması açık.
- **Tarih**: 2026-05-25 (başlangıç) → 2026-06-03 (kalıcı çözüm)

### Çözüm (SPEC-Z8 2026-06-03)
**Katman A — yara bandı**: `scripts/reboot.py _split_trade_history` `write_text("")` yıkıcı satırı kaldırıldı. Keep boş olsa bile audit dokunulmaz. Mistik scheduler hâlâ tetiklese bile defter ölmez.

**Katman B — forensic JSONL logger**: print() detached subprocess'te kayboluyordu (stdout=DEVNULL). Yeni `_write_archive_forensic` `logs/runtime/archive_forensic.jsonl`'e yazar: ts_utc, pid, parent process (psutil), open_cids sample, audit_files, TÜM stack zinciri (inspect.stack filtresiz). 1-2 saat gözlem sonrası mistik çağırıcı belli olur → kaldırılır → tüm forensic temizliği yapılır.

**Katman C — defansif**: Her split öncesi `.bak.before_split_<timestamp>` yedek.

### Sonraki adım (forensic gözlem)
1. Bot 1-2 saat çalışsın
2. `logs/runtime/archive_forensic.jsonl` incelenir
3. Mistik çağırıcı (parent.cmdline + stack[0]) tespit edilince:
   - Çağrı kaynağı kaldırılır (cron / scheduler / bot içi gizli call)
   - `_write_archive_forensic` ve forensic dosya silinir (TODO-007 tam kapanır)

### Etki
Audit silinmesi kaynaklı orphan exit / "Branches: UNKNOWN" / Realized PnL drift dashboard semptomları KÖKÜNDEN durdu. Bot trade etmeye devam ediyor, defter sağlam. Lab v2 stale lock kalıntısı da temizlendi.

---

## TODO-008: BSL/Lega/VTB HTML Parser İmplementasyonu (SPEC-EUROBASKET-001 kalan kısım) — ✅ DONE 2026-06-03

- **Durum**: DONE — 3 paralel subagent ile yazıldı, `/teams` API endpoint ile cross-check. Bkz DECISIONS SPEC-EUROBASKET-001 ikinci pass notu.
- **Önceki tahmin**: DEFERRED — placeholder scraper'lar var (`src/infrastructure/data/basketball/{bsl,lega,vtb}_scraper.py`), HTML parse `NotImplementedError` fırlatır
- **Tarih**: 2026-06-02
- **Öncelik**: P2 — Liga Endesa scraper aktif, diğer 3 ligin Polymarket market hacmi gözlemlenince öncelik artar
- **Önkoşul**: Her lig için sezon içi aktif market gözlemi + canlı HTML doğrulaması

### Yapılacaklar (her lig için ayrı sprint)

| Lig | Kaynak site | Slug prefix (tahmin) | Takım sayısı |
|---|---|---|---|
| Turkey BSL | tbf.org.tr veya tblstat.com | `bkbsl` | 16 |
| Italy Lega | legabasket.it | `bklega` | 16 |
| VTB | vtb-league.com | `bkvtb` | 12 |

### Implementasyon adımları (referans: `acb_scraper.py`)
1. Polymarket gamma API'den gerçek slug prefix doğrula (`tag_slug=turkey-bsl` vs)
2. Resmi site calendario/results sayfasını curl ile çek (raw HTML)
3. BeautifulSoup ile takım isimleri + skorlar + tarih CSS selector'larını bul
4. `_fetch_html` + `_parse_teams` + `_parse_games` override et
5. Tarih format helper (Türkçe/İtalyanca/Rusça aylar)
6. `_NAME_TO_ABBR` dict (resolver `_BSL_TEAMS`/`_LEGA_TEAMS`/`_VTB_TEAMS` ile hizalı)
7. Unit test: fixture HTML + parse doğrulaması (`test_acb_scraper.py` paralel)
8. `config.yaml` `allowed_sport_tags` + `enabled_leagues`'a lig ekle
9. `basketball.leagues.<lig>` parametreleri (Euroleague baseline)
10. Bot reload + log doğrulama

### NO_DATA_NO_TRADE devrede
Şu an placeholder NotImplementedError fırlattığı için bu liglerin slug'ı dispatch'e gelirse model `MODEL_TEAM_NOT_IN_RATINGS` fail döner, trade YAPILMAZ. Telegram alert atılmaz çünkü scraper hiç çağrılmıyor — `enabled_leagues`'a eklenmemiş. Parser yazılınca aktive edildiğinde fail kayıtları başlar, 3-strike sonra critical alert.

---

## TODO-009: [sonraki eklenecekler]
