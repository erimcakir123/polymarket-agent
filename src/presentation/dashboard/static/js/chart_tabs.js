/* PolyAgent Dashboard — chart period tab binding.
 *
 * Splits the tab click → state update → re-render wiring out of dashboard.js
 * to keep dashboard.js under the 400-line ARCH_GUARD cap (Kural 3).
 *
 * Depends on `window.FILTER` being loaded first (trade_filter.js).
 * Exposes `CHART_TABS.bind(deps)` — caller supplies charts + state + cache.
 *
 * Spec: docs/superpowers/specs/2026-04-16-chart-period-tabs-design.md §4.4
 */
(function (global) {
  "use strict";

  // Chart.js plugin: sticky scroll-right. Eğer kullanıcı en sağda idiyse
  // (veya ilk render), güncelleme sonrası en sağa dayalı kalır. Kullanıcı
  // sola kaydırdıysa pozisyon korunur.
  const _atRight = new WeakMap();
  global.Chart.register({
    id: "stickyScrollRight",
    beforeUpdate(chart) {
      const sc = chart.canvas.closest(".chart-scroll");
      if (!sc) return;
      _atRight.set(chart, (sc.scrollLeft + sc.clientWidth) >= (sc.scrollWidth - 10));
    },
    afterUpdate(chart) {
      const sc = chart.canvas.closest(".chart-scroll");
      if (sc && _atRight.get(chart) !== false) sc.scrollLeft = sc.scrollWidth;
    },
  });

  function bind(deps) {
    const { charts, state, cache, initialBankroll } = deps;
    const binding = {
      equity: {
        stateKey: "equityPeriod",
        render: () => charts.setEquity(cache.trades, initialBankroll),
      },
      pnl: {
        stateKey: "pnlPeriod",
        render: () => charts.setWaterfall(cache.trades),
      },
    };

    document.querySelectorAll(".chart-tabs").forEach((group) => {
      const chart = group.dataset.chart;
      const b = binding[chart];
      if (!b) return;
      group.addEventListener("click", (e) => {
        const btn = e.target.closest(".chart-tab");
        if (!btn) return;
        group.querySelectorAll(".chart-tab").forEach((x) => x.classList.remove("active"));
        btn.classList.add("active");
        state[b.stateKey] = btn.dataset.period;
        b.render();
      });
    });

    // Mouse wheel → yatay scroll (yalnızca yatay taşma varsa).
    document.querySelectorAll(".chart-scroll").forEach((el) => {
      el.addEventListener("wheel", (e) => {
        if (el.scrollWidth <= el.clientWidth) return;  // taşma yoksa sayfayı bırak
        if (e.deltaY === 0) return;
        e.preventDefault();
        el.scrollLeft += e.deltaY;
      }, { passive: false });
    });
  }

  global.CHART_TABS = { bind };
})(window);
