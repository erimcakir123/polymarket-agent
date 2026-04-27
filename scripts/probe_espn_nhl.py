"""
Probe ESPN NHL endpoints to capture response structure across game states.

Output: data/probes/nhl/<game_id>_<state>.json files
        data/probes/nhl/SUMMARY.md (human-readable analysis)

Run: python scripts/probe_espn_nhl.py

Read-only against ESPN. No state modification, no production code touched.
"""
from __future__ import annotations

import json
import time
from pathlib import Path
from datetime import datetime, timezone, timedelta
import urllib.request

OUTPUT_DIR = Path("data/probes/nhl")

SCOREBOARD_URL = "https://site.api.espn.com/apis/site/v2/sports/hockey/nhl/scoreboard"
SCOREBOARD_DATE_URL = "https://site.api.espn.com/apis/site/v2/sports/hockey/nhl/scoreboard?dates={date}"
SUMMARY_URL = "https://site.api.espn.com/apis/site/v2/sports/hockey/nhl/summary?event={game_id}"

# Fallback game_ids: 2024 Stanley Cup Final G7 (EDM vs FLA), 2024 SCF G6
FALLBACK_GAME_IDS = ["401688971", "401688970", "401688969"]


def fetch_json(url: str) -> dict:
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
    with urllib.request.urlopen(req, timeout=15) as r:
        return json.loads(r.read())


def categorize_game_state(event: dict) -> str:
    status = event.get("status", {})
    state = status.get("type", {}).get("state", "")
    detail = status.get("type", {}).get("detail", "").lower()
    period = status.get("period", 0)

    if state == "pre":
        return "pre"
    if state == "in":
        if "shootout" in detail:
            return "live_so"
        if "ot" in detail or "overtime" in detail or period >= 4:
            return "live_ot"
        if period == 1:
            return "live_p1"
        if period == 2:
            return "live_p2"
        if period == 3:
            return "live_p3"
        return "live_unknown"
    if state == "post":
        if "so" in detail or "shootout" in detail:
            return "final_so"
        if "ot" in detail or "overtime" in detail:
            return "final_ot"
        return "final"
    return "unknown"


def save_event(event: dict, state_label: str, source: str) -> Path:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    game_id = event.get("id", "unknown")
    fname = f"{game_id}_{state_label}_{source}.json"
    path = OUTPUT_DIR / fname
    with open(path, "w", encoding="utf-8") as f:
        json.dump(event, f, indent=2, ensure_ascii=False)
    return path


def probe_scoreboard_date(date_str: str) -> dict[str, Path]:
    """Fetch scoreboard for a specific YYYYMMDD date."""
    url = SCOREBOARD_DATE_URL.format(date=date_str)
    print(f"  Trying {date_str}: {url}")
    sb = fetch_json(url)
    events = sb.get("events", [])
    saved_states: dict[str, Path] = {}
    for event in events:
        state = categorize_game_state(event)
        if state not in saved_states:
            path = save_event(event, state, "scoreboard")
            saved_states[state] = path
            print(f"    Saved {state}: {path.name}")
    return saved_states


def probe_scoreboard() -> dict[str, Path]:
    """Get current day, fallback to recent days if no events."""
    print(f"\n[1/3] Fetching scoreboard: {SCOREBOARD_URL}")
    sb = fetch_json(SCOREBOARD_URL)
    events = sb.get("events", [])
    print(f"  Got {len(events)} events today")

    saved_states: dict[str, Path] = {}
    for event in events:
        state = categorize_game_state(event)
        if state not in saved_states:
            path = save_event(event, state, "scoreboard")
            saved_states[state] = path
            print(f"  Saved {state}: {path.name}")

    if not saved_states:
        print("  No events today. Searching last 14 days...")
        today = datetime.now(timezone.utc)
        for delta in range(1, 15):
            past = today - timedelta(days=delta)
            date_str = past.strftime("%Y%m%d")
            time.sleep(0.3)
            try:
                day_states = probe_scoreboard_date(date_str)
                saved_states.update({k: v for k, v in day_states.items() if k not in saved_states})
                if len(saved_states) >= 3:
                    break
            except Exception as e:
                print(f"    WARN: {date_str} fetch failed: {e}")

    if not saved_states:
        print("  Still no events. Using fallback hardcoded game_ids (2024 SCF).")

    return saved_states


