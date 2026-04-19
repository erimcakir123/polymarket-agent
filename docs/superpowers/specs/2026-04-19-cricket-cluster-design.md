# SPEC-011: Cricket Cluster Integration

> **Durum**: IMPLEMENTED
> **Tarih**: 2026-04-19
> **Katman**: infrastructure (cricket_client) + strategy (cricket_score_exit) + orchestration (score_enricher integration) + config
> **Scope**: 7 cricket ligi + CricAPI entegrasyonu + tennis simetrik C1/C2/C3 score exit

---

## 1. Amac

Polymarket'te her gun 2-3 IPL cricket maci isleniyor. Bookmaker coverage guclu (5 sharp), Polymarket liquidity iyi. Ama bizim bot:
- Cricket slug'larini taniyamiyor
- Sport key mapping yok
- Canli skor kaynak yok (ESPN cricket YOK, Odds API /scores sadece aggregate run)
- Forced exit kurali yok

Cricket clusterini `tennis`/`hockey`/`baseball` ile **simetrik** olarak entegre et.

---

## 2. Kapsam

### 2a. Dahil 7 Lig (Odds API keys)
- `cricket_ipl` — IPL (Nisan-Haziran), SU AN AKTIF
- `cricket_odi` — International ODI (yil boyu)
- `cricket_international_t20` — International T20 (yil boyu)
- `cricket_psl` — Pakistan Super League (Subat-Mart)
- `cricket_big_bash` — Big Bash League Australia (Aralik-Ocak)
- `cricket_caribbean_premier_league` — CPL (Agustos-Eylul)
- `cricket_t20_blast` — UK T20 Blast (Mayis-Eylul)

### 2b. Kapsam Disi
- `cricket_test_match` — 5 gunluk maç, draw mumkun, mimari tutarsizlik
- Cricket Hundred (tek turnuva, lig degil)

---

## 3. Kok Parcalari

### 3a. CricAPI Client (Infrastructure)

Yeni dosya: `src/infrastructure/apis/cricket_client.py`

