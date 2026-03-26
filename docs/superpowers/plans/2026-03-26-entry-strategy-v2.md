# Entry Strategy V2 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Rewrite entry logic to use Winner/Underdog/DeadZone modes, fix Scout spam bug, and reframe AI confidence as data quality rather than outcome certainty.

**Architecture:** Three changes in three files — no new files, no cross-file coupling.
(1) Scout dedup: add in-memory cooldown to prevent re-runs within same cycle window.
(2) EntryGate: replace edge-only entry logic with three-mode classifier (Winner / DeadZone / Underdog), each with its own confidence requirements and rank score formula.
(3) AI prompt: redefine confidence grades as data availability tiers, not outcome certainty.

**Tech Stack:** Python 3.11, no new dependencies.

---

## Context for implementer

**Branch:** `rewrite/clean-architecture`
**Working dir:** `C:\Users\erimc\OneDrive\Desktop\CLAUDE\Polymarket Agent`

The three tasks are fully independent. Each can be implemented and committed without the others. Do NOT restructure any file — surgical edits only.

### Trading strategy the user confirmed:

| Mode | Condition | Confidence required | Edge required |
|------|-----------|-------------------|---------------|
| **WINNER** | AI direction prob ≥ 65% | A or B+ only | None |
| **DEADZONE** | 50% ≤ AI direction prob < 65% | A, B+, B- allowed | Yes (existing min_edge) |
| **UNDERDOG** | AI direction prob < 50% but meaningful edge | A or B+ only | Yes (existing min_edge) |

**Direction prob** = ai_prob if BUY_YES, (1 - ai_prob) if BUY_NO.

**Rank score formula:**
- WINNER: `direction_prob × conf_score`
- DEADZONE / UNDERDOG: `edge × direction_prob × conf_score`

Where `conf_score = {"A": 4, "B+": 3, "B-": 2, "C": 1}`.

**Position sizing:** Winner mode uses a fixed floor edge (0.05) passed to existing risk calculator so Kelly stays positive. Edge modes use actual edge. Confidence level already scales the output inside risk manager.

---

## Task 1: Fix Scout spam — in-memory cooldown

**Files:**
- Modify: `src/scout_scheduler.py`

**Bug:** `should_run_scout()` checks a marker file but the file's datetime parsing can fail silently (exception → `pass` → returns `True`). Result: scout runs every cycle at hour 18 UTC (21:00 Turkey time), reporting 51 "new" matches each time.

**Fix:** Add `self._last_run_ts: float = 0.0` to `__init__`. At top of `run_scout()`, guard with a 4-hour in-memory check. This is reliable regardless of file system issues.

- [ ] **Step 1: Write the failing test**

```python
# tests/test_scout_dedup.py
import time
from unittest.mock import MagicMock, patch

def _make_scout():
    from src.scout_scheduler import ScoutScheduler
    sports = MagicMock()
    esports = MagicMock()
    esports.available = False
    with patch("src.scout_scheduler.SCOUT_QUEUE_FILE") as qf:
        qf.exists.return_value = False
        s = ScoutScheduler(sports, esports)
    return s

def test_scout_does_not_rerun_within_4h():
    """run_scout called twice in quick succession must return 0 on 2nd call."""
    scout = _make_scout()
    scout._last_run_ts = time.time()  # Pretend ran just now
    with patch.object(scout, "_fetch_espn_upcoming", return_value=[]):
        with patch.object(scout, "_fetch_esports_upcoming", return_value=[]):
            result = scout.run_scout()
    assert result == 0, f"Expected 0, got {result}"

def test_scout_runs_after_cooldown_expires():
    """run_scout should proceed when last run was >4h ago."""
    scout = _make_scout()
    scout._last_run_ts = time.time() - 5 * 3600  # 5 hours ago
    with patch.object(scout, "_fetch_espn_upcoming", return_value=[]):
        with patch.object(scout, "_fetch_esports_upcoming", return_value=[]):
            with patch.object(scout, "_save_queue"):
                with patch("src.scout_scheduler.SCOUT_MARKER_FILE") as mf:
                    mf.parent = MagicMock()
                    result = scout.run_scout()
    assert result == 0  # 0 new matches (empty feeds), but ran
    assert scout._last_run_ts > time.time() - 10  # timestamp was updated
```

