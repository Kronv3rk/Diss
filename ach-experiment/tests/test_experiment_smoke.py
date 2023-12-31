"""Smoke test for the core experiment loop: finite metrics, zero violations."""
import os

import numpy as np
import yaml

from src.experiment import run_experiment


def _cfg(T=80):
    root = os.path.join(os.path.dirname(__file__), "..")
    with open(os.path.join(root, "configs", "base.yaml")) as f:
        cfg = yaml.safe_load(f)
    cfg["T"] = T
    cfg["load"] = {"type": "constant", "lambda": 1437.5}
    return cfg


def test_run_experiment_smoke():
    res = run_experiment(_cfg(), seed=42)
    assert set(res) >= {"ACH", "Static-W", "Static-Wt", "Dynamic-R", "Bounded-Loads"}
    for name, r in res.items():
        agg = r["agg"]
        assert np.isfinite(agg["D_mean"]) and agg["D_mean"] >= 0.0
        assert np.isfinite(agg["D_max"])
        assert len(r["violations"]) == 0, f"{name}: invariant violations {r['violations'][:3]}"
