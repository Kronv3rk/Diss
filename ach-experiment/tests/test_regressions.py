"""Regression tests for simulator defects fixed in branch fix/sim-bugs.

1. Key hashes were drawn from the same RandomState stream as the token
   positions, so the first V keys sat exactly on the V token positions.
2. Removed nodes stayed eligible as receivers (ACH, Dynamic-R,
   Bounded-Loads, CH-BL) and were counted in D(t) and total_load.
3. All orphaned tokens of a removed node went to node 0 instead of the
   clockwise successor owner.
4. ACH "largest_first" always moves at least one token per source, so
   M_keys <= m(t) does not hold; the "fit" rule enforces it exactly.
5. ACH reset the hysteresis state of every node when a node was added.
6. NoiseModel kept an unclipped "last good" value for imputation.
"""
import os

import numpy as np
import yaml

from src.algorithms.ach import ACH
from src.algorithms.bounded_loads import BoundedLoads
from src.algorithms.ch_bounded import CHBoundedLoads
from src.algorithms.dynamic_r import DynamicR
from src.experiment import key_hash_seed, run_experiment
from src.invariants import check_all
from src.load_generator import LoadGenerator
from src.noise_model import NoiseModel
from src.ring import HashRing

BASE_PARAMS = {
    "ell_star": 0.65, "eps_on": 0.10, "eps_off": 0.04, "tau": 0.85,
    "tau_min": 0.50, "kappa": 0.10, "M_max": 0.02, "M_H": 0.25, "H": 100,
    "v_min": 3,
}


def _base_cfg(T=120):
    root = os.path.join(os.path.dirname(__file__), "..")
    with open(os.path.join(root, "configs", "base.yaml")) as f:
        cfg = yaml.safe_load(f)
    cfg["T"] = T
    cfg["load"] = {"type": "constant", "lambda": 1437.5}
    return cfg


# 1 -------------------------------------------------------------------------
def test_key_hashes_independent_of_token_positions():
    for seed in (42, 1042, 29042):
        ring = HashRing(V=1000, n_nodes=10, seed=seed)
        gen = LoadGenerator(NK=50_000, zipf_s=1.0, seed=key_hash_seed(seed))
        hot = gen._key_hashes[:1000]
        assert not np.any(np.isin(hot, ring.pos)), seed
        # hot keys are no longer spread exactly one per token
        tokens = np.searchsorted(ring.pos, hot, side="left") % ring.V
        assert len(np.unique(tokens)) < 1000


# 3 -------------------------------------------------------------------------
def test_remove_node_hands_tokens_to_clockwise_successor():
    ring = HashRing(V=1000, n_nodes=10, seed=42)
    before = ring.a.copy()
    moved = ring.remove_node(9)
    assert 9 in ring.dead
    assert not np.any(ring.a == 9)
    for s in moved:
        succ = before[(s + 1) % ring.V]
        assert ring.a[s] == succ or before[(s + 1) % ring.V] == 9
    # orphans are spread over several owners, not dumped on node 0
    assert len(np.unique(ring.a[moved])) > 1


def test_remove_two_adjacent_owners_skips_dead():
    ring = HashRing(V=1000, n_nodes=10, seed=42)
    ring.remove_node(9)
    ring.remove_node(8)
    assert not np.any(np.isin(ring.a, [8, 9]))
    assert check_all(ring, 10, v_min=3, dead_nodes={8, 9}) == []


def test_check_all_flags_token_on_removed_node():
    ring = HashRing(V=1000, n_nodes=10, seed=42)
    ring.remove_node(9)
    ring.a[0] = 9
    viols = check_all(ring, 10, v_min=3, dead_nodes={9})
    assert any(v.startswith("Inv3") for v in viols)


# 2 -------------------------------------------------------------------------
def _dead_node_setup():
    ring = HashRing(V=1000, n_nodes=10, seed=42)
    ring.remove_node(9)
    ell = np.full(10, 0.65)
    ell[0] = 0.95          # overloaded live node
    ell[1] = 0.40          # underloaded live node
    ell[9] = 0.0           # removed node: no tokens, zero load
    return ring, ell


