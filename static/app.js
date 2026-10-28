// =========================================================
// LabVision • Controlador Frontend Principal
// Creado por NachoFari
// =========================================================

let currentMode = 'viscometer';       // 'viscometer' | 'balance'
let currentProfile = 'normal';         // 'low' | 'normal' | 'high'
let currentScreen = 'live';            // 'live' | 'chart' | 'history' | 'calibration'
let sourceType = 'video';             // 'video' | 'camera'
let currentSource = null;             // ruta de archivo o número de cámara
let loadedImage = null;
let currentRoi = null;                // [x, y, w, h] en coordenadas del fotograma real
let isDrawing = false;
let startX = 0, startY = 0;
let pollInterval = null;
let lastRenderedRowIndex = -1;
let allStoredRows = [];
let currentHistoryFilter = 'all';

// Referencias DOM principales
const canvas = document.getElementById('roi-canvas');
const ctx = canvas ? canvas.getContext('2d') : null;
const placeholder = document.getElementById('canvas-placeholder');

// ================= INICIALIZACIÓN PYWEBVIEW Y PREFERENCIAS =================
window.addEventListener('pywebviewready', async () => {
  console.log("PyWebView API lista");
  await initApp();
});

document.addEventListener('DOMContentLoaded', () => {
  loadStoredPreferences();
  if (!window.pywebview) {
    setTimeout(initApp, 500);
  }
});

function loadStoredPreferences() {
  // 1. Cargar Tema
  const savedTheme = localStorage.getItem('lab_theme') || 'theme-dark';
  applyTheme(savedTheme, false);

  // 2. Cargar Escala de Fuente
  const savedScale = localStorage.getItem('lab_font_scale') || 'normal';
  setFontScale(savedScale, false);

  // 3. Cargar Densidad
  const savedDensity = localStorage.getItem('lab_table_density') || 'comfortable';
  setTableDensity(savedDensity, false);

  // 4. Cargar Ajustes de Audio
  if (window.labAudio) {
    const chkSucc = document.getElementById('chk-audio-success');
    const chkWarn = document.getElementById('chk-audio-warn');
    const sliderVol = document.getElementById('slider-volume');
    if (chkSucc) chkSucc.checked = window.labAudio.soundEnabled;
    if (chkWarn) chkWarn.checked = window.labAudio.warnSoundEnabled;
    if (sliderVol) sliderVol.value = window.labAudio.volume;
  }

  // 5. Cargar Intervalo de Auto-guardado
  const savedAutosave = localStorage.getItem('lab_autosave_min') || '20';
  const selAutosave = document.getElementById('select-autosave-interval');
  if (selAutosave) selAutosave.value = savedAutosave;
}

function changeAutosaveInterval(val) {
  const mins = parseFloat(val) || 20;
  localStorage.setItem('lab_autosave_min', mins.toString());
  if (window.pywebview && window.pywebview.api && window.pywebview.api.save_settings) {
    window.pywebview.api.save_settings({ autosave_interval_min: mins });
  }
}

async function initApp() {
  if (window.pywebview && window.pywebview.api) {
    try {
      const info = await window.pywebview.api.get_system_info();
      const hw = info.hardware;
      const hwText = document.getElementById('hw-text');
      const hwBadge = document.getElementById('hw-badge');

      if (hw.has_gpu) {
        hwText.innerText = "GPU CUDA";
        hwText.className = "text-emerald-400 font-semibold text-[11px]";
        hwBadge.title = hw.description;
      } else {
        hwText.innerText = "CPU (Notebook)";
        hwText.className = "text-sky-300 font-medium text-[11px]";
        hwBadge.title = "Optimizado para procesadores portátiles";
      }

      if (info.config && info.config.discord_webhook) {
        const discInput = document.getElementById('input-discord-url');
        if (discInput) discInput.value = info.config.discord_webhook;
      }
    } catch (e) {
      console.error("Error al obtener info de sistema:", e);
    }
  }
  setupCanvasEvents();
}

// ================= NAVEGACIÓN Y ENLACE A GITHUB (CREADO POR NACHOFARI) =================
function openGitHubProfile(e) {
  if (e) {
    try { e.preventDefault(); } catch (err) {}
  }
  const url = "https://github.com/NachoFari";
  if (window.pywebview && window.pywebview.api && window.pywebview.api.open_browser) {
    window.pywebview.api.open_browser(url);
  } else {
    window.open(url, "_blank");
  }
}

// ================= PANTALLAS / VISTAS PRINCIPALES =================
function switchScreen(screenName) {
  currentScreen = screenName;
  const screens = ['live', 'chart', 'history', 'calibration'];

  screens.forEach(s => {
    const el = document.getElementById(`screen-${s}`);
    const btn = document.getElementById(`nav-btn-${s}`);
    if (el) el.classList.toggle('hidden', s !== screenName);

    if (btn) {
      if (s === screenName) {
        btn.className = "px-3 py-1.5 rounded-lg text-xs font-semibold flex items-center space-x-1.5 transition-all bg-brand-600 text-white shadow-sm";
      } else {
        btn.className = "px-3 py-1.5 rounded-lg text-xs font-semibold flex items-center space-x-1.5 transition-all text-slate-400 hover:text-white hover:bg-slate-800";
      }
    }
  });

  if (screenName === 'chart') {
    if (typeof window.initLiveChart === 'function') {
      window.initLiveChart('live-chart-canvas', currentMode);
    }
  } else if (screenName === 'calibration') {
    runCameraCalibration();
  }
}

