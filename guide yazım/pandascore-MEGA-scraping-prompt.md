# PandaScore — Complete Reference Scraping Prompt

## Hedef
TEK bir devasa MD dosyası (`pandascore-complete-reference.md`) + TEK bir index dosyası (`pandascore-complete-index.md`)

Dosya 2 PART'tan oluşacak:
- PART 1: Documentation (Guides & Tutorials) — zaten hazır, aşağıda
- PART 2: API Reference (Tüm endpoint'ler) — senin çekmen gereken kısım

---

## Link
https://developers.pandascore.co/reference/get_additions

---

## Prompt (Antigravity'e yapıştır)

```
Görev: PandaScore'un TAMAMINI tek bir devasa MD dosyasına topla.

Bu dosya 2 PART'tan oluşacak:

### PART 1: Documentation (Guides & Tutorials)
Bu kısım ZATEN HAZIR. Aşağıdaki dosyayı oku ve dosyanın BAŞINA koy:
- Dosya: pandascore-full-api-reference.md (uploads'ta mevcut)
- Bu dosya 30 sayfalık guide/tutorial içeriyor (851 satır)
- Bunu olduğu gibi PART 1 olarak dosyanın başına yerleştir

### PART 2: API Reference (Tüm Endpoint'ler)
Bu kısmı SEN çekeceksin. https://developers.pandascore.co/reference/get_additions sayfasını aç.

1. SOL SIDEBAR'daki TÜM endpoint linklerini topla. Her kategori:
   - Incidents (additions, changes, deletions)
   - All Video Games (videogames, lives, matches, leagues, series, tournaments, teams, players)
   - Counter-Strike (games, leagues, matches, players, series, teams, tournaments, stats)
   - DotA 2 (games, heroes, items, leagues, matches, players, series, teams, tournaments, stats)
   - EA Sports FC
   - King of Glory  
   - League of Legends (champions, games, items, leagues, mastery, matches, players, runes, series, spells, teams, tournaments, stats)
   - LoL Wild Rift
   - Mobile Legends: Bang Bang
   - Overwatch (games, heroes, leagues, maps, matches, players, series, teams, tournaments, stats)
   - PUBG
   - R6 Siege
   - Rocket League
   - Starcraft 2
   - Starcraft Brood War
   - Valorant (agents, games, leagues, maps, matches, players, series, teams, tournaments, weapons, stats)
   - Call of Duty
   - Codmw

2. Her endpoint sayfasını ziyaret et ve şu bilgileri çek:
   - HTTP Method (GET/POST/PUT/DELETE)
   - Full URL path (örn: https://api.pandascore.co/csgo/games/{csgo_game_id})
   - Description
   - Path Parameters (isim, tip, required/optional, açıklama)
   - Query Parameters (isim, tip, required/optional, açıklama)  
   - Request body (varsa)
   - Response codes (200, 400, 401, 403, 404 vs.)
   - Response schema/fields (mümkün olduğunca detaylı)
   - cURL örneği
   - Hangi plan gerekiyor (fixtures/historical/live)

3. Dosya yapısı — TEK DOSYA:
   ```
   # PandaScore — Complete API Reference
   
   # ============================================
   # PART 1: DOCUMENTATION (GUIDES & TUTORIALS)
   # ============================================
   [pandascore-full-api-reference.md içeriğinin tamamı buraya]
   
   # ============================================
   # PART 2: API REFERENCE (ALL ENDPOINTS)  
   # ============================================
   
   ## CATEGORY: Incidents
   ### GET /additions
   ...
   ### GET /changes
   ...
   
   ## CATEGORY: All Video Games
   ### GET /videogames
   ...
   
   ## CATEGORY: Counter-Strike
   ### GET /csgo/games/{csgo_game_id}
   ...
   
   [tüm kategoriler ve endpoint'ler]
   ```

4. INDEX dosyası oluştur: `pandascore-complete-index.md`
   - Polymarket index formatında: Read("pandascore-complete-reference.md", offset=START, limit=SIZE)
   - PART 1 bölümleri (guides) + PART 2 bölümleri (endpoints) tek tabloda
   - Her kategori için tablo
   - Quick reference section (domains, auth, data hierarchy)

5. Çıktı dosyaları /mnt/user-data/outputs/ altına kaydet:
   - pandascore-complete-reference.md (DEVASA TEK DOSYA)
   - pandascore-complete-index.md (INDEX)

KURALLAR:
- HİÇBİR endpoint'i atlama — sidebar'daki HER LİNKE gir
- HİÇBİR guide sayfasını atlama — PART 1 zaten hazır, olduğu gibi koy
- Response schema field'larını mümkün olduğunca detaylı yaz
- Toplam muhtemelen 200+ endpoint + 30 guide sayfası olacak
- Her şey TEK DOSYADA, TEK INDEX'te
```

---

## Ek: PART 1 içeriği (pandascore-full-api-reference.md)

Bu dosyayı Antigravity'e upload et veya yeni oturumda ona bu dosyayı okumasını söyle.
Bu dosya zaten uploads'ta mevcut: pandascore-full-api-reference.md (851 satır, 30 guide sayfası)

İçindekiler:
- Introduction, Fundamentals, Authentication, Rate Limits
- Tutorials: First Request, Discord Score-Bot  
- CS2 Migration Guide
- REST API: Formats, Tracking Changes, Tournaments, Matches Lifecycle, Match Formats, Filtering/Sorting, Pagination, Errors, Image Optimization, Players' Age, FAQ
- Live API: WebSockets Overview, Data Samples (CS/DotA2/LoL), Events Recovery, Disconnections, Sandbox
- Esports: Seasons/Circuits, Dota 2, LoL, Overwatch