- [ ] **Step 2: Run test to verify it fails**

```bash
cd "C:\Users\erimc\OneDrive\Desktop\CLAUDE\Polymarket Agent"
python -m pytest tests/test_scout_dedup.py -v 2>&1 | head -30
```
Expected: FAIL — `ScoutScheduler` has no `_last_run_ts` attribute.

- [ ] **Step 3: Add `_last_run_ts` to `__init__` and guard in `run_scout`**

In `src/scout_scheduler.py`, find `__init__` (line 53) and add the field:

```python
def __init__(self, sports: SportsDataClient, esports: EsportsDataClient) -> None:
    self.sports = sports
    self.esports = esports
    self._queue: Dict[str, dict] = {}
    self._last_run_ts: float = 0.0          # ← ADD THIS
    self._load_queue()
```

In `run_scout()` (line 110), add the guard as the FIRST thing in the method body, before the logger.info:

```python
def run_scout(self) -> int:
    # In-memory cooldown: never run twice within 4 hours
    _COOLDOWN_SECS = 4 * 3600
    if time.time() - self._last_run_ts < _COOLDOWN_SECS:
        logger.debug("Scout cooldown active — skipping (%.1fh since last run)",
                     (time.time() - self._last_run_ts) / 3600)
        return 0

    logger.info("=== SCOUT RUN START ===")
    now = datetime.now(timezone.utc)
    new_count = 0
    # ... rest of method unchanged ...
```

At the very end of `run_scout()`, right before `return new_count`, update the timestamp:

```python
    self._last_run_ts = time.time()   # ← ADD before return
    logger.info("=== SCOUT COMPLETE: %d new, %d total in queue ===", new_count, len(self._queue))
    return new_count
```

- [ ] **Step 4: Run tests to verify they pass**

```bash
python -m pytest tests/test_scout_dedup.py -v
```
Expected: 2 PASS

- [ ] **Step 5: Commit**

```bash
git add src/scout_scheduler.py tests/test_scout_dedup.py
git commit -m "fix: add 4h in-memory cooldown to prevent Scout spam re-runs"
```

---

## Task 2: Three-mode entry strategy in EntryGate

**Files:**
- Modify: `src/entry_gate.py` lines 360–542 (`_evaluate_candidates` method only)

**Replace the current edge-first flow with a three-mode classifier.** The method signature and everything outside it stay unchanged.

### New flow (replaces lines 376–541):

```
for each market:
  1. Skip if confidence in _CONF_SKIP (C / "" / ?)
  2. Sanity check (unchanged)
  3. Odds API anchor (unchanged)
  4. Classify mode: WINNER / DEADZONE / UNDERDOG / HOLD
     - mode determined by direction_prob (AI prob for chosen side)
     - direction chosen by: Winner side > DeadZone > Underdog > HOLD
  5. Filter by mode+confidence:
     - WINNER/UNDERDOG → A or B+ only
     - DEADZONE → A, B+, B- allowed
  6. Size position (winner: floor edge 0.05; others: actual edge)
  7. Rank score:
     - WINNER: direction_prob × conf_score
     - DEADZONE/UNDERDOG: edge × direction_prob × conf_score
```

- [ ] **Step 1: Write the failing test**

