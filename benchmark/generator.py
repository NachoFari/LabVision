"""
generator.py - Generador de Videos Sintéticos de Laboratorio
Simula con alta fidelidad visual las pantallas de:
1. Viscosímetro Rotacional Digital NDJ-8S (Pantalla LCD azul de matriz de puntos)
2. Balanza / Gramera Digital de Precisión (Pantalla LCD verde/gris digital)
"""

import os
import sys
import math
import cv2
import numpy as np
from PIL import Image, ImageDraw, ImageFont

# Dimensiones estándar para videos de simulación
FRAME_WIDTH = 640
FRAME_HEIGHT = 480

def get_font(font_type="mono", size=32, bold=True):
    """
    Carga fuentes limpias y legibles disponibles en Windows, con fallbacks estándar.
    """
    if font_type == "mono":
        candidates = [
            r"C:\Windows\Fonts\consolab.ttf" if bold else r"C:\Windows\Fonts\consola.ttf",
            r"C:\Windows\Fonts\consola.ttf",
            r"C:\Windows\Fonts\lucon.ttf",
            r"C:\Windows\Fonts\courbd.ttf",
            r"C:\Windows\Fonts\arialbd.ttf"
        ]
    else:  # sans-serif / digital
        candidates = [
            r"C:\Windows\Fonts\arialbd.ttf" if bold else r"C:\Windows\Fonts\arial.ttf",
            r"C:\Windows\Fonts\segoeuib.ttf" if bold else r"C:\Windows\Fonts\segoeui.ttf",
            r"C:\Windows\Fonts\calibrib.ttf",
            r"C:\Windows\Fonts\arial.ttf"
        ]

    for path in candidates:
        if os.path.exists(path):
            try:
                return ImageFont.truetype(path, size)
            except Exception:
                pass
    return ImageFont.load_default()

def draw_viscometer_frame(rotor: int, speed: float, viscosity: float, percent: float, font) -> np.ndarray:
    """
    Renderiza un fotograma simulando la pantalla azul del viscosímetro NDJ-8S:
    - Carcasa mate de instrumento con bisel
    - Pantalla LCD con fondo azul intenso y viñeteado
    - Matriz de puntos sutil
    - 4 filas: ROTOR, SPEED, DATA (mPa.s), PERCENT (%)
    """
    frame = np.zeros((FRAME_HEIGHT, FRAME_WIDTH, 3), dtype=np.uint8)
    
    # 1. Carcasa de instrumento (Gris pizarra mate)
    frame[:] = (32, 34, 38)
    
    # Rótulo de marca en carcasa
    cv2.putText(frame, "NDJ-8S DIGITAL ROTATIONAL VISCOMETER", (50, 30), 
                cv2.FONT_HERSHEY_SIMPLEX, 0.5, (160, 165, 175), 1, cv2.LINE_AA)
    
    # Indicador LED de encendido
    cv2.circle(frame, (595, 25), 5, (0, 220, 100), -1, cv2.LINE_AA)
    cv2.circle(frame, (595, 25), 6, (0, 150, 70), 1, cv2.LINE_AA)

    # 2. Área de la Pantalla LCD
    lx, ly, lw, lh = 45, 45, 550, 390
    
    # Bordes de bisel 3D
    cv2.rectangle(frame, (lx - 6, ly - 6), (lx + lw + 6, ly + lh + 6), (18, 20, 22), 2)
    cv2.rectangle(frame, (lx - 2, ly - 2), (lx + lw + 2, ly + lh + 2), (70, 75, 80), 2)

    # Gradiente azul característico de la retroiluminación NDJ-8S
    y_coords = np.linspace(-1, 1, lh).reshape(-1, 1)
    x_coords = np.linspace(-1, 1, lw).reshape(1, -1)
    dist = np.sqrt(x_coords**2 + y_coords**2)
    vignette = 1.0 - 0.18 * np.clip(dist, 0, 1)

    lcd_b = np.clip(215 * vignette, 0, 255).astype(np.uint8)
    lcd_g = np.clip(100 * vignette, 0, 255).astype(np.uint8)
    lcd_r = np.clip(22 * vignette, 0, 255).astype(np.uint8)

    lcd_panel = np.stack([lcd_b, lcd_g, lcd_r], axis=-1)
    frame[ly:ly+lh, lx:lx+lw] = lcd_panel

    # 3. Dibujar textos en matriz de puntos con PIL
    pil_frame = Image.fromarray(cv2.cvtColor(frame, cv2.COLOR_BGR2RGB))
    draw = ImageDraw.Draw(pil_frame)

    # Color de texto iluminado: Blanco azulado brillante
    dot_color = (248, 252, 255)

    row_y0 = ly + 36
    row_spacing = 86

    # Línea 1: ROTOR
    draw.text((lx + 45, row_y0), f"ROTOR  {rotor} #", fill=dot_color, font=font)
    
    # Línea 2: SPEED
    draw.text((lx + 45, row_y0 + row_spacing), f"SPEED  {speed:.0f} RPM", fill=dot_color, font=font)
    
    # Línea 3: DATA (viscosidad en mPa.s)
    draw.text((lx + 45, row_y0 + row_spacing * 2), f"DATA  {viscosity:.1f} mPa.s", fill=dot_color, font=font)
    
    # Línea 4: PERCENT (torque en %)
    draw.text((lx + 45, row_y0 + row_spacing * 3), f"PERCENT  {percent:.1f} %", fill=dot_color, font=font)

    res = cv2.cvtColor(np.array(pil_frame), cv2.COLOR_RGB2BGR)

    # 4. Textura de matriz de puntos LCD
    grid_mask = np.ones((lh, lw), dtype=np.float32)
    grid_mask[::3, :] *= 0.88
    grid_mask[:, ::3] *= 0.88
    
    lcd_region = res[ly:ly+lh, lx:lx+lw].astype(np.float32)
    lcd_textured = (lcd_region * grid_mask[:, :, None]).clip(0, 255).astype(np.uint8)
    res[ly:ly+lh, lx:lx+lw] = lcd_textured

    # Reflejo sutil antirreflejo en la parte superior
    for sy in range(ly + 5, ly + 25):
        alpha = 0.08 * (1.0 - (sy - ly) / 20.0)
        res[sy, lx+10:lx+lw-10] = cv2.addWeighted(
            res[sy, lx+10:lx+lw-10], 1.0 - alpha,
            np.full_like(res[sy, lx+10:lx+lw-10], 255), alpha, 0
        )

    return res

