import os
import csv
import time

class CSVExporter:
    """Exportador ultraligero y rápido a formato CSV delimitado por comas con filtrado de columnas."""
    @staticmethod
    def export(data_rows, output_path, mode="viscometer", metadata=None, selected_columns=None):
        """
        Exporta las filas a un archivo CSV.
        
        :param data_rows: Lista de diccionarios con los datos leídos.
        :param output_path: Ruta del archivo CSV destino.
        :param mode: Modo de instrumento ('viscometer', 'balance', 'universal', etc.)
        :param metadata: Metadatos adicionales (unidad, nombre del instrumento, etc.)
        :param selected_columns: Lista de nombres de columnas a exportar, o None/'all' para exportar todas.
        """
        os.makedirs(os.path.dirname(os.path.abspath(output_path)), exist_ok=True)
        metadata = metadata or {}
        unit = metadata.get("unit", "g")

        # 1. Determinar todas las columnas disponibles según el modo o datos dinámicos
        if mode == "viscometer":
            full_columns = [
                ("Tiempo_seg", lambda r: r.get("time_sec", 0)),
                ("Timestamp", lambda r: r.get("timestamp_str", "")),
                ("Rotor", lambda r: r.get("rotor", "")),
                ("Velocidad_RPM", lambda r: r.get("speed_rpm", "")),
                ("Viscosidad_mPas", lambda r: r.get("viscosity_mpa", "")),
                ("Torque_Pct", lambda r: r.get("torque_pct", "")),
                ("Confianza_Pct", lambda r: f"{round(float(r['confidence'])*100, 1)}%" if r.get("confidence") is not None else ""),
                ("Estado", lambda r: "DUDOSA" if r.get("is_bad") else "OPTIMA")
            ]
        elif mode == "balance":
            full_columns = [
                ("Tiempo_seg", lambda r: r.get("time_sec", 0)),
                ("Timestamp", lambda r: r.get("timestamp_str", "")),
                (f"Peso_{unit}", lambda r: r.get("weight", "")),
                ("Unidad", lambda r: r.get("unit", unit)),
                ("Confianza_Pct", lambda r: f"{round(float(r['confidence'])*100, 1)}%" if r.get("confidence") is not None else ""),
                ("Estado", lambda r: "DUDOSA" if r.get("is_bad") else "OPTIMA")
            ]
        else:
            # Modo universal o plantilla dinámica: detectar claves de data_rows
            all_keys = []
            if data_rows:
                # Priorizar tiempo y timestamp primero
                base_keys = ["time_sec", "timestamp_str"]
                for k in base_keys:
                    if any(k in r for r in data_rows):
                        all_keys.append(k)
                # Luego variables dinámicas
                for r in data_rows:
                    for k in r.keys():
                        if k not in all_keys and k not in ("is_bad", "confidence", "raw_text"):
                            all_keys.append(k)
                # Finalmente confianza y estado
                all_keys.extend(["confidence", "is_bad"])
            else:
                all_keys = ["time_sec", "timestamp_str"]

            full_columns = []
            for k in all_keys:
                if k == "time_sec":
                    full_columns.append(("Tiempo_seg", lambda r: r.get("time_sec", 0)))
                elif k == "timestamp_str":
                    full_columns.append(("Timestamp", lambda r: r.get("timestamp_str", "")))
                elif k == "confidence":
                    full_columns.append(("Confianza_Pct", lambda r: f"{round(float(r['confidence'])*100, 1)}%" if r.get("confidence") is not None else ""))
                elif k == "is_bad":
                    full_columns.append(("Estado", lambda r: "DUDOSA" if r.get("is_bad") else "OPTIMA"))
                else:
                    col_name = k.capitalize()
                    full_columns.append((col_name, lambda r, key=k: r.get(key, "")))

        # 2. Aplicar filtro de columnas seleccionadas si se especificó
        if selected_columns and selected_columns != "all" and isinstance(selected_columns, (list, tuple, set)):
            # Normalizar nombres para matching flexible (ignorar mayúsculas y guiones bajos)
            norm_selected = {str(c).strip().lower().replace("_", "") for c in selected_columns}
            filtered_columns = [
                (col_name, extractor) for col_name, extractor in full_columns
                if col_name.lower().replace("_", "") in norm_selected
            ]
            if filtered_columns:
                active_columns = filtered_columns
            else:
                active_columns = full_columns
        else:
            active_columns = full_columns

        # 3. Escribir archivo CSV
        with open(output_path, mode="w", newline="", encoding="utf-8-sig") as f:
            writer = csv.writer(f)
            writer.writerow([f"# LabVision Pro - Registro Científico ({mode.upper()})"])
            writer.writerow([f"# Autor: Creado por NachoFari (https://github.com/NachoFari)"])
            writer.writerow([f"# Fecha: {time.strftime('%Y-%m-%d %H:%M:%S')}"])
            writer.writerow([f"# Columnas exportadas: {len(active_columns)} de {len(full_columns)}"])
            writer.writerow([])

            # Encabezados
            writer.writerow([col_name for col_name, _ in active_columns])

            # Datos
            for row in data_rows:
                writer.writerow([extractor(row) for _, extractor in active_columns])

        print(f"[LabVision] Archivo CSV guardado en: {output_path} ({len(active_columns)} columnas)")
        return output_path

