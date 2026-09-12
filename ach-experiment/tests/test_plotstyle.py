"""The figure scripts must cover every algorithm the experiment actually runs.

HRW and CH-BL were once missing from the trace plots' hardcoded algorithm list,
so those two were silently absent from the figures while the tables reported
all seven. These tests pin the shared style table to the experiment itself.
"""
import os

import yaml

from src import plotstyle
from src.experiment import run_experiment


def _cfg(T=40):
    root = os.path.join(os.path.dirname(__file__), "..")
    with open(os.path.join(root, "configs", "base.yaml")) as f:
        cfg = yaml.safe_load(f)
    cfg["T"] = T
    cfg["load"] = {"type": "constant", "lambda": 1437.5}
    return cfg


def test_plotstyle_covers_every_algorithm():
    produced = set(run_experiment(_cfg(), seed=7))
    assert produced == set(plotstyle.ALGO_ORDER), (
        "src/plotstyle.ALGO_ORDER is out of sync with src.experiment: "
        f"missing {sorted(produced - set(plotstyle.ALGO_ORDER))}, "
        f"stale {sorted(set(plotstyle.ALGO_ORDER) - produced)}"
    )


def test_every_algorithm_has_a_distinct_style():
    colors = [plotstyle.ALGO_STYLES[a]["color"] for a in plotstyle.ALGO_ORDER]
    dashes = [plotstyle.ALGO_STYLES[a]["linestyle"] for a in plotstyle.ALGO_ORDER]
    assert len(set(colors)) == len(colors), "duplicate colours in ALGO_STYLES"
    assert len(set(dashes)) == len(dashes), "duplicate dash patterns in ALGO_STYLES"


def test_analysis_scripts_share_the_same_order():
    """analyze.py and make_tables.py keep their own copy of the order."""
    import importlib.util

    root = os.path.join(os.path.dirname(__file__), "..", "scripts")
    for script in ("analyze.py", "make_tables.py"):
        spec = importlib.util.spec_from_file_location(
            f"_probe_{script[:-3]}", os.path.join(root, script)
        )
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        assert mod.ALGO_ORDER == plotstyle.ALGO_ORDER, f"{script} disagrees on ALGO_ORDER"


def test_present_algorithms_keeps_canonical_order_and_unknowns():
    runs = [{"algorithms": {"ACH": {}, "Static-W": {}, "Newcomer": {}}}]
    assert plotstyle.present_algorithms(runs) == ["Static-W", "ACH", "Newcomer"]
