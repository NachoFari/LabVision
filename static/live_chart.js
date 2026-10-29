/**
 * LabVision Pro - live_chart.js
 * Módulo de Gráficos Interactivos en Tiempo Real para Laboratorio
 * 
 * Características:
 * - Soporte dual: Utiliza Chart.js si está presente o motor Canvas 2D nativo ultraliviano si no hay internet (offline).
 * - Tema oscuro de laboratorio con colores cian neón (#38bdf8) para viscosidad y verde esmeralda (#34d399) para balanza.
 * - Ventana deslizante (últimos 60 puntos) con animación fluida y sin saltos bruscos.
 * - Detección y resaltado visual con marcadores rojos brillantes en lecturas dudosas (isBad).
 * - Exportación de capturas en alta resolución a PNG con fondo sólido e intento de copiado directo al portapapeles.
 * - Soporte nativo para pantallas High-DPI (Retina) en Edge Chromium / PyWebView.
 * 
 * Creado por NachoFari para LabVision Pro
 */

(function (root, factory) {
  if (typeof define === 'function' && define.amd) {
    define([], factory);
  } else if (typeof module === 'object' && module.exports) {
    module.exports = factory();
  } else {
    const exports = factory();
    root.LiveChart = exports;
    // Exponer funciones globales requeridas
    root.initLiveChart = exports.initLiveChart;
    root.updateLiveChart = exports.updateLiveChart;
    root.exportChartImage = exports.exportChartImage;
    root.resetChart = exports.resetChart;
    root.switchChartMode = exports.switchChartMode;
    root.setChartSeries = exports.setChartSeries;
    root.setChartFillType = exports.setChartFillType;
  }
})(typeof window !== 'undefined' ? window : this, function () {
  'use strict';

  // ================= CONFIGURACIÓN Y PALETAS =================
  const MAX_POINTS = 60; // Ventana deslizante de puntos visibles

  const THEMES = {
    viscometer: {
      id: 'viscometer',
      label: 'Viscosidad',
      unit: 'mPa·s',
      colorLine: '#38bdf8',       // Cian neón
      colorLineGlow: 'rgba(56, 189, 248, 0.45)',
      colorGradientTop: 'rgba(56, 189, 248, 0.35)',
      colorGradientBottom: 'rgba(56, 189, 248, 0.00)',
      colorPoint: '#38bdf8',
      colorBadge: '#0284c7'
    },
    balance: {
      id: 'balance',
      label: 'Peso de Balanza',
      unit: 'g',
      colorLine: '#34d399',       // Verde esmeralda
      colorLineGlow: 'rgba(52, 211, 153, 0.45)',
      colorGradientTop: 'rgba(52, 211, 153, 0.35)',
      colorGradientBottom: 'rgba(52, 211, 153, 0.00)',
      colorPoint: '#34d399',
      colorBadge: '#059669'
    },
    alert: {
      colorBad: '#ef4444',        // Rojo brillante para lecturas dudosas
      colorBadGlow: 'rgba(239, 68, 68, 0.65)',
      colorBadFill: '#f87171'
    },
    lab: {
      bgDark: '#0B0F19',
      bgCard: '#131B2E',
      borderColor: '#1F293D',
      gridLines: 'rgba(255, 255, 255, 0.06)',
      textMuted: '#94a3b8',
      textMain: '#f8fafc'
    }
  };

  // Estado del módulo
  let currentMode = 'viscometer'; // 'viscometer' | 'balance'
  let targetContainer = null;
  let canvasElement = null;
  let chartJsInstance = null;
  let useNativeEngine = false;
  let resizeObserver = null;

  // Almacenamiento de puntos: [{ timeSec, value, isBad, label }]
  let dataPoints = [];

  // ================= INICIALIZACIÓN =================

  /**
   * Resuelve el elemento contenedor y asegura un <canvas> preparado
   */
  function resolveCanvas(containerId) {
    let container = null;
    if (typeof containerId === 'string') {
      container = document.getElementById(containerId);
    } else if (containerId && containerId.nodeType) {
      container = containerId;
    }

    if (!container) {
      console.warn(`[LiveChart] Contenedor '${containerId}' no encontrado en el DOM.`);
      return null;
    }

    targetContainer = container;

    if (container.tagName.toLowerCase() === 'canvas') {
      canvasElement = container;
    } else {
      let canvas = container.querySelector('canvas');
      if (!canvas) {
        canvas = document.createElement('canvas');
        canvas.id = (container.id || 'chart-container') + '-canvas';
        canvas.style.width = '100%';
        canvas.style.height = '100%';
        canvas.style.display = 'block';
        container.innerHTML = '';
        container.appendChild(canvas);
      }
      canvasElement = canvas;
    }

    // Configurar High-DPI para el canvas nativo
    adjustCanvasDPI(canvasElement);

    return canvasElement;
  }

  /**
   * Ajusta la resolución del canvas físico al devicePixelRatio del sistema
   * Evita que el gráfico se vea borroso en laptops con escalado al 125% o 150%
   */
  function adjustCanvasDPI(canvas) {
    if (!canvas) return;
    const dpr = window.devicePixelRatio || 1;
    const rect = canvas.getBoundingClientRect();
    const parentW = (targetContainer ? targetContainer.clientWidth : 0) || (canvas.parentElement ? canvas.parentElement.clientWidth : 0) || 1000;
    const parentH = (targetContainer ? targetContainer.clientHeight : 0) || (canvas.parentElement ? canvas.parentElement.clientHeight : 0) || 450;
    const width = Math.max(rect.width, parentW, 300);
    const height = Math.max(rect.height, parentH, 150);

    canvas.width = Math.round(width * dpr);
    canvas.height = Math.round(height * dpr);

    const ctx = canvas.getContext('2d');
    if (ctx && !chartJsInstance) {
      ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
    }
  }

  /**
   * Inicializa el módulo de gráficos en tiempo real
   * @param {string|HTMLElement} containerId - ID del contenedor o canvas
   * @param {string} mode - 'viscometer' o 'balance'
   */
  function initLiveChart(containerId, mode = 'viscometer') {
    currentMode = (mode === 'balance') ? 'balance' : 'viscometer';
    const canvas = resolveCanvas(containerId);
    if (!canvas) return false;

    // Detectar si Chart.js está disponible globalmente
    const hasChartJs = typeof window.Chart !== 'undefined';
    useNativeEngine = !hasChartJs;

    if (hasChartJs) {
      setupChartJs(canvas);
    } else {
      setupNativeCanvas(canvas);
    }

    // Observar redimensionamiento del contenedor para reescalado suave
    if (window.ResizeObserver && targetContainer) {
      if (resizeObserver) resizeObserver.disconnect();
      resizeObserver = new ResizeObserver(() => {
        if (useNativeEngine) {
          adjustCanvasDPI(canvasElement);
          renderNativeChart();
        } else if (chartJsInstance) {
          chartJsInstance.resize();
        }
      });
      resizeObserver.observe(targetContainer);
    }

    return true;
  }

  // ================= MODO A: MOTOR CHART.JS =================

  function setupChartJs(canvas) {
    if (chartJsInstance) {
      chartJsInstance.destroy();
      chartJsInstance = null;
    }

    const theme = THEMES[currentMode];
    const ctx = canvas.getContext('2d');

    // Gradiente translúcido dinámico
    const getGradient = (context) => {
      const chartArea = context.chart.chartArea;
      if (!chartArea) return null;
      const gradient = context.chart.ctx.createLinearGradient(0, chartArea.top, 0, chartArea.bottom);
      gradient.addColorStop(0, theme.colorGradientTop);
      gradient.addColorStop(1, theme.colorGradientBottom);
      return gradient;
    };

    chartJsInstance = new window.Chart(ctx, {
      type: 'line',
      data: {
        labels: [],
        datasets: [{
          label: `${theme.label} (${theme.unit})`,
          data: [],
          borderColor: theme.colorLine,
          borderWidth: 2.2,
          backgroundColor: getGradient,
          fill: true,
          tension: 0.28, // Curvatura spline suave
          pointRadius: (ctx) => {
            const index = ctx.dataIndex;
            const pt = dataPoints[index];
            return pt && pt.isBad ? 6 : 3;
          },
          pointHoverRadius: 6,
          pointBackgroundColor: (ctx) => {
            const index = ctx.dataIndex;
            const pt = dataPoints[index];
            return pt && pt.isBad ? THEMES.alert.colorBad : theme.colorPoint;
          },
          pointBorderColor: (ctx) => {
            const index = ctx.dataIndex;
            const pt = dataPoints[index];
            return pt && pt.isBad ? '#ffffff' : theme.colorLine;
          },
          pointBorderWidth: (ctx) => {
            const index = ctx.dataIndex;
            const pt = dataPoints[index];
            return pt && pt.isBad ? 2 : 1;
          }
        }]
      },
      options: {
        responsive: true,
        maintainAspectRatio: false,
        animation: {
          duration: 200,
          easing: 'easeOutQuad'
        },
        interaction: {
          mode: 'index',
          intersect: false
        },
        plugins: {
          legend: {
            display: true,
            labels: {
              color: THEMES.lab.textMain,
              font: {
                family: 'system-ui, -apple-system, sans-serif',
                size: 11,
                weight: '600'
              },
              boxWidth: 12,
              padding: 10
            }
          },
          tooltip: {
            backgroundColor: 'rgba(11, 15, 25, 0.95)',
            titleColor: THEMES.lab.textMain,
            bodyColor: THEMES.lab.textMuted,
            borderColor: THEMES.lab.borderColor,
            borderWidth: 1,
            padding: 8,
            boxPadding: 4,
            callbacks: {
              label: (context) => {
                const pt = dataPoints[context.dataIndex];
                const badTag = pt && pt.isBad ? ' [DUDOSA]' : '';
                return ` ${context.parsed.y} ${theme.unit}${badTag}`;
              }
            }
          }
        },
        scales: {
          x: {
            grid: {
              color: THEMES.lab.gridLines,
              drawBorder: false
            },
            ticks: {
              color: THEMES.lab.textMuted,
              font: { family: 'monospace', size: 10 },
              maxRotation: 0,
              autoSkip: true,
              maxTicksLimit: 10
            }
          },
          y: {
            grid: {
              color: THEMES.lab.gridLines,
              drawBorder: false
            },
            ticks: {
              color: THEMES.lab.textMuted,
              font: { family: 'monospace', size: 10 }
            },
            suggestedMin: 0
          }
        }
      }
    });
  }

  // ================= MODO B: MOTOR CANVAS 2D NATIVO =================
  // Se activa automáticamente si Chart.js no está disponible (ej: sin conexión en laboratorio)

  function setupNativeCanvas(canvas) {
    adjustCanvasDPI(canvas);
    renderNativeChart();
  }

  /**
   * Renderizador completo de alto rendimiento para el tema oscuro de laboratorio
   */
  function renderNativeChart() {
    if (!canvasElement) return;
    const ctx = canvasElement.getContext('2d');
    if (!ctx) return;

    const dpr = window.devicePixelRatio || 1;
    const rect = canvasElement.getBoundingClientRect();
    const w = Math.max(rect.width, (targetContainer ? targetContainer.clientWidth : 0) || 1000);
    const h = Math.max(rect.height, (targetContainer ? targetContainer.clientHeight : 0) || 450);

    ctx.save();
    ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
    ctx.clearRect(0, 0, w, h);

    const theme = THEMES[currentMode];
    const padL = 50;
    const padR = 25;
    const padT = 30;
    const padB = 30;
    const plotW = w - padL - padR;
    const plotH = h - padT - padB;

    // Fondo del gráfico de laboratorio
    ctx.fillStyle = THEMES.lab.bgDark;
    ctx.fillRect(0, 0, w, h);

    // Si no hay datos, mostrar rejilla vacía con mensaje de espera
    if (dataPoints.length === 0) {
      drawLabGrid(ctx, padL, padT, plotW, plotH, 0, 100, 5);
      ctx.fillStyle = THEMES.lab.textMuted;
      ctx.font = '12px system-ui, sans-serif';
      ctx.textAlign = 'center';
      ctx.fillText(`Esperando lecturas de ${theme.label}...`, padL + plotW / 2, padT + plotH / 2);
      ctx.restore();
      return;
    }

    // Calcular límites Y dinámicos con holgura
    let minY = Infinity;
    let maxY = -Infinity;
    dataPoints.forEach(p => {
      if (p.value < minY) minY = p.value;
      if (p.value > maxY) maxY = p.value;
    });

    if (minY === Infinity) { minY = 0; maxY = 100; }
    if (minY === maxY) { minY = Math.max(0, minY - 10); maxY = maxY + 10; }
    const spanY = maxY - minY;
    minY = Math.max(0, minY - spanY * 0.1);
    maxY = maxY + spanY * 0.1;

    // Dibujar rejilla y ejes
    drawLabGrid(ctx, padL, padT, plotW, plotH, minY, maxY, 5);

    // Mapear coordenadas de pantalla
    const coords = dataPoints.map((pt, i) => {
      const x = (dataPoints.length === 1)
        ? padL + plotW / 2
        : padL + (i / (dataPoints.length - 1)) * plotW;
      const normalizedY = (pt.value - minY) / (maxY - minY || 1);
      const y = padT + plotH - (normalizedY * plotH);
      return { x, y, pt };
    });

    // 1. Área con gradiente translúcido
    if (coords.length > 1) {
      const grad = ctx.createLinearGradient(0, padT, 0, padT + plotH);
      grad.addColorStop(0, theme.colorGradientTop);
      grad.addColorStop(1, theme.colorGradientBottom);

      ctx.beginPath();
      ctx.moveTo(coords[0].x, padT + plotH);
      ctx.lineTo(coords[0].x, coords[0].y);
      for (let i = 1; i < coords.length; i++) {
        // Suavizado cuadrático entre puntos
        const xc = (coords[i].x + coords[i - 1].x) / 2;
        const yc = (coords[i].y + coords[i - 1].y) / 2;
        ctx.quadraticCurveTo(coords[i - 1].x, coords[i - 1].y, xc, yc);
      }
      ctx.lineTo(coords[coords.length - 1].x, coords[coords.length - 1].y);
      ctx.lineTo(coords[coords.length - 1].x, padT + plotH);
      ctx.closePath();
      ctx.fillStyle = grad;
      ctx.fill();
    }

    // 2. Línea principal neón con brillo
    ctx.save();
    ctx.beginPath();
    ctx.moveTo(coords[0].x, coords[0].y);
    for (let i = 1; i < coords.length; i++) {
      const xc = (coords[i].x + coords[i - 1].x) / 2;
      const yc = (coords[i].y + coords[i - 1].y) / 2;
      ctx.quadraticCurveTo(coords[i - 1].x, coords[i - 1].y, xc, yc);
    }
    if (coords.length > 1) {
      ctx.lineTo(coords[coords.length - 1].x, coords[coords.length - 1].y);
    }
    ctx.strokeStyle = theme.colorLine;
    ctx.lineWidth = 2.2;
    ctx.shadowColor = theme.colorLineGlow;
    ctx.shadowBlur = 8;
    ctx.stroke();
    ctx.restore();

    // 3. Puntos de lectura (resaltando dudosas en rojo)
    coords.forEach(({ x, y, pt }) => {
      if (pt.isBad) {
        // Halo de advertencia rojo
        ctx.beginPath();
        ctx.arc(x, y, 7, 0, Math.PI * 2);
        ctx.fillStyle = THEMES.alert.colorBadGlow;
        ctx.fill();

        // Punto rojo central
        ctx.beginPath();
        ctx.arc(x, y, 4, 0, Math.PI * 2);
        ctx.fillStyle = THEMES.alert.colorBad;
        ctx.fill();
        ctx.strokeStyle = '#ffffff';
        ctx.lineWidth = 1.5;
        ctx.stroke();
      } else {
        // Punto estándar
        ctx.beginPath();
        ctx.arc(x, y, 2.5, 0, Math.PI * 2);
        ctx.fillStyle = theme.colorPoint;
        ctx.fill();
      }
    });

    // 4. HUD / Encabezado de información en vivo en la esquina superior
    drawLabHeader(ctx, padL, 18, theme, dataPoints[dataPoints.length - 1]);

    ctx.restore();
  }

  function drawLabGrid(ctx, x, y, w, h, minY, maxY, ticksY = 5) {
    ctx.strokeStyle = THEMES.lab.borderColor;
    ctx.lineWidth = 1;
    ctx.strokeRect(x, y, w, h);

    ctx.font = '10px monospace';
    ctx.fillStyle = THEMES.lab.textMuted;
    ctx.textAlign = 'right';
    ctx.textBaseline = 'middle';

    // Líneas horizontales de valor
    for (let i = 0; i <= ticksY; i++) {
      const frac = i / ticksY;
      const val = maxY - (frac * (maxY - minY));
      const lineY = y + (frac * h);

      ctx.beginPath();
      ctx.strokeStyle = THEMES.lab.gridLines;
      ctx.moveTo(x, lineY);
      ctx.lineTo(x + w, lineY);
      ctx.stroke();

      ctx.fillText(val.toFixed(1), x - 6, lineY);
    }

    // Líneas verticales de tiempo
    if (dataPoints.length > 0) {
      ctx.textAlign = 'center';
      ctx.textBaseline = 'top';
      const step = Math.max(1, Math.floor(dataPoints.length / 5));
      for (let i = 0; i < dataPoints.length; i += step) {
        const lineX = (dataPoints.length === 1)
          ? x + w / 2
          : x + (i / (dataPoints.length - 1)) * w;

        ctx.beginPath();
        ctx.strokeStyle = THEMES.lab.gridLines;
        ctx.moveTo(lineX, y);
        ctx.lineTo(lineX, y + h);
        ctx.stroke();

        const pt = dataPoints[i];
        const label = pt.label || `${pt.timeSec}s`;
        ctx.fillText(label, lineX, y + h + 6);
      }
    }
  }

  function drawLabHeader(ctx, x, y, theme, lastPoint) {
    ctx.font = 'bold 11px system-ui, sans-serif';
    ctx.fillStyle = theme.colorLine;
    ctx.textAlign = 'left';
    ctx.fillText(`${theme.label.toUpperCase()}`, x, y);

    if (lastPoint) {
      ctx.font = '11px monospace';
      ctx.fillStyle = THEMES.lab.textMain;
      const txt = `: ${lastPoint.value} ${theme.unit}`;
      ctx.fillText(txt, x + ctx.measureText(`${theme.label.toUpperCase()}`).width + 4, y);

      if (lastPoint.isBad) {
        ctx.fillStyle = THEMES.alert.colorBad;
        ctx.font = 'bold 10px system-ui, sans-serif';
        ctx.fillText('  [LIVELOG: CALIDAD DUDOSA]', x + 200, y);
      }
    }
  }

  // ================= ACTUALIZACIÓN EN TIEMPO REAL =================

  /**
   * Agrega un nuevo punto al gráfico con animación fluida y ventana deslizante
   * @param {number|string} timeSec - Tiempo en segundos o marca temporal
   * @param {number} value - Valor numérico leído
   * @param {boolean} isBad - True si la lectura tiene baja confianza o es dudosa
   */
  function updateLiveChart(timeSec, value, isBad = false) {
    const numVal = parseFloat(value);
    if (isNaN(numVal)) return;

    const numericTime = typeof timeSec === 'number' ? timeSec : parseFloat(timeSec) || 0;
    const label = `${Math.round(numericTime)}s`;

    // Empujar punto nuevo
    dataPoints.push({
      timeSec: numericTime,
      label: label,
      value: numVal,
      isBad: Boolean(isBad)
    });

    // Mantener ventana fija de últimos 60 puntos
    if (dataPoints.length > MAX_POINTS) {
      dataPoints.shift();
    }

    // Actualizar motor correspondiente
    if (useNativeEngine || !chartJsInstance) {
      renderNativeChart();
    } else {
      const theme = THEMES[currentMode];
      const dataset = chartJsInstance.data.datasets[0];
      dataset.label = `${theme.label} (${theme.unit})`;

      chartJsInstance.data.labels = dataPoints.map(p => p.label);
      dataset.data = dataPoints.map(p => p.value);

      // Actualizar Chart.js con animación fluida sin bloquear el hilo principal
      chartJsInstance.update('none');
    }
  }

  /**
   * Cambia dinámicamente entre modo Viscosímetro y Balanza
   * @param {string} newMode - 'viscometer' | 'balance'
   */
  function switchChartMode(newMode) {
    currentMode = (newMode === 'balance') ? 'balance' : 'viscometer';
    const theme = THEMES[currentMode];

    if (chartJsInstance) {
      const dataset = chartJsInstance.data.datasets[0];
      dataset.label = `${theme.label} (${theme.unit})`;
      dataset.borderColor = theme.colorLine;
      chartJsInstance.update();
    } else if (useNativeEngine) {
      renderNativeChart();
    }
  }

  // ================= LIMPIEZA / RESET =================

  /**
   * Limpia todos los puntos acumulados y restablece el gráfico
   */
  function resetChart() {
    dataPoints = [];

    if (chartJsInstance) {
      chartJsInstance.data.labels = [];
      chartJsInstance.data.datasets[0].data = [];
      chartJsInstance.update();
    } else if (useNativeEngine) {
      renderNativeChart();
    }
  }

  // ================= EXPORTACIÓN A IMAGEN PNG =================

  /**
   * Exporta el gráfico actual como imagen PNG con fondo oscuro de laboratorio.
   * Descarga el archivo automáticamente e intenta copiarlo al portapapeles.
   * @param {string} [filename] - Nombre del archivo de salida
   * @returns {string|null} DataURL de la imagen generada
   */
  function exportChartImage(filename) {
    if (!canvasElement) {
      console.warn('[LiveChart] No hay canvas disponible para exportar.');
      return null;
    }

    try {
      const theme = THEMES[currentMode];
      const timeStamp = new Date().toISOString().replace(/[:.]/g, '-').slice(0, 19);
      const defaultFilename = `LabVision_${theme.id}_${timeStamp}.png`;
      const exportName = filename || defaultFilename;

      // Crear canvas fuera de pantalla con fondo lab sólido para que no sea transparente
      const offscreen = document.createElement('canvas');
      offscreen.width = canvasElement.width || 800;
      offscreen.height = canvasElement.height || 400;
      const offCtx = offscreen.getContext('2d');

      // 1. Fondo sólido de laboratorio
      offCtx.fillStyle = THEMES.lab.bgDark;
      offCtx.fillRect(0, 0, offscreen.width, offscreen.height);

      // 2. Dibujar el contenido del gráfico
      offCtx.drawImage(canvasElement, 0, 0);

      // 3. Marca de agua y membrete en esquina inferior derecha
      offCtx.font = '10px system-ui, sans-serif';
      offCtx.fillStyle = 'rgba(255, 255, 255, 0.45)';
      offCtx.textAlign = 'right';
      offCtx.fillText('LabVision Pro • Creado por NachoFari', offscreen.width - 15, offscreen.height - 10);

      const dataUrl = offscreen.toDataURL('image/png');

      // Descarga automática en navegador / PyWebView
      const link = document.createElement('a');
      link.download = exportName;
      link.href = dataUrl;
      document.body.appendChild(link);
      link.click();
      document.body.removeChild(link);

      // Intentar copiar al portapapeles si la API está disponible
      if (navigator.clipboard && window.ClipboardItem && offscreen.toBlob) {
        offscreen.toBlob((blob) => {
          if (blob) {
            try {
              navigator.clipboard.write([
                new window.ClipboardItem({ 'image/png': blob })
              ]).then(() => {
                console.log('[LiveChart] Gráfico copiado al portapapeles del sistema.');
              }).catch(() => {});
            } catch (e) {}
          }
        });
      }

      return dataUrl;
    } catch (err) {
      console.error('[LiveChart] Error exportando imagen del gráfico:', err);
      return null;
    }
  }

  // ================= API PÚBLICA =================
  return {
    initLiveChart,
    updateLiveChart,
    exportChartImage,
    resetChart,
    switchChartMode,
    getDataPoints: () => [...dataPoints]
  };
});
