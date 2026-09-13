"""
plot_traces.py – Generate matplotlib trace plots for each experiment series.

Produces D(t) traces with median and inter-quartile bands for each algorithm.
Saves plots as SVG files.

Algorithm order, colours and dash patterns come from src.plotstyle, shared with
plot_series_bars.py.

Usage
-----
    python scripts/plot_traces.py --series C1 --results-dir results/C1 \
        --output-dir plots/C1

    python scripts/plot_traces.py --input-dir results --output-dir plots
"""

import argparse
import glob
import json
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import matplotlib
import numpy as np
import yaml

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.ticker as ticker

from src.plotstyle import (
    SERIES,
    labels,
    line_style,
    present_algorithms,
    set_style,
)


def _load_results(results_dir: str) -> list:
    pattern = os.path.join(results_dir, "run_*.json")
    files   = sorted(glob.glob(pattern))
    if not files:
        raise FileNotFoundError(f"No run_*.json files in {results_dir}")
    data = []
    for path in files:
        with open(path) as f:
            data.append(json.load(f))
    return data


def _default_warmup() -> int:
    """The warmup the aggregates use, read from configs/base.yaml."""
    path = os.path.join(os.path.dirname(__file__), "..", "configs", "base.yaml")
    try:
        with open(path) as f:
            return int(yaml.safe_load(f).get("warmup", 40))
    except (OSError, ValueError, AttributeError):
        return 40


def _gather_traces(runs: list, algo: str, key: str, warmup: int = 0) -> np.ndarray:
    """Stack traces across runs into a 2D array (n_runs, T - warmup).

    The first ``warmup`` steps are dropped, matching metrics.aggregate_metrics:
    the figures then cover exactly the window the reported numbers cover. It
    also keeps the t=0 initial key placement - which moves nearly the whole key
    space once - from flattening the M_keys axis.
    """
    traces = []
    for run in runs:
        trace = run.get("algorithms", {}).get(algo, {}).get(key, [])
        if trace:
            traces.append(np.array(trace, dtype=np.float64))
    if not traces:
        return np.empty((0, 0))
    min_len = min(len(t) for t in traces)
    if warmup >= min_len:
        return np.empty((0, 0))
    return np.vstack([t[warmup:min_len] for t in traces])


def plot_D_traces(runs: list, series: str, output_dir: str, lang: str = "en",
                  fmt: str = "svg", warmup: int = 0):
    """Plot D(t) median + IQR bands for all algorithms present in the runs.

    Parameters
    ----------
    runs : list
        Loaded run data.
    series : str
        Series name (used in title and filename).
    output_dir : str
        Directory to save the SVG.
    lang : str
        'en' for code-level algorithm names, 'ru' for the thesis A0-A4 labels.
    """
    set_style()
    label = labels(lang)
    fig, ax = plt.subplots(figsize=(8, 4.5))
    data_top = 0.0

    for algo in present_algorithms(runs):
        mat = _gather_traces(runs, algo, "D_trace", warmup)
        if mat.shape[0] == 0:
            continue

        t_axis = np.arange(warmup, warmup + mat.shape[1])
        med = np.median(mat, axis=0)
        q25 = np.percentile(mat, 25, axis=0)
        q75 = np.percentile(mat, 75, axis=0)

        style = line_style(algo)
        ax.plot(t_axis, med, label=label.get(algo, algo), **style)
        ax.fill_between(t_axis, q25, q75, color=style["color"], alpha=0.13,
                        linewidth=0)
        data_top = max(data_top, float(np.max(q75)))

    ax.set_xlabel("Шаг управления $t$" if lang == "ru" else "Control step $t$")
    ax.set_ylabel("Дисбаланс нагрузки $D(t)$" if lang == "ru"
                  else "Load imbalance $D(t)$")
    # No in-figure title: the caption belongs in the thesis text.
    ax.legend(loc="upper right", framealpha=0.9, ncol=2)
    ax.yaxis.set_major_formatter(ticker.FormatStrFormatter("%.2f"))
    ax.grid(True, linestyle=":", alpha=0.4, linewidth=0.6)
    ax.set_axisbelow(True)
    ax.set_xlim(warmup, None)
    # Headroom for the two-column legend, so it never covers a curve.
    ax.set_ylim(0, data_top * 1.34 if data_top > 0 else None)

    fig.tight_layout()
    os.makedirs(output_dir, exist_ok=True)
    out_path = os.path.join(output_dir, f"D_traces_{series}.{fmt}")
    fig.savefig(out_path, format=fmt, bbox_inches="tight")
    plt.close(fig)
    print(f"Saved: {out_path}")