```python
# tests/test_entry_modes.py
"""Tests for three-mode entry strategy."""
from unittest.mock import MagicMock, patch
import pytest


def _make_estimate(ai_prob, confidence):
    est = MagicMock()
    est.ai_probability = ai_prob
    est.confidence = confidence
    return est


def _make_market(yes_price, cid="cid-001", slug="test-market", question="Will X win?"):
    m = MagicMock()
    m.condition_id = cid
    m.yes_price = yes_price
    m.slug = slug
    m.question = question
    m.sport_tag = ""
    return m


def _make_gate():
    """Create a minimal EntryGate with mocked dependencies."""
    from src.entry_gate import EntryGate
    cfg = MagicMock()
    cfg.edge.min_edge = 0.06
    cfg.edge.fill_ratio_scaling = False
    cfg.edge.default_spread = 0.0
    cfg.edge.confidence_multipliers = None
    cfg.consensus_entry.enabled = False
    cfg.risk.max_positions = 10
    gate = EntryGate.__new__(EntryGate)
    gate.config = cfg
    gate.portfolio = MagicMock()
    gate.portfolio.active_position_count = 0
    gate.portfolio.count_by_entry_reason = MagicMock(return_value=0)
    gate.odds_api = MagicMock()
    gate.odds_api.available = False
    gate.manip_guard = MagicMock()
    gate.manip_guard.check.return_value = MagicMock(ok=True)
    gate.manip_guard.adjust_position_size = lambda size, _: size
    gate.risk = MagicMock()
    gate.risk.calculate_position_size = MagicMock(return_value=10.0)
    gate.trade_log = MagicMock()
    gate._far_market_ids = set()
    gate._analyzed_market_ids = {}
    return gate


def test_winner_mode_enters_without_edge():
    """AI ≥ 65% should enter even if market price equals AI probability (no edge)."""
    gate = _make_gate()
    # AI says 80%, market says 80% → zero edge, but should WINNER-enter
    market = _make_market(yes_price=0.80)
    estimate = _make_estimate(ai_prob=0.80, confidence="B+")
    with patch("src.sanity_check.check_bet_sanity") as mock_sanity:
        mock_sanity.return_value = MagicMock(ok=True)
        with patch("src.probability_engine.calculate_anchored_probability") as mock_anchor:
            mock_anchor.return_value = MagicMock(probability=0.80)
            with patch("src.probability_engine.get_edge_threshold_adjustment", return_value=0.0):
                candidates = gate._evaluate_candidates(
                    [market], {market.condition_id: estimate},
                    bankroll=1000.0, cycle_count=1, fresh_scan=True,
                )
    assert len(candidates) == 1
    assert candidates[0]["mode"] == "WINNER"
    from src.models import Direction
    assert candidates[0]["direction"] == Direction.BUY_YES


def test_winner_mode_b_minus_rejected():
    """Winner mode should reject B- confidence."""
    gate = _make_gate()
    market = _make_market(yes_price=0.50)
    estimate = _make_estimate(ai_prob=0.80, confidence="B-")
    with patch("src.sanity_check.check_bet_sanity") as mock_sanity:
        mock_sanity.return_value = MagicMock(ok=True)
        with patch("src.probability_engine.calculate_anchored_probability") as mock_anchor:
            mock_anchor.return_value = MagicMock(probability=0.80)
            with patch("src.probability_engine.get_edge_threshold_adjustment", return_value=0.0):
                candidates = gate._evaluate_candidates(
                    [market], {market.condition_id: estimate},
                    bankroll=1000.0, cycle_count=1, fresh_scan=True,
                )
    assert len(candidates) == 0


def test_underdog_enters_with_edge_a_plus():
    """AI 40%, market 12% → underdog YES — enters if A/B+ confidence."""
    gate = _make_gate()
    market = _make_market(yes_price=0.12)
    estimate = _make_estimate(ai_prob=0.40, confidence="A")
    with patch("src.sanity_check.check_bet_sanity") as mock_sanity:
        mock_sanity.return_value = MagicMock(ok=True)
        with patch("src.probability_engine.calculate_anchored_probability") as mock_anchor:
            mock_anchor.return_value = MagicMock(probability=0.40)
            with patch("src.probability_engine.get_edge_threshold_adjustment", return_value=0.0):
                candidates = gate._evaluate_candidates(
                    [market], {market.condition_id: estimate},
                    bankroll=1000.0, cycle_count=1, fresh_scan=True,
                )
    assert len(candidates) == 1
    assert candidates[0]["mode"] == "UNDERDOG"


def test_underdog_rejects_b_minus():
    """Underdog mode must reject B- confidence."""
    gate = _make_gate()
    market = _make_market(yes_price=0.12)
    estimate = _make_estimate(ai_prob=0.40, confidence="B-")
    with patch("src.sanity_check.check_bet_sanity") as mock_sanity:
        mock_sanity.return_value = MagicMock(ok=True)
        with patch("src.probability_engine.calculate_anchored_probability") as mock_anchor:
            mock_anchor.return_value = MagicMock(probability=0.40)
            with patch("src.probability_engine.get_edge_threshold_adjustment", return_value=0.0):
                candidates = gate._evaluate_candidates(
                    [market], {market.condition_id: estimate},
                    bankroll=1000.0, cycle_count=1, fresh_scan=True,
                )
    assert len(candidates) == 0


def test_deadzone_allows_b_minus():
    """Dead zone (55% AI, 40% market) allows B- confidence."""
    gate = _make_gate()
    market = _make_market(yes_price=0.40)
    estimate = _make_estimate(ai_prob=0.55, confidence="B-")
    with patch("src.sanity_check.check_bet_sanity") as mock_sanity:
        mock_sanity.return_value = MagicMock(ok=True)
        with patch("src.probability_engine.calculate_anchored_probability") as mock_anchor:
            mock_anchor.return_value = MagicMock(probability=0.55)
            with patch("src.probability_engine.get_edge_threshold_adjustment", return_value=0.0):
                candidates = gate._evaluate_candidates(
                    [market], {market.condition_id: estimate},
                    bankroll=1000.0, cycle_count=1, fresh_scan=True,
                )
    assert len(candidates) == 1
    assert candidates[0]["mode"] == "DEADZONE"


def test_winner_score_higher_than_edge_score():
    """Winner candidate (95% AI, B+) should outrank edge candidate (20% edge, A)."""
    from src.models import Direction
    gate = _make_gate()

    m_winner = _make_market(yes_price=0.70, cid="win-001", slug="winner", question="Team A wins?")
    est_winner = _make_estimate(ai_prob=0.95, confidence="B+")

    m_edge = _make_market(yes_price=0.30, cid="edge-001", slug="edger", question="Team B wins?")
    est_edge = _make_estimate(ai_prob=0.50, confidence="A")  # dead zone, 20% edge

    estimates = {
        "win-001": est_winner,
        "edge-001": est_edge,
    }
    with patch("src.sanity_check.check_bet_sanity") as mock_sanity:
        mock_sanity.return_value = MagicMock(ok=True)
        with patch("src.probability_engine.calculate_anchored_probability") as mock_anchor:
            def anchor(ai_prob, **kwargs):
                return MagicMock(probability=ai_prob)
            mock_anchor.side_effect = anchor
            with patch("src.probability_engine.get_edge_threshold_adjustment", return_value=0.0):
                candidates = gate._evaluate_candidates(
                    [m_winner, m_edge], estimates,
                    bankroll=1000.0, cycle_count=1, fresh_scan=True,
                )
    assert len(candidates) == 2
    assert candidates[0]["market"].condition_id == "win-001", "Winner should rank first"
```

