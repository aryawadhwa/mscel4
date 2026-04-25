import streamlit as st
import mlx.core as mx
import numpy as np
import plotly.graph_objects as go
import yaml
import os
import sys

# Add backend/src to path
backend_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "backend"))
sys.path.append(os.path.join(backend_path, "src"))

from simulator.scenario_manager import ScenarioManager
from simulator.modules.thermal import ThermalModule
from simulator.modules.uv import UVModule
from simulator.property_mapper import PropertyMapper
from simulator.integrity_checker import IntegrityChecker
from simulator.recommender import Recommender

st.set_page_config(page_title="Degradation Simulator", layout="wide")
st.title("Physics-Based Degradation Simulator for Sustainable Packaging")

# Load Material DB
db_path = os.path.join(backend_path, "data", "materials.yaml")
with open(db_path, "r") as f:
    materials_db = yaml.safe_load(f)

st.sidebar.header("Environment & Scenarios")
t_horizon = st.sidebar.number_input("Time Horizon (days)", value=365.0)
dt = st.sidebar.number_input("Time Step (days)", value=1.0)
base_temp = st.sidebar.slider("Base Temperature (K)", 273.0, 350.0, 308.0)
uv_intensity = st.sidebar.slider("UV Intensity (W/m2)", 0.0, 100.0, 40.0)
target_life = st.sidebar.number_input("Required Service Life (days)", value=180.0)

st.sidebar.header("Failure Criteria")
e_thresh = st.sidebar.slider("Stiffness Threshold (E/E0)", 0.1, 1.0, 0.6)
s_thresh = st.sidebar.slider("Strength Threshold (σ/σ0)", 0.1, 1.0, 0.5)

if st.button("Run Multi-Material Comparative Study"):
    sm = ScenarioManager(t_horizon, dt)
    temps, rhs = sm.generate_scenarios(base_temp, 2.0, 0.7, 0.1, 1) # Hot & Humid Baseline
    
    pm = PropertyMapper()
    ic = IntegrityChecker(e_thresh, s_thresh)
    rec = Recommender(target_life)
    
    fig_mw = go.Figure()
    fig_kd = go.Figure()
    
    results = []
    
    for key, mat in materials_db.items():
        tm = ThermalModule(mat["thermal_a"], mat["thermal_ea"], mat["mw_0"])
        uv = UVModule(mat["uv_base"], mat["uv_ea"])
        
        k_t = tm.compute_k(temps[0])
        k_uv = uv.compute_k_uv(temps[0], mx.array(uv_intensity))
        
        # Total degradation kinetics
        mw_t = tm.compute_mw_decay(k_t + k_uv, sm.t_array)
        moisture = mx.zeros_like(mw_t) # Prototype isolation
        
        knockdown = pm.compute_knockdown(mw_t, mat["mw_0"], moisture)
        
        # Integrity evaluation (Knockdown drives both E and Sigma in this regime)
        usable_mask = ic.evaluate_usability(knockdown, 1.0, knockdown, 1.0)
        
        first_fail_idx = ic.find_deadline_indices(usable_mask).item()
        if first_fail_idx == 0 and usable_mask[0].item() == True:
            first_fail_idx = len(sm.t_array) - 1 # Survived the entire horizon
            
        score_data = rec.evaluate_material(mat["name"], first_fail_idx, dt, mat["cost_score"])
        results.append(score_data)
        
        time_np = np.array(sm.t_array)
        fig_mw.add_trace(go.Scatter(x=time_np, y=np.array(mw_t), mode='lines', name=mat["name"]))
        fig_kd.add_trace(go.Scatter(x=time_np, y=np.array(knockdown), mode='lines', name=mat["name"]))

    col1, col2 = st.columns(2)
    with col1:
        fig_mw.update_layout(title="Molecular Weight Decay", xaxis_title="Time (Days)", yaxis_title="Mw")
        st.plotly_chart(fig_mw, use_container_width=True)
    with col2:
        fig_kd.update_layout(title="Mechanical Knockdown Factor", xaxis_title="Time (Days)", yaxis_title="Residual Property Ratio")
        st.plotly_chart(fig_kd, use_container_width=True)
        
    st.subheader("Recommender Scoring")
    st.table(results)
