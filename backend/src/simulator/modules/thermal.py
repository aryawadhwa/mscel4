import numpy as np

class ThermalModule:
    """
    Computes thermal degradation via Arrhenius hydrolytic/thermal decay.
    """
    def __init__(self, a_factor: float, e_a: float, mw_0: float):
        self.A = a_factor      # Pre-exponential factor
        self.E_a = e_a         # Activation Energy (J/mol)
        self.Mw_0 = mw_0       # Initial molecular weight
        self.R = 8.314         # Ideal gas constant (J/(mol*K))
        
    def compute_k(self, temps_k: np.ndarray) -> np.ndarray:
        """
        Arrhenius rate constant k(T).
        """
        return self.A * np.exp(-self.E_a / (self.R * temps_k))

    def compute_mw_decay(self, k_array: np.ndarray, t_array: np.ndarray) -> np.ndarray:
        """
        First order decay of Molecular Weight.
        Mw(t) = Mw_0 * exp(-k * t)
        """
        return self.Mw_0 * np.exp(-k_array * t_array)