- [ ] **Step 2: Run test to verify it fails**

```bash
python -m pytest tests/test_entry_modes.py -v 2>&1 | head -50
```
Expected: FAIL — `_evaluate_candidates` has no "mode" key in candidates dict, and winner entry logic doesn't exist.

- [ ] **Step 3: Replace `_evaluate_candidates` body**

Open `src/entry_gate.py`. Replace the ENTIRE body of `_evaluate_candidates` (lines 368–542, keeping the method signature on line 360–367 intact) with:

```python
        """Evaluate each market, return ranked candidate list."""
        from src.edge_calculator import scale_min_edge
        from src.probability_engine import calculate_anchored_probability, get_edge_threshold_adjustment
        from src.sanity_check import check_bet_sanity
        from src.models import Direction

        cfg = self.config
        candidates: list[dict] = []
        _CONF_SKIP = {"C", "", "?"}
        _WINNER_UNDERDOG_CONF = {"A", "B+"}  # B- not allowed in winner/underdog modes

        # Fill-ratio edge scaling
        fill_ratio = self.portfolio.active_position_count / max(1, cfg.risk.max_positions)
        effective_min_edge = cfg.edge.min_edge
        if cfg.edge.fill_ratio_scaling:
            effective_min_edge = scale_min_edge(cfg.edge.min_edge, fill_ratio)

        for market in markets:
            cid = market.condition_id

            estimate = estimates.get(cid)
            if estimate is None:
                continue
            if estimate.confidence in _CONF_SKIP:
                continue

            # ── Sanity check ────────────────────────────────────────────────
            sanity_result = check_bet_sanity(
                question=getattr(market, "question", ""),
                direction="BUY_YES",
                ai_probability=estimate.ai_probability,
                market_price=market.yes_price,
                edge=0.0,
                confidence=estimate.confidence,
            )
            if not sanity_result.ok:
                self.trade_log.log({
                    "market": market.slug, "action": "BLOCKED",
                    "question": market.question,
                    "ai_prob": estimate.ai_probability, "price": market.yes_price,
                    "rejected": f"SANITY: {sanity_result.reason}",
                })
                continue

            # ── Bookmaker anchor (read-only, no new API calls if unavailable) ─
            _is_esports_mkt = is_esports(getattr(market, "sport_tag", "") or "")
            _anchor_book_prob = None
            _anchor_num_books = 0
            if not _is_esports_mkt and self.odds_api.available:
                try:
                    _mkt_odds = self.odds_api.get_market_odds(market)
                    if _mkt_odds:
                        _anchor_book_prob = _mkt_odds.get("probability")
                        _anchor_num_books = _mkt_odds.get("num_bookmakers", 0)
                except Exception:
                    pass
            anchored = calculate_anchored_probability(
                ai_prob=estimate.ai_probability,
                bookmaker_prob=_anchor_book_prob,
                num_bookmakers=_anchor_num_books,
            )
            _edge_threshold_adj = get_edge_threshold_adjustment(anchored)
            threshold = effective_min_edge + _edge_threshold_adj

            # ── Three-mode classifier ─────────────────────────────────────────
            ai_p = anchored.probability          # P(YES)
            ai_n = 1.0 - ai_p                   # P(NO)
            mkt_p = market.yes_price             # market P(YES)
            mkt_n = 1.0 - mkt_p

            edge_yes = ai_p - mkt_p             # positive → YES has value
            edge_no = ai_n - mkt_n              # = mkt_p - ai_p, positive → NO has value

            def _classify_side(direction_prob: float, direction_edge: float) -> str:
                if direction_prob >= 0.65:
                    return "WINNER"
                if direction_prob >= 0.50 and direction_edge >= threshold:
                    return "DEADZONE"
                if direction_prob < 0.50 and direction_edge >= threshold:
                    return "UNDERDOG"
                return "HOLD"

            yes_mode = _classify_side(ai_p, edge_yes)
            no_mode = _classify_side(ai_n, edge_no)

            # Pick direction: Winner > DeadZone > Underdog > Hold
            _MODE_PRIORITY = {"WINNER": 4, "DEADZONE": 3, "UNDERDOG": 2, "HOLD": 1}
            if _MODE_PRIORITY[yes_mode] >= _MODE_PRIORITY[no_mode]:
                direction = Direction.BUY_YES
                mode = yes_mode
                edge = edge_yes
                direction_prob = ai_p
            else:
                direction = Direction.BUY_NO
                mode = no_mode
                edge = edge_no
                direction_prob = ai_n

            if mode == "HOLD":
                self.trade_log.log({
                    "market": market.slug, "action": "HOLD",
                    "ai_prob": estimate.ai_probability, "price": market.yes_price,
                    "edge_yes": round(edge_yes, 4), "edge_no": round(edge_no, 4),
                })
                self._analyzed_market_ids[cid] = time.time()
                continue

            # ── Confidence gate (mode-specific) ──────────────────────────────
            if mode in ("WINNER", "UNDERDOG") and estimate.confidence not in _WINNER_UNDERDOG_CONF:
                logger.info("%s mode requires A/B+, got %s: %s",
                            mode, estimate.confidence, market.slug[:40])
                self.trade_log.log({
                    "market": market.slug, "action": "HOLD",
                    "rejected": f"{mode}_CONF_GATE: conf={estimate.confidence} (need A/B+)",
                })
                continue

            # ── Esports underdog guard ────────────────────────────────────────
            if is_esports(getattr(market, "sport_tag", "") or ""):
                if direction == Direction.BUY_YES and ai_p < 0.50 and mode != "UNDERDOG":
                    self.trade_log.log({
                        "market": market.slug, "action": "HOLD",
                        "rejected": f"ESPORTS_UNDERDOG_NO_EDGE: AI={ai_p:.0%}",
                    })
                    continue

            # ── FAR market: require minimum edge ─────────────────────────────
            if cid in self._far_market_ids and mode != "WINNER" and edge < 0.08:
                logger.info("FAR market edge too low (%.1f%% < 8%%): %s",
                            edge * 100, market.slug[:40])
                self.trade_log.log({
                    "market": market.slug, "action": "HOLD",
                    "rejected": f"FAR_LOW_EDGE: {edge*100:.1f}% < 8%",
                })
                continue

            # ── Position sizing ───────────────────────────────────────────────
            # Winner mode: use floor edge (0.05) so Kelly stays positive
            sizing_edge = edge if mode != "WINNER" else max(edge, 0.05)
            manip_check = self.manip_guard.check(market, estimate)
            adjusted_size = self.risk.calculate_position_size(
                edge=sizing_edge, bankroll=bankroll, confidence=estimate.confidence,
            )
            adjusted_size = self.manip_guard.adjust_position_size(adjusted_size, manip_check)

            # ── Rank score ────────────────────────────────────────────────────
            conf_score = _CONF_SCORE.get(estimate.confidence, 1)
            if mode == "WINNER":
                rank_score = direction_prob * conf_score
            else:
                rank_score = edge * direction_prob * conf_score

            logger.info(
                "%s mode: %s | AI=%.0f%% mkt=%.0f%% edge=%.1f%% conf=%s score=%.3f",
                mode, market.slug[:35],
                direction_prob * 100, mkt_p * 100 if direction == Direction.BUY_YES else mkt_n * 100,
                edge * 100, estimate.confidence, rank_score,
            )

            candidates.append({
                "score": rank_score,
                "mode": mode,
                "market": market,
                "estimate": estimate,
                "direction": direction,
                "edge": edge,
                "direction_prob": direction_prob,
                "adjusted_size": adjusted_size,
                "sanity": sanity_result,
                "manip_check": manip_check,
                "is_consensus": False,
                "entry_reason": mode.lower(),
                "is_far": cid in self._far_market_ids,
            })

        candidates.sort(key=lambda c: c["score"], reverse=True)
        return candidates
```

