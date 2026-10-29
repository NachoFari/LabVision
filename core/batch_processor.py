"""
batch_processor.py - Motor de Procesamiento por Lotes y Filtro Delta de Movimiento
LabVision Universal - Work Package 3

Componentes Clave:
1. MotionDeltaFilter:
   Filtro temporal de visión artificial basado en diferencia absoluta de píxeles (cv2.absdiff).
   Identifica fotogramas estáticos con una variación inferior al umbral (por defecto 1.5%),
   omitiendo la inferencia costosa de redes neuronales OCR y reutilizando los valores estables.

2. BatchVideoProcessor:
   Orquestador secuencial y multihilo para procesamiento eficiente de grabaciones de laboratorio,
   con soporte para submuestreo temporal (stride / sample_interval), cálculo dinámico de FPS,
   estimación de tiempo restante (ETA) y recolección de telemetría científica estructurada.
"""

import os
import sys
import copy
import time
import threading
from typing import Callable, Optional, Dict, Any, List, Tuple
import cv2
import numpy as np

# Resolución de rutas relativas con base estricta en BASE_DIR
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

from ocr_engine import LabVisionEngine
from exporters.csv_exporter import CSVExporter
from exporters.excel_exporter import ExcelExporter


class MotionDeltaFilter:
    """
    Filtro de Diferencia de Movimiento Cuadro a Cuadro (Motion Delta Filter).

    Calcula la variación pixel a pixel entre fotogramas consecutivos dentro del
    ROI de visualización (Display ROI) utilizando sustracción absoluta (cv2.absdiff).
    Si el porcentaje de cambio es inferior al umbral configurado (por defecto 1.5%),
    el fotograma se cataloga como estático/sin cambios ('is_static = True'), permitiendo
    omitir la costosa inferencia de la red neuronal OCR (CRAFT + ResNet/BiLSTM) y
    reutilizar los últimos valores estables válidos actualizando el timestamp,
    acelerando dramáticamente el rendimiento del pipeline de video.

    Parámetros Científicos:
    -----------------------
    threshold_pct : float
        Porcentaje máximo de píxeles alterados respecto al total del ROI para
        considerar el cuadro estático (default: 1.5%).
    pixel_diff_threshold : int
        Diferencia de intensidad mínima (0-255) en escala de grises para registrar
        un píxel como modificado. Filtra ruido de sensor CMOS y artefactos de compresión H.264.
    blur_kernel : tuple
        Núcleo para suavizado gaussiano previo al cálculo de delta (default: (3, 3)).
        Atenúa variaciones microscópicas de cuantización fotométrica.
    """

    def __init__(
        self,
        threshold_pct: float = 1.5,
        pixel_diff_threshold: int = 25,
        blur_kernel: Tuple[int, int] = (3, 3)
    ):
        self.threshold_pct = float(threshold_pct)
        self.pixel_diff_threshold = int(pixel_diff_threshold)
        self.blur_kernel = blur_kernel

        self.last_gray_roi: Optional[np.ndarray] = None
        self.last_stable_result: Optional[Dict[str, Any]] = None

        # Métricas operativas de telemetría
        self.total_evaluated: int = 0
        self.static_count: int = 0
        self.dynamic_count: int = 0

    def reset(self) -> None:
        """Reinicia el estado del filtro y vacía el búfer de fotogramas anteriores."""
        self.last_gray_roi = None
        self.last_stable_result = None
        self.total_evaluated = 0
        self.static_count = 0
        self.dynamic_count = 0

    def calculate_delta(self, roi_frame: np.ndarray) -> Tuple[float, Optional[np.ndarray]]:
        """
        Calcula la diferencia absoluta (absdiff) contra el cuadro previo en escala de grises.

        Retorna:
            change_pct: Porcentaje (0.0 a 100.0) de píxeles que cambiaron.
            diff_map: Matriz 2D de diferencias de píxeles, o None en el primer fotograma.
        """
        if roi_frame is None or roi_frame.size == 0:
            return 100.0, None

        # Conversión defensiva a escala de grises
        if len(roi_frame.shape) == 3 and roi_frame.shape[2] == 3:
            gray = cv2.cvtColor(roi_frame, cv2.COLOR_BGR2GRAY)
        elif len(roi_frame.shape) == 2:
            gray = roi_frame
        else:
            return 100.0, None

        # Filtrado de ruido gaussiano
        if self.blur_kernel and self.blur_kernel[0] > 1:
            try:
                gray = cv2.GaussianBlur(gray, self.blur_kernel, 0)
            except Exception:
                pass

        # Primer fotograma de la serie: no hay referencia anterior
        if self.last_gray_roi is None or self.last_gray_roi.shape != gray.shape:
            self.last_gray_roi = gray.copy()
            return 100.0, None

        # Cálculo de diferencia absoluta entre cuadros
        delta = cv2.absdiff(self.last_gray_roi, gray)

        # Contar píxeles que superan el umbral de ruido fotométrico
        changed_pixels = int(np.count_nonzero(delta > self.pixel_diff_threshold))
        total_pixels = max(1, delta.size)
        change_pct = (changed_pixels / float(total_pixels)) * 100.0

        # Actualizar referencia temporal
        self.last_gray_roi = gray.copy()

        return float(change_pct), delta

    def is_static(
        self,
        roi_frame: np.ndarray,
        threshold_pct: Optional[float] = None
    ) -> Tuple[bool, float]:
        """
        Determina si el fotograma actual es estático según el umbral configurado.

        Retorna:
            (is_static, change_pct)
        """
        eff_threshold = threshold_pct if threshold_pct is not None else self.threshold_pct
        change_pct, _ = self.calculate_delta(roi_frame)

        self.total_evaluated += 1
        is_static_frame = (change_pct < eff_threshold)

        if is_static_frame:
            self.static_count += 1
        else:
            self.dynamic_count += 1

        return is_static_frame, change_pct

    def update_stable_result(self, parsed: Dict[str, Any]) -> None:
        """Almacena el último resultado OCR confiable obtenido en un cuadro dinámico."""
        if parsed and isinstance(parsed, dict):
            self.last_stable_result = copy.deepcopy(parsed)

    def get_stable_result(self) -> Optional[Dict[str, Any]]:
        """Retorna una copia del último resultado estable almacenado."""
        if self.last_stable_result is not None:
            return copy.deepcopy(self.last_stable_result)
        return None

    def get_metrics(self) -> Dict[str, Any]:
        """Retorna estadísticas del comportamiento del filtro."""
        skip_ratio = (self.static_count / float(max(1, self.total_evaluated))) * 100.0
        return {
            "total_evaluated": self.total_evaluated,
            "static_frames": self.static_count,
            "dynamic_frames": self.dynamic_count,
            "skip_ratio_pct": round(skip_ratio, 2)
        }


