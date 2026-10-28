import cv2
import numpy as np

class CameraCalibrator:
    """Evalúa la calidad del encuadre, nitidez y reflejos en la pantalla del equipo."""
    @staticmethod
    def evaluate(frame, roi=None):
        if roi and len(roi) == 4 and roi[2] > 10 and roi[3] > 10:
            x, y, w, h = [int(v) for v in roi]
            h_max, w_max = frame.shape[:2]
            crop = frame[max(0, y):min(h_max, y+h), max(0, x):min(w_max, x+w)]
        else:
            crop = frame

        if crop is None or crop.size == 0:
            return {"error": "Cuadro o recorte no válido"}

        gray = cv2.cvtColor(crop, cv2.COLOR_BGR2GRAY)

        # 1. Nitidez / Foco mediante Varianza del Laplaciano
        blur_score = cv2.Laplacian(gray, cv2.CV_64F).var()
        if blur_score < 75:
            focus_status = "error"
            focus_msg = "🔴 Imagen borrosa o fuera de foco. Ajusta la distancia o lente de la cámara."
        elif blur_score < 180:
            focus_status = "warning"
            focus_msg = "🟡 Nitidez moderada. Se aconseja enfocar un poco más para evitar confusiones."
        else:
            focus_status = "ok"
            focus_msg = "🟢 Enfoque excelente y nítido."

        # 2. Detección de Reflejos de luz de laboratorio (Glare)
        glare_pixels = np.sum(gray > 245)
        glare_pct = (glare_pixels / float(gray.size)) * 100
        if glare_pct > 8.0:
            glare_status = "error"
            glare_msg = f"🔴 Reflejo intenso ({glare_pct:.1f}% saturado). Inclina la cámara 5° a 10° para desviar la luz del techo."
        elif glare_pct > 3.0:
            glare_status = "warning"
            glare_msg = f"🟡 Reflejo leve detectado ({glare_pct:.1f}%). Puede restar contraste a los dígitos."
        else:
            glare_status = "ok"
            glare_msg = "🟢 Sin reflejos perjudiciales en la pantalla."

        # 3. Nivel de Iluminación y Exposición
        mean_lum = np.mean(gray)
        if mean_lum < 40:
            lum_status = "error"
            lum_msg = "🔴 Iluminación insuficiente. La pantalla o display se ve demasiado oscura."
        elif mean_lum > 220:
            lum_status = "error"
            lum_msg = "🔴 Sobreexposición. Reduce la exposición o aleja las lámparas directas."
        else:
            lum_status = "ok"
            lum_msg = "🟢 Nivel de iluminación equilibrado."

        is_ready = (focus_status != "error" and glare_status != "error" and lum_status == "ok")

        return {
            "is_ready": is_ready,
            "blur_score": round(blur_score, 1),
            "focus_status": focus_status,
            "focus_msg": focus_msg,
            "glare_pct": round(glare_pct, 1),
            "glare_status": glare_status,
            "glare_msg": glare_msg,
            "mean_lum": round(mean_lum, 1),
            "lum_status": lum_status,
            "lum_msg": lum_msg
        }
