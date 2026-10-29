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
        self._config = ConfigManager.load()
        self._notifier = DiscordNotifier(self._config.get("discord_webhook", ""))
        self._engine = None
        self._engine_ready = False
        self._window = None

        # Estado del procesamiento
        self.is_processing = False
        self.cancel_requested = False
        self.processing_thread = None
        self.last_all_data_rows = []

        # Inicialización en segundo plano para que la ventana abra al instante (en 1 segundo)
        threading.Thread(target=self._init_engine_thread, daemon=True).start()

    def _init_engine_thread(self):
        try:
            self._engine = LabVisionEngine()
            self._engine_ready = True
            print("[LabVision] Motor OCR listo en segundo plano.")
        except Exception as e:
            print(f"[LabVision] Error inicializando motor OCR: {e}")

    def _get_engine(self):
        while not self._engine_ready or self._engine is None:
            time.sleep(0.05)
        return self._engine

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
        self._window = window

    def get_system_info(self):
        hw = self._engine.get_hardware_info() if (self._engine_ready and self._engine) else {"has_gpu": False, "description": "Iniciando OCR en segundo plano...", "torch_version": "2.14.0"}
        return {
            "hardware": hw,
            "config": self._config
        }

    def save_settings(self, new_config):
        self._config.update(new_config)
        ConfigManager.save(self._config)
        if "discord_webhook" in new_config:
            self._notifier.set_webhook(new_config["discord_webhook"])
        return {"success": True}

    def test_discord(self, webhook_url):
        ok, msg = self._notifier.send_test(webhook_url)
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
        if not self._window:
            return None
        file_types = ('Archivos de Video (*.mp4;*.avi;*.mov;*.mkv;*.wmv)', 'Todos los archivos (*.*)')
        result = self._window.create_file_dialog(webview.OPEN_DIALOG, allow_multiple=False, file_types=file_types)
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
        suggested_box = self._get_engine().detect_screen_auto(frame, mode="viscometer")

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

        eval_result = self._get_engine().calibrate_frame(frame, roi=roi)
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

        parsed, crop = self._get_engine().process_frame(
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
        hw_desc = f"{self._get_engine().hardware_desc} [Perfil: {profile.upper()}]"

        self._notifier.notify_start(mode, source_name, sample_interval, hw_desc)

        cap = cv2.VideoCapture(src_val, cv2.CAP_DSHOW if is_cam and sys.platform == 'win32' else cv2.CAP_ANY)
        if not cap.isOpened():
            self.current_state["is_running"] = False
            self.current_state["error_msg"] = f"No se pudo abrir {source_name}"
            self.is_processing = False
            self._notifier.notify_error(
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
        output_dir = self._config.get("output_dir", os.path.join(os.path.dirname(os.path.abspath(__file__)), "output"))
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
        autosave_interval_sec = float(self._config.get("autosave_interval_min", 20)) * 60.0

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
                parsed, crop = self._get_engine().process_frame(
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
                        self._get_engine().export_to_excel(all_data_rows, checkpoint_excel, mode=mode, metadata={"unit": unit})
                        self.current_state["last_autosave_time"] = time.strftime("%H:%M:%S")
                        print(f"[LabVision] Auto-guardado de respaldo completado: {checkpoint_excel}")
                    except Exception as e_save:
                        print(f"[LabVision] Error en auto-guardado periodico: {e_save}")

                if parsed["is_bad"]:
                    bad_reading_streak += 1
                    self.current_state["quality_alert"] = True
                    self.current_state["alert_message"] = parsed["warning"]
                    if bad_reading_streak == 1 or (bad_reading_streak % 5 == 0):
                        self._notifier.notify_warning(parsed["warning"], ts_str)
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
                self._notifier.notify_error(
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
        output_dir = self._config.get("output_dir", os.path.join(os.path.dirname(os.path.abspath(__file__)), "output"))
        timestamp_slug = time.strftime("%Y%m%d_%H%M%S")
        excel_path = os.path.join(output_dir, f"Datos_{mode.capitalize()}_{timestamp_slug}.xlsx")
        csv_path = os.path.join(output_dir, f"Datos_{mode.capitalize()}_{timestamp_slug}.csv")

        if all_data_rows:
            self._get_engine().export_to_excel(all_data_rows, excel_path, mode=mode, metadata={"unit": unit})
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
            self._notifier.notify_finish(mode, len(all_data_rows), elapsed, excel_path, stats)

        self.current_state["is_running"] = False
        self.current_state["progress_pct"] = 100
        self.is_processing = False

    def export_csv_now(self):
        """Exporta inmediatamente a CSV los datos acumulados hasta el momento."""
        if not self.last_all_data_rows and not self.current_state.get("recent_rows"):
            return {"error": "No hay datos acumulados para exportar"}

        rows = self.last_all_data_rows or self.current_state.get("recent_rows", [])
        output_dir = self._config.get("output_dir", os.path.join(os.path.dirname(os.path.abspath(__file__)), "output"))
        timestamp_slug = time.strftime("%Y%m%d_%H%M%S")
        csv_path = os.path.join(output_dir, f"Export_{timestamp_slug}.csv")
        
        self._get_engine().export_to_csv(rows, csv_path, mode="viscometer")
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
        target = folder_path or self._config.get("output_dir", os.path.dirname(os.path.abspath(__file__)))
        if os.path.exists(target):
            if sys.platform == 'win32':
                os.startfile(target)
            else:
                subprocess.Popen(['xdg-open', target])
            return {"success": True}
        return {"error": "Carpeta no encontrada"}

def find_free_port(start_port=23456, max_attempts=100):
    """Verifica si un puerto está libre. Si está ocupado, busca dinámicamente el siguiente."""
    import socket
    for port in range(start_port, start_port + max_attempts):
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
                s.bind(('127.0.0.1', port))
                return port
        except OSError:
            continue
    return None

def start_app():
    if sys.platform == 'win32':
        try:
            import ctypes
            ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID('nachofari.labvision.pro.v08')
        except Exception:
            pass

    api = LabVisionAPI()
    base_dir = os.path.dirname(os.path.abspath(__file__))
    static_dir = os.path.join(base_dir, "static")
    index_file = os.path.join(static_dir, "index.html")
    icon_file = os.path.join(base_dir, "labvision.ico")
    if not os.path.exists(icon_file):
        icon_file = None

    window = webview.create_window(
        title="LabVision • Extractor de Pantallas de Laboratorio",
        url=index_file,
        js_api=api,
        width=1360,
        height=880,
        min_size=(1024, 680),
        maximized=True,
        text_select=True,
        background_color='#0b0f19'
    )
    api.set_window(window)

    # Detección y salto automático de puerto si el predeterminado está ocupado
    selected_port = find_free_port(start_port=23456)
    if selected_port:
        print(f"[LabVision] Puerto libre asignado dinámicamente: {selected_port}")
        webview.start(gui='edgechromium', http_port=selected_port, icon=icon_file, debug=False)
    else:
        webview.start(gui='edgechromium', icon=icon_file, debug=False)

if __name__ == "__main__":
    start_app()
