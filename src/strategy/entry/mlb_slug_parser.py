"""MLB Polymarket slug parser — pure static parsing (no I/O, no deps).

TODO-005 (2026-05-25): mlb_submarket_engine.py'dan ayrıştırıldı. ARCH_GUARD Kural 3
(<400 satır) için. Engine sadece import eder, parser kendi başına test edilebilir.

Slug pattern'leri (gerçek Polymarket formatı — SPEC-X 2026-05-24):
  totals:    mlb-{away}-{home}-{YYYY-MM-DD}-total-{N}pt5
  run_line:  mlb-{away}-{home}-{YYYY-MM-DD}-spread-{home|away}-{N}pt5
  moneyline: mlb-{away}-{home}-{YYYY-MM-DD}
"""
from __future__ import annotations

import re

_SLUG_TOTALS_RE = re.compile(
    r"^mlb-(\w+)-(\w+)-(\d{4}-\d{2}-\d{2})-total-(\d+)pt5$"
)
_SLUG_RUN_LINE_RE = re.compile(
    r"^mlb-(\w+)-(\w+)-(\d{4}-\d{2}-\d{2})-spread-(home|away)-(\d+)pt5$"
)
_SLUG_MONEYLINE_RE = re.compile(
    r"^mlb-(\w+)-(\w+)-(\d{4}-\d{2}-\d{2})$"
)


def parse_slug(slug: str) -> tuple[str, str, float, str, str] | None:
    """Parse MLB slug → (date_str, market_type, line, away_abbr, home_abbr).

    Returns None for unrecognised slugs.

    Line yorumu (SPEC-X):
      - spread-home-Npt5 → home team -N.5 covers (yes_token); home_line = -N.5
      - spread-away-Npt5 → away team -N.5 covers → home gets +N.5; home_line = +N.5
      - totals → line = N.5 (over/under threshold)
      - moneyline → line = 0.0 (unused)
    """
    m_t = _SLUG_TOTALS_RE.match(slug)
    if m_t:
        away, home, date, n = m_t.groups()
        return date, "totals", float(n) + 0.5, away, home
    m_r = _SLUG_RUN_LINE_RE.match(slug)
    if m_r:
        away, home, date, side, n_str = m_r.groups()
        magnitude = float(n_str) + 0.5
        line = -magnitude if side == "home" else +magnitude
        return date, "run_line", line, away, home
    m_m = _SLUG_MONEYLINE_RE.match(slug)
    if m_m:
        away, home, date = m_m.groups()
        return date, "moneyline", 0.0, away, home
    return None