def plot_M_traces(runs: list, series: str, output_dir: str, lang: str = "en",
                  fmt: str = "svg", warmup: int = 0):
    """Plot M_keys(t) median + upper-quartile bands for key-moving algorithms.

    Which algorithms those are is read off the data (any algorithm whose
    M_trace is not identically zero), not from a hardcoded list.
    """
    set_style()
    label = labels(lang)
    fig, ax = plt.subplots(figsize=(8, 4.5))
    data_top = 0.0

    plotted = 0
    for algo in present_algorithms(runs):
        mat = _gather_traces(runs, algo, "M_trace", warmup)
        if mat.shape[0] == 0 or not np.any(mat > 0):
            continue  # stateless algorithms never move keys

        t_axis = np.arange(warmup, warmup + mat.shape[1])
        med = np.median(mat, axis=0)
        q75 = np.percentile(mat, 75, axis=0)

        style = line_style(algo)
        ax.plot(t_axis, med, label=label.get(algo, algo), **style)
        ax.fill_between(t_axis, 0, q75, color=style["color"], alpha=0.10,
                        linewidth=0)
        data_top = max(data_top, float(np.max(q75)))
        plotted += 1

    if plotted == 0:
        plt.close(fig)
        print(f"[SKIP] {series}: no algorithm moves keys, M plot omitted")
        return

    ax.set_xlabel("Шаг управления $t$" if lang == "ru" else "Control step $t$")
    ax.set_ylabel("$M_{\\rm keys}(t)$")
    # No in-figure title: the caption belongs in the thesis text.
    ax.legend(loc="upper right", framealpha=0.9, ncol=2)
    ax.yaxis.set_major_formatter(ticker.FormatStrFormatter("%.4f"))
    ax.grid(True, linestyle=":", alpha=0.4, linewidth=0.6)
    ax.set_axisbelow(True)
    ax.set_xlim(warmup, None)
    ax.set_ylim(0, data_top * 1.34 if data_top > 0 else None)

    fig.tight_layout()
    os.makedirs(output_dir, exist_ok=True)
    out_path = os.path.join(output_dir, f"M_traces_{series}.{fmt}")
    fig.savefig(out_path, format=fmt, bbox_inches="tight")
    plt.close(fig)
    print(f"Saved: {out_path}")


def main():
    parser = argparse.ArgumentParser(
        description="Generate trace plots for ACH experiment series."
    )
    parser.add_argument("--series",      nargs="+", default=[],
                        help="Series names (e.g. C1 C2 C3 C4a). "
                             "If omitted with --results-dir, a single unnamed series is plotted.")
    parser.add_argument("--results-dir", default=None,
                        help="Directory containing run_*.json files (single series).")
    parser.add_argument("--input-dir",   default=None,
                        help="Root results directory; auto-discovers series subdirectories.")
    parser.add_argument("--output-dir",  default=None,
                        help="Directory to save SVG plots. Default: <results-dir>/plots/")
    parser.add_argument("--labels",      choices=["en", "ru"], default="en",
                        help="Legend/axis language: 'en' algorithm names "
                             "or 'ru' thesis A0-A4 labels.")
    parser.add_argument("--format",      choices=["svg", "png", "pdf"], default="svg",
                        help="Output file format (default: svg).")
    parser.add_argument("--warmup",      type=int, default=None,
                        help="Steps to drop from the start of each trace. Default: the "
                             "warmup in configs/base.yaml, so the figures cover the same "
                             "window as the reported aggregates.")
    args = parser.parse_args()

    warmup = _default_warmup() if args.warmup is None else args.warmup

    # Determine (results_dir, series_name) pairs to process
    jobs = []

    if args.input_dir:
        series_list = args.series if args.series else SERIES
        root = args.input_dir
        for s in series_list:
            d = os.path.join(root, s)
            if os.path.isdir(d):
                out = args.output_dir or os.path.join(root, "plots")
                jobs.append((d, s, out))
            else:
                print(f"[SKIP] {s}: directory not found at {d}")
    elif args.results_dir:
        s = args.series[0] if args.series else ""
        out = args.output_dir or os.path.join(args.results_dir, "plots")
        jobs.append((args.results_dir, s, out))
    else:
        parser.error("Provide either --results-dir or --input-dir.")

    for results_dir, series_name, output_dir in jobs:
        try:
            runs = _load_results(results_dir)
            print(f"Loaded {len(runs)} runs from {results_dir}")
            plot_D_traces(runs, series=series_name, output_dir=output_dir, lang=args.labels,
                          fmt=args.format, warmup=warmup)
            plot_M_traces(runs, series=series_name, output_dir=output_dir, lang=args.labels,
                          fmt=args.format, warmup=warmup)
        except FileNotFoundError as e:
            print(f"[SKIP] {series_name}: {e}")


if __name__ == "__main__":
    main()
