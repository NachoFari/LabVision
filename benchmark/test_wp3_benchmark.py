"""
test_wp3_benchmark.py - Script de Verificación y Benchmarking de Work Package 3
LabVision Universal

Crea un video sintético de 300 fotogramas simulando una balanza de precisión:
- Cuadros 0 a 99 (100 cuadros): Balanza estática en 50.00 g
- Cuadros 100 a 199 (100 cuadros): Transición dinámica de masa 50.00 g -> 75.00 g
- Cuadros 200 a 299 (100 cuadros): Balanza estática en 75.00 g

Evalúa:
1. Rendimiento Baseline: OCR ejecutado en cada uno de los 300 fotogramas (sin filtro).
2. Rendimiento Optimizado: MotionDeltaFilter activado (umbral 1.5%), omitiendo cuadros estáticos.
3. Cálculo de métricas: Aceleración (Speedup factor), FPS efectivo, latencia promedio y exactitud de telemetría.
"""

import os
import sys
import time
import json
import cv2
import numpy as np

# Configuración de codificación UTF-8 para consola de Windows
try:
    if sys.stdout.encoding.lower() != 'utf-8':
        sys.stdout.reconfigure(encoding='utf-8', errors='replace')
except Exception:
    pass

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

from ocr_engine import LabVisionEngine
from core.batch_processor import BatchVideoProcessor, MotionDeltaFilter
from benchmark.generator import draw_balance_frame, get_font, FRAME_WIDTH, FRAME_HEIGHT

OUTPUT_DIR = os.path.join(BASE_DIR, "output")
os.makedirs(OUTPUT_DIR, exist_ok=True)
VIDEO_PATH = os.path.join(OUTPUT_DIR, "synthetic_scale_300frames.mp4")
RESULTS_JSON = os.path.join(OUTPUT_DIR, "wp3_benchmark_results.json")


def create_300frame_scale_video(video_path: str, fps: int = 30) -> list:
    """
    Genera el video sintético de 300 fotogramas con ground truth frame a frame.
    """
    print(f"[Synthetic Video] Generando video de 300 cuadros: {video_path}")
    font_large = get_font(font_type="sans", size=72, bold=True)
    font_small = get_font(font_type="sans", size=24, bold=True)

    fourcc = cv2.VideoWriter_fourcc(*'mp4v')
    out = cv2.VideoWriter(video_path, fourcc, float(fps), (FRAME_WIDTH, FRAME_HEIGHT))

    ground_truth = []

    # Segmento 1: 100 cuadros a 50.00 g (Estático)
    for i in range(100):
        frame_idx = i
        weight = 50.00
        frame_bgr = draw_balance_frame(weight, "g", font_large, font_small)
        out.write(frame_bgr)
        ground_truth.append({
            "frame_idx": frame_idx,
            "weight": weight,
            "phase": "static_50g"
        })

    # Segmento 2: 100 cuadros cambiando a 75.00 g (Dinámico)
    for i in range(100):
        frame_idx = 100 + i
        # Aumento continuo de 50.00 a 75.00
        alpha = (i + 1) / 100.0
        weight = round(50.00 + (75.00 - 50.00) * alpha, 2)
        frame_bgr = draw_balance_frame(weight, "g", font_large, font_small)
        out.write(frame_bgr)
        ground_truth.append({
            "frame_idx": frame_idx,
            "weight": weight,
            "phase": "transition_50_to_75g"
        })

    # Segmento 3: 100 cuadros a 75.00 g (Estático)
    for i in range(100):
        frame_idx = 200 + i
        weight = 75.00
        frame_bgr = draw_balance_frame(weight, "g", font_large, font_small)
        out.write(frame_bgr)
        ground_truth.append({
            "frame_idx": frame_idx,
            "weight": weight,
            "phase": "static_75g"
        })

    out.release()
    file_size_kb = os.path.getsize(video_path) / 1024.0
    print(f"[Synthetic Video] Video guardado con éxito. Tamaño: {file_size_kb:.1f} KB (300 cuadros a {fps} FPS).\n")
    return ground_truth


