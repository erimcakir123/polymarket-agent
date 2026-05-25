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

  function _latestExitTs(t) {
    // Trade'in en yeni exit timestamp'i — partial veya full close.
    // Partial-only kayıtların `exit_timestamp`'i boş; partial_exits[].timestamp'i var.
    const tops = t && t.exit_timestamp ? [t.exit_timestamp] : [];
    const partials = ((t && t.partial_exits) || [])
      .map((pe) => pe && pe.timestamp).filter(Boolean);
    const all = tops.concat(partials);
    if (!all.length) return NaN;
    let latest = -Infinity;
    for (const s of all) {
      const ts = Date.parse(s);
      if (Number.isFinite(ts) && ts > latest) latest = ts;
    }
    return Number.isFinite(latest) ? latest : NaN;
  }

  function filterByPeriod(trades, period) {
    if (!trades) return [];
    const hours = HOURS_BY_PERIOD[period];
    if (!hours) return trades;
    const cutoff = Date.now() - hours * 3600 * 1000;
    return trades.filter((t) => {
      const ts = _latestExitTs(t);
      return Number.isFinite(ts) && ts >= cutoff;
    });
  }

  // ISO 8601 week key — Thursday-anchored, UTC-based.
  function _isoWeekKey(isoTs) {
    if (isoTs == null) return null;
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

  // Tüm exit event'leri tek liste — partial scale-out + full close ayrı ayrı
  // chronological sıralı. Dashboard cumulative chart için: partial PnL atlama
  // bug'ı (chart $500-$620 takılı kalıyordu, gerçek equity $1100+) düzeltildi.
  function _allExitEvents(trades) {
    // Bot exit'leri 2 yere yaziyor: (1) orijinal trade kaydinin partial_exits[] dizisi,
    // (2) ayri trade kaydi (exit_reason=scale_out_tier_X, exit_price=null). Eski filtre
    // sadece partial_exits[] + exit_price!=null okuyordu — ayri scale-out kayitlari
    // (henuz kapanmamis trade'lerin partial'lari) chart'tan dusuyordu, Exited tab ile
    // tutarsizlik yaratiyordu. Cozum: her iki kaynaktan da topla, (slug+timestamp) ile
    // dedupe (Droguet/Tomljan gibi cift yazilmis trade'lerde tek say).
    const events = [];
    const seen = new Set();
    for (const t of (trades || [])) {
      const slug = t.slug || "";
      const question = t.question || "";
      for (const pe of (t.partial_exits || [])) {
        if (!pe || !pe.timestamp) continue;
        const key = slug + "|" + pe.timestamp;
        if (seen.has(key)) continue;
        seen.add(key);
        events.push({
          timestamp: pe.timestamp,
          pnl: Number(pe.realized_pnl_usdc || 0),
          slug,
          question,
        });
      }
      if (t.exit_timestamp && t.exit_pnl_usdc != null) {
        const key = slug + "|" + t.exit_timestamp;
        if (seen.has(key)) continue;
        seen.add(key);
        events.push({
          timestamp: t.exit_timestamp,
          pnl: Number(t.exit_pnl_usdc || 0),
          slug,
          question,
        });
      }
    }
    events.sort((a, b) => (a.timestamp < b.timestamp ? -1 : 1));
    return events;
  }

  // Chronological cumsum, collapsed to bucket resolution.
  // Input: trade records (api/trades format) — partial_exits + exit_price birlikte handle edilir.
  // Output: [{timestamp, value}] chronological (oldest → newest).
  function cumulativeByResolution(trades, initial, resolution) {
    const events = _allExitEvents(trades);
    const byKey = new Map();
    let running = Number(initial) || 0;
    for (const ev of events) {
      running += ev.pnl;
      const key = _bucketKey(ev.timestamp, resolution);
      if (!key) continue;
      byKey.set(key, { timestamp: ev.timestamp, value: running });
    }
    return Array.from(byKey.values());
  }

  function periodSum(trades) {
    // Tüm exit event'leri (full + partial) toplamı — partial PnL'i atlamayan toplam.
    return _allExitEvents(trades).reduce((acc, ev) => acc + ev.pnl, 0);
  }

  const _MONTH = ["Jan", "Feb", "Mar", "Apr", "May", "Jun",
                  "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"];
  const _WEEKDAY = ["Sun", "Mon", "Tue", "Wed", "Thu", "Fri", "Sat"];

  function _pad2(n) { return String(n).padStart(2, "0"); }

  // Period-aware x-axis label. UTC values used to stay consistent with ISO ts.
  function periodLabel(isoTs, period) {
    if (!isoTs) return "";
    const d = new Date(isoTs);
    if (Number.isNaN(d.getTime())) return "";
    if (period === "24h") return `${_pad2(d.getUTCHours())}:${_pad2(d.getUTCMinutes())}`;
    if (period === "7d")  return `${_WEEKDAY[d.getUTCDay()]} ${_pad2(d.getUTCHours())}h`;
    if (period === "30d") return `${_MONTH[d.getUTCMonth()]} ${d.getUTCDate()}`;
    if (period === "1y") {
      const key = _isoWeekKey(isoTs);
      return key ? "W" + key.slice(6) : "";  // "2026-W15" → "W15"
    }
    return "";
  }

  // PnL bar chart bucketing — partial + full exit event'lerini gruplar, her bucket net PnL.
  // Input: trade records. Output: [{timestamp, pnl, count}] chronological.
  function pnlByResolution(trades, resolution) {
    const events = _allExitEvents(trades);
    if (resolution === "event") {
      return events.map((ev) => ({
        timestamp: ev.timestamp,
        pnl: ev.pnl,
        count: 1,
        slug: ev.slug || "",
        question: ev.question || "",
      }));
    }
    const byKey = new Map();
    for (const ev of events) {
      const key = _bucketKey(ev.timestamp, resolution);
      if (!key) continue;
      const existing = byKey.get(key);
      if (existing) {
        existing.pnl += ev.pnl;
        existing.count += 1;
      } else {
        byKey.set(key, {
          timestamp: ev.timestamp,
          pnl: ev.pnl,
          count: 1,
        });
      }
    }
    return Array.from(byKey.values());
  }

  global.FILTER = {
    filterByPeriod,
    cumulativeByResolution,
    pnlByResolution,
    periodSum,
    periodLabel,
    RESOLUTION_BY_PERIOD,
  };
})(window);
