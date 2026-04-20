"""Sharp bookmaker vs Polymarket fiyat hareketi observer (sharp-vs-poly pilot).

Bot'tan TAM IZOLASYONLU:
- Ayri API key (ODDS_API_TEST_KEY) — bot butcesine dokunmaz
- Ayri log dizini (logs/sharp_vs_poly/)
- Bot state dosyalarini okumaz/yazmaz
- Minimal import — sadece domain/matching (pure, I/O yok)
- Ctrl+C guvenli kapanma + state.json
- Otomatik Telegram bildirimi tamamlaninca

Durma kriteri:
- 50 benzersiz maçta en az 3 snapshot, VEYA
- 450 credit kullanimi, VEYA
- Ctrl+C

Her 15 dk:
- 9 spor icin Odds API h2h bulk cek (9 credit)
- Her event icin sharp consensus hesapla (Pinnacle, Betfair Exchange, Matchbook, Smarkets)
- Polymarket Gamma'dan canli sport marketleri cek (ucretsiz)
- Pair matcher ile event ↔ market eslestir
- Eslesen maç icin snapshot yaz
"""
from __future__ import annotations

import json
import os
import signal
import sys
import time
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import requests
from dotenv import load_dotenv

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

load_dotenv()

from src.domain.matching.pair_matcher import match_pair
from src.strategy.enrichment.question_parser import extract_teams

# ── Config ────────────────────────────────────────────────────────────

TARGET_MATCHES = 50
MIN_SNAPSHOTS = 3
POLL_INTERVAL_SEC = 10 * 60        # 10 dk — Test 2 daha granuler
CREDIT_LIMIT = 400                  # Test 2 — free tier 500, 72 test 1'den kullanildi
MAX_ELAPSED_SEC = 5 * 3600          # 5 saat guvenlik
# Test 2 kapsamli: hedef maç sayısı kaldırıldı, sadece credit/süre ile durur
STOP_ON_TARGET = False

LOG_DIR = PROJECT_ROOT / "logs" / "sharp_vs_poly"
LOG_DIR.mkdir(parents=True, exist_ok=True)
STATE_FILE = LOG_DIR / "_state.json"

ODDS_BASE = "https://api.the-odds-api.com/v4"
GAMMA_BASE = "https://gamma-api.polymarket.com"

# Odds API sport_keys — hepsini takip (cricket, ana major sporlar, MMA, boxing)
ODDS_API_SPORTS = [
    "cricket_ipl",
    "cricket_odi",
    "cricket_international_t20",
    "cricket_big_bash_league",
    "cricket_psl",
    "cricket_t20_blast",
    "cricket_caribbean_premier_league",
    "baseball_mlb",
    "basketball_nba",
    "basketball_wnba",
    "basketball_ncaab",
    "basketball_euroleague",
    "icehockey_nhl",
    "americanfootball_nfl",
    "mma_mixed_martial_arts",
    "boxing_boxing",
    "tennis_atp_singles",
    "tennis_wta_singles",
]

SHARP_BOOKS = frozenset({"pinnacle", "betfair_ex_eu", "matchbook", "smarkets"})

# ── State ─────────────────────────────────────────────────────────────

_RUNNING = True


def _shutdown_handler(signum: int, frame: Any) -> None:
    global _RUNNING
    print("\n[!] Durdurma sinyali alindi, state kaydediliyor...")
    _RUNNING = False


signal.signal(signal.SIGINT, _shutdown_handler)
signal.signal(signal.SIGTERM, _shutdown_handler)


def _log(msg: str) -> None:
    ts = datetime.now(timezone.utc).strftime("%H:%M:%S")
    print(f"[{ts}] {msg}", flush=True)


def _load_state() -> dict:
    if STATE_FILE.exists():
        try:
            return json.loads(STATE_FILE.read_text(encoding="utf-8"))
        except Exception:
            return {}
    return {}


