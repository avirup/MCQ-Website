(function () {
  "use strict";

  // ---- Utilities ---------------------------------------------------------

  function $(id) { return document.getElementById(id); }

  function formatHMS(totalSeconds) {
    const s = Math.max(0, Math.floor(totalSeconds));
    const h = Math.floor(s / 3600);
    const m = Math.floor((s % 3600) / 60);
    const sec = s % 60;
    if (h > 0) return `${h}:${String(m).padStart(2, "0")}:${String(sec).padStart(2, "0")}`;
    return `${m}:${String(sec).padStart(2, "0")}`;
  }

  function parseISOUTC(s) {
    // Returns ms since epoch or null
    if (!s) return null;
    const t = Date.parse(s);
    return Number.isFinite(t) ? t : null;
  }

  function nowMs() { return Date.now(); }

  function clamp(n, min, max) { return Math.min(Math.max(n, min), max); }

  // ---- Navigation guard --------------------------------------------------

  let navigated = false;
  function safeNavigate(url) {
    if (navigated || !url) return;
    navigated = true;
    window.location.assign(url);
  }

  // ---- Core --------------------------------------------------------------

  const cfg = (window.TEST_TIMER_CONFIG || {});
  // cfg: {
  //   mode: 'display'|'interactive',
  //   auto_advance: boolean,
  //   timer_mode: 'per-question'|'total-test',
  //   per_question_duration: number (sec),
  //   total_duration: number (sec),
  //   test_end_time: ISO string (UTC) | null,
  //   question_index: number,
  //   total_questions: number,
  //   next_url: string | null,
  //   finish_url: string | null,
  //   submit_api: string | null
  // }

  const lbl = $("timer-label");
  const val = $("timer-value");

  function setLabel(text) {
    if (lbl) lbl.textContent = text;
  }

  function setTime(seconds) {
    if (val) val.textContent = formatHMS(seconds);
  }

  function finishTest(reason) {
    // Could POST a heartbeat to server if you add an API; for now just navigate.
    safeNavigate(cfg.finish_url);
  }

  function onPerQuestionExpired() {
    if (cfg.auto_advance) {
      // Display mode: just navigate
      // Interactive mode: ideally save answer first (handled by template's click handler); here we just move on.
      safeNavigate(cfg.next_url || cfg.finish_url);
    } else {
      // No auto-advance: simply stop at 0 (user can navigate manually)
      // Optionally, you can flash the timer or show a notice here.
    }
  }

  function computePerQuestionRemaining(startMs, durationSec) {
    const elapsed = (nowMs() - startMs) / 1000;
    return durationSec - elapsed;
  }

  function computeTotalTestRemainingFromServer(endUtcMs) {
    // Anti-tamper: server-provided end time is the authority
    return (endUtcMs - nowMs()) / 1000;
  }

  // ---- Timers ------------------------------------------------------------

  let rafId = null;
  let intervalId = null;

  function clearTimers() {
    if (intervalId) { clearInterval(intervalId); intervalId = null; }
    if (rafId) { cancelAnimationFrame(rafId); rafId = null; }
  }

  function runPerQuestionTimer() {
    setLabel("Question Time");
    const duration = Math.max(5, Number(cfg.per_question_duration || 0));
    const start = nowMs();

    function tick() {
      const remaining = computePerQuestionRemaining(start, duration);
      setTime(Math.max(0, Math.ceil(remaining)));
      if (remaining <= 0) {
        clearTimers();
        onPerQuestionExpired();
        return;
      }
    }

    // Update every 250ms for smoothness; text changes once per second.
    tick();
    intervalId = setInterval(tick, 250);

    document.addEventListener("visibilitychange", () => {
      // Keep counting even if page hidden; recompute on return
      if (document.visibilityState === "visible") tick();
    });
  }

  function runTotalTestTimer() {
    setLabel("Total Test Time");
    // Prefer server-authoritative end time; fallback to local duration if missing
    const endMs = parseISOUTC(cfg.test_end_time);
    let remaining;

    function computeRemaining() {
      if (endMs !== null) {
        // Anti-tamper: based on server end time
        return computeTotalTestRemainingFromServer(endMs);
      } else {
        // Fallback: local countdown from page load (less safe, but functional)
        if (!runTotalTestTimer._fallbackStart) {
          runTotalTestTimer._fallbackStart = nowMs();
        }
        const elapsed = (nowMs() - runTotalTestTimer._fallbackStart) / 1000;
        return Number(cfg.total_duration || 0) - elapsed;
      }
    }

    function tick() {
      remaining = computeRemaining();
      setTime(Math.max(0, Math.ceil(remaining)));
      if (remaining <= 0) {
        clearTimers();
        finishTest("time-expired");
        return;
      }
    }

    tick();
    intervalId = setInterval(tick, 250);

    document.addEventListener("visibilitychange", () => {
      if (document.visibilityState === "visible") tick();
    });
  }

  // ---- Init --------------------------------------------------------------

  function init() {
    if (!val || !lbl) return; // no timer in DOM, do nothing

    // Normalize/guard
    const timerMode = (cfg.timer_mode || "").toLowerCase(); // 'per-question'|'total-test'
    const mode = (cfg.mode || "").toLowerCase();           // 'display'|'interactive'

    if (timerMode === "per-question") {
      // Display: always per-question timer (per BRD)
      // Interactive: per-question mode also valid; if auto_advance=false, we simply show countdown without auto-advance
      runPerQuestionTimer();
    } else if (timerMode === "total-test") {
      // Only for interactive when auto-advance=no per BRD; we enforce via server end time if provided
      runTotalTestTimer();
    } else {
      // Unknown timer mode; hide label
      setLabel("Time");
      setTime(0);
    }

    // Defensive: if total-test mode and server-provided end time already passed, finish immediately.
    if (timerMode === "total-test" && parseISOUTC(cfg.test_end_time) !== null) {
      const rem = computeTotalTestRemainingFromServer(parseISOUTC(cfg.test_end_time));
      if (rem <= 0) {
        finishTest("time-expired-immediate");
      }
    }
  }

  // Run when DOM is ready
  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", init);
  } else {
    init();
  }
})();