def probe_fallback_summaries() -> dict[str, Path]:
    """Fetch summary for known completed finals — captures final/final_ot/final_so."""
    saved: dict[str, Path] = {}
    for game_id in FALLBACK_GAME_IDS:
        try:
            time.sleep(0.5)
            summary = fetch_json(SUMMARY_URL.format(game_id=game_id))
            # determine state from summary header
            events = summary.get("header", {}).get("competitions", [])
            state = "final"
            if events:
                comp = events[0]
                detail = comp.get("status", {}).get("type", {}).get("detail", "").lower()
                if "so" in detail or "shootout" in detail:
                    state = "final_so"
                elif "ot" in detail or "overtime" in detail:
                    state = "final_ot"
            label = f"{state}_fallback"
            if label not in saved:
                path = OUTPUT_DIR / f"{game_id}_{label}_summary.json"
                OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
                with open(path, "w", encoding="utf-8") as f:
                    json.dump(summary, f, indent=2, ensure_ascii=False)
                saved[label] = path
                print(f"  Fallback saved {label}: {path.name}")
        except Exception as e:
            print(f"  WARN: fallback {game_id} failed: {e}")
    return saved


def probe_summaries(saved_scoreboard_states: dict[str, Path]) -> dict[str, Path]:
    print(f"\n[2/3] Fetching summary endpoints...")
    saved_summaries: dict[str, Path] = {}

    for state, sb_path in saved_scoreboard_states.items():
        with open(sb_path) as f:
            event = json.load(f)
        game_id = event.get("id")
        if not game_id:
            continue
        try:
            time.sleep(0.5)
            summary = fetch_json(SUMMARY_URL.format(game_id=game_id))
            path = save_event(summary, state, "summary")
            saved_summaries[state] = path
            print(f"  Saved {state} summary: {path.name}")
        except Exception as e:
            print(f"  WARN: summary fetch failed for {game_id} ({state}): {e}")

    if not saved_summaries:
        print("  No scoreboard summaries — fetching fallback completed games...")
        saved_summaries = probe_fallback_summaries()

    return saved_summaries


def get_nested(d: dict, path: str):
    parts = path.split(".")
    cur = d
    for p in parts:
        if cur is None:
            return None
        if p.isdigit():
            idx = int(p)
            if isinstance(cur, list) and idx < len(cur):
                cur = cur[idx]
            else:
                return None
        else:
            if isinstance(cur, dict):
                cur = cur.get(p)
            else:
                return None
    return cur


SCOREBOARD_FIELDS = [
    "id",
    "status.type.state",
    "status.type.detail",
    "status.type.shortDetail",
    "status.period",
    "status.clock",
    "status.displayClock",
    "competitions.0.competitors",
    "competitions.0.competitors.0.score",
    "competitions.0.competitors.0.team.id",
    "competitions.0.competitors.0.team.abbreviation",
    "competitions.0.competitors.0.team.displayName",
    "competitions.0.competitors.0.homeAway",
    "competitions.0.competitors.0.records",
    "competitions.0.competitors.0.probables",
    "competitions.0.competitors.0.statistics",
    "competitions.0.situation",
    "competitions.0.situation.lastPlay",
    "competitions.0.situation.onIce",
    "competitions.0.broadcasts",
]