def _save_state(state: dict) -> None:
    try:
        STATE_FILE.write_text(json.dumps(state, indent=2), encoding="utf-8")
    except Exception as e:
        _log(f"[!] state save error: {e}")


# ── Telegram ──────────────────────────────────────────────────────────

def send_telegram(msg: str) -> None:
    token = os.getenv("TELEGRAM_BOT_TOKEN", "")
    chat = os.getenv("TELEGRAM_CHAT_ID", "")
    if not token or not chat:
        _log("[!] Telegram credentials yok — bildirim gonderilmedi")
        return
    try:
        r = requests.post(
            f"https://api.telegram.org/bot{token}/sendMessage",
            json={"chat_id": chat, "text": msg, "parse_mode": "HTML"},
            timeout=15,
        )
        if r.status_code == 200:
            _log("[OK] Telegram bildirimi gonderildi")
        else:
            _log(f"[!] Telegram HTTP {r.status_code}: {r.text[:120]}")
    except Exception as e:
        _log(f"[!] Telegram error: {e}")


# ── Odds API ──────────────────────────────────────────────────────────

def fetch_sport_events(sport_key: str, api_key: str) -> list[dict]:
    url = f"{ODDS_BASE}/sports/{sport_key}/odds"
    params = {
        "apiKey": api_key,
        "regions": "eu,uk",
        "markets": "h2h",
        "oddsFormat": "decimal",
        "dateFormat": "iso",
    }
    try:
        r = requests.get(url, params=params, timeout=15)
        if r.status_code == 200:
            return r.json() or []
        if r.status_code == 404:
            return []  # sport has no live events, normal
        _log(f"[!] Odds API {sport_key} HTTP {r.status_code}: {r.text[:120]}")
        return []
    except Exception as e:
        _log(f"[!] Odds API {sport_key} error: {e}")
        return []


def compute_sharp_prob(event: dict) -> tuple[float | None, int, float | None]:
    """Sharp consensus probability (home team icin) + bookmaker sayisi + avg odds.

    Vig-adjusted: 1/home_odds + 1/away_odds = 1+margin, bol margin'e.
    """
    home = event.get("home_team", "")
    away = event.get("away_team", "")
    if not home or not away:
        return None, 0, None

    sharp_pairs: list[tuple[float, float]] = []
    for bm in event.get("bookmakers", []):
        if bm.get("key") not in SHARP_BOOKS:
            continue
        for market in bm.get("markets", []):
            if market.get("key") != "h2h":
                continue
            outcomes = market.get("outcomes", [])
            home_price = next((o.get("price") for o in outcomes if o.get("name") == home), None)
            away_price = next((o.get("price") for o in outcomes if o.get("name") == away), None)
            if home_price and away_price and home_price > 1.0 and away_price > 1.0:
                sharp_pairs.append((home_price, away_price))

    if not sharp_pairs:
        return None, 0, None

    # Average vig-adjusted home probability
    probs = []
    for hp, ap in sharp_pairs:
        imp_h = 1.0 / hp
        imp_a = 1.0 / ap
        total = imp_h + imp_a
        if total > 0:
            probs.append(imp_h / total)

    if not probs:
        return None, 0, None

    avg_prob = sum(probs) / len(probs)
    avg_home_price = sum(p[0] for p in sharp_pairs) / len(sharp_pairs)
    return avg_prob, len(sharp_pairs), avg_home_price


# ── Polymarket Gamma ──────────────────────────────────────────────────

