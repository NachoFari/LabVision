import os
import sys
import cv2
import json
import time
import base64
import threading
import subprocess
import webview

# Importaciones modulares limpias
from ocr_engine import LabVisionEngine
from notifications.discord import DiscordNotifier
from config.manager import ConfigManager

class LabVisionAPI:
    def __init__(self):
        self.config = ConfigManager.load()
        self.notifier = DiscordNotifier(self.config.get("discord_webhook", ""))
        self.engine = LabVisionEngine()
        self.window = None

        # Estado del procesamiento
        self.is_processing = False
        self.cancel_requested = False
        self.processing_thread = None
        self.last_all_data_rows = []
        
        self.current_state = {
            "is_running": False,
            "progress_pct": 0,
            "current_time_str": "00:00:00",
            "current_reading": None,
            "quality_alert": False,
            "alert_message": "",
            "rows_extracted": 0,
            "last_row": None,
            "recent_rows": [],
            "excel_file": None,
            "csv_file": None,
            "error_msg": None
        }

    def set_window(self, window):
        self.window = window

    def get_system_info(self):
        hw = self.engine.get_hardware_info()
        return {
            "hardware": hw,
            "config": self.config
        }

    def save_settings(self, new_config):
        self.config.update(new_config)
        ConfigManager.save(self.config)
        if "discord_webhook" in new_config:
            self.notifier.set_webhook(new_config["discord_webhook"])
        return {"success": True}

    def test_discord(self, webhook_url):
        ok, msg = self.notifier.send_test(webhook_url)
        return {"success": ok, "message": msg}

    def list_cameras(self):
        """Busca cámaras web o capturadoras USB conectadas (índices 0, 1, 2)."""
        if self.is_processing:
            return [{"index": 0, "name": "Cámara activa en extracción"}]
        available = []
        for i in range(3):
            cap = cv2.VideoCapture(i, cv2.CAP_DSHOW if sys.platform == 'win32' else cv2.CAP_ANY)
            if cap.isOpened():
                ret, _ = cap.read()
                if ret:
                    available.append({"index": i, "name": f"Cámara USB / Webcam #{i}"})
                cap.release()
        if not available:
            available.append({"index": 0, "name": "Cámara por defecto (0)"})
        return available

    def select_video_dialog(self):
        """Abre un diálogo nativo de Windows para seleccionar video."""
        if not self.window:
            return None
        file_types = ('Archivos de Video (*.mp4;*.avi;*.mov;*.mkv;*.wmv)', 'Todos los archivos (*.*)')
        result = self.window.create_file_dialog(webview.OPEN_DIALOG, allow_multiple=False, file_types=file_types)
        if result and len(result) > 0:
            return result[0]
        return None

    def get_video_frame(self, source, frame_second=0.5):
        """
        Extrae un fotograma del video o de la cámara para que el usuario
        pueda dibujar el recuadro (ROI) en el canvas.
        """
        if self.is_processing:
            return {"error": "Extracción en curso. No se puede capturar otro fotograma simultáneamente."}

        is_cam = isinstance(source, int) or str(source).isdigit()
        src_val = int(source) if is_cam else source

        cap = cv2.VideoCapture(src_val, cv2.CAP_DSHOW if is_cam and sys.platform == 'win32' else cv2.CAP_ANY)
        if not cap.isOpened():
            return {"error": f"No se pudo abrir la fuente: {source}"}

        if not is_cam and frame_second > 0:
            fps = cap.get(cv2.CAP_PROP_FPS) or 30.0
            cap.set(cv2.CAP_PROP_POS_FRAMES, int(fps * frame_second))

        ret, frame = cap.read()
        cap.release()

        if not ret or frame is None:
            return {"error": "No se pudo leer el cuadro del video"}

        h, w = frame.shape[:2]
        max_dim = 1280
        if max(h, w) > max_dim:
            scale = max_dim / float(max(h, w))
            frame_preview = cv2.resize(frame, (int(w * scale), int(h * scale)))
        else:
            frame_preview = frame

        # Detectar automáticamente si hay pantalla azul presente (sugerencia de ROI)
        suggested_box = self.engine.detect_screen_auto(frame, mode="viscometer")

        _, buffer = cv2.imencode('.jpg', frame_preview, [cv2.IMWRITE_JPEG_QUALITY, 85])
        jpg_as_text = base64.b64encode(buffer).decode('utf-8')

        return {
            "success": True,
            "width": w,
            "height": h,
            "preview_width": frame_preview.shape[1],
            "preview_height": frame_preview.shape[0],
            "image_base64": f"data:image/jpeg;base64,{jpg_as_text}",
            "suggested_roi": suggested_box
        }

    def calibrate_camera(self, source, roi=None):
        """Ejecuta diagnóstico de nitidez, enfoque y reflejos en la cámara."""
        if self.is_processing:
            return {"error": "Extracción en curso. No se puede ejecutar calibración simultáneamente."}

        is_cam = isinstance(source, int) or str(source).isdigit()
        src_val = int(source) if is_cam else source

        cap = cv2.VideoCapture(src_val, cv2.CAP_DSHOW if is_cam and sys.platform == 'win32' else cv2.CAP_ANY)
        if not cap.isOpened():
            return {"error": "No se pudo acceder a la cámara o video"}

        if not is_cam:
            fps = cap.get(cv2.CAP_PROP_FPS) or 30.0
            cap.set(cv2.CAP_PROP_POS_FRAMES, int(fps * 0.5))

        ret, frame = cap.read()
        cap.release()

        if not ret or frame is None:
            return {"error": "No se pudo capturar imagen para calibrar"}

        eval_result = self.engine.calibrate_frame(frame, roi=roi)
        return {"success": True, "evaluation": eval_result}

    def test_roi_reading(self, source, roi, mode, unit="g", profile="normal", auto_track=False):
        """Ejecuta una prueba instantánea sobre el recuadro seleccionado."""
        if self.is_processing:
            return {"error": "Extracción en curso. No se puede probar encuadre simultáneamente."}

        is_cam = isinstance(source, int) or str(source).isdigit()
        src_val = int(source) if is_cam else source

        cap = cv2.VideoCapture(src_val, cv2.CAP_DSHOW if is_cam and sys.platform == 'win32' else cv2.CAP_ANY)
        if not cap.isOpened():
            return {"error": "No se pudo acceder a la fuente de video"}

        if not is_cam:
            fps = cap.get(cv2.CAP_PROP_FPS) or 30.0
            cap.set(cv2.CAP_PROP_POS_FRAMES, int(fps * 0.5))

        ret, frame = cap.read()
        cap.release()

        if not ret or frame is None:
            return {"error": "Error al capturar fotograma"}

        parsed, crop = self.engine.process_frame(
            frame, roi=roi, mode=mode, unit=unit, profile=profile, auto_track=auto_track
        )
        
        _, buffer = cv2.imencode('.jpg', crop, [cv2.IMWRITE_JPEG_QUALITY, 90])
        crop_b64 = base64.b64encode(buffer).decode('utf-8')

        return {
            "success": True,
            "parsed": parsed,
            "crop_base64": f"data:image/jpeg;base64,{crop_b64}"
        }

    def start_processing(self, options):
        """Inicia el proceso de lectura continua en un hilo secundario."""
        if self.is_processing:
            return {"error": "Ya hay un proceso en ejecución"}

        source = options.get("source")
        mode = options.get("mode", "viscometer")
        roi = options.get("roi")
        sample_interval = float(options.get("sample_interval", 1.0))
        unit = options.get("unit", "g")
        profile = options.get("profile", "normal")
        auto_track = bool(options.get("auto_track", False))
        min_conf = float(options.get("min_confidence", 0.45))
        duration_limit = float(options.get("duration_limit", 0))

        self.is_processing = True
        self.cancel_requested = False
        self.last_all_data_rows = []
        
        self.current_state = {
            "is_running": True,
            "progress_pct": 0,
            "current_time_str": "00:00:00",
            "current_reading": None,
            "quality_alert": False,
            "alert_message": "",
            "rows_extracted": 0,
            "last_row": None,
            "recent_rows": [],
            "excel_file": None,
            "csv_file": None,
            "error_msg": None
        }

        self.processing_thread = threading.Thread(
            target=self._run_processing_loop,
            args=(source, mode, roi, sample_interval, unit, min_conf, duration_limit, profile, auto_track),
            daemon=True
        )
        self.processing_thread.start()
        return {"success": True}

    def stop_processing(self):
        if self.is_processing:
            self.cancel_requested = True
            return {"success": True, "message": "Detención solicitada"}
        return {"success": False, "message": "No hay proceso activo"}

    def get_status(self):
        return self.current_state

    def _run_processing_loop(self, source, mode, roi, sample_interval, unit, min_conf, duration_limit, profile="normal", auto_track=False):
        is_cam = isinstance(source, int) or str(source).isdigit()
        src_val = int(source) if is_cam else source

        source_name = f"Cámara #{src_val}" if is_cam else os.path.basename(str(source))
        hw_desc = f"{self.engine.hardware_desc} [Perfil: {profile.upper()}]"

        self.notifier.notify_start(mode, source_name, sample_interval, hw_desc)

        cap = cv2.VideoCapture(src_val, cv2.CAP_DSHOW if is_cam and sys.platform == 'win32' else cv2.CAP_ANY)
        if not cap.isOpened():
            self.current_state["is_running"] = False
            self.current_state["error_msg"] = f"No se pudo abrir {source_name}"
            self.is_processing = False
            self.notifier.notify_error(
                "Dispositivo no disponible",
                f"No se pudo inicializar la fuente de video ({source_name}). Compruebe la conexión USB o verifique que ninguna otra app esté bloqueando la cámara.",
                "00:00:00"
            )
            return

        fps = cap.get(cv2.CAP_PROP_FPS) or 30.0
        total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT)) if not is_cam else 0
        frame_step = max(1, int(fps * sample_interval))
        
        all_data_rows = []
        frame_idx = 0
        current_second = 0.0
        start_real_time = time.time()
        last_autosave_time = time.time()
        bad_reading_streak = 0

        # Preparar archivo CSV en streaming directo para protección total contra apagones
        output_dir = self.config.get("output_dir", os.path.join(os.path.dirname(os.path.abspath(__file__)), "output"))
        os.makedirs(output_dir, exist_ok=True)
        timestamp_slug = time.strftime("%Y%m%d_%H%M%S")
        live_csv_path = os.path.join(output_dir, f"Datos_{mode.capitalize()}_{timestamp_slug}.csv")
        excel_path = os.path.join(output_dir, f"Datos_{mode.capitalize()}_{timestamp_slug}.xlsx")
        
        csv_file_handle = open(live_csv_path, mode="w", newline="", encoding="utf-8-sig")
        import csv as py_csv
        csv_writer = py_csv.writer(csv_file_handle)
        csv_writer.writerow([f"# LabVision - Registro en Vivo {mode.upper()}"])
        csv_writer.writerow([f"# Autor: Creado por NachoFari (https://github.com/NachoFari)"])
        csv_writer.writerow([f"# Inicio: {time.strftime('%Y-%m-%d %H:%M:%S')}"])
        csv_writer.writerow([])
        if mode == "viscometer":
            csv_writer.writerow(["Tiempo_seg", "Timestamp", "Rotor", "Velocidad_RPM", "Viscosidad_mPas", "Torque_Pct", "Confianza_Pct", "Estado"])
        else:
            csv_writer.writerow(["Tiempo_seg", "Timestamp", f"Peso_{unit}", "Unidad", "Confianza_Pct", "Estado"])
        csv_file_handle.flush()
        if hasattr(os, 'fsync'):
            try: os.fsync(csv_file_handle.fileno())
            except Exception: pass

        self.current_state["csv_file"] = live_csv_path
        self.current_state["last_autosave_time"] = time.strftime("%H:%M:%S")

        # Intervalo de auto-guardado en minutos (por defecto 20 minutos = 1200 seg)
        autosave_interval_sec = float(self.config.get("autosave_interval_min", 20)) * 60.0

        try:
            while not self.cancel_requested:
                if not is_cam:
                    cap.set(cv2.CAP_PROP_POS_FRAMES, frame_idx)
                    ret, frame = cap.read()
                    if not ret:
                        break
                    current_second = frame_idx / fps
                    progress = min(100, int((frame_idx / max(1, total_frames)) * 100))
                else:
                    ret, frame = cap.read()
                    if not ret:
                        break
                    current_second = time.time() - start_real_time
                    progress = 50
                    if duration_limit > 0 and current_second >= duration_limit:
                        break

                m, s = divmod(int(current_second), 60)
                h, m = divmod(m, 60)
                ts_str = f"{h:02d}:{m:02d}:{s:02d}"

                # Inferencia con auto-tracking y perfil
                parsed, crop = self.engine.process_frame(
                    frame, roi=roi, mode=mode, unit=unit, min_confidence=min_conf, profile=profile, auto_track=auto_track
                )

                row_entry = {
                    "time_sec": round(current_second, 2),
                    "timestamp_str": ts_str,
                    "confidence": parsed["confidence"],
                    "is_bad": parsed["is_bad"],
                    "warning": parsed["warning"]
                }

                if mode == "viscometer":
                    row_entry["rotor"] = parsed["rotor"]
                    row_entry["speed_rpm"] = parsed["speed_rpm"]
                    row_entry["viscosity_mpa"] = parsed["viscosity_mpa"]
                    row_entry["torque_pct"] = parsed["torque_pct"]
                else:
                    row_entry["weight"] = parsed["weight"]
                    row_entry["unit"] = parsed["unit"]

                all_data_rows.append(row_entry)

                # Escritura instantanea en CSV con flush y sync (Proteccion 100% contra apagones)
                c_val = row_entry.get("confidence")
                c_pct = f"{round(float(c_val)*100, 1)}%" if c_val is not None else ""
                estado_str = "DUDOSA" if row_entry["is_bad"] else "OPTIMA"
                if mode == "viscometer":
                    csv_writer.writerow([
                        row_entry["time_sec"], row_entry["timestamp_str"],
                        row_entry.get("rotor") or "", row_entry.get("speed_rpm") or "",
                        row_entry.get("viscosity_mpa") or "", row_entry.get("torque_pct") or "",
                        c_pct, estado_str
                    ])
                else:
                    csv_writer.writerow([
                        row_entry["time_sec"], row_entry["timestamp_str"],
                        row_entry.get("weight") or "", row_entry.get("unit") or unit,
                        c_pct, estado_str
                    ])
                csv_file_handle.flush()

                # Auto-guardado de respaldo periodico cada 20 minutos (o configurado)
                if time.time() - last_autosave_time >= autosave_interval_sec:
                    last_autosave_time = time.time()
                    try:
                        checkpoint_slug = time.strftime("%H%M%S")
                        checkpoint_excel = os.path.join(output_dir, f"AutoSave_{mode.capitalize()}_{timestamp_slug}_{checkpoint_slug}.xlsx")
                        self.engine.export_to_excel(all_data_rows, checkpoint_excel, mode=mode, metadata={"unit": unit})
                        self.current_state["last_autosave_time"] = time.strftime("%H:%M:%S")
                        print(f"[LabVision] Auto-guardado de respaldo completado: {checkpoint_excel}")
                    except Exception as e_save:
                        print(f"[LabVision] Error en auto-guardado periodico: {e_save}")

                if parsed["is_bad"]:
                    bad_reading_streak += 1
                    self.current_state["quality_alert"] = True
                    self.current_state["alert_message"] = parsed["warning"]
                    if bad_reading_streak == 1 or (bad_reading_streak % 5 == 0):
                        self.notifier.notify_warning(parsed["warning"], ts_str)
                else:
                    bad_reading_streak = 0
                    self.current_state["quality_alert"] = False
                    self.current_state["alert_message"] = ""

                self.current_state["progress_pct"] = progress
                self.current_state["current_time_str"] = ts_str
                self.current_state["current_reading"] = parsed
                self.current_state["last_row"] = row_entry
                self.current_state["rows_extracted"] = len(all_data_rows)
                self.current_state["recent_rows"] = all_data_rows[-10:]

                if not is_cam:
                    frame_idx += frame_step
                else:
                    # Espera granular en cámara de 50ms para responder de inmediato al botón Detener
                    sleep_until = time.time() + sample_interval
                    while time.time() < sleep_until and not self.cancel_requested:
                        time.sleep(0.05)

        except Exception as e:
            self.current_state["error_msg"] = str(e)
            print(f"[LabVision] Error en loop: {e}")
            try:
                self.notifier.notify_error(
                    "Fallo durante adquisición",
                    str(e),
                    self.current_state.get("current_time_str", "En curso")
                )
            except Exception as e_notify:
                print(f"[LabVision] Error enviando alerta a Discord: {e_notify}")
        finally:
            cap.release()
            try:
                csv_file_handle.flush()
                csv_file_handle.close()
            except Exception:
                pass

        self.last_all_data_rows = all_data_rows

        # Exportar automáticamente Excel y CSV
        output_dir = self.config.get("output_dir", os.path.join(os.path.dirname(os.path.abspath(__file__)), "output"))
        timestamp_slug = time.strftime("%Y%m%d_%H%M%S")
        excel_path = os.path.join(output_dir, f"Datos_{mode.capitalize()}_{timestamp_slug}.xlsx")
        csv_path = os.path.join(output_dir, f"Datos_{mode.capitalize()}_{timestamp_slug}.csv")

        if all_data_rows:
            self.engine.export_to_excel(all_data_rows, excel_path, mode=mode, metadata={"unit": unit})
            self.current_state["excel_file"] = excel_path
            self.current_state["csv_file"] = live_csv_path

            stats = {}
            if mode == "viscometer":
                visc_vals = [r["viscosity_mpa"] for r in all_data_rows if r["viscosity_mpa"] is not None]
                if visc_vals:
                    stats["avg_viscosity"] = sum(visc_vals) / len(visc_vals)
                rpms = [r["speed_rpm"] for r in all_data_rows if r["speed_rpm"] is not None]
                if rpms:
                    stats["rpm"] = rpms[0]
            else:
                weights = [r["weight"] for r in all_data_rows if r["weight"] is not None]
                if weights:
                    stats["final_weight"] = weights[-1]
                stats["unit"] = unit

            elapsed = time.time() - start_real_time
            self.notifier.notify_finish(mode, len(all_data_rows), elapsed, excel_path, stats)

        self.current_state["is_running"] = False
        self.current_state["progress_pct"] = 100
        self.is_processing = False

    def export_csv_now(self):
        """Exporta inmediatamente a CSV los datos acumulados hasta el momento."""
        if not self.last_all_data_rows and not self.current_state.get("recent_rows"):
            return {"error": "No hay datos acumulados para exportar"}

        rows = self.last_all_data_rows or self.current_state.get("recent_rows", [])
        output_dir = self.config.get("output_dir", os.path.join(os.path.dirname(os.path.abspath(__file__)), "output"))
        timestamp_slug = time.strftime("%Y%m%d_%H%M%S")
        csv_path = os.path.join(output_dir, f"Export_{timestamp_slug}.csv")
        
        self.engine.export_to_csv(rows, csv_path, mode="viscometer")
        return {"success": True, "file_path": csv_path}

    def open_browser(self, url="https://github.com/NachoFari"):
        """Abre un enlace web externo en el navegador predeterminado del sistema."""
        target_url = url or "https://github.com/NachoFari"
        if not target_url.startswith("http"):
            target_url = "https://" + target_url
        try:
            if sys.platform == 'win32':
                os.startfile(target_url)
            else:
                import webbrowser
                webbrowser.open(target_url)
            return {"success": True}
        except Exception:
            try:
                subprocess.Popen(['cmd', '/c', 'start', '', target_url], shell=True)
                return {"success": True}
            except Exception as e2:
                return {"error": str(e2)}

    def open_excel(self, file_path=None):
        target = file_path or self.current_state.get("excel_file")
        if target and os.path.exists(target):
            if sys.platform == 'win32':
                os.startfile(target)
            else:
                subprocess.Popen(['xdg-open', target])
            return {"success": True}
        return {"error": "Archivo Excel no encontrado aún"}

    def open_csv(self, file_path=None):
        target = file_path or self.current_state.get("csv_file")
        if target and os.path.exists(target):
            if sys.platform == 'win32':
                os.startfile(target)
            else:
                subprocess.Popen(['xdg-open', target])
            return {"success": True}
        return {"error": "Archivo CSV no encontrado aún"}

    def open_folder(self, folder_path=None):
        target = folder_path or self.config.get("output_dir", os.path.dirname(os.path.abspath(__file__)))
        if os.path.exists(target):
            if sys.platform == 'win32':
                os.startfile(target)
            else:
                subprocess.Popen(['xdg-open', target])
            return {"success": True}
        return {"error": "Carpeta no encontrada"}

def start_app():
    api = LabVisionAPI()
    static_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "static")
    index_file = os.path.join(static_dir, "index.html")

    window = webview.create_window(
        title="LabVision • Extractor de Pantallas de Laboratorio",
        url=index_file,
        js_api=api,
        width=1360,
        height=880,
        min_size=(1024, 680),
        maximized=True,
        text_select=True
    )
    api.set_window(window)
    webview.start(gui='edgechromium', debug=False)

if __name__ == "__main__":
    start_app()
