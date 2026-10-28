# 📘 MANUAL DE LABORATORIO Y PROTOCOLO DE OPERACIÓN (SOP)
## Sistema Automatizado de Adquisición Visual • LabVision
> **Desarrollado y Creado por [NachoFari (GitHub)](https://github.com/NachoFari)**  
> *Versión del Protocolo: 0.3 • Área de Instrumentación y Control*

---

## 1. OBJETIVO DEL SISTEMA
El presente protocolo estandariza la adquisición digital automatizada de datos experimentales a partir de video o transmisión en tiempo real de pantallas de instrumentos de laboratorio (Viscosímetros Rotacionales y Balanzas Analíticas o de Precisión), eliminando el error humano de transcripción manual y exportando tablas cronológicas en formato Excel (`.xlsx`) y CSV (`.csv`) con trazabilidad completa.

---

## 2. INSTRUMENTOS SOPORTADOS

| Instrumento | Modelo de Referencia | Variables Capturadas | Unidades |
| :--- | :--- | :--- | :--- |
| **Viscosímetro Rotacional** | NDJ-8S (y compatibles) | Rotor (#), Velocidad (RPM), Viscosidad, Torque (%) | $mPa\cdot s$ / $cP$, $\%$ |
| **Balanza de Precisión / Analítica** | Balanzas analíticas / digitales | Masa con decimales (+/-), Unidad de medida | $g$, $mg$, $kg$, $lb$, $oz$ |

---

## 3. GUÍA DE MONTAJE Y CONDICIONES ÓPTIMAS DE CÁMARA

Para garantizar lecturas continuas con una tasa de acierto del 100%, deben seguirse las siguientes recomendaciones de montaje:

1. **Ángulo contra Reflejos (Regla de los 5°-10°):**
   * Las pantallas de los instrumentos de laboratorio poseen cubiertas de acrílico o vidrio que reflejan intensamente las lámparas fluorescentes o LED del techo.
   * **Recomendación:** No ubicar la cámara perpendicular ($90^\circ$) exacta a la pantalla. Inclinarla entre $5^\circ$ y $10^\circ$ lateralmente o verticalmente para que el reflejo de la luz escape del lente.
2. **Distancia y Encuadre:**
   * La pantalla debe ocupar al menos el 25% del encuadre total del video para garantizar que cada dígito cuente con suficientes píxeles de resolución.
3. **Iluminación Ambiental:**
   * Evitar el uso del flash del celular o linternas directas (causan puntos ciegos blancos). Es preferible iluminación difusa ambiental.
4. **Cámara Estática vs Móvil:**
   * **Montaje ideal:** Trípode o pinza de soporte universal.
   * **Montaje con celular en mano:** Si la cámara se mueve o tiembla, activar la casilla **`Auto-Tracking de Pantalla`** en la aplicación para que el algoritmo rastree automáticamente el contorno del display cuadro a cuadro.

---

## 4. PERFILES DE POTENCIA Y RENDIMIENTO

El software se adapta al hardware del computador donde se esté utilizando:

| Perfil | Icono Pixel Art | Descripción y Uso Recomendado | Consumo de CPU |
| :--- | :---: | :--- | :--- |
| **Bajo** | [Batería] | **Notebooks antiguos, Celeron/i3 o trabajo con batería.** Escala la imagen a 360px y ejecuta una pasada rápida. Permite que el notebook no se caliente ni se ralentice (latencia de ~1.1s). | Muy Bajo |
| **Normal** | [Engranaje] | **Recomendado para la mayoría de los computadores.** Equilibrio ideal entre resolución (540px) y filtrado de ruido (~300ms en GPU). | Moderado |
| **Alto** | [Cohete] | **Workstations de laboratorio o PCs con tarjeta gráfica NVIDIA (CUDA).** Aplica doble resolución y realce local CLAHE para máxima precisión en displays degradados. | Alto / GPU |

---

## 5. MODOS DE VISTA (MENÚ VER)

La interfaz cuenta con un selector de vista superior para adaptarse a distintos tipos de pantalla:

1. **🖥️ Vista Completa (Setup / Calibración):** Modo predeterminado con panel de control a la izquierda y visor a la derecha.
2. **🔬 Vista Operador (Limpia):** Oculta los selectores de archivo y parámetros, dejando visible el video de la cámara y las tarjetas numéricas con la tabla expandida para un monitoreo despejado.
3. **📊 Vista Solo Datos (Máxima):** Oculta toda la columna izquierda y expande el dashboard al 100% de la pantalla (ideal para monitores de pared o pantallas secundarias).

---

## 6. PROCEDIMIENTO OPERATIVO ESTANDARIZADO (PASO A PASO)

### Paso 1: Inicialización
1. Conectar la cámara USB al computador (o tener listo el archivo de video descargado).
2. Hacer doble clic en el acceso directo de escritorio **`LabVision`** (o ejecutar `Iniciar_LabVision.bat`).
3. Comprobar que en la barra superior el indicador muestre el estado de aceleración de hardware.

### Paso 2: Selección de Instrumento y Origen
1. Seleccionar la pestaña **Viscosímetro (NDJ-8S)** o **Balanza de Precisión**.
2. Si es balanza, seleccionar la unidad de medida correspondiente ($g$, $mg$, etc.).
3. Elegir entre **Archivo de Video** o **Cámara en Vivo (USB)**.

### Paso 3: Encuadre y Calibración
1. Al cargar la imagen, se mostrará el fotograma en el lienzo central.
2. Con el botón izquierdo del mouse, arrastrar un recuadro rectangular cubriendo los números de la pantalla.
3. Hacer clic en **`Evaluar Cámara`**:
   * **Nitidez:** Informará si el foco es óptimo o si la imagen está borrosa.
   * **Reflejos:** Medirá el porcentaje de saturación de luz.
   * **Iluminación:** Confirmará si la exposición es correcta.
4. Hacer clic en **`Probar Lectura`** para verificar que el software interprete correctamente los valores antes de iniciar.

### Paso 4: Extracción y Monitoreo en Vivo
1. Definir la frecuencia de muestreo (por defecto: *Cada 1.0 segundo*).
2. Si la toma fue grabada a pulso con el teléfono, marcar **`Auto-Tracking de Pantalla`**.
3. Presionar **`INICIAR EXTRACCIÓN`**.
4. Observar las tarjetas de métricas en tiempo real y la tabla cronológica que se va completando.

### Paso 5: Alertas de Calidad durante el Ensayo
Si durante el ensayo la pantalla se obstruye (ej: paso de la mano del operador) o un dígito pierde nitidez, se activará el banner rojo:
* `AVISO DE CALIDAD: Lectura dudosa o datos incompletos detectados.`
* El software continuará registrando pero marcará esa fila con la etiqueta `DUDOSA` en el reporte final para permitir su posterior filtrado o auditoría.

### Paso 6: Exportación de Resultados
Al finalizar la extracción:
1. Hacer clic en **`Excel (.xlsx)`** para abrir directamente la planilla formateada con diseño corporativo, columnas numéricas y cabecera institucional.
2. O hacer clic en **`CSV`** para obtener el archivo de texto plano delimitado por comas, listo para importar en software estadístico (R, MATLAB, Python, Origin).

---

## 7. INTEGRACIÓN CON DISCORD (ALERTAS Y BITÁCORA REMOTA)

Para que el personal de laboratorio reciba notificaciones en su teléfono o canal de trabajo:
1. En Discord, ir a *Ajustes de Canal > Integraciones > Crear Webhook* y copiar la URL.
2. En LabVision, presionar el botón **`Discord`** en la barra superior.
3. Pegar la URL y hacer clic en **`Enviar Mensaje de Prueba`**.
4. Guardar. A partir de ese momento, cada inicio de ensayo, alerta de obstrucción y resumen de finalización se publicará automáticamente en el canal de Discord.

---
*Documento oficial de laboratorio emitido para el proyecto Reotaxis • **[NachoFari](https://github.com/NachoFari)**.*
