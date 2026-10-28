import re

class ViscometerParser:
    """Extrae Rotor, RPM, Viscosidad (mPa·s) y Torque (%) desde las líneas de EasyOCR."""
    @staticmethod
    def parse(ocr_results, min_confidence=0.45):
        raw_lines = []
        confidences = []
        
        for bbox, text, conf in ocr_results:
            clean_text = text.strip()
            if clean_text:
                raw_lines.append(clean_text)
                confidences.append(float(conf))

        full_text = " \n ".join(raw_lines)

        # 1. Rotor
        rotor = None
        rotor_m = re.search(r'ROTOR\s*[\n:]*\s*(\d+)', full_text, re.I)
        if not rotor_m:
            rotor_m = re.search(r'(\d+)\s*#', full_text)
        if rotor_m:
            rotor = int(rotor_m.group(1))

        # 2. Speed (RPM)
        speed = None
        speed_m = re.search(r'SPEED\s*[\n:]*\s*(\d+(?:\.\d+)?)', full_text, re.I)
        if not speed_m:
            speed_m = re.search(r'(\d+(?:\.\d+)?)\s*(?:RPM|RPH)', full_text, re.I)
        if speed_m:
            try:
                speed = float(speed_m.group(1))
            except ValueError:
                pass

        # 3. Data (Viscosidad en mPa·s)
        viscosity = None
        data_m = re.search(r'DATA\s*[\n:]*\s*([\dliIoOsS\.\,\-]+)', full_text, re.I)
        if not data_m:
            data_m = re.search(r'([\dliIoOsS\.\,\-]+)\s*(?:mPa|c[Pp])', full_text, re.I)
        
        if data_m:
            raw_v = data_m.group(1)
            clean_v = raw_v.replace('i', '1').replace('l', '1').replace('I', '1')
            clean_v = clean_v.replace('o', '0').replace('O', '0').replace('s', '5').replace('S', '5')
            clean_v = clean_v.replace(',', '.')
            clean_v = re.sub(r'[^\d\.]', '', clean_v)
            try:
                viscosity = float(clean_v)
            except ValueError:
                pass

        # 4. Percent (Torque %)
        percent = None
        pct_m = re.search(r'PERCENT\s*[\n:]*\s*([\d\.\,\s]+)', full_text, re.I)
        if not pct_m:
            pct_m = re.search(r'([\d\.\,\s]+)%', full_text)
        
        if pct_m:
            raw_p = pct_m.group(1).replace(" ", "").replace(",", ".")
            clean_p = re.sub(r'96$', '', raw_p) # común artefacto de %
            match_num = re.search(r'(\d+(?:\.\d+)?)', clean_p)
            if match_num:
                try:
                    percent = float(match_num.group(1))
                except ValueError:
                    pass

        avg_conf = sum(confidences) / len(confidences) if confidences else 0.0

        is_bad = False
        warning_reason = []

        if viscosity is None:
            is_bad = True
            warning_reason.append("No se detectó Viscosidad (DATA)")
        if percent is None:
            is_bad = True
            warning_reason.append("No se detectó Torque (PERCENT)")
        if avg_conf < min_confidence:
            is_bad = True
            warning_reason.append(f"Confianza baja ({avg_conf*100:.1f}%)")

        return {
            "rotor": rotor,
            "speed_rpm": speed,
            "viscosity_mpa": viscosity,
            "torque_pct": percent,
            "confidence": round(avg_conf, 3),
            "is_bad": is_bad,
            "warning": " | ".join(warning_reason) if is_bad else "",
            "raw_text": full_text
        }
