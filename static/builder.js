// =========================================================
// LabVision • Constructor Visual de Plantillas (No-Code Sub-ROIs)
// Work Package 5 - Roadmap Universal
// Creado por NachoFari
// =========================================================

(function() {
  'use strict';

  // Paleta de colores industriales de alto contraste para variables de laboratorio
  const LAB_PALETTE = [
    '#38bdf8', // Cian / Viscosidad / Primario
    '#34d399', // Esmeralda / Balanza
    '#f59e0b', // Ámbar / Temperatura
    '#f43f5e', // Rosa / Advertencia
    '#a78bfa', // Violeta / Conductividad
    '#fb923c', // Naranja / Presión
    '#2dd4bf', // Turquesa
    '#818cf8', // Índigo
    '#e879f9', // Fucsia
    '#4ade80'  // Lima
  ];

  class TemplateBuilder {
    constructor() {
      this.modal = null;
      this.canvas = null;
      this.ctx = null;
      this.container = null;

      // Estado de la plantilla en edición
      this.currentTemplate = {
        id: '',
        name: 'Nueva Plantilla Personalizada',
        description: 'Plantilla de digitalización creada con el Constructor No-Code',
        author: 'Operador de Laboratorio',
        displayType: 'lcd_reflective',
        subRois: []
      };

      // Imagen de referencia
      this.refImage = null;
      this.refImageBase64 = null;
      this.imgNaturalWidth = 1280;
      this.imgNaturalHeight = 720;

      // Estado de interacción de Canvas
      this.isDrawing = false;
      this.isDragging = false;
      this.isResizing = false;
      this.activeHandle = null; // 'nw', 'ne', 'se', 'sw'
      this.selectedRoiId = null;
      this.hoveredRoiId = null;
      this.dragStart = { x: 0, y: 0 };
      this.tempBox = null; // { x, y, w, h } en pixeles del canvas

      // Herramientas visuales
      this.zoomLevel = 1.0;
      this.showGrid = true;
      this.isTestingOcr = false;

      // Inicialización diferida del DOM
      if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', () => this.initDom());
      } else {
        this.initDom();
      }
    }

    initDom() {
      this.modal = document.getElementById('templateBuilderModal');
      this.canvas = document.getElementById('builder-canvas');
      this.ctx = this.canvas ? this.canvas.getContext('2d') : null;
      this.container = document.getElementById('builder-canvas-container');

      if (!this.canvas) return;

      this.bindEvents();
      this.loadCustomTemplatesFromStorage();
    }

    bindEvents() {
      // Eventos del Canvas
      this.canvas.addEventListener('mousedown', (e) => this.onMouseDown(e));
      window.addEventListener('mousemove', (e) => this.onMouseMove(e));
      window.addEventListener('mouseup', (e) => this.onMouseUp(e));

      // Input de archivo local para imagen de referencia
      const fileInput = document.getElementById('builder-file-input');
      if (fileInput) {
        fileInput.addEventListener('change', (e) => this.handleLocalImageUpload(e));
      }

      // Input de archivo para importar .lvtemplate
      const importInput = document.getElementById('builder-import-input');
      if (importInput) {
        importInput.addEventListener('change', (e) => this.handleTemplateFileImport(e));
      }

      // Tecla Escape para cerrar o cancelar
      window.addEventListener('keydown', (e) => {
        if (!this.modal || this.modal.classList.contains('hidden')) return;
        if (e.key === 'Escape') {
          if (this.selectedRoiId) {
            this.selectedRoiId = null;
            this.render();
          } else {
            this.closeModal();
          }
        } else if (e.key === 'Delete' || e.key === 'Backspace') {
          // Si el foco no está en un input y hay un ROI seleccionado, borrarlo
          if (this.selectedRoiId && !['INPUT', 'SELECT', 'TEXTAREA'].includes(document.activeElement?.tagName)) {
            this.deleteSubRoi(this.selectedRoiId);
          }
        }
      });
    }

    // ================= GESTIÓN DEL MODAL =================

    openModal(options = {}) {
      if (!this.modal) this.initDom();
      if (!this.modal) return;

      this.modal.classList.remove('hidden');

      // Si nos pasaron una plantilla para editar
      if (options.template) {
        this.currentTemplate = JSON.parse(JSON.stringify(options.template));
      } else {
        this.resetTemplate();
      }

      // Actualizar campos de metadatos en el encabezado
      const nameInput = document.getElementById('builder-tpl-name');
      if (nameInput) nameInput.value = this.currentTemplate.name || 'Nueva Plantilla';
      const dispSelect = document.getElementById('builder-display-type');
      if (dispSelect) dispSelect.value = this.currentTemplate.displayType || 'lcd_reflective';

      // Cargar imagen de referencia: o del fotograma actual de app.js o sintética de prueba
      if (options.image) {
        this.setReferenceImage(options.image);
      } else if (window.loadedImage && window.loadedImage.element) {
        this.setReferenceImage(window.loadedImage.element.src);
      } else {
        this.generateDefaultSyntheticReference();
      }

      this.renderSidebarList();
      this.resizeCanvasToContainer();
      this.render();
    }

    closeModal() {
      if (!this.modal) return;
      this.modal.classList.add('hidden');
    }

    resetTemplate() {
      this.currentTemplate = {
        id: 'tpl_' + Date.now().toString(36),
        name: 'Instrumento Personalizado ' + new Date().toLocaleDateString('es-ES'),
        description: 'Plantilla de laboratorio multi-variable',
        author: 'Operador LabVision',
        displayType: 'lcd_reflective',
        subRois: []
      };
      this.selectedRoiId = null;
      this.hoveredRoiId = null;
    }

    // ================= MANEJO DE IMAGEN DE REFERENCIA =================

    setReferenceImage(srcOrBase64) {
      this.refImageBase64 = srcOrBase64;
      const img = new Image();
      img.crossOrigin = 'anonymous';
      img.onload = () => {
        this.refImage = img;
        this.imgNaturalWidth = img.naturalWidth || img.width || 1280;
        this.imgNaturalHeight = img.naturalHeight || img.height || 720;
        this.resizeCanvasToContainer();
        this.render();
        this.showToast('Imagen de referencia cargada (' + this.imgNaturalWidth + '×' + this.imgNaturalHeight + ')');
      };
      img.onerror = () => {
        console.warn('[Builder] Error al cargar imagen de referencia, generando patrón sintético');
        this.generateDefaultSyntheticReference();
      };
      img.src = srcOrBase64;
    }

    captureCurrentVideoFrame() {
      // Intentar obtener el fotograma activo cargado en app.js
      if (window.loadedImage && window.loadedImage.element) {
        this.setReferenceImage(window.loadedImage.element.src);
        return;
      }

      // Si hay backend PyWebView disponible, llamar a get_video_frame
      if (window.pywebview && window.pywebview.api && window.currentSource !== null && window.currentSource !== undefined) {
        window.pywebview.api.get_video_frame(window.currentSource, 1.0).then(res => {
          if (res && res.image_base64) {
            this.setReferenceImage(res.image_base64);
          } else {
            alert('No se pudo capturar el fotograma del video activo.');
          }
        }).catch(err => {
          alert('Error al capturar fotograma: ' + err);
        });
      } else {
        alert('No hay ninguna fuente de video o cámara activa en este momento. Carga un video en la pantalla principal o sube una imagen de referencia.');
      }
    }

    triggerUploadImage() {
      const input = document.getElementById('builder-file-input');
      if (input) {
        input.value = '';
        input.click();
      }
    }

    handleLocalImageUpload(e) {
      const file = e.target.files && e.target.files[0];
      if (!file) return;

      const reader = new FileReader();
      reader.onload = (event) => {
        this.setReferenceImage(event.target.result);
      };
      reader.readAsDataURL(file);
    }

    generateDefaultSyntheticReference() {
      // Crea una pantalla de instrumento sintética para que el usuario pueda probar de inmediato
      const offCanvas = document.createElement('canvas');
      offCanvas.width = 1280;
      offCanvas.height = 720;
      const oCtx = offCanvas.getContext('2d');

      // Fondo industrial de laboratorio
      oCtx.fillStyle = '#0f172a';
      oCtx.fillRect(0, 0, 1280, 720);

      // Chasis de instrumento
      oCtx.fillStyle = '#1e293b';
      oCtx.strokeStyle = '#334155';
      oCtx.lineWidth = 4;
      oCtx.beginPath();
      oCtx.roundRect(140, 90, 1000, 540, 24);
      oCtx.fill();
      oCtx.stroke();

      // Bisel de pantalla LCD
      oCtx.fillStyle = '#090d16';
      oCtx.strokeStyle = '#475569';
      oCtx.lineWidth = 2;
      oCtx.beginPath();
      oCtx.roundRect(200, 140, 880, 440, 12);
      oCtx.fill();
      oCtx.stroke();

      // Display retroiluminado azul/cian de laboratorio
      const grad = oCtx.createLinearGradient(220, 160, 220, 560);
      grad.addColorStop(0, '#042f47');
      grad.addColorStop(1, '#021827');
      oCtx.fillStyle = grad;
      oCtx.fillRect(220, 160, 840, 400);

      // Líneas de display y textos digitales de muestra
      oCtx.fillStyle = '#38bdf8';
      oCtx.font = 'bold 22px monospace';
      oCtx.fillText('LABORATORY INSTRUMENT MULTI-DISPLAY v2.0', 260, 210);

      // Variable 1: Valor Primario (Grande)
      oCtx.fillStyle = '#7dd3fc';
      oCtx.font = 'bold 16px sans-serif';
      oCtx.fillText('CANAL PRINCIPAL (CH 1)', 260, 270);
      oCtx.font = 'bold 72px monospace';
      oCtx.fillStyle = '#ffffff';
      oCtx.fillText('142.50', 260, 350);
      oCtx.font = 'bold 24px monospace';
      oCtx.fillStyle = '#38bdf8';
      oCtx.fillText('mPa·s', 540, 350);

      // Variable 2: Secundaria (Torque / Porcentaje)
      oCtx.fillStyle = '#7dd3fc';
      oCtx.font = 'bold 16px sans-serif';
      oCtx.fillText('POTENCIA / TORQUE', 260, 420);
      oCtx.font = 'bold 44px monospace';
      oCtx.fillStyle = '#f8fafc';
      oCtx.fillText('48.3 %', 260, 480);

      // Variable 3: Velocidad / Temperatura
      oCtx.fillStyle = '#7dd3fc';
      oCtx.font = 'bold 16px sans-serif';
      oCtx.fillText('VELOCIDAD / TEMP', 680, 270);
      oCtx.font = 'bold 48px monospace';
      oCtx.fillStyle = '#34d399';
      oCtx.fillText('25.4 °C', 680, 340);

      // Variable 4: Estado
      oCtx.fillStyle = '#7dd3fc';
      oCtx.font = 'bold 16px sans-serif';
      oCtx.fillText('ESTADO EQUIPO', 680, 420);
      oCtx.font = 'bold 32px monospace';
      oCtx.fillStyle = '#38bdf8';
      oCtx.fillText('STABLE / RUN', 680, 470);

      const dataUrl = offCanvas.toDataURL('image/jpeg', 0.9);
      this.setReferenceImage(dataUrl);
    }

    // ================= ADAPTACIÓN DE TAMAÑO Y COORDENADAS =================

    resizeCanvasToContainer() {
      if (!this.canvas || !this.container) return;

      // El canvas interno tiene las dimensiones de la imagen natural
      this.canvas.width = this.imgNaturalWidth;
      this.canvas.height = this.imgNaturalHeight;

      this.updateZoomDisplay();
    }

    setZoom(level) {
      this.zoomLevel = Math.max(0.4, Math.min(3.0, level));
      this.updateZoomDisplay();
      this.render();
    }

    zoomIn() {
      this.setZoom(this.zoomLevel + 0.2);
    }

    zoomOut() {
      this.setZoom(this.zoomLevel - 0.2);
    }

    zoomFit() {
      this.setZoom(1.0);
    }

    updateZoomDisplay() {
      const label = document.getElementById('builder-zoom-label');
      if (label) label.innerText = Math.round(this.zoomLevel * 100) + '%';
      if (this.canvas) {
        this.canvas.style.transform = `scale(${this.zoomLevel})`;
        this.canvas.style.transformOrigin = 'top left';
      }
    }

    toggleGrid() {
      this.showGrid = !this.showGrid;
      const btn = document.getElementById('btn-builder-grid');
      if (btn) {
        btn.classList.toggle('bg-cyan-900/60', this.showGrid);
        btn.classList.toggle('text-cyan-300', this.showGrid);
      }
      this.render();
    }

    // Convierte evento de ratón a coordenadas en píxeles del canvas nativo
    getCanvasCoordinates(e) {
      if (!this.canvas) return { x: 0, y: 0 };
      const rect = this.canvas.getBoundingClientRect();
      const scaleX = this.canvas.width / rect.width;
      const scaleY = this.canvas.height / rect.height;
      return {
        x: Math.max(0, Math.min(this.canvas.width, (e.clientX - rect.left) * scaleX)),
        y: Math.max(0, Math.min(this.canvas.height, (e.clientY - rect.top) * scaleY))
      };
    }

    // Convierte caja en píxeles nativos a relativas (0..1)
    toRelativeBox(pixelBox) {
      return {
        x: Math.max(0, Math.min(1, pixelBox.x / this.canvas.width)),
        y: Math.max(0, Math.min(1, pixelBox.y / this.canvas.height)),
        w: Math.max(0.01, Math.min(1, pixelBox.w / this.canvas.width)),
        h: Math.max(0.01, Math.min(1, pixelBox.h / this.canvas.height))
      };
    }

    // Convierte caja relativa (0..1) a píxeles nativos
    toPixelBox(relBox) {
      return {
        x: relBox.x * this.canvas.width,
        y: relBox.y * this.canvas.height,
        w: relBox.w * this.canvas.width,
        h: relBox.h * this.canvas.height
      };
    }

    // ================= INTERACCIÓN DE RATÓN Y EDICIÓN DE SUB-ROIs =================

    onMouseDown(e) {
      if (e.button !== 0) return; // Solo clic izquierdo
      const pos = this.getCanvasCoordinates(e);

      // 1. Comprobar si clicó en un handle de redimensionamiento del ROI seleccionado
      if (this.selectedRoiId) {
        const selRoi = this.currentTemplate.subRois.find(r => r.id === this.selectedRoiId);
        if (selRoi) {
          const pBox = this.toPixelBox(selRoi);
          const handle = this.getHitHandle(pos, pBox);
          if (handle) {
            this.isResizing = true;
            this.activeHandle = handle;
            this.dragStart = { ...pos };
            this.origBox = { ...pBox };
            return;
          }
        }
      }

      // 2. Comprobar si clicó dentro de algún Sub-ROI existente (para seleccionarlo y moverlo)
      const clickedRoi = this.findRoiAt(pos);
      if (clickedRoi) {
        this.selectedRoiId = clickedRoi.id;
        this.isDragging = true;
        this.dragStart = { ...pos };
        this.origBox = this.toPixelBox(clickedRoi);
        this.renderSidebarList();
        this.render();
        return;
      }

      // 3. Si clicó en zona vacía, iniciar dibujo de nuevo Sub-ROI
      this.isDrawing = true;
      this.selectedRoiId = null;
      this.dragStart = { ...pos };
      this.tempBox = { x: pos.x, y: pos.y, w: 0, h: 0 };
      this.render();
    }

    onMouseMove(e) {
      const pos = this.getCanvasCoordinates(e);

      // Actualizar lectura de coordenadas HUD
      this.updateCoordinatesHud(pos);

      // Caso A: Dibujando nuevo recuadro
      if (this.isDrawing) {
        this.tempBox = {
          x: Math.min(this.dragStart.x, pos.x),
          y: Math.min(this.dragStart.y, pos.y),
          w: Math.abs(pos.x - this.dragStart.x),
          h: Math.abs(pos.y - this.dragStart.y)
        };
        this.render();
        return;
      }

      // Caso B: Redimensionando Sub-ROI seleccionado mediante handle
      if (this.isResizing && this.selectedRoiId && this.origBox) {
        const dx = pos.x - this.dragStart.x;
        const dy = pos.y - this.dragStart.y;
        const newBox = { ...this.origBox };

        if (this.activeHandle === 'nw') {
          newBox.x += dx;
          newBox.y += dy;
          newBox.w -= dx;
          newBox.h -= dy;
        } else if (this.activeHandle === 'ne') {
          newBox.y += dy;
          newBox.w += dx;
          newBox.h -= dy;
        } else if (this.activeHandle === 'se') {
          newBox.w += dx;
          newBox.h += dy;
        } else if (this.activeHandle === 'sw') {
          newBox.x += dx;
          newBox.w -= dx;
          newBox.h += dy;
        }

        if (newBox.w > 15 && newBox.h > 15) {
          const selRoi = this.currentTemplate.subRois.find(r => r.id === this.selectedRoiId);
          if (selRoi) {
            const rel = this.toRelativeBox(newBox);
            selRoi.x = rel.x;
            selRoi.y = rel.y;
            selRoi.w = rel.w;
            selRoi.h = rel.h;
          }
        }
        this.render();
        return;
      }

      // Caso C: Moviendo Sub-ROI seleccionado
      if (this.isDragging && this.selectedRoiId && this.origBox) {
        const dx = pos.x - this.dragStart.x;
        const dy = pos.y - this.dragStart.y;
        const newBox = {
          x: Math.max(0, Math.min(this.canvas.width - this.origBox.w, this.origBox.x + dx)),
          y: Math.max(0, Math.min(this.canvas.height - this.origBox.h, this.origBox.y + dy)),
          w: this.origBox.w,
          h: this.origBox.h
        };

        const selRoi = this.currentTemplate.subRois.find(r => r.id === this.selectedRoiId);
        if (selRoi) {
          const rel = this.toRelativeBox(newBox);
          selRoi.x = rel.x;
          selRoi.y = rel.y;
        }
        this.render();
        return;
      }

      // Caso D: Cursor hover
      this.updateCursor(pos);
    }

    onMouseUp(e) {
      if (this.isDrawing && this.tempBox) {
        // Solo agregar si tiene un tamaño mínimo útil (ej. 20x15 px)
        if (this.tempBox.w >= 20 && this.tempBox.h >= 15) {
          const rel = this.toRelativeBox(this.tempBox);
          const newRoi = this.createSubRoiObject(rel);
          this.currentTemplate.subRois.push(newRoi);
          this.selectedRoiId = newRoi.id;
          this.renderSidebarList();
          this.scrollSidebarToCard(newRoi.id);
        }
      }

      this.isDrawing = false;
      this.isDragging = false;
      this.isResizing = false;
      this.tempBox = null;
      this.activeHandle = null;
      this.origBox = null;
      this.render();
    }

    updateCoordinatesHud(pos) {
      const hud = document.getElementById('builder-coord-hud');
      if (hud) {
        const pctX = ((pos.x / this.canvas.width) * 100).toFixed(1);
        const pctY = ((pos.y / this.canvas.height) * 100).toFixed(1);
        hud.innerText = `X: ${Math.round(pos.x)}px (${pctX}%) | Y: ${Math.round(pos.y)}px (${pctY}%)`;
      }
    }

    updateCursor(pos) {
      if (!this.canvas) return;

      if (this.selectedRoiId) {
        const selRoi = this.currentTemplate.subRois.find(r => r.id === this.selectedRoiId);
        if (selRoi) {
          const pBox = this.toPixelBox(selRoi);
          const handle = this.getHitHandle(pos, pBox);
          if (handle) {
            this.canvas.style.cursor = (handle === 'nw' || handle === 'se') ? 'nwse-resize' : 'nesw-resize';
            return;
          }
        }
      }

      const hit = this.findRoiAt(pos);
      if (hit) {
        this.hoveredRoiId = hit.id;
        this.canvas.style.cursor = 'move';
      } else {
        this.hoveredRoiId = null;
        this.canvas.style.cursor = 'crosshair';
      }
    }

    getHitHandle(pos, pBox) {
      const handleSize = 10;
      const handles = {
        nw: { x: pBox.x, y: pBox.y },
        ne: { x: pBox.x + pBox.w, y: pBox.y },
        se: { x: pBox.x + pBox.w, y: pBox.y + pBox.h },
        sw: { x: pBox.x, y: pBox.y + pBox.h }
      };

      for (const [key, pt] of Object.entries(handles)) {
        if (Math.abs(pos.x - pt.x) <= handleSize && Math.abs(pos.y - pt.y) <= handleSize) {
          return key;
        }
      }
      return null;
    }

    findRoiAt(pos) {
      // Búsqueda en orden inverso (los superiores primero)
      for (let i = this.currentTemplate.subRois.length - 1; i >= 0; i--) {
        const roi = this.currentTemplate.subRois[i];
        const pBox = this.toPixelBox(roi);
        if (
          pos.x >= pBox.x && pos.x <= pBox.x + pBox.w &&
          pos.y >= pBox.y && pos.y <= pBox.y + pBox.h
        ) {
          return roi;
        }
      }
      return null;
    }

    createSubRoiObject(relCoords) {
      const index = this.currentTemplate.subRois.length + 1;
      const color = LAB_PALETTE[(index - 1) % LAB_PALETTE.length];

      // Sugerencia de nombre inteligente según índice
      const defaultNames = ['Viscosidad', 'Temperatura', 'Masa', 'pH', 'Velocidad', 'Torque', 'Presión', 'Voltaje'];
      const suggestedName = defaultNames[index - 1] || ('Variable ' + index);
      const suggestedUnit = suggestedName === 'Viscosidad' ? 'mPa·s' :
                            suggestedName === 'Temperatura' ? '°C' :
                            suggestedName === 'Masa' ? 'g' :
                            suggestedName === 'pH' ? 'pH' :
                            suggestedName === 'Velocidad' ? 'RPM' :
                            suggestedName === 'Torque' ? '%' : '';

      return {
        id: 'roi_' + Date.now().toString(36) + '_' + Math.floor(Math.random() * 1000),
        name: suggestedName,
        unit: suggestedUnit,
        dataType: 'float', // 'float', 'int', 'string'
        min: null,
        max: null,
        color: color,
        x: relCoords.x,
        y: relCoords.y,
        w: relCoords.w,
        h: relCoords.h,
        testResult: null // { value, confidence, isBad, warning }
      };
    }

    deleteSubRoi(id) {
      this.currentTemplate.subRois = this.currentTemplate.subRois.filter(r => r.id !== id);
      if (this.selectedRoiId === id) this.selectedRoiId = null;
      this.renderSidebarList();
      this.render();
    }

    clearAllSubRois() {
      if (this.currentTemplate.subRois.length === 0) return;
      if (confirm('¿Deseas eliminar todos los Sub-ROIs creados?')) {
        this.currentTemplate.subRois = [];
        this.selectedRoiId = null;
        this.renderSidebarList();
        this.render();
      }
    }

    addSubRoiManually() {
      // Agrega un Sub-ROI en el centro de la pantalla
      const rel = {
        x: 0.35,
        y: 0.35,
        w: 0.30,
        h: 0.20
      };
      const newRoi = this.createSubRoiObject(rel);
      this.currentTemplate.subRois.push(newRoi);
      this.selectedRoiId = newRoi.id;
      this.renderSidebarList();
      this.scrollSidebarToCard(newRoi.id);
      this.render();
    }

    // ================= DIBUJADO EN CANVAS =================

    render() {
      if (!this.ctx || !this.canvas) return;

      const ctx = this.ctx;
      const w = this.canvas.width;
      const h = this.canvas.height;

      // 1. Limpiar lienzo
      ctx.clearRect(0, 0, w, h);

      // 2. Dibujar imagen de referencia
      if (this.refImage) {
        ctx.drawImage(this.refImage, 0, 0, w, h);
      } else {
        ctx.fillStyle = '#090d16';
        ctx.fillRect(0, 0, w, h);
      }

      // 3. Calibrated Grid (cuadrícula de medición)
      if (this.showGrid) {
        this.drawCalibratedGrid(ctx, w, h);
      }

      // 4. Dibujar todos los Sub-ROIs guardados
      this.currentTemplate.subRois.forEach((roi, idx) => {
        const isSelected = roi.id === this.selectedRoiId;
        const isHovered = roi.id === this.hoveredRoiId;
        this.drawSubRoiBox(ctx, roi, idx + 1, isSelected, isHovered);
      });

      // 5. Dibujar caja temporal mientras el usuario arrastra el mouse
      if (this.isDrawing && this.tempBox) {
        ctx.save();
        ctx.strokeStyle = '#38bdf8';
        ctx.fillStyle = 'rgba(56, 189, 248, 0.15)';
        ctx.lineWidth = 2;
        ctx.setLineDash([6, 4]);
        ctx.fillRect(this.tempBox.x, this.tempBox.y, this.tempBox.w, this.tempBox.h);
        ctx.strokeRect(this.tempBox.x, this.tempBox.y, this.tempBox.w, this.tempBox.h);

        // Etiqueta de dimensiones en vivo
        const dimStr = `${Math.round(this.tempBox.w)} × ${Math.round(this.tempBox.h)} px`;
        ctx.setLineDash([]);
        ctx.fillStyle = '#0b0f19';
        ctx.font = '10px monospace';
        const txtWidth = ctx.measureText(dimStr).width;
        ctx.fillRect(this.tempBox.x + this.tempBox.w - txtWidth - 8, this.tempBox.y + this.tempBox.h - 18, txtWidth + 6, 16);
        ctx.fillStyle = '#38bdf8';
        ctx.fillText(dimStr, this.tempBox.x + this.tempBox.w - txtWidth - 5, this.tempBox.y + this.tempBox.h - 6);
        ctx.restore();
      }
    }

    drawCalibratedGrid(ctx, w, h) {
      ctx.save();
      ctx.strokeStyle = 'rgba(56, 189, 248, 0.08)';
      ctx.lineWidth = 1;

      // Líneas de 10%
      const stepX = w / 10;
      const stepY = h / 10;

      for (let x = stepX; x < w; x += stepX) {
        ctx.beginPath();
        ctx.moveTo(x, 0);
        ctx.lineTo(x, h);
        ctx.stroke();
      }

      for (let y = stepY; y < h; y += stepY) {
        ctx.beginPath();
        ctx.moveTo(0, y);
        ctx.lineTo(w, y);
        ctx.stroke();
      }

      // Marcas de regla en los bordes
      ctx.strokeStyle = 'rgba(56, 189, 248, 0.25)';
      ctx.fillStyle = 'rgba(148, 163, 184, 0.6)';
      ctx.font = '9px monospace';
      for (let x = 0; x < w; x += stepX) {
        ctx.beginPath();
        ctx.moveTo(x, 0);
        ctx.lineTo(x, 6);
        ctx.stroke();
        if (x > 0) ctx.fillText(Math.round((x / w) * 100) + '%', x + 2, 12);
      }
      for (let y = 0; y < h; y += stepY) {
        ctx.beginPath();
        ctx.moveTo(0, y);
        ctx.lineTo(6, y);
        ctx.stroke();
        if (y > 0) ctx.fillText(Math.round((y / h) * 100) + '%', 8, y - 2);
      }

      ctx.restore();
    }

    drawSubRoiBox(ctx, roi, numberIndex, isSelected, isHovered) {
      const pBox = this.toPixelBox(roi);
      const color = roi.color || '#38bdf8';

      ctx.save();

      // 1. Relleno semi-transparente
      ctx.fillStyle = isSelected ? this.hexToRgba(color, 0.28) : this.hexToRgba(color, 0.14);
      ctx.fillRect(pBox.x, pBox.y, pBox.w, pBox.h);

      // 2. Trazo del Bounding Box
      ctx.lineWidth = isSelected ? 3 : (isHovered ? 2.5 : 2);
      ctx.strokeStyle = color;
      ctx.strokeRect(pBox.x, pBox.y, pBox.w, pBox.h);

      // 3. Handles de redimensionamiento si está seleccionado
      if (isSelected) {
        const handleSize = 8;
        ctx.fillStyle = '#ffffff';
        ctx.strokeStyle = color;
        ctx.lineWidth = 2;

        const handles = [
          { x: pBox.x, y: pBox.y },
          { x: pBox.x + pBox.w, y: pBox.y },
          { x: pBox.x + pBox.w, y: pBox.y + pBox.h },
          { x: pBox.x, y: pBox.y + pBox.h }
        ];

        handles.forEach(h => {
          ctx.fillRect(h.x - handleSize / 2, h.y - handleSize / 2, handleSize, handleSize);
          ctx.strokeRect(h.x - handleSize / 2, h.y - handleSize / 2, handleSize, handleSize);
        });
      }

      // 4. Etiqueta superior con Nombre, Unidad y Resultado OCR
      let labelText = `#${numberIndex} ${roi.name}`;
      if (roi.unit) labelText += ` (${roi.unit})`;

      // Si se probó el OCR, mostrar valor y porcentaje de confianza
      if (roi.testResult && roi.testResult.value !== null && roi.testResult.value !== undefined) {
        const valStr = roi.testResult.value;
        const confStr = `${Math.round(roi.testResult.confidence * 100)}%`;
        labelText += ` ➔ ${valStr} [${confStr}]`;
      }

      ctx.font = 'bold 11px monospace';
      const textMetrics = ctx.measureText(labelText);
      const badgeW = textMetrics.width + 16;
      const badgeH = 20;
      const badgeX = pBox.x;
      const badgeY = Math.max(0, pBox.y - badgeH);

      // Fondo oscuro de alta visibilidad para la etiqueta
      ctx.fillStyle = '#0b0f19';
      ctx.beginPath();
      ctx.roundRect(badgeX, badgeY, badgeW, badgeH, [4, 4, 0, 0]);
      ctx.fill();

      // Borde de la etiqueta
      ctx.strokeStyle = color;
      ctx.lineWidth = 1.5;
      ctx.stroke();

      // Punto de color identificador
      ctx.fillStyle = color;
      ctx.beginPath();
      ctx.arc(badgeX + 8, badgeY + badgeH / 2, 4, 0, Math.PI * 2);
      ctx.fill();

      // Texto de la etiqueta
      ctx.fillStyle = roi.testResult && roi.testResult.isBad ? '#f43f5e' : '#f8fafc';
      ctx.fillText(labelText, badgeX + 16, badgeY + 14);

      // Si hay advertencia de rango, pintar icono de alerta
      if (roi.testResult && roi.testResult.isBad) {
        ctx.fillStyle = '#f43f5e';
        ctx.font = 'bold 12px sans-serif';
        ctx.fillText('⚠', badgeX + badgeW - 14, badgeY + 14);
      }

      ctx.restore();
    }

    hexToRgba(hex, alpha) {
      let c = hex.replace('#', '');
      if (c.length === 3) c = c.split('').map(x => x + x).join('');
      const num = parseInt(c, 16);
      return `rgba(${(num >> 16) & 255}, ${(num >> 8) & 255}, ${num & 255}, ${alpha})`;
    }

    // ================= SIDEBAR: LISTA DE VARIABLES =================

    renderSidebarList() {
      const container = document.getElementById('builder-roi-list');
      const countBadge = document.getElementById('builder-roi-count');
      if (!container) return;

      const subRois = this.currentTemplate.subRois;
      if (countBadge) {
        countBadge.innerText = `${subRois.length} ${subRois.length === 1 ? 'variable' : 'variables'}`;
      }

      if (subRois.length === 0) {
        container.innerHTML = `
          <div class="text-center py-10 px-4 text-slate-500 border border-dashed border-slate-800 rounded-xl">
            <svg class="w-8 h-8 mx-auto mb-2 text-slate-600" viewBox="0 0 16 16" fill="currentColor">
              <rect x="2" y="2" width="12" height="12" fill="none" stroke="currentColor" stroke-width="1.5" stroke-dasharray="2,2"/>
              <rect x="7" y="4" width="2" height="8"/>
              <rect x="4" y="7" width="8" height="2"/>
            </svg>
            <p class="text-xs font-semibold text-slate-400">Sin variables definidas todavía</p>
            <p class="text-[11px] text-slate-500 mt-1">Haz clic y arrastra en el visor de la izquierda para trazar el primer display de lectura.</p>
            <button type="button" onclick="window.labBuilder.addSubRoiManually()" class="mt-3 px-3 py-1.5 rounded-lg bg-cyan-950/70 hover:bg-cyan-900 border border-cyan-700/60 text-cyan-300 text-xs font-semibold transition-all">
              + Añadir Variable Manualmente
            </button>
          </div>
        `;
        return;
      }

      container.innerHTML = '';
      subRois.forEach((roi, idx) => {
        const isSelected = roi.id === this.selectedRoiId;
        const card = document.createElement('div');
        card.id = `card-${roi.id}`;
        card.className = `p-3 rounded-xl border transition-all ${
          isSelected
            ? 'bg-slate-800/90 border-cyan-500 shadow-md ring-1 ring-cyan-500/30'
            : 'bg-slate-900/70 border-slate-800 hover:border-slate-700'
        }`;

        // Contenido de la tarjeta de variable
        card.innerHTML = `
          <div class="flex items-center justify-between pb-2 border-b border-slate-800/80 mb-2.5">
            <div class="flex items-center space-x-2">
              <span class="w-5 h-5 rounded-md flex items-center justify-center text-[10px] font-bold font-mono text-white shadow-sm" style="background-color: ${roi.color}">
                ${idx + 1}
              </span>
              <span class="text-xs font-bold text-slate-200">${roi.name || 'Variable ' + (idx + 1)}</span>
            </div>
            <div class="flex items-center space-x-1">
              <button type="button" onclick="window.labBuilder.selectRoi('${roi.id}')" title="Seleccionar en Canvas" class="p-1 rounded text-slate-400 hover:text-cyan-300 transition-colors">
                <svg class="w-3.5 h-3.5" viewBox="0 0 16 16" fill="currentColor">
                  <rect x="2" y="2" width="4" height="2"/>
                  <rect x="2" y="2" width="2" height="4"/>
                  <rect x="10" y="2" width="4" height="2"/>
                  <rect x="12" y="2" width="2" height="4"/>
                  <rect x="2" y="12" width="4" height="2"/>
                  <rect x="2" y="10" width="2" height="4"/>
                  <rect x="10" y="12" width="4" height="2"/>
                  <rect x="12" y="10" width="2" height="4"/>
                </svg>
              </button>
              <button type="button" onclick="window.labBuilder.deleteSubRoi('${roi.id}')" title="Eliminar Sub-ROI" class="p-1 rounded text-slate-500 hover:text-rose-400 transition-colors">
                <svg class="w-3.5 h-3.5" viewBox="0 0 16 16" fill="currentColor">
                  <rect x="3" y="3" width="10" height="2"/>
                  <rect x="5" y="6" width="2" height="7"/>
                  <rect x="9" y="6" width="2" height="7"/>
                  <rect x="4" y="5" width="8" height="9" fill="none" stroke="currentColor" stroke-width="1.5"/>
                </svg>
              </button>
            </div>
          </div>

          <div class="grid grid-cols-2 gap-2 text-xs">
            <!-- Nombre de la Variable -->
            <div>
              <label class="block text-[10px] uppercase font-bold text-slate-400 mb-0.5">Nombre:</label>
              <input type="text" value="${roi.name}" oninput="window.labBuilder.updateRoiField('${roi.id}', 'name', this.value)" class="w-full bg-slate-950 border border-slate-700 rounded-lg px-2 py-1 text-slate-200 text-xs focus:outline-none focus:border-cyan-400 font-medium">
            </div>

            <!-- Unidad SI -->
            <div>
              <label class="block text-[10px] uppercase font-bold text-slate-400 mb-0.5">Unidad SI:</label>
              <input type="text" value="${roi.unit || ''}" placeholder="mPa·s, °C, pH..." oninput="window.labBuilder.updateRoiField('${roi.id}', 'unit', this.value)" class="w-full bg-slate-950 border border-slate-700 rounded-lg px-2 py-1 text-slate-200 text-xs focus:outline-none focus:border-cyan-400 font-mono">
            </div>

            <!-- Tipo de Dato -->
            <div>
              <label class="block text-[10px] uppercase font-bold text-slate-400 mb-0.5">Tipo de Dato:</label>
              <select onchange="window.labBuilder.updateRoiField('${roi.id}', 'dataType', this.value)" class="w-full bg-slate-950 border border-slate-700 rounded-lg px-2 py-1 text-slate-200 text-xs focus:outline-none focus:border-cyan-400 font-mono">
                <option value="float" ${roi.dataType === 'float' ? 'selected' : ''}>Decimal (Float)</option>
                <option value="int" ${roi.dataType === 'int' ? 'selected' : ''}>Entero (Int)</option>
                <option value="string" ${roi.dataType === 'string' ? 'selected' : ''}>Texto / Alfanum</option>
              </select>
            </div>

            <!-- Rango Min y Max -->
            <div>
              <label class="block text-[10px] uppercase font-bold text-slate-400 mb-0.5">Límites (Mín / Máx):</label>
              <div class="flex space-x-1">
                <input type="number" step="any" placeholder="Min" value="${roi.min !== null && roi.min !== undefined ? roi.min : ''}" oninput="window.labBuilder.updateRoiField('${roi.id}', 'min', this.value)" class="w-1/2 bg-slate-950 border border-slate-700 rounded-lg px-1.5 py-1 text-slate-200 text-xs focus:outline-none focus:border-cyan-400 font-mono">
                <input type="number" step="any" placeholder="Max" value="${roi.max !== null && roi.max !== undefined ? roi.max : ''}" oninput="window.labBuilder.updateRoiField('${roi.id}', 'max', this.value)" class="w-1/2 bg-slate-950 border border-slate-700 rounded-lg px-1.5 py-1 text-slate-200 text-xs focus:outline-none focus:border-cyan-400 font-mono">
              </div>
            </div>
          </div>

          <!-- Chips de unidades rápidas -->
          <div class="flex flex-wrap gap-1 mt-2 pt-1.5 border-t border-slate-800/60">
            ${['mPa·s', '°C', 'pH', 'g', 'RPM', 'µS/cm', '%', 'mV'].map(u => `
              <button type="button" onclick="window.labBuilder.updateRoiField('${roi.id}', 'unit', '${u}')" class="px-1.5 py-0.5 text-[9px] rounded bg-slate-800 hover:bg-slate-700 text-slate-300 font-mono transition-colors">
                ${u}
              </button>
            `).join('')}
          </div>

          <!-- Resultado del Test OCR si existe -->
          ${roi.testResult ? `
            <div class="mt-2.5 p-2 rounded-lg bg-slate-950 border ${roi.testResult.isBad ? 'border-rose-700/80 bg-rose-950/20' : 'border-emerald-700/80 bg-emerald-950/20'} flex items-center justify-between text-xs">
              <div>
                <span class="text-[9px] uppercase font-bold ${roi.testResult.isBad ? 'text-rose-400' : 'text-emerald-400'} block">Lectura OCR:</span>
                <span class="font-mono font-bold text-white text-sm">${roi.testResult.value !== null ? roi.testResult.value : '--'} ${roi.unit}</span>
                ${roi.testResult.warning ? `<span class="block text-[9px] text-rose-300 italic">${roi.testResult.warning}</span>` : ''}
              </div>
              <div class="text-right">
                <span class="text-[9px] uppercase font-bold text-slate-400 block">Confianza</span>
                <span class="font-mono text-xs font-bold ${roi.testResult.isBad ? 'text-rose-400' : 'text-emerald-300'}">
                  ${Math.round(roi.testResult.confidence * 100)}%
                </span>
              </div>
            </div>
          ` : ''}
        `;

        card.addEventListener('click', (e) => {
          if (['INPUT', 'SELECT', 'BUTTON', 'SVG', 'PATH'].includes(e.target.tagName)) return;
          this.selectRoi(roi.id);
        });

        container.appendChild(card);
      });
    }

    scrollSidebarToCard(roiId) {
      setTimeout(() => {
        const card = document.getElementById(`card-${roiId}`);
        if (card) {
          card.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
        }
      }, 50);
    }

    selectRoi(roiId) {
      this.selectedRoiId = roiId;
      this.renderSidebarList();
      this.render();
    }

    updateRoiField(roiId, field, value) {
      const roi = this.currentTemplate.subRois.find(r => r.id === roiId);
      if (!roi) return;

      if (field === 'min' || field === 'max') {
        roi[field] = value === '' ? null : parseFloat(value);
      } else {
        roi[field] = value;
      }

      this.render();
    }

    // ================= ACCIONES: PROBAR OCR, GUARDAR, EXPORTAR =================

    async testTemplateOcr() {
      if (this.currentTemplate.subRois.length === 0) {
        alert('Debes definir al menos un Sub-ROI sobre la imagen para probar el reconocimiento OCR.');
        return;
      }

      if (!this.refImageBase64) {
        alert('Carga una imagen de referencia o fotograma de video antes de probar.');
        return;
      }

      const btn = document.getElementById('btn-test-ocr');
      const originalText = btn ? btn.innerHTML : '';
      if (btn) {
        btn.disabled = true;
        btn.innerHTML = `
          <svg class="animate-spin -ml-1 mr-2 h-4 w-4 text-cyan-300 inline" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24">
            <circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"></circle>
            <path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8v8H4z"></path>
          </svg>
          <span>Analizando Regiones OCR...</span>
        `;
      }

      // Preparar payload de Sub-ROIs con coordenadas
      const payload = this.currentTemplate.subRois.map(r => ({
        id: r.id,
        name: r.name,
        unit: r.unit,
        data_type: r.dataType,
        min: r.min,
        max: r.max,
        x: r.x,
        y: r.y,
        w: r.w,
        h: r.h
      }));

      try {
        let results = [];

        // 1. Si existe backend PyWebView conectado
        if (window.pywebview && window.pywebview.api && window.pywebview.api.test_template_ocr) {
          const res = await window.pywebview.api.test_template_ocr(this.refImageBase64, payload);
          if (res.error) {
            throw new Error(res.error);
          }
          results = res.results || [];
        } else {
          // 2. Modo autónomo / navegador: Simulación científica inteligente para pruebas UI
          await new Promise(r => setTimeout(r, 650));
          results = payload.map((p, i) => {
            let simVal = 142.5;
            if (p.unit === '°C') simVal = 25.4;
            else if (p.unit === 'g') simVal = 24.8152;
            else if (p.unit === 'pH') simVal = 7.02;
            else if (p.unit === 'RPM') simVal = 30.0;
            else if (p.unit === '%') simVal = 48.3;
            else simVal = +(10 + i * 15.2).toFixed(2);

            return {
              id: p.id,
              name: p.name,
              unit: p.unit,
              raw_text: simVal.toString(),
              parsed_value: simVal,
              confidence: 0.965,
              confidence_pct: 96.5,
              is_bad: false,
              warning: null
            };
          });
        }

        // Aplicar resultados en los Sub-ROIs
        results.forEach(res => {
          const roi = this.currentTemplate.subRois.find(r => r.id === res.id);
          if (roi) {
            roi.testResult = {
              value: res.parsed_value,
              confidence: res.confidence,
              isBad: res.is_bad,
              warning: res.warning
            };
          }
        });

        // Sonido de confirmación sintético de laboratorio
        if (window.labAudio) {
          const anyBad = results.some(r => r.is_bad);
          if (anyBad) window.labAudio.playWarningBeep();
          else window.labAudio.playSuccessBeep();
        }

        this.renderSidebarList();
        this.render();
        this.showToast('✅ OCR completado: ' + results.length + ' regiones evaluadas');

      } catch (err) {
        console.error('[Builder] Error en test OCR:', err);
        alert('Error ejecutando reconocimiento OCR: ' + err.message);
      } finally {
        if (btn) {
          btn.disabled = false;
          btn.innerHTML = originalText;
        }
      }
    }

    saveTemplate() {
      const nameInput = document.getElementById('builder-tpl-name');
      const dispSelect = document.getElementById('builder-display-type');

      const templateName = (nameInput && nameInput.value.trim()) || 'Plantilla Personalizada';
      const displayType = (dispSelect && dispSelect.value) || 'lcd_reflective';

      if (this.currentTemplate.subRois.length === 0) {
        alert('Debes definir al menos una variable / Sub-ROI antes de guardar la plantilla.');
        return;
      }

      this.currentTemplate.name = templateName;
      this.currentTemplate.displayType = displayType;
      this.currentTemplate.updatedAt = new Date().toISOString();

      // Generar paquete estandarizado según la especificación .lvtemplate
      const lvPackage = this.buildLvTemplatePackage(this.currentTemplate);

      // 1. Guardar en localStorage
      const savedList = this.getStoredTemplates();
      const existingIdx = savedList.findIndex(t => t.metadata.template_id === lvPackage.metadata.template_id);
      if (existingIdx >= 0) {
        savedList[existingIdx] = lvPackage;
      } else {
        savedList.push(lvPackage);
      }
      localStorage.setItem('lab_custom_templates', JSON.stringify(savedList));

      // 2. Si hay backend PyWebView, guardar también en disco
      if (window.pywebview && window.pywebview.api && window.pywebview.api.save_custom_template) {
        window.pywebview.api.save_custom_template(lvPackage).catch(e => console.warn('Error guardando en backend:', e));
      }

      // 3. Actualizar Selector de Presets de la UI Principal
      this.updatePresetSelectorOptions();

      this.showToast(`💾 Plantilla "${templateName}" guardada con éxito`);
      this.closeModal();

      // Si existe función para cargar la plantilla en la vista principal, aplicarla
      if (typeof window.applyCustomTemplateToDashboard === 'function') {
        window.applyCustomTemplateToDashboard(lvPackage);
      }
    }

    exportLvTemplate() {
      const nameInput = document.getElementById('builder-tpl-name');
      const templateName = (nameInput && nameInput.value.trim()) || 'Plantilla_LabVision';

      if (this.currentTemplate.subRois.length === 0) {
        alert('La plantilla no tiene variables para exportar.');
        return;
      }

      this.currentTemplate.name = templateName;
      const lvPackage = this.buildLvTemplatePackage(this.currentTemplate);
      const jsonStr = JSON.stringify(lvPackage, null, 2);

      // Si PyWebView soporta diálogo nativo de guardado
      const safeFilename = templateName.replace(/[^a-zA-Z0-9_\-\.]/g, '_') + '.lvtemplate';
      if (window.pywebview && window.pywebview.api && window.pywebview.api.export_template_dialog) {
        window.pywebview.api.export_template_dialog(jsonStr, safeFilename).then(res => {
          if (res && res.success) {
            this.showToast('📤 Archivo .lvtemplate exportado exitosamente');
          }
        }).catch(() => {
          this.downloadBlobFile(jsonStr, safeFilename);
        });
      } else {
        this.downloadBlobFile(jsonStr, safeFilename);
      }
    }

    downloadBlobFile(content, filename) {
      const blob = new Blob([content], { type: 'application/json' });
      const url = URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = filename;
      document.body.appendChild(a);
      a.click();
      document.body.removeChild(a);
      URL.revokeObjectURL(url);
      this.showToast('📤 Archivo .lvtemplate descargado: ' + filename);
    }

    triggerImportTemplate() {
      // Si PyWebView soporta diálogo nativo
      if (window.pywebview && window.pywebview.api && window.pywebview.api.import_template_dialog) {
        window.pywebview.api.import_template_dialog().then(res => {
          if (res && res.template) {
            this.loadTemplateFromData(res.template);
          }
        }).catch(err => {
          console.warn('Fallo diálogo nativo, usando file picker HTML:', err);
          const input = document.getElementById('builder-import-input');
          if (input) { input.value = ''; input.click(); }
        });
      } else {
        const input = document.getElementById('builder-import-input');
        if (input) { input.value = ''; input.click(); }
      }
    }

    handleTemplateFileImport(e) {
      const file = e.target.files && e.target.files[0];
      if (!file) return;

      const reader = new FileReader();
      reader.onload = (event) => {
        try {
          const data = JSON.parse(event.target.result);
          this.loadTemplateFromData(data);
        } catch (err) {
          alert('Error: el archivo seleccionado no es un .lvtemplate o JSON válido.\n' + err.message);
        }
      };
      reader.readAsText(file);
    }

    loadTemplateFromData(data) {
      if (!data || !data.sub_rois) {
        alert('Estructura de plantilla inválida: faltan sub_rois.');
        return;
      }

      const meta = data.metadata || {};
      const newTemplate = {
        id: meta.template_id || 'tpl_' + Date.now().toString(36),
        name: meta.name || 'Plantilla Importada',
        description: meta.description || '',
        author: meta.author || 'NachoFari',
        displayType: (data.display_profile && data.display_profile.type) || 'lcd_reflective',
        subRois: data.sub_rois.map((sr, idx) => ({
          id: sr.id || ('roi_' + idx),
          name: sr.display_label || sr.name || `Var ${idx + 1}`,
          unit: sr.unit || '',
          dataType: sr.data_type || 'float',
          min: (sr.valid_range && sr.valid_range[0]) ?? null,
          max: (sr.valid_range && sr.valid_range[1]) ?? null,
          color: LAB_PALETTE[idx % LAB_PALETTE.length],
          x: sr.coordinates_relative ? sr.coordinates_relative.x : (sr.x || 0.1),
          y: sr.coordinates_relative ? sr.coordinates_relative.y : (sr.y || 0.1),
          w: sr.coordinates_relative ? sr.coordinates_relative.w : (sr.w || 0.3),
          h: sr.coordinates_relative ? sr.coordinates_relative.h : (sr.h || 0.2),
          testResult: null
        }))
      };

      this.currentTemplate = newTemplate;
      this.selectedRoiId = newTemplate.subRois.length > 0 ? newTemplate.subRois[0].id : null;

      // Actualizar encabezados
      const nameInput = document.getElementById('builder-tpl-name');
      if (nameInput) nameInput.value = newTemplate.name;
      const dispSelect = document.getElementById('builder-display-type');
      if (dispSelect) dispSelect.value = newTemplate.displayType;

      this.renderSidebarList();
      this.render();
      this.showToast(`📂 Plantilla "${newTemplate.name}" cargada con ${newTemplate.subRois.length} variables`);

      // Abrir modal si estaba cerrado
      if (this.modal && this.modal.classList.contains('hidden')) {
        this.openModal({ template: newTemplate });
      }
    }

    // ================= ESPECIFICACIÓN ESTÁNDAR .lvtemplate (ROADMAP WP5) =================

    buildLvTemplatePackage(tpl) {
      const templateId = tpl.id || ('custom_' + Date.now().toString(36));
      return {
        "$schema": "https://labvision.org/schemas/v1/template.json",
        "lvtemplate_version": "1.0",
        "metadata": {
          "template_id": templateId,
          "name": tpl.name || "Plantilla Personalizada",
          "description": tpl.description || "Plantilla generada con LabVision No-Code Builder",
          "author": tpl.author || "NachoFari",
          "institution": "Laboratorio Analítico",
          "created_at": new Date().toISOString(),
          "compatible_hardware": [tpl.name]
        },
        "display_profile": {
          "type": tpl.displayType || "lcd_reflective",
          "preprocessing": {
            "grayscale": true,
            "clahe": false,
            "threshold_mode": "otsu_adaptive",
            "invert_polarity": false,
            "noise_kernel_size": 3
          }
        },
        "sub_rois": tpl.subRois.map(r => ({
          "id": r.id,
          "display_label": r.name,
          "unit": r.unit || "",
          "coordinates_relative": {
            "x": Math.round(r.x * 1000) / 1000,
            "y": Math.round(r.y * 1000) / 1000,
            "w": Math.round(r.w * 1000) / 1000,
            "h": Math.round(r.h * 1000) / 1000
          },
          "data_type": r.dataType || "float",
          "decimal_places": r.dataType === 'int' ? 0 : 2,
          "valid_range": (r.min !== null || r.max !== null) ? [r.min ?? -999999, r.max ?? 999999] : null,
          "ocr_whitelist": r.dataType === 'string' ? null : "0123456789.-"
        })),
        "streaming_export": {
          "default_sample_interval_sec": 1.0,
          "csv_columns": [
            "Tiempo_seg",
            "Timestamp",
            ...tpl.subRois.map(r => r.name.replace(/[^a-zA-Z0-9_]/g, '_')),
            "Confianza_Pct",
            "Estado"
          ]
        },
        "live_chart": {
          "primary_series": {
            "field_id": tpl.subRois.length > 0 ? tpl.subRois[0].id : "main",
            "color": tpl.subRois.length > 0 ? tpl.subRois[0].color : "#06b6d4",
            "chart_type": "line"
          }
        }
      };
    }

    getStoredTemplates() {
      try {
        const raw = localStorage.getItem('lab_custom_templates');
        return raw ? JSON.parse(raw) : [];
      } catch (e) {
        return [];
      }
    }

    loadCustomTemplatesFromStorage() {
      this.updatePresetSelectorOptions();
    }

    updatePresetSelectorOptions() {
      const customOptgroup = document.getElementById('optgroup-custom-templates');
      if (!customOptgroup) return;

      const templates = this.getStoredTemplates();
      customOptgroup.innerHTML = '';

      if (templates.length === 0) {
        customOptgroup.classList.add('hidden');
        return;
      }

      customOptgroup.classList.remove('hidden');
      templates.forEach(t => {
        const opt = document.createElement('option');
        const meta = t.metadata || {};
        opt.value = `custom:${meta.template_id}`;
        opt.innerText = `🧪 ${meta.name || 'Plantilla'} (${(t.sub_rois || []).length} vars)`;
        customOptgroup.appendChild(opt);
      });
    }

    showToast(message) {
      let toast = document.getElementById('builder-toast');
      if (!toast) {
        toast = document.createElement('div');
        toast.id = 'builder-toast';
        toast.className = 'fixed bottom-6 right-6 z-[60] bg-slate-900 border border-cyan-500 text-cyan-200 px-4 py-2.5 rounded-xl shadow-2xl text-xs font-semibold flex items-center space-x-2 transition-all transform translate-y-12 opacity-0';
        document.body.appendChild(toast);
      }
      toast.innerText = message;
      toast.classList.remove('translate-y-12', 'opacity-0');
      clearTimeout(this._toastTimeout);
      this._toastTimeout = setTimeout(() => {
        toast.classList.add('translate-y-12', 'opacity-0');
      }, 3500);
    }
  }

  // Instanciar singleton global
  window.labBuilder = new TemplateBuilder();

  // Funciones globales de acceso rápido
  window.openTemplateBuilder = function(options) {
    window.labBuilder.openModal(options);
  };

  window.closeTemplateBuilder = function() {
    window.labBuilder.closeModal();
  };

  window.importTemplateFile = function() {
    window.labBuilder.triggerImportTemplate();
  };

})();
