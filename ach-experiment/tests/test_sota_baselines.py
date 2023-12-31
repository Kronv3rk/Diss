"""Tests for the SOTA baselines HRW (weighted rendezvous) and CH-BL."""
import numpy as np

from src.algorithms.ch_bounded import CHBoundedLoads
from src.algorithms.rendezvous import HRW
from src.ring import HashRing

CAPS = np.array([1.0, 1.0, 1.0, 0.55, 0.55, 0.55, 0.55, 0.25, 0.25, 0.25])
V = 1000


def _counts(ring, n):
    return np.bincount(ring.a, minlength=n)


def test_hrw_deterministic():
    r1, r2 = HashRing(V, 10, seed=1), HashRing(V, 10, seed=2)
    HRW(CAPS, V).step(r1, np.zeros(10), 0.0, 0)
    HRW(CAPS, V).step(r2, np.zeros(10), 0.0, 0)
    assert np.array_equal(r1.a, r2.a)            # placement independent of ring seed


def test_hrw_capacity_proportional_and_vmin():
    ring = HashRing(V, 10, seed=42)
    HRW(CAPS, V).step(ring, np.zeros(10), 0.0, 0)
    c = _counts(ring, 10)
    assert c.min() >= 3                          # v_min respected
    assert c[0] > 2.0 * c[9]                     # strong (1.0) >> weak (0.25)
    # proportional-ish: strong/weak count ratio near capacity ratio (4x), within tolerance
    assert 2.5 < c[:3].mean() / c[7:].mean() < 5.5


def test_chbl_caps_overloaded_and_respects_vmin():
    ring = HashRing(V, 10, seed=7)
    ell = np.full(10, 0.5)
    ell[0] = 1.5                                  # node 0 heavily overloaded
    algo = CHBoundedLoads(epsilon=0.25)
    moved = 0.0
    for t in range(50):
        moved += algo.step(ring, ell, float(np.mean(ell)), t)
    assert moved > 0.0                           # it actually rebalanced
    assert _counts(ring, 10).min() >= 3          # v_min never violated


def test_chbl_noop_when_balanced():
    ring = HashRing(V, 10, seed=0)
    ell = np.full(10, 0.65)
    assert CHBoundedLoads().step(ring, ell, 0.65, 0) == 0.0
