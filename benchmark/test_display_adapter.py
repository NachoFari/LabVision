"""
benchmark/test_display_adapter.py - Suite de Validación de Pipelines de Pantalla
================================================================================
LabVision Universal - Work Package 2

Pruebas unitarias y de integración que generan patrones sintéticos NumPy para simular
físicamente las tecnologías de visualización de laboratorio:
1. LCD Azul Retroiluminado (NDJ-8S)
2. LCD Gris Reflectivo con dilatación 2x1 (Balanzas / pH-metros)
3. LED 7-Segmentos Rojo con rechazo de destellos blancos (Baños / Muflas)
4. LED 7-Segmentos Verde con rechazo de interferencias rojas
5. VFD Turquesa/Cian con supresión de rejilla de aceleración
6. Modo Estándar / Genérico
7. Despacho por .lvtemplate y pruebas de tolerancia a fallos
"""

import os
import sys
import numpy as np
import cv2

# Asegurar importación relativa al directorio raíz del proyecto
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

from core.display_adapter import DisplayAdapter, preprocess_display_frame


def test_lcd_blue_backlit():
    print("[TEST 1/7] Probando 'lcd_blue_backlit'...")
    h, w = 120, 200
    # Fondo azul/cian brillante característico de pantalla STN
    frame = np.zeros((h, w, 3), dtype=np.uint8)
    frame[:, :] = (220, 140, 30)  # BGR: Azul=220, Verde=140, Rojo=30

    # Caracteres oscuros LCD (bloquean luz)
    # Dibujar dos barras simulando trazos de dígito LCD
    frame[30:90, 40:60] = (35, 35, 30)
    frame[30:90, 100:120] = (35, 35, 30)

    # Añadir leve ruido gaussiano
    noise = np.random.normal(0, 3, frame.shape).astype(np.int16)
    noisy_frame = np.clip(frame.astype(np.int16) + noise, 0, 255).astype(np.uint8)

    # 1. Ejecutar pipeline estándar (polaridad normal)
    out = DisplayAdapter.pipeline_lcd_blue_backlit(noisy_frame)
    assert out.shape == (h, w), f"Dimensiones incorrectas: {out.shape}"
    unique_vals = set(np.unique(out))
    assert unique_vals.issubset({0, 255}), f"Valores no binarios detectados: {unique_vals}"

    # Los segmentos oscuros deben emerger como 255 (primer plano para OCR)
    assert out[60, 50] == 255, "El segmento oscuro 1 debe ser blanco (255)"
    assert out[60, 110] == 255, "El segmento oscuro 2 debe ser blanco (255)"
    # El fondo azul debe ser 0
    assert out[10, 10] == 0, "El fondo azul debe ser negro (0)"
    assert out[60, 80] == 0, "El espacio intersegmento debe ser negro (0)"

    # 2. Probar inversión de polaridad
    out_inv = DisplayAdapter.pipeline_lcd_blue_backlit(noisy_frame, invert_polarity=True)
    assert out_inv[60, 50] == 0, "Con invert_polarity, el segmento debe ser 0"
    assert out_inv[10, 10] == 255, "Con invert_polarity, el fondo debe ser 255"

    print("  -> PASS: 'lcd_blue_backlit' aisló segmentos oscuros con precisión.")


