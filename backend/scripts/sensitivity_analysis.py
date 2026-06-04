import os
import sys
import yaml
import numpy as np
import pandas as pd

# Setup path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "src")))
from simulator.scenario_manager import ScenarioManager
from simulator.modules.thermal import ThermalModule
from simulator.modules.uv import UVModule
from simulator.modules.moisture import MoistureModule
from simulator.property_mapper import PropertyMapper
from simulator.integrity_checker import IntegrityChecker
from simulator.constants import UV_BASELINE_W_M2

def run_sensitivity():
    print("Starting Sensitivity Analysis...")
    db_path = os.path.join(os.path.dirname(__file__), "..", "data", "materials.yaml")
    with open(db_path, "r") as f:
        materials_db = yaml.safe_load(f)
    
    mat_key = "bagasse_pla" # Focus on composite for sensitivity
    mat = materials_db[mat_key]
    
    dt = 1.0
    t_horizon = 365.0
    sm = ScenarioManager(t_horizon, dt)
    # Use temperate climate for variance
    temps, rhs = sm.generate_climate_profile("temperate", 100)
    
    pm = PropertyMapper()
    ic = IntegrityChecker(E_threshold=0.5, sigma_threshold=0.5) # Paper threshold 50%
    
    # Perturbations: +/- 10% on thermal activation energy (Ea) and thickness
    perturbations = [
        {"name": "Baseline", "ea_mod": 1.0, "h_mod": 1.0},
        {"name": "High Ea (+10%)", "ea_mod": 1.1, "h_mod": 1.0},
        {"name": "Low Ea (-10%)", "ea_mod": 0.9, "h_mod": 1.0},
        {"name": "Thick (+20%)", "ea_mod": 1.0, "h_mod": 1.2},
        {"name": "Thin (-20%)", "ea_mod": 1.0, "h_mod": 0.8},
    ]
    
    results = []
    
    for pert in perturbations:
        tm = ThermalModule(float(mat["thermal_a"]), float(mat["thermal_ea"]) * pert["ea_mod"], float(mat["mw_0"]))
        uv = UVModule(float(mat["uv_base"]), float(mat["uv_ea"]))
        # Thickness baseline = 0.002
        mm = MoistureModule(float(mat["gab_xm"]), float(mat["gab_c"]), float(mat["gab_k"]), float(mat["d_eff"]), thickness=0.002 * pert["h_mod"])
        
        # Parallel solve for 100 scenarios
        k_t = tm.compute_k(temps)
        k_uv = uv.compute_k_uv(temps, np.ones_like(temps) * UV_BASELINE_W_M2)
        
        mw_t = tm.compute_mw_decay(k_t + k_uv, sm.t_array)
        moisture = mm.solve_1d_ham_pde(dt * 86400.0, rhs[0])
        
        knockdown = pm.compute_knockdown(mw_t, mat["mw_0"], moisture)
        usable_mask = ic.evaluate_usability(knockdown, 1.0, knockdown, 1.0)
        
        # Calculate time to failure per scenario
        failures = []
        for i in range(100):
            first_fail_idx = ic.find_deadline_indices(usable_mask[i:i+1]).item()
            if first_fail_idx == 0 and usable_mask[i, 0].item() == True:
                first_fail_idx = len(sm.t_array) - 1
            failures.append(first_fail_idx * dt)
        
        failures_series = pd.Series(failures)
        results.append({
            "Perturbation": pert["name"],
            "Median_Lifetime_Days": failures_series.median(),
            "5th_Percentile": failures_series.quantile(0.05),
            "95th_Percentile": failures_series.quantile(0.95)
        })
        print(f"Processed {pert['name']}")
        
    df = pd.DataFrame(results)
    out_path = os.path.join(os.path.dirname(__file__), "sensitivity_results.csv")
    df.to_csv(out_path, index=False)
    print(f"Results saved to {out_path}")

if __name__ == "__main__":
    run_sensitivity()
