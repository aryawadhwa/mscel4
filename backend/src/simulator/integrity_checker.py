import mlx.core as mx

class IntegrityChecker:
    """
    Evaluates mechanical integrity against user-defined failure thresholds.
    """
    def __init__(self, E_threshold: float, sigma_threshold: float):
        self.E_threshold = E_threshold
        self.sigma_threshold = sigma_threshold

    def evaluate_usability(self, E_t: mx.array, E_0: mx.array, sigma_t: mx.array, sigma_0: mx.array) -> mx.array:
        """
        Returns boolean mask array for time steps where material is still usable.
        """
        e_mask = (E_t / E_0) > self.E_threshold
        sigma_mask = (sigma_t / sigma_0) > self.sigma_threshold
        return mx.logical_and(e_mask, sigma_mask)

    def find_deadline_indices(self, usable_mask: mx.array) -> mx.array:
        """
        Finds the first time step index where failure occurs.
        """
        # Argmin on logical NOT finds first occurrence of False.
        # Ensure correct axis if operating on batched scenarios.
        return mx.argmin(usable_mask, axis=-1)