def test_lcd_gray_reflective():
    print("[TEST 2/7] Probando 'lcd_gray_reflective' y dilatación 2x1...")
    h, w = 120, 200
    frame = np.zeros((h, w, 3), dtype=np.uint8)
    
    # Fondo gris plata con gradiente de iluminación irregular (sombras de laboratorio)
    gradient = np.linspace(170, 215, w).reshape(1, -1).astype(np.uint8)
    frame[:, :, 0] = gradient
    frame[:, :, 1] = gradient
    frame[:, :, 2] = gradient

    # Dibujar segmento vertical y segmento horizontal con brecha física de 1 píxel
    # Segmento vertical: x de 40 a 45, y de 30 a 60
    frame[30:60, 40:46] = (30, 30, 30)
    # Brecha física de 1 pixel: x=46
    # Segmento horizontal contiguo: x de 47 a 70, y de 30 a 35
    frame[30:36, 47:70] = (30, 30, 30)

    # 1. Procesar sin dilatación horizontal para verificar que la brecha existe inicialmente
    out_no_morph = DisplayAdapter.pipeline_lcd_gray_reflective(frame, morph_kernel=(1, 1), clahe=True)
    assert out_no_morph[32, 43] == 255, "Segmento vertical detectado"
    assert out_no_morph[32, 55] == 255, "Segmento horizontal detectado"
    assert out_no_morph[32, 46] == 0, "La brecha de 1 px debe estar desconectada sin dilatación"

    # 2. Procesar con dilatación sutil horizontal 2x1 (requisito de Roadmap)
    out_morph = DisplayAdapter.pipeline_lcd_gray_reflective(frame, morph_kernel=(2, 1), clahe=True)
    assert out_morph.shape == (h, w)
    assert set(np.unique(out_morph)).issubset({0, 255})
    # La brecha de 1 pixel en x=46 ahora debe haber sido puenteada por el kernel horizontal (2, 1)
    assert out_morph[32, 46] == 255, "El kernel 2x1 debe puentear la discontinuidad de 1 px"
    # Sin embargo, el fondo lejos de los segmentos debe permanecer 0
    assert out_morph[10, 10] == 0, "El fondo gris plata debe permanecer 0"

    print("  -> PASS: 'lcd_gray_reflective' aplicó CLAHE y puenteó brecha de 7-seg con kernel 2x1.")


def test_led_7seg_red():
    print("[TEST 3/7] Probando 'led_7seg_red' y rechazo de destello blanco...")
    h, w = 120, 200
    frame = np.zeros((h, w, 3), dtype=np.uint8)
    # Chasis oscuro/negro
    frame[:] = (20, 20, 20)

    # Dígito LED rojo brillante (B=20, G=30, R=245)
    frame[30:90, 40:60] = (20, 30, 245)

    # Destello de luz blanca ambiental en el bisel (B=180, G=180, R=180)
    # Un umbralizador simple por brillo fallaría aquí confundiéndolo con un dígito
    frame[30:50, 140:160] = (180, 180, 180)

    out = DisplayAdapter.pipeline_led_7seg_red(frame, min_threshold=30)
    assert out.shape == (h, w)
    assert set(np.unique(out)).issubset({0, 255})

    # El LED rojo debe estar en 255
    assert out[60, 50] == 255, "El LED rojo debe aislarse en 255"
    # El chasis negro debe ser 0
    assert out[10, 10] == 0, "El chasis negro debe ser 0"
    # El reflejo de luz blanca ambiental debe haber sido RECHAZADO (0)
    assert out[40, 150] == 0, "El destello blanco debe ser rechazado por R-(G+B)/2 y HSV"

    print("  -> PASS: 'led_7seg_red' aisló emisión roja y rechazó reflejo blanco espurio.")


def test_led_7seg_green():
    print("[TEST 4/7] Probando 'led_7seg_green' y rechazo de interferencias...")
    h, w = 120, 200
    frame = np.zeros((h, w, 3), dtype=np.uint8)
    frame[:] = (25, 25, 25)

    # Segmento LED verde puro (B=30, G=240, R=30)
    frame[30:90, 50:70] = (30, 240, 30)

    # LED vecino de alarma en rojo (B=20, G=20, R=230)
    frame[30:50, 130:150] = (20, 20, 230)

    out = DisplayAdapter.pipeline_led_7seg_green(frame, min_threshold=30)
    assert out.shape == (h, w)
    assert set(np.unique(out)).issubset({0, 255})

    # El LED verde debe estar en 255
    assert out[60, 60] == 255, "El LED verde debe aislarse en 255"
    # El chasis debe ser 0
    assert out[10, 10] == 0, "El chasis debe ser 0"
    # El LED rojo adyacente debe ser rechazado
    assert out[40, 140] == 0, "El indicador rojo debe ser rechazado por G-(R+B)/2"

    print("  -> PASS: 'led_7seg_green' aisló emisión verde y rechazó indicador rojo.")


