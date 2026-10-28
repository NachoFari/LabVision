r"""
suite.py - Suite de Benchmarking de Alto Rendimiento para LabVision Pro
Evalúa el rendimiento de OCR y extracción de datos en:
- Viscosímetro Rotacional NDJ-8S
- Balanza / Gramera Digital

Pruebas ejecutadas:
- Modo Aceleración GPU vs Modo CPU Forzado
- Perfiles de preprocesamiento: 'low', 'normal', 'high'
- Métricas: Latencia (ms/cuadro), Throughput (FPS), Tasa de acierto (%)

Resultados exportados en:
- JSON: output\benchmark_results.json
- Tabla comparativa en Markdown impresa por consola
"""

import os
import sys
import time
import json
import cv2
import numpy as np

# Configurar salida UTF-8 en consola de Windows
try:
    if sys.stdout.encoding.lower() != 'utf-8':
        sys.stdout.reconfigure(encoding='utf-8', errors='replace')
except Exception:
    pass

PROJECT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if PROJECT_DIR not in sys.path:
    sys.path.insert(0, PROJECT_DIR)

from ocr_engine import LabVisionEngine
from benchmark.generator import generate_viscometer_video, generate_balance_video

OUTPUT_DIR = os.path.join(PROJECT_DIR, "output")
JSON_RESULTS_PATH = os.path.join(OUTPUT_DIR, "benchmark_results.json")
VISCOMETER_VIDEO_PATH = os.path.join(OUTPUT_DIR, "benchmark_viscometer.mp4")
BALANCE_VIDEO_PATH = os.path.join(OUTPUT_DIR, "benchmark_balance.mp4")

def evaluate_run(engine: LabVisionEngine, video_path: str, ground_truth: list,
                 frames_to_test: list, mode: str = "viscometer",
                 profile: str = "normal", unit: str = "g") -> dict:
    """
    Ejecuta un ciclo de evaluación en el video para un conjunto de fotogramas,
    midiendo latencia de inferencia y verificando precisión contra el Ground Truth.
    """
    cap = cv2.VideoCapture(video_path)
    if not cap.isOpened():
        raise RuntimeError(f"No se pudo abrir el archivo de video: {video_path}")

    # 1. Warmup (precalentamiento de buffers y grafos de inferencia)
    ret, warmup_frame = cap.read()
    if ret:
        engine.process_frame(warmup_frame, mode=mode, unit=unit, profile=profile)

    latencies_ms = []
    hits = 0
    details = []

    for idx, frame_no in enumerate(frames_to_test):
        cap.set(cv2.CAP_PROP_POS_FRAMES, frame_no)
        ret, frame = cap.read()
        if not ret:
            continue

        gt = ground_truth[frame_no]

        t0 = time.perf_counter()
        parsed, _ = engine.process_frame(frame, mode=mode, unit=unit, profile=profile)
        t1 = time.perf_counter()

        lat_ms = (t1 - t0) * 1000.0
        latencies_ms.append(lat_ms)

        # Verificación de exactitud contra Ground Truth
        is_hit = False
        if mode == "viscometer":
            rotor_ok = (parsed.get("rotor") == gt.get("rotor"))
            speed_ok = (parsed.get("speed_rpm") == gt.get("speed_rpm"))
            
            visc_ok = False
            if parsed.get("viscosity_mpa") is not None:
                visc_ok = abs(parsed["viscosity_mpa"] - gt["viscosity_mpa"]) <= 1.5

            pct_ok = False
            if parsed.get("torque_pct") is not None:
                pct_ok = abs(parsed["torque_pct"] - gt["torque_pct"]) <= 0.8

            not_bad = not parsed.get("is_bad", True)
            is_hit = (rotor_ok and speed_ok and visc_ok and pct_ok and not_bad)

        else: # balance
            weight_ok = False
            if parsed.get("weight") is not None:
                weight_ok = abs(parsed["weight"] - gt["weight"]) <= 0.05

            unit_ok = (parsed.get("unit") == gt.get("unit"))
            not_bad = not parsed.get("is_bad", True)
            is_hit = (weight_ok and unit_ok and not_bad)

        if is_hit:
            hits += 1

        details.append({
            "frame_no": frame_no,
            "latency_ms": round(lat_ms, 2),
            "is_hit": is_hit,
            "confidence": parsed.get("confidence", 0.0),
            "ocr_output": parsed,
            "ground_truth": gt
        })

    cap.release()

    total_tested = len(latencies_ms)
    avg_latency = float(np.mean(latencies_ms)) if latencies_ms else 0.0
    min_latency = float(np.min(latencies_ms)) if latencies_ms else 0.0
    max_latency = float(np.max(latencies_ms)) if latencies_ms else 0.0
    accuracy_pct = (hits / total_tested * 100.0) if total_tested > 0 else 0.0
    fps = (1000.0 / avg_latency) if avg_latency > 0 else 0.0

    return {
        "mode": mode,
        "profile": profile,
        "total_tested": total_tested,
        "hits": hits,
        "accuracy_pct": round(accuracy_pct, 2),
        "avg_latency_ms": round(avg_latency, 2),
        "min_latency_ms": round(min_latency, 2),
        "max_latency_ms": round(max_latency, 2),
        "fps": round(fps, 2),
        "details": details
    }