def fetch_polymarket_live_sports() -> list[dict]:
    """Canli sport marketleri — Gamma /events?tag_id=1 (sports parent tag).

    Event'ler markets dizisi icinde market'leri tutar, her market'i flat dondururuz
    question + conditionId + outcomePrices + sport_tag (ilk spesifik tag) ile.
    """
    url = f"{GAMMA_BASE}/events"
    results: list[dict] = []
    offset = 0
    page_size = 200
    max_pages = 25  # ~5000 events — individual game events genelde ~500+ offset'te
    _GENERIC_TAGS = {"sports", "esports", "games", "all", ""}

    for _ in range(max_pages):
        params = {
            "tag_id": 1,  # sports parent
            "active": "true",
            "closed": "false",
            "limit": page_size,
            "offset": offset,
        }
        try:
            r = requests.get(url, params=params, timeout=20)
            if r.status_code != 200:
                _log(f"[!] Gamma HTTP {r.status_code}")
                break
            events = r.json() or []
        except Exception as e:
            _log(f"[!] Gamma error: {e}")
            break
        if not events:
            break

        for event in events:
            # Specific sport tag
            sport_tag = "sports"
            tags = event.get("tags") or []
            if isinstance(tags, list):
                for t in tags:
                    if isinstance(t, dict):
                        slug = str(t.get("slug", "") or "").lower()
                        if slug and slug not in _GENERIC_TAGS:
                            sport_tag = slug
                            break

            for mkt in event.get("markets", []) or []:
                if not mkt.get("conditionId"):
                    continue
                if mkt.get("closed"):
                    continue
                # Flatten event data into market
                mkt["_sport_tag"] = sport_tag
                mkt["_event_id"] = event.get("id", "")
                mkt["_event_live"] = bool(event.get("live", False))
                mkt["_event_ended"] = bool(event.get("ended", False))
                results.append(mkt)

        offset += page_size
        if len(events) < page_size:
            break

    return results


def _clean_pm_question(question: str) -> str:
    """PM sorularindan tournament prefix'ini sil.

    'T20 Series Afghanistan vs Sri Lanka: Afghanistan vs Sri Lanka - prop'
    -> 'Afghanistan vs Sri Lanka - prop'

    'KBO: Lotte Giants vs. Samsung Lions' -> 'Lotte Giants vs. Samsung Lions'
    """
    if not question:
        return question
    # Eger ":" varsa, SON ":" sonrasini kullan (tournament adini atla)
    if ":" in question:
        parts = question.rsplit(":", 1)
        if len(parts) == 2 and parts[1].strip():
            return parts[1].strip()
    return question


def extract_pm_price_and_teams(market: dict) -> tuple[float | None, str, str, str]:
    """Polymarket market → (yes_price, question, team_a, team_b)."""
    question = market.get("question", "") or ""
    prices_raw = market.get("outcomePrices", "")
    yes_price: float | None = None
    if isinstance(prices_raw, str):
        try:
            prices = json.loads(prices_raw)
            if isinstance(prices, list) and len(prices) >= 1:
                yes_price = float(prices[0])
        except Exception:
            pass
    elif isinstance(prices_raw, list) and len(prices_raw) >= 1:
        try:
            yes_price = float(prices_raw[0])
        except Exception:
            pass

    # Clean tournament prefix for better team extraction
    clean_q = _clean_pm_question(question)
    team_a, team_b = extract_teams(clean_q)
    return yes_price, question, team_a or "", team_b or ""


# ── Matching ──────────────────────────────────────────────────────────

# Non-moneyline market patterns
_NON_MONEYLINE_PATTERNS = (
    "O/U", "OVER/UNDER", "TOTAL", "NRFI", "YRFI", "PROPS", "ANYTIME",
    "1ST INNING", "FIRST TO", "HOME RUN", "STRIKEOUTS", "BET THE",
    "MAKE THE PLAYOFFS", "WIN THE ", "WIN AL ", "WIN NL ",
    "DIVISION WINNER", "CUP", "CHAMPIONSHIP",
    "END IN A DRAW",  # 3-way market leak
)

