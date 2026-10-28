# 🧪 LabVision `v0.3`
### *Digitalización Inteligente de Pantallas de Laboratorio a Excel & CSV*

[![Version](https://img.shields.io/badge/version-v0.3-cyan.svg)](https://github.com/NachoFari)
[![Python](https://img.shields.io/badge/python-3.10%20%7C%203.11%20%7C%203.12-blue.svg)](https://www.python.org/)
[![GUI](https://img.shields.io/badge/gui-PyWebView%20%2B%20Edge%20Chromium-teal.svg)](https://pywebview.flowrl.com/)
[![OCR Engine](https://img.shields.io/badge/ocr-OpenCV%20%2B%20EasyOCR%20%2B%20PyTorch-emerald.svg)](https://github.com/JaidedAI/EasyOCR)
[![Author](https://img.shields.io/badge/creado%20por-NachoFari-orange.svg)](https://github.com/NachoFari)

---

## 📌 Descripción

**LabVision** es un software de escritorio para Windows diseñado para laboratorios científicos e industriales. Permite extraer de manera automática y en tiempo real las lecturas numéricas mostradas en las pantallas de instrumentos analíticos (como el **Viscosímetro Rotacional NDJ-8S** o **Balanzas Digitales de Precisión**), ya sea directamente desde una cámara USB/webcam o a partir de archivos de video grabados (`.mp4`, `.avi`, `.mov`).

Los datos leídos se procesan mediante visión por computadora (OpenCV y PyTorch/EasyOCR), se validan con filtros de confianza estadística y se transmiten directamente a disco en streaming continuo (CSV y Excel `.xlsx`) con protección total ante cortes de energía.

---

## 🚀 Características Principales

1. **4 Pantallas y Modos de Trabajo:**
   * 🖥️ **Captura en Vivo:** Dashboard central con visor interactivo de encuadre (ROI), tarjetas de parámetros principales y tabla en tiempo real acotada y delimitada al píxel.
   * 📈 **Gráficos en Vivo:** Visualización continua de tendencias con HUD de estadísticas dinámicas (Mínimo, Máximo, Promedio, Último valor) y exportación a PNG.
   * 🗄️ **Base de Datos:** Historial tabular completo con filtros rápidos por nivel de confianza y exportación directa.
   * ⚙️ **Calibración:** Visor de diagnóstico para ajustar contraste, binarización y preprocesamiento de imagen.

2. **Instrumentos Soportados:**
   * 🧪 **Viscosímetro Digital (NDJ-8S):** Lectura sincronizada de Viscosidad ($mPa\cdot s$ / $cP$), Torque (%), Velocidad (RPM) y Rotor (#).
   * ⚖️ **Balanza de Precisión:** Extracción de peso con soporte multiunidad ($g$, $mg$, $kg$, $lb$, $oz$) y cronómetro continuo.

3. **Protección Total contra Cortes de Energía (Zero Data Loss):**
   * **Streaming CSV en tiempo real:** Cada fila leída se vuelca y sincroniza inmediatamente en disco físico (`flush` + `os.fsync`), garantizando que ninguna lectura se pierda si el computador se apaga o desconecta súbitamente.
   * **Checkpoints automáticos en Excel:** Guardado periódico programable (por defecto cada 20 minutos).

4. **Audio Sintetizado de Laboratorio (Web Audio API):**
   * Beep suave y profesional de confirmación de lectura válida (880 Hz / A5, 75 ms).
   * Alarma sonora discreta de doble tono ante lecturas dudosas o baja confianza.
   * 100% sintetizado en el navegador: cero dependencias de archivos de sonido externos.

5. **Auto-Tracking de Pantalla:**
   * Algoritmo de compensación automática de movimiento para grabaciones con temblor de pulso, vibraciones o desplazamientos de cámara.

6. **Notificaciones vía Discord Webhooks:**
   * Notificaciones enriquecidas (Embeds) enviadas a canales de laboratorio al iniciar, finalizar o si se detectan obstrucciones prolongadas en la pantalla.

7. **Personalización y Temas Visuales:**
   * 4 temas completos: **Oscuro Lab**, **Claro Bio**, **Cyber OLED** y **Ámbar Nocturno**.
   * Escalado dinámico de tipografía (Normal / Grande) y selector de densidad de tabla (Cómoda / Compacta).

---

## 📁 Estructura del Repositorio

```text
E:\reotaxis\
├── app.py                      # Backend principal y puente PyWebView <-> Python
├── ocr_engine.py               # Orquestador del motor de visión OCR
├── Launcher.cs                 # Código fuente del lanzador nativo C# WinExe
├── LabVision.exe               # Ejecutable nativo silencioso (con icono pixel art)
├── labvision.ico               # Icono oficial del matraz pixel art
├── fox.ico                     # Icono de autor (NachoFari)
├── Instalador_LabVision.bat    # Instalador automatizado en un clic
├── setup_installer.ps1         # Script PowerShell de aprovisionamiento
├── Iniciar_LabVision.bat       # Lanzador por lotes
├── Iniciar_LabVision.vbs       # Lanzador VBS silencioso
├── Crear_Acceso_Directo.bat    # Generador de acceso directo en el Escritorio
├── Verificar_Instalacion.bat   # Herramienta de autodiagnóstico del sistema
├── requirements.txt            # Dependencias pip del proyecto
├── README.md                   # Documentación principal
├── MANUAL_DE_LABORATORIO.md    # Guía operativa de campo
│
├── core/                       # Lógica interna y módulos de análisis
│   ├── hardware.py             # Detección de CPU vs GPU NVIDIA CUDA
│   ├── preprocessor.py         # Filtros adaptativos de imagen y contraste
│   ├── calibrator.py           # Herramientas de ajuste de display
│   └── parsers/                # Parsers específicos por equipo
│       ├── viscometer_parser.py
│       └── balance_parser.py
│
├── exporters/                  # Generadores de reportes
│   ├── csv_exporter.py         # Exportador y streaming CSV
│   └── excel_exporter.py       # Planillas Excel (.xlsx) con estilo de laboratorio
│
├── notifications/              # Canales de notificación externa
│   └── discord.py              # Integración con Discord Webhooks
│
├── config/                     # Persistencia de ajustes
│   └── manager.py              # Gestor seguro de configuración JSON
│
├── static/                     # Frontend moderno (Edge Chromium)
│   ├── index.html              # Interfaz y modales
│   ├── style.css               # Temas, densidades y diseño responsivo
│   ├── app.js                  # Controlador JavaScript y bindings
│   ├── lab_audio.js            # Motor de síntesis Web Audio API
│   ├── live_chart.js           # Motor de gráficos continuos en canvas
│   ├── lab_badge_256.png       # Badge oficial en alta resolución
│   ├── labvision.ico           # Icono web
│   └── fox_32.png              # Sello oficial NachoFari (Pixel art 32x32)
│
└── output/                     # Carpeta de destino de planillas y mediciones (.gitkeep)
```

---

## ⚡ Instalación y Puesta en Marcha

### Opción 1: Instalación Rápida Automática (Recomendada)
1. Haz doble clic en **`Instalador_LabVision.bat`**.
2. El script detectará tu versión de Python, creará el entorno virtual `.venv`, instalará las dependencias necesarias y creará el acceso directo en tu Escritorio.
3. Inicia la aplicación desde el acceso directo de **LabVision** en tu Escritorio.

### Opción 2: Instalación Manual
```powershell
# 1. Crear entorno virtual
python -m venv .venv
.\.venv\Scripts\activate

# 2. Instalar dependencias básicas
pip install -r requirements.txt

# 3. (Opcional) Aceleración por GPU NVIDIA CUDA 12.x
pip install torch torchvision --index-url https://download.pytorch.org/whl/cu121

# 4. Iniciar la aplicación
python app.py
```

---

## 🔬 Modo de Uso Rápido

1. Abre **LabVision**.
2. Selecciona tu instrumento: **Viscosímetro (NDJ-8S)** o **Balanza de Precisión**.
3. Carga un video (`.mp4`, `.avi`, `.mov`) o activa la **Cámara USB en Vivo**.
4. En el recuadro de **3. Encuadre de la Pantalla**, arrastra el cursor del ratón sobre los dígitos del display.
5. Pulsa **Probar Lectura** para confirmar la lectura inmediata y porcentaje de confianza.
6. Haz clic en **INICIAR EXTRACCIÓN**.
7. Al concluir la medición, abre tus resultados con los botones **CSV** o **Excel (.xlsx)**.

---

## 🦊 Autor

Creado con dedicación por **NachoFari**.
* GitHub: [github.com/NachoFari](https://github.com/NachoFari)

---

## 🔒 Derechos de Autor y Propiedad

© 2026 **NachoFari**. Todos los derechos reservados.  
Software propietario desarrollado para adquisición de datos científicos y automatización de laboratorio. Prohibida su copia, redistribución o uso comercial no autorizado sin el consentimiento expreso del autor.
