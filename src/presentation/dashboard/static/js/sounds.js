/* Trade sound notifications — entry + exit (win/loss) with fade-out.
 *
 * Depends on: nothing (standalone namespace).
 * Entry sounds queue sequentially (N entries → N plays in a row).
 * Last 2 seconds of entry sound are cut (stop early).
 */
(function (global) {
  "use strict";

  const FADE_DURATION_MS = 2000;
  const FADE_STEPS = 20;
  const BASE_VOLUME = 0.65;
  const ENTRY_TAIL_CUT_MS = 2000;

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

  // Entry queue — N entries → N sequential plays, each with last 2s cut.
  let _entryQueue = 0;
  let _entryPlaying = false;

  function _playEntryOnce(onComplete) {
    // Her calışta yeni Audio — seri calma icin paralel overlap olmasın.
    const audio = new Audio("/static/sounds/market_entry.mp3");
    audio.volume = BASE_VOLUME;
    const handleMetadata = () => {
      const totalMs = (audio.duration || 0) * 1000;
      const playMs = Math.max(500, totalMs - ENTRY_TAIL_CUT_MS);
      audio.play().catch(() => {});
      setTimeout(() => {
        audio.pause();
        audio.currentTime = 0;
        onComplete();
      }, playMs);
    };
    if (audio.readyState >= 1) {
      handleMetadata();
    } else {
      audio.addEventListener("loadedmetadata", handleMetadata, { once: true });
      audio.addEventListener("error", () => onComplete(), { once: true });
    }
  }

  function _drainEntryQueue() {
    if (_entryPlaying || _entryQueue <= 0) return;
    _entryPlaying = true;
    _entryQueue -= 1;
    _playEntryOnce(() => {
      _entryPlaying = false;
      _drainEntryQueue();
    });
  }

  const SOUNDS = {
    /** PnL'den ses tipi belirle ve cal. */
    playExit(pnl) {
      if (pnl < 0) {
        _play(_audio.loss);
      } else {
        _play(_audio.win);
      }
    },

    /** Market giris sesi — N kez cagrilirsa N kez seri calar. */
    playEntry() {
      _entryQueue += 1;
      _drainEntryQueue();
    },
  };

  global.SOUNDS = SOUNDS;
})(window);
