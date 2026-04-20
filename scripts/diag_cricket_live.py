"""SPEC-011 live diagnostic — CricAPI fetch + score_builder + score_exit."""
from __future__ import annotations

import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from dotenv import load_dotenv

load_dotenv()

from src.infrastructure.apis.cricket_client import CricketAPIClient
from src.orchestration.cricket_score_builder import (
    build_cricket_score_info,
    find_cricket_match,
)
from src.strategy.exit.cricket_score_exit import check as score_exit_check


def _mock_position(question: str, direction: str = "BUY_YES", sport_tag: str = "cricket_ipl"):
    class _P:
        pass
    p = _P()
    p.question = question
    p.slug = "cricipl-test"
    p.direction = direction
    p.event_id = "evt-diag"
    p.sport_tag = sport_tag
    return p


def main() -> None:
    key = os.getenv("CRICAPI_KEY", "")
    if not key:
        print("CRICAPI_KEY env yok — .env dosyasina ekle.")
        sys.exit(1)

    print("=" * 70)
    print("1) CricAPI /currentMatches fetch")
    print("=" * 70)
    client = CricketAPIClient(api_key=key)
    matches = client.get_current_matches()
    if matches is None:
        print("[X] Fetch basarisiz (quota dolu veya network hatasi)")
        sys.exit(1)

    print(f"[OK] {len(matches)} aktif mac alindi")
    print(f"     Quota: {client.quota.used_today}/{client.quota.daily_limit}")
    print()

    if not matches:
        print("Su an aktif cricket maci yok — builder/exit test edilemiyor.")
        print("Bu normal, aktif IPL saatlerinde tekrar dene.")
        return

    print("=" * 70)
    print("2) Ilk 5 mac detay")
    print("=" * 70)
    for i, m in enumerate(matches[:5], 1):
        print(f"[{i}] {m.name}")
        print(f"    Type: {m.match_type}  Started: {m.match_started}  Ended: {m.match_ended}")
        print(f"    Status: {m.status}")
        if m.innings:
            for inn in m.innings:
                print(
                    f"    {inn['team']} Inning {inn['inning_num']}: "
                    f"{inn['runs']}/{inn['wickets']} ({inn['overs']} overs)"
                )
        print()

    print("=" * 70)
    print("3) Bir maci score_builder'dan gecir")
    print("=" * 70)
    # Aktif chase maci bul (2 innings'i olan)
    chase_match = next((m for m in matches if len(m.innings) >= 2 and not m.match_ended), None)
    if chase_match is None:
        print("Aktif 2. innings (chase) maci yok — builder sadece innings 1 ile test edilecek.")
        any_started = next((m for m in matches if m.match_started and m.innings), None)
        if any_started is None:
            print("Hicbir baslamis mac yok — builder test edilemez.")
            return
        chase_match = any_started

    print(f"Kullanilan mac: {chase_match.name}")
    # Pozisyon: ilk takimi destekliyoruz (BUY_YES)
    pos = _mock_position(chase_match.name, direction="BUY_YES")
    score_info = build_cricket_score_info(pos, chase_match)
    print(f"score_info: {score_info}")
    print()

    print("=" * 70)
    print("4) score_exit kontrolu (C1/C2/C3)")
    print("=" * 70)
    result = score_exit_check(score_info, current_price=0.20, sport_tag="cricket_ipl")
    if result is None:
        print("[INFO] Exit tetiklenmedi — mac normal seyrinde.")
    else:
        print(f"[EXIT] {result.reason.value}: {result.detail}")
    print()

    print("=" * 70)
    print("5) Polymarket IPL mac testi (gercek fuzzy match)")
    print("=" * 70)
    # Bot'un skipped'te bulduğu maç: "Indian Premier League: Gujarat Titans vs Mumbai Indians"
    pm_question = "Indian Premier League: Gujarat Titans vs Mumbai Indians"
    pm_pos = _mock_position(pm_question, direction="BUY_YES")
    matched = find_cricket_match(pm_pos, matches)
    if matched is None:
        print(f"[?] Polymarket sorusu '{pm_question}' CricAPI maclariyla eslesmedi.")
        print("    (Mac bugun oynanmiyorsa normal — fuzzy match aktif olmasi gerekiyor)")
    else:
        print(f"[OK] Eslesme: {matched.name}")
        info = build_cricket_score_info(pm_pos, matched)
        print(f"    score_info: {info}")


if __name__ == "__main__":
    main()
