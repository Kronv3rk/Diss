"""Non-parametric effect size (Cliff's delta) and percentile bootstrap CIs.

Complements the Wilcoxon p-values: a p-value says *whether* ACH differs from a
baseline; Cliff's delta says *how much* (practical significance), and the
bootstrap CI gives a distribution-free interval for each mean.
"""
import numpy as np

# Romano et al. (2006) thresholds
_THRESH = ((0.147, "negligible"), (0.33, "small"), (0.474, "medium"))


def cliffs_delta(a, b):
    """Cliff's delta = P(a>b) - P(a<b) in [-1, 1], with a magnitude label.

    Used as cliffs_delta(baseline, ACH) on D so that a **positive** delta means
    the baseline tends to have larger D, i.e. ACH is better."""
    a = np.asarray(a, dtype=np.float64)
    a = a[~np.isnan(a)]
    b = np.asarray(b, dtype=np.float64)
    b = b[~np.isnan(b)]
    if a.size == 0 or b.size == 0:
        return float("nan"), "undefined"
    delta = float(np.sign(a[:, None] - b[None, :]).mean())
    mag = "large"
    for thr, label in _THRESH:
        if abs(delta) < thr:
            mag = label
            break
    return delta, mag


def bootstrap_ci_mean(x, n_boot: int = 10000, alpha: float = 0.05, seed: int = 0):
    """Percentile bootstrap CI for the mean. Returns (lo, hi)."""
    x = np.asarray(x, dtype=np.float64)
    x = x[~np.isnan(x)]
    if x.size < 2:
        return float("nan"), float("nan")
    rng = np.random.RandomState(seed)
    idx = rng.randint(0, x.size, size=(n_boot, x.size))
    means = x[idx].mean(axis=1)
    lo, hi = np.percentile(means, [100 * alpha / 2.0, 100 * (1.0 - alpha / 2.0)])
    return float(lo), float(hi)