// ================= MODAL DE AJUSTES Y PERSONALIZACIÓN =================
function openSettingsModal() {
  document.getElementById('modal-settings').classList.remove('hidden');
}

function closeSettingsModal() {
  document.getElementById('modal-settings').classList.add('hidden');
}

// ================= TEMAS VISUALES =================
function applyTheme(themeClass, save = true) {
  const themes = ['theme-dark', 'theme-light', 'theme-oled', 'theme-sepia'];
  const body = document.body;
  const html = document.documentElement;

  themes.forEach(t => {
    body.classList.remove(t);
    html.classList.remove(t);
    const mark = document.getElementById(`mark-${t}`);
    if (mark) mark.classList.add('hidden');
  });

  body.classList.add(themeClass);
  html.classList.add(themeClass);

  const activeMark = document.getElementById(`mark-${themeClass}`);
  if (activeMark) activeMark.classList.remove('hidden');

  if (save) {
    localStorage.setItem('lab_theme', themeClass);
    if (window.pywebview && window.pywebview.api && window.pywebview.api.save_settings) {
      window.pywebview.api.save_settings({ theme: themeClass });
    }
  }
}

// ================= ESCALA DE TIPOGRAFÍA =================
function setFontScale(scale, save = true) {
  const btnNorm = document.getElementById('btn-font-normal');
  const btnLarge = document.getElementById('btn-font-large');

  if (scale === 'large') {
    document.body.classList.add('font-large');
    if (btnLarge) btnLarge.className = "py-2 px-3 rounded-lg border border-brand-500 bg-brand-500/10 text-brand-400 font-semibold text-center";
    if (btnNorm) btnNorm.className = "py-2 px-3 rounded-lg border border-slate-700 bg-slate-800 text-slate-300 font-semibold text-center";
  } else {
    document.body.classList.remove('font-large');
    if (btnNorm) btnNorm.className = "py-2 px-3 rounded-lg border border-brand-500 bg-brand-500/10 text-brand-400 font-semibold text-center";
    if (btnLarge) btnLarge.className = "py-2 px-3 rounded-lg border border-slate-700 bg-slate-800 text-slate-300 font-semibold text-center";
  }

  if (save) localStorage.setItem('lab_font_scale', scale);
}

// ================= DENSIDAD DE TABLA =================
function setTableDensity(density, save = true) {
  const tables = document.querySelectorAll('table');
  const btnComf = document.getElementById('btn-density-comf');
  const btnComp = document.getElementById('btn-density-comp');

  if (density === 'compact') {
    tables.forEach(t => t.classList.add('density-compact'));
    if (btnComp) btnComp.className = "py-2 px-3 rounded-lg border border-brand-500 bg-brand-500/10 text-brand-400 font-semibold text-center";
    if (btnComf) btnComf.className = "py-2 px-3 rounded-lg border border-slate-700 bg-slate-800 text-slate-300 font-semibold text-center";
  } else {
    tables.forEach(t => t.classList.remove('density-compact'));
    if (btnComf) btnComf.className = "py-2 px-3 rounded-lg border border-brand-500 bg-brand-500/10 text-brand-400 font-semibold text-center";
    if (btnComp) btnComp.className = "py-2 px-3 rounded-lg border border-slate-700 bg-slate-800 text-slate-300 font-semibold text-center";
  }

  if (save) localStorage.setItem('lab_table_density', density);
}

// ================= CONTROLES DE AUDIO SINTETIZADO =================
function toggleAudioSuccess(enabled) {
  if (window.labAudio) window.labAudio.setSoundEnabled(enabled);
}

function toggleAudioWarn(enabled) {
  if (window.labAudio) window.labAudio.setWarnSoundEnabled(enabled);
}

function changeAudioVolume(val) {
  if (window.labAudio) window.labAudio.setVolume(parseFloat(val));
}

function testAudioBeep() {
  if (window.labAudio) {
    window.labAudio.playSuccessBeep();
    setTimeout(() => window.labAudio.playWarningBeep(), 280);
  }
}

// ================= PANTALLA COMPLETA =================
function toggleFullscreen() {
  if (!document.fullscreenElement) {
    document.documentElement.requestFullscreen().catch(err => {
      console.warn("Fullscreen no soportado:", err);
    });
  } else {
    if (document.exitFullscreen) {
      document.exitFullscreen();
    }
  }
}

// ================= PERFILES DE RENDIMIENTO =================
function setProfile(prof) {
  currentProfile = prof;
  const pLow = document.getElementById('prof-low');
  const pNorm = document.getElementById('prof-normal');
  const pHigh = document.getElementById('prof-high');
  const hint = document.getElementById('profile-hint');

  const btnActive = "py-1.5 px-1.5 rounded-lg border text-xs font-medium flex flex-col items-center justify-center border-brand-500 bg-brand-500/10 text-brand-400 transition-all";
  const btnInactive = "py-1.5 px-1.5 rounded-lg border text-xs font-medium flex flex-col items-center justify-center border-slate-700 bg-slate-800/40 text-slate-400 hover:text-slate-200 transition-all";

  pLow.className = prof === 'low' ? btnActive : btnInactive;
  pNorm.className = prof === 'normal' ? btnActive : btnInactive;
  pHigh.className = prof === 'high' ? btnActive : btnInactive;

  if (prof === 'low') {
    hint.innerText = "Bajo (Menor uso CPU)";
    hint.className = "text-[10px] text-amber-400 font-medium";
  } else if (prof === 'high') {
    hint.innerText = "Alto (Máxima resolución / GPU)";
    hint.className = "text-[10px] text-cyan-400 font-medium";
  } else {
    hint.innerText = "Equilibrado";
    hint.className = "text-[10px] text-brand-400 font-medium";
  }
}

