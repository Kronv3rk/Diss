"""
make_thesis_figures.py - Greyscale figures for the thesis and the autoreferat.

    fig_series_bars_<S>.png  - Fig. 4.1 / 4.3 / 4.5: mean D (95 % bootstrap CI)
                               and cumulative rebuild cost per algorithm
    fig_traces_<S>.png       - Fig. 4.2 / 4.4 / 4.6: median D(t) and median
                               cumulative cost with inter-quartile bands
    fig_overview.png         - autoreferat Fig. 3: mean D, ACH vs A0, per series
    fig_timeline.png         - Fig. 3.4: time structure of the series

Bars read results/all_results.json; traces read the per-run JSONs.

Usage
-----
    python scripts/make_thesis_figures.py --results-dir results --output-dir plots/thesis
"""

import argparse
import glob
import json
import os

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

ORDER = ["Static-W", "Static-Wt", "HRW", "Dynamic-R", "Bounded-Loads", "CH-BL", "ACH"]
LAB = {
    "Static-W": "А0 статическое",
    "Static-Wt": "А1 взвешенное",
    "HRW": "HRW",
    "Dynamic-R": "А2 динамическое",
    "Bounded-Loads": "А3 огранич. нагрузки",
    "CH-BL": "CH-BL",
    "ACH": "А4 разработанный",
}
BAR = {
    "Static-W": ("white", ""),
    "Static-Wt": ("white", "//"),
    "HRW": ("white", "\\\\"),
    "Dynamic-R": ("white", "xx"),
    "Bounded-Loads": ("#dddddd", ".."),
    "CH-BL": ("white", "++"),
    "ACH": ("#4d4d4d", ""),
}
LINE = {
    "Static-W": ("black", (0, (8, 3)), 1.6),
    "Static-Wt": ("#555555", (0, (3, 2)), 1.3),
    "HRW": ("#999999", (0, (8, 2, 1, 2)), 1.3),
    "Dynamic-R": ("#333333", (0, (6, 2, 1, 2, 1, 2)), 1.3),
    "Bounded-Loads": ("#888888", (0, (1, 2)), 1.6),
    "CH-BL": ("#444444", (0, (4, 2)), 1.3),
    "ACH": ("black", (0, ()), 2.8),
}
WARMUP = 40


def style():
    plt.rcParams.update(
        {
            "font.family": "serif",
            "font.serif": ["Liberation Serif", "DejaVu Serif"],
            "font.size": 15,
            "mathtext.fontset": "stix",
            "axes.linewidth": 1.0,
            "hatch.linewidth": 1.2,
        }
    )


def ru(x, nd):
    return f"{x:.{nd}f}".replace(".", ",")


def comma_axis(ax, nd):
    ax.yaxis.set_major_formatter(matplotlib.ticker.FuncFormatter(lambda v, _: ru(v, nd)))


def series_bars(res, s, out):
    A = res[s]["algorithms"]
    fig, axs = plt.subplots(2, 1, figsize=(11.7, 13.5))
    for ax, m, nd, ylab in (
        (axs[0], "D_mean", 4, r"Средний дисбаланс $\bar{D}$"),
        (
            axs[1],
            "M_cum",
            3,
            r"Накопленная стоимость перестройки $M_{\mathrm{keys}}^{\mathrm{cum}}$",
        ),
    ):
        x = np.arange(len(ORDER))
        top = 0
        for i, a in enumerate(ORDER):
            v = A[a][f"{m}_mean"]
            lo = A[a].get(f"{m}_boot_lo", v)
            hi = A[a].get(f"{m}_boot_hi", v)
            fc, h = BAR[a]
            ax.bar(i, v, 0.7, color=fc, hatch=h, edgecolor="black", linewidth=1.4, zorder=2)
            ax.errorbar(
                i,
                v,
                yerr=[[max(0, v - lo)], [max(0, hi - v)]],
                fmt="none",
                ecolor="black",
                capsize=6,
                elinewidth=1.4,
                zorder=3,
            )
            top = max(top, hi)
        for i, a in enumerate(ORDER):
            v = A[a][f"{m}_mean"]
            hi = A[a].get(f"{m}_boot_hi", v)
            ax.text(i, hi + top * 0.03, ru(v, nd), ha="center", va="bottom", fontsize=14)
        ax.set_ylim(0, top * 1.15)
        ax.set_xticks(x)
        ax.set_xticklabels([LAB[a] for a in ORDER], rotation=30, ha="right")
        ax.set_ylabel(ylab)
        ax.grid(axis="y", color="#d0d0d0", zorder=0)
        for sp in ("top", "right"):
            ax.spines[sp].set_visible(False)
        comma_axis(ax, 2 if m == "D_mean" else 0)
    fig.tight_layout(h_pad=3)
    fig.savefig(out, dpi=150)
    plt.close(fig)


