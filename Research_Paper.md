# A Computational Multi-Physics Simulator for the Environmental Degradation of Sustainable Packaging Materials

**Arya Wadhwa [1RV24CI023]**  
**Aarush Garg [1RV24CI003]**  
**Dia Arora [1RV24CI031]**  
*Material Science Lab*

**Abstract:**  
*Sustainable bioplastics such as Polylactic Acid (PLA) and Thermoplastic Starch (TPS) are critical to reducing global plastic waste. However, their physical and chemical behaviors under diverse supply chain environments remain difficult to predict without expensive, time-consuming laboratory weathering. This paper presents a novel deterministic multi-physics simulator that models the kinetic degradation, moisture sorption, and macroscopic structural collapse of biodegradable packaging. By coupling Arrhenius kinetics and Fickian spatial diffusion directly into Classical Lamination Theory (CLT), we bridge the gap between microscopic chemistry and macroscopic mechanical failure. The simulator relies strictly on interpretable physics rather than opaque machine learning architectures, enabling rapid Monte Carlo analysis of supply chain stochasticity. Results demonstrate that variance in supply chain temperature heavily drives variance in failure time, emphasizing the need for kinetic modeling in sustainable packaging design.*

---

## 1. Introduction

The global transition away from petroleum-based plastics has driven the adoption of bio-based, compostable alternatives like Polylactic Acid (PLA) and Thermoplastic Starch (TPS). While highly desirable for their environmental profiles, these materials suffer from significant sensitivity to ambient temperature and humidity [1, 2]. During global transit, packaging is subjected to fluctuating environmental stressors that accelerate hydrolytic chain scission and moisture plasticization. 

Traditionally, the lifecycle of these materials is evaluated via destructive physical testing—a bottleneck in material discovery [3]. In recent years, researchers have turned to deep learning and predictive machine learning models. However, neural networks remain "black boxes" that require massive empirical datasets to train and fail to provide the deterministic interpretability required by mechanical engineers [4].

This research proposes a computational companion that solves this problem using first-principles physics. We introduce a highly optimized, pure-Python degradation simulator. The software mathematically couples molecular kinetics (Arrhenius chain scission) and thermodynamics (Guggenheim-Anderson-de Boer isotherms) directly into the physical stiffness matrix $[Q]$ of the material [5]. A 3D Forward-Time Central-Space (FTCS) finite difference scheme visualizes moisture pooling, and Monte Carlo sampling evaluates the component's survivability under diverse climates. 

---

## 2. Methodology

The simulator architecture is divided into three coupled regimes: Chemical Degradation, Spatial Moisture Diffusion, and Structural Mechanics.

### 2.1 Thermal and UV Kinetics (Arrhenius)
We model the decay of the polymer's molecular weight ($M_w$) as a first-order kinetic process driven by temperature and ultraviolet (UV) irradiance. The combined reaction rate constant $k_{total}$ is defined as:

$$ k_{total}(T, I) = A \cdot \exp\left(-\frac{E_a}{R T}\right) + k_{uv,base} \cdot I \cdot \exp\left(-\frac{E_{a,uv}}{R T}\right) $$

where $E_a$ is the activation energy, $R$ is the universal gas constant (8.314 J/mol·K), $T$ is temperature, and $I$ is UV intensity. Over a time vector $t$, the molecular weight decays according to $M_w(t) = M_{w0} \exp(-k_{total} \cdot t)$.

### 2.2 Moisture Thermodynamics and Diffusion
Biopolymers like TPS are highly hydrophilic. To compute the equilibrium moisture content ($M_{eq}$) under a given relative humidity ($a_w$), the simulator utilizes the GAB (Guggenheim-Anderson-de Boer) thermodynamic isotherm [6]:

$$ M_{eq} = \frac{X_m \cdot C \cdot K \cdot a_w}{(1 - K \cdot a_w)(1 - K \cdot a_w + C \cdot K \cdot a_w)} $$

To visualize the transient pooling of moisture across physical packaging structures (e.g., a thermoformed tray), we solve Fick's Second Law in three dimensions:

