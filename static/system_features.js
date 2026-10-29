/**
 * LabVision Pro & Universal - Funcionalidades de Sistema:
 * 1. Captura de pantalla nativa (F9 / Botón) con feedback sonoro
 * 2. Comprobador de actualizaciones automáticas desde GitHub
 * 3. Gestión y persistencia de temas visuales (NaTex 20+ Themes)
 * 
 * Creado por NachoFari (https://github.com/NachoFari)
 */

// ================= 1. CAPTURAS DE PANTALLA UX (F9 / BOTÓN) =================

async function takeScreenshotUI() {
  playCameraShutterSound();

  // Feedback visual de flash
  const flashOverlay = document.createElement('div');
  flashOverlay.style.cssText = 'position:fixed;inset:0;background:white;opacity:0.6;z-index:99999;pointer-events:none;transition:opacity 0.25s ease-out;';
  document.body.appendChild(flashOverlay);
  requestAnimationFrame(() => {
    flashOverlay.style.opacity = '0';
    setTimeout(() => flashOverlay.remove(), 260);
  });

  if (window.pywebview && window.pywebview.api && window.pywebview.api.take_screenshot) {
    try {
      const res = await window.pywebview.api.take_screenshot("labvision_ux");
      if (res.success) {
        showLabToast(`📸 Captura guardada: ${res.filename}`, "success");
      } else {
        showLabToast(`Error al capturar pantalla: ${res.error}`, "error");
      }
    } catch (err) {
      console.error("Error en take_screenshot:", err);
      showLabToast("Error al invocar API de captura nativa.", "error");
    }
  } else {
    showLabToast("API de captura nativa no disponible en modo navegador puro.", "info");
  }
}

// Sonido sintético de obturador de cámara (Web Audio API)
function playCameraShutterSound() {
  try {
    const AudioContext = window.AudioContext || window.webkitAudioContext;
    if (!AudioContext) return;
    const ctx = new AudioContext();

    // Ruido blanco filtrado para emular el 'click-clack' mecánico
    const bufferSize = ctx.sampleRate * 0.08;
    const buffer = ctx.createBuffer(1, bufferSize, ctx.sampleRate);
    const data = buffer.getChannelData(0);
    for (let i = 0; i < bufferSize; i++) {
      data[i] = (Math.random() * 2 - 1) * Math.exp(-i / (ctx.sampleRate * 0.02));
    }

    const noise = ctx.createBufferSource();
    noise.buffer = buffer;

    const filter = ctx.createBiquadFilter();
    filter.type = 'highpass';
    filter.frequency.value = 1200;

    const gain = ctx.createGain();
    gain.gain.setValueAtTime(0.35, ctx.currentTime);
    gain.gain.exponentialRampToValueAtTime(0.01, ctx.currentTime + 0.07);

    noise.connect(filter);
    filter.connect(gain);
    gain.connect(ctx.destination);

    noise.start();
  } catch (e) {
    // Silencioso si el audio está bloqueado por autoplay policy
  }
}

// Hotkey global F9 para capturas de pantalla de los evaluadores UX
window.addEventListener('keydown', (e) => {
  if (e.key === 'F9') {
    e.preventDefault();
    takeScreenshotUI();
  }
});


// ================= 2. AUTO-UPDATER DE GITHUB =================

let latestReleaseInfo = null;

