import numpy as np

class ComponentSimulator:
    """
    Simulates physical packaging components under real-world mechanical loads.
    Utilizes Classical Lamination Theory (CLT) matrices to compute physical deflection.
    """
    def __init__(self, length_m: float, width_m: float, load_n: float):
        self.L = length_m
        self.b = width_m
        self.P = load_n
        
    def compute_tray_deflection(self, abd_matrix: np.ndarray) -> np.ndarray:
        """
        Computes maximum deflection of a simply supported rectangular plate 
        (packaging tray) under a central stacking load.
        
        Args:
            abd_matrix: Tensor of shape [..., 6, 6] containing CLT A, B, D matrices.
            
        Returns:
            Deflection w_max (in millimeters) as a batched tensor.
        """
        # Extract D11 (Bending Stiffness along principal axis)
        # ABD is [6, 6]. D is the bottom right [3, 3] quadrant.
        # D11 is at index [3, 3] of the 6x6 matrix.
        D11 = abd_matrix[..., 3, 3]
        
        # Simplified 1D beam bending approximation for central load P
        # w_max = (P * L^3) / (48 * D11 * b)
        # Convert to millimeters (* 1000)
        
        # Avoid division by zero if D11 collapses completely
        D11_safe = np.where(D11 > 1e-6, D11, 1e-6)
        
        deflection_m = (self.P * (self.L ** 3)) / (48 * D11_safe * self.b)
        return deflection_m * 1000.0
