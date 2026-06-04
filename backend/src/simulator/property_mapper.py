import numpy as np

class PropertyMapper:
    """
    Maps physical degradation to constituent properties and integrates 
    Classical Lamination Theory (CLT) to construct macro-mechanical parameters.
    """
    def compute_knockdown(self, mw_t: np.ndarray, mw_0: float, moisture_t: np.ndarray) -> np.ndarray:
        """
        Phenomenological exponential knockdown factor based on cumulative damage.
        """
        damage_var = (1.0 - (mw_t / mw_0)) + 0.5 * moisture_t
        return np.exp(-damage_var)

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
        absorption curve bypasses the initial ramp-up phase. Does not modify
        ``compute_knockdown``; delegates after building the moisture time series.
        """
        moisture_t = moisture_module.fickian_uptake(
            t_array, meq, m0_offset=m0_offset
        )
        return self.compute_knockdown(mw_t, mw_0, moisture_t)

    def compute_lamina_Q(self, E11: float, E22: float, v12: float, G12: float, knockdown: np.ndarray) -> np.ndarray:
        """
        Assembles time-dependent reduced stiffness matrix Q for orthotropic lamina.
        Returns tensor of shape [..., 3, 3] representing batched time steps.
        """
        v21 = v12 * E22 / E11
        denom = 1.0 - v12 * v21
        
        Q11 = (E11 * knockdown) / denom
        Q22 = (E22 * knockdown) / denom
        Q12 = (v12 * E22 * knockdown) / denom
        Q66 = G12 * knockdown
        zero = np.zeros_like(Q11)
        
        row1 = np.stack([Q11, Q12, zero], axis=-1)
        row2 = np.stack([Q12, Q22, zero], axis=-1)
        row3 = np.stack([zero, zero, Q66], axis=-1)
        
        return np.stack([row1, row2, row3], axis=-2)
        
    def assemble_ABD(self, z_coords: list, Q_matrices: list) -> np.ndarray:
        """
        Assembles ABD matrix based on CLT formulation.
        Q_matrices is a list of Q tensors for each lamina. 
        """
        # Base ABD assembly, operates on final [3, 3] shapes across batched scenarios.
        A = np.zeros_like(Q_matrices[0])
        B = np.zeros_like(Q_matrices[0])
        D = np.zeros_like(Q_matrices[0])
        
        for i in range(len(Q_matrices)):
            Q = Q_matrices[i]
            z_top = z_coords[i+1]
            z_bot = z_coords[i]
            
            A = A + Q * (z_top - z_bot)
            B = B + 0.5 * Q * (z_top**2 - z_bot**2)
            D = D + (1.0/3.0) * Q * (z_top**3 - z_bot**3)
            
        row1 = np.concatenate([A, B], axis=-1)
        row2 = np.concatenate([B, D], axis=-1)
        ABD = np.concatenate([row1, row2], axis=-2)
        return ABD
