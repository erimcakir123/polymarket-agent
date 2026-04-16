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

  // Chart.js plugin: sticky scroll-right. Kullanıcı en sağda idiyse (veya
  // ilk render), güncelleme sonrası en sağda kalır; sola kaydırdıysa korunur.
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
      if (sc && _atRight.get(chart) !== false) {
        sc.scrollTo({ left: sc.scrollWidth, behavior: "smooth" });
      }
    },
  });

  // Chart.js plugin: external y-axis. Chart'ın kendi y-label'ları gizli;
  // canvas dışındaki `#{canvas.dataset.yAxisTarget}` elementine tick'leri
  // mutlak konumlu div'ler olarak yazar → scroll'a rağmen sabit kalır.
  const _fmtDollar = (v) => {
    const abs = Math.abs(v);
    const body = abs >= 1000 ? (abs / 1000).toFixed(2) + "k" : abs.toFixed(0);
    return (v < 0 ? "-" : "") + "$" + body;
  };
  global.Chart.register({
    id: "externalYAxis",
    afterUpdate(chart) {
      const targetId = chart.canvas.dataset.yAxisTarget;
      if (!targetId) return;
      const target = document.getElementById(targetId);
      const yScale = chart.scales && chart.scales.y;
      if (!target || !yScale || !yScale.ticks) return;
      target.innerHTML = yScale.ticks.map((t) => {
        const y = yScale.getPixelForValue(t.value);
        return `<div class="chart-y-tick" style="top:${y}px">${_fmtDollar(t.value)}</div>`;
      }).join("");
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