$$ \frac{\partial C}{\partial t} = D_{eff} \left( \frac{\partial^2 C}{\partial x^2} + \frac{\partial^2 C}{\partial y^2} + \frac{\partial^2 C}{\partial z^2} \right) $$

This Partial Differential Equation (PDE) is resolved using an explicit Forward-Time Central-Space (FTCS) finite difference numerical scheme optimized via tensor operations in NumPy. Dirichlet boundary conditions ($C = M_{eq}$) are applied to the exposed surfaces.

### 2.3 Macroscopic Failure (Classical Lamination Theory)
The bridge between chemistry and mechanics is achieved through a phenomenological knockdown parameter ($kd$), which continuously reduces the material's elastic modulus:

$$ kd(t) = \exp\left(-\left[ \left(1 - \frac{M_w(t)}{M_{w0}}\right) + 0.5 \cdot C(x,y,z,t) \right]\right) $$

This knockdown factor modifies the elastic matrix $[Q]$ of the lamina. By integrating $[Q]$ across the component thickness, we assemble the $[A]$, $[B]$, and $[D]$ stiffness matrices defined by Classical Lamination Theory (CLT). The $[D]$ (bending stiffness) matrix is directly passed to a simply-supported beam deflection model to output physical sagging in millimeters [8].

---

## 3. Computational Framework and Technological Stack

To guarantee both high-performance numerical simulation and interactive user accessibility, the software architecture utilizes a modern, open-source Python stack:

- **Core Physics Engine (`NumPy`)**: The computationally expensive Partial Differential Equations (e.g., the 3D FTCS Fickian solver) and tensor algebra (Classical Lamination Theory matrices) are driven entirely by `NumPy`. This ensures the mathematical logic is aggressively vectorized and highly portable across hardware environments without requiring complex GPU toolchains.
- **Global Sensitivity Analysis (`SALib`)**: To conduct rigorous parameter influence testing, the Sensitivity Analysis Library (`SALib`) is utilized to generate Monte Carlo Saltelli samples and compute first-order and total-order Sobol sensitivity indices.
- **Interactive Interface (`Streamlit`)**: Rather than providing a rigid command-line tool, the framework is wrapped in `Streamlit`, enabling rapid hyperparameter tuning (e.g., Target Lifetimes, Climate baselines) and deterministic comparative studies via a reactive web dashboard.
- **Data Visualization (`Plotly`)**: 3D geometric sagging meshes, volumetric moisture diffusion gradients, and 1D confidence-band degradation trajectories are dynamically rendered using `Plotly`'s interactive graphing suite.
- **Database Management (`PyYAML`)**: Material properties and kinetic constants (Activation Energy, Monolayer Moisture, etc.) are strictly separated from the codebase using `PyYAML`, allowing researchers to plug in new bio-composite profiles without modifying the underlying Python logic.

---

## 4. Simulator Architecture & Dashboard

The backend physics engine is encapsulated in an interactive `Streamlit` dashboard, rendering 1D trajectories and 3D surface geometries using `Plotly`.

**Figure 1: The Simulator Dashboard Interface**  
*(Dashboard Overview showing material selection, parameter tuning, and comparative lifetime scoring)*  
![Simulator Dashboard](./dashboard_main.png)

The application evaluates a library of bio-composites defined parametrically in a YAML database. By separating the user interface from the backend physics, researchers can perform "what-if" analyses instantly, varying the supply chain horizon, target life criteria, and component geometry.

---

## 5. Results and Discussion

The multi-physics nature of the simulator allows for complex, non-linear insights into biodegradable packaging design.

### 5.1 Monte Carlo and Confidence Bands
Supply chain climates are not static. The simulator's `ScenarioManager` introduces Gaussian noise to the base temperature and humidity parameters to simulate realistic global transits. 

**Figure 2: 1D Degradation and Structural Knockdown**  
*(Comparative plots showing standard vs. adaptive knockdown factors and molecular weight decay)*  
![Comparative Results](./dashboard_results.png)