```python
"""CricAPI HTTP client — free tier 100 hit/gun.

Tek endpoint: /v1/currentMatches — TUM aktif cricket maclari doner.
Response cache TTL ve timeout config'den gelir (ARCH_GUARD Kural 6).

Hit budget tracking: API response'unda hitsUsed/hitsLimit field'lari
var. Client bunu monitor eder, limit dolmaya yakin uyari loglar.
Limit dolunca get_current_matches() None doner.
"""
from __future__ import annotations

import logging
import time
from dataclasses import dataclass, field
from typing import Any

import requests

logger = logging.getLogger(__name__)

_BASE_URL = "https://api.cricapi.com/v1"  # endpoint — config'e tasinmaz


@dataclass
class CricketMatchScore:
    """CricAPI response'undan parse edilen tek bir mac."""

    match_id: str
    name: str               # "Team A vs Team B"
    match_type: str         # "t20" | "odi" | "test"
    teams: list[str]        # [home, away]
    status: str             # "India won by 5 wickets" | "In progress" | ...
    match_started: bool
    match_ended: bool
    venue: str
    date_time_gmt: str
    # Scores array: innings basina [{r, w, o, inning}]
    # inning string "Team A Inning 1" formatinda
    innings: list[dict]     # [{runs: int, wickets: int, overs: float, team: str, inning_num: int}]


@dataclass
class CricAPIQuota:
    """API kullanim takibi — her response'da guncelleniyor."""
    used_today: int = 0
    daily_limit: int = 100
    last_checked: float = 0.0

    @property
    def remaining(self) -> int:
        return max(0, self.daily_limit - self.used_today)

    @property
    def exhausted(self) -> bool:
        return self.used_today >= self.daily_limit


class CricketAPIClient:
    """CricAPI /currentMatches wrapper + cache + quota tracking."""

    def __init__(
        self,
        api_key: str,
        daily_limit: int = 100,
        cache_ttl_sec: int = 240,
        timeout_sec: int = 15,
        http_get=None,
    ) -> None:
        """Config'den: daily_limit, cache_ttl_sec, timeout_sec.
        Factory.py bu parametreleri cfg.cricket'ten gecirir.
        """
        self._api_key = api_key
        self._http = http_get or self._default_get
        self._cache_ttl = cache_ttl_sec
        self._timeout = timeout_sec
        self._cached_data: list[CricketMatchScore] | None = None
        self._cache_timestamp: float = 0.0
        self.quota = CricAPIQuota(daily_limit=daily_limit)

    def get_current_matches(self) -> list[CricketMatchScore] | None:
        """TUM aktif cricket maclari. None → limit dolu VEYA hata."""
        if self.quota.exhausted:
            logger.warning("CricAPI quota exhausted (%d/%d), skipping",
                           self.quota.used_today, self.quota.daily_limit)
            return None

        # Cache check
        now = time.time()
        if self._cached_data is not None and (now - self._cache_timestamp) < self._cache_ttl:
            return self._cached_data

        try:
            response = self._http(
                f"{_BASE_URL}/currentMatches",
                params={"apikey": self._api_key, "offset": 0},
                timeout=self._timeout,
            )
            if response.status_code != 200:
                logger.warning("CricAPI HTTP %d", response.status_code)
                return None
            data = response.json() or {}
            info = data.get("info", {})
            self.quota.used_today = int(info.get("hitsToday", 0))
            self.quota.daily_limit = int(info.get("hitsLimit", 100))
            matches_raw = data.get("data", [])
            matches = [self._parse_match(m) for m in matches_raw if self._parse_match(m)]
            self._cached_data = matches
            self._cache_timestamp = now
            logger.info("CricAPI: %d matches, quota %d/%d",
                        len(matches), self.quota.used_today, self.quota.daily_limit)
            return matches
        except Exception as exc:
            logger.warning("CricAPI fetch error: %s", exc)
            return None

    def _parse_match(self, raw: dict) -> CricketMatchScore | None:
        """Raw CricAPI response → CricketMatchScore."""
        try:
            innings = []
            for s in raw.get("score", []):
                inning_str = s.get("inning", "")
                team_name = inning_str.rsplit(" Inning ", 1)[0] if " Inning " in inning_str else ""
                inning_num = int(inning_str.rsplit(" ", 1)[-1]) if " Inning " in inning_str else 0
                innings.append({
                    "runs": int(s.get("r", 0)),
                    "wickets": int(s.get("w", 0)),
                    "overs": float(s.get("o", 0)),
                    "team": team_name,
                    "inning_num": inning_num,
                })
            return CricketMatchScore(
                match_id=raw.get("id", ""),
                name=raw.get("name", ""),
                match_type=raw.get("matchType", "").lower(),
                teams=raw.get("teams", []),
                status=raw.get("status", ""),
                match_started=bool(raw.get("matchStarted", False)),
                match_ended=bool(raw.get("matchEnded", False)),
                venue=raw.get("venue", ""),
                date_time_gmt=raw.get("dateTimeGMT", ""),
                innings=innings,
            )
        except Exception:
            return None

    @staticmethod
    def _default_get(url: str, params: dict, timeout: int):
        return requests.get(url, params=params, timeout=timeout)
```

**Test edilebilir**: DI ile http_get mock'lanabilir.
**Infrastructure katmaninda**: I/O burada yapilir.
**~120 satir**, ARCH_GUARD Kural 3 (<400) uyumlu.

### 3b. Cricket Score Exit (Strategy)

Yeni dosya: `src/strategy/exit/cricket_score_exit.py`

