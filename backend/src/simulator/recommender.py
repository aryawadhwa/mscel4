import numpy as np


class Recommender:
    """
    Rule-based material recommender scoring materials on usability deadline,
    lifecycle margin, and normalised cost.

    Scoring formula (0–100):
        life_score  = clip(life_margin * 50 + 50, 0, 100)
        total_score = 0.7 * life_score + 0.3 * cost_score_normalised

    where cost_score_normalised = cost_score (0–10 from materials.yaml) * 10
    to map onto the same 0–100 scale.
    """

    def __init__(self, required_lifetime_days: float):
        """
        Parameters
        ----------
        required_lifetime_days : float  Target service life [days] — must be > 0
        """
        if required_lifetime_days <= 0:
            raise ValueError(
                f"required_lifetime_days must be > 0, got {required_lifetime_days}"
            )
        self.target_life = required_lifetime_days

    def evaluate_material(
        self,
        material_name: str,
        deadline_idx: int,
        dt: float,
        cost_score: float,
    ) -> dict:
        """
        Evaluate a material and return a scoring dict.

        Parameters
        ----------
        material_name : str    Display name of the material
        deadline_idx  : int    First time index where failure occurs
        dt            : float  Time step [days]
        cost_score    : float  Raw cost score from materials.yaml (0–10 scale)

        Returns
        -------
        dict with keys: material, viable, days_to_failure, score
        """
        days_to_failure = deadline_idx * dt
        passed_life = days_to_failure >= self.target_life

        # Life margin: normalised distance above/below requirement
        life_margin = (days_to_failure - self.target_life) / self.target_life
        # Map margin to 0–100: margin=0 → score=50, margin=1 → score=100
        life_score = float(np.clip(life_margin * 50.0 + 50.0, 0.0, 100.0))

        if not passed_life:
            total_score = 0.0
        else:
            # cost_score is on a 0–10 scale from materials.yaml;
            # multiply by 10 to bring it onto the same 0–100 scale as life_score.
            cost_score_normalised = np.clip(cost_score * 10.0, 0.0, 100.0)
            total_score = 0.7 * life_score + 0.3 * cost_score_normalised

        return {
            "material": material_name,
            "viable": bool(passed_life),
            "days_to_failure": float(days_to_failure),
            "score": round(float(total_score), 2),
        }