def load_runs(d):
    return [json.load(open(f)) for f in sorted(glob.glob(os.path.join(d, "run_*.json")))]


def series_traces(runs, out):
    fig, axs = plt.subplots(2, 1, figsize=(10.7, 13.3))
    T = len(runs[0]["algorithms"]["ACH"]["D_trace"])
    t = np.arange(WARMUP, T)
    for a in ORDER:
        D = np.array([r["algorithms"][a]["D_trace"][WARMUP:] for r in runs])
        M = np.cumsum(np.array([r["algorithms"][a]["M_trace"][WARMUP:] for r in runs]), axis=1)
        c, ls, lw = LINE[a]
        for ax, X in ((axs[0], D), (axs[1], M)):
            med = np.median(X, 0)
            q1, q3 = np.percentile(X, [25, 75], axis=0)
            if ax is axs[1] and med.max() <= 0:
                continue
            ax.fill_between(t, q1, q3, color="#cccccc", alpha=0.35, lw=0)
            ax.plot(t, med, color=c, linestyle=ls, lw=lw, label=LAB[a])
    axs[0].set_ylim(bottom=0)
    comma_axis(axs[0], 2)
    axs[0].set_ylabel(r"Дисбаланс нагрузки $D(t)$")
    axs[1].set_yscale("log")
    axs[1].set_ylim(1e-3, None)
    axs[1].set_ylabel(r"Накопленная стоимость $\sum M_{\mathrm{keys}}$")
    for ax in axs:
        ax.set_xlim(-50, T + 50)
        ax.set_xlabel(r"Шаг управления $t$")
        ax.grid(color="#e0e0e0")
    h, l = axs[0].get_legend_handles_labels()
    fig.legend(h, l, loc="upper center", ncol=3, frameon=False, fontsize=13)
    fig.tight_layout(rect=(0, 0, 1, 0.93), h_pad=3)
    fig.savefig(out, dpi=150)
    plt.close(fig)


def overview(res, out):
    ser = [
        ("C1", "С1"),
        ("C2", "С2"),
        ("C3", "С3"),
        ("C4a", "С4а"),
        ("C4b", "С4б"),
        ("TRACE", "трасса"),
        ("C4c", "С4в"),
    ]
    fig, ax = plt.subplots(figsize=(12.8, 5.9))
    w = 0.36
    for i, (s, lab) in enumerate(ser):
        d0 = res[s]["algorithms"]["Static-W"]["D_mean_mean"]
        d4 = res[s]["algorithms"]["ACH"]["D_mean_mean"]
        ax.bar(
            i - w / 2,
            d0,
            w,
            color="white",
            hatch="//",
            edgecolor="black",
            lw=1.2,
            label="статическое распределение" if i == 0 else None,
        )
        ax.bar(
            i + w / 2,
            d4,
            w,
            color="#595959",
            edgecolor="black",
            lw=1.2,
            label="разработанный метод" if i == 0 else None,
        )
        pct = (d0 - d4) / d0 * 100
        ax.text(i, max(d0, d4) + 0.012, ru(pct, 1) + " %", ha="center", va="bottom")
    ax.axvline(len(ser) - 1.5, color="black", ls="--", lw=1.2)
    ax.text(
        len(ser) - 1, 0.5, "за границей\nобласти\nприменимости", ha="center", va="top", fontsize=14
    )
    ax.set_xticks(range(len(ser)))
    ax.set_xticklabels([l for _, l in ser])
    ax.set_ylim(0, 0.56)
    comma_axis(ax, 1)
    ax.set_ylabel(r"Средний дисбаланс $\bar{D}$")
    for sp in ("top", "right"):
        ax.spines[sp].set_visible(False)
    ax.legend(loc="upper left", frameon=False)
    fig.tight_layout()
    fig.savefig(out, dpi=150)
    plt.close(fig)


