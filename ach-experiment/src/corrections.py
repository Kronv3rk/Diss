"""Multiple-comparison corrections (pure NumPy, no extra dependencies).

Provides Holm-Bonferroni (controls family-wise error rate) and
Benjamini-Hochberg (controls false discovery rate), plus a helper that
annotates an all_results.json dict with adjusted p-values across the family
of ACH-vs-baseline Wilcoxon tests.
"""
from __future__ import annotations

import numpy as np

_METRIC_PS = ("p_D_mean", "p_M_cum")


def holm(pvals) -> np.ndarray:
    """Holm-Bonferroni step-down adjusted p-values (monotone, clipped to 1)."""
    p = np.asarray(pvals, dtype=float)
    m = p.size
    order = np.argsort(p)
    adj = np.empty(m)
    running = 0.0
    for rank, idx in enumerate(order):
        running = max(running, (m - rank) * p[idx])
        adj[idx] = min(running, 1.0)
    return adj


def benjamini_hochberg(pvals) -> np.ndarray:
    """Benjamini-Hochberg step-up adjusted p-values (FDR, monotone, clipped)."""
    p = np.asarray(pvals, dtype=float)
    m = p.size
    order = np.argsort(p)
    adj = np.empty(m)
    running = 1.0
    for rank in range(m - 1, -1, -1):
        idx = order[rank]
        running = min(running, p[idx] * m / (rank + 1))
        adj[idx] = min(running, 1.0)
    return adj


def annotate_results(results: dict) -> dict:
    """Add `_holm` and `_bh` adjusted p-values to every wilcoxon_vs_ach entry,
    correcting across the whole family of ACH-vs-baseline tests. Returns the
    same dict (mutated) with a top-level `multiple_comparisons` summary."""
    keys, pv = [], []
    for series, sd in results.items():
        w = sd.get("wilcoxon_vs_ach") if isinstance(sd, dict) else None
        if not isinstance(w, dict):
            continue
        for base, bd in w.items():
            for pk in _METRIC_PS:
                if isinstance(bd, dict) and bd.get(pk) is not None:
                    keys.append((series, base, pk))
                    pv.append(float(bd[pk]))
    if not pv:
        return results
    h = holm(pv)
    bh = benjamini_hochberg(pv)
    for (series, base, pk), ph, pb in zip(keys, h, bh):
        entry = results[series]["wilcoxon_vs_ach"][base]
        entry[pk + "_holm"] = float(ph)
        entry[pk + "_bh"] = float(pb)
    results["multiple_comparisons"] = {
        "family": "ACH vs each baseline (Wilcoxon signed-rank), metrics D_mean & M_cum",
        "n_tests": len(pv),
        "methods": ["holm (FWER)", "benjamini_hochberg (FDR)"],
        "n_significant_raw_0.05": int(sum(p < 0.05 for p in pv)),
        "n_significant_holm_0.05": int(sum(p < 0.05 for p in h)),
        "n_significant_bh_0.05": int(sum(p < 0.05 for p in bh)),
    }
    return results
