# Plan 2 — Sunucu Kurulum Runbook (Server Provisioning)

> **Tür:** Ops runbook (kod değil — adım adım kurulum). Plan 1 (kod sertleştirme) TAMAM; bu plan o kodu gerçek sunucuda çalıştırır.
> **Hedef:** Hetzner VPS + Tailscale (sadece sen) + systemd (7/24) + Telegram + yedek + güvenli geçiş. **PAPER mod** (şu an nasılsa öyle).
> **Önkoşul:** Repo GitHub'da (✓), Plan 1 dalı `feature/server-readiness` (✓). Cutover'a kadar evdeki bot çalışmaya devam eder.

> **Komut gösterimi:** `[SEN]` = kullanıcının tarayıcıda/panelde yapacağı; `[BEN]` = SSH üzerinden birlikte çalıştıracağımız; `# yorum`.

---

## Faz 0 — Senin yapacakların (sadece bu kısım sende)

Teknik olmayan ama tıklamayla yapılır. Bittiğinde gerisini ben SSH ile hallederim.

1. **[SEN]** Hetzner Cloud hesabı aç: https://console.hetzner.cloud → kayıt + ödeme yöntemi.
2. **[SEN]** Yeni proje → "polymarket-bot".
3. **[SEN]** "Add Server":
   - Location: **Nuremberg** (veya Falkenstein) — AB.
   - Image: **Ubuntu 24.04**.
   - Type: **CX22** (2 vCPU / 4 GB) — Shared vCPU.
   - SSH key: **bana soracaksın** — ben senin bilgisayarında bir anahtar üreteceğim (Faz 1.0), onun "public" kısmını buraya yapıştıracaksın. (Ya da şimdilik parola ile aç, sonra anahtara geçeriz.)
   - Name: `polybot-01`.
   - "Create & Buy now".
4. **[SEN]** Sunucunun **IP adresini** bana ver (panelde görünür, örn. `203.0.113.45`).

> Bu 4 adım bitince "sunucu hazır, IP şu" de — gerisi otomatik.

---

## Faz 1 — Temel sunucu sertleştirme

### 1.0 SSH anahtarı (önce, yerelde)
- **[BEN]** Senin bilgisayarında anahtar üret (varsa atla):
  ```powershell
  ssh-keygen -t ed25519 -C "polybot" -f $env:USERPROFILE\.ssh\polybot_ed25519 -N '""'
  ```
- **[SEN]** `polybot_ed25519.pub` içeriğini Hetzner'e (Faz 0.3) yapıştır — VEYA ben ilk parola girişinde eklerim.

### 1.1 İlk giriş + sistem güncelleme
- **[BEN]** `ssh root@<IP>` (ilk sefer parola/anahtar).
- **[BEN]**
  ```bash
  apt update && apt -y upgrade
  apt -y install ufw fail2ban unattended-upgrades build-essential python3.12 python3.12-venv python3.12-dev git curl
  ```
  > `build-essential` + `python3.12-dev` = E9 (rapidfuzz/numpy derlemesi).

### 1.2 Ayrı kullanıcı (bot root çalışmaz)
- **[BEN]**
  ```bash
  adduser --disabled-password --gecos "" polybot
  mkdir -p /home/polybot/.ssh && cp ~/.ssh/authorized_keys /home/polybot/.ssh/
  chown -R polybot:polybot /home/polybot/.ssh && chmod 700 /home/polybot/.ssh && chmod 600 /home/polybot/.ssh/authorized_keys
  ```

### 1.3 SSH sıkılaştırma
- **[BEN]** `/etc/ssh/sshd_config.d/hardening.conf`:
  ```
  PermitRootLogin no
  PasswordAuthentication no
  ```
  ```bash
  systemctl restart ssh
  ```
  > Bundan sonra giriş: `ssh polybot@<IP>` (sadece anahtarla).

### 1.4 Otomatik güvenlik güncellemeleri (E: bakım azaltma)
- **[BEN]**
  ```bash
  dpkg-reconfigure -plow unattended-upgrades   # Enable: Yes
  ```

