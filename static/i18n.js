/**
 * LabVision Pro & Universal - Sistema de Internacionalización (i18n)
 * Creado por NachoFari (https://github.com/NachoFari)
 * Soporte bilingüe completo: Español (es) & Inglés (en)
 */

const LABVISION_I18N = {
  es: {
    // Barra superior
    app_title: "LabVision",
    app_subtitle: "Digitalización de Pantallas de Laboratorio a Excel & CSV",
    instrument_label: "Instrumento:",
    optgroup_presets: "─── Instrumentos Predefinidos ───",
    preset_viscometer: "Viscosímetro Digital (NDJ-8S)",
    preset_balance: "Balanza Analítica",
    optgroup_custom: "─── Plantillas Personalizadas ───",
    optgroup_actions: "─── Acciones de Plantilla ───",
    action_new_template: "📐 Diseñar Nueva Plantilla Personalizada...",
    action_import_template: "📂 Importar Plantilla (.lvtemplate)...",

    // Navegación principal
    nav_live: "Captura en Vivo",
    nav_chart: "Gráfico en Vivo",
    nav_history: "Historial & Datos",
    nav_calibration: "Calibración",
    nav_tutorial: "Tutorial",
    nav_settings: "Ajustes",

    // Botones de acción
    btn_start: "INICIAR LECTURA",
    btn_stop: "DETENER",
    btn_csv: "CSV",
    btn_excel: "Excel (.xlsx)",
    btn_screenshot: "Capturar Pantalla",
    btn_screenshot_title: "Tomar captura de pantalla de la aplicación (F9 / Botón)",
    btn_open_folder_title: "Abrir carpeta de resultados",

    // Modos de entrada
    lbl_source_video: "Archivo Video",
    lbl_source_camera: "Cámara Web",
    btn_select_file: "Seleccionar Archivo de Video",
    lbl_display_filter: "Filtro Óptico de Pantalla:",
    filter_standard: "Estándar / Neutro",
    filter_lcd_blue: "LCD Azul Retroiluminado (NDJ-8S)",
    filter_lcd_gray: "LCD Gris Reflectivo (Balanzas)",
    filter_led_red: "LED 7-Segmentos Rojo",
    filter_led_green: "LED 7-Segmentos Verde",
    filter_vfd_teal: "VFD Verde Agua (Fluorescente)",

    // Telemetría y tarjetas
    card_viscosity: "Viscosidad",
    card_torque: "Torque",
    card_speed: "Velocidad",
    card_rotor: "Rotor",
    card_weight: "Peso",
    card_unit: "Unidad",
    card_confidence: "Confianza OCR",
    card_status: "Estado de Lectura",
    status_optimal: "ÓPTIMA",
    status_doubtful: "DUDOSA",
    status_idle: "EN ESPERA",
    status_capturing: "EXTRAYENDO",

    // Modal de Exportación CSV
    modal_csv_title: "Exportación Científica CSV",
    modal_csv_mode_all: "Exportar Todo (Predeterminado)",
    modal_csv_mode_all_desc: "Exporta todas las variables registradas en el experimento",
    modal_csv_mode_custom: "Selección Específica de Columnas",
    modal_csv_mode_custom_desc: "Elige mediante casillas las variables que deseas en el archivo",
    modal_csv_available_cols: "Columnas Disponibles:",
    btn_select_all: "✓ Seleccionar Todas",
    btn_deselect_all: "✗ Deseleccionar Todas",
    btn_confirm_export: "Confirmar y Exportar CSV",
    btn_cancel: "Cancelar",

    // Modal Diseñador de Plantillas
    builder_title: "Diseñador de Plantillas No-Code de Instrumentos",
    builder_subtitle: "Dibuja las regiones de lectura (Sub-ROIs) directamente sobre el fotograma de referencia",
    builder_vars_header: "Variables / Sub-ROIs",
    builder_btn_add_var: "+ Añadir Variable",
    builder_btn_clear_all: "Limpiar Todo",
    builder_btn_test_ocr: "🔍 Probar OCR en Vivo",
    builder_btn_save: "💾 Guardar Plantilla",
    builder_btn_export: "📤 Exportar .lvtemplate",
    builder_close: "Cerrar Diseñador",

    // Ajustes
    settings_title: "Ajustes de LabVision",
    settings_lang_header: "Idioma de la Interfaz:",
    settings_theme_header: "Tema Visual y Mascota (NaTex Themes):",
    settings_updater_header: "Actualizaciones del Sistema (GitHub):",
    btn_check_updates: "Buscar Actualizaciones Ahora",
    lbl_current_version: "Versión Instalada:",
    lbl_latest_version: "Última Versión:",
    btn_download_update: "Descargar e Instalar Actualización",
    updater_up_to_date: "El software está actualizado a la última versión.",
    updater_checking: "Verificando con el repositorio oficial...",
    updater_available: "¡Nueva versión disponible en GitHub!",

    // Capturas y Audio
    toast_screenshot_saved: "Captura de pantalla guardada en: "
  },

  en: {
    // Topbar
    app_title: "LabVision",
    app_subtitle: "Laboratory Screen Digitization to Excel & CSV",
    instrument_label: "Instrument:",
    optgroup_presets: "─── Preset Instruments ───",
    preset_viscometer: "Digital Viscometer (NDJ-8S)",
    preset_balance: "Analytical Balance",
    optgroup_custom: "─── Custom Templates ───",
    optgroup_actions: "─── Template Actions ───",
    action_new_template: "📐 Design New Custom Template...",
    action_import_template: "📂 Import Template (.lvtemplate)...",

    // Navigation
    nav_live: "Live Capture",
    nav_chart: "Live Chart",
    nav_history: "History & Data",
    nav_calibration: "Calibration",
    nav_tutorial: "Tutorial",
    nav_settings: "Settings",

    // Action buttons
    btn_start: "START EXTRACTION",
    btn_stop: "STOP",
    btn_csv: "CSV",
    btn_excel: "Excel (.xlsx)",
    btn_screenshot: "Take Screenshot",
    btn_screenshot_title: "Capture application screenshot (F9 / Button)",
    btn_open_folder_title: "Open results folder",

    // Source Modes
    lbl_source_video: "Video File",
    lbl_source_camera: "Webcam",
    btn_select_file: "Select Video File",
    lbl_display_filter: "Optical Display Filter:",
    filter_standard: "Standard / Neutral",
    filter_lcd_blue: "Blue Backlit LCD (NDJ-8S)",
    filter_lcd_gray: "Gray Reflective LCD (Balances)",
    filter_led_red: "Red 7-Segment LED",
    filter_led_green: "Green 7-Segment LED",
    filter_vfd_teal: "Teal VFD (Vacuum Fluorescent)",

    // Telemetry & Cards
    card_viscosity: "Viscosity",
    card_torque: "Torque",
    card_speed: "Speed",
    card_rotor: "Rotor",
    card_weight: "Weight",
    card_unit: "Unit",
    card_confidence: "OCR Confidence",
    card_status: "Reading Status",
    status_optimal: "OPTIMAL",
    status_doubtful: "UNCERTAIN",
    status_idle: "IDLE",
    status_capturing: "READING",

    // CSV Export Modal
    modal_csv_title: "Scientific CSV Export",
    modal_csv_mode_all: "Export All (Default)",
    modal_csv_mode_all_desc: "Export all variables recorded in this experiment run",
    modal_csv_mode_custom: "Specific Column Selection",
    modal_csv_mode_custom_desc: "Check only the individual variables you want in the file",
    modal_csv_available_cols: "Available Columns:",
    btn_select_all: "✓ Select All",
    btn_deselect_all: "✗ Deselect All",
    btn_confirm_export: "Confirm & Export CSV",
    btn_cancel: "Cancel",

    // Template Builder Modal
    builder_title: "No-Code Instrument Template Designer",
    builder_subtitle: "Draw reading regions (Sub-ROIs) directly over the reference frame",
    builder_vars_header: "Variables / Sub-ROIs",
    builder_btn_add_var: "+ Add Variable",
    builder_btn_clear_all: "Clear All",
    builder_btn_test_ocr: "🔍 Test Live OCR",
    builder_btn_save: "💾 Save Template",
    builder_btn_export: "📤 Export .lvtemplate",
    builder_close: "Close Designer",

    // Settings
    settings_title: "LabVision Settings",
    settings_lang_header: "Interface Language:",
    settings_theme_header: "Visual Theme & Mascot (NaTex Themes):",
    settings_updater_header: "System Updates (GitHub):",
    btn_check_updates: "Check for Updates Now",
    lbl_current_version: "Installed Version:",
    lbl_latest_version: "Latest Version:",
    btn_download_update: "Download & Install Update",
    updater_up_to_date: "Software is up to date with the latest release.",
    updater_checking: "Checking with official GitHub repository...",
    updater_available: "A new version is available on GitHub!",

    // Audio & Screenshots
    toast_screenshot_saved: "Screenshot saved at: "
  }
};