The resulting Monte Carlo plots (Figure 2) demonstrate that materials with high activation energies (e.g., PLA) exhibit extreme variance in mechanical knockdown. A slightly warmer shipment can accelerate failure by weeks, generating a massive 90% confidence interval width, proving the risk of relying purely on fixed-temperature laboratory tests.

### 5.2 Global Sensitivity Analysis (Sobol)
Using Saltelli sampling on the kinetic constants, the simulator calculated Sobol sensitivity indices for the time-to-failure output. The total-order Sobol index for Thermal Activation Energy ($S_{T,Ea} \approx 0.81$) drastically outweighed the index for Moisture Diffusivity ($S_{T,Deff} \approx 0.12$). This mathematical insight allows materials engineers to prioritize thermal stabilization additives over hydrophobic coatings for this specific class of bio-composite packaging.

### 5.3 3D Spatial Moisture Profiles
The FTCS finite difference solver successfully rendered 3D spatial diffusion gradients. Results show rapid moisture pooling at the corners of the geometry, indicating that edge-sealing strategies are the most critical geometric factor in preventing premature delamination in high-humidity (e.g., tropical) transits.

---

## 6. Future Work
Currently, the pipeline supports deterministic prediction based on ideal initial conditions. Future iterations will integrate a pre-trained YOLO computer vision model to dynamically detect physical manufacturing defects (e.g., micro-cracks) from input imagery. This visual data will alter the initial condition boundaries ($M_{0}$) of the Fickian PDE, allowing the system to adaptively downgrade the predicted lifetime for flawed packaging batches.

---

## 7. Conclusion
The computational tool developed in this study provides a vital bridge between chemical kinetics and macroscopic structural engineering. By utilizing deterministic, interpretable physical models like Arrhenius decay, the GAB isotherm, and Classical Lamination Theory, we eliminate the black-box limitations of deep learning while remaining computationally fast enough for real-time dashboard interaction. This software successfully allows for robust, multi-dimensional lifecycle assessments of sustainable biopolymers under chaotic real-world environments.

---

## References
1. Laycock, B., et al. (2017). "Lifetime prediction of biodegradable polymers." *Progress in Polymer Science*, 71, 144-189.
2. Tsuji, H. (2002). "Autocatalytic hydrolysis of amorphous-made polylactides." *Polymer*, 43(6), 1789-1796.
3. Rizzarelli, P., et al. (2004). "Thermal and hydrolytic degradation of biodegradable aliphatic polyesters." *Polymer Degradation and Stability*, 85(2), 855-863.
4. Garlotta, D. (2001). "A Literature Review of Poly(Lactic Acid)." *Journal of Polymers and the Environment*, 9(2), 63-84.
5. Crank, J. (1975). *The Mathematics of Diffusion*. Oxford University Press.
6. Bizot, H. (1983). "Using the 'GAB' model to construct sorption isotherms." *Physical Properties of Foods*, 43-54.
7. Al-Muhtaseb, A. H., et al. (2002). "Moisture sorption isotherms characteristics of food products: A review." *Food Research International*.
8. Jones, R. M. (1999). *Mechanics of Composite Materials*. Taylor & Francis.
9. Halpin, J. C., & Tsai, S. W. (1969). "Effects of environmental factors on composite materials." *Air Force Materials Lab*.
10. Saltelli, A., et al. (2010). "Variance based sensitivity analysis of model output. Design and estimator for the total sensitivity index." *Computer Physics Communications*, 181(2), 259-270.
11. Sobol, I. M. (2001). "Global sensitivity indices for nonlinear mathematical models." *Mathematics and Computers in Simulation*, 55, 271-280.
12. Siracusa, V., et al. (2008). "Biodegradable polymers for food packaging: a review." *Trends in Food Science & Technology*.
13. Averous, L. (2004). "Biodegradable multiphase systems based on plasticized starch: a review." *Journal of Macromolecular Science*.
14. Jamshidian, M., et al. (2010). "Poly-Lactic Acid: production, applications, nanocomposites, and release studies." *Comprehensive Reviews in Food Science and Food Safety*.
15. Rhim, J. W., et al. (2013). "Bio-nanocomposites for food packaging applications." *Progress in Polymer Science*.
