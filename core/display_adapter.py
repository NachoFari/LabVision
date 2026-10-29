"""
core/display_adapter.py - Adaptadores de Preprocesamiento Óptico para Pantallas de Laboratorio
=============================================================================================
LabVision Universal - Work Package 2

Módulo especializado en pipelines de visión por computadora adaptados a las características
fotométricas, espectrales y morfológicas de los diferentes tipos de displays de instrumentos
analíticos e industriales:

1. LCD Azul Retroiluminado (lcd_blue_backlit):
   - Emisión STN / FSTN positiva en rango azul-cian (~460-490 nm).
   - Descomposición espectral de canales y umbralización para aislar segmentos oscuros del fondo cian.

2. LCD Gris Reflectivo (lcd_gray_reflective):
   - Pantallas nemáticas reflectivas (TN/STN) dependientes de luz ambiental difusa (e.g., balanzas analíticas).
   - Ecualización adaptativa local por histograma limitado (CLAHE) para compensar sombras y reflejos.
   - Binarización Otsu y dilatación morfológica horizontal sutil (kernel 2x1) para conectar
     las discontinuidades físicas no conductoras entre segmentos de dígitos de 7 segmentos.

3. LED 7 Segmentos Rojo (led_7seg_red):
   - Emisión electroluminiscente AlGaAs / GaAsP (~630-660 nm) sobre chasis oscuro/negro.
   - Diferenciación cromática R - (G + B)/2 y aislamiento en espacio HSV (Hue [0, 10] U [170, 180]).
   - Umbralización paso-alto para eliminar reflejos espurios y ruido del bisel.

4. LED 7 Segmentos Verde (led_7seg_green):
   - Emisión GaP / InGaN verde puro (~520-565 nm) sobre fondo opaco.
   - Diferenciación cromática G - (R + B)/2 con umbralización paso-alto.

5. VFD Verde Azulado / Turquesa (vfd_teal):
   - Emisión por fósforo anódico fluorescente (ZnO:Zn / ZnS:Cu,Al) a ~505 nm en tubo de vacío.
   - Aislamiento de emisión cian/turquesa y filtrado de rejillas físicas de control de malla.

6. Estándar (standard):
   - Pipeline robusto de desenfoque gaussiano y binarización adaptativa Otsu para casos generales.
"""

import os
import cv2
import numpy as np
from typing import Dict, Any, Optional, Union, Tuple, List

# Ruta base del proyecto LabVision (desacoplada, sin rutas absolutas fijas)
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