def draw_balance_frame(weight: float, unit: str, font_large, font_small) -> np.ndarray:
    """
    Renderiza un fotograma simulando la pantalla digital de una balanza/gramera:
    - Carcasa de laboratorio
    - Pantalla LCD verde claro/gris salvia
    - Indicador de estabilidad 'STABLE' y 'ZERO'
    - Número de peso grande y legible con decimales (ej. 12.50 g)
    """
    frame = np.zeros((FRAME_HEIGHT, FRAME_WIDTH, 3), dtype=np.uint8)
    
    # 1. Carcasa de la balanza (Gris plata / laboratorio)
    frame[:] = (40, 44, 48)

    # Rótulo institucional en carcasa
    cv2.putText(frame, "LABORATORY DIGITAL PRECISION BALANCE", (60, 35),
                cv2.FONT_HERSHEY_SIMPLEX, 0.52, (185, 190, 200), 1, cv2.LINE_AA)

    # LED indicador de estado
    cv2.circle(frame, (595, 25), 5, (0, 210, 90), -1, cv2.LINE_AA)

    # 2. Área de Pantalla LCD (Panel verde salvia claro de alto contraste)
    lx, ly, lw, lh = 55, 55, 530, 360
    cv2.rectangle(frame, (lx - 6, ly - 6), (lx + lw + 6, ly + lh + 6), (20, 22, 25), 2)
    cv2.rectangle(frame, (lx - 2, ly - 2), (lx + lw + 2, ly + lh + 2), (90, 95, 100), 2)

    # Fondo LCD verde salvia con leve degradé de iluminación
    y_coords = np.linspace(-1, 1, lh).reshape(-1, 1)
    dist = np.abs(y_coords)
    lum_factor = 1.0 - 0.08 * dist

    lcd_b = np.clip(180 * lum_factor, 0, 255).astype(np.uint8)
    lcd_g = np.clip(212 * lum_factor, 0, 255).astype(np.uint8)
    lcd_r = np.clip(185 * lum_factor, 0, 255).astype(np.uint8)

    lcd_panel = np.stack([lcd_b, lcd_g, lcd_r], axis=-1)
    frame[ly:ly+lh, lx:lx+lw] = lcd_panel

    # 3. Dibujar textos e indicadores digitales con PIL
    pil_frame = Image.fromarray(cv2.cvtColor(frame, cv2.COLOR_BGR2RGB))
    draw = ImageDraw.Draw(pil_frame)

    text_color = (12, 22, 12)       # Tinta oscura LCD
    sub_color = (35, 50, 35)        # Rótulos secundarios

    # Indicadores superiores de estado
    draw.text((lx + 40, ly + 30), "STABLE", fill=sub_color, font=font_small)
    draw.text((lx + lw - 140, ly + 30), "ZERO / NET", fill=sub_color, font=font_small)

    # Lectura principal: peso grande con decimales
    reading_str = f"{weight:.2f} {unit}"
    draw.text((lx + 80, ly + 125), reading_str, fill=text_color, font=font_large)

    # Indicador inferior de escala y capacidad
    draw.text((lx + 40, ly + lh - 45), f"Max: 500{unit}   d=0.01{unit}", fill=sub_color, font=font_small)

    res = cv2.cvtColor(np.array(pil_frame), cv2.COLOR_RGB2BGR)

    # 4. Textura leve de cristal LCD
    glass_mask = np.ones((lh, lw), dtype=np.float32)
    glass_mask[::2, :] *= 0.96
    lcd_region = res[ly:ly+lh, lx:lx+lw].astype(np.float32)
    res[ly:ly+lh, lx:lx+lw] = (lcd_region * glass_mask[:, :, None]).clip(0, 255).astype(np.uint8)

    return res