```python
"""Cricket inning-based score exit (SPEC-011) — pure.

A-conf pozisyonlar icin FORCED exit. Tennis T1/T2 ve hockey K1-K4
ile simetrik. Sadece 2. innings (chase) mantigi — 1. innings'te
veri yetersiz.

C1: Matematiksel imkansiz chase
    balls_remaining < 30 AND required_run_rate > 18
    → exit (per ball 3+ run gerekli, gerceklesmiz)

C2: Cok fazla wicket kaybi
    wickets_lost >= 8 AND runs_remaining > 20
    → exit (son 2 wicket + uzak hedef)

C3: Son over'lar + uzak hedef
    balls_remaining < 6 AND runs_remaining > 10
    → exit (1 over'da 10+ run gerekli)

Tum threshold'lar sport_rules.py config'inden (magic number yok).
"""
from __future__ import annotations

from dataclasses import dataclass

from src.config.sport_rules import get_sport_rule
from src.models.enums import ExitReason


@dataclass
class CricketExitResult:
    """Cricket exit sonucu — monitor.py ExitSignal'a cevirir."""

    reason: ExitReason
    detail: str


def check(
    score_info: dict,
    current_price: float,
    sport_tag: str = "cricket_ipl",
) -> CricketExitResult | None:
    """Cricket C1/C2/C3 exit kontrolu.

    score_info dict beklenen format:
      {
        "available": True,
        "innings": 2,              # 2nd innings (chase)
        "balls_remaining": int,
        "runs_remaining": int,     # target - current_score
        "wickets_lost": int,
        "required_run_rate": float,
      }

    1. innings veya available=False → None (skip, near_resolve yeterli).
    """
    if not score_info.get("available"):
        return None

    innings = score_info.get("innings", 0)
    if innings != 2:
        return None  # Sadece chase'te mantikli

    balls_remaining = score_info.get("balls_remaining", 0)
    runs_remaining = score_info.get("runs_remaining", 0)
    wickets_lost = score_info.get("wickets_lost", 0)
    required_rate = score_info.get("required_run_rate", 0.0)

    if runs_remaining <= 0:
        return None  # Chase tamamlandi (YES)

    # Config thresholds
    c1_balls = int(get_sport_rule(sport_tag, "score_exit_c1_balls", 30))
    c1_rate = float(get_sport_rule(sport_tag, "score_exit_c1_rate", 18.0))
    c2_wickets = int(get_sport_rule(sport_tag, "score_exit_c2_wickets", 8))
    c2_runs = int(get_sport_rule(sport_tag, "score_exit_c2_runs", 20))
    c3_balls = int(get_sport_rule(sport_tag, "score_exit_c3_balls", 6))
    c3_runs = int(get_sport_rule(sport_tag, "score_exit_c3_runs", 10))

    # C1: Impossible chase
    if balls_remaining < c1_balls and required_rate > c1_rate:
        return CricketExitResult(
            reason=ExitReason.SCORE_EXIT,
            detail=f"C1: balls_left={balls_remaining} rrr={required_rate:.1f} threshold={c1_rate}",
        )

    # C2: Too many wickets
    if wickets_lost >= c2_wickets and runs_remaining > c2_runs:
        return CricketExitResult(
            reason=ExitReason.SCORE_EXIT,
            detail=f"C2: wkts={wickets_lost} runs_left={runs_remaining}",
        )

    # C3: Final balls
    if balls_remaining < c3_balls and runs_remaining > c3_runs:
        return CricketExitResult(
            reason=ExitReason.SCORE_EXIT,
            detail=f"C3: balls_left={balls_remaining} runs_left={runs_remaining}",
        )

    return None
```

~80 satir. Tennis T1/T2 ile **simetrik**.

### 3c. Cricket Score Builder (Orchestration — Ayrı Modül)

**ARCH_GUARD Kural 3**: score_enricher.py 367 satir. Cricket branch
eklenirse 400'u asar. Cricket-specific build fonksiyonu ayri modulde:

Yeni dosya: `src/orchestration/cricket_score_builder.py`

```python
"""Cricket match state → score_info dict donusumu (SPEC-011).

CricAPI CricketMatchScore nesnesinden, position direction'a gore,
C1/C2/C3 kurallarinin tukettigi score_info dict'i uretir.

Pure: CricAPI response VE position verilir, dict doner. I/O yok.
"""
from __future__ import annotations

from src.infrastructure.apis.cricket_client import CricketMatchScore
from src.models.position import Position
from src.domain.matching.pair_matcher import match_team

_FORMAT_MAX_OVERS = {"t20": 20, "t20i": 20, "odi": 50}


def build_cricket_score_info(pos: Position, match: CricketMatchScore) -> dict:
    """CricAPI match → score_info. available=False → skip."""
    if not match.innings or not match.match_started:
        return {"available": False}
    # ... (spec'in Data Donusumleri bolumundeki logic) ...


def find_cricket_match(pos: Position, matches: list[CricketMatchScore]) -> CricketMatchScore | None:
    """Pair matcher ile position-match eslestir."""
    # ... pair_matcher.match_pair ile ...
```