---

## Faz 2 — Tailscale (sadece sen erişirsin)

### 2.1 Sunucuya Tailscale
- **[BEN]**
  ```bash
  curl -fsSL https://tailscale.com/install.sh | sh
  tailscale up --ssh
  ```
  → Çıkan linki **[SEN]** tarayıcıda aç, Tailscale hesabınla onayla (Google/GitHub ile giriş — ücretsiz).
- **[BEN]** Sunucunun Tailscale IP'sini not et: `tailscale ip -4` (örn. `100.x.y.z`).

### 2.2 Senin cihazların
- **[SEN]** Telefonuna + bilgisayarına **Tailscale uygulaması** kur, aynı hesapla giriş yap. Artık `100.x.y.z`'ye sadece senin cihazların ulaşır.

### 2.3 Güvenlik duvarı — her şeyi kapat, sadece Tailscale'i aç
- **[BEN]**
  ```bash
  ufw default deny incoming
  ufw default allow outgoing
  ufw allow in on tailscale0          # Tailscale ağı içi serbest (SSH + pano)
  ufw --force enable
  ```
  > Genel internetten **hiçbir port açık değil**. Pano internette görünmez (E: "sadece sen").

---

## Faz 3 — Çalışma ortamı + kod

### 3.1 Repo'yu çek
- **[BEN]** (polybot olarak)
  ```bash
  cd /home/polybot
  git clone https://github.com/erimcakir123/polymarket-agent.git
  cd polymarket-agent
  git checkout feature/basketball-model-foundation   # canlı dal (Plan 1 merge sonrası buraya gelir)
  ```
  > Repo private ise: GitHub Personal Access Token veya deploy key ile clone. **[SEN]** GitHub'da bir "deploy key" eklersin (ben yönlendiririm).

### 3.2 Sanal ortam + bağımlılıklar
- **[BEN]**
  ```bash
  python3.12 -m venv .venv
  . .venv/bin/activate
  pip install --upgrade pip
  pip install -r requirements.txt          # E9: build-essential sayesinde rapidfuzz/numpy derlenir
  ```

### 3.3 Testler sunucuda da geçiyor mu (doğrulama)
- **[BEN]**
  ```bash
  pip install -e ".[dev]" 2>/dev/null || pip install pytest
  pytest -q                                 # Beklenen: ~1956 passed
  ```

---

## Faz 4 — Gizli anahtarlar + model verisi

