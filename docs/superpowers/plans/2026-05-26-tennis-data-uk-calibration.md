# Tennis Data UK — Closing Odds Calibration Tool Plan

> **For agentic workers:** Use superpowers:subagent-driven-development. Tasks below.

**Goal:** Download Tennis Data UK historical match data (free, includes Pinnacle closing odds). Build offline calibration tool that compares our Glicko model's win-probability predictions to Pinnacle closing odds for historical matches. Output: calibration table showing where our model systematically over/under-predicts. Future use: apply as bias correction in predictor.

**Honest scope note:** Tennis Data UK is HISTORICAL data only — closing odds from finished matches. NOT a real-time bookmaker anchor (Pinnacle real-time API is paid). Practical value is offline calibration, not live decision-making. Live anchor integration deferred (would need separate paid API).

**Repo:** `c:\Users\erimc\OneDrive\Desktop\CLAUDE PROJELER\tennis-lab\`

**Drift policy:** Per-task drift check; new tool lives in `scripts/calibration/` (new dir) — keep isolated from live bot code paths.

---

## Task 1: Download Tennis Data UK CSV/xlsx

**Files:**
- Create: `data/tennis_data_uk/atp_{year}.csv` and `wta_{year}.csv` for 2022-2026

**Source:** http://www.tennis-data.co.uk/ — free downloads, each year has separate xlsx for ATP and WTA.

- [ ] **Step 1: Verify URL pattern + try CSV-vs-XLSX**

```bash
PYTHONIOENCODING=utf-8 python -c "
import urllib.request
from pathlib import Path
dest = Path('data/tennis_data_uk')
dest.mkdir(parents=True, exist_ok=True)
for tour in ('atp', 'wta'):
    for year in (2022, 2023, 2024, 2025, 2026):
        # Try CSV first, fall back to xlsx
        for ext in ('csv', 'xlsx'):
            url = f'http://www.tennis-data.co.uk/{year}/{year}.{ext}' if tour=='atp' else f'http://www.tennis-data.co.uk/{year}w/{year}.{ext}'
            out = dest / f'{tour}_{year}.{ext}'
            try:
                req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
                with urllib.request.urlopen(req, timeout=15) as resp:
                    data = resp.read()
                if len(data) < 1000:
                    continue
                out.write_bytes(data)
                print(f'OK {tour} {year} .{ext}: {len(data)} bytes')
                break
            except Exception as e:
                continue
        else:
            print(f'FAIL {tour} {year}: tried csv + xlsx')
"
```

- [ ] **Step 2: List downloaded files + gitignore check**

```bash
ls -la data/tennis_data_uk/ 2>&1
echo "data/tennis_data_uk/" >> .gitignore  # if not already there
```

Verify .gitignore covers the new dir. If you added a line, commit just the .gitignore change.

- [ ] **Step 3: No data commit (gitignored)**

If schema differs between years, flag in report.

---

## Task 2: Tennis Data UK parser

**Files:**
- Create: `src/infrastructure/data/tennis_data_uk_client.py`
- Create: `tests/unit/infrastructure/data/test_tennis_data_uk_client.py`

**Schema (typical Tennis Data UK columns):**
- ATP/Date/Tournament/Location/Surface/Tier
- Winner/Loser/WRank/LRank/B365W/B365L/PSW/PSL (Pinnacle odds)
- Best of/Comment

PSW/PSL are Pinnacle's closing decimal odds. Win probability = 1 / (PSW + small margin).

- [ ] **Step 1: Write failing test**

```python
def test_tennis_data_uk_parser_reads_csv(tmp_path: Path) -> None:
    csv_content = (
        "ATP,Location,Tournament,Date,Surface,Round,Best of,Winner,Loser,WRank,LRank,B365W,B365L,PSW,PSL\n"
        "1,Sydney,ATP Cup,2024-01-05,Hard,F,3,Djokovic N.,Federer R.,1,5,1.50,2.50,1.55,2.40\n"
    )
    csv_path = tmp_path / "atp_2024.csv"
    csv_path.write_text(csv_content, encoding="utf-8")
    from src.infrastructure.data.tennis_data_uk_client import TennisDataUKClient
    client = TennisDataUKClient(cache_dir=tmp_path)
    matches = client.load_year("atp", 2024)
    assert len(matches) == 1
    m = matches[0]
    assert m.winner_name == "Djokovic N."
    assert m.surface == "Hard"
    assert m.pinnacle_winner_odds == 1.55  # PSW
    assert m.pinnacle_loser_odds == 2.40   # PSL
```

- [ ] **Step 2: Implement TennisDataUKClient + TennisDataUKMatch dataclass**

```python
@dataclass
class TennisDataUKMatch:
    tour: str            # "atp" | "wta"
    date: str            # ISO YYYY-MM-DD
    tournament: str
    surface: str
    winner_name: str
    loser_name: str
    winner_rank: int | None
    loser_rank: int | None
    pinnacle_winner_odds: float | None
    pinnacle_loser_odds: float | None


