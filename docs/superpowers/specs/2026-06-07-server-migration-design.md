# Sunucuya Taşıma — Tasarım Belgesi (Server Migration Design)

> **Tarih:** 2026-06-07
> **Durum:** TASLAK — kullanıcı onayı bekliyor
> **Hedef:** Botu kişisel bilgisayardan bağımsız, 7/24 çalışan, sadece sahibinin eriştiği, güvenli, bakımı az bir buluta taşımak — **sıfır teknik borç**.
> **Not:** Bu bir TASARIM belgesidir; kod değiştirmez. Kod değişiklikleri uygulama (implementation) aşamasında, ARCHITECTURE_GUARD self-check ile yapılır.

---

## 0. Sade Özet (teknik olmayan sahibi için)

Bugün bot senin bilgisayarında çalışıyor; bilgisayar kapanınca/internet gidince duruyor. Bunu, bulutta hiç kapanmayan kiralık bir bilgisayara ("sunucu") taşıyoruz. Sonuç:

- Bot **7/24 çalışır** — senin cihazların kapalı olsa da.
- Panoya ve kontrole **dünyanın her yerinden, sadece sen** ulaşırsın (pano internette hiç görünmez; senin cihazlarına özel bir tünelle bağlanır).
- **Telegram'dan** hem uyarı alırsın hem komut verirsin (dur / trade alma / durum sor).
- Bir terslik olursa bot **kendi kendine yeniden başlar** ve sana **Telegram'dan haber** gelir.
- Sen **buradan, benimle** geliştirmeye devam edersin; değişikliği **tek komutla** sunucuya gönderirim.

İyi haber: Kod taramasında çıkan sonuç — sistem **~%90 hazır**. Sadece birkaç "sunucuda çalışsın diye" düzeltme gerekiyor (aşağıda Bölüm 5). Bunlar bilinçli olarak şimdi çözülecek ki sonradan borç kalmasın.

---

## 1. Hedefler ve Kapsam Dışı

### Hedefler
1. Bot 7/24, kişisel bilgisayardan ve ev internetinden **tamamen bağımsız** çalışsın.
2. Pano + kontrol **sadece sahibine**, her yerden güvenli erişilebilir olsun (genel internete **sıfır açık kapı**).
3. Telegram: anlık uyarı + uzaktan komut (dur / yeni trade alma / durum).
4. Çökme/hata durumunda **otomatik yeniden başlatma** + Telegram bildirimi.
5. **Veri kaybı = 0**: açık pozisyonlar, işlem geçmişi, güvenlik durumu kalıcı diskte + yedekli.
6. Geliştirme yerelde kalsın; güncelleme **tek komutla** sunucuya aksın.
7. **Sıfır teknik borç**: taşıma için gereken kod düzeltmeleri düzgün yapılsın, hack bırakılmasın.

### Kapsam Dışı (YAGNI)
- Çoklu sunucu / yük dengeleme (tek bot, tek sunucu yeter).
- Halka açık web sitesi / çok kullanıcılı erişim.
- Anahtar yenileme (anahtarlar hiç sızmadı — gerek yok).
- Strateji/mantık değişikliği (taşıma davranışı **birebir** korur).

---

## 2. Hedef Mimari

```
   [Senin telefonun / bilgisayarın]                [Bulut Sunucu — Linux VPS]
            |                                       ┌──────────────────────────┐
            |  Tailscale özel tünel (sadece         │  systemd: polymarket-bot │  ← 7/24 bot süreci
            |  senin cihazların görür)              │  systemd: polymarket-dash│  ← pano (Gunicorn)
            +─────────────────────────────────────► │  Tailscale (özel ağ)     │
            |                                       │  ufw güvenlik duvarı     │  ← tüm genel portlar kapalı
            |  Telegram (uyarı + komut)             │  /opt/polymarket-agent   │  ← kod (GitHub'dan)
            +◄────────────────────────────────────► │  kalıcı disk: data/ logs/│  ← durum + yedek
                  api.telegram.org                  └──────────────────────────┘
                                                              │  dışa giden HTTPS/WSS
                                                              ▼
                          Polymarket · The Odds API · ESPN · Gamma · (Telegram)
```