function updateBalanceUnit() {
  const unit = document.getElementById('balance-unit')?.value || 'g';
  const label = document.getElementById('card-unit-label');
  if (label) label.innerText = unit;
  if (window.labChart) window.labChart.configure(currentMode, unit);
}

// ================= CAMBIO DE MODO: VISCOSÍMETRO / BALANZA =================
function switchMode(mode) {
  currentMode = mode;
  const tabVisc = document.getElementById('tab-viscometer');
  const tabBal = document.getElementById('tab-balance');
  const viscCards = document.getElementById('viscometer-cards');
  const balCards = document.getElementById('balance-cards');
  const viscSettings = document.getElementById('viscometer-settings');
  const balSettings = document.getElementById('balance-settings');
  const tableHeaders = document.getElementById('table-headers');

  if (mode === 'viscometer') {
    tabVisc.className = "flex-1 py-1.5 px-3 rounded-lg text-xs font-semibold flex items-center justify-center space-x-2 transition-all bg-brand-600 text-white shadow-sm";
    tabBal.className = "flex-1 py-1.5 px-3 rounded-lg text-xs font-semibold flex items-center justify-center space-x-2 transition-all text-slate-400 hover:text-white hover:bg-slate-800";
    viscCards.classList.remove('hidden');
    balCards.classList.add('hidden');
    viscSettings.classList.remove('hidden');
    balSettings.classList.add('hidden');

    tableHeaders.innerHTML = `
      <th class="py-2 px-3">Tiempo</th>
      <th class="py-2 px-3">Timestamp</th>
      <th class="py-2 px-3">Rotor</th>
      <th class="py-2 px-3">RPM</th>
      <th class="py-2 px-3">Viscosidad (mPa·s)</th>
      <th class="py-2 px-3">Torque (%)</th>
      <th class="py-2 px-3 text-center">Confianza</th>
      <th class="py-2 px-3 text-center">Estado</th>
    `;
  } else {
    tabBal.className = "flex-1 py-1.5 px-3 rounded-lg text-xs font-semibold flex items-center justify-center space-x-2 transition-all bg-brand-600 text-white shadow-sm";
    tabVisc.className = "flex-1 py-1.5 px-3 rounded-lg text-xs font-semibold flex items-center justify-center space-x-2 transition-all text-slate-400 hover:text-white hover:bg-slate-800";
    viscCards.classList.add('hidden');
    balCards.classList.remove('hidden');
    viscSettings.classList.add('hidden');
    balSettings.classList.remove('hidden');

    const unit = document.getElementById('balance-unit')?.value || 'g';
    document.getElementById('card-unit-label').innerText = unit;

    tableHeaders.innerHTML = `
      <th class="py-2 px-3">Tiempo</th>
      <th class="py-2 px-3">Timestamp</th>
      <th class="py-2 px-3">Peso (${unit})</th>
      <th class="py-2 px-3">Unidad</th>
      <th class="py-2 px-3 text-center">Confianza</th>
      <th class="py-2 px-3 text-center">Estado</th>
    `;
  }

  if (typeof window.switchChartMode === 'function') {
    window.switchChartMode(mode);
  }
}

// ================= SELECCIÓN DE FUENTE: VIDEO / CÁMARA =================
function setSourceType(type) {
  sourceType = type;
  const btnVideo = document.getElementById('btn-src-video');
  const btnCam = document.getElementById('btn-src-camera');
  const boxVideo = document.getElementById('box-video-file');
  const boxCam = document.getElementById('box-camera-select');

  if (type === 'video') {
    btnVideo.className = "py-1.5 px-2.5 rounded-lg border text-xs font-medium flex items-center justify-center space-x-1.5 border-brand-500 bg-brand-500/10 text-brand-400";
    btnCam.className = "py-1.5 px-2.5 rounded-lg border text-xs font-medium flex items-center justify-center space-x-1.5 border-slate-700 bg-slate-800/50 text-slate-400 hover:text-slate-200";
    boxVideo.classList.remove('hidden');
    boxCam.classList.add('hidden');
  } else {
    btnCam.className = "py-1.5 px-2.5 rounded-lg border text-xs font-medium flex items-center justify-center space-x-1.5 border-brand-500 bg-brand-500/10 text-brand-400";
    btnVideo.className = "py-1.5 px-2.5 rounded-lg border text-xs font-medium flex items-center justify-center space-x-1.5 border-slate-700 bg-slate-800/50 text-slate-400 hover:text-slate-200";
    boxVideo.classList.add('hidden');
    boxCam.classList.remove('hidden');
    refreshCameras();
  }
}

async function browseVideoFile() {
  if (!window.pywebview) return;
  const filePath = await window.pywebview.api.select_video_dialog();
  if (filePath) {
    currentSource = filePath;
    document.getElementById('selected-video-name').innerText = filePath.split(/[\\/]/).pop();
    await loadFramePreview(filePath);
  }
}