def run_benchmark():
    print("=" * 70)
    print("🔬 LABVISION UNIVERSAL - WORK PACKAGE 3 VERIFICATION BENCHMARK")
    print("=" * 70)

    # 1. Crear video sintético
    ground_truth = create_300frame_scale_video(VIDEO_PATH, fps=30)

    # Región de interés (ROI) designada en la pantalla de la balanza sobre el área de lectura
    # Dimensiones estándar del display en draw_balance_frame:
    # lx=55, ly=55, lw=530, lh=360. Texto principal centrado en x: 135..555, y: 170..310
    display_roi = [130, 170, 420, 140]

    # 2. Inicializar motor OCR compartido y realizar precalentamiento (warmup)
    print("[Benchmark] Inicializando motor EasyOCR y cargando pesos en memoria...")
    engine = LabVisionEngine()
    
    # Warmup
    warmup_frame = draw_balance_frame(50.00, "g", get_font("sans", 72, True), get_font("sans", 24, True))
    engine.process_frame(warmup_frame, roi=display_roi, mode="balance", unit="g")
    print("[Benchmark] Precalentamiento completado.\n")

    processor = BatchVideoProcessor(engine=engine)

    # -------------------------------------------------------------
    # PRUEBA 1: BASELINE (Sin MotionDeltaFilter, OCR en cada cuadro)
    # -------------------------------------------------------------
    print("-------------------------------------------------------------")
    print("▶ Ejecutando RUN 1: BASELINE (Sin Filtro Delta, OCR en 300 cuadros)")
    print("-------------------------------------------------------------")

    last_pct = -1
    def progress_cb_baseline(info):
        nonlocal last_pct
        pct = int(info["percent"])
        if pct % 20 == 0 and pct != last_pct:
            print(f"  [Baseline] Progreso: {info['percent']}% | Cuadro: {info['current_frame']}/{info['total_frames']} | FPS: {info['fps']:.1f} | ETA: {info['eta_sec']:.1f}s")
            last_pct = pct

    t0 = time.perf_counter()
    rows_baseline = processor.process_video(
        video_path=VIDEO_PATH,
        roi=display_roi,
        mode="balance",
        unit="g",
        stride=1,
        profile="normal",
        use_motion_filter=False,
        progress_callback=progress_cb_baseline
    )
    t1 = time.perf_counter()
    time_baseline = t1 - t0
    stats_baseline = processor.stats.copy()

    print(f"✔ RUN 1 Completado en {time_baseline:.2f} s | FPS efectivo: {stats_baseline['effective_fps']:.2f}")
    print(f"  Pases OCR ejecutados: {stats_baseline['ocr_passes_executed']} | Omitidos: {stats_baseline['ocr_passes_skipped']}\n")

    # -------------------------------------------------------------
    # PRUEBA 2: OPTIMIZADO (Con MotionDeltaFilter activado, umbral 1.5%)
    # -------------------------------------------------------------
    print("-------------------------------------------------------------")
    print("▶ Ejecutando RUN 2: OPTIMIZADO (Con MotionDeltaFilter @ 1.5% umbral)")
    print("-------------------------------------------------------------")

    last_pct = -1
    def progress_cb_filtered(info):
        nonlocal last_pct
        pct = int(info["percent"])
        if pct % 20 == 0 and pct != last_pct:
            print(f"  [Filtro Delta] Progreso: {info['percent']}% | Cuadro: {info['current_frame']}/{info['total_frames']} | FPS: {info['fps']:.1f} | ETA: {info['eta_sec']:.1f}s")
            last_pct = pct

    t2 = time.perf_counter()
    rows_filtered = processor.process_video(
        video_path=VIDEO_PATH,
        roi=display_roi,
        mode="balance",
        unit="g",
        stride=1,
        profile="normal",
        use_motion_filter=True,
        motion_threshold_pct=1.5,
        progress_callback=progress_cb_filtered
    )
    t3 = time.perf_counter()
    time_filtered = t3 - t2
    stats_filtered = processor.stats.copy()

    print(f"✔ RUN 2 Completado en {time_filtered:.2f} s | FPS efectivo: {stats_filtered['effective_fps']:.2f}")
    print(f"  Pases OCR ejecutados: {stats_filtered['ocr_passes_executed']} | Omitidos: {stats_filtered['ocr_passes_skipped']}")
    print(f"  Tasa de omisión de fotogramas estáticos: {stats_filtered['skip_ratio_pct']}%\n")

    # -------------------------------------------------------------
    # CÁLCULO DE ACELERACIÓN Y VERIFICACIÓN CIENTÍFICA
    # -------------------------------------------------------------
    speedup = time_baseline / max(0.001, time_filtered)
    latency_baseline_ms = (time_baseline / max(1, len(rows_baseline))) * 1000.0
    latency_filtered_ms = (time_filtered / max(1, len(rows_filtered))) * 1000.0

    # Verificación de exactitud contra Ground Truth
    # Cuadros estáticos iniciales (50.00 g)
    sample_50g = rows_filtered[50].get("weight")
    # Cuadros estáticos finales (75.00 g)
    sample_75g = rows_filtered[250].get("weight")
    # Cuadro en transición
    sample_trans = rows_filtered[150].get("weight")

    # Exportar resultados de telemetría a CSV y Excel
    csv_out = os.path.join(OUTPUT_DIR, "telemetry_wp3_benchmark.csv")
    excel_out = os.path.join(OUTPUT_DIR, "telemetry_wp3_benchmark.xlsx")
    processor.export_csv(csv_out, mode="balance", metadata={"unit": "g"})
    processor.export_excel(excel_out, mode="balance", metadata={"unit": "g"})

    results_data = {
        "benchmark_name": "LabVision WP3 MotionDeltaFilter vs Full OCR",
        "total_video_frames": 300,
        "baseline": {
            "total_time_sec": round(time_baseline, 3),
            "effective_fps": round(stats_baseline["effective_fps"], 2),
            "latency_ms_per_frame": round(latency_baseline_ms, 2),
            "ocr_passes_executed": stats_baseline["ocr_passes_executed"],
            "ocr_passes_skipped": stats_baseline["ocr_passes_skipped"]
        },
        "motion_delta_filtered": {
            "total_time_sec": round(time_filtered, 3),
            "effective_fps": round(stats_filtered["effective_fps"], 2),
            "latency_ms_per_frame": round(latency_filtered_ms, 2),
            "ocr_passes_executed": stats_filtered["ocr_passes_executed"],
            "ocr_passes_skipped": stats_filtered["ocr_passes_skipped"],
            "skip_ratio_pct": stats_filtered["skip_ratio_pct"]
        },
        "comparison": {
            "speedup_factor": round(speedup, 2),
            "time_saved_sec": round(time_baseline - time_filtered, 2),
            "reduction_in_ocr_passes_pct": round(
                (stats_filtered["ocr_passes_skipped"] / float(max(1, stats_baseline["ocr_passes_executed"]))) * 100.0, 1
            )
        },
        "scientific_integrity_check": {
            "reading_at_frame_50": sample_50g,
            "expected_at_frame_50": 50.00,
            "reading_at_frame_150": sample_trans,
            "expected_at_frame_150": 62.50,
            "reading_at_frame_250": sample_75g,
            "expected_at_frame_250": 75.00,
            "stable_phase_preserved": (sample_50g == 50.0 and sample_75g == 75.0)
        }
    }

    with open(RESULTS_JSON, "w", encoding="utf-8") as f:
        json.dump(results_data, f, indent=4, ensure_ascii=False)

    print("=" * 70)
    print("📊 RESULTADOS FINALES DE RENDIMIENTO (BENCHMARK SPEEDUP NUMBERS)")
    print("=" * 70)
    print(f"• Tiempo Baseline (Full OCR, 300 cuadros): {time_baseline:.2f} s ({stats_baseline['effective_fps']:.1f} FPS, {latency_baseline_ms:.1f} ms/cuadro)")
    print(f"• Tiempo con MotionDeltaFilter (1.5%):    {time_filtered:.2f} s ({stats_filtered['effective_fps']:.1f} FPS, {latency_filtered_ms:.1f} ms/cuadro)")
    print(f"• Factor de Aceleración (Speedup):        {speedup:.2f}x de velocidad")
    print(f"• Pases OCR omitidos:                     {stats_filtered['ocr_passes_skipped']} / 300 cuadros ({stats_filtered['skip_ratio_pct']}%)")
    print(f"• Integridad Científica (50g -> 75g):     {'APROBADO' if results_data['scientific_integrity_check']['stable_phase_preserved'] else 'REVISAR'}")
    print(f"• Reporte JSON:                           {RESULTS_JSON}")
    print(f"• Telemetría exportada en CSV:            {csv_out}")
    print(f"• Telemetría exportada en Excel:          {excel_out}")
    print("=" * 70)

    return results_data


if __name__ == "__main__":
    run_benchmark()
