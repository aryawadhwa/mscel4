import os
import sys
import yaml
import numpy as np
import plotly.graph_objects as go

# Setup path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "src")))
from simulator.scenario_manager import ScenarioManager
from simulator.modules.thermal import ThermalModule
from simulator.modules.uv import UVModule
from simulator.modules.moisture import MoistureModule
from simulator.property_mapper import PropertyMapper
from simulator.integrity_checker import IntegrityChecker

def generate_paper_figures():
    print("Generating Q1 Paper Figures...")
    db_path = os.path.join(os.path.dirname(__file__), "..", "data", "materials.yaml")
    with open(db_path, "r") as f:
        materials_db = yaml.safe_load(f)
        
    # Compare Bagasse/PLA vs pure TPS under Tropical vs Cold Chain
    materials = ["bagasse_pla", "starch"]
    climates = ["tropical", "cold_chain"]
    
    dt = 1.0
    t_horizon = 365.0
    num_scenarios = 500 # High N for smooth confidence bands
    
    sm = ScenarioManager(t_horizon, dt)
    pm = PropertyMapper()
    
    fig = go.Figure()
    
    colors = {
        "bagasse_pla_tropical": "rgba(255, 99, 71, 1.0)",
        "bagasse_pla_cold_chain": "rgba(65, 105, 225, 1.0)",
        "starch_tropical": "rgba(255, 165, 0, 1.0)",
        "starch_cold_chain": "rgba(135, 206, 250, 1.0)"
    }
    
    for climate in climates:
        temps, rhs = sm.generate_climate_profile(climate, num_scenarios)
        
        for mat_key in materials:
            mat = materials_db[mat_key]
            tm = ThermalModule(float(mat["thermal_a"]), float(mat["thermal_ea"]), float(mat["mw_0"]))
            uv = UVModule(float(mat["uv_base"]), float(mat["uv_ea"]))
            mm = MoistureModule(float(mat["gab_xm"]), float(mat["gab_c"]), float(mat["gab_k"]), float(mat["d_eff"]), thickness=0.002, nodes=5)
            
            k_t = tm.compute_k(temps)
            k_uv = uv.compute_k_uv(temps, np.ones_like(temps) * 40.0)
            
            mw_t = tm.compute_mw_decay(k_t + k_uv, sm.t_array)
            moisture = mm.solve_1d_ham_pde(dt * 86400, rhs)
            
            knockdown = pm.compute_knockdown(mw_t, mat["mw_0"], moisture)
            
            # Extract median and 5th/95th percentiles across scenarios
            kd_np = np.array(knockdown)
            median_kd = np.median(kd_np, axis=0)
            p05_kd = np.percentile(kd_np, 5, axis=0)
            p95_kd = np.percentile(kd_np, 95, axis=0)
            
            time_np = np.array(sm.t_array)
            label = f"{mat['name']} ({climate.replace('_', ' ').title()})"
            color_key = f"{mat_key}_{climate}"
            
            # Add median line
            fig.add_trace(go.Scatter(
                x=time_np, y=median_kd,
                mode='lines',
                name=label,
                line=dict(color=colors[color_key], width=3)
            ))
            
            # Add confidence bands
            fig.add_trace(go.Scatter(
                x=np.concatenate([time_np, time_np[::-1]]),
                y=np.concatenate([p95_kd, p05_kd[::-1]]),
                fill='toself',
                fillcolor=colors[color_key].replace("1.0)", "0.2)"),
                line=dict(color='rgba(255,255,255,0)'),
                hoverinfo="skip",
                showlegend=False
            ))
            
            print(f"Processed {label}")

    fig.update_layout(
        title="Cross-Material Comparison: Residual Strength Over Time (90% CI)",
        xaxis_title="Time (Days)",
        yaxis_title="Residual Strength Knockdown (σ / σ0)",
        template="simple_white",
        font=dict(family="Arial", size=14),
        legend=dict(x=0.05, y=0.05, bordercolor="Black", borderwidth=1)
    )
    
    out_path = os.path.join(os.path.dirname(__file__), "fig_climate_comparison.html")
    fig.write_html(out_path)
    print(f"Interactive figure saved to {out_path}")
    print("For static PDF/PNG, install kaleido and use fig.write_image()")

if __name__ == "__main__":
    generate_paper_figures()