async function refreshCameras() {
  if (!window.pywebview) return;
  const select = document.getElementById('camera-select');
  select.innerHTML = "<option>Buscando cámaras...</option>";
  try {
    const list = await window.pywebview.api.list_cameras();
    select.innerHTML = "";
    list.forEach(cam => {
      const opt = document.createElement('option');
      opt.value = cam.index;
      opt.innerText = cam.name;
      select.appendChild(opt);
    });
    if (list.length > 0) {
      currentSource = list[0].index;
      await loadFramePreview(currentSource);
    }
  } catch (e) {
    console.error("Error listando cámaras:", e);
  }
}

document.getElementById('camera-select')?.addEventListener('change', async (e) => {
  currentSource = parseInt(e.target.value);
  await loadFramePreview(currentSource);
});

// ================= CARGA DE PREVIEW Y CANVAS ROI =================
async function loadFramePreview(source) {
  if (!window.pywebview) return;
  const res = await window.pywebview.api.get_video_frame(source, 1.0);
  if (res.error) {
    alert("Error al cargar imagen previa: " + res.error);
    return;
  }

  const img = new Image();
  img.onload = () => {
    loadedImage = {
      element: img,
      origWidth: res.width,
      origHeight: res.height,
      previewWidth: res.preview_width,
      previewHeight: res.preview_height
    };
    if (canvas) {
      canvas.width = res.preview_width;
      canvas.height = res.preview_height;
    }
    if (placeholder) placeholder.classList.add('hidden');

    if (res.suggested_roi && !currentRoi) {
      currentRoi = res.suggested_roi;
      const chk = document.getElementById('chk-auto-track');
      if (chk) chk.checked = true;
    }

    redrawCanvas();
  };
  img.src = res.image_base64;
}

function redrawCanvas() {
  if (!loadedImage || !canvas || !ctx) return;
  ctx.clearRect(0, 0, canvas.width, canvas.height);
  ctx.drawImage(loadedImage.element, 0, 0, canvas.width, canvas.height);

  if (currentRoi) {
    const scaleX = canvas.width / loadedImage.origWidth;
    const scaleY = canvas.height / loadedImage.origHeight;
    const rx = currentRoi[0] * scaleX;
    const ry = currentRoi[1] * scaleY;
    const rw = currentRoi[2] * scaleX;
    const rh = currentRoi[3] * scaleY;

    // Sombra oscura
    ctx.fillStyle = "rgba(0, 0, 0, 0.45)";
    ctx.fillRect(0, 0, canvas.width, ry);
    ctx.fillRect(0, ry, rx, rh);
    ctx.fillRect(rx + rw, ry, canvas.width - (rx + rw), rh);
    ctx.fillRect(0, ry + rh, canvas.width, canvas.height - (ry + rh));

    // Borde Neón
    ctx.strokeStyle = "#00f0ff";
    ctx.lineWidth = 2;
    ctx.setLineDash([4, 2]);
    ctx.strokeRect(rx, ry, rw, rh);
    ctx.setLineDash([]);

    // Etiqueta
    ctx.fillStyle = "#00f0ff";
    ctx.font = "bold 11px monospace";
    ctx.fillText("PANTALLA SELECCIONADA", rx + 4, Math.max(14, ry - 4));
  }
}

function setupCanvasEvents() {
  if (!canvas) return;

  canvas.addEventListener('mousedown', (e) => {
    if (!loadedImage) return;
    const rect = canvas.getBoundingClientRect();
    const scaleX = canvas.width / rect.width;
    const scaleY = canvas.height / rect.height;
    startX = (e.clientX - rect.left) * scaleX;
    startY = (e.clientY - rect.top) * scaleY;
    isDrawing = true;
  });

  canvas.addEventListener('mousemove', (e) => {
    if (!isDrawing || !loadedImage) return;
    const rect = canvas.getBoundingClientRect();
    const scaleX = canvas.width / rect.width;
    const scaleY = canvas.height / rect.height;
    const currentX = (e.clientX - rect.left) * scaleX;
    const currentY = (e.clientY - rect.top) * scaleY;

    const x = Math.min(startX, currentX);
    const y = Math.min(startY, currentY);
    const w = Math.abs(currentX - startX);
    const h = Math.abs(currentY - startY);

    const origScaleX = loadedImage.origWidth / canvas.width;
    const origScaleY = loadedImage.origHeight / canvas.height;
    currentRoi = [
      Math.round(x * origScaleX),
      Math.round(y * origScaleY),
      Math.round(w * origScaleX),
      Math.round(h * origScaleY)
    ];

    redrawCanvas();
  });

  canvas.addEventListener('mouseup', () => { isDrawing = false; });
  canvas.addEventListener('mouseleave', () => { isDrawing = false; });
}

function clearRoi() {
  currentRoi = null;
  redrawCanvas();
}

