"""
run_sensitivity.py – Execute C5 parameter sensitivity sweep for ACH.

Sweeps eps_on and kappa independently (one parameter varied, others at default)
and records D_mean, M_cum, pi_chg for ACH only across n_runs repeats.

Usage
-----
    python scripts/run_sensitivity.py [--n-runs 10] [--output-dir results/C5]
                                       [--config-dir configs]
"""

import sys
import os
import argparse
import json
import copy
import time

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import numpy as np
import yaml

from src.experiment import run_experiment


def _load_config(config_dir: str) -> dict:
    base_path  = os.path.join(config_dir, "base.yaml")
    c5_path    = os.path.join(config_dir, "series_c5.yaml")
    with open(base_path) as f:
        base = yaml.safe_load(f)
    with open(c5_path) as f:
        c5 = yaml.safe_load(f)
    merged = dict(base)
    for k, v in c5.items():
        if k != "extends":
            if isinstance(v, dict) and isinstance(merged.get(k), dict):
                merged[k] = {**merged[k], **v}
            else:
                merged[k] = v
    return merged


def _run_grid_point(cfg: dict, param_name: str, param_val: float,
                    n_runs: int, base_seed: int) -> dict:
    """Run n_runs with a single ACH parameter overridden. Return aggregate stats."""
    cfg = copy.deepcopy(cfg)
    cfg["ach"][param_name] = param_val

    D_vals, M_vals, pi_vals = [], [], []
    for r in range(n_runs):
        seed = base_seed + r * 1000
        results = run_experiment(cfg, seed=seed)
        agg = results["ACH"]["agg"]
        D_vals.append(agg["D_mean"])
        M_vals.append(agg["M_cum"])
        pi_vals.append(agg["pi_chg"])

    return {
        "D_mean":  float(np.mean(D_vals)),
        "D_ci":    float(1.96 * np.std(D_vals, ddof=1) / np.sqrt(n_runs)),
        "M_cum":   float(np.mean(M_vals)),
        "M_ci":    float(1.96 * np.std(M_vals, ddof=1) / np.sqrt(n_runs)),
        "pi_chg":  float(np.mean(pi_vals)),
        "pi_ci":   float(1.96 * np.std(pi_vals, ddof=1) / np.sqrt(n_runs)),
        "n_runs":  n_runs,
    }


def run_sensitivity(n_runs: int, output_dir: str,
                    config_dir: str, base_seed: int = 42):
    cfg = _load_config(config_dir)
    sens = cfg.get("sensitivity", {})
    eps_on_vals = sens.get("eps_on", [0.05, 0.08, 0.10, 0.15, 0.20])
    kappa_vals  = sens.get("kappa",  [0.05, 0.10, 0.15, 0.20])

    os.makedirs(output_dir, exist_ok=True)
    results = {"eps_on": {}, "kappa": {}}

    # --- Sweep eps_on (eps_off = eps_on * 0.4, kappa at default) ---
    print("Sweeping eps_on  (kappa=default={:.2f}):".format(
        cfg["ach"].get("kappa", 0.10)))
    print(f"  {'eps_on':>8}  {'D_mean':>9}  {'M_cum':>9}  {'pi_chg':>9}")

    for eps in eps_on_vals:
        t0 = time.time()
        cfg_local = copy.deepcopy(cfg)
        cfg_local["ach"]["eps_on"]  = eps
        cfg_local["ach"]["eps_off"] = round(eps * 0.4, 4)

        D_vals, M_vals, pi_vals = [], [], []
        for r in range(n_runs):
            seed = base_seed + r * 1000
            res = run_experiment(cfg_local, seed=seed)
            agg = res["ACH"]["agg"]
            D_vals.append(agg["D_mean"])
            M_vals.append(agg["M_cum"])
            pi_vals.append(agg["pi_chg"])

        row = {
            "eps_off": round(eps * 0.4, 4),
            "D_mean":  float(np.mean(D_vals)),
            "D_ci":    float(1.96 * np.std(D_vals, ddof=1) / np.sqrt(n_runs)),
            "M_cum":   float(np.mean(M_vals)),
            "M_ci":    float(1.96 * np.std(M_vals, ddof=1) / np.sqrt(n_runs)),
            "pi_chg":  float(np.mean(pi_vals)),
            "pi_ci":   float(1.96 * np.std(pi_vals, ddof=1) / np.sqrt(n_runs)),
        }
        results["eps_on"][str(eps)] = row
        elapsed = time.time() - t0
        print(f"  {eps:8.2f}  {row['D_mean']:9.4f}  {row['M_cum']:9.4f}"
              f"  {row['pi_chg']:9.4f}  ({elapsed:.1f}s)")

    # --- Sweep kappa (eps_on/eps_off at default) ---
    print("\nSweeping kappa  (eps_on=default={:.2f}):".format(
        cfg["ach"].get("eps_on", 0.10)))
    print(f"  {'kappa':>8}  {'D_mean':>9}  {'M_cum':>9}  {'pi_chg':>9}")

    for kap in kappa_vals:
        t0 = time.time()
        row = _run_grid_point(cfg, "kappa", kap, n_runs, base_seed)
        results["kappa"][str(kap)] = row
        elapsed = time.time() - t0
        print(f"  {kap:8.2f}  {row['D_mean']:9.4f}  {row['M_cum']:9.4f}"
              f"  {row['pi_chg']:9.4f}  ({elapsed:.1f}s)")

    # Save results
    out_path = os.path.join(output_dir, "sensitivity_results.json")
    with open(out_path, "w") as f:
        json.dump(results, f, indent=2)
    print(f"\nSaved: {out_path}")

    # Print CI table
    print("\n--- eps_on sweep (mean ± 95% CI) ---")
    print(f"  {'eps_on':>6}  {'D_mean':>15}  {'M_cum':>15}  {'pi_chg':>15}")
    for k, v in results["eps_on"].items():
        print(f"  {float(k):6.2f}  "
              f"{v['D_mean']:7.4f}±{v['D_ci']:.4f}  "
              f"{v['M_cum']:7.4f}±{v['M_ci']:.4f}  "
              f"{v['pi_chg']:7.4f}±{v['pi_ci']:.4f}")

    print("\n--- kappa sweep (mean ± 95% CI) ---")
    print(f"  {'kappa':>6}  {'D_mean':>15}  {'M_cum':>15}  {'pi_chg':>15}")
    for k, v in results["kappa"].items():
        print(f"  {float(k):6.2f}  "
              f"{v['D_mean']:7.4f}±{v['D_ci']:.4f}  "
              f"{v['M_cum']:7.4f}±{v['M_ci']:.4f}  "
              f"{v['pi_chg']:7.4f}±{v['pi_ci']:.4f}")

    return results


def main():
    parser = argparse.ArgumentParser(
        description="Run ACH sensitivity sweep (series C5)."
    )
    parser.add_argument("--n-runs",     type=int, default=10)
    parser.add_argument("--output-dir", default=None)
    parser.add_argument("--config-dir", default=None)
    parser.add_argument("--base-seed",  type=int, default=42)
    args = parser.parse_args()

    script_dir = os.path.dirname(os.path.abspath(__file__))
    repo_dir   = os.path.join(script_dir, "..")
    config_dir = args.config_dir or os.path.join(repo_dir, "configs")
    output_dir = args.output_dir or os.path.join(repo_dir, "results", "C5")

    run_sensitivity(
        n_runs=args.n_runs,
        output_dir=output_dir,
        config_dir=config_dir,
        base_seed=args.base_seed,
    )


if __name__ == "__main__":
    main()