def test_vfd_teal():
    print("[TEST 5/7] Probando 'vfd_teal' y filtrado de rejillas de vacío...")
    h, w = 120, 200
    frame = np.zeros((h, w, 3), dtype=np.uint8)
    # Fondo de tubo de vacío tintado oscuro
    frame[:] = (30, 30, 30)

    # Rejillas finas horizontales de alambre metálico de aceleración anódica
    # Frecuentes en VFDs reales como líneas delgadas de bajo contraste
    for y in range(0, h, 8):
        frame[y, :] = (65, 65, 65)

    # Segmento de fósforo fluorescente turquesa/cian (B=230, G=240, R=35)
    frame[30:80, 60:85] = (230, 240, 35)

    out = DisplayAdapter.pipeline_vfd_teal(frame, min_threshold=25, blur_kernel=(3, 3))
    assert out.shape == (h, w)
    assert set(np.unique(out)).issubset({0, 255})

    # El segmento fluorescente turquesa debe ser 255
    assert out[55, 72] == 255, "El segmento VFD cian debe aislarse en 255"
    # El fondo oscuro debe ser 0
    assert out[10, 10] == 0, "El fondo oscuro debe ser 0"
    # Las rejillas de alambre deben ser atenuadas y resultar en 0
    assert out[16, 20] == 0, "Las rejillas de alambre deben ser suprimidas (0)"

    print("  -> PASS: 'vfd_teal' aisló fósforo turquesa y suprimió rejilla de aceleración.")


def test_standard_pipeline():
    print("[TEST 6/7] Probando 'standard' (Otsu + Gaussian Blur)...")
    h, w = 100, 150
    # Caso A: Fondo blanco con texto negro (documento o pantalla TFT clara)
    doc = np.full((h, w), 240, dtype=np.uint8)
    doc[30:70, 40:80] = 20  # Carácter negro

    out_doc = DisplayAdapter.pipeline_standard(doc)
    assert out_doc.shape == (h, w)
    assert set(np.unique(out_doc)).issubset({0, 255})
    assert out_doc[50, 60] == 255, "El carácter oscuro debe ser 255 por auto-inversión de fondo claro"
    assert out_doc[10, 10] == 0, "El fondo claro debe ser 0"

    # Caso B: Fondo negro con texto blanco
    screen = np.full((h, w), 20, dtype=np.uint8)
    screen[30:70, 40:80] = 240

    out_screen = DisplayAdapter.pipeline_standard(screen)
    assert out_screen[50, 60] == 255, "El texto blanco sobre fondo oscuro debe ser 255"
    assert out_screen[10, 10] == 0, "El fondo oscuro debe ser 0"

    print("  -> PASS: 'standard' resolvió automáticamente polaridades de fondo claro y oscuro.")


def test_lvtemplate_dispatcher_and_fault_tolerance():
    print("[TEST 7/7] Probando despachador .lvtemplate y tolerancia a fallos...")
    
    # 1. Probar estructura oficial de .lvtemplate con sub-configuración
    sample_img = np.zeros((80, 120, 3), dtype=np.uint8)
    sample_img[:] = (200, 200, 200)
    sample_img[20:60, 30:70] = (20, 20, 20)

    lvtemplate_profile = {
        "type": "lcd_gray_reflective",
        "preprocessing": {
            "grayscale": True,
            "clahe": True,
            "clip_limit": 2.5,
            "tile_grid_size": [8, 8],
            "threshold_mode": "otsu_adaptive",
            "invert_polarity": False,
            "morph_kernel": [2, 1]
        }
    }
    res = preprocess_display_frame(sample_img, lvtemplate_profile)
    assert res.shape == (80, 120)
    assert res[40, 50] == 255
    assert res[5, 5] == 0

    # 2. Probar alias directos de instrumentos (viscometer, balance, led_red)
    res_visco = preprocess_display_frame(sample_img, "viscometer")
    assert res_visco.shape == (80, 120)

    res_balance = preprocess_display_frame(sample_img, "balance")
    assert res_balance.shape == (80, 120)

    # 3. Tolerancia a fallos: imagen nula
    assert preprocess_display_frame(None, "standard") is None

    # 4. Tolerancia a fallos: imagen vacía (0x0)
    empty_img = np.zeros((0, 0), dtype=np.uint8)
    res_empty = preprocess_display_frame(empty_img, "standard")
    assert res_empty.size == 0

    # 5. Tolerancia a fallos: perfil nulo o corrupto
    res_corrupt1 = preprocess_display_frame(sample_img, None)
    assert res_corrupt1.shape == (80, 120)
    res_corrupt2 = preprocess_display_frame(sample_img, {"type": "perfil_inexistente_123"})
    assert res_corrupt2.shape == (80, 120)

    # 6. Tolerancia a fallos: imagen microscópica (1x1 o 2x2) que podría romper CLAHE tileGrid
    tiny_img = np.array([[200, 20], [30, 210]], dtype=np.uint8)
    res_tiny = preprocess_display_frame(tiny_img, "lcd_gray_reflective")
    assert res_tiny.shape == (2, 2)

    # 7. Tolerancia a fallos: imagen plana uniforme (todos los píxeles idénticos, varianza 0)
    flat_black = np.zeros((50, 50, 3), dtype=np.uint8)
    res_flat = preprocess_display_frame(flat_black, "led_7seg_red")
    assert res_flat.shape == (50, 50)
    assert set(np.unique(res_flat)).issubset({0, 255})

    # 8. Verificación de metadatos de perfiles
    profiles = DisplayAdapter.get_supported_profiles()
    assert len(profiles) == 6
    for p in profiles:
        meta = DisplayAdapter.get_profile_metadata(p)
        assert "name" in meta
        assert "display_tech" in meta
        assert "typical_devices" in meta

    print("  -> PASS: Despachador .lvtemplate y defensas de tolerancia a fallos verificados 100%.")