# Odds API sport_key → izin verilen PM sport_tag'leri (false cross-sport match'i onler)
_SPORT_COMPAT: dict[str, frozenset[str]] = {
    "baseball_mlb": frozenset({"mlb", "baseball", "american-league", "national-league"}),
    "basketball_nba": frozenset({"nba", "basketball"}),
    "basketball_wnba": frozenset({"wnba", "basketball"}),
    "basketball_ncaab": frozenset({"ncaab", "cbb", "basketball", "college-basketball"}),
    "basketball_euroleague": frozenset({"euroleague", "basketball"}),
    "icehockey_nhl": frozenset({"nhl", "hockey", "ahl"}),
    "americanfootball_nfl": frozenset({"nfl", "football", "ncaa-football"}),
    "mma_mixed_martial_arts": frozenset({"ufc", "mma"}),
    "boxing_boxing": frozenset({"boxing"}),
    "tennis_atp_singles": frozenset({"atp", "tennis", "wta"}),
    "tennis_wta_singles": frozenset({"wta", "tennis", "atp"}),
    "cricket_ipl": frozenset({"ipl", "cricket", "indian-premier-league"}),
    "cricket_odi": frozenset({"cricket", "international-cricket"}),
    "cricket_international_t20": frozenset({"cricket", "international-cricket"}),
    "cricket_big_bash_league": frozenset({"cricket", "big-bash-league"}),
    "cricket_psl": frozenset({"cricket", "psl"}),
    "cricket_t20_blast": frozenset({"cricket", "t20-blast"}),
    "cricket_caribbean_premier_league": frozenset({"cricket", "caribbean-premier-league"}),
}


def _is_moneyline_question(question: str) -> bool:
    if not question:
        return False
    q_upper = question.upper()
    if " VS" not in q_upper and " VS." not in q_upper:
        return False
    return not any(p in q_upper for p in _NON_MONEYLINE_PATTERNS)


def _is_sport_compatible(odds_sport: str, pm_sport_tag: str) -> bool:
    allowed = _SPORT_COMPAT.get(odds_sport, frozenset())
    if not allowed:
        return True  # Unknown -> permissive
    return pm_sport_tag.lower() in allowed


def find_pm_match(
    event: dict,
    pm_markets: list[dict],
    odds_sport_key: str,
) -> dict | None:
    home = event.get("home_team", "")
    away = event.get("away_team", "")
    if not home or not away:
        return None

    best: dict | None = None
    best_conf = 0.0
    for pm in pm_markets:
        pm_sport = pm.get("_sport_tag", "")
        if not _is_sport_compatible(odds_sport_key, pm_sport):
            continue
        question = pm.get("question", "") or ""
        if not _is_moneyline_question(question):
            continue
        _, _, team_a, team_b = extract_pm_price_and_teams(pm)
        if not team_a or not team_b:
            continue
        if ":" in team_b or "/" in team_b:
            continue
        is_match, conf = match_pair((team_a, team_b), (home, away))
        if is_match and conf > best_conf:
            best = pm
            best_conf = conf

    return best if best_conf >= 0.80 else None


# ── Main loop ─────────────────────────────────────────────────────────

def write_snapshot(row: dict) -> None:
    date_str = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    file = LOG_DIR / f"{date_str}.jsonl"
    with open(file, "a", encoding="utf-8") as f:
        f.write(json.dumps(row, ensure_ascii=False) + "\n")