class DisplayAdapter:
    """
    Motor desacoplado de preprocesamiento de imágenes adaptado a la física de captura
    de diversas tecnologías de visualizadores de instrumentos científicos.
    """

    # Mapeo canónico de perfiles y sus alias habituales en plantillas .lvtemplate
    PROFILE_ALIASES: Dict[str, str] = {
        "lcd_blue_backlit": "lcd_blue_backlit",
        "lcd_blue": "lcd_blue_backlit",
        "viscometer": "lcd_blue_backlit",
        "ndj8s": "lcd_blue_backlit",
        "lcd_gray_reflective": "lcd_gray_reflective",
        "lcd_reflective": "lcd_gray_reflective",
        "lcd_gray": "lcd_gray_reflective",
        "balance": "lcd_gray_reflective",
        "led_7seg_red": "led_7seg_red",
        "led_red": "led_7seg_red",
        "7seg_red": "led_7seg_red",
        "led_7seg_green": "led_7seg_green",
        "led_green": "led_7seg_green",
        "7seg_green": "led_7seg_green",
        "vfd_teal": "vfd_teal",
        "vfd": "vfd_teal",
        "vfd_cyan": "vfd_teal",
        "standard": "standard",
        "default": "standard",
        "generic": "standard",
    }

    @classmethod
    def get_supported_profiles(cls) -> List[str]:
        """Retorna la lista de identificadores canónicos de perfiles soportados."""
        return [
            "lcd_blue_backlit",
            "lcd_gray_reflective",
            "led_7seg_red",
            "led_7seg_green",
            "vfd_teal",
            "standard",
        ]

    @classmethod
    def get_profile_metadata(cls, profile_name: str) -> Dict[str, Any]:
        """
        Retorna metadatos científicos y ópticos del perfil seleccionado.
        """
        canonical = cls.normalize_profile_name(profile_name)
        metadata_catalog = {
            "lcd_blue_backlit": {
                "name": "LCD Azul Retroiluminado",
                "display_tech": "STN/FSTN Positivo con retroiluminación LED cian/azul",
                "wavelength_nm": "460 - 490 nm",
                "segment_polarity": "Oscuro sobre fondo iluminado",
                "typical_devices": ["Viscosímetro NDJ-8S", "Agitadores magnéticos con display digital", "Autoclaves modernos"],
                "default_preprocessing": {
                    "grayscale": False,
                    "clahe": False,
                    "threshold_mode": "otsu_adaptive",
                    "invert_polarity": False,
                    "noise_kernel_size": 3,
                }
            },
            "lcd_gray_reflective": {
                "name": "LCD Gris Reflectivo (7 Segmentos)",
                "display_tech": "TN Reflectivo Pasivo bajo iluminación ambiente",
                "wavelength_nm": "Banda ancha (Luz visible reflejada)",
                "segment_polarity": "Oscuro sobre fondo gris claro / plata",
                "typical_devices": ["Balanza Analítica Ohaus / Mettler Toledo", "pH-metro Hanna HI 2211", "Conductímetro portátil"],
                "default_preprocessing": {
                    "grayscale": True,
                    "clahe": True,
                    "clip_limit": 2.0,
                    "tile_grid_size": [8, 8],
                    "threshold_mode": "otsu_adaptive",
                    "invert_polarity": False,
                    "morph_kernel": [2, 1],
                    "noise_kernel_size": 0,
                }
            },
            "led_7seg_red": {
                "name": "LED 7 Segmentos Rojo",
                "display_tech": "Diodos emisores de luz AlGaAs / GaAsP",
                "wavelength_nm": "630 - 660 nm",
                "segment_polarity": "Segmentos brillantes sobre chasis oscuro",
                "typical_devices": ["Baños termostáticos Julabo / Memmert", "Muflas de alta temperatura", "Controladores PID"],
                "default_preprocessing": {
                    "grayscale": False,
                    "clahe": False,
                    "threshold_mode": "high_pass_color_diff",
                    "invert_polarity": False,
                    "min_threshold": 30,
                    "morph_kernel": [2, 1],
                }
            },
            "led_7seg_green": {
                "name": "LED 7 Segmentos Verde",
                "display_tech": "Diodos emisores de luz GaP / InGaN",
                "wavelength_nm": "520 - 565 nm",
                "segment_polarity": "Segmentos brillantes sobre chasis oscuro",
                "typical_devices": ["Incubadoras microbiológicas", "Temporizadores de proceso", "Centrífugas de laboratorio"],
                "default_preprocessing": {
                    "grayscale": False,
                    "clahe": False,
                    "threshold_mode": "high_pass_color_diff",
                    "invert_polarity": False,
                    "min_threshold": 30,
                    "morph_kernel": [2, 1],
                }
            },
            "vfd_teal": {
                "name": "VFD Turquesa / Cian (Vacuum Fluorescent Display)",
                "display_tech": "Fósforo anódico luminiscente ZnO:Zn en tubo de vacío con filtro tintado",
                "wavelength_nm": "500 - 515 nm",
                "segment_polarity": "Segmentos cian brillantes sobre fondo oscuro con rejilla",
                "typical_devices": ["Balanzas de precisión antiguas", "Espectrofotómetros UV-Vis", "Cromatógrafos clásicos"],
                "default_preprocessing": {
                    "grayscale": False,
                    "clahe": False,
                    "threshold_mode": "color_diff_otsu",
                    "invert_polarity": False,
                    "min_threshold": 25,
                    "blur_kernel": [3, 3],
                }
            },
            "standard": {
                "name": "Estándar / Genérico",
                "display_tech": "Pantalla genérica de alto contraste o documento impreso",
                "wavelength_nm": "Pancromático",
                "segment_polarity": "Auto-detectado por contraste de fondo",
                "typical_devices": ["Pantallas TFT a color", "Lectura de etiquetas", "Documentos de laboratorio"],
                "default_preprocessing": {
                    "grayscale": True,
                    "clahe": False,
                    "threshold_mode": "otsu_gaussian",
                    "invert_polarity": False,
                    "blur_kernel": [3, 3],
                }
            }
        }
        return metadata_catalog.get(canonical, metadata_catalog["standard"])

    @classmethod
    def normalize_profile_name(cls, profile_name: Optional[str]) -> str:
        """Normaliza el nombre del perfil resolviendo alias y mayúsculas."""
        if not profile_name or not isinstance(profile_name, str):
            return "standard"
        cleaned = profile_name.strip().lower()
        return cls.PROFILE_ALIASES.get(cleaned, "standard")

    @staticmethod
    def _ensure_bgr_and_valid(image: Optional[np.ndarray]) -> Optional[np.ndarray]:
        """
        Valida que la imagen no sea nula ni vacía y asegura formato BGR de 3 canales.
        """
        if image is None or not isinstance(image, np.ndarray) or image.size == 0:
            return None

        if image.ndim == 2:
            # Imagen monocromática / 1 canal -> replicar a BGR
            return cv2.cvtColor(image, cv2.COLOR_GRAY2BGR)

        if image.ndim == 3:
            channels = image.shape[2]
            if channels == 1:
                return cv2.cvtColor(image, cv2.COLOR_GRAY2BGR)
            elif channels == 3:
                return image
            elif channels == 4:
                return cv2.cvtColor(image, cv2.COLOR_BGRA2BGR)

        return None

    # =========================================================================
    # PIPELINE 1: LCD Azul Retroiluminado (lcd_blue_backlit)
    # =========================================================================
    @classmethod
    def pipeline_lcd_blue_backlit(
        cls,
        image: np.ndarray,
        invert_polarity: bool = False,
        noise_kernel_size: int = 3,
        **kwargs
    ) -> np.ndarray:
        """
        Descomposición espectral de canales y binarización para separar segmentos oscuros
        de LCD nemático respecto a una retroiluminación azul/celeste brillante.

        Parámetros:
        -----------
        image : np.ndarray
            Fotograma o recorte de sub-ROI en BGR.
        invert_polarity : bool
            Si es False (predeterminado), los segmentos oscuros resultan en 255 (blanco)
            y el fondo azul en 0 (negro). Si es True, invierte la máscara resultante.
        noise_kernel_size : int
            Tamaño de ventana de suavizado gaussiano previo para atenuar la trama de matriz de puntos.
        """
        if image is None:
            return None
        bgr = cls._ensure_bgr_and_valid(image)
        if bgr is None:
            return image

        b = bgr[:, :, 0].astype(np.float32)
        g = bgr[:, :, 1].astype(np.float32)
        r = bgr[:, :, 2].astype(np.float32)

        # Descomposición de color:
        # El fondo emite con alta intensidad en azul (B) y verde (G), y baja en rojo (R).
        # Los segmentos LCD bloquean la luz, teniendo valores bajos en B y G.
        # Restar una fracción del rojo amortigua reflejos espurios de luz ambiental blanca/cálida.
        cyan_intensity = np.clip(0.6 * b + 0.4 * g - 0.25 * r, 0, 255).astype(np.uint8)

        # Suavizado de ruido de matriz de cristal líquido
        k = max(1, noise_kernel_size)
        if k % 2 == 0:
            k += 1
        if k >= 3:
            cyan_intensity = cv2.GaussianBlur(cyan_intensity, (k, k), 0)

        # Umbralización Otsu inversa: los segmentos oscuros (baja intensidad cian) pasan a 255
        _, binary = cv2.threshold(cyan_intensity, 0, 255, cv2.THRESH_BINARY_INV + cv2.THRESH_OTSU)

        if invert_polarity:
            binary = cv2.bitwise_not(binary)

        return binary

    # =========================================================================
    # PIPELINE 2: LCD Gris Reflectivo (lcd_gray_reflective)
    # =========================================================================
    @classmethod
    def pipeline_lcd_gray_reflective(
        cls,
        image: np.ndarray,
        invert_polarity: bool = False,
        clahe: bool = True,
        clip_limit: float = 2.0,
        tile_grid_size: Union[Tuple[int, int], List[int]] = (8, 8),
        morph_kernel: Union[Tuple[int, int], List[int]] = (2, 1),
        noise_kernel_size: int = 0,
        **kwargs
    ) -> np.ndarray:
        """
        Conversión a escala de grises, realce local CLAHE, binarización adaptativa Otsu
        y dilatación morfológica horizontal sutil (kernel 2x1) para salvar las discontinuidades
        físicas no conductoras entre segmentos de dígitos de 7 segmentos.

        Parámetros:
        -----------
        image : np.ndarray
            Fotograma o recorte de sub-ROI.
        invert_polarity : bool
            False: segmentos oscuros pasan a blanco (255) y fondo plata a negro (0).
            True: segmentos oscuros en 0 y fondo en 255.
        clahe : bool
            Activa la ecualización adaptativa limitada de contraste para compensar sombras irregulares.
        clip_limit : float
            Límite de amplificación de contraste en CLAHE (típico 2.0 - 3.0).
        tile_grid_size : Tuple[int, int]
            Tamaño de cuadrícula de partición de mosaico CLAHE (por defecto 8x8).
        morph_kernel : Tuple[int, int]
            Dimensiones (ancho, alto) del elemento estructurante para dilatación horizontal.
            Un valor (2, 1) puentea sutilmente los espacios físicos entre segmentos sin engrosar verticalmente.
        noise_kernel_size : int
            Ventana para reducción previa de ruido gaussiano.
        """
        if image is None:
            return None
        if not isinstance(image, np.ndarray) or image.size == 0:
            return image

        # 1. Conversión a escala de grises defensiva
        if image.ndim == 3:
            if image.shape[2] == 3:
                gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
            elif image.shape[2] == 4:
                gray = cv2.cvtColor(image, cv2.COLOR_BGRA2GRAY)
            else:
                gray = image[:, :, 0].copy()
        elif image.ndim == 2:
            gray = image.copy()
        else:
            return image

        # 2. Atenuación opcional de ruido (desactivada por defecto para preservar bordes finos de 7 segmentos)
        if noise_kernel_size and noise_kernel_size >= 3:
            k = noise_kernel_size if noise_kernel_size % 2 == 1 else noise_kernel_size + 1
            gray = cv2.GaussianBlur(gray, (k, k), 0)

        # 3. CLAHE con adaptación defensiva a imágenes más pequeñas que la rejilla
        if clahe:
            h, w = gray.shape[:2]
            tw = max(1, min(int(tile_grid_size[0]), max(1, w // 2)))
            th = max(1, min(int(tile_grid_size[1]), max(1, h // 2)))
            clahe_obj = cv2.createCLAHE(clipLimit=float(clip_limit), tileGridSize=(tw, th))
            enhanced = clahe_obj.apply(gray)
        else:
            enhanced = gray

        # 4. Binarización Otsu Inversa: dígitos oscuros a 255, fondo claro a 0
        _, binary = cv2.threshold(enhanced, 0, 255, cv2.THRESH_BINARY_INV + cv2.THRESH_OTSU)

        # 5. Dilatación morfológica horizontal sutil (kernel 2x1)
        # Puentea el espacio físico entre segmentos verticales y horizontales de dígitos
        kw = max(1, int(morph_kernel[0]))
        kh = max(1, int(morph_kernel[1]))
        if kw > 1 or kh > 1:
            kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (kw, kh))
            binary = cv2.dilate(binary, kernel, iterations=1)

        # 6. Polaridad
        if invert_polarity:
            binary = cv2.bitwise_not(binary)

        return binary

    # =========================================================================
    # PIPELINE 3: LED 7 Segmentos Rojo (led_7seg_red)
    # =========================================================================
    @classmethod
    def pipeline_led_7seg_red(
        cls,
        image: np.ndarray,
        invert_polarity: bool = False,
        min_threshold: int = 30,
        morph_kernel: Union[Tuple[int, int], List[int]] = (2, 1),
        **kwargs
    ) -> np.ndarray:
        """
        Aislamiento de dígitos LED emisivos rojos frente a chasis negro/gris mediante:
        - Diferenciación cromática espectral: R - (G + B)/2
        - Filtrado en espacio HSV: Hue en rango [0, 10] U [170, 180]
        - Umbralización paso-alto para suprimir reflejos no monocromáticos.

        Parámetros:
        -----------
        image : np.ndarray
            Fotograma o recorte de sub-ROI en BGR.
        invert_polarity : bool
            False: dígitos LED rojos en 255 (blanco), fondo en 0 (negro).
        min_threshold : int
            Piso mínimo de umbralización para evitar la binarización de ruido térmico en chasis negro.
        morph_kernel : Tuple[int, int]
            Elemento estructurante para puenteo de segmentos LED discontinuos.
        """
        if image is None:
            return None
        bgr = cls._ensure_bgr_and_valid(image)
        if bgr is None:
            return image

        b = bgr[:, :, 0].astype(np.float32)
        g = bgr[:, :, 1].astype(np.float32)
        r = bgr[:, :, 2].astype(np.float32)

        # 1. Diferencia cromática: R - (G + B) / 2
        # La emisión monocromática roja tiene alto R y casi nulos G y B.
        # Las luces de ambiente blancas tienen R ≈ G ≈ B, resultando en diff ≈ 0.
        red_diff = np.clip(r - (g + b) / 2.0, 0, 255).astype(np.uint8)

        # 2. Aislamiento en espacio HSV (Hue rojo bicomponente: [0, 10] U [170, 180])
        hsv = cv2.cvtColor(bgr, cv2.COLOR_BGR2HSV)
        mask_red_low = cv2.inRange(hsv, np.array([0, 45, 35]), np.array([10, 255, 255]))
        mask_red_high = cv2.inRange(hsv, np.array([170, 45, 35]), np.array([180, 255, 255]))
        hsv_red_mask = cv2.bitwise_or(mask_red_low, mask_red_high)

        # 3. Umbralización adaptativa paso-alto sobre red_diff
        otsu_val, _ = cv2.threshold(red_diff, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
        effective_thresh = max(int(otsu_val), min_threshold)
        _, diff_binary = cv2.threshold(red_diff, effective_thresh, 255, cv2.THRESH_BINARY)

        # Combinar filtrado cromático con máscara espectral HSV
        combined = cv2.bitwise_and(diff_binary, hsv_red_mask)

        # Fallback de seguridad: si HSV es muy estricto ante iluminación saturada, usar diff_binary
        if np.count_nonzero(combined) == 0 and np.count_nonzero(diff_binary) > 0:
            binary = diff_binary
        else:
            binary = combined

        # 4. Dilatación horizontal sutil si fue solicitada
        kw = max(1, int(morph_kernel[0]))
        kh = max(1, int(morph_kernel[1]))
        if kw > 1 or kh > 1:
            kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (kw, kh))
            binary = cv2.dilate(binary, kernel, iterations=1)

        if invert_polarity:
            binary = cv2.bitwise_not(binary)

        return binary

    # =========================================================================
    # PIPELINE 4: LED 7 Segmentos Verde (led_7seg_green)
    # =========================================================================
    @classmethod
    def pipeline_led_7seg_green(
        cls,
        image: np.ndarray,
        invert_polarity: bool = False,
        min_threshold: int = 30,
        morph_kernel: Union[Tuple[int, int], List[int]] = (2, 1),
        **kwargs
    ) -> np.ndarray:
        """
        Aislamiento de dígitos LED emisivos verdes frente a chasis negro/gris mediante:
        - Diferenciación cromática espectral: G - (R + B)/2
        - Umbralización paso-alto y filtrado de interferencias rojas o luces blancas.

        Parámetros:
        -----------
        image : np.ndarray
            Fotograma o recorte de sub-ROI en BGR.
        invert_polarity : bool
            False: dígitos LED verdes en 255 (blanco), fondo en 0 (negro).
        min_threshold : int
            Piso mínimo de umbralización.
        """
        if image is None:
            return None
        bgr = cls._ensure_bgr_and_valid(image)
        if bgr is None:
            return image

        b = bgr[:, :, 0].astype(np.float32)
        g = bgr[:, :, 1].astype(np.float32)
        r = bgr[:, :, 2].astype(np.float32)

        # 1. Diferencia cromática: G - (R + B) / 2
        green_diff = np.clip(g - (r + b) / 2.0, 0, 255).astype(np.uint8)

        # 2. Máscara complementaria HSV para verde (Hue 35 a 85 en escala OpenCV 0-180)
        hsv = cv2.cvtColor(bgr, cv2.COLOR_BGR2HSV)
        mask_green = cv2.inRange(hsv, np.array([35, 40, 35]), np.array([85, 255, 255]))

        # 3. Umbralización Otsu con piso paso-alto
        otsu_val, _ = cv2.threshold(green_diff, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
        effective_thresh = max(int(otsu_val), min_threshold)
        _, diff_binary = cv2.threshold(green_diff, effective_thresh, 255, cv2.THRESH_BINARY)

        combined = cv2.bitwise_and(diff_binary, mask_green)
        if np.count_nonzero(combined) == 0 and np.count_nonzero(diff_binary) > 0:
            binary = diff_binary
        else:
            binary = combined

        # 4. Dilatación sutil
        kw = max(1, int(morph_kernel[0]))
        kh = max(1, int(morph_kernel[1]))
        if kw > 1 or kh > 1:
            kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (kw, kh))
            binary = cv2.dilate(binary, kernel, iterations=1)

        if invert_polarity:
            binary = cv2.bitwise_not(binary)

        return binary

    # =========================================================================
    # PIPELINE 5: VFD Verde Azulado / Turquesa (vfd_teal)
    # =========================================================================
    @classmethod
    def pipeline_vfd_teal(
        cls,
        image: np.ndarray,
        invert_polarity: bool = False,
        min_threshold: int = 25,
        blur_kernel: Union[Tuple[int, int], List[int]] = (3, 3),
        **kwargs
    ) -> np.ndarray:
        """
        Aislamiento de emisiones de fósforo en displays fluorescentes al vacío (VFD, ~505 nm)
        mediante combinación espectral de canales verde y azul con rechazo de componente roja,
        seguido de suavizado gaussiano para atenuar las rejillas metálicas de control de malla.

        Parámetros:
        -----------
        image : np.ndarray
            Fotograma o recorte de sub-ROI en BGR.
        invert_polarity : bool
            False: fósforo VFD en 255 (blanco), fondo oscuro en 0 (negro).
        min_threshold : int
            Piso mínimo de umbralización.
        blur_kernel : Tuple[int, int]
            Filtro de suavizado para mitigar las rejillas de malla metálica del tubo de vacío.
        """
        if image is None:
            return None
        bgr = cls._ensure_bgr_and_valid(image)
        if bgr is None:
            return image

        b = bgr[:, :, 0].astype(np.float32)
        g = bgr[:, :, 1].astype(np.float32)
        r = bgr[:, :, 2].astype(np.float32)

        # El fósforo emite intensamente en Cian/Verde azulado (G y B altos, R despreciable).
        # Restar R descarta iluminación ambiental incandescente o fluorescente cálida.
        teal_diff = np.clip(((g + b) / 2.0) - r, 0, 255).astype(np.uint8)

        # Suavizado gaussiano para suprimir la fina rejilla de alambres de aceleración
        kw = max(1, int(blur_kernel[0]))
        kh = max(1, int(blur_kernel[1]))
        if kw % 2 == 0:
            kw += 1
        if kh % 2 == 0:
            kh += 1
        if kw >= 3 and kh >= 3:
            teal_diff = cv2.GaussianBlur(teal_diff, (kw, kh), 0)

        otsu_val, _ = cv2.threshold(teal_diff, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
        effective_thresh = max(int(otsu_val), min_threshold)
        _, binary = cv2.threshold(teal_diff, effective_thresh, 255, cv2.THRESH_BINARY)

        if invert_polarity:
            binary = cv2.bitwise_not(binary)

        return binary

    # =========================================================================
    # PIPELINE 6: Estándar / Genérico (standard)
    # =========================================================================
    @classmethod
    def pipeline_standard(
        cls,
        image: np.ndarray,
        invert_polarity: bool = False,
        blur_kernel: Union[Tuple[int, int], List[int]] = (3, 3),
        **kwargs
    ) -> np.ndarray:
        """
        Pipeline estándar universal de binarización adaptativa Otsu + desenfoque gaussiano
        con detección automática de contraste para garantizar caracteres legibles en OCR.

        Parámetros:
        -----------
        image : np.ndarray
            Fotograma o recorte de sub-ROI.
        invert_polarity : bool
            Permite forzar la inversión de polaridad resultante.
        blur_kernel : Tuple[int, int]
            Filtro de suavizado gaussiano contra ruido de compresión o grano de sensor.
        """
        if image is None:
            return None
        if not isinstance(image, np.ndarray) or image.size == 0:
            return image

        if image.ndim == 3:
            if image.shape[2] == 3:
                gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
            elif image.shape[2] == 4:
                gray = cv2.cvtColor(image, cv2.COLOR_BGRA2GRAY)
            else:
                gray = image[:, :, 0].copy()
        elif image.ndim == 2:
            gray = image.copy()
        else:
            return image

        # Desenfoque gaussiano
        kw = max(1, int(blur_kernel[0]))
        kh = max(1, int(blur_kernel[1]))
        if kw % 2 == 0:
            kw += 1
        if kh % 2 == 0:
            kh += 1
        if kw >= 3 and kh >= 3:
            blurred = cv2.GaussianBlur(gray, (kw, kh), 0)
        else:
            blurred = gray

        # Detección inteligente de polaridad por media de fondo:
        # Si la imagen es predominantemente clara (fondo blanco/gris con texto oscuro),
        # THRESH_BINARY_INV extrae el texto como 255.
        # Si es predominantemente oscura (texto brillante), THRESH_BINARY extrae texto como 255.
        mean_val = float(np.mean(blurred))
        if mean_val > 127.0:
            thresh_mode = cv2.THRESH_BINARY_INV + cv2.THRESH_OTSU
        else:
            thresh_mode = cv2.THRESH_BINARY + cv2.THRESH_OTSU

        _, binary = cv2.threshold(blurred, 0, 255, thresh_mode)

        if invert_polarity:
            binary = cv2.bitwise_not(binary)

        return binary

    # =========================================================================
    # Despachador Principal (preprocess)
    # =========================================================================
    @classmethod
    def preprocess(
        cls,
        image: np.ndarray,
        profile: Optional[Union[Dict[str, Any], str]] = None
    ) -> np.ndarray:
        """
        Procesa la imagen según el perfil de pantalla especificado.
        """
        if image is None:
            return None
        if not isinstance(image, np.ndarray) or image.size == 0:
            return image

        # 1. Resolver el perfil y parámetros
        profile_type = "standard"
        prep_params: Dict[str, Any] = {}

        if isinstance(profile, str):
            profile_type = profile
        elif isinstance(profile, dict):
            profile_type = profile.get("type", "standard")
            raw_prep = profile.get("preprocessing", {})
            if isinstance(raw_prep, dict):
                prep_params = raw_prep.copy()
            # También absorber posibles parámetros en la raíz del diccionario
            for key in ["invert_polarity", "clahe", "clip_limit", "tile_grid_size", "morph_kernel", "noise_kernel_size", "min_threshold", "blur_kernel"]:
                if key in profile and key not in prep_params:
                    prep_params[key] = profile[key]

        canonical = cls.normalize_profile_name(profile_type)

        # 2. Despacho a la función de pipeline correspondiente
        dispatch_table = {
            "lcd_blue_backlit": cls.pipeline_lcd_blue_backlit,
            "lcd_gray_reflective": cls.pipeline_lcd_gray_reflective,
            "led_7seg_red": cls.pipeline_led_7seg_red,
            "led_7seg_green": cls.pipeline_led_7seg_green,
            "vfd_teal": cls.pipeline_vfd_teal,
            "standard": cls.pipeline_standard,
        }

        pipeline_fn = dispatch_table.get(canonical, cls.pipeline_standard)

        try:
            return pipeline_fn(image, **prep_params)
        except Exception as e:
            # Fallback ultra-seguro ante errores inesperados para nunca tumbar la aplicación
            print(f"[DisplayAdapter] Advertencia en pipeline '{canonical}': {e}. Usando fallback estándar.")
            try:
                return cls.pipeline_standard(image)
            except Exception:
                # Si todo falla, devolver la imagen original o escala de grises
                if image.ndim == 3:
                    return cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
                return image


def preprocess_display_frame(
    image: np.ndarray,
    profile: Optional[Union[Dict[str, Any], str]] = None
) -> np.ndarray:
    """
    Función de utilidad desacoplada para preprocesar un fotograma o sub-ROI recortado
    según la sección 'display_profile' de un archivo .lvtemplate o nombre de preset.

    Parámetros:
    -----------
    image : np.ndarray
        Imagen recortada de la región de interés (ROI) en formato BGR o escala de grises.
    profile : dict | str | None
        Diccionario con la sección 'display_profile' de una plantilla .lvtemplate,
        o cadena de texto indicando el modo (e.g., 'lcd_blue_backlit').
        Ejemplo:
        {
            "type": "lcd_gray_reflective",
            "preprocessing": {
                "clahe": True,
                "clip_limit": 2.0,
                "tile_grid_size": [8, 8],
                "morph_kernel": [2, 1],
                "invert_polarity": False
            }
        }

    Retorna:
    --------
    np.ndarray
        Imagen binaria (uint8, valores 0 y 255) optimizada para inferencia OCR.
    """
    return DisplayAdapter.preprocess(image, profile=profile)
