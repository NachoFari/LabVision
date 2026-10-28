import requests
import datetime
import time

class DiscordNotifier:
    """Envía notificaciones enriquecidas (Embeds) a canales de Discord vía Webhooks."""
    def __init__(self, webhook_url=None):
        self.webhook_url = webhook_url.strip() if webhook_url else ""
        self.last_warning_time = 0
        self.warning_cooldown = 15  # segundos entre avisos para evitar spam

    def set_webhook(self, url):
        self.webhook_url = url.strip() if url else ""

    def is_configured(self):
        return bool(self.webhook_url and self.webhook_url.startswith("https://discord.com/api/webhooks/"))

    def send_test(self, url=None):
        target_url = url or self.webhook_url
        if not target_url:
            return False, "URL de webhook no proporcionada"
        
        payload = {
            "username": "LabVision Pro (NachoFari)",
            "avatar_url": "https://cdn-icons-png.flaticon.com/512/3067/3067260.png",
            "embeds": [{
                "title": "🧪 Conexión Exitosa con LabVision Pro",
                "description": "El sistema de notificaciones está correctamente vinculado y listo para enviar alertas de laboratorio.",
                "color": 3066993,
                "fields": [
                    {"name": "Estado", "value": "🟢 Operativo", "inline": True},
                    {"name": "Autor", "value": "NachoFari", "inline": True}
                ],
                "footer": {"text": "LabVision Pro • Automatización de Laboratorio"},
                "timestamp": datetime.datetime.now(datetime.timezone.utc).isoformat()
            }]
        }
        try:
            res = requests.post(target_url, json=payload, timeout=8)
            if res.status_code in [200, 204]:
                return True, "Mensaje de prueba enviado exitosamente a Discord."
            return False, f"Discord respondió con error {res.status_code}: {res.text}"
        except Exception as e:
            return False, f"Error de conexión: {str(e)}"

    def notify_start(self, mode_name, source_name, sample_interval, hardware_mode):
        if not self.is_configured():
            return
        
        embed = {
            "title": f"🚀 Procesamiento Iniciado: {mode_name.upper()}",
            "description": f"Se ha comenzado a capturar y procesar datos desde **{source_name}**.",
            "color": 3447003,
            "fields": [
                {"name": "Modo", "value": f"🔬 {mode_name.capitalize()}", "inline": True},
                {"name": "Muestreo", "value": f"⏱️ Cada {sample_interval}s", "inline": True},
                {"name": "Aceleración", "value": f"⚙️ {hardware_mode}", "inline": True}
            ],
            "footer": {"text": "LabVision Pro • Creado por NachoFari"},
            "timestamp": datetime.datetime.now(datetime.timezone.utc).isoformat()
        }
        try:
            requests.post(self.webhook_url, json={"username": "LabVision Pro", "embeds": [embed]}, timeout=5)
        except Exception as e:
            print(f"[Discord] Error notificando inicio: {e}")

    def notify_warning(self, message, current_time_str=""):
        if not self.is_configured():
            return
        
        now = time.time()
        if now - self.last_warning_time < self.warning_cooldown:
            return
        self.last_warning_time = now

        embed = {
            "title": "⚠️ Alerta de Calidad de Lectura",
            "description": f"Se detectaron lecturas de baja confianza o pantalla obstruida.\n**Detalle:** {message}",
            "color": 15105570,
            "fields": [
                {"name": "Tiempo Video", "value": current_time_str or "En curso", "inline": True},
                {"name": "Recomendación", "value": "Verificar encuadre, iluminación o reflejos.", "inline": False}
            ],
            "footer": {"text": "LabVision Alertas • Creado por NachoFari"},
            "timestamp": datetime.datetime.now(datetime.timezone.utc).isoformat()
        }
        try:
            requests.post(self.webhook_url, json={"username": "LabVision Pro", "embeds": [embed]}, timeout=5)
        except Exception as e:
            print(f"[Discord] Error notificando advertencia: {e}")

    def notify_finish(self, mode_name, total_rows, duration_sec, excel_path, stats=None):
        if not self.is_configured():
            return
        
        fields = [
            {"name": "Registros extraídos", "value": f"📊 {total_rows} filas", "inline": True},
            {"name": "Duración", "value": f"⏱️ {duration_sec:.1f} s", "inline": True},
            {"name": "Archivo Excel", "value": f"📁 `{os.path.basename(excel_path)}`", "inline": False}
        ]

        if stats and mode_name == "viscometer":
            if "avg_viscosity" in stats and stats["avg_viscosity"] is not None:
                fields.append({"name": "Viscosidad Promedio", "value": f"🧪 {stats['avg_viscosity']:.1f} mPa·s", "inline": True})
            if "rpm" in stats and stats["rpm"]:
                fields.append({"name": "Velocidad (RPM)", "value": f"🔄 {stats['rpm']} RPM", "inline": True})
        elif stats and mode_name in ["balance", "precision_balance"]:
            if "final_weight" in stats and stats["final_weight"] is not None:
                fields.append({"name": "Último Peso", "value": f"⚖️ {stats['final_weight']} {stats.get('unit', 'g')}", "inline": True})

        embed = {
            "title": f"✅ Procesamiento Finalizado: {mode_name.upper()}",
            "description": "Se completó la extracción de datos con éxito y la tabla Excel ha sido generada.",
            "color": 5763719,
            "fields": fields,
            "footer": {"text": "LabVision Pro • Creado por NachoFari"},
            "timestamp": datetime.datetime.now(datetime.timezone.utc).isoformat()
        }
        try:
            requests.post(self.webhook_url, json={"username": "LabVision Pro", "embeds": [embed]}, timeout=8)
        except Exception as e:
            print(f"[Discord] Error notificando finalización: {e}")
