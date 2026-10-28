import json
import os

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CONFIG_FILE = os.path.join(BASE_DIR, "config.json")
LOCAL_OUTPUT = os.path.join(BASE_DIR, "output")

DEFAULT_CONFIG = {
    "discord_webhook": "",
    "default_mode": "viscometer",
    "default_profile": "normal",
    "viscometer": {
        "sample_interval": 1.0,
        "min_confidence": 0.45,
        "auto_track": True
    },
    "balance": {
        "sample_interval": 1.0,
        "unit": "g",
        "min_confidence": 0.45,
        "auto_track": False
    },
    "output_dir": os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "output")
}

class ConfigManager:
    """Gestiona la lectura y persistencia de ajustes en config.json."""
    @staticmethod
    def load():
        local_output = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "output")
        if os.path.exists(CONFIG_FILE):
            try:
                with open(CONFIG_FILE, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    merged = DEFAULT_CONFIG.copy()
                    merged.update(data)

                    # Validar y resolver output_dir
                    out_dir = merged.get("output_dir")
                    if not out_dir:
                        merged["output_dir"] = local_output
                    elif not os.path.isabs(out_dir):
                        # Ruta relativa (ej. "output"), resolverla respecto a la raíz del proyecto
                        merged["output_dir"] = os.path.normpath(os.path.join(BASE_DIR, out_dir))
                    elif not os.path.exists(out_dir):
                        # Fallback automatico si la ruta no existe (ej. E:\reotaxis\output)
                        merged["output_dir"] = local_output

                    try:
                        os.makedirs(merged["output_dir"], exist_ok=True)
                    except Exception:
                        merged["output_dir"] = local_output
                        os.makedirs(local_output, exist_ok=True)

                    return merged
            except Exception:
                return DEFAULT_CONFIG.copy()
        return DEFAULT_CONFIG.copy()

    @staticmethod
    def save(new_config):
        try:
            with open(CONFIG_FILE, "w", encoding="utf-8") as f:
                json.dump(new_config, f, indent=4, ensure_ascii=False)
            return True
        except Exception as e:
            print(f"[ConfigManager] Error guardando config: {e}")
            return False
