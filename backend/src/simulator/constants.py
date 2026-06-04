"""
Shared physical constants and pure functions for the mscel4 degradation simulator.

All constants are documented with units and source references so that the
computational companion can be audited against the paper's methods section.
"""

import numpy as np

# ---------------------------------------------------------------------------
# Physical constants
# ---------------------------------------------------------------------------

R_GAS = 8.314  # J / (mol·K) — IUPAC 2018 value

# ---------------------------------------------------------------------------
# Simulation defaults (used by standalone scripts for reproducibility)
# ---------------------------------------------------------------------------

UV_BASELINE_W_M2 = 40.0  # W/m² — baseline UV irradiance used in all paper runs
COURANT_SAFETY = 0.9      # CFL safety factor for explicit FTCS schemes (dimensionless)


# ---------------------------------------------------------------------------
# Pure isotherm functions
# ---------------------------------------------------------------------------

def gab_equilibrium_moisture(xm: float, c: float, k: float, aw: float) -> float:
    """
    GAB (Guggenheim-Anderson-de Boer) sorption isotherm.

    Returns equilibrium moisture content M_eq (kg water / kg dry solid).

    Parameters
    ----------
    xm : float
        Monolayer moisture content  [kg/kg]
    c  : float
        GAB constant C (energy parameter, dimensionless)
    k  : float
        GAB constant K (dimensionless, 0 < k < 1)
    aw : float
        Water activity (≡ relative humidity as a fraction, 0–1)

    Raises
    ------
    ValueError
        If the denominator is numerically zero (physically degenerate inputs).
    """
    num = xm * c * k * aw
    den = (1.0 - k * aw) * (1.0 - k * aw + c * k * aw)
    if abs(den) < 1e-12:
        return 0.0
    return num / den


# ---------------------------------------------------------------------------
# Module factory
# ---------------------------------------------------------------------------

def build_modules_from_material(mat: dict, tray_thickness: float = 0.002):
    """
    Construct ThermalModule, UVModule, and MoistureModule from a material dict
    loaded from materials.yaml.

    This factory centralises the YAML key unpacking that was previously
    copy-pasted across every script and the Streamlit frontend.

    Parameters
    ----------
    mat            : dict   Material entry from materials.yaml
    tray_thickness : float  Thickness of the packaging tray [m] (default 2 mm)

    Returns
    -------
    (ThermalModule, UVModule, MoistureModule)
    """
    # Local imports to avoid circular imports at module level
    from simulator.modules.thermal import ThermalModule
    from simulator.modules.uv import UVModule
    from simulator.modules.moisture import MoistureModule

    tm = ThermalModule(
        float(mat["thermal_a"]),
        float(mat["thermal_ea"]),
        float(mat["mw_0"]),
    )
    uv = UVModule(
        float(mat["uv_base"]),
        float(mat["uv_ea"]),
    )
    mm = MoistureModule(
        float(mat["gab_xm"]),
        float(mat["gab_c"]),
        float(mat["gab_k"]),
        float(mat["d_eff"]),
        thickness=float(mat.get("thickness", tray_thickness)),
    )
    return tm, uv, mm
