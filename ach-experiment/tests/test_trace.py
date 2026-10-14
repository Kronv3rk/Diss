"""Tests for real-trace popularity loading and replay in the experiment."""
import os

import numpy as np
import yaml

from src.experiment import run_experiment
from src.trace_loader import load_popularity

ROOT = os.path.join(os.path.dirname(__file__), "..")
TRACE = os.path.join(ROOT, "traces", "sample_real.csv")


def test_popularity_shape_normalized_descending():
    p = load_popularity(TRACE, 1000)
    assert len(p) == 1000
    assert abs(p.sum() - 1.0) < 1e-9
    assert np.all(np.diff(p) <= 1e-12)              # monotone non-increasing


def test_popularity_is_heavy_tailed():
    p = load_popularity(TRACE, 5000)
    assert p[:50].sum() > 0.20                      # real measured skew, not uniform


def test_experiment_runs_with_real_trace():
    cfg = yaml.safe_load(open(os.path.join(ROOT, "configs", "base.yaml")))
    cfg["T"] = 60
    cfg["load"] = {"type": "constant", "lambda": 1437.5}
    cfg["trace"] = "traces/sample_real.csv"
    res = run_experiment(cfg, seed=1)
    assert {"ACH", "HRW", "CH-BL"} <= set(res)
    for name, r in res.items():
        assert np.isfinite(r["agg"]["D_mean"])
        assert len(r["violations"]) == 0, f"{name}: {r['violations'][:2]}"


WIKI = os.path.join(ROOT, "traces", "wikipedia_en_20240115.csv")


def test_wikipedia_trace_used_by_series_trace():
    cfg = yaml.safe_load(open(os.path.join(ROOT, "configs", "series_trace.yaml")))
    assert cfg["trace"] == "traces/wikipedia_en_20240115.csv"
    p = load_popularity(WIKI, 50_000)
    assert len(p) == 50_000 and abs(p.sum() - 1.0) < 1e-9
    # Main_Page ~3.5 %, top-100 ~12.5 % of requests (one day, 2024-01-15)
    assert 0.03 < p[0] < 0.04
    assert 0.11 < p[:100].sum() < 0.14
    with open(WIKI.replace(".csv", ".csv.sha256")) as f:
        assert len([ln for ln in f if ln.strip()]) == 24   # 24 hourly dumps