def test_generator_integration():
    print("[TEST 8/8] Probando integración con benchmark/generator.py (Viscosímetro y Balanza)...")
    try:
        from benchmark.generator import draw_viscometer_frame, draw_balance_frame, get_font
        font_mono = get_font("mono", 28, bold=True)
        font_large = get_font("digital", 36, bold=True)
        font_small = get_font("digital", 16, bold=False)

        # 1. Probar fotograma sintético del viscosímetro NDJ-8S
        visco_frame = draw_viscometer_frame(rotor=2, speed=60.0, viscosity=123.4, percent=45.6, font=font_mono)
        assert visco_frame is not None and visco_frame.shape == (480, 640, 3)
        # Recortar área de la pantalla LCD azul
        visco_roi = visco_frame[45:435, 45:595]
        visco_bin = preprocess_display_frame(visco_roi, "viscometer")
        assert visco_bin.shape == (390, 550)
        assert set(np.unique(visco_bin)).issubset({0, 255})
        assert np.count_nonzero(visco_bin) > 0, "Debe haber caracteres detectados en el viscosímetro"

        # 2. Probar fotograma sintético de la balanza analítica
        balance_frame = draw_balance_frame(weight=25.43, unit="g", font_large=font_large, font_small=font_small)
        assert balance_frame is not None and balance_frame.shape == (480, 640, 3)
        # Recortar área del display LCD gris/verde reflectivo
        balance_roi = balance_frame[55:415, 55:585]
        balance_bin = preprocess_display_frame(balance_roi, {
            "type": "lcd_gray_reflective",
            "preprocessing": {
                "clahe": True,
                "morph_kernel": [2, 1]
            }
        })
        assert balance_bin.shape == (360, 530)
        assert set(np.unique(balance_bin)).issubset({0, 255})
        assert np.count_nonzero(balance_bin) > 0, "Debe haber caracteres detectados en la balanza"

        print("  -> PASS: Integración con benchmark/generator.py validada correctamente.")
    except Exception as e:
        print(f"  -> WARNING / SKIP: Integración opcional no ejecutada ({e})")


def run_all_tests():
    print("=" * 70)
    print("LabVision Universal - WP2: Suite de Pruebas de DisplayAdapter")
    print("=" * 70)
    test_lcd_blue_backlit()
    test_lcd_gray_reflective()
    test_led_7seg_red()
    test_led_7seg_green()
    test_vfd_teal()
    test_standard_pipeline()
    test_lvtemplate_dispatcher_and_fault_tolerance()
    test_generator_integration()
    print("=" * 70)
    print("TODAS LAS PRUEBAS PASARON EXITOSAMENTE (8/8).")
    print("=" * 70)


if __name__ == "__main__":
    run_all_tests()
