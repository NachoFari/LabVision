import cv2

class ImagePreprocessor:
    """Preprocesa y adapta la imagen según el perfil de rendimiento seleccionado."""
    @staticmethod
    def process(crop_img, profile="normal"):
        if crop_img is None or crop_img.size == 0:
            return crop_img

        h, w = crop_img.shape[:2]

        if profile == "low":
            # Perfil bajo: menor resolución para máxima velocidad en notebooks
            target_w = 360
            if w > target_w:
                scale = target_w / float(w)
                crop_img = cv2.resize(crop_img, None, fx=scale, fy=scale, interpolation=cv2.INTER_LINEAR)
            elif w < 240:
                scale = 240 / float(w)
                crop_img = cv2.resize(crop_img, None, fx=scale, fy=scale, interpolation=cv2.INTER_LINEAR)
            return crop_img

        elif profile == "high":
            # Perfil alto: escalado 2x y realce local de contraste CLAHE
            scale = max(2.0, 720.0 / max(1, w))
            scaled = cv2.resize(crop_img, None, fx=scale, fy=scale, interpolation=cv2.INTER_CUBIC)
            try:
                lab = cv2.cvtColor(scaled, cv2.COLOR_BGR2LAB)
                l, a, b = cv2.split(lab)
                clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))
                cl = clahe.apply(l)
                limg = cv2.merge((cl, a, b))
                scaled = cv2.cvtColor(limg, cv2.COLOR_LAB2BGR)
            except Exception:
                pass
            return scaled

        else: # "normal"
            if w < 440 or h < 200:
                scale = max(1.5, 440.0 / max(1, w))
                crop_img = cv2.resize(crop_img, None, fx=scale, fy=scale, interpolation=cv2.INTER_CUBIC)
            return crop_img
