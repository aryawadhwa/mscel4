"""
Unit tests for VisionAdapter — validates all Adapter Mathematics.

Tests cover:
    - I₀ computation with known area ratios
    - Material parameter adaptation (E, σ, UV, moisture)
    - Edge cases: I₀ = 0 (total damage), I₀ = 1 (pristine)
    - Moisture offset integration with Fickian uptake
    - UV rate scaling
    - Detection summary for UI
"""

import sys
import os
import numpy as np

# Add backend/src to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "src")))

from simulator.vision_adapter import VisionAdapter
from simulator.modules.moisture import MoistureModule


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

def make_adapter(n=1.5):
    """Create a VisionAdapter with default weights."""
    return VisionAdapter(calibration_n=n)


def make_detections(*items):
    """Helper to build detection dicts from (class_name, area_ratio) tuples."""
    return [
        {"class_name": name, "area_ratio": ratio}
        for name, ratio in items
    ]


def sample_material():
    """Return a minimal material dict matching materials.yaml structure."""
    return {
        "name": "Test Material",
        "baseline_e": 3.5e9,
        "baseline_sigma": 60.0e6,
        "uv_base": 1.0e-5,
        "mw_0": 150000.0,
        "gab_xm": 0.02,
        "gab_c": 5.0,
        "gab_k": 0.9,
    }


# ---------------------------------------------------------------------------
# Test: I₀ Computation
# ---------------------------------------------------------------------------

def test_I0_no_damage():
    """Pristine packaging: no detections → I₀ = 1.0."""
    adapter = make_adapter()
    I0 = adapter.compute_integrity_factor([])
    assert I0 == 1.0, f"Expected I₀=1.0, got {I0}"


def test_I0_single_crack():
    """Single crack covering 10% of area: I₀ = 1 - (0.8 × 0.10) = 0.92."""
    adapter = make_adapter()
    dets = make_detections(("crack", 0.10))
    I0 = adapter.compute_integrity_factor(dets)
    assert abs(I0 - 0.92) < 1e-6, f"Expected I₀≈0.92, got {I0}"


def test_I0_multi_damage():
    """Multiple damage types: crack 10% + moisture 15% + discoloration 20%."""
    adapter = make_adapter()
    dets = make_detections(
        ("crack", 0.10),       # 0.8 × 0.10 = 0.080
        ("moisture", 0.15),    # 0.5 × 0.15 = 0.075
        ("discoloration", 0.20)  # 0.2 × 0.20 = 0.040
    )
    # I₀ = 1.0 - (0.080 + 0.075 + 0.040) = 1.0 - 0.195 = 0.805
    I0 = adapter.compute_integrity_factor(dets)
    assert abs(I0 - 0.805) < 1e-6, f"Expected I₀≈0.805, got {I0}"


def test_I0_total_destruction():
    """Extreme damage: I₀ should clamp to 0.0 (not go negative)."""
    adapter = make_adapter()
    dets = make_detections(
        ("crack", 0.80),
        ("erosion", 0.50),
        ("moisture", 0.60),
    )
    I0 = adapter.compute_integrity_factor(dets)
    assert I0 == 0.0, f"Expected I₀=0.0 (clamped), got {I0}"


# ---------------------------------------------------------------------------
# Test: CLT Stiffness / Strength Knockdown
# ---------------------------------------------------------------------------

def test_stiffness_knockdown_n1():
    """Linear knockdown (n=1): E_adapted = E₀ × I₀."""
    adapter = make_adapter(n=1.0)
    E_adapted = adapter.adapt_stiffness(3.5e9, 0.80)
    expected = 3.5e9 * 0.80
    assert abs(E_adapted - expected) < 1.0, f"Expected {expected}, got {E_adapted}"


def test_stiffness_knockdown_n2():
    """Quadratic knockdown (n=2): E_adapted = E₀ × I₀²."""
    adapter = make_adapter(n=2.0)
    E_adapted = adapter.adapt_stiffness(3.5e9, 0.80)
    expected = 3.5e9 * 0.80**2
    assert abs(E_adapted - expected) < 1.0, f"Expected {expected}, got {E_adapted}"


def test_strength_knockdown():
    """σ_adapted = σ₀ × I₀^n."""
    adapter = make_adapter(n=1.5)
    sigma = adapter.adapt_strength(60.0e6, 0.90)
    expected = 60.0e6 * 0.90**1.5
    assert abs(sigma - expected) < 1.0, f"Expected {expected}, got {sigma}"


# ---------------------------------------------------------------------------
# Test: UV Rate Scaling
# ---------------------------------------------------------------------------

def test_uv_no_discoloration():
    """No discoloration → k_UV unchanged."""
    adapter = make_adapter()
    k_adapted = adapter.adapt_uv_rate(1.0e-5, [])
    assert k_adapted == 1.0e-5, f"Expected 1e-5, got {k_adapted}"


def test_uv_with_discoloration():
    """30% discoloration → k_UV × 1.3."""
    adapter = make_adapter()
    dets = make_detections(("discoloration", 0.30))
    k_adapted = adapter.adapt_uv_rate(1.0e-5, dets)
    expected = 1.0e-5 * 1.30
    assert abs(k_adapted - expected) < 1e-10, f"Expected {expected}, got {k_adapted}"


