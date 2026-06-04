# Physics-Based Degradation Simulator for Sustainable Packaging

## Abstract
This project presents a highly optimized, physics-based simulator designed to evaluate the environmental degradation and mechanical lifecycle of biodegradable packaging materials (e.g., PLA, Thermoplastic Starch, Bagasse composites). Abandoning black-box ML/DL models in favor of interpretable engineering and chemistry fundamentals, the simulator couples kinetic degradation models with structural analysis to predict residual strength across stochastic environmental scenarios. The tool empowers researchers to conduct rapid, deterministic lifecycle assessments under real-world supply chain stressors.

## Introduction
Sustainable packaging materials often face unpredictable degradation pathways in dynamic supply chains. Current evaluation methods either rely on expensive, time-consuming physical testing or opaque machine learning models that lack physical interpretability. This project introduces a computational companion that bridges the "lifetime evaluation gap" by utilizing established physical chemistry and mechanics. We provide an interactive, batch-accelerated Monte Carlo dashboard for comparative material studies, enabling the design of resilient, sustainable packaging.

## Related Work
- **Kinetic Degradation Models**: Foundational work on Arrhenius kinetics for hydrolytic and thermal decay.
- **Moisture Sorption**: Guggenheim-Anderson-de Boer (GAB) isotherm modeling for equilibrium moisture content in biopolymers.
- **Composite Mechanics**: Classical Lamination Theory (CLT) (Jones, R.M., 1999) applied to time-dependent degradation of laminates.
- **Sensitivity Analysis**: Variance-based global sensitivity analysis using Saltelli sampling and Sobol indices (Saltelli, A. et al., 2010).

## Proposed System
### System Concept
The simulator models the degradation of packaging trays over a specified time horizon (e.g., 365 days). It samples environmental profiles (Temperature, Relative Humidity) via Monte Carlo methods to simulate diverse climate scenarios (Temperate, Tropical, Cold, Hot Dry, Refrigerated). The kinetic modules compute molecular weight decay and moisture uptake, which are then mapped to macroscopic structural knockdown factors to predict mechanical failure.

### Tech Stack
- **Backend (Physics Engine)**: Pure Python with `NumPy` for vectorized, hardware-agnostic tensor operations and PDE solving. `SALib` for global sensitivity analysis.
- **Frontend (Interactive UI)**: `Streamlit` for the web dashboard, providing real-time 1D/3D visualization and parameter tuning.
- **Visualization**: `Plotly` for interactive 3D surface plots and confidence bands.
- **Data Management**: `PyYAML` for the parametric material database.

## Methodology
The simulation engine relies on the following core physical models:

1. **Thermal & UV Degradation (Arrhenius Kinetics)**:
   Chain scission and molecular weight ($M_w$) loss are modeled using the Arrhenius equation:
   $$k(T) = A \cdot \exp\left(-\frac{E_a}{R \cdot T}\right)$$
   UV-induced degradation is coupled with temperature and irradiance:
   $$k_{uv}(T, I) = k_{uv,base} \cdot I \cdot \exp\left(-\frac{E_{a,uv}}{R \cdot T}\right)$$

2. **Moisture Uptake (GAB Isotherm & Fickian Diffusion)**:
   Equilibrium moisture ($M_{eq}$) is determined by the GAB isotherm:
   $$M_{eq} = \frac{X_m \cdot C \cdot K \cdot a_w}{(1 - K \cdot a_w)(1 - K \cdot a_w + C \cdot K \cdot a_w)}$$
   Transient 1D/3D uptake is solved via Fick's Second Law using an explicit FTCS (Forward-Time Central-Space) finite difference scheme.

3. **Structural Knockdown (Classical Lamination Theory)**:
   A phenomenological mapping combines $M_w$ loss and moisture plasticization into a knockdown factor:
   $$kd(t) = \exp\left(-\left[\left(1 - \frac{M_w(t)}{M_{w0}}\right) + 0.5 \cdot M(t)\right]\right)$$
   This factor reduces the lamina stiffness matrix $[Q]$, which is then assembled into the macroscopic $[A]$, $[B]$, and $[D]$ matrices via CLT.

4. **Sensitivity & Monte Carlo Analysis**:
   Environmental profiles use normal distributions around base climate parameters. Sobol analysis identifies the primary parameter drivers (e.g., Activation Energy) for failure time variance.

## Results and Discussion
The simulator outputs provide multi-dimensional insights into material behavior:
- **1D Degradation Trajectories**: Displays the median residual strength over time with 90% confidence intervals under varying climates.
- **3D Moisture Diffusion**: Visualizes spatial moisture gradients across the packaging geometry over time.
- **Sobol Sensitivity Indices**: Identifies that Thermal Activation Energy ($E_a$) dominates the variance in predicted failure times, validating the Arrhenius-driven kinetic model.
- **Visual Diversity for Demonstration**: By adjusting the *Environment* (e.g., Tropical vs. Refrigerated), the *Material* (e.g., Bagasse/PLA vs. TPS), and the *Failure Criteria* ($E$ and $\sigma$ thresholds), users can observe distinct failure profiles, from rapid structural collapse to prolonged stability.

