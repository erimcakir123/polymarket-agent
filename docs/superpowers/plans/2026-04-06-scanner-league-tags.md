# Scanner: League-Specific Tag Discovery

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Fix scanner to discover daily H2H match markets by fetching league-specific tag_ids from Polymarket's `/sports` endpoint instead of relying on parent tags (1, 64) that only return season-long/futures markets.

**Architecture:** At the start of `_fetch_by_tag_ids`, call `GET /sports` to get all 171 league entries. Extract every unique tag_id from their `tags` CSV fields. Use ALL of those tag_ids (including the existing 1 and 64) to query `/events`. The existing deduplication by conditionId prevents double-counting when a market appears under multiple tags. Cache the tag list for 24h to avoid repeated `/sports` calls.

**Tech Stack:** Python, requests, existing scanner pagination logic.

---

## File Structure

| File | Change |
|---|---|
| `src/market_scanner.py` | MODIFY — add `_fetch_league_tags()` method, modify `_fetch_by_tag_ids()` to use dynamic tags |

No new files. No other files touched.

---

### Task 1: Add league tag discovery + use in scanner

**Files:**
- Modify: `src/market_scanner.py`

- [ ] **Step 1: Add `_fetch_league_tags` method to MarketScanner**

After the `EVENTS_PER_PAGE` constant (line 23), add:

```python
# Cache for league-specific tag_ids from /sports endpoint (refreshed daily)
_league_tags_cache: list[tuple[str, int]] = []
_league_tags_ts: float = 0.0
```

Inside `class MarketScanner`, add this method before `_fetch_by_tag_ids`:

```python
    def _fetch_league_tags(self) -> list[tuple[str, int]]:
        """Fetch all league-specific tag_ids from Polymarket /sports endpoint.

        The /sports endpoint returns 171 sport/league entries, each with a
        'tags' CSV field listing relevant tag_ids. Daily H2H match markets
        live under these league-specific tags, NOT under the parent tags
        (1=sports, 64=esports) which only cover season-long/futures markets.

        Returns list of (sport_code, tag_id) tuples. Cached for 24 hours.
        """
        import time
        global _league_tags_cache, _league_tags_ts
        if _league_tags_cache and (time.time() - _league_tags_ts) < 86400:
            return _league_tags_cache

        try:
            resp = requests.get(f"{GAMMA_BASE}/sports", timeout=15)
            resp.raise_for_status()
            sports = resp.json()
        except Exception as exc:
            logger.warning("/sports endpoint failed: %s — falling back to parent tags", exc)
            return PARENT_TAGS

        seen_tags: set[int] = set()
        result: list[tuple[str, int]] = []

        for entry in sports:
            sport_code = entry.get("sport", "")
            tags_str = entry.get("tags", "")
            for t in tags_str.split(","):
                t = t.strip()
                if t.isdigit():
                    tid = int(t)
                    if tid not in seen_tags:
                        seen_tags.add(tid)
                        result.append((sport_code, tid))

        if result:
            _league_tags_cache = result
            _league_tags_ts = time.time()
            logger.info("Discovered %d league tag_ids from /sports (%d sport entries)",
                        len(result), len(sports))
        else:
            logger.warning("No tags from /sports — falling back to parent tags")
            return PARENT_TAGS

        return result
```

- [ ] **Step 2: Modify `_fetch_by_tag_ids` to use dynamic tags**

Replace the line:

```python
        for category, tag_id in PARENT_TAGS:
```

with:

```python
        league_tags = self._fetch_league_tags()
        for category, tag_id in league_tags:
```

- [ ] **Step 3: Update the log line**

Replace:

```python
        logger.info("Parent-tag scan: %d queries -> %d events -> %d unique markets",
                     total_queries, total_events, len(all_raw))
```

with:

```python
        logger.info("League-tag scan: %d tags, %d queries -> %d events -> %d unique markets",
                     len(league_tags), total_queries, total_events, len(all_raw))
```

- [ ] **Step 4: Run tests**

Run: `python -m pytest tests/test_match_exit.py tests/test_odds_api_bugs.py tests/test_reentry.py tests/test_bid_mtm.py tests/test_matcher_layer0.py -q`
Expected: 165 passed.

- [ ] **Step 5: Import smoke test**

Run: `python -c "from src.market_scanner import MarketScanner; print('ok')"`

- [ ] **Step 6: Commit**

```bash
git add src/market_scanner.py
git commit -m "feat(scanner): discover league-specific tags from /sports for daily H2H markets"
```

---

### Task 2: Audit + push

- [ ] **Step 1: Audit (1 round, 0 bug = done)**

Scope: `src/market_scanner.py` only. Check:
- `_fetch_league_tags` handles API failure gracefully (falls back to PARENT_TAGS)
- Dedup by conditionId still works (existing `seen_ids` set)
- No other files touched
- 165 tests pass

- [ ] **Step 2: Push**

```bash
git push origin master
```

---

### Task 3: Live verify

- [ ] **Step 1: Restart bot, check first cycle log**

After restart, look for:
```
League-tag scan: 171 tags, N queries -> M events -> K unique markets
```

`K` should be significantly higher than the old ~1355 (potentially 3000-5000+).

- [ ] **Step 2: Check Turkish Super Lig match appeared**

```
grep "tur-koc-iba" logs/bot.log
```

Should show the market being scanned, matched, and potentially entered.
