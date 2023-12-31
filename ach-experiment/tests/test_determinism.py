"""Determinism: same seed -> bit-identical aggregates; different seed -> differs."""
import os

import yaml

from src.experiment import run_experiment


def _cfg(T=60):
    root = os.path.join(os.path.dirname(__file__), "..")
    with open(os.path.join(root, "configs", "base.yaml")) as f:
        cfg = yaml.safe_load(f)
    cfg["T"] = T
    cfg["load"] = {"type": "constant", "lambda": 1437.5}
    return cfg


def test_same_seed_identical():
    a = run_experiment(_cfg(), seed=123)
    b = run_experiment(_cfg(), seed=123)
    for name in a:
        assert a[name]["agg"] == b[name]["agg"], f"{name} not reproducible for fixed seed"


def test_different_seed_differs():
    a = run_experiment(_cfg(), seed=1)
    b = run_experiment(_cfg(), seed=2)
    assert any(a[n]["agg"] != b[n]["agg"] for n in a)