// ================= TEST INSTANTÁNEO EN UN CUADRO =================
async function testCurrentRoi() {
  if (!window.pywebview) return;
  if (!currentSource) {
    alert("Primero selecciona un archivo de video o cámara.");
    return;
  }

  const btn = document.getElementById('btn-test-frame');
  btn.innerText = "Leyendo...";
  btn.disabled = true;

  try {
    const unit = document.getElementById('balance-unit')?.value || 'g';
    const autoTrack = document.getElementById('chk-auto-track')?.checked || false;
    const res = await window.pywebview.api.test_roi_reading(
      currentSource, currentRoi, currentMode, unit, currentProfile, autoTrack
    );

    const resultBox = document.getElementById('test-result-box');
    const confSpan = document.getElementById('test-conf');
    const details = document.getElementById('test-details');
    resultBox.classList.remove('hidden');

    if (res.success && res.parsed) {
      const p = res.parsed;
      const conf = Math.round((p.confidence || 0.95) * 100);
      confSpan.innerText = `${conf}% confianza`;
      confSpan.className = p.is_bad ? "text-rose-400 font-bold" : "text-emerald-400 font-bold";

      if (window.labAudio) {
        if (p.is_bad) window.labAudio.playWarningBeep();
        else window.labAudio.playSuccessBeep();
      }

      if (currentMode === 'viscometer') {
        details.innerHTML = `
          <div><b>Viscosidad:</b> ${p.viscosity_mpa !== null ? p.viscosity_mpa + ' mPa·s' : 'No detectado'}</div>
          <div><b>Torque:</b> ${p.torque_pct !== null ? p.torque_pct + ' %' : 'No detectado'}</div>
          <div><b>Velocidad:</b> ${p.speed_rpm !== null ? p.speed_rpm + ' RPM' : '--'} | <b>Rotor:</b> ${p.rotor || '--'}</div>
          ${p.is_bad ? `<div class="text-rose-300 mt-1">Aviso: ${p.warning}</div>` : '<div class="text-emerald-400 mt-1">Lectura óptima</div>'}
        `;
      } else {
        details.innerHTML = `
          <div><b>Peso Detectado:</b> ${p.weight !== null ? p.weight + ' ' + p.unit : 'No detectado'}</div>
          ${p.is_bad ? `<div class="text-rose-300 mt-1">Aviso: ${p.warning}</div>` : '<div class="text-emerald-400 mt-1">Lectura óptima</div>'}
        `;
      }
    } else {
      details.innerHTML = `<span class="text-rose-400">${res.error || 'Error al procesar'}</span>`;
    }
  } catch (e) {
    console.error("Error en test de ROI:", e);
  } finally {
    btn.innerHTML = "<span>Probar Lectura</span>";
    btn.disabled = false;
  }
}

// ================= CALIBRACIÓN DE CÁMARA =================
async function runCameraCalibration() {
  if (!window.pywebview || !currentSource) return;

  const banner = document.getElementById('full-calib-banner');
  if (banner) banner.innerHTML = "<span>Analizando iluminación, enfoque y reflejos de la cámara...</span>";

  try {
    const res = await window.pywebview.api.calibrate_camera(currentSource, currentRoi);

    if (res.success && res.evaluation) {
      const ev = res.evaluation;
      if (banner) {
        if (ev.is_ready) {
          banner.className = "p-4 rounded-xl border bg-emerald-950/70 border-emerald-700 text-emerald-300 font-semibold flex items-center space-x-2";
          banner.innerHTML = "<span>[OK] Cámara calibrada de forma óptima para lectura automática.</span>";
        } else {
          banner.className = "p-4 rounded-xl border bg-amber-950/70 border-amber-700 text-amber-300 font-semibold flex items-center space-x-2";
          banner.innerHTML = "<span>[AVISO] Se recomiendan pequeños ajustes de encuadre o iluminación.</span>";
        }
      }

      const fMsg = document.getElementById('full-calib-focus-msg');
      const fBadge = document.getElementById('full-calib-focus-badge');
      if (fMsg) fMsg.innerText = ev.focus_msg;
      if (fBadge) {
        fBadge.innerText = `Score: ${ev.blur_score}`;
        fBadge.className = ev.focus_status === 'ok' ? 'px-2.5 py-1 rounded text-xs font-bold bg-emerald-900 text-emerald-300' : 'px-2.5 py-1 rounded text-xs font-bold bg-rose-900 text-rose-300';
      }

      const gMsg = document.getElementById('full-calib-glare-msg');
      const gBadge = document.getElementById('full-calib-glare-badge');
      if (gMsg) gMsg.innerText = ev.glare_msg;
      if (gBadge) {
        gBadge.innerText = `${ev.glare_pct}%`;
        gBadge.className = ev.glare_status === 'ok' ? 'px-2.5 py-1 rounded text-xs font-bold bg-emerald-900 text-emerald-300' : 'px-2.5 py-1 rounded text-xs font-bold bg-rose-900 text-rose-300';
      }

      const lMsg = document.getElementById('full-calib-lum-msg');
      const lBadge = document.getElementById('full-calib-lum-badge');
      if (lMsg) lMsg.innerText = ev.lum_msg;
      if (lBadge) {
        lBadge.innerText = `${ev.mean_lum} / 255`;
        lBadge.className = ev.lum_status === 'ok' ? 'px-2.5 py-1 rounded text-xs font-bold bg-emerald-900 text-emerald-300' : 'px-2.5 py-1 rounded text-xs font-bold bg-rose-900 text-rose-300';
      }
    }
  } catch (e) {
    console.error("Error en calibración:", e);
  }
}

