import streamlit as st
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
from simulator.modules.moisture import MoistureModule
from simulator.property_mapper import PropertyMapper
from simulator.integrity_checker import IntegrityChecker
from simulator.recommender import Recommender
from simulator.vision_adapter import load_adapter_from_config
from simulator.yolo_inference import YOLOInference, is_model_available

st.set_page_config(page_title="Degradation Simulator", layout="wide")
st.title("Physics-Based Degradation Simulator for Sustainable Packaging")

# Load Material DB
db_path = os.path.join(backend_path, "data", "materials.yaml")
with open(db_path, "r") as f:
    materials_db = yaml.safe_load(f)

adapter_config_path = os.path.join(backend_path, "data", "adapter_config.yaml")
with open(adapter_config_path, "r") as f:
    adapter_cfg = yaml.safe_load(f)

model_path = os.path.join(
    backend_path,
    adapter_cfg.get("yolo_model_path", "models/best.onnx").replace("backend/", ""),
)
model_available = is_model_available(model_path)

# ---------------------------------------------------------------------------
# Sidebar — environment
# ---------------------------------------------------------------------------
st.sidebar.header("Environment & Scenarios")
t_horizon = st.sidebar.number_input("Time Horizon (days)", value=365.0)
dt = st.sidebar.number_input("Time Step (days)", value=1.0)
base_temp = st.sidebar.slider("Base Temperature (K)", 273.0, 350.0, 308.0)
uv_intensity = st.sidebar.slider("UV Intensity (W/m2)", 0.0, 100.0, 40.0)
target_life = st.sidebar.number_input("Required Service Life (days)", value=180.0)
base_rh = st.sidebar.slider("Base Relative Humidity", 0.0, 1.0, 0.7)

st.sidebar.header("Failure Criteria")
e_thresh = st.sidebar.slider("Stiffness Threshold (E/E0)", 0.1, 1.0, 0.6)
s_thresh = st.sidebar.slider("Strength Threshold (σ/σ0)", 0.1, 1.0, 0.5)

# ---------------------------------------------------------------------------
# Sidebar — Vision-Adaptive Mode
# ---------------------------------------------------------------------------
st.sidebar.header("Vision-Adaptive Mode")
uploaded_image = st.sidebar.file_uploader(
    "Upload Packaging Image", type=["jpg", "png", "jpeg"]
)
vision_adaptive = st.sidebar.toggle("Vision-Adaptive Simulation", value=False)
calibration_n = st.sidebar.slider(
    "Calibration Exponent (n)", 0.5, 3.0, 1.5, disabled=not vision_adaptive
)

vision_active = False
detections = []
vision_summary = None
annotated_bgr = None
adapter = None

if vision_adaptive:
    if not uploaded_image:
        st.sidebar.info("Upload an image to enable vision-adaptive simulation.")
    elif not model_available:
        st.sidebar.warning(
            f"No ONNX model at `{model_path}`. "
            "Train and export with `backend/training/train_yolov8_seg.py`, "
            "or run in standard mode."
        )
    else:
        vision_active = True
        adapter = load_adapter_from_config(
            adapter_config_path, calibration_n_override=calibration_n
        )

        try:
            import cv2

            file_bytes = np.asarray(bytearray(uploaded_image.read()), dtype=np.uint8)
            image_bgr = cv2.imdecode(file_bytes, cv2.IMREAD_COLOR)
        except ImportError:
            from PIL import Image

            image_bgr = np.array(Image.open(uploaded_image).convert("RGB"))[:, :, ::-1]

        yolo = YOLOInference(
            model_path,
            conf_threshold=float(adapter_cfg.get("confidence_threshold", 0.25)),
            input_size=int(adapter_cfg.get("input_size", 640)),
        )
        detections = yolo.predict(image_bgr)
        annotated_bgr = yolo.annotate_image(image_bgr, detections)
        vision_summary = adapter.summarize_detections(detections)

        st.sidebar.markdown("**Detected damage**")
        for cls_name, pct in vision_summary["damage_breakdown"].items():
            st.sidebar.write(f"- {cls_name}: {pct:.1f}% area")
        st.sidebar.metric("Initial Integrity Factor (I₀)", f"{vision_summary['I0']:.4f}")


