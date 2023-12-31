import numpy as np

from src.effectsize import bootstrap_ci_mean, cliffs_delta


def test_cliffs_all_greater_is_one():
    d, m = cliffs_delta([5, 6, 7], [1, 2, 3])
    assert d == 1.0 and m == "large"


def test_cliffs_identical_is_zero():
    d, m = cliffs_delta([1, 2, 3], [1, 2, 3])
    assert d == 0.0 and m == "negligible"


def test_cliffs_antisymmetric():
    d1, _ = cliffs_delta([1, 2, 3], [4, 5, 6])
    d2, _ = cliffs_delta([4, 5, 6], [1, 2, 3])
    assert abs(d1 + d2) < 1e-9


def test_bootstrap_contains_mean_and_ordered():
    x = np.arange(30.0)
    lo, hi = bootstrap_ci_mean(x, seed=0)
    assert lo < x.mean() < hi and lo < hi


def test_bootstrap_deterministic():
    x = np.random.RandomState(1).normal(0, 1, 40)
    assert bootstrap_ci_mean(x, seed=7) == bootstrap_ci_mean(x, seed=7)
