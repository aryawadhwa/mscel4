import numpy as np

class ScenarioManager:
    """
    Manages environmental scenarios and time-stepping for degradation simulation.
    Utilizes Apple MLX for hardware-accelerated batched scenario processing.
    """
    def __init__(self, time_horizon_days: float, dt_days: float = 0.1):
        self.time_horizon = time_horizon_days
        self.dt = dt_days
        self.time_steps = int(time_horizon_days / dt_days)
        # Using NumPy for time array
        self.t_array = np.linspace(0, time_horizon_days, self.time_steps)
        
    def generate_scenarios(self, base_temp_k: float, temp_var: float, 
                           base_rh: float, rh_var: float, num_scenarios: int):
        """
        Generates batched Monte Carlo scenarios for Temperature and Relative Humidity.
        """
        # NumPy accelerated random normal generation
        # Temp shape: (num_scenarios, time_steps)
        self.temps = base_temp_k + temp_var * np.random.normal(size=(num_scenarios, self.time_steps))
        
        # RH shape: (num_scenarios, time_steps), clamped between 0 and 1
        rh_raw = base_rh + rh_var * np.random.normal(size=(num_scenarios, self.time_steps))
        self.rhs = np.clip(rh_raw, 0.0, 1.0)
        
        self.num_scenarios = num_scenarios
        return self.temps, self.rhs
