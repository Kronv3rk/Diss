"""Shared plotting style for the figure scripts.

Single source of truth for which algorithms are drawn, in what order, and in
what colour. Both ``scripts/plot_traces.py`` and ``scripts/plot_series_bars.py``
import from here so a new algorithm cannot end up on one figure but not the
other - the failure mode that silently dropped HRW and CH-BL from the trace
plots.

The palette is a validated categorical set: worst adjacent CVD separation is
dE 9.1 (OKLab x100, protan), above the 8.0 target, and worst adjacent
normal-vision separation is dE 19.6, above the 15 floor. Three of the hues sit
below 3:1 contrast on white, so every figure carries a second, non-colour
encoding as well - distinct dash patterns on the traces, hatch fills and direct
value labels on the bars. That also keeps the figures readable when the thesis
is printed in greyscale.
"""

from __future__ import annotations

# Canonical order, matching src.experiment._make_algorithms and the
# ALGO_ORDER used by scripts/analyze.py and scripts/make_tables.py.
ALGO_ORDER = [
    "Static-W",
    "Static-Wt",
    "HRW",
    "Dynamic-R",
    "Bounded-Loads",
    "CH-BL",
    "ACH",
]

# Colour is assigned by position in ALGO_ORDER and never cycled: an algorithm
# keeps its hue no matter which subset a given figure happens to draw.
ALGO_STYLES = {
    "Static-W":      {"color": "#2a78d6", "linestyle": (0, (9, 3)),
                      "linewidth": 1.4, "hatch": ""},
    "Static-Wt":     {"color": "#eb6834", "linestyle": (0, (6, 2)),
                      "linewidth": 1.4, "hatch": "//"},
    "HRW":           {"color": "#1baf7a", "linestyle": (0, (3, 1, 1, 1)),
                      "linewidth": 1.4, "hatch": "\\\\"},
    "Dynamic-R":     {"color": "#eda100", "linestyle": (0, (4, 1, 1, 1, 1, 1)),
                      "linewidth": 1.4, "hatch": "xx"},
    "Bounded-Loads": {"color": "#e87ba4", "linestyle": (0, (1, 1.4)),
                      "linewidth": 1.6, "hatch": ".."},
    "CH-BL":         {"color": "#008300", "linestyle": (0, (5, 1)),
                      "linewidth": 1.4, "hatch": "++"},
    "ACH":           {"color": "#4a3aa7", "linestyle": (0, ()),
                      "linewidth": 2.4, "hatch": ""},
}

_FALLBACK_STYLE = {"color": "#555555", "linestyle": (0, ()), "linewidth": 1.4, "hatch": ""}

# Labels. 'en' keeps the code-level algorithm names; 'ru' uses the A0-A4
# designations the thesis text and tables use.
LABELS_EN = {a: a for a in ALGO_ORDER}
LABELS_RU = {
    "Static-W":      "А0 статическое",
    "Static-Wt":     "А1 взвешенное",
    "HRW":           "HRW",
    "Dynamic-R":     "А2 динамическое",
    "Bounded-Loads": "А3 огранич. нагрузки",
    "CH-BL":         "CH-BL",
    "ACH":           "А4 разработанный",
}

SERIES_TITLES_EN = {
    "C1":    "Stationary load",
    "C2":    "Step + periodic + degradation",
    "C3":    "Churn + hot keys (Zipf)",
    "C4a":   "Noise sigma=0.02",
    "C4b":   "Noise sigma=0.05",
    "C4c":   "Strong noise + lag + missing",
    "TRACE": "Real-corpus popularity replay",
}
SERIES_TITLES_RU = {
    "C1":    "стационарная нагрузка",
    "C2":    "ступень + периодика + деградация",
    "C3":    "чурн + горячие ключи (Zipf)",
    "C4a":   "шум телеметрии σ=0,02",
    "C4b":   "шум телеметрии σ=0,05",
    "C4c":   "сильный шум + запаздывание + пропуски",
    "TRACE": "воспроизведение реальной популярности",
}

# Series carrying per-run traces; C5 is a parameter sweep with no D(t) traces.
SERIES = ["C1", "C2", "C3", "C4a", "C4b", "C4c", "TRACE"]

FONT_SIZE = 12


def style_for(algo: str) -> dict:
    """Line/patch style for one algorithm, falling back to a neutral grey."""
    return dict(ALGO_STYLES.get(algo, _FALLBACK_STYLE))


def line_style(algo: str) -> dict:
    """Style keywords accepted by ``Axes.plot`` (no hatch)."""
    s = style_for(algo)
    s.pop("hatch", None)
    return s


def labels(lang: str) -> dict:
    return LABELS_RU if lang == "ru" else LABELS_EN


def series_titles(lang: str) -> dict:
    return SERIES_TITLES_RU if lang == "ru" else SERIES_TITLES_EN


def present_algorithms(runs: list) -> list:
    """Algorithms present in ``runs``, in canonical order.

    Names not in ALGO_ORDER are appended rather than dropped, so a newly added
    algorithm shows up on the figure (with the fallback style) instead of
    disappearing without a word.
    """
    seen = set()
    for run in runs:
        seen.update(run.get("algorithms", {}).keys())
    known = [a for a in ALGO_ORDER if a in seen]
    extra = sorted(seen - set(ALGO_ORDER))
    return known + extra


def set_style(font_size: int = FONT_SIZE) -> None:
    """Times New Roman-style settings for thesis figures."""
    import matplotlib.pyplot as plt

    plt.rcParams.update({
        "font.family":     "serif",
        "font.serif":      ["Times New Roman", "DejaVu Serif"],
        "font.size":       font_size,
        "axes.labelsize":  font_size,
        "axes.titlesize":  font_size + 1,
        "legend.fontsize": font_size - 2,
        "xtick.labelsize": font_size - 1,
        "ytick.labelsize": font_size - 1,
        "axes.edgecolor":  "#666666",
        "axes.linewidth":  0.8,
        "grid.color":      "#b0b0b0",
        "figure.dpi":      150,
    })
