import numpy as np

class IntegrityChecker:
    """
    Evaluates mechanical integrity against user-defined failure thresholds.
    """
    def __init__(self, E_threshold: float, sigma_threshold: float):
        self.E_threshold = E_threshold
        self.sigma_threshold = sigma_threshold

    def evaluate_usability(self, E_t: np.ndarray, E_0: np.ndarray, sigma_t: np.ndarray, sigma_0: np.ndarray) -> np.ndarray:
        """
        Returns boolean mask array for time steps where material is still usable.
        """
        e_mask = (E_t / E_0) > self.E_threshold
        sigma_mask = (sigma_t / sigma_0) > self.sigma_threshold
        return np.logical_and(e_mask, sigma_mask)

    def find_deadline_indices(self, usable_mask: np.ndarray) -> np.ndarray:
        """
        Finds the first time step index where failure occurs.
        """
        # Argmin on logical NOT finds first occurrence of False.
        # Ensure correct axis if operating on batched scenarios.
        return np.argmin(usable_mask, axis=-1)