**İki süreç (bugünküyle aynı ayrım):**
- **Bot süreci** (`src/main.py`): maçları izler, işlem yapar, durumu `data/`'ya yazar. Dışarıya port açmaz (sadece dışa bağlanır).
- **Pano süreci** (`src/presentation/dashboard`): `data/`'yı okur, web arayüzü sunar. Sadece Tailscale üzerinden, localhost'ta dinler.

---

## 3. Barındırma ve Altyapı Kararları

| Karar | Seçim | Gerekçe |
|---|---|---|
| Sunucu tipi | Bulut VPS (sanal sunucu) | 7/24 stateful bot için en sağlam/öngörülebilir (PaaS değil — uyku/veri sorunları olur) |
| Sağlayıcı | **Hetzner CX22** (kullanıcı "sen karar ver" dedi) | Ucuz (~€4–6/ay), yüksek uptime, AB veri merkezi |
| İşletim sistemi | Ubuntu 24.04 LTS | Uzun destek, Python 3.12 standart, en yaygın → en az sürpriz |
| CPU/RAM | 2 vCPU / 4 GB | Bot + pano + ara sıra model üretimi (tennis ratings) için rahat |
| Disk | 40 GB SSD (kalıcı) | `data/` + `logs/` + arşiv için fazlasıyla yeter |
| Süreç yönetimi | **systemd** (2 servis) | Otomatik başlat, çökünce yeniden başlat, log toplama — Linux standardı |
| Pano sunucusu | **Gunicorn** (Flask dev server DEĞİL) | Üretim kalitesi; dev server tek kullanıcıda bile borç sayılır |

---

## 4. Güvenlik Modeli — "Sadece Sen"

Tasarımın çekirdeği: **panonun genel internette hiçbir açık kapısı olmaması.**

1. **Tailscale özel ağ (WireGuard tabanlı):** Sunucuya ve telefonuna/bilgisayarına Tailscale uygulaması kurulur, aynı hesapla giriş yapılır. Pano yalnızca bu özel ağ içinden (`100.x.x.x` Tailscale IP) erişilebilir. Genel internetten **adresi bile bulunamaz**. Kurulum = uygulama kur + giriş yap (teknik olmayan dostu).
2. **Güvenlik duvarı (ufw):** Sunucuda tüm genel gelen portlar kapalı. Sadece (a) SSH'i Tailscale üzerinden, (b) pano portunu Tailscale üzerinden açarız. Dışarıya giden bağlantılar (Polymarket, Telegram vb.) serbest.
3. **SSH anahtarla giriş, şifre kapalı**, root login kapalı, ayrı `polybot` kullanıcısı (bot root değil).
4. **Gizli anahtarlar** sunucuda `.env` dosyasında, `chmod 600` (sadece bot kullanıcısı okur), **asla** git'e girmez (yeni `.gitignore` kuralı bunu garantiler).
5. **Otomatik güvenlik güncellemeleri** (`unattended-upgrades`) — işletim sistemi yamaları kendiliğinden kurulur (ayda ~0 dakika senin işin).
6. **Pano kimlik doğrulaması (ikinci kat):** Tailscale tek başına yeterli ama ek olarak panoya basit bir parola koyabiliriz (opsiyonel — Bölüm 12).

> Sonuç: Saldırı yüzeyi neredeyse sıfır. Pano dışarıdan görünmez; sunucuya sadece senin Tailscale cihazların girer.

---

## 5. Kod Sertleştirme — Edge Case'ler (sıfır-borç düzeltmeleri)

Kod taramasında çıkan, **sunucuda çalışınca bug/borç yaratacak** noktalar. Hepsi şimdi, düzgün çözülecek. (Uygulama aşamasında ARCH_GUARD + TDD ile.)

