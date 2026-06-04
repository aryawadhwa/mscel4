import numpy as np
from simulator.constants import R_GAS


class UVModule:
    """
    Computes UV-induced chain scission via first-order kinetics.

    The UV degradation rate constant couples irradiance with an Arrhenius
    temperature dependence:
        k_uv(T, I) = k_uv_base * I * exp(-Ea_uv / (R * T))
    """

    def __init__(self, k_uv_base: float, e_a_uv: float):
        """
        Parameters
        ----------
        k_uv_base : float  Base UV rate constant [(W/m²·day)⁻¹]
        e_a_uv    : float  UV activation energy [J/mol]
        """
        self.k_uv_base = k_uv_base
        self.e_a_uv = e_a_uv

    def compute_k_uv(self, temps_k: np.ndarray, intensity: np.ndarray) -> np.ndarray:
        """
        Effective UV degradation rate constant coupled with temperature.

        Parameters
        ----------
        temps_k   : np.ndarray  Temperature [K]
        intensity : np.ndarray  UV irradiance [W/m²]
        """
        temp_factor = np.exp(-self.e_a_uv / (R_GAS * temps_k))
        return self.k_uv_base * intensity * temp_factor
