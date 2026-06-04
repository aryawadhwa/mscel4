import numpy as np
from simulator.constants import R_GAS


class ThermalModule:
    """
    Computes thermal degradation via Arrhenius hydrolytic/thermal decay.

    The rate constant k(T) follows the Arrhenius equation:
        k(T) = A * exp(-Ea / (R * T))

    where R is the universal gas constant (imported from constants.py).
    """

    def __init__(self, a_factor: float, e_a: float, mw_0: float):
        """
        Parameters
        ----------
        a_factor : float  Pre-exponential (frequency) factor [1/day]
        e_a      : float  Activation energy [J/mol]
        mw_0     : float  Initial molecular weight [g/mol]
        """
        if a_factor <= 0:
            raise ValueError(f"a_factor must be > 0, got {a_factor}")
        if mw_0 <= 0:
            raise ValueError(f"mw_0 must be > 0, got {mw_0}")
        self.A = a_factor
        self.E_a = e_a
        self.Mw_0 = mw_0

    def compute_k(self, temps_k: np.ndarray) -> np.ndarray:
        """
        Arrhenius rate constant k(T).

        Parameters
        ----------
        temps_k : np.ndarray  Temperature array [K]
        """
        return self.A * np.exp(-self.E_a / (R_GAS * temps_k))

    def compute_mw_decay(self, k_array: np.ndarray, t_array: np.ndarray) -> np.ndarray:
        """
        First-order decay of Molecular Weight.
            Mw(t) = Mw_0 * exp(-k * t)

        Parameters
        ----------
        k_array : np.ndarray  Rate constant array (same shape as t_array) [1/day]
        t_array : np.ndarray  Time array [days]
        """
        return self.Mw_0 * np.exp(-k_array * t_array)
