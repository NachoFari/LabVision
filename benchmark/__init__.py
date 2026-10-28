"""
Benchmark package for LabVision Pro
Synthetic video generators and hardware performance benchmark suite.
"""

from .generator import generate_viscometer_video, generate_balance_video

__all__ = ["generate_viscometer_video", "generate_balance_video"]
