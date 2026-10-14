"""
granularity_check.py - How strongly does the step budget m(t) dose the moved
key share for a given number of ring tokens V?

For every ACH step with rebalancing it records the step budget m(t), the moved
key share M_keys(t), the number of moved tokens and the number of source nodes
|O(t)|, and reports per (series, V):

    ratio_median   median of M_keys(t) / m(t)   (1 = budget is the volume)
    tokens_per_src median number of tokens a source gives per step
    one_token_frac share of steps where moved tokens == number of sources
    D_mean         ACH mean imbalance after warm-up (for reference)

With V = 1000 each source gives exactly one token and M_keys/m >> 1, i.e. m(t)
acts as an on/off switch; with larger V the ratio approaches 1.

Usage
-----
    python scripts/granularity_check.py --series C1 C3 --V 1000 10000 100000 \
        --n-runs 5 --out results/granularity.json

The recording wraps ACH._rebalance; it only reads state and does not change
the algorithm, so D/M results equal those of run_series.py for the same seed.
"""
import argparse
import json
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, os.path.dirname(__file__))

import numpy as np
from run_series import _load_config

import src.algorithms.ach as ach_mod
from src.experiment import run_experiment

_REC = []
_orig_rebalance = ach_mod.ACH._rebalance


def _recording_rebalance(self, ring, ell, m):
    prev = ring.snapshot()
    n_src = int(np.sum(self.sigma == +1))
    M = _orig_rebalance(self, ring, ell, m)
    moved = int(np.sum(ring.a != prev))
    _REC.append((m, M, moved, n_src))
    return M


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--series", nargs="+", default=["C1", "C3"])
    ap.add_argument("--V", nargs="+", type=int, default=[1000, 10000, 100000])
    ap.add_argument("--n-runs", type=int, default=5)
    ap.add_argument("--base-seed", type=int, default=42)
    ap.add_argument("--out", default="results/granularity.json")
    args = ap.parse_args()

    ach_mod.ACH._rebalance = _recording_rebalance
    repo = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..")
    out = {}
    for series in args.series:
        for V in args.V:
            cfg = _load_config(series, os.path.join(repo, "configs"))
            cfg["V"] = V
            rows, D = [], []
            for r in range(args.n_runs):
                _REC.clear()
                res = run_experiment(cfg, seed=args.base_seed + r * 1000)
                D.append(res["ACH"]["agg"]["D_mean"])
                rows.extend(x for x in _REC if x[1] > 0.0)
            x = np.array(rows, dtype=np.float64)
            per_src = x[:, 2] / np.maximum(x[:, 3], 1)
            key = f"{series}_V{V}"
            out[key] = {
                "series": series, "V": V, "n_runs": args.n_runs,
                "n_active_steps": int(len(x)),
                "m_median": float(np.median(x[:, 0])),
                "M_step_median": float(np.median(x[:, 1])),
                "ratio_median": float(np.median(x[:, 1] / x[:, 0])),
                "ratio_p90": float(np.percentile(x[:, 1] / x[:, 0], 90)),
                "tokens_per_src_median": float(np.median(per_src)),
                "one_token_frac": float(np.mean(x[:, 2] == x[:, 3])),
                "D_mean": float(np.mean(D)),
            }
            o = out[key]
            print(f"{key:12s} active={o['n_active_steps']:5d}  m~{o['m_median']:.2e}  "
                  f"M/m~{o['ratio_median']:.2f} (p90 {o['ratio_p90']:.2f})  "
                  f"tok/src~{o['tokens_per_src_median']:.2f}  "
                  f"one-token={o['one_token_frac']:.2f}  D={o['D_mean']:.4f}", flush=True)
    os.makedirs(os.path.dirname(args.out) or ".", exist_ok=True)
    with open(args.out, "w") as f:
        json.dump(out, f, indent=2)
    print(f"saved {args.out}")


if __name__ == "__main__":
    main()
