/* PolyAgent Dashboard — trade filtering + bucketing (pure, no I/O).
 *
 * Global namespace `FILTER`:
 *   filterByPeriod(trades, period) → trades[]
 *   cumulativeByResolution(trades, initial, resolution) → [{timestamp, value}]
 *   periodSum(trades) → number
 *   RESOLUTION_BY_PERIOD → { "24h": "event", "7d": "hour", "30d": "day", "1y": "week" }
 *
 * Spec: docs/superpowers/specs/2026-04-16-chart-period-tabs-design.md §3, §4.1
 */
(function (global) {
  "use strict";

  const HOURS_BY_PERIOD = { "24h": 24, "7d": 168, "30d": 720, "1y": 8760 };
  const RESOLUTION_BY_PERIOD = {
    "24h": "event",
    "7d": "hour",
    "30d": "day",
    "1y": "week",
  };

  function filterByPeriod(trades, period) {
    if (!trades) return [];
    const hours = HOURS_BY_PERIOD[period];
    if (!hours) return trades;
    const cutoff = Date.now() - hours * 3600 * 1000;
    return trades.filter((t) => {
      const ts = t && t.exit_timestamp ? Date.parse(t.exit_timestamp) : NaN;
      return Number.isFinite(ts) && ts >= cutoff;
    });
  }

  // ISO 8601 week key — Thursday-anchored, UTC-based.
  function _isoWeekKey(isoTs) {
    const d = new Date(isoTs);
    if (Number.isNaN(d.getTime())) return null;
    const tmp = new Date(
      Date.UTC(d.getUTCFullYear(), d.getUTCMonth(), d.getUTCDate())
    );
    const dayNum = tmp.getUTCDay() || 7;
    tmp.setUTCDate(tmp.getUTCDate() + 4 - dayNum);
    const yearStart = new Date(Date.UTC(tmp.getUTCFullYear(), 0, 1));
    const week = Math.ceil(((tmp - yearStart) / 86400000 + 1) / 7);
    return `${tmp.getUTCFullYear()}-W${String(week).padStart(2, "0")}`;
  }

  function _bucketKey(isoTs, resolution) {
    if (!isoTs) return null;
    if (resolution === "event") return isoTs;
    if (resolution === "hour") return isoTs.slice(0, 13);
    if (resolution === "day") return isoTs.slice(0, 10);
    if (resolution === "week") return _isoWeekKey(isoTs);
    return isoTs;
  }

  // Chronological cumsum, collapsed to bucket resolution.
  // Input: trades DESC-sorted by exit_timestamp (api/trades format).
  // Output: [{timestamp, value}] chronological (oldest → newest).
  function cumulativeByResolution(trades, initial, resolution) {
    const chron = [...(trades || [])].reverse();
    const byKey = new Map();
    let running = Number(initial) || 0;
    for (const t of chron) {
      running += Number(t.exit_pnl_usdc || 0);
      const key = _bucketKey(t.exit_timestamp, resolution);
      if (!key) continue;
      byKey.set(key, { timestamp: t.exit_timestamp, value: running });
    }
    return Array.from(byKey.values());
  }

  function periodSum(trades) {
    return (trades || []).reduce(
      (acc, t) => acc + Number(t.exit_pnl_usdc || 0),
      0
    );
  }

  global.FILTER = {
    filterByPeriod,
    cumulativeByResolution,
    periodSum,
    RESOLUTION_BY_PERIOD,
  };
})(window);