| # | Edge case | Bugünkü davranış | Risk (sunucuda) | Çözüm | Öncelik |
|---|---|---|---|---|---|
| E1 | **Headless LIVE onayı** — `src/main.py:38` `input("CONFIRM LIVE")` | Klavyeden onay bekler | Sunucuda klavye yok → bot **sonsuza kadar takılır** | `sys.stdin.isatty()` kontrolü; klavye yoksa `POLYMARKET_CONFIRM_LIVE=1` ortam değişkeniyle onay | 🔴 P0 |
| E2 | **Düzgün kapanma sinyali** — agent'ta SIGTERM/SIGINT yok | Sadece `atexit` ve Telegram `/stop` | systemd "dur/yeniden başlat" derken **anlık işlem kaybı** + bayat kilit + Telegram bildirimi gitmez | `signal.SIGTERM`/`SIGINT` → `agent.request_stop()` (mevcut graceful yol) bağla | 🔴 P0 |
| E3 | **Pano üretim sunucusu** — Flask `app.run()` | Geliştirme sunucusu | Tek kullanıcıda bile kararsız/borç | **Gunicorn** ile servis; systemd `polymarket-dash` | 🔴 P0 |
| E4 | **Kalıcı durum diski** — `data/`, `logs/` | Yerel klasör | Sunucu yeniden kurulursa **pozisyon/geçmiş kaybı** | Kalıcı diske bağla; `positions.json`, `circuit_breaker_state.json`, `trade_events.jsonl` kritik | 🔴 P0 |
| E5 | **Bayat süreç kilidi** — SIGKILL'de `agent.pid` kalır | Açılışta üzerine yazıyor (kısmî) | Nadiren çift örnek yarışı | systemd `ExecStartPre=rm -f logs/agent.pid` + `TimeoutStopSec=30` | 🟡 P1 |
| E6 | **reboot.py Windows'a yaslı** — `taskkill`/`wmic` (Linux yedeği var) | Çift kodlu, Linux dalı mevcut | Düşük; ama "yeniden başlat" artık systemd işi | reboot.py yerine `systemctl restart` sarmalayıcısı; reboot.py dev-only kalır | 🟡 P1 |
| E7 | **Sabit Windows yolları** — `scripts/basket_*.py` `c:/Users/...` | Tanı (diagnostic) script'leri | Sadece o script'ler Linux'ta patlar (çekirdek değil) | Yolları `Path(__file__)`'a göre parametreleştir | 🟡 P1 |
| E8 | **Atomik yazma yedeği** — `json_store.py` PermissionError dalı non-atomik | Sadece Windows/OneDrive'da tetikleniyor | Linux ext4'te atomik yol çalışır → **sorun ortadan kalkar**; yine de yedek dalı sağlamlaştır | Linux'ta sorun yok; not olarak izlenecek | 🟢 P2 |
| E9 | **Derleme araçları** — `rapidfuzz`, `numpy` C-derleme | Windows'ta wheel hazır | İlk kurulumda `gcc` yoksa pip patlar | Sunucuya `build-essential python3.12-dev` kur | 🟡 P1 (kurulum) |
| E10 | **Build edilen model verisi** — `tennis_ratings*.json`, `tennis_calibration.json` | Yerelde üretilmiş | Sunucuda yoksa tennis trade'i bozulur / health alarmı | İlk kurulumda mevcut dosyaları kopyala **veya** `scripts.build_tennis_ratings` çalıştır | 🟡 P1 |

> Bu 10 maddenin hepsi yol haritasının uygulama planına girer. Hiçbiri "sonra hallederiz" değil — **sıfır borç** demek bu.

---

## 6. Telegram Kontrol Genişletmesi (uyarı + komut)

