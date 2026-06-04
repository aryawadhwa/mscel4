"""
Vision Adapter — Maps YOLOv8-seg visual defect detections to physics solver
input parameter modifications.

This module implements the "Adapter Mathematics" described in the paper:
    I₀ = 1.0 − Σᵢ(Wᵢ × Aᵢ)
    E_adapted = E₀ × (I₀)^n
    σ_adapted = σ₀ × (I₀)^n
    M₀_adapted = Moisture_Area_Ratio × M_eq
    k_UV_adapted = k_UV × (1 + Discoloration_Ratio)

CRITICAL DESIGN PRINCIPLE: This adapter NEVER modifies the physics engine.
It acts purely as an input filter that alters material parameters before
they reach the existing kinetic solvers and CLT formulation.
"""

import copy
import yaml
import os
import numpy as np
from typing import Optional


# ---------------------------------------------------------------------------
# Default severity weights (can be overridden via adapter_config.yaml)
# ---------------------------------------------------------------------------
DEFAULT_WEIGHTS = {
    "crack": 0.8,
    "erosion": 0.6,
    "moisture": 0.5,
    "discoloration": 0.2,
}

DEFAULT_CLASS_MAP = {
    0: "crack",
    1: "erosion",
    2: "moisture",
    3: "discoloration",
}


