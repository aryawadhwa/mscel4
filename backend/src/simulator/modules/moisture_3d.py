import numpy as np

try:
    import mlx.core as mx
    _HAS_MLX = True
except ImportError:
    _HAS_MLX = False


class MoistureModule3D:
    """
    Computes 3D moisture uptake using GAB isotherm and 3D Finite Element (FTCS) diffusion.
    Stores only a fixed number of snapshots (num_snapshots) to avoid memory blowout.
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

    def equilibrium_moisture_gab(self, aw: float) -> float:
        """GAB Model for equilibrium moisture content. aw = water activity (RH)."""
        num = self.xm * self.c * self.k * aw
        den = (1 - self.k * aw) * (1 - self.k * aw + self.c * self.k * aw)
        if den == 0:
            return 0.0
        return num / den

    def solve_3d_ham_pde(
        self,
        dt: float,
        rh_env,
        num_snapshots: int = 10,
    ) -> tuple:
        """
        Solves the 3D moisture diffusion PDE using an explicit FTCS scheme.

        Only stores `num_snapshots` evenly-spaced grid snapshots instead of
        one per time step, preventing memory exhaustion and UI freeze.

        Args:
            dt:            Time step size in seconds.
            rh_env:        Array of external RH values, shape (time_steps,).
            num_snapshots: How many grid frames to capture (default 10).

        Returns:
            (snapshot_days, grid_history)
            snapshot_days:  list of day indices for each saved frame.
            grid_history:   list of np.ndarray of shape (N, N, N).
        """
        # Convert rh_env to plain Python list so we don't depend on MLX here
        if hasattr(rh_env, "tolist"):
            rh_list = rh_env.tolist()
        else:
            rh_list = list(rh_env)

        time_steps = len(rh_list)

        # Courant stability limit for explicit 3D FTCS
        max_dt = 1.0 / (
            2
            * self.d_eff
            * (1 / self.dx ** 2 + 1 / self.dy ** 2 + 1 / self.dz ** 2)
        )
        sub_steps = max(1, int(np.ceil(dt / max_dt)))
        sub_dt = dt / sub_steps

        alpha_x = self.d_eff * sub_dt / self.dx ** 2
        alpha_y = self.d_eff * sub_dt / self.dy ** 2
        alpha_z = self.d_eff * sub_dt / self.dz ** 2

        # Decide which outer time steps to snapshot
        snap_indices = set(
            int(round(i * (time_steps - 1) / (num_snapshots - 1)))
            for i in range(num_snapshots)
        )
        snap_indices.add(0)
        snap_indices.add(time_steps - 1)
        snap_indices = sorted(snap_indices)

        # Use plain NumPy for the grid — avoids MLX graph growth
        W = np.zeros((self.N, self.N, self.N), dtype=np.float32)

        grid_history = []
        snapshot_days = []

        for t in range(time_steps):
            aw = float(rh_list[t]) if hasattr(rh_list[t], "__float__") else rh_list[t]
            w_eq = float(self.equilibrium_moisture_gab(aw))

            for _ in range(sub_steps):
                # Dirichlet BC on all 6 faces
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