def timeline(out):
    rows = [
        ("С1", [], "стационарная нагрузка, Λ = 1437,5 запроса/шаг"),
        (
            "С2",
            [200, 250, 350],
            "Λ: 1437,5 → 1750 (t = 200); деградация узлов 7, 8 до 40 % (t = 250); "
            "модуляция ±10 % (t ≥ 350)",
        ),
        (
            "С3",
            [(150, "−2 узла"), (300, "+3 узла")],
            "распределение Ципфа (s = 1,0); смена состава кластера",
        ),
        ("С4а", [], "шум σ$_ν$ = 0,02"),
        ("С4б", [], "шум σ$_ν$ = 0,05"),
        ("С4в", [], "шум σ$_ν$ = 0,10, запаздывание d = 2, пропуски 10 %"),
        ("трасса", [], "популярность ключей по суточному журналу просмотров Википедии"),
        ("С5", [], "сетка параметров: ε$_{on}$, κ, τ, $M_{max}$ (10 повторений на точку)"),
    ]
    fig, ax = plt.subplots(figsize=(16.1, 9.1))
    n = len(rows)
    for k, (lab, ev, txt) in enumerate(rows):
        y = n - 1 - k
        ax.add_patch(plt.Rectangle((0, y - 0.32), 2000, 0.64, fill=False, lw=1.2))
        ax.add_patch(plt.Rectangle((0, y - 0.32), 40, 0.64, color="#c0c0c0", lw=1.2, ec="black"))
        for e in ev:
            tt, nm = e if isinstance(e, tuple) else (e, None)
            ax.plot([tt, tt], [y - 0.32, y + 0.32], color="black", lw=3)
            if nm:
                ax.text(tt + 8, y, nm, va="center", fontsize=13)
        ax.text(560, y + 0.1, txt, va="center", fontsize=15)
    ax.set_yticks(range(n))
    ax.set_yticklabels([r[0] for r in rows][::-1], fontsize=18)
    ax.set_xlim(0, 2000)
    ax.set_ylim(-0.8, n - 0.3)
    ax.set_xticks([0, 40, 500, 1000, 1500, 2000])
    ax.set_xlabel(r"Шаг управления $t$")
    ax.text(-20, n - 0.15, "прогрев", fontsize=13)
    for sp in ("top", "right"):
        ax.spines[sp].set_visible(False)
    fig.tight_layout()
    fig.savefig(out, dpi=150)
    plt.close(fig)


def main():
    ap = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    ap.add_argument("--results-dir", default="results")
    ap.add_argument("--output-dir", default="plots/thesis")
    a = ap.parse_args()
    style()
    os.makedirs(a.output_dir, exist_ok=True)
    res = json.load(open(os.path.join(a.results_dir, "all_results.json")))
    for s in ("C1", "C3", "C4c"):
        series_bars(res, s, os.path.join(a.output_dir, f"fig_series_bars_{s}.png"))
        runs = load_runs(os.path.join(a.results_dir, s))
        if runs:
            series_traces(runs, os.path.join(a.output_dir, f"fig_traces_{s}.png"))
    overview(res, os.path.join(a.output_dir, "fig_overview.png"))
    timeline(os.path.join(a.output_dir, "fig_timeline.png"))
    print("saved to", a.output_dir)


if __name__ == "__main__":
    main()
