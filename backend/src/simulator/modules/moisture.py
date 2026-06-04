import numpy as np

class MoistureModule:
    """
    Computes moisture uptake using GAB isotherm and Fickian diffusion.
    """
    def __init__(self, gab_xm: float, gab_c: float, gab_k: float, d_eff: float, thickness: float):
        self.xm = gab_xm
        self.c = gab_c
        self.k = gab_k
        self.d_eff = d_eff
        self.h = thickness
        
    def equilibrium_moisture_gab(self, aw: np.ndarray) -> np.ndarray:
        """
        GAB Model for equilibrium moisture content. aw = water activity (RH).
        Batched over scenarios via NumPy.
        """
        num = self.xm * self.c * self.k * aw
        den = (1 - self.k * aw) * (1 - self.k * aw + self.c * self.k * aw)
        return num / den

    def fickian_uptake(self, t_array: np.ndarray, meq: np.ndarray, m0_offset: float = 0.0) -> np.ndarray:
        """
        Fickian moisture uptake over time array.
        M(t) = M0 + (Meq - M0) * [1 - (8/pi^2) * exp(-pi^2 * D_eff * t / h^2)]

        When m0_offset > 0, the absorption curve starts from a non-zero
        baseline representing pre-existing moisture damage detected by the
        Vision Adapter. This bypasses the initial ramp-up phase.

        Parameters
        ----------
        t_array : np.ndarray
            Time array in days.
        meq : np.ndarray
            Equilibrium moisture content from GAB isotherm.
        m0_offset : float, optional
            Initial moisture content offset [0, meq]. Default 0.0
            (standard simulation, no pre-existing moisture damage).
        """
        pi = 3.14159265359
        # Ensure proper broadcasting for batched arrays
        exponent = - (pi**2 * self.d_eff * t_array) / (self.h**2)
        effective_meq = meq - m0_offset
        uptake = m0_offset + effective_meq * (1 - (8 / (pi**2)) * np.exp(exponent))
        return uptake