### 4.1 .env (E: chmod 600)
- **[BEN]** `/home/polybot/polymarket-agent/.env` oluştur (içeriği **[SEN]** evdeki `.env`'den verirsin — ekrana yazılmaz, güvenli aktarılır):
  ```bash
  nano .env          # PRIVATE_KEY, ODDS_API_KEY, TELEGRAM_BOT_TOKEN, TELEGRAM_CHAT_ID, ...
  chmod 600 .env
  ```
  > PAPER modda PRIVATE_KEY boş kalabilir. TELEGRAM_* dolu olmalı (uyarı+komut için).

### 4.2 Model verisi (E10)
- **[BEN]** Tenis ratings dosyaları gerekiyor:
  ```bash
  python -m scripts.build_tennis_ratings     # ~10-15 dk (web scrape) → data/tennis_ratings*.json
  ```
  > VEYA evdeki `data/tennis_ratings*.json` + `tennis_calibration.json` dosyalarını **[SEN]** kopyalarsın (daha hızlı).

### 4.3 Kalıcı dizinler (E4)
- **[BEN]** `data/` ve `logs/` zaten repo kökünde, sunucu diskinde kalıcı. (CX22 diski kalıcı — ayrı mount gerekmez.)

---

## Faz 5 — systemd servisleri (7/24)

### 5.1 Bot servisi (E2 graceful + E5 lock temizliği)
- **[BEN]** `/etc/systemd/system/polymarket-bot.service`:
  ```ini
  [Unit]
  Description=Polymarket Trading Bot
  After=network-online.target
  Wants=network-online.target
  StartLimitIntervalSec=300
  StartLimitBurst=3

  [Service]
  Type=simple
  User=polybot
  WorkingDirectory=/home/polybot/polymarket-agent
  Environment=PYTHONUNBUFFERED=1
  ExecStartPre=/bin/rm -f logs/agent.pid
  ExecStart=/home/polybot/polymarket-agent/.venv/bin/python -m src.main --mode paper
  Restart=on-failure
  RestartSec=10
  KillSignal=SIGTERM
  TimeoutStopSec=30
  StandardOutput=journal
  StandardError=journal

  [Install]
  WantedBy=multi-user.target
  ```
  > `ExecStartPre rm agent.pid` = E5 (bayat kilit). `SIGTERM`+`TimeoutStopSec=30` = E2 graceful (Plan 1'de eklendi). `--mode paper` = E1 prompt'una takılmaz (LIVE değil).

### 5.2 Pano servisi (E3 Gunicorn)
- **[BEN]** `/etc/systemd/system/polymarket-dash.service`:
  ```ini
  [Unit]
  Description=Polymarket Dashboard
  After=network-online.target
  Wants=network-online.target

  [Service]
  Type=simple
  User=polybot
  WorkingDirectory=/home/polybot/polymarket-agent
  Environment=PYTHONUNBUFFERED=1
  ExecStart=/home/polybot/polymarket-agent/.venv/bin/gunicorn --workers 2 --bind 100.x.y.z:5050 src.presentation.dashboard.wsgi:app
  Restart=on-failure
  RestartSec=10
  StandardOutput=journal
  StandardError=journal

  [Install]
  WantedBy=multi-user.target
  ```
  > `--bind 100.x.y.z:5050` → **Tailscale IP'sine** bağlar (genel internete değil). Pano sadece senin cihazlarından `http://100.x.y.z:5050`. E3: gunicorn (Plan 1'de wsgi.py eklendi).

### 5.3 Başlat + boot'a ekle
- **[BEN]**
  ```bash
  systemctl daemon-reload
  systemctl enable --now polymarket-bot polymarket-dash
  systemctl status polymarket-bot --no-pager
  journalctl -u polymarket-bot -f          # canlı log
  ```
  → Telegram'a "bot başladı" mesajı düşmeli. Tailscale'li telefonundan `http://100.x.y.z:5050` panoyu açmalı.

### 5.4 Pano ek parola (karar 12.3 — opsiyonel ama açık)
- **[BEN]** Tailscale önünde basit HTTP Basic Auth (Caddy reverse proxy ile) — istenirse eklenir. Tailscale tek başına da yeterli.

---

## Faz 6 — Yedekleme

### 6.1 Saatlik kritik-dosya yedeği
- **[BEN]** `/home/polybot/backup.sh`:
  ```bash
  #!/bin/bash
  set -euo pipefail
  cd /home/polybot/polymarket-agent
  TS=$(date -u +%Y%m%d_%H%M%S)
  DEST=/home/polybot/backups
  mkdir -p "$DEST"
  cp -f data/positions.json data/circuit_breaker_state.json "$DEST/" 2>/dev/null || true
  cp -f logs/audit/trade_events.jsonl "$DEST/trade_events.$TS.jsonl" 2>/dev/null || true
  # 7 günden eski yedekleri sil
  find "$DEST" -name "trade_events.*.jsonl" -mtime +7 -delete
  ```
  ```bash
  chmod +x backup.sh
  ( crontab -l 2>/dev/null; echo "0 * * * * /home/polybot/backup.sh" ) | crontab -
  ```

### 6.2 .tmp kalıntı kontrolü (E8 izleme)
- **[BEN]** crontab'a: `*/15 * * * * find /home/polybot/polymarket-agent/data -name "*.tmp" -mmin +5 -print | head` (yarım yazma uyarısı).

### 6.3 Günlük dış indirme (karar 12.4)
- **[BEN]** Senin bilgisayarından (Tailscale ile) günlük çek:
  ```powershell
  scp polybot@100.x.y.z:/home/polybot/backups/* "C:\...\sunucu-yedek\"
  ```
  > Başlangıç: sunucu-içi + günlük indirme. İleride nesne depolama.

---

## Faz 7 — Güncelleme akışı (deploy.sh)

### 7.1 Tek-komut güncelleme
- **[BEN]** `/home/polybot/polymarket-agent/deploy.sh`:
  ```bash
  #!/bin/bash
  set -euo pipefail
  cd /home/polybot/polymarket-agent
  . .venv/bin/activate
  git pull --ff-only
  pip install -q -r requirements.txt
  pytest -q                                  # testler geçmezse aşağı inmez (set -e)
  sudo systemctl restart polymarket-bot polymarket-dash
  echo "Deploy OK: $(git rev-parse --short HEAD)"
  ```
  ```bash
  chmod +x deploy.sh
  ```
  > polybot'a sadece bu iki servisi restart için sudo izni: `/etc/sudoers.d/polybot-deploy`:
  > `polybot ALL=(root) NOPASSWD: /bin/systemctl restart polymarket-bot polymarket-dash`

### 7.2 Akış
1. **[BEN+SEN]** Değişikliği burada (yerelde/worktree) yap + test et.
2. **[BEN]** GitHub'a push.
3. **[BEN]** `ssh polybot@100.x.y.z "cd polymarket-agent && ./deploy.sh"` → test geçerse canlıya, geçmezse durur.

---

## Faz 8 — Cutover (sıfır-riskli geçiş)

1. **[BEN]** Sunucu PAPER modda çalışıyor (Faz 5). 1–2 gün **evdeki botla yan yana** izle (Telegram + pano).
2. **[BEN+SEN]** Doğrula: aynı maçlarda benzer kararlar, `pytest` geçiyor, log temiz, Telegram uyarı+komut çalışıyor (`/status`, `/pause`, `/resume`).
3. **[SEN]** "Sunucu hazır, eve gerek yok" onayı.
4. **[SEN]** Evdeki botu kapat (`python scripts/reboot.py` ile durdur — kullanıcı kararı).
5. **[BEN]** İlk 24 saat yakın izleme. Artık tek otorite sunucu.

> Mod PAPER kalır. Evdeki bot cutover'a kadar el değmeden çalışır → aksilikte eve dönüş, kayıp yok.

---

## Faz 9 — Bitiş doğrulama listesi

- [ ] `ssh polybot@100.x.y.z` çalışıyor (sadece anahtar, root kapalı)
- [ ] `ufw status` → sadece tailscale0 açık, genel portlar kapalı
- [ ] `systemctl is-enabled polymarket-bot polymarket-dash` → enabled
- [ ] `systemctl status` → both active (running)
- [ ] Telegram: boot mesajı + `/status` cevap veriyor + `/pause`/`/resume` çalışıyor
- [ ] Pano `http://100.x.y.z:5050` sadece Tailscale cihazından açılıyor
- [ ] `pytest -q` sunucuda geçiyor
- [ ] `crontab -l` → saatlik yedek + tmp kontrol
- [ ] `deploy.sh` bir kez test edildi (küçük commit ile)
- [ ] Sunucu reboot testi: `sudo reboot` → bot+pano otomatik geri geldi
- [ ] `.env` chmod 600
- [ ] Evdeki bot cutover'a kadar çalışıyor

## Edge case kapsam (Plan 2)
- E4 kalıcı disk → Faz 4.3 ✓ · E5 bayat kilit → Faz 5.1 ExecStartPre ✓ · E6 systemd restart → Faz 5+7 ✓
- E8 .tmp izleme → Faz 6.2 ✓ · E9 build-essential → Faz 1.1 ✓ · E10 model verisi → Faz 4.2 ✓
- Güvenlik: Tailscale (Faz 2) + ufw (2.3) + SSH-anahtar (1.3) + .env 600 (4.1) + auto-update (1.4) ✓
- Yedek: saatlik+günlük+arşiv (Faz 6) ✓
