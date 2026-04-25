import mlx.core as mx

class PropertyMapper:
    """
    Maps physical degradation to constituent properties and integrates 
    Classical Lamination Theory (CLT) to construct macro-mechanical parameters.
    """
    def compute_knockdown(self, mw_t: mx.array, mw_0: float, moisture_t: mx.array) -> mx.array:
        """
        Phenomenological exponential knockdown factor based on cumulative damage.
        """
        damage_var = (1.0 - (mw_t / mw_0)) + 0.5 * moisture_t
        return mx.exp(-damage_var)

    def compute_lamina_Q(self, E11: float, E22: float, v12: float, G12: float, knockdown: mx.array) -> mx.array:
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
        zero = mx.zeros_like(Q11)
        
        row1 = mx.stack([Q11, Q12, zero], axis=-1)
        row2 = mx.stack([Q12, Q22, zero], axis=-1)
        row3 = mx.stack([zero, zero, Q66], axis=-1)
        
        return mx.stack([row1, row2, row3], axis=-2)
        
    def assemble_ABD(self, z_coords: list, Q_matrices: list) -> mx.array:
        """
        Assembles ABD matrix based on CLT formulation.
        Q_matrices is a list of Q tensors for each lamina. 
        """
        # Base ABD assembly, operates on final [3, 3] shapes across batched scenarios.
        A = mx.zeros_like(Q_matrices[0])
        B = mx.zeros_like(Q_matrices[0])
        D = mx.zeros_like(Q_matrices[0])
        
        for i in range(len(Q_matrices)):
            Q = Q_matrices[i]
            z_top = z_coords[i+1]
            z_bot = z_coords[i]
            
            A = A + Q * (z_top - z_bot)
            B = B + 0.5 * Q * (z_top**2 - z_bot**2)
            D = D + (1.0/3.0) * Q * (z_top**3 - z_bot**3)
            
        row1 = mx.concatenate([A, B], axis=-1)
        row2 = mx.concatenate([B, D], axis=-1)
        ABD = mx.concatenate([row1, row2], axis=-2)
        return ABD
