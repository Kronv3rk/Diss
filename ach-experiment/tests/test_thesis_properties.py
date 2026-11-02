"""Focused verification of the conditional ACH claims in dissertation sections 2.5/4.5.

This suite is not a mathematical proof and does not replay the 420,000 steps.
Run: pytest -q tests/test_thesis_properties.py
"""

import json
from pathlib import Path

import numpy as np

from src.algorithms.ach import ACH
from src.ring import HashRing


PARAMS = {
    "ell_star": 0.65, "eps_on": 0.10, "eps_off": 0.04,
    "tau": 0.85, "tau_min": 0.50, "kappa": 0.10,
    "M_max": 0.02, "M_H": 0.25, "H": 100, "v_min": 3,
}


def _imbalanced():
    values = np.full(10, 0.65)
    values[0], values[1] = 0.90, 0.40
    return values


def test_p1_and_p3_budget_and_direction():
    """Step cost has one-token slack; only overloaded sources donate."""
    ring = HashRing(V=1000, n_nodes=10, seed=42)
    controller = ACH(dict(PARAMS))
    ell = _imbalanced()
    m = controller._compute_budget(controller._compute_C(0.60, ell), 0)
    before = ring.snapshot()
    cost = controller.step(ring, ell, total_load=0.60, t=0)
    changed = np.flatnonzero(ring.a != before)
    assert cost > 0 and changed.size > 0
    assert cost <= m + np.sum(controller.sigma == 1) * max(ring.L) + 1e-9
    assert set(before[changed]) == {0}
    assert set(ring.a[changed]) == {1}


def test_p2_rolling_window_bound_with_last_step_slack():
    """The H-window bound includes the largest step; it is not sum <= M_H."""
    ring = HashRing(V=1000, n_nodes=10, seed=42)
    controller = ACH(dict(PARAMS))
    steps = [controller.step(ring, _imbalanced(), 0.60, t) for t in range(200)]
    assert any(x > 0 for x in steps)
    h, cap = controller.H, controller.M_H
    maximal_step = max(steps)
    for end in range(h - 1, len(steps)):
        assert sum(steps[end + 1 - h:end + 1]) <= cap + maximal_step + 1e-9


def test_p4_stopping_once_all_nodes_reenter_neutral_zone():
    """Only conditional stabilization; reachability is not claimed."""
    ring = HashRing(V=1000, n_nodes=10, seed=42)
    controller = ACH(dict(PARAMS))
    controller.step(ring, _imbalanced(), 0.60, t=0)
    assert controller.sigma[0] == 1 and controller.sigma[1] == -1
    neutral = np.full(10, PARAMS["ell_star"])
    before = ring.snapshot()
    assert controller.step(ring, neutral, 0.60, t=1) == 0
    assert np.all(controller.sigma == 0)
    assert np.array_equal(ring.a, before)


def test_p5_bounded_aggregate_noise_cannot_start_hysteresis():
    """Noise bound applies to ell, not directly to Gaussian raw metrics."""
    ring = HashRing(V=1000, n_nodes=10, seed=42)
    controller = ACH(dict(PARAMS))
    true_load = np.full(10, PARAMS["ell_star"]) + np.linspace(-0.039, 0.039, 10)
    for t, sign in enumerate((1, -1, 1, -1)):
        measured = true_load + sign * PARAMS["eps_off"]
        assert controller.step(ring, measured, 0.60, t=t) == 0
        assert np.all(controller.sigma == 0)


def test_archived_reductions_and_horizon_slack():
    """Audit stored aggregate numbers, not an independent experiment rerun."""
    results_file = Path(__file__).resolve().parents[1] / "results" / "all_results.json"
    data = json.loads(results_file.read_text(encoding="utf-8"))
    thesis = {"C1": 21.0, "C2": 62.8, "C3": 65.4, "C4a": 22.5,
              "C4b": 26.9, "C4c": 11.2, "TRACE": 18.7}
    for series, expected in thesis.items():
        record = data[series]
        actual = record["algorithms"]["ACH"]["D_mean_mean"]
        control = record["algorithms"]["Static-W"]["D_mean_mean"]
        reduction = 100 * (control - actual) / control
        assert abs(reduction - expected) < 0.11, (series, reduction, expected)
        assert record["total_violations"] == 0
        alg = record["algorithms"]["ACH"]
        assert alg["M_win_max_mean"] <= PARAMS["M_H"] + alg["M_step_max_mean"] + 1e-9
    # C4c exceeds the nominal M_H, but not M_H plus last-step tolerance.
    assert data["C4c"]["algorithms"]["ACH"]["M_win_max_mean"] > PARAMS["M_H"]
