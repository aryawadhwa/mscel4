import mlx.core as mx

class Recommender:
    """
    Rule-based recommender system scoring materials based on usability deadlines,
    mechanical integrity, and cost. Designed for high interpretability.
    """
    def __init__(self, required_lifetime_days: float):
        self.target_life = required_lifetime_days

    def evaluate_material(self, material_name: str, deadline_idx: int, dt: float, cost_score: float) -> dict:
        """
        Calculates a composite score. If the deadline index mapped to days is less
        than the target life, the material fails the primary criterion.
        """
        # Calculate actual days until failure
        # If deadline_idx is 0, it either failed immediately or never failed (if masked carefully).
        # We assume deadline_idx > 0 means failure at that index.
        days_to_failure = deadline_idx * dt
        
        passed_life = days_to_failure >= self.target_life
        
        # Scoring mechanism (1-100)
        # Margin: normalized lifetime margin above requirement
        life_margin = (days_to_failure - self.target_life) / self.target_life
        life_score = mx.clip(mx.array(life_margin * 50.0 + 50.0), 0.0, 100.0).item()
        
        if not passed_life:
            total_score = 0.0
        else:
            # Weighting: 70% life margin, 30% cost efficiency
            total_score = 0.7 * life_score + 0.3 * (cost_score * 10.0)

        return {
            "material": material_name,
            "viable": bool(passed_life),
            "days_to_failure": float(days_to_failure),
            "score": round(float(total_score), 2)
        }
