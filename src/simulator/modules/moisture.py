import mlx.core as mx

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
        
    def equilibrium_moisture_gab(self, aw: mx.array) -> mx.array:
        """
        GAB Model for equilibrium moisture content. aw = water activity (RH).
        Batched over scenarios via MLX.
        """
        num = self.xm * self.c * self.k * aw
        den = (1 - self.k * aw) * (1 - self.k * aw + self.c * self.k * aw)
        return num / den

    def fickian_uptake(self, t_array: mx.array, meq: mx.array) -> mx.array:
        """
        Fickian moisture uptake over time array.
        M(t) = Meq * [1 - (8/pi^2) * exp(-pi^2 * D_eff * t / h^2)]
        """
        pi = 3.14159265359
        # Ensure proper broadcasting for batched arrays
        exponent = - (pi**2 * self.d_eff * t_array) / (self.h**2)
        uptake = meq * (1 - (8 / (pi**2)) * mx.exp(exponent))
        return uptake