### 3d. Score Enricher Integration (Minimal)

`src/orchestration/score_enricher.py` guncelle — sadece dispatch:
- Cricket sport_tag tespit et
- `_cricket_client.get_current_matches()` cagir
- `cricket_score_builder.find_cricket_match()` + `build_cricket_score_info()`
- Cricket sport_tag icin CricAPI path kullan (ESPN/Odds API yerine)

```python
# ScoreEnricher.__init__ icinde
from src.infrastructure.apis.cricket_client import CricketAPIClient
# cricket_client DI ile gecirilir (factory.py'de)

# _refresh_scores icinde cricket branch:
if sport in ("cricket", "cricket_ipl", ...):  # normalized
    if self._cricket_client is None:
        continue
    cricket_matches = self._cricket_client.get_current_matches()
    if cricket_matches is None:
        # Quota dolu veya hata — None sinyalini entry gate'e tasi
        self._cricket_limit_reached = True
        continue
    self._cached_cricket[tag] = cricket_matches
```

Yeni fonksiyon: `_build_cricket_score_info(pos, match)`:
- Parse innings, hesapla balls_remaining, RRR, runs_remaining
- position direction aware (BUY_YES takimı kim?)
- pos.direction + which_team_batting logic

### 3d. Entry Gate Cricket Skip

Cricket trade'i entry asamasinda **CricAPI quota doluysa** skip edilmeli:

`src/strategy/entry/gate.py` — cricket sport check:
```python
if _is_cricket(sport_tag):
    if self._cricket_unavailable:  # factory'den set
        return GateResult(cid, None, "cricapi_unavailable", ...)
```

