import numpy as np

class UVModule:
    """
    Computes UV-induced chain scission via first-order kinetics.
    Hardware-accelerated via NumPy.
    """
    def __init__(self, k_uv_base: float, e_a_uv: float):
        self.k_uv_base = k_uv_base
        self.e_a_uv = e_a_uv
        self.R = 8.314

    def compute_k_uv(self, temps_k: np.ndarray, intensity: np.ndarray) -> np.ndarray:
        """
        Calculates effective UV degradation rate constant coupled with temperature.
        """
        temp_factor = np.exp(-self.e_a_uv / (self.R * temps_k))
        return self.k_uv_base * intensity * temp_factor
        
    def compute_mw_decay(self, k_uv_array: np.ndarray, t_array: np.ndarray, mw_0: float) -> np.ndarray:
        """
        First order decay of Mw driven by UV exposure.
        """
        return mw_0 * np.exp(-k_uv_array * t_array)
