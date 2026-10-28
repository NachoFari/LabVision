import cv2
import numpy as np
import easyocr
import os

from core.hardware import HardwareDetector
from core.calibrator import CameraCalibrator
from core.preprocessor import ImagePreprocessor
from core.parsers.viscometer_parser import ViscometerParser
from core.parsers.balance_parser import BalanceParser
from exporters.excel_exporter import ExcelExporter
from exporters.csv_exporter import CSVExporter

class LabVisionEngine:
    """Orquestador modular de visión y lectura de pantallas de laboratorio."""
    def __init__(self, force_cpu=False):
        hw_info = HardwareDetector.detect(force_cpu=force_cpu)
        self.has_gpu = hw_info["has_gpu"]
        self.hardware_desc = hw_info["description"]
        self.torch_version = hw_info["torch_version"]

        print(f"[LabVision] Inicializando OCR con {self.hardware_desc}...")
        models_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "models")
        os.makedirs(models_dir, exist_ok=True)
        has_local_models = (
            os.path.exists(os.path.join(models_dir, "craft_mlt_25k.pth")) and
            os.path.exists(os.path.join(models_dir, "english_g2.pth"))
        )
        self.reader = easyocr.Reader(
            ['en'],
            gpu=self.has_gpu,
            model_storage_directory=models_dir,
            download_enabled=not has_local_models,
            verbose=False
        )
        print("[LabVision] OCR listo.")

    def get_hardware_info(self):
        return {
            "has_gpu": self.has_gpu,
            "description": self.hardware_desc,
            "torch_version": self.torch_version
        }

    def calibrate_frame(self, frame, roi=None):
        return CameraCalibrator.evaluate(frame, roi=roi)

    def detect_screen_auto(self, frame, mode="viscometer"):
        """
        Detección y seguimiento automático de la pantalla para videos donde la cámara se mueve
        (como en celulares sostenidos a mano).
        Para viscosímetro: aísla el panel azul/celeste retroiluminado.
        Para balanza: busca contornos rectangulares de alto contraste.
        """
        if frame is None or frame.size == 0:
            return None

        h, w = frame.shape[:2]

        if mode == "viscometer":
            hsv = cv2.cvtColor(frame, cv2.COLOR_BGR2HSV)
            # Rango HSV para la retroiluminación azul/cian de pantallas tipo NDJ-8S
            lower_blue = np.array([85, 30, 60])
            upper_blue = np.array([135, 255, 255])
            mask = cv2.inRange(hsv, lower_blue, upper_blue)

            contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
            best_box = None
            max_area = 0
            for cnt in contours:
                area = cv2.contourArea(cnt)
                # El display debe ocupar al menos el 2% del fotograma
                if area > max_area and area > (w * h * 0.02):
                    max_area = area
                    best_box = cv2.boundingRect(cnt)

            if best_box:
                bx, by, bw, bh = best_box
                # Añadir margen de seguridad
                pad_x = int(bw * 0.04)
                pad_y = int(bh * 0.04)
                x1 = max(0, bx - pad_x)
                y1 = max(0, by - pad_y)
                w1 = min(w - x1, bw + 2 * pad_x)
                h1 = min(h - y1, bh + 2 * pad_y)
                return [x1, y1, w1, h1]

        return None

    def process_frame(self, frame, roi=None, mode="viscometer", unit="g", min_confidence=0.45, profile="normal", auto_track=False):
        """
        Procesa un fotograma aplicando recorte (ROI manual o Auto-Tracking si hay movimiento),
        preprocesamiento adaptado al perfil, inferencia OCR y extracción de datos.
        """
        active_roi = roi

        # Si el usuario activó auto-tracking o no definió ROI, buscar la pantalla dinámicamente
        if auto_track or (roi is None):
            detected_box = self.detect_screen_auto(frame, mode=mode)
            if detected_box:
                active_roi = detected_box

        # Recorte del área de interés
        if active_roi and len(active_roi) == 4 and active_roi[2] > 10 and active_roi[3] > 10:
            x, y, w, h = [int(v) for v in active_roi]
            h_max, w_max = frame.shape[:2]
            x = max(0, min(x, w_max - 1))
            y = max(0, min(y, h_max - 1))
            w = max(10, min(w, w_max - x))
            h = max(10, min(h, h_max - y))
            crop = frame[y:y+h, x:x+w]
        else:
            crop = frame

        processed_crop = ImagePreprocessor.process(crop, profile=profile)
        ocr_results = self.reader.readtext(processed_crop)

        if mode == "viscometer":
            parsed = ViscometerParser.parse(ocr_results, min_confidence=min_confidence)
        else:
            parsed = BalanceParser.parse(ocr_results, user_unit=unit, min_confidence=min_confidence)

        return parsed, crop

    def export_to_excel(self, data_rows, output_path, mode="viscometer", metadata=None):
        return ExcelExporter.export(data_rows, output_path, mode=mode, metadata=metadata)

    def export_to_csv(self, data_rows, output_path, mode="viscometer", metadata=None):
        return CSVExporter.export(data_rows, output_path, mode=mode, metadata=metadata)