**Zaten çalışan (kod taramasıyla doğrulandı):**
- ✅ Giriş/çıkış uyarıları, açılış/kapanış bildirimi, sağlık alarmları (bayat fiyat, ardışık kayıp, scraper bozulması).
- ✅ `/stop` komutu → botu güvenle durdurur (`TelegramCommandPoller` arka plan thread'i).

**Eklenecek (kullanıcı "dur, trade alma" istedi — bu yeni komut gerektirir):**
| Komut | Davranış | Not |
|---|---|---|
| `/pause` | **Yeni trade almayı durdur**, ama açık pozisyonların yönetimini (çıkış/SL) sürdür | YENİ — entry gate'e "duraklat" bayrağı |
| `/resume` | Yeniden trade almaya başla | YENİ |
| `/status` | Açık pozisyon sayısı, günlük PnL, mod, son cycle özeti | YENİ (kısa özet) |
| `/stop` | Mevcut — botu tamamen durdur | VAR |

> `/pause` mantığı: bot çalışmaya devam eder, çıkışları yönetir, ama **yeni giriş açmaz**. Bayrak `data/`'da kalıcı (yeniden başlatmada korunur). Bu, "aklım kalmasın, gerekirse uzaktan kıs" hedefinin tam karşılığı.

İsteğe bağlı (Bölüm 12): `daily_summary` (config'de var, kod eksik) — günlük özet mesajı.

---

## 7. Veri Kalıcılığı ve Yedekleme

**Kritik durum dosyaları (kaybı = para/pozisyon kaybı):**
- `data/positions.json` — açık pozisyonlar, bankroll (her 5 sn yazılır, atomik)
- `data/circuit_breaker_state.json` — kayıp limitleri/cooldown (atomik)
- `logs/audit/trade_events.jsonl` — **tek gerçek kaynak** (append-only; pozisyonlar bundan yeniden kurulabilir)

**Yeniden üretilebilir (kritik değil):** `stock_queue.json`, `blacklist.json`, model cache'leri, `bot_status.json`.

**Yedekleme tasarımı:**
1. `data/` + `logs/audit/` **kalıcı diskte** (sunucu yeniden kurulsa bile durur).
2. **Saatlik yerel yedek:** kritik dosyaların zaman damgalı kopyası (cron) → `backups/`.
3. **Günlük dış yedek:** kritik dosyalar + `.env` (şifreli) → ayrı bir konuma (örn. ikinci sunucu diski veya nesne depolama). Detay Bölüm 12'de karar.
4. `.tmp` dosya kontrolü: yarım kalmış yazma tespiti için cron uyarısı.
5. Aylık arşiv: eski `equity_history`/`trade_events` sıkıştırılır (disk şişmesin).

---

## 8. Dağıtım ve Güncelleme Akışı (yerel → GitHub → sunucu)

**Geliştirme yerelde kalır. Sunucu sadece çalıştırır.** Akış:

```
[Senin bilgisayarın]  ──(1) değiştir + test (pytest)──►  [GitHub]  ──(2) sunucu çeker──►  [Sunucu]
                                                                        (3) systemctl restart
```

**Tek komutluk güncelleme (senin için sadeleştirilmiş):** Sunucuda bir `deploy.sh`:
1. `git pull` (GitHub'dan son sürüm)
2. `pip install -r requirements.txt` (bağımlılık değiştiyse)
3. `pytest -q` (sunucuda da testler geçsin — geçmezse dağıtımı durdur)
4. `systemctl restart polymarket-bot polymarket-dash`
5. Telegram'a "✅ güncellendi (commit abc123)" bildir

Sen bana "sunucuya gönder" dersin; ben `deploy.sh`'i tetiklerim. Yarım/bozuk güncelleme canlıya **asla** geçmez (test geçmezse durur).

---

## 9. Taşıma Kesişi (Cutover) — Sıfır Riskli Geçiş

Para riskine girmeden, davranış birebir doğrulanarak:

1. **Sunucu kur** (Bölüm 3–4) — bot henüz çalışmıyor.
2. **Kod + veri + .env** sunucuya taşı; bağımlılıkları kur (E9), model verisini koy (E10).
3. **E1–E7 kod düzeltmeleri** uygulanmış sürümle başla.
4. **PAPER modda** sunucuda çalıştır; aynı anda evdeki sistemle **yan yana** karşılaştır (1–2 gün): aynı maçlarda aynı kararlar mı?
5. `pytest` sunucuda tam geçiyor + dry_run/paper temiz → yeşil ışık.
6. **Otoriteyi devret:** sunucu **PAPER modda** evdekiyle aynı kararları verdiği doğrulanınca, **evdeki botu kapat** — sunucu tek otorite olur. (Mod PAPER kalır — şu an nasılsa öyle. Gelecekte LIVE istenirse E1 ortam değişkeniyle güvenli onay hazır olacak.)
7. İlk 24 saat yakın izleme (Telegram + pano).

> Kural: Evdeki çalışan bota **cutover'a kadar el sürülmez**; tek otorite o kalır. Bir aksilik → eve geri dön, kayıp yok. (Bkz. memory: çalışan bota dokunma.)

---

## 10. İzleme, Otomatik Yeniden Başlatma, Otomatik Güncelleme

- **systemd `Restart=on-failure`**: bot çökerse 10 sn'de otomatik yeniden başlar (sonsuz döngüye karşı `StartLimitBurst=3`).
- **Çökme bildirimi**: yeniden başlamada Telegram'a "🔄 bot yeniden başladı" (E2 graceful + boot mesajı).
- **Uptime izleme**: hafif bir "ben hayattayım" sinyali (bot N dakikadır cycle atmıyorsa Telegram uyarısı) — mevcut HealthMonitor genişletilir.
- **Otomatik OS güncelleme**: `unattended-upgrades` (güvenlik yamaları).
- **Log yönetimi**: `journald` + mevcut `RotatingFileHandler`; aylık arşiv.

---

## 11. Edge Case Sicili (özet kontrol listesi)

Taşımada bug çıkarabilecek **tüm** noktalar ve durumu:

- ✅ **Zaman dilimi**: kod zaten UTC-aware (sunucu UTC'de sorunsuz).
- ✅ **Dosya yolları**: `pathlib` her yerde (Linux uyumlu).
- ✅ **Dosya kodlaması**: her yerde açık `utf-8`.
- ✅ **Süreç yönetimi**: reboot.py zaten Linux dallı (yine de systemd'ye taşınıyor — E6).
- 🔧 **E1** headless LIVE onayı → çözülecek.
- 🔧 **E2** SIGTERM/SIGINT graceful → çözülecek.
- 🔧 **E3** Gunicorn → çözülecek.
- 🔧 **E4** kalıcı disk → kurulumda.
- 🔧 **E5** bayat kilit → systemd ExecStartPre.
- 🔧 **E6** systemd restart sarmalayıcı → çözülecek.
- 🔧 **E7** sabit Windows yolları (diagnostic) → parametreleştirilecek.
- 🟢 **E8** atomik yazma → Linux'ta zaten sorunsuz.
- 🔧 **E9** derleme araçları → kurulumda.
- 🔧 **E10** model verisi → kurulumda kopyala/üret.
- 🆕 **Telegram** `/pause` `/resume` `/status` → eklenecek.
- 🔒 **Güvenlik**: Tailscale + ufw + SSH-anahtar + .env 600 + otomatik yama.
- 💾 **Yedek**: saatlik + günlük + atomik + arşiv.

---

## 12. Kararlar (kullanıcı onayladı — 2026-06-07)

1. **Sağlayıcı:** ✅ **Hetzner** (kullanıcı "sen karar ver" dedi).
2. **Sunucudaki mod:** ✅ **PAPER** — şu an nasılsa öyle. Sunucu evdekini birebir mirror'lar, gerçek para yok. (Cutover'da da PAPER kalır.)
3. **Pano ikinci parola:** ✅ **Eklenecek** (Tailscale'in üstüne basit parola — ekstra güvenlik, zararsız).
4. **Dış yedek hedefi:** ✅ **Başlangıçta sunucu-içi + günlük indirme**; ihtiyaç olursa nesne depolamaya büyütülür.
5. **Günlük Telegram özeti:** ❌ **İstenmedi** — sadece olay bazlı uyarılar + `/status`.

---

## 13. Maliyet Özeti (yaklaşık)

| Kalem | Aylık |
|---|---|
| VPS (Hetzner CX22 / DO Basic) | €4–6 / $6–12 |
| Tailscale (kişisel kullanım) | Ücretsiz |
| Telegram | Ücretsiz |
| Yedekleme (sunucu içi) | Dahil |
| **Toplam** | **~$6–12 / ay** |

---

## Sonraki Adım

Bu tasarım onaylanınca → **uygulama planı** (writing-plans) yazılır: her kod düzeltmesi (E1–E10 + Telegram komutları) için adım adım, test-önce (TDD) görevler; sonra sunucu kurulum adımları; sonra cutover. Her kod görevi ARCHITECTURE_GUARD self-check ile yapılır.
