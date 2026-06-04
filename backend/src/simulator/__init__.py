"""
mscel4 Simulator Package

Public API — import physics classes directly from this package:

    from simulator import ThermalModule, MoistureModule, PropertyMapper
    from simulator import ScenarioManager, IntegrityChecker, Recommender
    from simulator import VisionAdapter, YOLOInference
    from simulator.constants import R_GAS, UV_BASELINE_W_M2
"""

# Physics modules
from .modules.thermal import ThermalModule
from .modules.uv import UVModule
from .modules.moisture import MoistureModule
from .modules.moisture_3d import MoistureModule3D

# Simulation orchestration
from .scenario_manager import ScenarioManager
from .property_mapper import PropertyMapper
from .integrity_checker import IntegrityChecker
from .recommender import Recommender

# Vision-adaptive layer (optional — requires ONNX model)
from .vision_adapter import VisionAdapter, load_adapter_from_config
from .yolo_inference import YOLOInference, is_model_available

__all__ = [
    "ThermalModule",
    "UVModule",
    "MoistureModule",
    "MoistureModule3D",
    "ScenarioManager",
    "PropertyMapper",
    "IntegrityChecker",
    "Recommender",
    "VisionAdapter",
    "load_adapter_from_config",
    "YOLOInference",
    "is_model_available",
]