- [ ] **Step 4: Run tests to verify they pass**

```bash
python -m pytest tests/test_entry_modes.py -v
```
Expected: 6 PASS

- [ ] **Step 5: Commit**

```bash
git add src/entry_gate.py tests/test_entry_modes.py
git commit -m "feat: three-mode entry strategy (Winner/DeadZone/Underdog) with AI-prob scoring"
```

---

## Task 3: Reframe AI confidence as data quality

**Files:**
- Modify: `src/ai_analyst.py` lines 121–133 (confidence grade definitions in `UNIFIED_SYSTEM` prompt)

**Problem:** Current grades define A/B+/B- in terms of outcome certainty ("adequate sample 8+ matches", "small sample <5 matches"). Claude interprets this as: "I'm uncertain about the soccer qualifier result → C". But confidence should mean "do I have data to make a call?", not "am I certain about the outcome".

**Fix:** Replace the confidence grade text to define grades as data-availability tiers.

- [ ] **Step 1: Write the failing test**

```python
# tests/test_ai_confidence_prompt.py
def test_confidence_prompt_contains_data_quality_language():
    """AI system prompt must define confidence by data availability, not outcome certainty."""
    from src.ai_analyst import UNIFIED_SYSTEM
    # Must contain data-quality language
    assert "data" in UNIFIED_SYSTEM.lower()
    assert "source" in UNIFIED_SYSTEM.lower()
    # Must NOT define grades primarily by sample size language that causes outcome-certainty grading
    assert "outcome certainty" not in UNIFIED_SYSTEM.lower()
    # Must include all four grades
    for grade in ['"A"', '"B+"', '"B-"', '"C"']:
        assert grade in UNIFIED_SYSTEM


def test_confidence_prompt_defines_c_as_no_data():
    """C grade must mean 'no data', not 'uncertain outcome'."""
    from src.ai_analyst import UNIFIED_SYSTEM
    # Find the C grade definition
    c_idx = UNIFIED_SYSTEM.find('"C"')
    assert c_idx != -1
    c_section = UNIFIED_SYSTEM[c_idx:c_idx + 200].lower()
    assert "no data" in c_section or "no source" in c_section or "insufficient data" in c_section


def test_confidence_prompt_a_requires_multiple_sources():
    """A grade must mention multiple sources or strong data."""
    from src.ai_analyst import UNIFIED_SYSTEM
    a_idx = UNIFIED_SYSTEM.find('"A"')
    assert a_idx != -1
    a_section = UNIFIED_SYSTEM[a_idx:a_idx + 300].lower()
    assert "source" in a_section or "data" in a_section
```

