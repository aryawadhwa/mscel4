import numpy as np
from simulator.constants import gab_equilibrium_moisture, COURANT_SAFETY
import warnings


class MoistureModule3D:
    """
    3D moisture diffusion via explicit FTCS Fickian scheme.

    Solves the 3D diffusion PDE:
        ∂C/∂t = D_eff * (∂²C/∂x² + ∂²C/∂y² + ∂²C/∂z²)

    with Dirichlet boundary conditions on all 6 faces derived from the
    GAB sorption isotherm.

    Only a fixed number of snapshots are stored (not one per time step) to
    prevent memory exhaustion in the Streamlit frontend.
    """

    def __init__(
        self,
        gab_xm: float,
        gab_c: float,
        gab_k: float,
        d_eff: float,
        length: float,
        width: float,
        thickness: float,
        nodes: int = 10,
    ):
        """
        Parameters
        ----------
        gab_xm    : float  GAB monolayer moisture content [kg/kg]
        gab_c     : float  GAB constant C (dimensionless)
        gab_k     : float  GAB constant K (dimensionless)
        d_eff     : float  Effective diffusion coefficient [m²/s]
        length    : float  Domain length in x [m]
        width     : float  Domain width in y [m]
        thickness : float  Domain thickness in z [m]
        nodes     : int    Grid points per dimension (N³ total nodes)
        """
        if d_eff <= 0:
            raise ValueError(f"d_eff must be > 0, got {d_eff}")
        if nodes < 3:
            raise ValueError(f"nodes must be >= 3, got {nodes}")

        self.xm = gab_xm
        self.c = gab_c
        self.k = gab_k
        self.d_eff = d_eff
        self.L = length
        self.W = width
        self.H = thickness
        self.N = nodes

        self.dx = length / (nodes - 1)
        self.dy = width / (nodes - 1)
        self.dz = thickness / (nodes - 1)

        # Warn if grid is coarse relative to diffusivity — informational only
        max_dt_stable = 0.5 / (
            d_eff * (1 / self.dx ** 2 + 1 / self.dy ** 2 + 1 / self.dz ** 2)
        )
        if max_dt_stable < 1.0:  # less than 1 second of stability per step
            warnings.warn(
                f"Grid is numerically coarse for D_eff={d_eff:.2e} m²/s. "
                f"Max stable dt={max_dt_stable:.3f} s. "
                "Many sub-steps will be needed per day — consider increasing nodes.",
                UserWarning,
                stacklevel=2,
            )

    def equilibrium_moisture_gab(self, aw: float) -> float:
        """GAB isotherm — delegates to shared pure function in constants.py."""
        return gab_equilibrium_moisture(self.xm, self.c, self.k, aw)

    def solve_3d_ham_pde(
        self,
        dt: float,
        rh_env,
        num_snapshots: int = 10,
    ) -> tuple:
        """
        Solve the 3D moisture diffusion PDE using an explicit FTCS scheme.

        Only `num_snapshots` evenly-spaced grid frames are stored to avoid
        memory exhaustion.

        Parameters
        ----------
        dt            : float        Outer time step [s]
        rh_env        : array-like   External RH values, shape (time_steps,) [0-1]
        num_snapshots : int          Number of grid frames to capture (default 10)

        Returns
        -------
        (snapshot_days, grid_history)
        snapshot_days : list[int]           Day indices of saved frames
        grid_history  : list[np.ndarray]    Grid snapshots, each shape (N, N, N)
        """
        rh_list = list(rh_env) if hasattr(rh_env, "__iter__") else [float(rh_env)]
        time_steps = len(rh_list)

        # Courant-Friedrichs-Lewy (CFL) stability limit for explicit 3D FTCS
        max_dt = 1.0 / (
            2.0 * self.d_eff * (
                1 / self.dx ** 2 + 1 / self.dy ** 2 + 1 / self.dz ** 2
            )
        )
        sub_steps = max(1, int(np.ceil(dt / (max_dt * COURANT_SAFETY))))
        sub_dt = dt / sub_steps

        alpha_x = self.d_eff * sub_dt / self.dx ** 2
        alpha_y = self.d_eff * sub_dt / self.dy ** 2
        alpha_z = self.d_eff * sub_dt / self.dz ** 2

        # Snapshot indices — evenly spaced across time steps
        num_snapshots = max(2, min(num_snapshots, time_steps))
        snap_indices = set(
            int(round(i * (time_steps - 1) / (num_snapshots - 1)))
            for i in range(num_snapshots)
        )
        snap_indices.add(0)
        snap_indices.add(time_steps - 1)
        snap_indices = sorted(snap_indices)

        W = np.zeros((self.N, self.N, self.N), dtype=np.float32)
        grid_history = []
        snapshot_days = []

        for t in range(time_steps):
            aw = float(rh_list[t])
            w_eq = float(self.equilibrium_moisture_gab(aw))

            for _ in range(sub_steps):
                # Dirichlet BC on all 6 exposed faces
                W[0, :, :] = w_eq
                W[-1, :, :] = w_eq
                W[:, 0, :] = w_eq
                W[:, -1, :] = w_eq
                W[:, :, 0] = w_eq
                W[:, :, -1] = w_eq

                # FTCS update on interior nodes only
                W_inner = W[1:-1, 1:-1, 1:-1]
                W[1:-1, 1:-1, 1:-1] = (
                    W_inner
                    + alpha_x * (W[2:, 1:-1, 1:-1] - 2 * W_inner + W[:-2, 1:-1, 1:-1])
                    + alpha_y * (W[1:-1, 2:, 1:-1] - 2 * W_inner + W[1:-1, :-2, 1:-1])
                    + alpha_z * (W[1:-1, 1:-1, 2:] - 2 * W_inner + W[1:-1, 1:-1, :-2])
                )

            if t in snap_indices:
                grid_history.append(W.copy())
                snapshot_days.append(t)

        return snapshot_days, grid_history
