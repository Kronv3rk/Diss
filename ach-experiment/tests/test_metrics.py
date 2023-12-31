"""Tests for src/metrics.compute_D - the dispersion metric all results rest on."""
import numpy as np

from src.metrics import compute_D


def test_balanced_load_is_zero():
    assert compute_D(np.array([0.5, 0.5, 0.5])) == 0.0


def test_known_value():
    # max=3, mean=1 -> D=2
    assert compute_D(np.array([3.0, 0.0, 0.0])) == 2.0


def test_nonnegative_scalar_exact():
    d = compute_D(np.array([0.1, 0.9, 0.4, 0.6]))  # max .9 mean .5
    assert isinstance(d, float)
    assert d >= 0.0
    assert abs(d - 0.4) < 1e-12