- [ ] **Step 2: Run test to verify it fails**

```bash
python -m pytest tests/test_ai_confidence_prompt.py -v
```
Expected: `test_confidence_prompt_defines_c_as_no_data` FAIL — current C grade says "insufficient evidence, essentially guessing" but not "no data" / "no source".

- [ ] **Step 3: Replace confidence grade definitions in `UNIFIED_SYSTEM`**

In `src/ai_analyst.py`, find the block starting at approximately line 121:

```python
Confidence grades:
- "A" = high conviction — sufficient evidence for a well-supported estimate.
        Clear form differential, adequate sample (8+ recent matches per team),
        strong trend or corroborating signals. Does NOT require multiple API sources.
- "B+" = solid conviction — good evidence with minor gaps.
         Reasonable sample (5-8 matches), clear but not dominant trend,
         one unknown factor (e.g., missing H2H, roster uncertainty).
- "B-" = moderate conviction — usable evidence but notable uncertainty.
         Small sample (<5 matches), conflicting signals, stale data (>14 days),
         or genuinely unclear matchup.
- "C"  = low conviction — insufficient evidence, essentially guessing.
         Return C when you cannot form a meaningful estimate.
         Will be SKIPPED (no trade opened).
```

Replace with:

```python
Confidence grades — rate DATA AVAILABILITY, not outcome certainty:
- "A"  = strong data — 2+ independent sources agree (e.g., bookmaker odds + match stats,
         or match stats + news). High-quality stats with 8+ recent matches per team (<14 days).
         Use A even if the result feels uncertain — if data is rich, grade is A.
- "B+" = good data — at least one solid source (bookmaker odds alone, OR match stats with
         5+ recent games, OR detailed news context). One unknown factor (e.g., no H2H data,
         roster change rumor) is fine — still B+ if core data is present.
- "B-" = minimal data — only one weak source (news only with no stats, or <5 match samples,
         or data older than 14 days). You can still form an estimate, but data is thin.
- "C"  = no data — no source provided meaningful information. Return C ONLY when you have
         literally no data to work with: empty stats, no news, no odds, no context.
         Do NOT return C because the outcome is uncertain — return C only for missing data.
         Will be SKIPPED (no trade opened).
```

