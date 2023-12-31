"""Tests for src/corrections.py (Holm & Benjamini-Hochberg)."""
import numpy as np

from src.corrections import annotate_results, benjamini_hochberg, holm


def test_holm_known_value():
    p = [0.01, 0.04, 0.03, 0.005]
    adj = holm(p)
    assert abs(adj[3] - 0.02) < 1e-9          # smallest p .005 -> *4
    assert np.all(adj >= np.array(p) - 1e-12)
    assert np.all(adj <= 1.0)


def test_bh_known_value():
    adj = benjamini_hochberg([0.01, 0.02, 0.03, 0.04])
    assert np.allclose(adj, 0.04)


def test_monotone_and_bounded():
    p = np.random.RandomState(0).uniform(0, 1, 25)
    for fn in (holm, benjamini_hochberg):
        a = fn(p)
        assert np.all(a >= p - 1e-12)
        assert np.all(a <= 1.0 + 1e-12)


def test_annotate_results_minimal():
    d = {"C1": {"wilcoxon_vs_ach": {"Base": {"p_D_mean": 0.001, "p_M_cum": 0.2}}}}
    annotate_results(d)
    e = d["C1"]["wilcoxon_vs_ach"]["Base"]
    assert "p_D_mean_holm" in e and "p_D_mean_bh" in e
    assert d["multiple_comparisons"]["n_tests"] == 2