def _lifetime_days(usable_mask, t_array, dt_days):
    ic_local = IntegrityChecker(e_thresh, s_thresh)
    first_fail_idx = ic_local.find_deadline_indices(usable_mask).item()
    if first_fail_idx == 0 and usable_mask[0].item():
        first_fail_idx = len(t_array) - 1
    return float(first_fail_idx * dt_days)


def run_material_trajectory(mat, sm, temps, rhs, pm, ic, detections_for_adapt=None):
    """
    Run degradation for one material.

    Returns dict with standard and (optionally) adaptive trajectories.
    """
    tm = ThermalModule(float(mat["thermal_a"]), float(mat["thermal_ea"]), float(mat["mw_0"]))
    uv = UVModule(float(mat["uv_base"]), float(mat["uv_ea"]))
    mm = MoistureModule(
        float(mat["gab_xm"]),
        float(mat["gab_c"]),
        float(mat["gab_k"]),
        float(mat["d_eff"]),
        float(mat.get("thickness", 0.002)),
    )

    k_t = tm.compute_k(temps[0])
    k_uv = uv.compute_k_uv(temps[0], np.array(uv_intensity))
    mw_t = tm.compute_mw_decay(k_t + k_uv, sm.t_array)

    aw = rhs[0] if rhs.ndim > 1 else rhs
    meq = mm.equilibrium_moisture_gab(aw if np.ndim(aw) == 0 else aw[0])
    if np.ndim(meq) == 0:
        meq_scalar = float(meq)
    else:
        meq_scalar = float(meq.flat[0])

    moisture_std = np.zeros_like(mw_t)
    knockdown_std = pm.compute_knockdown(mw_t, mat["mw_0"], moisture_std)
    usable_std = ic.evaluate_usability(knockdown_std, 1.0, knockdown_std, 1.0)
    life_std = _lifetime_days(usable_std, sm.t_array, dt)

    out = {
        "mw_std": mw_t,
        "knockdown_std": knockdown_std,
        "life_std": life_std,
        "E0": float(mat["baseline_e"]),
        "sigma0": float(mat["baseline_sigma"]),
        "I0": 1.0,
        "E_adapted": float(mat["baseline_e"]),
        "sigma_adapted": float(mat["baseline_sigma"]),
        "life_adapt": life_std,
        "mw_adapt": mw_t,
        "knockdown_adapt": knockdown_std,
    }

    if detections_for_adapt is not None and adapter is not None:
        adapted_mat = adapter.adapt_material_params(mat, detections_for_adapt)
        I0 = adapted_mat["vision_I0"]
        m0_offset = adapter.adapt_moisture_initial(meq_scalar, detections_for_adapt)

        tm_a = ThermalModule(
            float(adapted_mat["thermal_a"]),
            float(adapted_mat["thermal_ea"]),
            float(adapted_mat["mw_0"]),
        )
        uv_a = UVModule(float(adapted_mat["uv_base"]), float(adapted_mat["uv_ea"]))
        k_t_a = tm_a.compute_k(temps[0])
        k_uv_a = uv_a.compute_k_uv(temps[0], np.array(uv_intensity))
        mw_adapt = tm_a.compute_mw_decay(k_t_a + k_uv_a, sm.t_array)

        knockdown_adapt = pm.compute_knockdown_with_offset(
            mw_adapt,
            adapted_mat["mw_0"],
            sm.t_array,
            np.full_like(mw_adapt, meq_scalar),
            mm,
            m0_offset=m0_offset,
        )
        usable_adapt = ic.evaluate_usability(
            knockdown_adapt, 1.0, knockdown_adapt, 1.0
        )
        life_adapt = _lifetime_days(usable_adapt, sm.t_array, dt)

        out.update(
            {
                "I0": I0,
                "E_adapted": float(adapted_mat["baseline_e"]),
                "sigma_adapted": float(adapted_mat["baseline_sigma"]),
                "life_adapt": life_adapt,
                "mw_adapt": mw_adapt,
                "knockdown_adapt": knockdown_adapt,
            }
        )

    return out


