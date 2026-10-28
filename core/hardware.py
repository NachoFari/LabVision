import os
import torch

class HardwareDetector:
    """Gestiona la detección y optimización de hardware (GPU vs CPU Notebook)."""
    @staticmethod
    def detect(force_cpu=False):
        if force_cpu:
            has_gpu = False
            desc = "Modo CPU Forzado (Prueba Notebook)"
        else:
            has_gpu = torch.cuda.is_available()
            if not has_gpu:
                desc = "Modo CPU Optimizado (Notebook)"
            else:
                gpu_name = torch.cuda.get_device_name(0)
                desc = f"Modo Aceleración GPU ({gpu_name})"

        if not has_gpu:
            try:
                # Asignar hilos óptimos en CPU de notebook
                threads = max(1, (os.cpu_count() or 4) - 1)
                torch.set_num_threads(threads)
            except Exception:
                pass

        return {
            "has_gpu": has_gpu,
            "description": desc,
            "torch_version": torch.__version__
        }