## Future Scope
- **Vision Integration**: Integration of a Vision Adapter using YOLO to detect pre-existing surface defects and adjust the initial damage offset ($M_0$) in the Fickian solver.
- **Empirical Validation**: Expansion of the `materials.yaml` database with empirically validated constants from laboratory weathering tests.
- **Complex Geometries**: Support for complex, non-rectangular packaging geometries in the 3D PDE solver.

## Conclusion
The Degradation Simulator offers a robust, physics-driven alternative to purely empirical lifecycle assessments. By seamlessly linking molecular-level kinetics with macroscopic structural mechanics, it enables researchers to predict the viability of sustainable packaging across global supply chains.

## Acknowledgement
We would like to acknowledge the foundational work in composite mechanics and biopolymer kinetics that made this simulation possible. We extend our gratitude to our advisors and institution for their guidance and support throughout this research.

## References
**Kinetic Degradation & Thermodynamics**
1. Laycock, B., et al. (2017). "Lifetime prediction of biodegradable polymers." *Progress in Polymer Science*, 71, 144-189. [Link](https://doi.org/10.1016/j.progpolymsci.2017.02.004)
2. Tsuji, H. (2002). "Autocatalytic hydrolysis of amorphous-made polylactides: effects of L-lactide content, tacticity, and enantiomeric polymer blending." *Polymer*, 43(6), 1789-1796. [Link](https://doi.org/10.1016/S0032-3861(02)00004-9)
3. Rizzarelli, P., et al. (2004). "Thermal and hydrolytic degradation of biodegradable aliphatic polyesters." *Polymer Degradation and Stability*, 85(2), 855-863. [Link](https://doi.org/10.1016/j.polymdegradstab.2004.01.026)
4. Garlotta, D. (2001). "A Literature Review of Poly(Lactic Acid)." *Journal of Polymers and the Environment*, 9(2), 63-84. [Link](https://doi.org/10.1023/A:1020200822435)

**Moisture Sorption & Diffusion**
5. Crank, J. (1975). *The Mathematics of Diffusion*. Oxford University Press. [Link](https://global.oup.com/academic/product/the-mathematics-of-diffusion-9780198534112)
6. Bizot, H. (1983). "Using the 'GAB' model to construct sorption isotherms." *Physical Properties of Foods*, 43-54. [Link](https://cir.nii.ac.jp/crid/1574231874288077568)
7. Al-Muhtaseb, A. H., et al. (2002). "Moisture sorption isotherms characteristics of food products: A review." *Food Research International*, 35(6), 537-550. [Link](https://doi.org/10.1016/S0963-9969(01)00199-5)

**Composite Mechanics & Structural Simulation**
8. Jones, R. M. (1999). *Mechanics of Composite Materials*. Taylor & Francis. [Link](https://doi.org/10.1201/9781498711867)
9. Halpin, J. C., & Tsai, S. W. (1969). "Effects of environmental factors on composite materials." *Air Force Materials Lab*. [Link](https://apps.dtic.mil/sti/citations/AD0692481)

**Monte Carlo & Sensitivity Analysis**
10. Saltelli, A., et al. (2010). "Variance based sensitivity analysis of model output. Design and estimator for the total sensitivity index." *Computer Physics Communications*, 181(2), 259-270. [Link](https://doi.org/10.1016/j.cpc.2009.09.018)
11. Sobol, I. M. (2001). "Global sensitivity indices for nonlinear mathematical models and their Monte Carlo estimates." *Mathematics and Computers in Simulation*, 55(1-3), 271-280. [Link](https://doi.org/10.1016/S0378-4754(00)00270-6)

**Biodegradable Packaging Materials**
12. Siracusa, V., et al. (2008). "Biodegradable polymers for food packaging: a review." *Trends in Food Science & Technology*, 19(12), 634-643. [Link](https://doi.org/10.1016/j.tifs.2008.07.003)
13. Averous, L. (2004). "Biodegradable multiphase systems based on plasticized starch: a review." *Journal of Macromolecular Science, Part C*, 44(3), 231-274. [Link](https://doi.org/10.1081/MC-200029326)
14. Jamshidian, M., et al. (2010). "Poly-Lactic Acid: production, applications, nanocomposites, and release studies." *Comprehensive Reviews in Food Science and Food Safety*, 9(5), 552-571. [Link](https://doi.org/10.1111/j.1541-4337.2010.00126.x)
15. Rhim, J. W., et al. (2013). "Bio-nanocomposites for food packaging applications." *Progress in Polymer Science*, 38(10-11), 1629-1652. [Link](https://doi.org/10.1016/j.progpolymsci.2013.05.008)
