# Degradation Simulator for Sustainable Packaging

A highly optimized, physics-based simulator designed to evaluate the environmental degradation and mechanical lifecycle of biodegradable packaging materials (e.g., PLA, Thermoplastic Starch, Bagasse composites).

The simulator abandons black-box ML/DL in favor of interpretable engineering and chemistry fundamentals. By pairing Arrhenius and GAB moisture kinetics with Classical Lamination Theory (CLT), it predicts the residual strength and structural viability of sustainable packaging across Monte Carlo-sampled environmental scenarios.

All tensor operations are hardware-accelerated for Apple Silicon via **MLX**.

## Architecture

The repository is modularly structured into backend computation and a frontend UI:

- **`backend/`**: Contains the core simulation engine.
  - `src/simulator/modules/`: Individual kinetic solvers (Moisture, Thermal, UV).
  - `src/simulator/external_clt/`: Core integration of Classical Lamination Theory (stripped down and embedded from external references).
  - `src/simulator/property_mapper.py`: Connects kinetic molecular weight ($M_w$) decay to macroscopic structural stiffness ($E$) and strength ($\sigma$) knockdown factors.
  - `src/simulator/recommender.py`: Rule-based recommendation heuristic outputting composite material viability scores.
  - `data/materials.yaml`: Parametric database governing activation energies and baseline strengths for composites.
- **`frontend/`**: Contains the Streamlit user interface (`app.py`).

## Installation & Setup

1. **Clone the repository:**
   ```bash
   git clone https://github.com/aryawadhwa/mscel4.git
   cd mscel4
   ```

2. **Install dependencies:**
   Ensure you have Apple's MLX framework and Streamlit installed.
   ```bash
   pip install mlx streamlit plotly pyyaml numpy pandas
   ```

3. **Run the Simulator Interface:**
   Navigate into the project root and launch Streamlit targeting the frontend directory:
   ```bash
   streamlit run frontend/app.py
   ```

## Academic Positioning
This simulator is engineered to support Q1 academic publications addressing the "lifetime evaluation gap" in biodegradable packaging. By combining deterministic kinetic physics with an interactive, batch-accelerated Monte Carlo dashboard, researchers can rapidly conduct comparative material studies simulating real-world supply chain stressors.