def format_markdown_table(benchmark_runs: list) -> str:
    """
    Construye una tabla formateada en Markdown con todas las pruebas y métricas.
    """
    lines = []
    lines.append("| Instrumento | Hardware | Perfil | Latencia Promedio (ms) | Rango (Min - Max) | FPS | Acierto (%) | Estado |")
    lines.append("| :--- | :--- | :---: | :---: | :---: | :---: | :---: | :---: |")

    for run in benchmark_runs:
        inst_label = "Viscosímetro NDJ-8S" if run["mode"] == "viscometer" else "Balanza / Gramera"
        hw_label = run["device_label"]
        prof_label = run["profile"].capitalize()
        lat_avg = f"{run['avg_latency_ms']:.1f} ms"
        lat_range = f"{run['min_latency_ms']:.1f} - {run['max_latency_ms']:.1f} ms"
        fps_val = f"{run['fps']:.2f}"
        acc_val = f"{run['accuracy_pct']:.1f}% ({run['hits']}/{run['total_tested']})"
        status = "🟢 ÓPTIMO" if run["accuracy_pct"] >= 95.0 else ("🟡 ACEPTABLE" if run["accuracy_pct"] >= 75.0 else "🔴 MEJORABLE")

        lines.append(f"| {inst_label} | {hw_label} | {prof_label} | {lat_avg} | {lat_range} | {fps_val} | {acc_val} | {status} |")

    return "\n".join(lines)