class BatchVideoProcessor:
    """
    Procesador de Video por Lotes de Alto Rendimiento (Batch Video Processor).

    Gestiona la ejecución por lotes de videos científicos con:
    - Soporte de submuestreo temporal (stride por cuadros o sample_interval en segundos).
    - Integración nativa con MotionDeltaFilter para omisión inteligente de inferencias repetidas.
    - Retroalimentación en tiempo real: { current_frame, total_frames, percent, fps, eta_sec }.
    - Recolección y exportación estructurada a CSV y Excel (.xlsx).
    - Arquitectura tolerante a fallos y cancelación en segundo plano (multithreading).
    """

    def __init__(
        self,
        engine: Optional[LabVisionEngine] = None,
        delta_filter: Optional[MotionDeltaFilter] = None
    ):
        self._engine = engine
        self._delta_filter = delta_filter if delta_filter is not None else MotionDeltaFilter()

        # Primitivas de sincronización y multithreading
        self._stop_event = threading.Event()
        self._is_running = False
        self._worker_thread: Optional[threading.Thread] = None

        # Almacenamiento de telemetría y estado
        self.telemetry_rows: List[Dict[str, Any]] = []
        self.last_progress: Dict[str, Any] = {
            "current_frame": 0,
            "total_frames": 0,
            "percent": 0.0,
            "fps": 0.0,
            "eta_sec": 0.0
        }
        self.stats: Dict[str, Any] = {}

    def _ensure_engine(self) -> LabVisionEngine:
        """Garantiza la inicialización perezosa (lazy) del motor OCR."""
        if self._engine is None:
            self._engine = LabVisionEngine()
        return self._engine

    @staticmethod
    def crop_roi(frame: np.ndarray, roi: Optional[List[int]]) -> np.ndarray:
        """Recorta con seguridad defensiva la región de interés (ROI) del fotograma."""
        if frame is None or frame.size == 0:
            return frame
        if not roi or len(roi) != 4:
            return frame

        x, y, w, h = [int(v) for v in roi]
        h_max, w_max = frame.shape[:2]

        x = max(0, min(x, w_max - 1))
        y = max(0, min(y, h_max - 1))
        w = max(1, min(w, w_max - x))
        h = max(1, min(h, h_max - y))

        return frame[y:y+h, x:x+w]

    def process_video(
        self,
        video_path: str,
        roi: Optional[List[int]] = None,
        mode: str = "balance",
        unit: str = "g",
        sample_interval: Optional[float] = None,
        stride: int = 1,
        profile: str = "normal",
        min_confidence: float = 0.45,
        use_motion_filter: bool = True,
        motion_threshold_pct: float = 1.5,
        progress_callback: Optional[Callable[[Dict[str, Any]], None]] = None,
        frame_callback: Optional[Callable[[Dict[str, Any]], None]] = None
    ) -> List[Dict[str, Any]]:
        """
        Ejecuta el procesamiento secuencial del video aplicando filtrado delta y OCR.

        Parámetros:
        -----------
        video_path : str
            Ruta al archivo de video (compatible con rutas absolutas o relativas a BASE_DIR).
        roi : list [x, y, w, h]
            Coordenadas de la región de visualización de la pantalla a procesar.
        mode : str
            Instrumento ('balance' o 'viscometer').
        unit : str
            Unidad de medida esperada (ej. 'g', 'kg', 'mPa.s').
        sample_interval : float, optional
            Intervalo de muestreo en segundos (ej. 0.5s, 1.0s). Si se omite, usa `stride`.
        stride : int
            Intervalo de salto por fotogramas (ej. 1 = todos los cuadros).
        profile : str
            Perfil de preprocesamiento ('low', 'normal', 'high').
        min_confidence : float
            Umbral mínimo de certeza del OCR (0.0 a 1.0).
        use_motion_filter : bool
            Activa o desactiva la omisión de cuadros estáticos con MotionDeltaFilter.
        motion_threshold_pct : float
            Umbral de porcentaje de cambio delta para MotionDeltaFilter (default 1.5%).
        progress_callback : callable
            Función receptora de progreso: callback({ current_frame, total_frames, percent, fps, eta_sec }).
        frame_callback : callable
            Función receptora de cada fila de telemetría extraída.

        Retorna:
        --------
        telemetry_rows : list[dict]
            Lista completa de filas de telemetría extraídas.
        """
        # Resolución defensiva de la ruta del video
        resolved_path = video_path if os.path.isabs(video_path) else os.path.normpath(os.path.join(BASE_DIR, video_path))
        if not os.path.exists(resolved_path):
            raise FileNotFoundError(f"[BatchVideoProcessor] Video no encontrado: {resolved_path}")

        cap = cv2.VideoCapture(resolved_path)
        if not cap.isOpened():
            raise RuntimeError(f"[BatchVideoProcessor] No se pudo abrir el archivo de video: {resolved_path}")

        # Extracción segura de propiedades del video
        total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
        fps = float(cap.get(cv2.CAP_PROP_FPS) or 30.0)
        if fps <= 0.0 or np.isnan(fps):
            fps = 30.0

        # Determinación del paso de muestreo (stride)
        if sample_interval is not None and sample_interval > 0:
            effective_stride = max(1, int(round(fps * sample_interval)))
        else:
            effective_stride = max(1, int(stride))

        target_indices = list(range(0, total_frames, effective_stride)) if total_frames > 0 else []
        total_target_frames = len(target_indices)

        engine = self._ensure_engine()
        self._delta_filter.reset()
        self._delta_filter.threshold_pct = motion_threshold_pct

        self.telemetry_rows = []
        self._stop_event.clear()
        self._is_running = True

        start_time = time.perf_counter()
        ocr_passes_executed = 0
        ocr_passes_skipped = 0

        try:
            for idx_step, frame_idx in enumerate(target_indices):
                if self._stop_event.is_set():
                    break

                # Posicionamiento del lector de video
                if effective_stride == 1 and idx_step == frame_idx:
                    ret, frame = cap.read()
                else:
                    cap.set(cv2.CAP_PROP_POS_FRAMES, frame_idx)
                    ret, frame = cap.read()

                if not ret or frame is None:
                    break

                current_second = frame_idx / fps
                m, s = divmod(int(current_second), 60)
                h, m = divmod(m, 60)
                ts_str = f"{h:02d}:{m:02d}:{s:02d}"

                # Aislamiento del ROI
                roi_crop = self.crop_roi(frame, roi)

                # Evaluación con MotionDeltaFilter
                is_static_frame, change_pct = self._delta_filter.is_static(roi_crop)
                last_stable = self._delta_filter.get_stable_result()

                # Decisión de inferencia OCR vs reutilización de cuadro estático
                if use_motion_filter and is_static_frame and last_stable is not None:
                    # Omitir inferencia OCR costosa: reutilizar estado estable
                    row = copy.deepcopy(last_stable)
                    row["frame_idx"] = frame_idx
                    row["time_sec"] = round(current_second, 3)
                    row["timestamp_str"] = ts_str
                    row["is_static"] = True
                    row["motion_delta_pct"] = round(change_pct, 3)
                    row["skipped_ocr"] = True
                    ocr_passes_skipped += 1
                else:
                    # Ejecutar inferencia de red neuronal EasyOCR
                    parsed, _ = engine.process_frame(
                        frame,
                        roi=roi,
                        mode=mode,
                        unit=unit,
                        min_confidence=min_confidence,
                        profile=profile
                    )
                    row = copy.deepcopy(parsed)
                    row["frame_idx"] = frame_idx
                    row["time_sec"] = round(current_second, 3)
                    row["timestamp_str"] = ts_str
                    row["is_static"] = False
                    row["motion_delta_pct"] = round(change_pct, 3)
                    row["skipped_ocr"] = False
                    ocr_passes_executed += 1

                    # Actualizar valor estable de referencia si la lectura no es inválida
                    if not parsed.get("is_bad", False) or last_stable is None:
                        self._delta_filter.update_stable_result(parsed)

                self.telemetry_rows.append(row)

                # Cálculo defensivo de rendimiento y ETA
                elapsed = time.perf_counter() - start_time
                frames_done = len(self.telemetry_rows)
                current_fps = (frames_done / elapsed) if elapsed > 0 else 0.0
                remaining = max(0, total_target_frames - frames_done)
                eta_sec = (remaining / current_fps) if current_fps > 0 else 0.0
                percent = min(100.0, (frames_done / max(1, total_target_frames)) * 100.0)

                self.last_progress = {
                    "current_frame": frame_idx,
                    "total_frames": total_frames,
                    "percent": round(percent, 1),
                    "fps": round(current_fps, 2),
                    "eta_sec": round(eta_sec, 1)
                }

                if progress_callback:
                    try:
                        progress_callback(self.last_progress)
                    except Exception as e_cb:
                        print(f"[BatchVideoProcessor] Advertencia en progress_callback: {e_cb}")

                if frame_callback:
                    try:
                        frame_callback(row)
                    except Exception as e_fcb:
                        print(f"[BatchVideoProcessor] Advertencia en frame_callback: {e_fcb}")

        finally:
            cap.release()
            self._is_running = False

        total_time = time.perf_counter() - start_time
        avg_fps = (len(self.telemetry_rows) / total_time) if total_time > 0 else 0.0

        self.stats = {
            "total_frames_target": total_target_frames,
            "processed_frames": len(self.telemetry_rows),
            "ocr_passes_executed": ocr_passes_executed,
            "ocr_passes_skipped": ocr_passes_skipped,
            "skip_ratio_pct": round((ocr_passes_skipped / max(1, len(self.telemetry_rows))) * 100.0, 2),
            "total_time_sec": round(total_time, 3),
            "effective_fps": round(avg_fps, 2)
        }

        return self.telemetry_rows

    def start_async(
        self,
        video_path: str,
        roi: Optional[List[int]] = None,
        mode: str = "balance",
        unit: str = "g",
        sample_interval: Optional[float] = None,
        stride: int = 1,
        profile: str = "normal",
        min_confidence: float = 0.45,
        use_motion_filter: bool = True,
        motion_threshold_pct: float = 1.5,
        progress_callback: Optional[Callable[[Dict[str, Any]], None]] = None,
        frame_callback: Optional[Callable[[Dict[str, Any]], None]] = None,
        completion_callback: Optional[Callable[[List[Dict[str, Any]]], None]] = None
    ) -> threading.Thread:
        """Inicia el procesamiento por lotes en un hilo daemon en segundo plano."""
        if self._is_running:
            raise RuntimeError("[BatchVideoProcessor] Ya hay un procesamiento en curso.")

        def _worker():
            results = self.process_video(
                video_path=video_path,
                roi=roi,
                mode=mode,
                unit=unit,
                sample_interval=sample_interval,
                stride=stride,
                profile=profile,
                min_confidence=min_confidence,
                use_motion_filter=use_motion_filter,
                motion_threshold_pct=motion_threshold_pct,
                progress_callback=progress_callback,
                frame_callback=frame_callback
            )
            if completion_callback:
                try:
                    completion_callback(results)
                except Exception as e_comp:
                    print(f"[BatchVideoProcessor] Error en completion_callback: {e_comp}")

        self._worker_thread = threading.Thread(target=_worker, daemon=True)
        self._worker_thread.start()
        return self._worker_thread

    def stop(self) -> None:
        """Solicita la interrupción limpia del hilo de procesamiento."""
        self._stop_event.set()

    def is_running(self) -> bool:
        """Retorna True si hay un procesamiento activo en segundo plano."""
        return self._is_running

    def wait_completion(self, timeout: Optional[float] = None) -> None:
        """Espera defensivamente a que el hilo de procesamiento finalice."""
        if self._worker_thread and self._worker_thread.is_alive():
            self._worker_thread.join(timeout=timeout)

    def export_csv(
        self,
        output_path: str,
        mode: str = "balance",
        metadata: Optional[Dict[str, Any]] = None
    ) -> str:
        """Exporta las filas de telemetría recopiladas a un archivo CSV."""
        resolved = output_path if os.path.isabs(output_path) else os.path.normpath(os.path.join(BASE_DIR, output_path))
        return CSVExporter.export(self.telemetry_rows, resolved, mode=mode, metadata=metadata)

    def export_excel(
        self,
        output_path: str,
        mode: str = "balance",
        metadata: Optional[Dict[str, Any]] = None
    ) -> str:
        """Exporta las filas de telemetría recopiladas a un libro Excel (.xlsx)."""
        resolved = output_path if os.path.isabs(output_path) else os.path.normpath(os.path.join(BASE_DIR, output_path))
        return ExcelExporter.export(self.telemetry_rows, resolved, mode=mode, metadata=metadata)