async function checkForUpdatesUI() {
  const btn = document.getElementById('btn-check-update');
  const txt = document.getElementById('txt-check-update');
  const badge = document.getElementById('updater-status-badge');
  const feedback = document.getElementById('updater-feedback');
  const btnInstall = document.getElementById('btn-install-update');

  if (txt) txt.innerText = "Comprobando...";
  if (btn) btn.disabled = true;
  if (feedback) {
    feedback.classList.remove('hidden');
    feedback.className = "text-[11px] p-2 rounded-lg bg-slate-900 border border-slate-800 text-slate-300";
    feedback.innerText = "Consultando repositorio GitHub (NachoFari/LabVision)...";
  }

  if (window.pywebview && window.pywebview.api && window.pywebview.api.check_for_updates) {
    try {
      const res = await window.pywebview.api.check_for_updates();
      if (btn) btn.disabled = false;
      if (txt) txt.innerText = "Comprobar Actualizaciones";

      if (res.error) {
        feedback.className = "text-[11px] p-2 rounded-lg bg-rose-950/60 border border-rose-800 text-rose-300";
        feedback.innerText = `No se pudo conectar a GitHub: ${res.error}`;
        return;
      }

      if (res.update_available) {
        latestReleaseInfo = res;
        if (badge) {
          badge.className = "text-[10px] font-mono px-2 py-0.5 rounded bg-emerald-950 text-emerald-400 border border-emerald-800 animate-pulse";
          badge.innerText = `v${res.latest_version} DISPONIBLE`;
        }
        feedback.className = "text-[11px] p-2 rounded-lg bg-emerald-950/60 border border-emerald-800 text-emerald-300";
        feedback.innerText = `¡Nueva versión v${res.latest_version} disponible! ${res.release_notes || ''}`;
        if (btnInstall) btnInstall.classList.remove('hidden');
      } else {
        if (badge) {
          badge.className = "text-[10px] font-mono px-2 py-0.5 rounded bg-slate-800 text-slate-400 border border-slate-700";
          badge.innerText = `v${res.current_version} (Al día)`;
        }
        feedback.className = "text-[11px] p-2 rounded-lg bg-slate-900 border border-slate-800 text-slate-300";
        feedback.innerText = `LabVision está actualizado a la versión más reciente (v${res.current_version}).`;
        if (btnInstall) btnInstall.classList.add('hidden');
      }
    } catch (e) {
      if (btn) btn.disabled = false;
      if (txt) txt.innerText = "Comprobar Actualizaciones";
      feedback.className = "text-[11px] p-2 rounded-lg bg-rose-950/60 border border-rose-800 text-rose-300";
      feedback.innerText = `Error al verificar: ${e.message}`;
    }
  } else {
    if (btn) btn.disabled = false;
    if (txt) txt.innerText = "Comprobar Actualizaciones";
    feedback.innerText = "API de actualización no disponible en modo navegador web.";
  }
}

async function installUpdateUI() {
  const btnInstall = document.getElementById('btn-install-update');
  const txtInstall = document.getElementById('txt-install-update');
  const feedback = document.getElementById('updater-feedback');

  if (btnInstall) btnInstall.disabled = true;
  if (txtInstall) txtInstall.innerText = "Descargando e Instalando...";
  if (feedback) {
    feedback.className = "text-[11px] p-2.5 rounded-lg bg-cyan-950 border border-cyan-800 text-cyan-300";
    feedback.innerText = "Descargando instalador desde GitHub en segundo plano. El sistema se reiniciará automáticamente al completar...";
  }

  if (window.pywebview && window.pywebview.api && window.pywebview.api.download_and_install_update) {
    try {
      const assetUrl = latestReleaseInfo ? latestReleaseInfo.asset_url : null;
      const res = await window.pywebview.api.download_and_install_update(assetUrl);
      if (!res.success) {
        feedback.className = "text-[11px] p-2 rounded-lg bg-rose-950/60 border border-rose-800 text-rose-300";
        feedback.innerText = `Error en actualización: ${res.error}`;
        if (btnInstall) btnInstall.disabled = false;
        if (txtInstall) txtInstall.innerText = "Reintentar Actualización";
      }
    } catch (e) {
      feedback.innerText = `Error al ejecutar instalador: ${e.message}`;
      if (btnInstall) btnInstall.disabled = false;
    }
  }
}


// ================= 3. TOAST NOTIFICATIONS =================

function showLabToast(message, type = "info") {
  let toastContainer = document.getElementById('lab-toast-container');
  if (!toastContainer) {
    toastContainer = document.createElement('div');
    toastContainer.id = 'lab-toast-container';
    toastContainer.className = 'fixed bottom-4 right-4 z-50 flex flex-col space-y-2 pointer-events-none';
    document.body.appendChild(toastContainer);
  }

  const toast = document.createElement('div');
  const borderCol = type === 'success' ? 'border-emerald-600 bg-slate-900 text-emerald-300' :
                    type === 'error' ? 'border-rose-600 bg-slate-900 text-rose-300' :
                    'border-cyan-600 bg-slate-900 text-cyan-300';

  toast.className = `p-3 rounded-xl border ${borderCol} shadow-2xl text-xs font-semibold max-w-sm pointer-events-auto flex items-center space-x-2 transition-all transform translate-y-2 opacity-0`;
  toast.innerText = message;
  toastContainer.appendChild(toast);

  requestAnimationFrame(() => {
    toast.classList.remove('translate-y-2', 'opacity-0');
  });

  setTimeout(() => {
    toast.classList.add('opacity-0', 'translate-y-2');
    setTimeout(() => toast.remove(), 300);
  }, 4000);
}

window.takeScreenshotUI = takeScreenshotUI;
window.checkForUpdatesUI = checkForUpdatesUI;
window.installUpdateUI = installUpdateUI;
window.showLabToast = showLabToast;