SUMMARY_FIELDS = [
    "header.id",
    "header.competitions.0.status.type.state",
    "header.competitions.0.status.type.detail",
    "header.competitions.0.status.period",
    "header.competitions.0.status.clock",
    "header.competitions.0.status.displayClock",
    "header.competitions.0.competitors.0.score",
    "header.competitions.0.competitors.0.team.abbreviation",
    "header.competitions.0.competitors.0.probables",
    "boxscore",
    "boxscore.teams",
    "boxscore.players",
    "rosters",
    "leaders",
    "plays",
    "plays.0",
    "situation",
    "situation.lastPlay",
    "pickcenter",
    "predictor",
    "news",
    "videos",
]


def analyze_field_presence(saved_paths: dict[str, Path], fields: list[str]) -> dict:
    result = {}
    for state, path in saved_paths.items():
        with open(path, encoding="utf-8") as f:
            data = json.load(f)
        result[state] = {}
        for fp in fields:
            val = get_nested(data, fp)
            result[state][fp] = {
                "present": val is not None,
                "type": type(val).__name__ if val is not None else None,
                "preview": str(val)[:120] if val is not None else None,
            }
    return result


def write_summary_md(
    sb_states: dict[str, Path],
    sm_states: dict[str, Path],
    sb_analysis: dict,
    sm_analysis: dict,
) -> Path:
    md_path = OUTPUT_DIR / "SUMMARY.md"
    lines: list[str] = []
    lines.append("# ESPN NHL Probe Summary")
    lines.append(f"\nGenerated: {datetime.now(timezone.utc).isoformat()}")

    lines.append("\n## States captured")
    lines.append("\n### Scoreboard endpoint")
    for state, path in sorted(sb_states.items()):
        lines.append(f"- `{state}` -> {path.name}")
    lines.append("\n### Summary endpoint")
    for state, path in sorted(sm_states.items()):
        lines.append(f"- `{state}` -> {path.name}")

    if sb_analysis:
        lines.append("\n## Field presence - scoreboard endpoint\n")
        states = list(sb_analysis.keys())
        lines.append("| Field | " + " | ".join(states) + " |")
        lines.append("|" + "---|" * (len(states) + 1))
        first = next(iter(sb_analysis.values()))
        for fp in first.keys():
            row = [fp]
            for state in states:
                info = sb_analysis[state].get(fp, {})
                row.append(info["type"] if info.get("present") else "-")
            lines.append("| " + " | ".join(row) + " |")

    if sm_analysis:
        lines.append("\n## Field presence - summary endpoint\n")
        states = list(sm_analysis.keys())
        lines.append("| Field | " + " | ".join(states) + " |")
        lines.append("|" + "---|" * (len(states) + 1))
        first = next(iter(sm_analysis.values()))
        for fp in first.keys():
            row = [fp]
            for state in states:
                info = sm_analysis[state].get(fp, {})
                row.append(info["type"] if info.get("present") else "-")
            lines.append("| " + " | ".join(row) + " |")

    lines.append("\n## Sample field values\n")
    for state in sorted(sb_analysis.keys()):
        lines.append(f"\n### {state} - scoreboard")
        for fp, info in sb_analysis[state].items():
            if info.get("present"):
                lines.append(f"- `{fp}`: `{info['preview']}`")

    for state in sorted(sm_analysis.keys()):
        lines.append(f"\n### {state} - summary")
        for fp, info in sm_analysis[state].items():
            if info.get("present"):
                lines.append(f"- `{fp}`: `{info['preview']}`")

    md_path.write_text("\n".join(lines), encoding="utf-8")
    print(f"\n[3/3] Wrote {md_path}")
    return md_path


def main() -> None:
    print(f"ESPN NHL probe - {datetime.now().isoformat()}")
    print(f"Output: {OUTPUT_DIR}/")

    sb_states = probe_scoreboard()
    sm_states = probe_summaries(sb_states)

    sb_analysis = analyze_field_presence(sb_states, SCOREBOARD_FIELDS)
    sm_analysis = analyze_field_presence(sm_states, SUMMARY_FIELDS)

    write_summary_md(sb_states, sm_states, sb_analysis, sm_analysis)
    print("\nDone. Inspect data/probes/nhl/SUMMARY.md")


if __name__ == "__main__":
    main()
