"""
plot_series_bars.py – Bar charts of the aggregate metrics per series.

Reads results/all_results.json (the committed aggregate) rather than the
per-run JSONs, so the figures always match the numbers in the thesis tables.

Per series it draws:
  * D_bars_<series>.svg  – mean D with its 95% bootstrap CI, one bar per algorithm
  * M_bars_<series>.svg  – cumulative key migration M_cum (omitted when every
                           algorithm in the series moves zero keys)

and one overview figure across all series:
  * D_bars_overview.svg  – small multiples, one panel per series

Bars carry hatch fills and a printed value above each bar, so identity and
magnitude survive greyscale printing and colour-vision deficiency.

Usage
-----
    python scripts/plot_series_bars.py --output-dir plots
    python scripts/plot_series_bars.py --series C2 --labels ru --output-dir plots
"""

import argparse
import json
import math
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt

from src.plotstyle import (
    ALGO_ORDER,
    SERIES,
    labels,
    series_titles,
    set_style,
    style_for,
)

TEXT_INK = "#2b2b2b"


def _algos_present(series_data: dict) -> list:
    algos = series_data.get("algorithms", {})
    known = [a for a in ALGO_ORDER if a in algos]
    extra = sorted(set(algos) - set(ALGO_ORDER))
    return known + extra


def _value_and_err(agg: dict, metric: str):
    """Mean plus asymmetric 95% error bar.

    Prefers the bootstrap interval (what make_tables.py reports); falls back to
    the normal-theory CI95 when the bootstrap bounds are absent.
    """
    mean = agg.get(f"{metric}_mean")
    if mean is None or (isinstance(mean, float) and math.isnan(mean)):
        return None, 0.0, 0.0
    lo, hi = agg.get(f"{metric}_boot_lo"), agg.get(f"{metric}_boot_hi")
    if lo is not None and hi is not None and not math.isnan(lo) and not math.isnan(hi):
        return float(mean), max(0.0, float(mean) - float(lo)), max(0.0, float(hi) - float(mean))
    ci = agg.get(f"{metric}_ci95")
    ci = 0.0 if ci is None or math.isnan(ci) else float(ci)
    return float(mean), ci, ci


def _fmt(v: float, lang: str, nd: int) -> str:
    s = f"{v:.{nd}f}"
    return s.replace(".", ",") if lang == "ru" else s


def _draw_bars(ax, series_data: dict, metric: str, lang: str, nd: int,
               tick_labels: bool = True) -> bool:
    """Draw one panel of bars. Returns False when there is nothing to show."""
    label = labels(lang)
    algos = _algos_present(series_data)
    aggs  = series_data.get("algorithms", {})

    xs, means, lo_err, hi_err, names = [], [], [], [], []
    for i, algo in enumerate(algos):
        mean, lo, hi = _value_and_err(aggs.get(algo, {}), metric)
        if mean is None:
            continue
        xs.append(i)
        means.append(mean)
        lo_err.append(lo)
        hi_err.append(hi)
        names.append(algo)

    if not means or not any(m > 0 for m in means):
        return False

    for x, mean, lo, hi, algo in zip(xs, means, lo_err, hi_err, names):
        st = style_for(algo)
        ax.bar(x, mean, width=0.74,
               color=st["color"], alpha=0.85,
               edgecolor=st["color"], linewidth=0.8,
               hatch=st["hatch"] or None, zorder=2)
        ax.errorbar(x, mean, yerr=[[lo], [hi]], fmt="none",
                    ecolor=TEXT_INK, elinewidth=1.0, capsize=3, zorder=3)

    top = max(m + h for m, h in zip(means, hi_err))
    for x, mean, hi in zip(xs, means, hi_err):
        ax.text(x, mean + hi + top * 0.035, _fmt(mean, lang, nd),
                ha="center", va="bottom", fontsize=plt.rcParams["font.size"] - 3.5,
                color=TEXT_INK, zorder=4)

    ax.set_xticks(xs)
    if tick_labels:
        ax.set_xticklabels([label.get(a, a) for a in names],
                           rotation=30, ha="right")
    else:
        ax.set_xticklabels([])
    ax.set_xlim(-0.7, (xs[-1] if xs else 0) + 0.7)
    ax.set_ylim(0, top * 1.22)
    ax.grid(True, axis="y", linestyle=":", alpha=0.4, linewidth=0.6)
    ax.set_axisbelow(True)
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)
    return True