def test_ach_never_gives_tokens_to_removed_node():
    ring, ell = _dead_node_setup()
    ach = ACH(dict(BASE_PARAMS))
    for t in range(50):
        ach.step(ring, ell, total_load=0.6, t=t)
        assert not np.any(ring.a == 9)
    assert ach.sigma[9] == 0


def test_baselines_never_give_tokens_to_removed_node():
    for algo in (DynamicR(ell_star=0.65, threshold=0.03, rate=0.05, v_min=3),
                 BoundedLoads(ell_star=0.65, upper=0.12, lower=0.05,
                              max_tokens=2, v_min=3),
                 CHBoundedLoads(epsilon=0.25, v_min=3)):
        ring, ell = _dead_node_setup()
        for t in range(20):
            algo.step(ring, ell, total_load=0.6, t=t)
            assert not np.any(ring.a == 9), algo.name


def test_churn_run_has_no_tokens_on_removed_nodes():
    cfg = _base_cfg(T=120)
    cfg["zipf_s"] = 1.0
    cfg["churn"] = [
        {"t": 30, "events": [{"type": "remove", "node": 9},
                             {"type": "remove", "node": 8}]},
        {"t": 60, "events": [{"type": "add", "cap_class": 1},
                             {"type": "add", "cap_class": 0}]},
    ]
    res = run_experiment(cfg, seed=42)
    for name, r in res.items():
        assert r["violations"] == [], f"{name}: {r['violations'][:3]}"
        assert np.all(np.isfinite(r["D_trace"]))


# 4 -------------------------------------------------------------------------
def _random_steps(ach, n=200, seed=7):
    rng = np.random.RandomState(seed)
    ring = HashRing(V=1000, n_nodes=10, seed=0)
    out = []
    for t in range(n):
        ell = rng.uniform(0.3, 0.95, 10)
        total_load = float(0.5 * ell.mean() + 0.5 * ell.max())
        C = ach._compute_C(total_load, ell)
        m_expected = min(ach.M_max, ach.M_H / ach.H) * C
        M = ach.step(ring, ell, total_load, t)
        out.append((M, m_expected))
    return out


def test_fit_selection_respects_budget_exactly():
    ach = ACH({**BASE_PARAMS, "token_selection": "fit"})
    for M, m in _random_steps(ach):
        assert M <= m + 1e-9


def test_largest_first_overshoots_budget():
    # documents the legacy behaviour: with V=1000 the first token of a
    # source is longer than m(t) <= M_H/H, so M_keys > m(t) when it moves
    ach = ACH({**BASE_PARAMS, "token_selection": "largest_first"})
    moved = [(M, m) for M, m in _random_steps(ach) if M > 0]
    assert moved and any(M > m + 1e-9 for M, m in moved)


def test_unknown_token_selection_rejected():
    import pytest
    with pytest.raises(ValueError):
        ACH({**BASE_PARAMS, "token_selection": "smallest"})


# 5 -------------------------------------------------------------------------
def test_hysteresis_state_kept_when_node_added():
    ach = ACH(dict(BASE_PARAMS))
    ring = HashRing(V=1000, n_nodes=10, seed=42)
    ell = np.full(10, 0.65)
    ell[0] = 0.80                       # triggers overload on node 0
    ach.step(ring, ell, 0.6, 0)
    assert ach.sigma[0] == 1
    ring.n_nodes = 11
    ell11 = np.append(np.full(10, 0.65), 0.65)
    ell11[0] = 0.72                     # inside (eps_off, eps_on): keeps +1
    ach.step(ring, ell11, 0.6, 1)
    assert len(ach.sigma) == 11
    assert ach.sigma[0] == 1 and ach.sigma[10] == 0


# 6 -------------------------------------------------------------------------
def test_noise_model_imputes_clipped_values():
    nm = NoiseModel(sigma_noise=0.5, lag=0, p_miss=0.5, seed=0)
    raw = np.full((10, 3), 0.95)
    delta = np.full((10, 3), 0.5)       # pushes values above 1 before clipping
    nm.apply(raw, gauss_delta=delta, miss_mask=np.zeros((10, 3), bool))
    assert np.all(nm._last_good <= 1.0)
    out = nm.apply(raw, gauss_delta=np.zeros((10, 3)),
                   miss_mask=np.ones((10, 3), bool))
    assert np.all((out >= 0.0) & (out <= 1.0))
