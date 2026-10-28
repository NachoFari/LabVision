import json
import os

CONFIG_FILE = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "config.json")

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
        if os.path.exists(CONFIG_FILE):
            try:
                with open(CONFIG_FILE, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    merged = DEFAULT_CONFIG.copy()
                    merged.update(data)
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
