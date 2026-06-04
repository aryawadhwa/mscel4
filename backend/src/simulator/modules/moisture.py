import numpy as np
from simulator.constants import gab_equilibrium_moisture


class MoistureModule:
    """
    Computes moisture uptake using the GAB sorption isotherm and Fickian diffusion.

    The GAB isotherm provides the equilibrium moisture content M_eq(RH).
    The Fickian model describes the transient uptake towards M_eq over time:
        M(t) = M0 + (M_eq - M0) * [1 - (8/π²) * exp(-π² * D_eff * t / h²)]

    Reference: Crank, J. (1975). The Mathematics of Diffusion. Oxford University Press.
    """

    def __init__(
        self,
        gab_xm: float,
        gab_c: float,
        gab_k: float,
        d_eff: float,
        thickness: float,
    ):
        """
        Parameters
        ----------
        gab_xm    : float  GAB monolayer moisture content [kg/kg]
        gab_c     : float  GAB constant C (dimensionless)
        gab_k     : float  GAB constant K (dimensionless, 0 < k < 1)
        d_eff     : float  Effective diffusion coefficient [m²/s]
        thickness : float  Half-thickness of the laminate [m]
        """
        if d_eff <= 0:
            raise ValueError(f"d_eff must be > 0, got {d_eff}")
        if thickness <= 0:
            raise ValueError(f"thickness must be > 0, got {thickness}")
        self.xm = gab_xm
        self.c = gab_c
        self.k = gab_k
        self.d_eff = d_eff
        self.h = thickness

    def equilibrium_moisture_gab(self, aw) -> float:
        """
        GAB Model for equilibrium moisture content.

        Parameters
        ----------
        aw : float  Water activity (≡ relative humidity, 0–1)
        """
        return gab_equilibrium_moisture(self.xm, self.c, self.k, float(aw))

    def fickian_uptake(
        self,
        t_array: np.ndarray,
        meq: np.ndarray,
        m0_offset: float = 0.0,
    ) -> np.ndarray:
        """
        Fickian moisture uptake over time.

        M(t) = M0 + (Meq - M0) * [1 - (8/π²) * exp(-π² * D_eff * t / h²)]

        When m0_offset > 0, the absorption curve starts from a non-zero
        baseline representing pre-existing moisture damage detected by the
        Vision Adapter. This bypasses the initial ramp-up phase.

        Parameters
        ----------
        t_array   : np.ndarray  Time array [days] — converted to seconds internally
        meq       : np.ndarray  Equilibrium moisture content from GAB isotherm [kg/kg]
        m0_offset : float       Initial moisture offset [0, meq]. Default 0.0.

        Notes
        -----
        t_array is assumed to be in **days** and is converted to seconds
        using the factor 86400 internally.
        """
        meq_scalar = float(meq) if np.ndim(meq) == 0 else float(meq.flat[0])
        if m0_offset < 0:
            raise ValueError(f"m0_offset must be >= 0, got {m0_offset}")
        if m0_offset > meq_scalar:
            # Clip rather than crash — pre-existing moisture cannot exceed equilibrium
            m0_offset = meq_scalar

        t_seconds = np.asarray(t_array, dtype=float) * 86400.0
        exponent = -(np.pi ** 2 * self.d_eff * t_seconds) / (self.h ** 2)
        effective_meq = meq_scalar - m0_offset
        return m0_offset + effective_meq * (1.0 - (8.0 / np.pi ** 2) * np.exp(exponent))

    def solve_1d_ham_pde(self, dt_seconds: float, rh_env) -> np.ndarray:
        """
        Compatibility alias for the Fickian uptake solver.

        Accepts the same signature as the old HAM-PDE call used in batch
        scripts: dt in seconds and a relative humidity array.

        Parameters
        ----------
        dt_seconds : float       Time step [s]
        rh_env     : array-like  Relative humidity array (values 0–1)

        Returns
        -------
        np.ndarray  Moisture content time series [kg/kg]
        """
        rh = np.asarray(rh_env, dtype=float)
        aw = float(rh[0]) if rh.ndim > 0 else float(rh)
        meq = self.equilibrium_moisture_gab(aw)
        # Build a time array in days from dt_seconds
        n_steps = len(rh) if rh.ndim > 0 else 1
        t_days = np.arange(n_steps) * (dt_seconds / 86400.0)
        return self.fickian_uptake(t_days, meq)