- [ ] **Step 4: Run tests to verify they pass**

```bash
python -m pytest tests/test_ai_confidence_prompt.py -v
```
Expected: 3 PASS

- [ ] **Step 5: Commit**

```bash
git add src/ai_analyst.py tests/test_ai_confidence_prompt.py
git commit -m "fix: reframe AI confidence grades as data quality tiers, not outcome certainty"
```

---

## Self-Review

**Spec coverage check:**

| Requirement | Task |
|-------------|------|
| Fix Scout spam | Task 1 ✓ |
| Winner mode: AI ≥ 65%, A/B+ only, no edge | Task 2 ✓ |
| Underdog mode: AI < 50%, edge required, A/B+ only | Task 2 ✓ |
| Dead zone: 50-65%, edge required, B- allowed | Task 2 ✓ |
| Rank score: WINNER = direction_prob × conf; EDGE = edge × direction_prob × conf | Task 2 ✓ |
| Position size unchanged (confidence-based via risk manager) | Task 2 ✓ |
| Confidence = data quality, not outcome certainty | Task 3 ✓ |
| No new files, no spaghetti | All tasks ✓ |

**Placeholder scan:** None found — all code blocks are complete and runnable.

**Type consistency:** `mode` field added to candidates dict in Task 2 — `_execute_candidates` only reads `direction`, `adjusted_size`, `market`, `estimate`, `entry_reason`, `is_consensus`, `sanity`, `manip_check` — none of these changed. `mode` is logged but not required by executor. Safe.