def plot_series_metric(series_data: dict, series: str, metric: str,
                       output_dir: str, lang: str, fmt: str = "svg") -> None:
    """One figure: bars of ``metric`` for every algorithm in one series."""
    set_style()
    nd = 4 if metric == "D_mean" else 3
    fig, ax = plt.subplots(figsize=(7.2, 4.2))

    if not _draw_bars(ax, series_data, metric, lang, nd):
        plt.close(fig)
        print(f"[SKIP] {series}: {metric} is zero for every algorithm")
        return

    scenario = series_titles(lang).get(series, "")
    head = (f"Серия {series}" if lang == "ru" else f"Series {series}")
    if scenario:
        head = f"{head}: {scenario}"

    if metric == "D_mean":
        ylab = "Средний разбаланс $\\bar{D}$" if lang == "ru" else "Mean imbalance $\\bar{D}$"
        what = ("Разбаланс нагрузки (ниже — лучше)" if lang == "ru"
                else "Load imbalance (lower is better)")
    else:
        ylab = "$M_{\\rm cum}$"
        what = ("Суммарная миграция ключей (ниже — лучше)" if lang == "ru"
                else "Cumulative key migration (lower is better)")

    ax.set_ylabel(ylab)
    ax.set_title(f"{head}. {what}")
    n_runs = series_data.get("n_runs")
    note = None
    if n_runs:
        note = (f"n = {n_runs} прогонов, усы — 95 % бутстрэп-ДИ" if lang == "ru"
                else f"n = {n_runs} runs, whiskers = 95% bootstrap CI")

    # Reserve a strip under the rotated tick labels so the note cannot land on them.
    fig.tight_layout(rect=(0, 0.07, 1, 1) if note else None)
    if note:
        fig.text(0.01, 0.012, note, ha="left", va="bottom",
                 fontsize=plt.rcParams["font.size"] - 3.5, color="#6b6b6b")
    os.makedirs(output_dir, exist_ok=True)
    name = "D_bars" if metric == "D_mean" else "M_bars"
    out_path = os.path.join(output_dir, f"{name}_{series}.{fmt}")
    fig.savefig(out_path, format=fmt, bbox_inches="tight")
    plt.close(fig)
    print(f"Saved: {out_path}")


def plot_overview(results: dict, series_list: list, output_dir: str, lang: str,
                  fmt: str = "svg") -> None:
    """Small multiples: mean D per algorithm, one panel per series."""
    panels = [s for s in series_list
              if isinstance(results.get(s), dict) and results[s].get("algorithms")]
    if not panels:
        print("[SKIP] overview: no series with algorithms")
        return

    set_style()
    ncols = 4
    nrows = math.ceil(len(panels) / ncols)
    fig, axes = plt.subplots(nrows, ncols, figsize=(4.0 * ncols, 3.2 * nrows),
                             squeeze=False)
    label = labels(lang)

    for idx, series in enumerate(panels):
        ax = axes[idx // ncols][idx % ncols]
        _draw_bars(ax, results[series], "D_mean", lang, 3, tick_labels=False)
        ax.set_title(series)
        if idx % ncols == 0:
            ax.set_ylabel("$\\bar{D}$")

    for idx in range(len(panels), nrows * ncols):
        axes[idx // ncols][idx % ncols].axis("off")

    handles = [
        plt.Rectangle((0, 0), 1, 1,
                      facecolor=style_for(a)["color"], alpha=0.85,
                      edgecolor=style_for(a)["color"],
                      hatch=style_for(a)["hatch"] or None)
        for a in ALGO_ORDER
    ]
    fig.legend(handles, [label.get(a, a) for a in ALGO_ORDER],
               loc="lower center", ncol=min(len(ALGO_ORDER), 4),
               frameon=False, bbox_to_anchor=(0.5, -0.02))

    title = ("Средний разбаланс $\\bar{D}$ по сериям (ниже — лучше)" if lang == "ru"
             else "Mean imbalance $\\bar{D}$ by series (lower is better)")
    fig.suptitle(title, y=1.0)
    fig.tight_layout(rect=(0, 0.06, 1, 0.99))

    os.makedirs(output_dir, exist_ok=True)
    out_path = os.path.join(output_dir, f"D_bars_overview.{fmt}")
    fig.savefig(out_path, format=fmt, bbox_inches="tight")
    plt.close(fig)
    print(f"Saved: {out_path}")


def main():
    parser = argparse.ArgumentParser(
        description="Bar charts of aggregate metrics from all_results.json."
    )
    root = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..")
    parser.add_argument("--results", default=os.path.join(root, "results", "all_results.json"),
                        help="Path to all_results.json.")
    parser.add_argument("--series", nargs="+", default=SERIES,
                        help=f"Series to plot (default: {' '.join(SERIES)}).")
    parser.add_argument("--output-dir", default=os.path.join(root, "plots"),
                        help="Directory to save SVG plots.")
    parser.add_argument("--labels", choices=["en", "ru"], default="en",
                        help="Legend/axis language: 'en' algorithm names "
                             "or 'ru' thesis A0-A4 labels.")
    parser.add_argument("--format", choices=["svg", "png", "pdf"], default="svg",
                        help="Output file format (default: svg).")
    parser.add_argument("--no-overview", action="store_true",
                        help="Skip the cross-series small-multiples figure.")
    args = parser.parse_args()

    with open(args.results, encoding="utf-8") as f:
        results = json.load(f)

    for series in args.series:
        sd = results.get(series)
        if not isinstance(sd, dict) or not sd.get("algorithms"):
            print(f"[SKIP] {series}: not in {os.path.basename(args.results)}")
            continue
        plot_series_metric(sd, series, "D_mean", args.output_dir, args.labels, args.format)
        plot_series_metric(sd, series, "M_cum", args.output_dir, args.labels, args.format)

    if not args.no_overview:
        plot_overview(results, args.series, args.output_dir, args.labels, args.format)


if __name__ == "__main__":
    main()