# ---------------------------------------------------------------------------
# Test: Moisture Offset
# ---------------------------------------------------------------------------

def test_moisture_offset_none():
    """No moisture detection → M₀ = 0."""
    adapter = make_adapter()
    m0 = adapter.adapt_moisture_initial(0.05, [])
    assert m0 == 0.0, f"Expected 0.0, got {m0}"


def test_moisture_offset_15_percent():
    """15% moisture area → M₀ = 0.15 × M_eq."""
    adapter = make_adapter()
    meq = 0.05
    dets = make_detections(("moisture", 0.15))
    m0 = adapter.adapt_moisture_initial(meq, dets)
    expected = 0.15 * meq
    assert abs(m0 - expected) < 1e-10, f"Expected {expected}, got {m0}"


def test_fickian_with_offset():
    """Fickian uptake with m0_offset should start higher and converge to same meq."""
    mm = MoistureModule(gab_xm=0.02, gab_c=5.0, gab_k=0.9,
                         d_eff=1.0e-13, thickness=0.002)
    meq = np.array(0.05)
    t = np.linspace(0, 365, 100)

    standard = mm.fickian_uptake(t, meq, m0_offset=0.0)
    adapted = mm.fickian_uptake(t, meq, m0_offset=0.01)

    # At t=0, adapted should start at ~0.01, standard at ~0
    assert adapted[0] > standard[0], "Adapted should start higher"
    # Both should converge toward meq
    assert abs(standard[-1] - adapted[-1]) < 0.01, "Should converge to similar value"


# ---------------------------------------------------------------------------
# Test: Unified Material Adaptation
# ---------------------------------------------------------------------------

def test_adapt_material_params():
    """Full pipeline: adapt all params from detection results."""
    adapter = make_adapter(n=1.5)
    mat = sample_material()
    dets = make_detections(
        ("crack", 0.10),       # Stiffness/strength knockdown
        ("moisture", 0.15),    # Moisture offset
        ("discoloration", 0.20)  # UV rate scaling
    )

    adapted = adapter.adapt_material_params(mat, dets)

    # Original should be unmodified
    assert mat["baseline_e"] == 3.5e9, "Original must not be mutated"

    # I₀ = 1 - (0.8*0.1 + 0.5*0.15 + 0.2*0.2) = 1 - 0.195 = 0.805
    I0 = adapted["vision_I0"]
    assert abs(I0 - 0.805) < 1e-6, f"I₀ mismatch: {I0}"

    # E_adapted = 3.5e9 × 0.805^1.5
    expected_E = 3.5e9 * (0.805 ** 1.5)
    assert abs(adapted["baseline_e"] - expected_E) < 1.0, \
        f"E mismatch: {adapted['baseline_e']} vs {expected_E}"

    # UV scaled by discoloration
    expected_uv = 1.0e-5 * (1 + 0.20)
    assert abs(adapted["uv_base"] - expected_uv) < 1e-12, \
        f"UV mismatch: {adapted['uv_base']} vs {expected_uv}"

    # Moisture area stored
    assert abs(adapted["vision_moisture_area_ratio"] - 0.15) < 1e-6


# ---------------------------------------------------------------------------
# Test: Damage Summary
# ---------------------------------------------------------------------------

def test_summarize_detections():
    """Summary output format for UI."""
    adapter = make_adapter()
    dets = make_detections(("crack", 0.10), ("moisture", 0.05))
    summary = adapter.summarize_detections(dets)

    assert "damage_breakdown" in summary
    assert "I0" in summary
    assert summary["damage_breakdown"]["crack"] == 10.0
    assert summary["damage_breakdown"]["moisture"] == 5.0


# ---------------------------------------------------------------------------
# Runner
# ---------------------------------------------------------------------------

def run_all_tests():
    """Run all tests and report results."""
    tests = [
        test_I0_no_damage,
        test_I0_single_crack,
        test_I0_multi_damage,
        test_I0_total_destruction,
        test_stiffness_knockdown_n1,
        test_stiffness_knockdown_n2,
        test_strength_knockdown,
        test_uv_no_discoloration,
        test_uv_with_discoloration,
        test_moisture_offset_none,
        test_moisture_offset_15_percent,
        test_fickian_with_offset,
        test_adapt_material_params,
        test_summarize_detections,
    ]

    passed = 0
    failed = 0

    for test in tests:
        try:
            test()
            print(f"  PASS {test.__name__}")
            passed += 1
        except AssertionError as e:
            print(f"  FAIL {test.__name__}: {e}")
            failed += 1
        except Exception as e:
            print(f"  FAIL {test.__name__}: EXCEPTION -- {e}")
            failed += 1

    print(f"\n{'='*50}")
    print(f"Results: {passed} passed, {failed} failed, {passed + failed} total")
    return failed == 0


if __name__ == "__main__":
    print("Running VisionAdapter Unit Tests\n")
    success = run_all_tests()
    sys.exit(0 if success else 1)
