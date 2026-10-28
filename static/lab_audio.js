/**
 * LabVision - lab_audio.js
 * Módulo de Audio Sintético de Laboratorio (Web Audio API)
 * 
 * Genera retroalimentación acústica limpia y clara para operadores de laboratorio:
 * - Beep de confirmación de lectura exitosa (880 Hz / A5, 75ms)
 * - Tono de advertencia / lectura dudosa (494 Hz -> 370 Hz)
 * - Gestión automática de AudioContext suspendido en PyWebView / Edge Chromium
 * - Compatible con window.labAudio y window.LabAudio
 * - Persistencia de volumen y activación en localStorage
 * 
 * Creado por NachoFari para LabVision
 */

(function (root) {
  'use strict';

  const STORAGE_KEY_SUCCESS = 'labvision_audio_success';
  const STORAGE_KEY_WARN = 'labvision_audio_warn';
  const STORAGE_KEY_VOLUME = 'labvision_audio_volume';

  const DEFAULT_SUCCESS = true;
  const DEFAULT_WARN = true;
  const DEFAULT_VOLUME = 0.65; // Volumen claro y audible en laboratorio

  let audioCtx = null;
  let lastSuccessTime = 0;
  let lastWarningTime = 0;

  function loadBool(key, fallback) {
    try {
      const v = localStorage.getItem(key);
      if (v === null) return fallback;
      return v === 'true' || v === '1';
    } catch (e) {
      return fallback;
    }
  }

  function loadFloat(key, fallback) {
    try {
      const v = localStorage.getItem(key);
      if (v === null) return fallback;
      const n = parseFloat(v);
      return (!isNaN(n) && n >= 0 && n <= 1) ? n : fallback;
    } catch (e) {
      return fallback;
    }
  }

  function saveStorage(key, val) {
    try {
      localStorage.setItem(key, String(val));
    } catch (e) {}
  }

  // Estado interno
  const state = {
    soundEnabled: loadBool(STORAGE_KEY_SUCCESS, DEFAULT_SUCCESS),
    warnSoundEnabled: loadBool(STORAGE_KEY_WARN, DEFAULT_WARN),
    volume: loadFloat(STORAGE_KEY_VOLUME, DEFAULT_VOLUME)
  };

  /**
   * Obtiene o crea el AudioContext singleton
   */
  function getAudioContext() {
    if (!audioCtx) {
      const AudioCtxClass = window.AudioContext || window.webkitAudioContext;
      if (!AudioCtxClass) {
        console.warn('[LabAudio] Web Audio API no soportada.');
        return null;
      }
      try {
        audioCtx = new AudioCtxClass();
      } catch (err) {
        console.warn('[LabAudio] Error creando AudioContext:', err);
        return null;
      }
    }
    return audioCtx;
  }

  /**
   * Reanuda el AudioContext si está suspendido
   */
  function resumeAudio() {
    const ctx = getAudioContext();
    if (ctx && ctx.state === 'suspended') {
      return ctx.resume().catch(() => {});
    }
    return Promise.resolve();
  }

  // Auto-desbloqueo al primer clic o toque en cualquier parte de la ventana
  function setupAutoUnlock() {
    if (typeof window === 'undefined' || typeof document === 'undefined') return;
    const unlocker = function () {
      resumeAudio();
    };
    ['click', 'pointerdown', 'keydown', 'touchstart'].forEach(evt => {
      document.addEventListener(evt, unlocker, { capture: true, passive: true });
    });
  }
  setupAutoUnlock();

  /**
   * Beep de Éxito / Confirmación de lectura:
   * Tono claro de 880 Hz (A5), duración ~75ms, decaimiento exponencial suave.
   */
  function playSuccessBeep() {
    if (!state.soundEnabled || state.volume <= 0.001) return;

    // Rate-limiting a 45ms para evitar saturación
    const nowMs = Date.now();
    if (nowMs - lastSuccessTime < 45) return;
    lastSuccessTime = nowMs;

    const ctx = getAudioContext();
    if (!ctx) return;

    const playTone = () => {
      try {
        const now = ctx.currentTime;
        const osc = ctx.createOscillator();
        const gain = ctx.createGain();

        // 880 Hz = Tono A5 limpio y profesional
        osc.type = 'sine';
        osc.frequency.setValueAtTime(880, now);

        // Volumen escalado con el slider del usuario
        const peak = Math.max(0.01, state.volume * 0.75);

        gain.gain.setValueAtTime(0.0001, now);
        gain.gain.linearRampToValueAtTime(peak, now + 0.005);
        gain.gain.exponentialRampToValueAtTime(0.0001, now + 0.075);

        osc.connect(gain);
        gain.connect(ctx.destination);

        osc.start(now);
        osc.stop(now + 0.080);

        osc.onended = () => {
          try {
            osc.disconnect();
            gain.disconnect();
          } catch (e) {}
        };
      } catch (err) {
        console.warn('[LabAudio] Error generando beep:', err);
      }
    };

    if (ctx.state === 'suspended') {
      ctx.resume().then(playTone).catch(() => {});
    } else {
      playTone();
    }
  }

  /**
   * Beep de Advertencia / Alarma de lectura dudosa:
   * Tono doble descendente 494 Hz -> 370 Hz (B4 -> F#4)
   */
  function playWarningBeep() {
    if (!state.warnSoundEnabled || state.volume <= 0.001) return;

    const nowMs = Date.now();
    if (nowMs - lastWarningTime < 150) return;
    lastWarningTime = nowMs;

    const ctx = getAudioContext();
    if (!ctx) return;

    const playAlert = () => {
      try {
        const now = ctx.currentTime;
        const peak = Math.max(0.01, state.volume * 0.70);

        // Tono 1: 494 Hz (B4)
        const osc1 = ctx.createOscillator();
        const gain1 = ctx.createGain();
        osc1.type = 'sine';
        osc1.frequency.setValueAtTime(494, now);
        gain1.gain.setValueAtTime(0.0001, now);
        gain1.gain.linearRampToValueAtTime(peak, now + 0.005);
        gain1.gain.exponentialRampToValueAtTime(0.0001, now + 0.070);
        osc1.connect(gain1);
        gain1.connect(ctx.destination);
        osc1.start(now);
        osc1.stop(now + 0.075);

        // Tono 2: 370 Hz (F#4)
        const t2 = now + 0.085;
        const osc2 = ctx.createOscillator();
        const gain2 = ctx.createGain();
        osc2.type = 'sine';
        osc2.frequency.setValueAtTime(370, t2);
        gain2.gain.setValueAtTime(0.0001, t2);
        gain2.gain.linearRampToValueAtTime(peak * 0.9, t2 + 0.005);
        gain2.gain.exponentialRampToValueAtTime(0.0001, t2 + 0.090);
        osc2.connect(gain2);
        gain2.connect(ctx.destination);
        osc2.start(t2);
        osc2.stop(t2 + 0.095);

        osc1.onended = () => { try { osc1.disconnect(); gain1.disconnect(); } catch (e) {} };
        osc2.onended = () => { try { osc2.disconnect(); gain2.disconnect(); } catch (e) {} };
      } catch (err) {
        console.warn('[LabAudio] Error generando alerta:', err);
      }
    };

    if (ctx.state === 'suspended') {
      ctx.resume().then(playAlert).catch(() => {});
    } else {
      playAlert();
    }
  }

  function setSoundEnabled(enabled) {
    state.soundEnabled = Boolean(enabled);
    saveStorage(STORAGE_KEY_SUCCESS, state.soundEnabled);
    if (state.soundEnabled) playSuccessBeep();
    return state.soundEnabled;
  }

  function setWarnSoundEnabled(enabled) {
    state.warnSoundEnabled = Boolean(enabled);
    saveStorage(STORAGE_KEY_WARN, state.warnSoundEnabled);
    if (state.warnSoundEnabled) playWarningBeep();
    return state.warnSoundEnabled;
  }

  function setVolume(vol) {
    const n = parseFloat(vol);
    if (!isNaN(n)) {
      state.volume = Math.max(0.0, Math.min(1.0, n));
      saveStorage(STORAGE_KEY_VOLUME, state.volume);
    }
    return state.volume;
  }

  const labAudioExport = {
    get soundEnabled() { return state.soundEnabled; },
    set soundEnabled(v) { setSoundEnabled(v); },
    get warnSoundEnabled() { return state.warnSoundEnabled; },
    set warnSoundEnabled(v) { setWarnSoundEnabled(v); },
    get volume() { return state.volume; },
    set volume(v) { setVolume(v); },
    setSoundEnabled,
    setWarnSoundEnabled,
    setVolume,
    playSuccessBeep,
    playWarningBeep,
    resume: resumeAudio,
    getAudioContext
  };

  // Exponer en window tanto como labAudio como LabAudio y funciones globales
  root.labAudio = labAudioExport;
  root.LabAudio = labAudioExport;
  root.playSuccessBeep = playSuccessBeep;
  root.playWarningBeep = playWarningBeep;

})(typeof window !== 'undefined' ? window : this);
