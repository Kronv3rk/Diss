"""apply_corrections.py - add Holm/BH adjusted p-values to all_results.json.

Usage:
    python scripts/apply_corrections.py [--results results/all_results.json]
"""
import argparse
import json
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from src.corrections import annotate_results


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--results", default=None,
                    help="Path to all_results.json (default: <repo>/results/all_results.json)")
    args = ap.parse_args()
    root = os.path.join(os.path.dirname(__file__), "..")
    path = args.results or os.path.join(root, "results", "all_results.json")
    with open(path) as f:
        data = json.load(f)
    annotate_results(data)
    with open(path, "w") as f:
        json.dump(data, f, indent=2)
    mc = data.get("multiple_comparisons", {})
    print(f"Annotated {path}")
    print(f"  family n={mc.get('n_tests')}  "
          f"raw<0.05={mc.get('n_significant_raw_0.05')}  "
          f"holm<0.05={mc.get('n_significant_holm_0.05')}  "
          f"bh<0.05={mc.get('n_significant_bh_0.05')}")


if __name__ == "__main__":
    main()