if st.button("Run Multi-Material Comparative Study"):
    sm = ScenarioManager(t_horizon, dt)
    temps, rhs = sm.generate_scenarios(base_temp, 2.0, base_rh, 0.1, 1)

    pm = PropertyMapper()
    ic = IntegrityChecker(e_thresh, s_thresh)
    rec = Recommender(target_life)

    dets = detections if vision_active else None
    if vision_adaptive and not vision_active:
        st.info(
            "Vision-adaptive mode is enabled but no image was uploaded or no ONNX "
            "model is available. Running standard simulation."
        )

    results = []
    trajectories = {}
    time_np = np.array(sm.t_array)

    for key, mat in materials_db.items():
        traj = run_material_trajectory(mat, sm, temps, rhs, pm, ic, dets)
        trajectories[key] = traj

        delta_life = traj["life_adapt"] - traj["life_std"]
        score_data = rec.evaluate_material(
            mat["name"],
            int(traj["life_adapt"] / dt) if dt > 0 else 0,
            dt,
            mat["cost_score"],
        )
        score_data["I0"] = round(traj["I0"], 4)
        score_data["Adapted E0 (Pa)"] = f"{traj['E_adapted']:.3e}"
        score_data["Adapted σ0 (Pa)"] = f"{traj['sigma_adapted']:.3e}"
        score_data["Δ Lifetime (days)"] = round(delta_life, 1)
        score_data["Standard Life (days)"] = round(traj["life_std"], 1)
        score_data["Adaptive Life (days)"] = round(traj["life_adapt"], 1)
        results.append(score_data)

    # -----------------------------------------------------------------------
    # Vision dual-pane (detailed comparison for one material)
    # -----------------------------------------------------------------------
    if vision_active and trajectories:
        st.subheader("Vision-Adaptive Analysis")
        material_keys = list(trajectories.keys())
        mat_labels = {k: materials_db[k]["name"] for k in material_keys}
        selected_key = st.selectbox(
            "Material for Standard vs. Adaptive charts",
            material_keys,
            format_func=lambda k: mat_labels[k],
        )
        traj = trajectories[selected_key]

        col_left, col_right = st.columns(2)

        with col_left:
            st.markdown("**YOLO segmentation overlay**")
            try:
                import cv2

                st.image(
                    cv2.cvtColor(annotated_bgr, cv2.COLOR_BGR2RGB),
                    use_container_width=True,
                )
            except Exception:
                st.image(annotated_bgr[:, :, ::-1], use_container_width=True)

            if vision_summary:
                breakdown_rows = [
                    {
                        "Damage class": cls,
                        "Area (%)": pct,
                        "Weight": adapter.weights.get(cls, 0.0),
                    }
                    for cls, pct in vision_summary["damage_breakdown"].items()
                ]
                if not breakdown_rows:
                    breakdown_rows = [
                        {"Damage class": "(none)", "Area (%)": 0.0, "Weight": 0.0}
                    ]
                st.markdown("**Damage breakdown**")
                st.table(breakdown_rows)
                st.metric("Computed I₀", f"{vision_summary['I0']:.4f}")

        with col_right:
            fig_mw_cmp = go.Figure()
            fig_mw_cmp.add_trace(
                go.Scatter(
                    x=time_np,
                    y=np.array(traj["mw_std"]),
                    mode="lines",
                    name="Standard",
                    line=dict(dash="dash"),
                )
            )
            fig_mw_cmp.add_trace(
                go.Scatter(
                    x=time_np,
                    y=np.array(traj["mw_adapt"]),
                    mode="lines",
                    name="Adaptive",
                    line=dict(dash="solid"),
                )
            )
            fig_mw_cmp.update_layout(
                title="Molecular Weight Decay",
                xaxis_title="Time (days)",
                yaxis_title="Mw",
            )
            st.plotly_chart(fig_mw_cmp, use_container_width=True)

            fig_kd_cmp = go.Figure()
            fig_kd_cmp.add_trace(
                go.Scatter(
                    x=time_np,
                    y=np.array(traj["knockdown_std"]),
                    mode="lines",
                    name="Standard",
                    line=dict(dash="dash"),
                )
            )
            fig_kd_cmp.add_trace(
                go.Scatter(
                    x=time_np,
                    y=np.array(traj["knockdown_adapt"]),
                    mode="lines",
                    name="Adaptive",
                    line=dict(dash="solid"),
                )
            )
            fig_kd_cmp.update_layout(
                title="Mechanical Knockdown Factor",
                xaxis_title="Time (days)",
                yaxis_title="Residual property ratio",
            )
            st.plotly_chart(fig_kd_cmp, use_container_width=True)

            life_labels = ["Standard", "Adaptive"]
            life_values = [traj["life_std"], traj["life_adapt"]]
            fig_life = go.Figure(
                data=[
                    go.Bar(
                        x=life_labels,
                        y=life_values,
                        marker_color=["#636EFA", "#EF553B"],
                    )
                ]
            )
            fig_life.update_layout(
                title="Time-to-Failure Comparison",
                yaxis_title="Predicted lifetime (days)",
            )
            st.plotly_chart(fig_life, use_container_width=True)

    # -----------------------------------------------------------------------
    # Multi-material overview charts
    # -----------------------------------------------------------------------
    fig_mw = go.Figure()
    fig_kd = go.Figure()

    for key, mat in materials_db.items():
        traj = trajectories[key]
        label = mat["name"]
        if vision_active:
            fig_mw.add_trace(
                go.Scatter(
                    x=time_np,
                    y=np.array(traj["mw_std"]),
                    mode="lines",
                    name=f"{label} (std)",
                    line=dict(dash="dash"),
                )
            )
            fig_mw.add_trace(
                go.Scatter(
                    x=time_np,
                    y=np.array(traj["mw_adapt"]),
                    mode="lines",
                    name=f"{label} (adapt)",
                )
            )
            fig_kd.add_trace(
                go.Scatter(
                    x=time_np,
                    y=np.array(traj["knockdown_std"]),
                    mode="lines",
                    name=f"{label} (std)",
                    line=dict(dash="dash"),
                )
            )
            fig_kd.add_trace(
                go.Scatter(
                    x=time_np,
                    y=np.array(traj["knockdown_adapt"]),
                    mode="lines",
                    name=f"{label} (adapt)",
                )
            )
        else:
            fig_mw.add_trace(
                go.Scatter(
                    x=time_np, y=np.array(traj["mw_std"]), mode="lines", name=label
                )
            )
            fig_kd.add_trace(
                go.Scatter(
                    x=time_np,
                    y=np.array(traj["knockdown_std"]),
                    mode="lines",
                    name=label,
                )
            )

    if not vision_active:
        col1, col2 = st.columns(2)
        with col1:
            fig_mw.update_layout(
                title="Molecular Weight Decay",
                xaxis_title="Time (Days)",
                yaxis_title="Mw",
            )
            st.plotly_chart(fig_mw, use_container_width=True)
        with col2:
            fig_kd.update_layout(
                title="Mechanical Knockdown Factor",
                xaxis_title="Time (Days)",
                yaxis_title="Residual Property Ratio",
            )
            st.plotly_chart(fig_kd, use_container_width=True)

    st.subheader("Recommender Scoring")
    st.table(results)
