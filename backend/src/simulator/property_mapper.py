import numpy as np


class PropertyMapper:
    """
    Maps physical degradation state to constituent material properties and
    assembles macro-mechanical parameters via Classical Lamination Theory (CLT).

    Reference: Jones, R.M. (1999). Mechanics of Composite Materials. Taylor & Francis.
    """

    def compute_knockdown(
        self,
        mw_t: np.ndarray,
        mw_0: float,
        moisture_t: np.ndarray,
    ) -> np.ndarray:
        """
        Phenomenological exponential knockdown factor based on cumulative damage.

        Combines chain-scission (molecular weight loss) and plasticisation
        (moisture uptake) into a single residual-property ratio:
            kd(t) = exp(-[(1 - Mw(t)/Mw₀) + 0.5 * M(t)])

        The 0.5 coefficient weights moisture contribution relative to
        molecular weight loss (calibrated from literature on PLA/PBAT blends).

        Parameters
        ----------
        mw_t      : np.ndarray  Molecular weight at time t [g/mol]
        mw_0      : float       Initial molecular weight [g/mol]
        moisture_t: np.ndarray  Moisture content at time t [kg/kg]

        Returns
        -------
        np.ndarray  Knockdown factor ∈ (0, 1] (clipped to physical bounds)
        """
        if mw_0 <= 0:
            raise ValueError(f"mw_0 must be > 0, got {mw_0}")
        mw_ratio = np.clip(mw_t / mw_0, 0.0, 1.0)  # cannot exceed initial Mw
        damage_var = (1.0 - mw_ratio) + 0.5 * np.asarray(moisture_t, dtype=float)
        return np.clip(np.exp(-damage_var), 0.0, 1.0)

    def compute_knockdown_with_offset(
        self,
        mw_t: np.ndarray,
        mw_0: float,
        t_array: np.ndarray,
        meq: np.ndarray,
        moisture_module,
        m0_offset: float = 0.0,
    ) -> np.ndarray:
        """
        Knockdown factor with Fickian moisture uptake starting from a non-zero M₀.

        Used when the Vision Adapter detects pre-existing moisture damage so the
        absorption curve bypasses the initial ramp-up phase.
        """
        moisture_t = moisture_module.fickian_uptake(
            t_array, meq, m0_offset=m0_offset
        )
        return self.compute_knockdown(mw_t, mw_0, moisture_t)

    def compute_lamina_Q(
        self,
        E11: float,
        E22: float,
        v12: float,
        G12: float,
        knockdown: np.ndarray,
    ) -> np.ndarray:
        """
        Assemble the time-dependent reduced stiffness matrix Q for an orthotropic lamina.

        Returns tensor of shape [..., 3, 3] representing batched time steps.

        Parameters
        ----------
        E11, E22 : float  Young's moduli in principal directions [Pa]
        v12      : float  Major Poisson ratio (dimensionless)
        G12      : float  In-plane shear modulus [Pa]
        knockdown: np.ndarray  Residual property ratio ∈ (0, 1]

        Raises
        ------
        ValueError  If inputs are physically invalid (E=0, Poisson ratio ≥ 1, etc.)
        """
        if E11 <= 0:
            raise ValueError(f"E11 must be > 0, got {E11}")
        if E22 <= 0:
            raise ValueError(f"E22 must be > 0, got {E22}")

        v21 = v12 * E22 / E11
        denom = 1.0 - v12 * v21
        if denom <= 1e-12:
            raise ValueError(
                f"Invalid Poisson ratio: v12={v12}, v21={v21:.4f}. "
                "Ensure v12 * v21 < 1 (thermodynamic stability requirement)."
            )

        kd = np.asarray(knockdown, dtype=float)
        Q11 = (E11 * kd) / denom
        Q22 = (E22 * kd) / denom
        Q12 = (v12 * E22 * kd) / denom
        Q66 = G12 * kd
        zero = np.zeros_like(Q11)

        row1 = np.stack([Q11, Q12, zero], axis=-1)
        row2 = np.stack([Q12, Q22, zero], axis=-1)
        row3 = np.stack([zero, zero, Q66], axis=-1)

        return np.stack([row1, row2, row3], axis=-2)

    def assemble_ABD(self, z_coords: list, Q_matrices: list) -> np.ndarray:
        """
        Assemble the ABD stiffness matrix from CLT.

        Parameters
        ----------
        z_coords   : list  z-coordinates of ply interfaces [m], length = n_plies + 1
        Q_matrices : list  Reduced stiffness tensors, one per ply, each shape [..., 3, 3]
        """
        A = np.zeros_like(Q_matrices[0])
        B = np.zeros_like(Q_matrices[0])
        D = np.zeros_like(Q_matrices[0])

        for i, Q in enumerate(Q_matrices):
            z_top = z_coords[i + 1]
            z_bot = z_coords[i]
            A = A + Q * (z_top - z_bot)
            B = B + 0.5 * Q * (z_top ** 2 - z_bot ** 2)
            D = D + (1.0 / 3.0) * Q * (z_top ** 3 - z_bot ** 3)

        row1 = np.concatenate([A, B], axis=-1)
        row2 = np.concatenate([B, D], axis=-1)
        return np.concatenate([row1, row2], axis=-2)