class VisionAdapter:
    """
    Adapter layer that computes the Initial Integrity Factor (I₀) from
    YOLOv8-seg detection results and produces modified material parameter
    dictionaries for the existing physics solvers.

    Parameters
    ----------
    weights : dict, optional
        Severity weights per damage type {str: float}.
        Defaults to DEFAULT_WEIGHTS.
    calibration_n : float
        Exponent for CLT knockdown: E_adapted = E₀ × (I₀)^n.
    class_map : dict, optional
        Mapping from integer class IDs to damage type strings.
    """

    def __init__(
        self,
        weights: Optional[dict] = None,
        calibration_n: float = 1.5,
        class_map: Optional[dict] = None,
    ):
        self.weights = weights or DEFAULT_WEIGHTS.copy()
        self.n = calibration_n
        self.class_map = class_map or DEFAULT_CLASS_MAP.copy()

    # ------------------------------------------------------------------
    # Core: Initial Integrity Factor
    # ------------------------------------------------------------------

    def compute_integrity_factor(self, detections: list[dict]) -> float:
        """
        Compute the Initial Integrity Factor I₀ from YOLO detections.

        I₀ = 1.0 − Σᵢ(Wᵢ × Aᵢ)

        Parameters
        ----------
        detections : list of dict
            Each dict must contain:
                - "class_name" (str): damage type key matching self.weights
                - "area_ratio" (float): fraction of total image area [0, 1]

        Returns
        -------
        float
            I₀ clamped to [0.0, 1.0].
        """
        total_damage = 0.0
        for det in detections:
            cls_name = det.get("class_name", "")
            area_ratio = det.get("area_ratio", 0.0)
            weight = self.weights.get(cls_name, 0.0)
            total_damage += weight * area_ratio

        I_0 = 1.0 - total_damage
        return float(np.clip(I_0, 0.0, 1.0))

    # ------------------------------------------------------------------
    # Per-damage-type area ratio extractors
    # ------------------------------------------------------------------

    def _aggregate_area_by_class(self, detections: list[dict]) -> dict:
        """
        Aggregate area ratios per damage class across all detections.

        If multiple bounding boxes of the same class are detected, their
        area ratios are summed (capped at 1.0 per class).
        """
        areas = {}
        for det in detections:
            cls_name = det.get("class_name", "")
            ar = det.get("area_ratio", 0.0)
            areas[cls_name] = areas.get(cls_name, 0.0) + ar

        # Cap each class at 1.0
        return {k: min(v, 1.0) for k, v in areas.items()}

    # ------------------------------------------------------------------
    # Moisture Model Adaptation
    # ------------------------------------------------------------------

    def adapt_moisture_initial(
        self, meq: float, detections: list[dict]
    ) -> float:
        """
        Compute adapted initial moisture content M₀.

        If YOLO detects moisture damage covering X% of the surface,
        the Fickian diffusion model starts at M₀ = X × M_eq instead of 0.

        Parameters
        ----------
        meq : float
            Equilibrium moisture content from GAB isotherm.
        detections : list of dict
            YOLO detection results.

        Returns
        -------
        float
            Initial moisture offset M₀ ∈ [0, meq].
        """
        areas = self._aggregate_area_by_class(detections)
        moisture_ratio = areas.get("moisture", 0.0)
        m0 = moisture_ratio * meq
        return float(np.clip(m0, 0.0, meq))

    # ------------------------------------------------------------------
    # UV Rate Adaptation
    # ------------------------------------------------------------------

    def adapt_uv_rate(
        self, k_uv_base: float, detections: list[dict]
    ) -> float:
        """
        Scale UV degradation rate constant based on detected discoloration.

        Discoloration is a visual proxy for pre-existing UV chain scission.
        k_UV_adapted = k_UV_base × (1 + Discoloration_Ratio)

        Parameters
        ----------
        k_uv_base : float
            Baseline UV degradation rate constant from materials.yaml.
        detections : list of dict
            YOLO detection results.

        Returns
        -------
        float
            Adapted UV rate constant (always ≥ k_uv_base).
        """
        areas = self._aggregate_area_by_class(detections)
        discoloration_ratio = areas.get("discoloration", 0.0)
        return k_uv_base * (1.0 + discoloration_ratio)

    # ------------------------------------------------------------------
    # CLT Stiffness / Strength Knockdown
    # ------------------------------------------------------------------

    def adapt_stiffness(
        self, E_0: float, I_0: float
    ) -> float:
        """
        Adapted elastic modulus: E_adapted = E₀ × (I₀)^n

        Parameters
        ----------
        E_0 : float
            Baseline elastic modulus from materials.yaml.
        I_0 : float
            Initial Integrity Factor.

        Returns
        -------
        float
        """
        return E_0 * (I_0 ** self.n)

    def adapt_strength(
        self, sigma_0: float, I_0: float
    ) -> float:
        """
        Adapted tensile strength: σ_adapted = σ₀ × (I₀)^n

        Parameters
        ----------
        sigma_0 : float
            Baseline tensile strength from materials.yaml.
        I_0 : float
            Initial Integrity Factor.

        Returns
        -------
        float
        """
        return sigma_0 * (I_0 ** self.n)

    # ------------------------------------------------------------------
    # Unified Material Adaptation
    # ------------------------------------------------------------------

    def adapt_material_params(
        self, material: dict, detections: list[dict]
    ) -> dict:
        """
        Return a **modified copy** of the material dictionary with all
        vision-adapted parameters applied.

        Modifications:
            - baseline_e  → E₀ × (I₀)^n
            - baseline_sigma → σ₀ × (I₀)^n
            - uv_base → k_UV × (1 + discoloration_ratio)
            + adds 'vision_m0_offset' key for moisture initial offset
            + adds 'vision_I0' key for traceability

        The original material dict is NOT mutated.

        Parameters
        ----------
        material : dict
            Material entry from materials.yaml.
        detections : list of dict
            YOLO detection results.

        Returns
        -------
        dict
            Deep-copied material dict with adapted parameters.
        """
        adapted = copy.deepcopy(material)

        # Compute I₀
        I_0 = self.compute_integrity_factor(detections)
        adapted["vision_I0"] = I_0

        # CLT knockdown
        adapted["baseline_e"] = self.adapt_stiffness(
            float(material["baseline_e"]), I_0
        )
        adapted["baseline_sigma"] = self.adapt_strength(
            float(material["baseline_sigma"]), I_0
        )

        # UV rate scaling
        adapted["uv_base"] = self.adapt_uv_rate(
            float(material["uv_base"]), detections
        )

        # Moisture initial offset (stored as fraction of M_eq, computed
        # downstream when GAB equilibrium is known)
        areas = self._aggregate_area_by_class(detections)
        adapted["vision_moisture_area_ratio"] = areas.get("moisture", 0.0)

        return adapted

    # ------------------------------------------------------------------
    # Damage Summary (for UI display)
    # ------------------------------------------------------------------

    def summarize_detections(self, detections: list[dict]) -> dict:
        """
        Produce a human-readable summary of detected damage for the UI.

        Returns
        -------
        dict with keys:
            - "damage_breakdown": {class_name: area_percent}
            - "I0": float
            - "total_damage_percent": float
        """
        areas = self._aggregate_area_by_class(detections)
        I_0 = self.compute_integrity_factor(detections)

        breakdown = {
            k: round(v * 100, 2) for k, v in areas.items()
        }
        total = sum(areas.values()) * 100

        return {
            "damage_breakdown": breakdown,
            "I0": round(I_0, 4),
            "total_damage_percent": round(total, 2),
        }


# ---------------------------------------------------------------------------
# Factory: Load adapter from config file
# ---------------------------------------------------------------------------

def load_adapter_from_config(
    config_path: Optional[str] = None,
    calibration_n_override: Optional[float] = None,
) -> VisionAdapter:
    """
    Instantiate a VisionAdapter from adapter_config.yaml.

    Parameters
    ----------
    config_path : str, optional
        Path to adapter_config.yaml. If None, uses default location
        relative to this file.
    calibration_n_override : float, optional
        If provided, overrides the config file's calibration_exponent
        (used when the user adjusts the slider in the UI).
    """
    if config_path is None:
        config_path = os.path.join(
            os.path.dirname(__file__),
            "..", "..", "data", "adapter_config.yaml"
        )

    with open(config_path, "r") as f:
        config = yaml.safe_load(f)

    weights = config.get("severity_weights", DEFAULT_WEIGHTS)
    n = calibration_n_override or config.get("calibration_exponent", 1.5)

    raw_class_map = config.get("class_mapping", DEFAULT_CLASS_MAP)
    class_map = {int(k): v for k, v in raw_class_map.items()}

    return VisionAdapter(weights=weights, calibration_n=n, class_map=class_map)
