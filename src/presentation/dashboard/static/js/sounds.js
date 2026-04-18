/* Trade exit sound notifications — win / big win / loss with fade-out.
 *
 * Config: data-big-win-roi-pct on <body> (default 30).
 * Depends on: nothing (standalone namespace).
 */
(function (global) {
  "use strict";

  const BIG_WIN_ROI = parseFloat(document.body.dataset.bigWinRoiPct || "30") / 100;
  const FADE_DURATION_MS = 2000;
  const FADE_STEPS = 20;

  const _audio = {
    win: new Audio("/static/sounds/win.mp3"),
    bigWin: new Audio("/static/sounds/big_win.mp3"),
    loss: new Audio("/static/sounds/loss.mp3"),
  };

  function _fadeOut(audio) {
    const step = audio.volume / FADE_STEPS;
    const interval = FADE_DURATION_MS / FADE_STEPS;
    const timer = setInterval(() => {
      if (audio.volume - step <= 0) {
        audio.volume = 0;
        audio.pause();
        audio.currentTime = 0;
        audio.volume = 1;
        clearInterval(timer);
        return;
      }
      audio.volume -= step;
    }, interval);
  }

  function _play(audio) {
    audio.currentTime = 0;
    audio.volume = 1;
    audio.play().catch(() => {});
    const durationMs = (audio.duration || 5) * 1000;
    const fadeStart = Math.max(0, durationMs - FADE_DURATION_MS);
    setTimeout(() => _fadeOut(audio), fadeStart);
  }

  const SOUNDS = {
    /** PnL ve size'dan ses tipi belirle ve çal. */
    playExit(pnl, sizeUsdc) {
      if (pnl < 0) {
        _play(_audio.loss);
        return;
      }
      const roi = sizeUsdc > 0 ? pnl / sizeUsdc : 0;
      if (roi >= BIG_WIN_ROI) {
        _play(_audio.bigWin);
      } else {
        _play(_audio.win);
      }
    },
  };

  global.SOUNDS = SOUNDS;
})(window);