// ================= INICIAR Y DETENER EXTRACCIÓN =================
async function startExtraction() {
  if (window.labAudio && window.labAudio.resume) {
    window.labAudio.resume();
  }
  if (!window.pywebview) return;
  if (!currentSource) {
    alert("Por favor selecciona un video o cámara antes de iniciar.");
    return;
  }

  const sampleInterval = parseFloat(document.getElementById('sample-interval').value) || 1.0;
  const unit = document.getElementById('balance-unit')?.value || 'g';
  const autoTrack = document.getElementById('chk-auto-track')?.checked || false;

  const options = {
    source: currentSource,
    mode: currentMode,
    roi: currentRoi,
    sample_interval: sampleInterval,
    unit: unit,
    profile: currentProfile,
    auto_track: autoTrack,
    min_confidence: 0.45
  };

  const res = await window.pywebview.api.start_processing(options);
  if (res.error) {
    alert("Error al iniciar: " + res.error);
    return;
  }

  document.getElementById('btn-start').disabled = true;
  document.getElementById('btn-start').classList.add('opacity-40');
  document.getElementById('btn-stop').disabled = false;
  document.getElementById('btn-open-excel').disabled = true;
  document.getElementById('btn-open-csv').disabled = true;

  document.getElementById('table-body').innerHTML = "";
  document.getElementById('history-table-body').innerHTML = "";
  allStoredRows = [];
  lastRenderedRowIndex = -1;

  if (window.labChart) window.labChart.reset();

  if (pollInterval) clearInterval(pollInterval);
  pollInterval = setInterval(updateLiveStatus, 500);
}

async function stopExtraction() {
  if (!window.pywebview) return;
  await window.pywebview.api.stop_processing();
  document.getElementById('btn-stop').disabled = true;
}

