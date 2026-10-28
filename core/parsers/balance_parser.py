import re

class BalanceParser:
    """Extrae con alta precisión el peso (con decimales) y la unidad de medida de balanzas analíticas y de precisión."""
    @staticmethod
    def parse(ocr_results, user_unit="g", min_confidence=0.45):
        raw_lines = []
        confidences = []
        
        for bbox, text, conf in ocr_results:
            clean_text = text.strip()
            if clean_text:
                raw_lines.append(clean_text)
                confidences.append(float(conf))

        full_text = " \n ".join(raw_lines)
        detected_unit = user_unit

        # 1. Detectar unidad de medida (g, kg, mg, dwt, ct, oz, lb)
        unit_match = re.search(r'\b(kg|mg|dwt|ct|oz|lb|g)\b', full_text, re.I)
        if unit_match:
            detected_unit = unit_match.group(1).lower()

        weight = None

        # 2. Búsqueda prioritaria: número seguido de la unidad (ej: "12.50 g", "0.005 kg")
        near_unit = re.search(r'([-+]?\d+(?:[\.,]\d+)?)\s*(?:' + re.escape(detected_unit) + r')\b', full_text, re.I)
        if near_unit:
            raw_val = near_unit.group(1).replace(',', '.')
            try:
                weight = float(raw_val)
            except ValueError:
                pass

        # 3. Si no se encontró pegado a la unidad, buscar tokens puramente numéricos
        if weight is None:
            # Dividir en tokens y normalizar únicamente tokens que son predominantemente dígitos
            candidate_floats = []
            words = full_text.split()
            for w in words:
                # Si contiene letras que no sean de unidades o sufijos, descartar
                cleaned_w = w.replace(',', '.')
                # Sustitución selectiva en dígitos: O -> 0, l/I -> 1 sólo si la mayoría son números
                digit_count = sum(c.isdigit() for c in cleaned_w)
                if digit_count >= 1 or (cleaned_w.startswith(('+', '-')) and len(cleaned_w) > 1):
                    norm_w = cleaned_w.replace('O', '0').replace('o', '0').replace('l', '1').replace('I', '1')
                    match = re.search(r'[-+]?\d+(?:\.\d+)?', norm_w)
                    if match:
                        try:
                            val = float(match.group(0))
                            has_dec = '.' in match.group(0)
                            candidate_floats.append((val, has_dec, len(match.group(0))))
                        except ValueError:
                            pass

            if candidate_floats:
                # Priorizar números que tengan punto decimal explícito
                decimals = [c for c in candidate_floats if c[1]]
                if decimals:
                    # El de mayor longitud/precisión
                    decimals.sort(key=lambda x: x[2], reverse=True)
                    weight = decimals[0][0]
                else:
                    candidate_floats.sort(key=lambda x: x[2], reverse=True)
                    weight = candidate_floats[0][0]

        avg_conf = sum(confidences) / len(confidences) if confidences else 0.0

        is_bad = False
        warning_reason = []

        if weight is None:
            is_bad = True
            warning_reason.append("No se detectó número de peso en la balanza")
        elif avg_conf < min_confidence:
            is_bad = True
            warning_reason.append(f"Confianza baja ({avg_conf*100:.1f}%)")

        return {
            "weight": weight,
            "unit": detected_unit,
            "confidence": round(avg_conf, 3),
            "is_bad": is_bad,
            "warning": " | ".join(warning_reason) if is_bad else "",
            "raw_text": full_text
        }