def generate_viscometer_video(output_path: str, duration_sec: int = 6, fps: int = 10) -> list:
    """
    Genera un video sintético simulando la pantalla azul del viscosímetro NDJ-8S.
    - Rotor: 2 #
    - Speed: 12 RPM
    - Data: Variando suavemente entre 1100 y 1150 mPa.s
    - Percent: Variando suavemente entre 42 y 46%
    
    Retorna la lista de Ground Truth (valores exactos generados fotograma a fotograma).
    """
    total_frames = int(duration_sec * fps)
    os.makedirs(os.path.dirname(os.path.abspath(output_path)), exist_ok=True)

    print(f"[Generator] Creando video de Viscosimetro NDJ-8S: {output_path}")
    print(f"  Duracion: {duration_sec}s | FPS: {fps} | Cuadros totales: {total_frames}")

    font = get_font(font_type="mono", size=34, bold=True)
    fourcc = cv2.VideoWriter_fourcc(*'mp4v')
    out = cv2.VideoWriter(output_path, fourcc, float(fps), (FRAME_WIDTH, FRAME_HEIGHT))

    ground_truth = []

    for frame_idx in range(total_frames):
        t = frame_idx / float(fps)
        
        # Variación senoidal suave
        # Data entre 1100.0 y 1150.0 mPa.s
        # Percent entre 42.0 y 46.0 %
        phase = 2.0 * math.pi * (frame_idx / max(1, total_frames - 1))
        norm_val = 0.5 + 0.5 * math.sin(phase)
        
        viscosity = round(1100.0 + 50.0 * norm_val, 1)
        percent = round(42.0 + 4.0 * norm_val, 1)
        rotor = 2
        speed = 12.0

        frame_bgr = draw_viscometer_frame(rotor, speed, viscosity, percent, font)
        out.write(frame_bgr)

        ground_truth.append({
            "frame_idx": frame_idx,
            "time_sec": round(t, 2),
            "rotor": rotor,
            "speed_rpm": speed,
            "viscosity_mpa": viscosity,
            "torque_pct": percent
        })

    out.release()
    file_size_kb = os.path.getsize(output_path) / 1024.0
    print(f"[Generator] Video Viscosimetro guardado exitosamente ({file_size_kb:.1f} KB)\n")
    return ground_truth

def generate_balance_video(output_path: str, duration_sec: int = 6, fps: int = 10, unit: str = 'g') -> list:
    """
    Genera un video sintético simulando la pantalla digital de una balanza/gramera.
    - Pantalla LCD verde claro/gris con visualización digital
    - Peso aumentando suavemente de 12.50 g a 18.25 g con 2 decimales
    
    Retorna la lista de Ground Truth (valores exactos generados fotograma a fotograma).
    """
    total_frames = int(duration_sec * fps)
    os.makedirs(os.path.dirname(os.path.abspath(output_path)), exist_ok=True)

    print(f"[Generator] Creando video de Balanza / Gramera: {output_path}")
    print(f"  Duracion: {duration_sec}s | FPS: {fps} | Cuadros totales: {total_frames}")

    font_large = get_font(font_type="sans", size=72, bold=True)
    font_small = get_font(font_type="sans", size=24, bold=True)
    
    fourcc = cv2.VideoWriter_fourcc(*'mp4v')
    out = cv2.VideoWriter(output_path, fourcc, float(fps), (FRAME_WIDTH, FRAME_HEIGHT))

    ground_truth = []

    start_weight = 12.50
    end_weight = 18.25

    for frame_idx in range(total_frames):
        t = frame_idx / float(fps)
        
        # Aumento suave continuo de 12.50 g a 18.25 g
        alpha = frame_idx / float(max(1, total_frames - 1))
        weight = round(start_weight + (end_weight - start_weight) * alpha, 2)

        frame_bgr = draw_balance_frame(weight, unit, font_large, font_small)
        out.write(frame_bgr)

        ground_truth.append({
            "frame_idx": frame_idx,
            "time_sec": round(t, 2),
            "weight": weight,
            "unit": unit
        })

    out.release()
    file_size_kb = os.path.getsize(output_path) / 1024.0
    print(f"[Generator] Video Balanza guardado exitosamente ({file_size_kb:.1f} KB)\n")
    return ground_truth

if __name__ == "__main__":
    out_dir = r"E:\reotaxis\output"
    v_path = os.path.join(out_dir, "benchmark_viscometer.mp4")
    b_path = os.path.join(out_dir, "benchmark_balance.mp4")
    
    gt_v = generate_viscometer_video(v_path, duration_sec=6, fps=10)
    gt_b = generate_balance_video(b_path, duration_sec=6, fps=10, unit='g')
    print("Videos generados correctamente para pruebas.")