// ================= SONDEO DE ESTADO EN VIVO =================
async function updateLiveStatus() {
  if (!window.pywebview) return;
  try {
    const state = await window.pywebview.api.get_status();

    document.getElementById('progress-bar').style.width = `${state.progress_pct}%`;
    document.getElementById('progress-percent').innerText = `${state.progress_pct}%`;
    document.getElementById('counter-rows').innerText = state.rows_extracted;
    document.getElementById('live-time-str').innerText = state.current_time_str;
    const liveTimer = document.getElementById('live-timer');
    if (liveTimer) liveTimer.innerText = state.current_time_str;

    if (state.current_reading) {
      const cr = state.current_reading;
      if (currentMode === 'viscometer') {
        document.getElementById('card-viscosity').innerText = cr.viscosity_mpa !== null ? cr.viscosity_mpa : '--';
        document.getElementById('card-torque').innerText = cr.torque_pct !== null ? cr.torque_pct : '--';
        document.getElementById('card-rpm').innerText = cr.speed_rpm !== null ? cr.speed_rpm : '--';
        document.getElementById('card-rotor').innerText = cr.rotor !== null ? cr.rotor : '--';
      } else {
        document.getElementById('card-weight').innerText = cr.weight !== null ? cr.weight : '--';
      }
    }

    const alertBanner = document.getElementById('quality-alert-banner');
    const alertReason = document.getElementById('alert-reason-text');
    if (state.quality_alert) {
      alertBanner.classList.remove('hidden');
      alertReason.innerText = state.alert_message || "Lectura dudosa o datos incompletos detectados.";
    } else {
      alertBanner.classList.add('hidden');
    }

    if (state.recent_rows && state.recent_rows.length > 0) {
      const tbody = document.getElementById('table-body');
      const historyTbody = document.getElementById('history-table-body');

      state.recent_rows.forEach((row) => {
        if (row.time_sec > lastRenderedRowIndex) {
          lastRenderedRowIndex = row.time_sec;
          allStoredRows.push(row);

          // Actualizar contador
          const countBadge = document.getElementById('badge-total-records');
          if (countBadge) countBadge.innerText = `${allStoredRows.length} lecturas`;

          // Confianza con badge de color
          const conf = Math.round((row.confidence || 0.95) * 100);
          let confBadgeClass = "px-2 py-0.5 rounded text-[10px] font-bold bg-emerald-950/80 border border-emerald-700 text-emerald-300";
          if (conf < 70 || row.is_bad) {
            confBadgeClass = "px-2 py-0.5 rounded text-[10px] font-bold bg-rose-950/80 border border-rose-700 text-rose-300";
          } else if (conf < 85) {
            confBadgeClass = "px-2 py-0.5 rounded text-[10px] font-bold bg-amber-950/80 border border-amber-700 text-amber-300";
          }

          // Sonido de confirmación sintético de laboratorio
          if (window.labAudio) {
            if (row.is_bad) {
              window.labAudio.playWarningBeep();
            } else {
              window.labAudio.playSuccessBeep();
            }
          }

          // Alimentar Gráfico en Vivo
          if (typeof window.updateLiveChart === 'function') {
            const chartVal = currentMode === 'viscometer' ? row.viscosity_mpa : row.weight;
            window.updateLiveChart(row.time_sec, chartVal, row.is_bad);
          }

          // Insertar en Tabla de Registro en Vivo
          const tr = document.createElement('tr');
          tr.className = row.is_bad ? "table-row-warn" : "hover:bg-slate-800/40 transition-colors";

          if (currentMode === 'viscometer') {
            tr.innerHTML = `
              <td class="py-2 px-3 font-semibold">${row.time_sec}s</td>
              <td class="py-2 px-3 text-slate-400">${row.timestamp_str}</td>
              <td class="py-2 px-3">${row.rotor || '-'}</td>
              <td class="py-2 px-3">${row.speed_rpm || '-'}</td>
              <td class="py-2 px-3 font-bold text-cyan-300">${row.viscosity_mpa !== null ? row.viscosity_mpa : '-'}</td>
              <td class="py-2 px-3">${row.torque_pct !== null ? row.torque_pct + '%' : '-'}</td>
              <td class="py-2 px-3 text-center"><span class="${confBadgeClass}">${conf}%</span></td>
              <td class="py-2 px-3 text-center">${row.is_bad ? '<span class="px-1.5 py-0.5 rounded bg-rose-900/60 text-rose-300 text-[10px]">DUDOSA</span>' : '<span class="px-1.5 py-0.5 rounded bg-emerald-900/60 text-emerald-300 text-[10px]">OK</span>'}</td>
            `;
          } else {
            tr.innerHTML = `
              <td class="py-2 px-3 font-semibold">${row.time_sec}s</td>
              <td class="py-2 px-3 text-slate-400">${row.timestamp_str}</td>
              <td class="py-2 px-3 font-bold text-cyan-300">${row.weight !== null ? row.weight : '-'}</td>
              <td class="py-2 px-3">${row.unit || 'g'}</td>
              <td class="py-2 px-3 text-center"><span class="${confBadgeClass}">${conf}%</span></td>
              <td class="py-2 px-3 text-center">${row.is_bad ? '<span class="px-1.5 py-0.5 rounded bg-rose-900/60 text-rose-300 text-[10px]">DUDOSA</span>' : '<span class="px-1.5 py-0.5 rounded bg-emerald-900/60 text-emerald-300 text-[10px]">OK</span>'}</td>
            `;
          }
          tbody.prepend(tr);

          // Insertar también en Tabla Histórica Completa
          if (historyTbody) {
            const hTr = document.createElement('tr');
            hTr.className = row.is_bad ? "table-row-warn" : "hover:bg-slate-800/40";
            const mainVal = currentMode === 'viscometer' ? `${row.viscosity_mpa} mPa·s` : `${row.weight} ${row.unit || 'g'}`;
            const secVal = currentMode === 'viscometer' ? `Torque: ${row.torque_pct}% | RPM: ${row.speed_rpm} | Rotor: ${row.rotor}` : `Unidad: ${row.unit || 'g'}`;

            hTr.innerHTML = `
              <td class="py-2.5 px-4 font-semibold">${row.time_sec}s</td>
              <td class="py-2.5 px-4 text-slate-400">${row.timestamp_str}</td>
              <td class="py-2.5 px-4 font-bold text-cyan-300">${mainVal}</td>
              <td class="py-2.5 px-4 text-slate-300">${secVal}</td>
              <td class="py-2.5 px-4 text-center"><span class="${confBadgeClass}">${conf}%</span></td>
              <td class="py-2.5 px-4 text-center">${row.is_bad ? '<span class="px-2 py-0.5 rounded bg-rose-900/60 text-rose-300 text-[10px]">DUDOSA</span>' : '<span class="px-2 py-0.5 rounded bg-emerald-900/60 text-emerald-300 text-[10px]">OK</span>'}</td>
            `;
            historyTbody.prepend(hTr);
          }
        }
      });
    }

    if (!state.is_running && state.progress_pct >= 100) {
      clearInterval(pollInterval);
      document.getElementById('btn-start').disabled = false;
      document.getElementById('btn-start').classList.remove('opacity-40');
      document.getElementById('btn-stop').disabled = true;
      document.getElementById('btn-open-excel').disabled = false;
      document.getElementById('btn-open-csv').disabled = false;
      alertBanner.classList.add('hidden');
    }

    if (state.error_msg) {
      clearInterval(pollInterval);
      alert("Error: " + state.error_msg);
      document.getElementById('btn-start').disabled = false;
      document.getElementById('btn-start').classList.remove('opacity-40');
      document.getElementById('btn-stop').disabled = true;
    }

  } catch (e) {
    console.error("Error en polling:", e);
  }
}

