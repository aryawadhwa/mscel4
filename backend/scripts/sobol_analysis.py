"""
Global Sobol Variance-Based Sensitivity Analysis

Quantifies the contribution of each material parameter to variance in
predicted failure time using the Saltelli sampling scheme.

Reference: Saltelli, A. et al. (2010). Variance based sensitivity analysis
of model output. Design and estimator for the total sensitivity index.
Computer Physics Communications, 181(2), 259-270.
"""

import os
import sys
import yaml
import numpy as np
from SALib.sample import sobol as sobol_sampler
from SALib.analyze import sobol

# Path setup
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "src")))
from simulator.scenario_manager import ScenarioManager
from simulator.modules.thermal import ThermalModule
from simulator.modules.uv import UVModule
from simulator.modules.moisture import MoistureModule
from simulator.property_mapper import PropertyMapper
from simulator.integrity_checker import IntegrityChecker
from simulator.constants import UV_BASELINE_W_M2


def evaluate_model(X, base_mat, temps, rhs, dt, t_array):
    """
    Evaluate predicted failure time for each row of parameter multiplier
    matrix X.

    Parameter columns:
        X[:, 0] = Activation energy multiplier (Ea_mod)
        X[:, 1] = Diffusivity multiplier (D_eff_mod)
        X[:, 2] = Thickness multiplier (h_mod)

    Returns
    -------
    np.ndarray  Predicted time-to-failure [days], shape (num_samples,)
    """
    num_samples = X.shape[0]
    results = np.zeros(num_samples)

    pm = PropertyMapper()
    ic = IntegrityChecker(E_threshold=0.5, sigma_threshold=0.5)

    for i in range(num_samples):
        ea_mod, deff_mod, h_mod = X[i]

        tm = ThermalModule(
            float(base_mat["thermal_a"]),
            float(base_mat["thermal_ea"]) * ea_mod,
            float(base_mat["mw_0"]),
        )
        uv = UVModule(float(base_mat["uv_base"]), float(base_mat["uv_ea"]))
        mm = MoistureModule(
            float(base_mat["gab_xm"]),
            float(base_mat["gab_c"]),
            float(base_mat["gab_k"]),
            float(base_mat["d_eff"]) * deff_mod,
            thickness=0.002 * h_mod,
        )

        # Use first scenario only — sufficient for variance decomposition
        t_scenario = temps[0]   # shape (time_steps,)
        rh_scenario = rhs[0]    # shape (time_steps,)

        uv_intensity = np.ones_like(t_scenario) * UV_BASELINE_W_M2
        k_t = tm.compute_k(t_scenario)
        k_uv = uv.compute_k_uv(t_scenario, uv_intensity)

        mw_t = tm.compute_mw_decay(k_t + k_uv, t_array)
        moisture = mm.solve_1d_ham_pde(dt * 86400.0, rh_scenario)

        knockdown = pm.compute_knockdown(mw_t, base_mat["mw_0"], moisture)
        usable_mask = ic.evaluate_usability(knockdown, 1.0, knockdown, 1.0)

        first_fail_idx = int(ic.find_deadline_indices(usable_mask))
        # If argmin returns 0 and element 0 is True, material never failed
        if first_fail_idx == 0 and bool(usable_mask[0]):
            first_fail_idx = len(t_array) - 1

        results[i] = first_fail_idx * dt

    return results


def run_sobol_analysis(material_key: str = "bagasse_pla", n_samples: int = 32):
    """
    Run the full Sobol analysis for a given material.

    Parameters
    ----------
    material_key : str  Key in materials.yaml (default "bagasse_pla")
    n_samples    : int  Saltelli base sample count N;
                        total evaluations = N * (2D + 2) where D=3 variables.
                        Increase to 256+ for a production paper run.
    """
    print("Starting Global Sobol Sensitivity Analysis...")
    db_path = os.path.join(os.path.dirname(__file__), "..", "data", "materials.yaml")
    with open(db_path, "r") as f:
        materials_db = yaml.safe_load(f)

    if material_key not in materials_db:
        raise KeyError(
            f"Material '{material_key}' not found. "
            f"Available: {list(materials_db.keys())}"
        )
    base_mat = materials_db[material_key]
    print(f"Material: {base_mat.get('name', material_key)}")

    problem = {
        "num_vars": 3,
        "names": ["Activation_Energy", "Diffusivity", "Thickness"],
        "bounds": [[0.8, 1.2], [0.8, 1.2], [0.8, 1.2]],
    }

    param_values = sobol_sampler.sample(problem, n_samples, calc_second_order=False)

    dt = 1.0          # days
    t_horizon = 365.0  # days
    sm = ScenarioManager(t_horizon, dt)
    temps, rhs = sm.generate_climate_profile("temperate", 1)

    print(f"Evaluating {param_values.shape[0]} parameter combinations...")
    Y = evaluate_model(param_values, base_mat, temps, rhs, dt, sm.t_array)

    Si = sobol.analyze(problem, Y, calc_second_order=False, print_to_console=False)

    print("\n--- Sobol First-Order Sensitivity Indices (S1) ---")
    for name, s1 in zip(problem["names"], Si["S1"]):
        print(f"  {name:25s}: {s1:+.4f}")

    print("\n--- Sobol Total-Order Sensitivity Indices (ST) ---")
    for name, st in zip(problem["names"], Si["ST"]):
        print(f"  {name:25s}: {st:+.4f}")

    print("\nAnalysis complete.")
    return Si


if __name__ == "__main__":
    run_sobol_analysis()