def main() -> None:
    api_key = os.getenv("ODDS_API_TEST_KEY", "")
    if not api_key:
        _log("[X] ODDS_API_TEST_KEY .env'de yok, cikiliyor")
        sys.exit(1)

    state = _load_state()
    credits_used: int = state.get("credits_used", 0)
    snapshots_by_match: dict[str, int] = defaultdict(
        int, state.get("snapshots_by_match", {}),
    )
    started_at = state.get("started_at", datetime.now(timezone.utc).isoformat())
    state["started_at"] = started_at

    _log("=" * 60)
    _log("Sharp vs Polymarket Recorder")
    _log(f"Target: {TARGET_MATCHES} macs x min {MIN_SNAPSHOTS} snapshot")
    _log(f"Credit budget: {CREDIT_LIMIT}/{500}")
    _log(f"Poll interval: {POLL_INTERVAL_SEC // 60} min")
    _log(f"Log: {LOG_DIR}")
    _log(f"State (devam durumu): credits={credits_used}, macs={len(snapshots_by_match)}")
    _log("=" * 60)

    poll_count = 0
    while _RUNNING:
        poll_count += 1
        _log(f"--- Poll {poll_count} basliyor ---")

        # 1) Gamma: tum canli PM sports marketleri
        pm_markets = fetch_polymarket_live_sports()
        _log(f"Polymarket: {len(pm_markets)} aktif sport market")

        # 2) Odds API: her spor icin h2h
        total_events_polled = 0
        snapshots_this_poll = 0
        sport_event_counts: dict[str, int] = {}

        for sport in ODDS_API_SPORTS:
            if not _RUNNING:
                break
            if credits_used >= CREDIT_LIMIT:
                _log(f"[!] Credit limit {CREDIT_LIMIT} asildi")
                break

            events = fetch_sport_events(sport, api_key)
            credits_used += 1
            sport_event_counts[sport] = len(events)

            if not events:
                continue

            for event in events:
                if not event.get("bookmakers"):
                    continue
                sharp_prob, sharp_count, sharp_price = compute_sharp_prob(event)
                if sharp_prob is None or sharp_count < 1:
                    continue

                pm = find_pm_match(event, pm_markets, sport)
                if pm is None:
                    continue

                pm_yes, pm_question, pm_ta, pm_tb = extract_pm_price_and_teams(pm)
                if pm_yes is None:
                    continue

                cid = pm.get("conditionId") or pm.get("condition_id") or ""
                slug = pm.get("slug", "")

                # Direction normalization — pm_yes hangi takim icin?
                # Fuzzy match: pm_ta (YES team) vs odds home team
                from src.domain.matching.pair_matcher import match_team as _match_one
                home_team = event.get("home_team", "")
                yes_is_home_match, yes_is_home_conf, _ = _match_one(pm_ta, home_team)
                yes_is_home = yes_is_home_match and yes_is_home_conf >= 0.80

                # sharp_prob_for_pm_yes: PM YES takiminin sharp olasiligi
                if yes_is_home:
                    sharp_prob_for_pm_yes = sharp_prob
                else:
                    sharp_prob_for_pm_yes = 1.0 - sharp_prob

                snapshot = {
                    "ts": datetime.now(timezone.utc).isoformat(),
                    "poll": poll_count,
                    "cid": cid,
                    "slug": slug,
                    "question": pm_question,
                    "sport_key": sport,
                    "event_id": event.get("id", ""),
                    "home": event.get("home_team", ""),
                    "away": event.get("away_team", ""),
                    "pm_yes_team": pm_ta,
                    "pm_no_team": pm_tb,
                    "yes_is_home": yes_is_home,
                    "commence_time": event.get("commence_time", ""),
                    "sharp_prob_home": round(sharp_prob, 4),
                    "sharp_prob_for_pm_yes": round(sharp_prob_for_pm_yes, 4),
                    "sharp_book_count": sharp_count,
                    "sharp_home_price": round(sharp_price, 3) if sharp_price else None,
                    "pm_yes_price": round(pm_yes, 4),
                    "pm_no_price": round(1 - pm_yes, 4),
                    "divergence_yes": round(sharp_prob_for_pm_yes - pm_yes, 4),
                }
                write_snapshot(snapshot)
                snapshots_by_match[cid] += 1
                snapshots_this_poll += 1
                total_events_polled += 1

        _log(
            f"Poll {poll_count}: {snapshots_this_poll} snapshot, "
            f"{len(snapshots_by_match)} benzersiz mac, "
            f"credit {credits_used}/{CREDIT_LIMIT}"
        )

        # Sport breakdown (ilk 10)
        top = sorted(sport_event_counts.items(), key=lambda x: -x[1])[:10]
        _log("  " + ", ".join(f"{s}={c}" for s, c in top if c > 0))

        # Save state
        state.update({
            "credits_used": credits_used,
            "snapshots_by_match": dict(snapshots_by_match),
            "last_poll_ts": datetime.now(timezone.utc).isoformat(),
            "poll_count": poll_count,
        })
        _save_state(state)

        # Stop conditions
        complete_matches = sum(1 for n in snapshots_by_match.values() if n >= MIN_SNAPSHOTS)
        _log(f"  Tam (>={MIN_SNAPSHOTS} snap): {complete_matches}")

        if STOP_ON_TARGET and complete_matches >= TARGET_MATCHES:
            _log("[OK] Hedef tamamlandi")
            break
        if credits_used >= CREDIT_LIMIT:
            _log("[!] Credit limit dolu")
            break

        # Max elapsed süre
        elapsed_sec = (
            datetime.now(timezone.utc) - datetime.fromisoformat(started_at)
        ).total_seconds()
        if elapsed_sec >= MAX_ELAPSED_SEC:
            _log(f"[!] Max sure asildi ({elapsed_sec/60:.0f} dk)")
            break

        if not _RUNNING:
            break

        # Sleep until next poll
        _log(f"Uyku: {POLL_INTERVAL_SEC // 60} dk ({datetime.now(timezone.utc).strftime('%H:%M:%S')} -> next {POLL_INTERVAL_SEC // 60}m)")
        for _ in range(POLL_INTERVAL_SEC):
            if not _RUNNING:
                break
            time.sleep(1)

    # ── Bitis ──
    elapsed_min = (
        datetime.now(timezone.utc) - datetime.fromisoformat(started_at)
    ).total_seconds() / 60

    final_complete = sum(1 for n in snapshots_by_match.values() if n >= MIN_SNAPSHOTS)
    sport_breakdown: dict[str, int] = defaultdict(int)
    # Rebuild sport breakdown from log file
    for f in sorted(LOG_DIR.glob("*.jsonl")):
        with open(f, encoding="utf-8") as fh:
            for line in fh:
                try:
                    row = json.loads(line)
                    sport_breakdown[row.get("sport_key", "?")] += 1
                except Exception:
                    pass

    sport_summary = ", ".join(
        f"{s}={n}" for s, n in sorted(sport_breakdown.items(), key=lambda x: -x[1])[:8]
    )

    reason = "manual stop"
    if STOP_ON_TARGET and final_complete >= TARGET_MATCHES:
        reason = "target reached"
    elif credits_used >= CREDIT_LIMIT:
        reason = "credit limit"
    elif elapsed_min * 60 >= MAX_ELAPSED_SEC - POLL_INTERVAL_SEC:
        reason = "max elapsed"

    msg = (
        f"<b>Sharp vs Poly Recorder bitti</b>\n\n"
        f"Sebep: <i>{reason}</i>\n"
        f"Sure: {elapsed_min:.0f} dk\n"
        f"Benzersiz mac: {len(snapshots_by_match)}\n"
        f"Tam (>={MIN_SNAPSHOTS} snap): {final_complete}\n"
        f"Credit kullanilan: {credits_used}/{CREDIT_LIMIT}\n"
        f"Toplam snapshot: {sum(snapshots_by_match.values())}\n"
        f"Poll turu: {poll_count}\n\n"
        f"Snapshot dagilimi:\n{sport_summary}\n\n"
        f"Log: <code>logs/sharp_vs_poly/</code>\n"
        f"Analiz: <code>python scripts/sharp_vs_poly_analyze.py</code>"
    )
    send_telegram(msg)

    _log("=" * 60)
    _log("Bitti")
    _log(f"Benzersiz mac: {len(snapshots_by_match)}, tam: {final_complete}")
    _log(f"Credit: {credits_used}/{CREDIT_LIMIT}")
    _log(f"Log: {LOG_DIR}")


if __name__ == "__main__":
    main()
