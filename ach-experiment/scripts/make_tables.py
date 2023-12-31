"""make_tables.py - render thesis-ready Markdown tables from all_results.json.

Usage:
    python scripts/make_tables.py [--results results/all_results.json] [--out results/tables.md]
"""
import argparse
import json
import os

ALGO_ORDER = ["Static-W", "Static-Wt", "HRW", "Dynamic-R", "Bounded-Loads", "CH-BL", "ACH"]
SERIES_TITLES = {
    "C1": "Stationary load", "C2": "Step + periodic + degradation",
    "C3": "Churn + hot keys (Zipf)", "C4a": "Noise sigma=0.02",
    "C4b": "Noise sigma=0.05", "C4c": "Strong noise + lag + missing",
    "TRACE": "Real-corpus popularity replay",
}
SERIES = ["C1", "C2", "C3", "C4a", "C4b", "C4c", "C-DZZ", "TRACE"]


def fmt(x, nd=4):
    return "-" if x is None else f"{x:.{nd}f}"


def d_with_ci(ad):
    """D_mean with a 95% bootstrap CI [lo, hi]; falls back to ± normal CI95."""
    lo, hi = ad.get("D_mean_boot_lo"), ad.get("D_mean_boot_hi")
    if lo is not None and hi is not None:
        return f"{fmt(ad.get('D_mean_mean'))} [{fmt(lo)}, {fmt(hi)}]"
    return f"{fmt(ad.get('D_mean_mean'))} ± {fmt(ad.get('D_mean_ci95'))}"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--results", default=None)
    ap.add_argument("--out", default=None)
    args = ap.parse_args()
    root = os.path.join(os.path.dirname(__file__), "..")
    path = args.results or os.path.join(root, "results", "all_results.json")
    out = args.out or os.path.join(root, "results", "tables.md")
    with open(path, encoding="utf-8") as f:
        d = json.load(f)

    lines = ["# Result tables (auto-generated from all_results.json)\n"]
    mc = d.get("multiple_comparisons")
    if mc:
        lines.append(f"_Multiple-comparison family: {mc['n_tests']} ACH-vs-baseline tests; "
                     f"significant at 0.05 - raw {mc['n_significant_raw_0.05']}, "
                     f"Holm {mc['n_significant_holm_0.05']}, "
                     f"BH {mc['n_significant_bh_0.05']}. D_mean shows the 95% bootstrap CI; "
                     "Cliff's δ is the effect size (positive = ACH better)._\n")

    for s in SERIES:
        sd = d.get(s)
        if not isinstance(sd, dict):
            continue
        algos = sd.get("algorithms", {})
        w = sd.get("wilcoxon_vs_ach", {})
        lines.append(f"## {s} - {SERIES_TITLES.get(s, '')}  (n_runs={sd.get('n_runs')}, "
                     f"violations={sd.get('total_violations')})\n")
        lines.append("| Algorithm | D_mean [95% bootstrap CI] | M_cum | ACH ΔD | "
                     "Cliff's δ (D) | p(Holm) |")
        lines.append("|---|---|---|---|---|---|")
        for a in ALGO_ORDER:
            ad = algos.get(a, {})
            if a not in algos:
                continue
            if a == "ACH":
                delta = cliff = pholm = "-"
            else:
                wb = w.get(a, {})
                pct = wb.get("ach_D_pct")
                delta = "-" if pct is None else f"{pct:+.1f}%"
                cd = wb.get("cliffs_D_mean")
                cliff = "-" if cd is None else f"{cd:+.2f} ({wb.get('cliffs_D_mean_mag', '')})"
                pholm = fmt(wb.get("p_D_mean_holm"), 5)
            lines.append(f"| {a} | {d_with_ci(ad)} | {fmt(ad.get('M_cum_mean'), 3)} | "
                         f"{delta} | {cliff} | {pholm} |")
        lines.append("")

    with open(out, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))
    print(f"Wrote {out}  ({len(lines)} lines)")


if __name__ == "__main__":
    main()