def run_benchmark_suite(sample_gpu_count: int = 15, sample_cpu_count: int = 4):
    """
    Ejecuta el benchmark completo:
    - 2 Instrumentos: Viscosímetro y Balanza
    - 2 Dispositivos: GPU (CUDA) y CPU Forzado
    - 3 Perfiles: 'low', 'normal', 'high'
    Total: 12 combinaciones de prueba.
    """
    os.makedirs(OUTPUT_DIR, exist_ok=True)

    print("\n" + "="*80)
    print("          LABVISION PRO - SUITE DE BENCHMARKING DE HARDWARE Y PERFILES")
    print("="*80)

    # 1. Asegurar generación de videos sintéticos
    print("\n[Paso 1/3] Verificando videos sintéticos de prueba...")
    gt_viscometer = generate_viscometer_video(VISCOMETER_VIDEO_PATH, duration_sec=6, fps=10)
    gt_balance = generate_balance_video(BALANCE_VIDEO_PATH, duration_sec=6, fps=10, unit='g')

    total_frames_v = len(gt_viscometer)
    total_frames_b = len(gt_balance)

    # Selección uniforme de cuadros
    # GPU: muestra estadística de 15 cuadros representativos
    gpu_frames_v = [int(i) for i in np.linspace(0, total_frames_v - 1, sample_gpu_count)]
    gpu_frames_b = [int(i) for i in np.linspace(0, total_frames_b - 1, sample_gpu_count)]

    # CPU: muestra de 4 cuadros estratégicos para benchmarking preciso y rápido
    cpu_frames_v = [int(i) for i in np.linspace(0, total_frames_v - 1, sample_cpu_count)]
    cpu_frames_b = [int(i) for i in np.linspace(0, total_frames_b - 1, sample_cpu_count)]

    # 2. Inicialización de Motores
    print("\n[Paso 2/3] Inicializando motores OCR para GPU y CPU...")
    has_gpu = LabVisionEngine(force_cpu=False).has_gpu
    
    engines = []
    if has_gpu:
        eng_gpu = LabVisionEngine(force_cpu=False)
        engines.append({
            "engine": eng_gpu,
            "device_key": "gpu",
            "device_label": "GPU (CUDA)",
            "frames_v": gpu_frames_v,
            "frames_b": gpu_frames_b
        })
    else:
        print("[Aviso] No se detectó GPU CUDA en este entorno. Las pruebas se realizarán en CPU.")

    eng_cpu = LabVisionEngine(force_cpu=True)
    engines.append({
        "engine": eng_cpu,
        "device_key": "cpu",
        "device_label": "CPU (Notebook)",
        "frames_v": cpu_frames_v,
        "frames_b": cpu_frames_b
    })

    profiles = ["low", "normal", "high"]
    instruments = [
        {"mode": "viscometer", "video_path": VISCOMETER_VIDEO_PATH, "gt": gt_viscometer, "unit": "g"},
        {"mode": "balance", "video_path": BALANCE_VIDEO_PATH, "gt": gt_balance, "unit": "g"}
    ]

    all_results = []
    total_combinations = len(engines) * len(instruments) * len(profiles)
    current_test = 0

    print(f"\n[Paso 3/3] Ejecutando {total_combinations} configuraciones de prueba...\n")

    for eng_info in engines:
        engine = eng_info["engine"]
        dev_label = eng_info["device_label"]

        for inst in instruments:
            mode = inst["mode"]
            inst_name = "Viscosímetro NDJ-8S" if mode == "viscometer" else "Balanza / Gramera"
            video_path = inst["video_path"]
            gt = inst["gt"]
            unit = inst["unit"]
            frames_to_test = eng_info["frames_v"] if mode == "viscometer" else eng_info["frames_b"]

            for prof in profiles:
                current_test += 1
                print(f"  [{current_test}/{total_combinations}] Testeando: {inst_name:<20} | {dev_label:<16} | Perfil: {prof:<6}...", end="", flush=True)

                eval_data = evaluate_run(
                    engine=engine,
                    video_path=video_path,
                    ground_truth=gt,
                    frames_to_test=frames_to_test,
                    mode=mode,
                    profile=prof,
                    unit=unit
                )

                eval_data["device_key"] = eng_info["device_key"]
                eval_data["device_label"] = dev_label
                eval_data["hardware_desc"] = engine.hardware_desc
                all_results.append(eval_data)

                print(f" -> Latencia: {eval_data['avg_latency_ms']:>6.1f} ms | FPS: {eval_data['fps']:>5.2f} | Acierto: {eval_data['accuracy_pct']:>5.1f}%")

    # 3. Resumen y Análisis Comparativo
    markdown_table = format_markdown_table(all_results)

    # Calcular aceleración promedio GPU vs CPU si GPU está presente
    speedup_summary = {}
    if has_gpu:
        for mode in ["viscometer", "balance"]:
            for prof in profiles:
                gpu_res = next((r for r in all_results if r["mode"] == mode and r["profile"] == prof and r["device_key"] == "gpu"), None)
                cpu_res = next((r for r in all_results if r["mode"] == mode and r["profile"] == prof and r["device_key"] == "cpu"), None)
                if gpu_res and cpu_res and gpu_res["avg_latency_ms"] > 0:
                    factor = round(cpu_res["avg_latency_ms"] / gpu_res["avg_latency_ms"], 1)
                    speedup_summary[f"{mode}_{prof}"] = factor

    # Guardar archivo JSON
    system_hw = engines[0]["engine"].get_hardware_info()
    json_payload = {
        "benchmark_timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
        "system_info": {
            "hardware_desc": system_hw.get("description"),
            "has_gpu": has_gpu,
            "torch_version": system_hw.get("torch_version"),
            "cpu_cores": os.cpu_count()
        },
        "test_parameters": {
            "sample_gpu_frames": sample_gpu_count,
            "sample_cpu_frames": sample_cpu_count,
            "profiles_tested": profiles,
            "instruments_tested": ["viscometer", "balance"]
        },
        "speedup_gpu_vs_cpu": speedup_summary,
        "results": all_results
    }

    with open(JSON_RESULTS_PATH, "w", encoding="utf-8") as f:
        json.dump(json_payload, f, indent=2, ensure_ascii=False)

    print(f"\n[Suite] Resultados guardados en: {JSON_RESULTS_PATH}")

    # 4. Imprimir Reporte en Formato Markdown
    print("\n" + "="*80)
    print("                TABLA COMPARATIVA DE RENDIMIENTO (MARKDOWN)")
    print("="*80)
    print(markdown_table)
    print("="*80)

    if speedup_summary:
        print("\n⚡ FACTORES DE ACELERACIÓN GPU:")
        for k, factor in speedup_summary.items():
            print(f"  • {k}: {factor}x más rápido con GPU")
    print("\n")

    return json_payload, markdown_table

if __name__ == "__main__":
    run_benchmark_suite()