let currentLanguage = 'es';

/**
 * Aplica el idioma especificado a todos los elementos del DOM marcados con [data-i18n]
 * @param {string} lang - 'es' o 'en'
 */
function applyLanguage(lang) {
  if (lang !== 'es' && lang !== 'en') lang = 'es';
  currentLanguage = lang;

  try {
    localStorage.setItem('labvision_language', lang);
  } catch (e) {}

  const dict = LABVISION_I18N[lang] || LABVISION_I18N.es;

  // Actualizar textos por data-i18n
  document.querySelectorAll('[data-i18n]').forEach(el => {
    const key = el.getAttribute('data-i18n');
    if (dict[key]) {
      el.innerText = dict[key];
    }
  });

  // Actualizar placeholders
  document.querySelectorAll('[data-i18n-placeholder]').forEach(el => {
    const key = el.getAttribute('data-i18n-placeholder');
    if (dict[key]) {
      el.placeholder = dict[key];
    }
  });

  // Actualizar titles/tooltips
  document.querySelectorAll('[data-i18n-title]').forEach(el => {
    const key = el.getAttribute('data-i18n-title');
    if (dict[key]) {
      el.title = dict[key];
    }
  });

  // Botones de cambio de idioma activos en la UI
  const btnEs = document.getElementById('btn-lang-es');
  const btnEn = document.getElementById('btn-lang-en');
  if (btnEs && btnEn) {
    if (lang === 'es') {
      btnEs.className = "px-3 py-1.5 rounded-lg text-xs font-bold bg-cyan-600 text-white shadow-sm";
      btnEn.className = "px-3 py-1.5 rounded-lg text-xs font-medium text-slate-400 hover:text-white hover:bg-slate-800 transition-colors";
    } else {
      btnEs.className = "px-3 py-1.5 rounded-lg text-xs font-medium text-slate-400 hover:text-white hover:bg-slate-800 transition-colors";
      btnEn.className = "px-3 py-1.5 rounded-lg text-xs font-bold bg-cyan-600 text-white shadow-sm";
    }
  }

  // Refrescar cuadrícula de temas si existe para actualizar nombres de temas en el nuevo idioma
  if (typeof renderThemeSelectorGrid === 'function') {
    const active = document.documentElement.getAttribute('data-theme') || 'fox';
    renderThemeSelectorGrid(active);
  }
}

// Inicialización automática
window.LABVISION_I18N = LABVISION_I18N;
window.applyLanguage = applyLanguage;

document.addEventListener('DOMContentLoaded', () => {
  let saved = 'es';
  try {
    saved = localStorage.getItem('labvision_language') || 'es';
  } catch (e) {}
  applyLanguage(saved);
});
