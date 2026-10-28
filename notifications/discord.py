import requests
import datetime
import time
import os

class DiscordNotifier:
    """Envía notificaciones enriquecidas (Embeds) a canales de Discord vía Webhooks."""
    def __init__(self, webhook_url=None):
        self.webhook_url = webhook_url.strip() if webhook_url else ""
        self.last_warning_time = 0
        self.warning_cooldown = 8  # segundos entre avisos para evitar saturación de Discord

    def set_webhook(self, url):
        self.webhook_url = url.strip() if url else ""

    def is_configured(self):
        u = (self.webhook_url or "").strip().lower()
        return bool(u and ("discord.com/api/webhooks/" in u or "discordapp.com/api/webhooks/" in u))

    def send_test(self, url=None):
        target_url = (url or self.webhook_url or "").strip()
        if not target_url:
            return False, "URL de webhook no proporcionada"
        
        payload = {
            "username": "LabVision (NachoFari)",
            "avatar_url": "https://raw.githubusercontent.com/NachoFari/LabVision/main/static/lab_badge_256.png",
            "embeds": [{
                "title": "🧪 Conexión Exitosa con LabVision",
                "description": "El sistema de notificaciones está correctamente vinculado y listo para enviar alertas de laboratorio.",
                "color": 3066993,
                "fields": [
                    {"name": "Estado", "value": "🟢 Operativo", "inline": True},
                    {"name": "Autor", "value": "NachoFari", "inline": True}
                ],
                "footer": {"text": "LabVision v0.3 • Automatización de Laboratorio"},
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
            "footer": {"text": "LabVision • Creado por NachoFari"},
            "timestamp": datetime.datetime.now(datetime.timezone.utc).isoformat()
        }
        try:
            requests.post(self.webhook_url, json={"username": "LabVision", "embeds": [embed]}, timeout=5)
        except Exception as e:
            print(f"[Discord] Error notificando inicio: {e}")

    def notify_warning(self, message, current_time_str=""):
        """Envía alerta amarilla ante lecturas dudosas o baja confianza del OCR."""
        if not self.is_configured():
            return
        
        now = time.time()
        if now - self.last_warning_time < self.warning_cooldown:
            return
        self.last_warning_time = now

        embed = {
            "title": "⚠️ Alerta de Calidad de Lectura",
            "description": f"Se detectaron lecturas de baja confianza o pantalla obstruida.\n**Detalle:** {message}",
            "color": 15105570,  # Ámbar / Naranja
            "fields": [
                {"name": "Tiempo Video", "value": current_time_str or "En curso", "inline": True},
                {"name": "Recomendación", "value": "Verificar encuadre, iluminación o vibración.", "inline": False}
            ],
            "footer": {"text": "LabVision Alertas • Creado por NachoFari"},
            "timestamp": datetime.datetime.now(datetime.timezone.utc).isoformat()
        }
        try:
            requests.post(self.webhook_url, json={"username": "LabVision Alertas", "embeds": [embed]}, timeout=5)
        except Exception as e:
            print(f"[Discord] Error notificando advertencia: {e}")

    def notify_error(self, error_title, error_detail, current_time_str=""):
        """Envía alerta roja urgente ante errores críticos o caídas de cámara."""
        if not self.is_configured():
            return

        detail_text = str(error_detail)[:1200]
        embed = {
            "title": f"🚨 Error en Adquisición de Datos: {error_title}",
            "description": f"Ocurrió una falla durante el proceso de adquisición:\n```{detail_text}```",
            "color": 15158332,  # Rojo intenso
            "fields": [
                {"name": "Momento del Fallo", "value": current_time_str or "Al iniciar o conectar", "inline": True},
                {"name": "Acción Sugerida", "value": "Compruebe la conexión USB de la cámara o el formato del archivo.", "inline": False}
            ],
            "footer": {"text": "LabVision Alertas Críticas • Creado por NachoFari"},
            "timestamp": datetime.datetime.now(datetime.timezone.utc).isoformat()
        }
        try:
            requests.post(self.webhook_url, json={"username": "LabVision Alertas", "embeds": [embed]}, timeout=6)
        except Exception as e:
            print(f"[Discord] Error notificando error crítico: {e}")

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
            "description": "Se completó la extracción de datos con éxito y la planilla Excel ha sido generada.",
            "color": 5763719,  # Verde
            "fields": fields,
            "footer": {"text": "LabVision • Creado por NachoFari"},
            "timestamp": datetime.datetime.now(datetime.timezone.utc).isoformat()
        }
        try:
            requests.post(self.webhook_url, json={"username": "LabVision", "embeds": [embed]}, timeout=8)
        except Exception as e:
            print(f"[Discord] Error notificando finalización: {e}")
