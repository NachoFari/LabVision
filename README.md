<div align="center">

<img src="static/lab_badge_256.png" alt="LabVision Logo" width="115" />

# 🧪 LabVision

**Digitalización inteligente y adquisición de datos en tiempo real desde pantallas de laboratorio a Excel y CSV.**

[![Version](https://img.shields.io/badge/version-v0.8-cyan.svg)](https://github.com/NachoFari/LabVision)
[![Python](https://img.shields.io/badge/python-3.10%20%7C%203.11%20%7C%203.12-blue.svg)](https://www.python.org/)
[![GUI](https://img.shields.io/badge/gui-PyWebView%20%2B%20Edge%20Chromium-teal.svg)](https://pywebview.flowrl.com/)
[![OCR Engine](https://img.shields.io/badge/ocr-OpenCV%20%2B%20EasyOCR%20%2B%20PyTorch-emerald.svg)](https://github.com/JaidedAI/EasyOCR)
[![OS](https://img.shields.io/badge/os-Windows%2010%20%2F%2011-0078D6.svg)](https://www.microsoft.com/windows)

*Adquisición científica automatizada, protección total contra cortes de energía y streaming continuo.*

</div>

---

## 📌 Descripción

**LabVision** es un software de escritorio para Windows diseñado para laboratorios científicos e industriales. Permite extraer de manera automática y en tiempo real las lecturas numéricas mostradas en las pantallas de instrumentos analíticos (como el **Viscosímetro Rotacional NDJ-8S** o **Balanzas Digitales de Precisión**), ya sea directamente desde una cámara USB/webcam o a partir de archivos de video grabados (`.mp4`, `.avi`, `.mov`).

Los datos leídos se procesan mediante visión por computadora (OpenCV y PyTorch/EasyOCR), se validan con filtros de confianza estadística y se transmiten directamente a disco en streaming continuo (CSV y Excel `.xlsx`) con protección total ante cortes de energía.

---

## ⚡ Instalación y Puesta en Marcha

### Opción 1: Instalación Rápida Automática (Recomendada)
1. Haz doble clic en **`Instalador_LabVision.bat`**.
2. El asistente detectará tu versión de Python, creará el entorno virtual `.venv`, instalará todas las dependencias necesarias y generará un acceso directo en tu Escritorio.
3. Inicia la aplicación directamente desde el acceso directo de **LabVision**.

### Opción 2: Instalación Manual
```powershell
# 1. Clonar el repositorio
git clone https://github.com/NachoFari/LabVision.git
cd LabVision

# 2. Crear y activar entorno virtual
python -m venv .venv
.\.venv\Scripts\activate

# 3. Instalar dependencias
pip install -r requirements.txt

# 4. (Opcional) Aceleración por GPU NVIDIA CUDA 12.x
pip install torch torchvision --index-url https://download.pytorch.org/whl/cu121

# 5. Iniciar la aplicación
python app.py
```

---

## 🚀 Funcionalidades Principales

- **4 Pantallas y Modos de Trabajo:**
  - 🖥️ **Captura en Vivo:** Dashboard central con visor interactivo de encuadre (ROI), tarjetas de parámetros y tabla en tiempo real acotada al píxel.
  - 📈 **Gráficos en Vivo:** Visualización continua de tendencias con HUD de estadísticas dinámicas (Mínimo, Máximo, Promedio, Último valor) y exportación a PNG.
  - 🗄️ **Base de Datos:** Historial tabular completo con filtros rápidos por nivel de confianza y exportación directa.
  - ⚙️ **Calibración:** Visor de diagnóstico para ajustar contraste, binarización y preprocesamiento de imagen.

- **Instrumentos Soportados:**
  - 🧪 **Viscosímetro Digital (NDJ-8S):** Lectura sincronizada de Viscosidad ($mPa\cdot s$ / $cP$), Torque (%), Velocidad (RPM) y Rotor (#).
  - ⚖️ **Balanza de Precisión:** Extracción de peso con soporte multiunidad ($g$, $mg$, $kg$, $lb$, $oz$) y cronómetro continuo.

- **Protección Total contra Cortes de Energía (Zero Data Loss):**
  - **Streaming CSV en tiempo real:** Cada fila leída se sincroniza inmediatamente en disco físico (`flush` + `os.fsync`), evitando pérdidas ante fallos de energía.
  - **Checkpoints periódicos en Excel:** Guardado programable automático (por defecto cada 20 minutos).

- **Audio Sintetizado de Laboratorio (Web Audio API):**
  - Beep profesional de confirmación de lectura válida (880 Hz / A5).
  - Alarma sonora discreta de doble tono ante lecturas dudosas o baja confianza.
  - 100% sintetizado en el navegador: cero dependencias de archivos de audio externos.

- **Auto-Tracking de Pantalla:**
  - Algoritmo de compensación de movimiento ante vibraciones, pulso o desplazamientos de cámara.

- **Notificaciones vía Discord Webhooks:**
  - Envío automático de Embeds con reportes al iniciar, finalizar o si se detecta obstrucción del display.

- **Personalización y Temas Visuales:**
  - 4 temas: **Oscuro Lab**, **Claro Bio**, **Cyber OLED** y **Ámbar Nocturno**.
  - Escalado dinámico de tipografía y selector de densidad de tabla (Cómoda / Compacta).

---

## 🔬 Modo de Uso Rápido

1. Abre **LabVision**.
2. Selecciona tu instrumento: **Viscosímetro (NDJ-8S)** o **Balanza de Precisión**.
3. Carga un archivo de video (`.mp4`, `.avi`, `.mov`) o activa la **Cámara USB en Vivo**.
4. En **3. Encuadre de la Pantalla**, arrastra el ratón sobre los dígitos del display.
5. Pulsa **Probar Lectura** para verificar el reconocimiento y porcentaje de confianza.
6. Haz clic en **INICIAR EXTRACCIÓN**.
7. Al concluir la medición, accede a tus datos generados mediante los accesos directos de **CSV** o **Excel (.xlsx)**.

---

## 📁 Estructura del Repositorio

```text
LabVision/
├── app.py                      # Backend principal y puente PyWebView <-> Python
├── ocr_engine.py               # Orquestador del motor de visión OCR
├── Launcher.cs                 # Código fuente del lanzador nativo C# WinExe
├── LabVision.exe               # Ejecutable nativo silencioso
├── labvision.ico               # Icono oficial del matraz pixel art
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
│   └── excel_exporter.py       # Planillas Excel (.xlsx) con formato de laboratorio
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
│   └── lab_badge_256.png       # Badge oficial en alta resolución
│
└── output/                     # Carpeta de destino de planillas y mediciones (.gitkeep)
```

---

<div align="center">
Desarrollado con ❤️ por <b>NachoFari</b> — <b>NaTex Studio</b> 🦊
</div>