Skip reason: `cricapi_unavailable` (skipped_trades.jsonl'de loglanir).

### 3e. Config Updates

`config.yaml`:
```yaml
# Cricket config (SPEC-011)
cricket:
  enabled: true
  # api_key: env'den CRICAPI_KEY
  daily_limit: 100       # free tier; TODO-003 paid tier'da 1000 olur
  cache_ttl_sec: 240     # 4dk bulk cache
  timeout_sec: 15        # HTTP timeout

scanner:
  allowed_sport_tags:
    # ... mevcut ...
    # Cricket (SPEC-011)
    - cricket
    - cricket_ipl
    - cricket_odi
    - cricket_international_t20
    - cricket_psl
    - cricket_big_bash
    - cricket_caribbean_premier_league
    - cricket_t20_blast
    - indian-premier-league        # Polymarket tag
    - international-cricket        # Polymarket tag
```

`sport_rules.py` yeni cricket bloklari:
```python
"cricket_ipl": {
    "stop_loss_pct": 0.30,
    "match_duration_hours": 3.5,
    "score_source": "cricapi",
    "score_exit_c1_balls": 30, "score_exit_c1_rate": 18.0,
    "score_exit_c2_wickets": 8, "score_exit_c2_runs": 20,
    "score_exit_c3_balls": 6, "score_exit_c3_runs": 10,
},
"cricket_odi": {
    "stop_loss_pct": 0.30,
    "match_duration_hours": 8.0,
    "score_source": "cricapi",
    # Ayni C1/C2/C3 threshold'lar ama balls max=300 (50 over)
    "score_exit_c1_balls": 60,   # ODI icin daha gevsek (150 ball gerek olabilir)
    "score_exit_c1_rate": 12.0,  # ODI RRR 12+ imkansiz
    "score_exit_c2_wickets": 8, "score_exit_c2_runs": 40,
    "score_exit_c3_balls": 30, "score_exit_c3_runs": 30,
},
# T20 variant'lar (big_bash, cpl, etc.) IPL ile ayni
"cricket_big_bash": { ... ayni T20 ... },
"cricket_caribbean_premier_league": { ... },
"cricket_t20_blast": { ... },
"cricket_psl": { ... },
"cricket_international_t20": { ... },
```

### 3f. Team Resolver (Cricket Aliases)

`src/domain/matching/team_resolver.py` — `_STATIC_ABBREVS` genislet:
```python
# Cricket (IPL)
"csk": "chennai super kings", "mi": "mumbai indians",
"rcb": "royal challengers bengaluru", "kkr": "kolkata knight riders",
"srh": "sunrisers hyderabad", "dc": "delhi capitals",
"pk": "punjab kings", "rr": "rajasthan royals",
"lsg": "lucknow super giants", "gt": "gujarat titans",
# Cricket (International)
"ind": "india", "aus": "australia", "eng": "england",
"pak": "pakistan", "nz": "new zealand", "sa": "south africa",
"wi": "west indies", "ban": "bangladesh", "sl": "sri lanka",
"afg": "afghanistan", "zim": "zimbabwe", "ire": "ireland",
```

### 3g. Slug Parser

Cricket Polymarket slug formatlari:
- IPL: `cricipl-kol-raj-2026-04-19` (prefix: cricipl-)
- ODI: `crict20i-ban-nz-2026-04-20` (prefix: crict20i-)
- PSL: `cricpsl-lah-kar-2026-02-15`
- vs.

`src/domain/matching/slug_parser.py` veya `sport_classifier.py` cricket regex ekle.

### 3h. Odds API Key Resolver

`src/domain/matching/odds_sport_keys.py` — cricket mapping:
```python
# Cricket
"cricipl": "cricket_ipl",
"cricket_ipl": "cricket_ipl",
"crict20i": "cricket_international_t20",
"international-cricket": "cricket_international_t20",  # PM tag
"cricodi": "cricket_odi",
"cricpsl": "cricket_psl",
"cricbbl": "cricket_big_bash",
"cricket_big_bash": "cricket_big_bash",
"criccpl": "cricket_caribbean_premier_league",
"crictbl": "cricket_t20_blast",
```

---

## 4. Etkilenen Dosyalar

### Yeni Dosyalar
| Dosya | Boyut Tahmini | Katman |
|---|---|---|
| `src/infrastructure/apis/cricket_client.py` | ~120 satir | Infrastructure |
| `src/orchestration/cricket_score_builder.py` | ~80 satir | Orchestration (score_enricher 400'u asmasin) |
| `src/strategy/exit/cricket_score_exit.py` | ~80 satir | Strategy |
| `tests/unit/infrastructure/apis/test_cricket_client.py` | ~80 satir | — |
| `tests/unit/orchestration/test_cricket_score_builder.py` | ~80 satir | — |
| `tests/unit/strategy/exit/test_cricket_score_exit.py` | ~130 satir | — |

### Guncelleme
| Dosya | Islem |
|---|---|
| `src/orchestration/score_enricher.py` | Cricket dispatch branch (+15 satir — builder'a delegate) |
| `src/orchestration/agent.py` | AgentDeps'e cricket_client (+1 satir) |
| `src/orchestration/factory.py` | CricAPI init (+5 satir) |
| `src/strategy/exit/monitor.py` | cricket_score_exit wire (+10 satir) |
| `src/strategy/entry/gate.py` | CricAPI unavailable skip (+5 satir) |
| `src/config/sport_rules.py` | 7 cricket blok ekle (+80 satir) |
| `src/config/settings.py` | CricketConfig class (+10 satir) |
| `config.yaml` | cricket: block + allowed_sport_tags (+15 satir) |
| `src/domain/matching/team_resolver.py` | Cricket aliases (+30 satir) |
| `src/domain/matching/odds_sport_keys.py` | Cricket keys (+10 satir) |
| `src/domain/matching/sport_classifier.py` | cricket pattern (+5 satir) |

### Dokuman
| Dosya | Islem |
|---|---|
| `TDD.md` | §7 sport rules tablosuna 7 cricket ligi satiri; §6 cricket score exit alt-bolum (tennis/hockey/baseball simetrik); §7.2 MVP kapsamina cricket ekle |
| `PRD.md` | F11 Cricket Cluster feature madde (tennis/hockey/baseball F-formatinda) |
| `CLAUDE.md` | Degisiklik yok (CricAPI paid TODO zaten TODO.md'de) |

---

## 5. Sinir Durumlari

| Durum | Davranis |
|---|---|
| CricAPI limit doldu | Quota object exhausted=True → get_current_matches() None doner → entry skip (cricapi_unavailable) |
| CricAPI HTTP hatasi | None doner, quota artmaz (hit sayilmadi), exit score_exit yok (near_resolve fallback) |
| Cricket match CricAPI'de yok (PM phantom) | pair_matcher match_pair confidence < 0.80 → skip, score_info.available=False |
| 1. innings pozisyon | score_exit trigger etmez (sadece chase mantikli), near_resolve/scale_out/market_flip calisir |
| ODI 8 saat tek maci | 8h × 12 poll = 96 hit — tek maci bile limit doldurur! → T20 only v1, ODI TODO-003 ile paid'e eklenecek |
| Super over (tied T20) | Score_info format karisik, C1/C2/C3 tetiklenmeyebilir → near_resolve yakalar |
| Match started=False (pre-match) | innings=0 → check() early return None |
| Match ended=True | innings veriye dolu ama near_resolve zaten 94¢'te yakalami olur |
| cricket_client=None (test/dev) | ScoreEnricher gracefully skip |

---

## 6. Test Senaryolari

### CricAPI Client (unit)
- `test_get_current_matches_success`: Mock response → list<CricketMatchScore>
- `test_quota_tracking`: hitsToday/hitsLimit parse dogru
- `test_quota_exhausted_returns_none`: used>=limit → None
- `test_cache_hit`: 2nd call within 4min → cache
- `test_cache_expired_refetch`: 5min sonra cache bust
- `test_http_error_returns_none`: 500 → None, quota artmaz
- `test_parse_match_malformed`: bozuk data → None

### Cricket Score Exit (unit)
- `test_innings_1_no_exit`: innings=1 → None
- `test_chase_not_started`: innings=2, runs_remaining=target → None
- `test_c1_impossible_rrr_t20`: balls=24, rrr=20 → C1 exit
- `test_c1_not_quite_threshold`: balls=24, rrr=17 → None
- `test_c2_8_wickets_20_runs_left`: wkts=8, runs=25 → C2 exit
- `test_c2_7_wickets_no_exit`: wkts=7, runs=30 → None
- `test_c3_final_balls_big_gap`: balls=4, runs=15 → C3 exit
- `test_c3_final_balls_small_gap`: balls=4, runs=5 → None
- `test_chase_won_no_exit`: runs_remaining <= 0 → None
- `test_config_driven_thresholds`: ODI farkli threshold (c1_rate=12)
- `test_unavailable_no_exit`: available=False → None
- `test_sport_tag_variations`: cricket_ipl vs cricket_big_bash same rules

### Monitor Integration
- `test_cricket_score_exit_triggers_for_a_conf`: A-conf cricket + C1 score_info → SCORE_EXIT
- `test_cricket_exit_doesnt_fire_for_basketball`: sport_tag check

### Entry Gate
- `test_cricapi_unavailable_skip`: quota exhausted → skip_reason cricapi_unavailable
- `test_cricapi_available_allow`: normal giris

### Score Enricher
- `test_cricket_path_uses_cricapi`: sport=cricket → CricAPI called, not ESPN
- `test_cricket_score_info_built`: parse CricketMatchScore → score_info dict
- `test_cricket_no_match_returns_empty`: PM match != CricAPI match → None

---

## 7. Veri Donusumleri

### CricAPI response → score_info

```python
def _cricket_score_info(pos: Position, match: CricketMatchScore) -> dict:
    """Cricket match state → our score_info format."""
    if not match.innings:
        return {"available": False}
    
    # Position direction → which team is ours?
    team_a, team_b = extract_teams(pos.question)
    # Direction-aware mapping
    our_team_name = ...  # match with pair_matcher
    
    # Find our team's innings (if exists)
    # Find opponent team's innings (target = their score + 1 in chase)
    
    # Determine current innings (1 or 2)
    if len(match.innings) == 1:
        # 1st innings in progress
        return {
            "available": True,
            "innings": 1,
            "status": match.status,
        }
    
    # 2nd innings — chase
    first_innings = match.innings[0]
    second_innings = match.innings[1]
    target = first_innings["runs"] + 1
    
    # Determine format for max_balls
    max_overs = {"t20": 20, "odi": 50, "t20i": 20}.get(match.match_type, 20)
    max_balls = max_overs * 6
    
    balls_faced = int(second_innings["overs"] * 6 + (second_innings["overs"] % 1) * 10)
    # "15.3 overs" = 93 balls (15*6 + 3)
    
    runs_scored = second_innings["runs"]
    wickets_lost = second_innings["wickets"]
    balls_remaining = max_balls - balls_faced
    runs_remaining = target - runs_scored
    
    required_rate = (runs_remaining * 6 / balls_remaining) if balls_remaining > 0 else 0.0
    current_rate = (runs_scored * 6 / balls_faced) if balls_faced > 0 else 0.0
    
    # Check if OUR team is batting (2nd innings)
    chasing_team = second_innings["team"]
    our_chasing = _team_match(our_team_name, chasing_team)
    
    return {
        "available": True,
        "innings": 2,
        "target": target,
        "runs_remaining": runs_remaining,
        "balls_remaining": balls_remaining,
        "wickets_lost": wickets_lost,
        "required_run_rate": required_rate,
        "current_run_rate": current_rate,
        "our_chasing": our_chasing,  # True = bizim takim chase ediyor
    }
```

**Dikkat**: Chase senaryosunda bizim takim batting (chasing) olabilir VEYA bowling (defending):
- BUY_YES Team A + Team A chasing → we want them to REACH target → C1/C2/C3 triggers = EXIT (kaybettik)
- BUY_YES Team A + Team A defending → we want them to PREVENT chase → C1/C2/C3 = ALIVE (kazaniyoruz)

Bu nuance icin `cricket_score_exit.check()` de `our_chasing` bayragi dikkate alinir — sadece `our_chasing=True` iken C1/C2/C3 tetiklenir.

### Revize Score Exit

```python
def check(score_info, current_price, sport_tag="cricket_ipl"):
    if not score_info.get("available"): return None
    if score_info.get("innings", 0) != 2: return None
    if not score_info.get("our_chasing", False):
        return None  # Biz defending side'dayiz, chase cokmesi KAZANC
    
    # ... C1/C2/C3 kontrol et (yukaridaki gibi) ...
```

---

## 8. Tahmini Etki

### Aktif Volumetrik

- IPL: 2 maç/gun (Nisan-Haziran) × $50 bet × %60 WR × 13% edge = **~$8/gun**
- ODI: ortalama 1 maç/gun (TODO-003 paid sonra) = ~$4/gun
- Diger T20 ligleri seasonal: ~$2/gun ortalama

Yillik ~**$2000-3000** potansiyel cricket profit.

### Risk Tarafi

- Free tier limit = günlük 2 ODI veya 3-4 T20 maç ile dar
- Phantom matchup yanlis takim eslesmesi → mevcut pair_matcher fix (SPEC-010) ile yakalandi
- Direction confusion (our_chasing) → score_info build fonksiyonu edge case testi

---

## 9. Rollback Plani

1. `cricket.enabled: false` config'de
2. Bot restart — cricket branch komplet atlar
3. Mevcut cricket pozisyonlar near_resolve'a kadar tutulur (cricket_score_exit skip olur)

---

## 10. Teknik Olmayan Ozet

1. **Cricket entegre edilir** — 7 T20/ODI ligi (IPL, Big Bash, CPL, vs).
2. **Bookmaker edge** mevcut altyapi ile cekilir (Odds API).
3. **Canli skor** CricAPI free tier ile cekilir (100 istek/gun).
4. **Limit dolarsa** cricket trade'leri o gun skip edilir (log'a `cricapi_unavailable` yazilir).
5. **Score exit** tennis T1/T2 ile simetrik: C1/C2/C3 (over+wicket+RRR bazli).
6. **Diger sporlara etki yok** — tennis/hockey/baseball/MLB devam.
