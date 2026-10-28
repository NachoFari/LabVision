import os
import csv
import time

class CSVExporter:
    """Exportador ultraligero y rápido a formato CSV delimitado por comas."""
    @staticmethod
    def export(data_rows, output_path, mode="viscometer", metadata=None):
        os.makedirs(os.path.dirname(os.path.abspath(output_path)), exist_ok=True)
        unit = metadata.get("unit", "g") if metadata else "g"

        with open(output_path, mode="w", newline="", encoding="utf-8-sig") as f:
            writer = csv.writer(f)
            writer.writerow([f"# LabVision Pro - Registro {mode.upper()}"])
            writer.writerow([f"# Autor: Creado por NachoFari (https://github.com/NachoFari)"])
            writer.writerow([f"# Fecha: {time.strftime('%Y-%m-%d %H:%M:%S')}"])
            writer.writerow([])

            if mode == "viscometer":
                writer.writerow(["Tiempo_seg", "Timestamp", "Rotor", "Velocidad_RPM", "Viscosidad_mPas", "Torque_Pct", "Confianza_Pct", "Estado"])
                for r in data_rows:
                    c = r.get("confidence")
                    c_str = f"{round(float(c)*100, 1)}%" if c is not None else ""
                    writer.writerow([
                        r.get("time_sec", 0),
                        r.get("timestamp_str", ""),
                        r.get("rotor", ""),
                        r.get("speed_rpm", ""),
                        r.get("viscosity_mpa", ""),
                        r.get("torque_pct", ""),
                        c_str,
                        "DUDOSA" if r.get("is_bad") else "OPTIMA"
                    ])
            else:
                writer.writerow(["Tiempo_seg", "Timestamp", f"Peso_{unit}", "Unidad", "Confianza_Pct", "Estado"])
                for r in data_rows:
                    c = r.get("confidence")
                    c_str = f"{round(float(c)*100, 1)}%" if c is not None else ""
                    writer.writerow([
                        r.get("time_sec", 0),
                        r.get("timestamp_str", ""),
                        r.get("weight", ""),
                        r.get("unit", unit),
                        c_str,
                        "DUDOSA" if r.get("is_bad") else "OPTIMA"
                    ])

        print(f"[LabVision] Archivo CSV guardado en: {output_path}")
        return output_path
