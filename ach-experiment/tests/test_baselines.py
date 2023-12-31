"""Baseline parity: every rebalancing baseline must respect v_min.

This is a regression guard for the historical bug where Bounded-Loads could
drain a node down to 1 token while ACH/Dynamic-R kept >= v_min, giving it an
unfair advantage (and 1568 invariant violations in series C3).
"""
import numpy as np
import pytest

from src.algorithms.bounded_loads import BoundedLoads
from src.algorithms.dynamic_r import DynamicR
from src.ring import HashRing

V_MIN = 3


def _stress(algo, n=10, V=100, steps=120, seed=0):
    """Hold node 0 persistently overloaded so it must shed tokens repeatedly."""
    ring = HashRing(V=V, n_nodes=n, seed=seed)
    ell = np.full(n, 0.30)
    ell[0] = 1.60
    for t in range(steps):
        algo.step(ring, ell, float(np.mean(ell)), t)
    return np.bincount(ring.a, minlength=n)


@pytest.mark.parametrize("algo", [BoundedLoads(v_min=V_MIN), DynamicR(v_min=V_MIN)])
def test_baseline_respects_v_min(algo):
    counts = _stress(algo)
    assert counts.min() >= V_MIN, f"{algo.name}: node drained to {counts.min()} (< v_min={V_MIN})"


def test_bounded_loads_v_min_regression():
    # Buggy code drained to 1; fixed code must floor at v_min.
    assert _stress(BoundedLoads(v_min=3)).min() >= 3