// ================= FILTRADO DE HISTORIAL =================
function filterHistory(filterType) {
  currentHistoryFilter = filterType;
  const historyTbody = document.getElementById('history-table-body');
  if (!historyTbody) return;

  const btnAll = document.getElementById('filter-all');
  const btnVal = document.getElementById('filter-valid');
  const btnWarn = document.getElementById('filter-warn');

  [btnAll, btnVal, btnWarn].forEach(b => {
    if (b) b.className = "px-2.5 py-1 rounded text-slate-400 hover:text-white";
  });

  if (filterType === 'all' && btnAll) btnAll.className = "px-2.5 py-1 rounded bg-slate-800 text-white font-medium";
  if (filterType === 'valid' && btnVal) btnVal.className = "px-2.5 py-1 rounded bg-emerald-900 text-emerald-300 font-medium";
  if (filterType === 'warn' && btnWarn) btnWarn.className = "px-2.5 py-1 rounded bg-rose-900 text-rose-300 font-medium";

  historyTbody.innerHTML = "";
  const filtered = allStoredRows.filter(r => {
    if (filterType === 'valid') return !r.is_bad;
    if (filterType === 'warn') return r.is_bad;
    return true;
  });

  if (filtered.length === 0) {
    historyTbody.innerHTML = `<tr><td colspan="6" class="py-12 text-center text-slate-500 italic">No hay registros coincidentes con el filtro.</td></tr>`;
    return;
  }

  filtered.forEach(row => {
    const hTr = document.createElement('tr');
    hTr.className = row.is_bad ? "table-row-warn" : "hover:bg-slate-800/40";
    const conf = Math.round((row.confidence || 0.95) * 100);
    let confBadgeClass = conf < 70 || row.is_bad ? "px-2 py-0.5 rounded text-[10px] font-bold bg-rose-950/80 border border-rose-700 text-rose-300" : "px-2 py-0.5 rounded text-[10px] font-bold bg-emerald-950/80 border border-emerald-700 text-emerald-300";
    const mainVal = currentMode === 'viscometer' ? `${row.viscosity_mpa} mPa·s` : `${row.weight} ${row.unit || 'g'}`;
    const secVal = currentMode === 'viscometer' ? `Torque: ${row.torque_pct}% | RPM: ${row.speed_rpm} | Rotor: ${row.rotor}` : `Unidad: ${row.unit || 'g'}`;

    hTr.innerHTML = `
      <td class="py-2.5 px-4 font-semibold">${row.time_sec}s</td>
      <td class="py-2.5 px-4 text-slate-400">${row.timestamp_str}</td>
      <td class="py-2.5 px-4 font-bold text-cyan-300">${mainVal}</td>
      <td class="py-2.5 px-4 text-slate-300">${secVal}</td>
      <td class="py-2.5 px-4 text-center"><span class="${confBadgeClass}">${conf}%</span></td>
      <td class="py-2.5 px-4 text-center">${row.is_bad ? '<span class="px-2 py-0.5 rounded bg-rose-900/60 text-rose-300 text-[10px]">DUDOSA</span>' : '<span class="px-2 py-0.5 rounded bg-emerald-900/60 text-emerald-300 text-[10px]">OK</span>'}</td>
    `;
    historyTbody.appendChild(hTr);
  });
}

// ================= ACCIONES DE GRÁFICO =================
function exportChartPng() {
  if (typeof window.exportChartImage === 'function') {
    window.exportChartImage();
  }
}

function resetLiveChart() {
  if (typeof window.resetChart === 'function') {
    window.resetChart();
  }
}

// ================= APERTURA DE EXCEL Y CSV =================
async function openExcelResult() {
  if (!window.pywebview) return;
  const res = await window.pywebview.api.open_excel();
  if (res.error) alert(res.error);
}

async function openCsvResult() {
  if (!window.pywebview) return;
  const res = await window.pywebview.api.open_csv();
  if (res.error) {
    const exp = await window.pywebview.api.export_csv_now();
    if (exp.success) {
      await window.pywebview.api.open_csv(exp.file_path);
    } else {
      alert(res.error);
    }
  }
}

async function openOutputFolder() {
  if (!window.pywebview) return;
  const res = await window.pywebview.api.open_folder();
  if (res.error) alert(res.error);
}

// ================= TUTORIAL Y DISCORD =================
function openTutorialModal() {
  document.getElementById('modal-tutorial').classList.remove('hidden');
}

function closeTutorialModal() {
  document.getElementById('modal-tutorial').classList.add('hidden');
}

function openDiscordModal() {
  document.getElementById('modal-discord').classList.remove('hidden');
}

function closeDiscordModal() {
  document.getElementById('modal-discord').classList.add('hidden');
}

async function testDiscordWebhook() {
  if (!window.pywebview) return;
  const url = document.getElementById('input-discord-url').value.trim();
  const fb = document.getElementById('discord-test-feedback');
  fb.classList.remove('hidden');
  fb.className = "p-2 rounded-lg text-xs bg-slate-800 text-slate-300";
  fb.innerText = "Enviando prueba a Discord...";

  const res = await window.pywebview.api.test_discord(url);
  if (res.success) {
    fb.className = "p-2 rounded-lg text-xs bg-emerald-950 border border-emerald-700 text-emerald-300";
    fb.innerText = "[OK] " + res.message;
  } else {
    fb.className = "p-2 rounded-lg text-xs bg-rose-950 border border-rose-700 text-rose-300";
    fb.innerText = "[ERROR] " + res.message;
  }
}

async function saveDiscordWebhook() {
  if (!window.pywebview) return;
  const url = document.getElementById('input-discord-url').value.trim();
  await window.pywebview.api.save_settings({ discord_webhook: url });
  closeDiscordModal();
}

// ================= DEEP LINKING Y TESTING =================
window.addEventListener('DOMContentLoaded', () => {
  setTimeout(() => {
    const hash = window.location.hash;
    if (hash === '#settings') openSettingsModal();
    else if (hash === '#chart') switchScreen('chart');
    else if (hash === '#history') switchScreen('history');
    else if (hash === '#calibration') switchScreen('calibration');
    else if (hash === '#tutorial') openTutorialModal();
    else if (hash === '#discord') openDiscordModal();

    if (window.location.search.includes('theme=light')) applyTheme('theme-light');
    else if (window.location.search.includes('theme=oled')) applyTheme('theme-oled');
    else if (window.location.search.includes('theme=sepia')) applyTheme('theme-sepia');
  }, 100);
});

