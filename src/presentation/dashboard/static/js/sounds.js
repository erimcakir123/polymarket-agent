/* Trade exit sound notifications — win / loss with fade-out.
 *
 * Depends on: nothing (standalone namespace).
 */
(function (global) {
  "use strict";

  const FADE_DURATION_MS = 2000;
  const FADE_STEPS = 20;
  const BASE_VOLUME = 0.65;

  const _audio = {
    win: new Audio("/static/sounds/win.mp3"),
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
        audio.volume = BASE_VOLUME;
        clearInterval(timer);
        return;
      }
      audio.volume -= step;
    }, interval);
  }

  function _play(audio) {
    audio.currentTime = 0;
    audio.volume = BASE_VOLUME;
    audio.play().catch(() => {});
    const durationMs = (audio.duration || 5) * 1000;
    const fadeStart = Math.max(0, durationMs - FADE_DURATION_MS);
    setTimeout(() => _fadeOut(audio), fadeStart);
  }

  const SOUNDS = {
    /** PnL'den ses tipi belirle ve çal. */
    playExit(pnl) {
      if (pnl < 0) {
        _play(_audio.loss);
      } else {
        _play(_audio.win);
      }
    },
  };

  global.SOUNDS = SOUNDS;
})(window);