class TennisDataUKClient:
    def __init__(self, cache_dir: Path) -> None:
        self._cache_dir = Path(cache_dir)

    def load_year(self, tour: str, year: int) -> list[TennisDataUKMatch]:
        path = self._cache_dir / f"{tour}_{year}.csv"
        if not path.exists():
            return []
        with open(path, encoding="utf-8") as f:
            reader = csv.DictReader(f)
            return [self._parse_row(row, tour) for row in reader if row]
```

Handle missing fields gracefully (return None).

For xlsx fallback: add optional openpyxl-based reader. If openpyxl not installed, skip with warning.

- [ ] **Step 3: Tests + commit**

```bash
git add src/infrastructure/data/tennis_data_uk_client.py tests/unit/infrastructure/data/test_tennis_data_uk_client.py
git commit -m "feat(tennis-data-uk): parser for free historical closing odds (Pinnacle)"
```

---

## Task 3: Calibration analysis script

**Files:**
- Create: `scripts/calibration/compare_glicko_vs_pinnacle.py`
- (Optional) `tests/unit/scripts/test_compare_glicko_vs_pinnacle.py`

**Goal:** For each historical Tennis Data UK match, compute our Glicko model's predicted win probability for the winner. Compare to Pinnacle's implied probability (1/(PSW × overround_correction)). Output:
- Calibration table: model_prob_bucket → mean_actual_win_rate
- If our model says 60%, what actually happens 60% of the time? (Perfect calibration)
- Bias by surface, by rating-diff bucket

- [ ] **Step 1: Script outline**

```python
"""Compare Glicko model predictions to Pinnacle closing odds (calibration tool).

Outputs:
  - Calibration plot data: (model_prob_bucket, mean_actual_win_rate, n)
  - Surface bias: per-surface mean (model - pinnacle) error
  - Conclusion: is our model well-calibrated, optimistic, or pessimistic?

Run: python scripts/calibration/compare_glicko_vs_pinnacle.py
Reads:
  - data/tennis_data_uk/{atp,wta}_{year}.csv (historical matches + Pinnacle odds)
  - data/tennis_ratings.json (current Glicko ratings — uses snapshot, not match-time)
Outputs:
  - logs/calibration/glicko_vs_pinnacle_{date}.md (analysis report)
  - logs/calibration/calibration_table.csv
"""
```

- [ ] **Step 2: Implementation**

For each Tennis Data UK match:
1. Look up both players in our ratings JSON (by name match — handle missing).
2. Compute our predicted P(winner wins) via Glicko-2 + Klaassen-Magnus (use existing predictor functions).
3. Compute Pinnacle implied prob: `1 / pinnacle_winner_odds` (ignore overround for simplicity).
4. Record (model_prob, pinnacle_prob, actual_outcome=1).

Bucketize:
- model_prob: 0-10%, 10-20%, ..., 90-100% (10 buckets)
- For each bucket: count actual wins (always 1 since winner is given) — actually we need BOTH winners and losers.

Wait — Tennis Data UK only lists the WINNER as winner. We have (winner, loser) pairs. For each match, we can also COMPUTE the model's probability that the LOSER would win, and record actual=0.

So per match, 2 data points: (model_prob_W, 1) and (model_prob_L=1-prob_W, 0). Same for Pinnacle.

- [ ] **Step 3: Generate report**

```markdown
# Glicko vs Pinnacle Calibration — {date}

## Sample: {n} matches from 2022-2026 ATP + WTA

## Calibration Table
| Model Prob Bucket | Actual Win Rate | n | Error |
|---|---|---|---|
| 0-10% | 5% | 234 | -5% |
| 10-20% | 18% | 412 | +3% |
| ... | ... | ... | ... |

## Surface Bias
| Surface | Mean Model Prob | Mean Pinnacle Prob | Bias |
|---|---|---|---|
| Hard | 50.2% | 49.8% | +0.4% (optimistic) |
| Clay | ... | ... | ... |

## Conclusion
- Model is well/poorly calibrated in {bucket range}
- Surface bias: {summary}
- Recommended correction: {if any}
```

- [ ] **Step 4: Run on real data + commit script**

```bash
PYTHONIOENCODING=utf-8 python scripts/calibration/compare_glicko_vs_pinnacle.py
ls -la logs/calibration/
```

Verify report generates. Commit the script (not the report — logs gitignored):

```bash
git add scripts/calibration/
git commit -m "feat(calibration): Glicko vs Pinnacle calibration analysis tool"
```

---

## Per-task drift check

```bash
PYTHONIOENCODING=utf-8 grep -rn "TennisDataUK\|tennis_data_uk" src/ tests/ scripts/ 2>/dev/null
```

All hits should be in the new files. No accidental imports into live bot code.

## Notes

- Live bot is UNCHANGED by this plan. Calibration is offline tool.
- Integration as live anchor (auto-apply calibration to predictions) is FUTURE work — needs user decision after seeing calibration report.
