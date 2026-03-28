"""
Experiment runner for the ACH dissertation experiment.

Runs all five algorithms (A0–A4) on an identical load sequence and
returns per-algorithm traces and aggregate metrics.
"""

import copy
import numpy as np
from typing import Dict, Any

from .ring import HashRing
from .cluster import Cluster
from .load_generator import LoadGenerator
from .telemetry import Telemetry
from .noise_model import NoiseModel
from .metrics import compute_D, aggregate_metrics
from .invariants import check_all
from .algorithms.static_w import StaticW
from .algorithms.static_weighted import StaticWeighted
from .algorithms.dynamic_r import DynamicR
from .algorithms.bounded_loads import BoundedLoads
from .algorithms.ach import ACH


# Capacity class lookup for node churn events
CAP_CLASSES = [1.0, 0.55, 0.25]


def _build_algorithms(cfg: dict, ring_snapshot: HashRing) -> list:
    """Construct one instance of each algorithm.

    Parameters
    ----------
    cfg : dict
        Full experiment configuration.
    ring_snapshot : HashRing
        The initial ring (used to extract V and capacities for StaticWeighted).

    Returns
    -------
    list of algorithm objects
    """
    caps = np.array(cfg.get("capacities", [1.0]*10), dtype=np.float64)
    V    = int(cfg.get("V", 1000))
    ach_params = cfg.get("ach", {})

    algos = [
        StaticW(),
        StaticWeighted(caps, V),
        DynamicR(
            ell_star=float(ach_params.get("ell_star", 0.65)),
            threshold=0.03,
            rate=0.05,
        ),
        BoundedLoads(
            ell_star=float(ach_params.get("ell_star", 0.65)),
            upper=0.12,
            lower=0.05,
            max_tokens=2,
        ),
        ACH(ach_params),
    ]
    return algos


def _make_load_sequence(cfg: dict, rng: np.random.RandomState,
                        gen: LoadGenerator) -> list:
    """Pre-generate the full load sequence so all algorithms see the same data.

    Parameters
    ----------
    cfg : dict
        Experiment config, must contain 'load' and optionally 'T'.
    rng : np.random.RandomState
    gen : LoadGenerator

    Returns
    -------
    list of (key_hashes, write_flags) tuples, length T
    """
    T = int(cfg.get("T", 500))
    load_cfg = cfg.get("load", {})
    load_type = load_cfg.get("type", "constant")

    sequence = []
    for t in range(T):
        lam = _get_lambda(load_cfg, t, T)
        kh, wf = gen.generate(lam, rng)
        sequence.append((kh, wf))
    return sequence


def _get_lambda(load_cfg: dict, t: int, T: int) -> float:
    """Compute arrival rate lambda at time step t.

    Supports load types:
      constant       : fixed lambda
      step_periodic  : step-up at step_t, periodic modulation after periodic_t
    """
    load_type = load_cfg.get("type", "constant")

    if load_type == "constant":
        return float(load_cfg.get("lambda", 1800.0))

    elif load_type == "step_periodic":
        lam_low  = float(load_cfg.get("lambda_low",  1800.0))
        lam_high = float(load_cfg.get("lambda_high", 3200.0))
        step_t   = int(load_cfg.get("step_t", 200))
        per_t    = int(load_cfg.get("periodic_t", 350))
        period   = int(load_cfg.get("period", 50))
        amp      = float(load_cfg.get("amplitude", 0.25))

        lam = lam_low if t < step_t else lam_high
        if t >= per_t:
            lam = lam * (1.0 + amp * np.sin(2.0 * np.pi * (t - per_t) / period))
        return float(lam)

    else:
        raise ValueError(f"Unknown load type: {load_type!r}")


def run_experiment(cfg: dict, seed: int = 42) -> dict:
    """Run all 5 algorithms on the same load sequence.

    Parameters
    ----------
    cfg : dict
        Full experiment configuration (loaded from YAML).
    seed : int
        Random seed for this run.

    Returns
    -------
    dict with keys per algorithm name:
        {
          'D_trace'   : list of float (length T)
          'M_trace'   : list of float (length T)
          'ell_trace' : list of np.ndarray (T x n_nodes)
          'violations': list of str (invariant violations)
          'agg'       : dict of aggregate metrics
        }
    """
    rng = np.random.RandomState(seed)

    # --- Setup ---
    V       = int(cfg.get("V", 1000))
    n_nodes = int(cfg.get("n0", 10))
    T       = int(cfg.get("T", 500))
    NK      = int(cfg.get("NK", 50000))
    warmup  = int(cfg.get("warmup", 40))

    caps     = list(cfg.get("capacities", [1.0]*n_nodes))
    mu_base  = float(cfg.get("mu_base", 350.0))
    zipf_s   = float(cfg.get("zipf_s", 0.0))

    tel_params = cfg.get("telemetry", {})
    ach_params = cfg.get("ach", {})
    noise_cfg  = cfg.get("noise", {})
    degrade_cfg = cfg.get("degradation", {})
    churn_cfg  = cfg.get("churn", [])

    # --- Build shared infrastructure ---
    cluster = Cluster(capacities=caps, mu_base=mu_base)
    gen = LoadGenerator(NK=NK, zipf_s=zipf_s, seed=seed)
    noise = NoiseModel(
        sigma_noise=float(noise_cfg.get("sigma", 0.0)),
        lag=int(noise_cfg.get("lag", 0)),
        p_miss=float(noise_cfg.get("p_miss", 0.0)),
        seed=seed + 1,
    )

    # Pre-generate load sequence (all algorithms use the same)
    load_seq = _make_load_sequence(cfg, rng, gen)

    # --- Build one ring per algorithm (all identical at t=0) ---
    rings = [HashRing(V=V, n_nodes=n_nodes, seed=seed) for _ in range(5)]
    telemetries = [Telemetry(n_nodes, tel_params) for _ in range(5)]
    algos = _build_algorithms(cfg, rings[0])

    # Results containers
    results: Dict[str, Any] = {}
    for algo in algos:
        results[algo.name] = {
            "D_trace":    [],
            "M_trace":    [],
            "ell_trace":  [],
            "violations": [],
            "agg":        {},
        }

    # --- Main simulation loop ---
    for t in range(T):
        key_hashes, write_flags = load_seq[t]

        # Handle churn events
        for event_group in churn_cfg:
            if event_group.get("t") == t:
                for ev in event_group.get("events", []):
                    if ev["type"] == "remove":
                        node_id = ev["node"]
                        cluster.remove_node(node_id)
                        for ring in rings:
                            # Reassign orphaned tokens to node 0
                            orphaned = np.where(ring.a == node_id)[0]
                            if len(orphaned) > 0:
                                ring.reassign(orphaned,
                                              np.zeros(len(orphaned), dtype=np.int32))
                    elif ev["type"] == "add":
                        cap_class_idx = ev.get("cap_class", 0)
                        cap = CAP_CLASSES[cap_class_idx]
                        new_id = cluster.add_node(cap)
                        for ring in rings:
                            ring.n_nodes = cluster.n_nodes
                            ring.a = np.where(ring.a >= ring.n_nodes,
                                              ring.a % ring.n_nodes, ring.a)

        # Handle degradation events
        if degrade_cfg:
            t_start = int(degrade_cfg.get("t_start", T))
            if t == t_start:
                for node_str, factor in degrade_cfg.get("nodes", {}).items():
                    cluster.degrade_node(int(node_str), float(factor))

        # Generate telemetry from the first ring (A0) as ground truth
        # then apply noise model — all algorithms receive the same noisy obs
        raw_telem, _ = cluster.simulate_load(rings[0], key_hashes, write_flags)
        noisy_telem = noise.apply(raw_telem, rng)

        for algo_idx, (algo, ring, tel) in enumerate(
                zip(algos, rings, telemetries)):

            # Use noisy telemetry for this algorithm's ring (simulate routing
            # from the real ring state, not just ring[0])
            raw_i, _ = cluster.simulate_load(ring, key_hashes, write_flags)
            noisy_i = noise.apply(raw_i, rng) if algo_idx > 0 else noisy_telem

            tel.update(noisy_i)
            ell = tel.compute_ell()
            total_load = tel.compute_total_load(ell)

            prev = ring.snapshot()
            M_keys = algo.step(ring, ell, total_load, t)

            D = compute_D(ell)
            results[algo.name]["D_trace"].append(D)
            results[algo.name]["M_trace"].append(M_keys)
            results[algo.name]["ell_trace"].append(ell.copy())

            # Check invariants every step
            viols = check_all(ring, ring.n_nodes, v_min=int(ach_params.get("v_min", 3)))
            for v in viols:
                results[algo.name]["violations"].append(f"t={t}: {v}")

    # --- Compute aggregates ---
    for algo in algos:
        name = algo.name
        D_arr = np.array(results[name]["D_trace"])
        M_arr = np.array(results[name]["M_trace"])
        results[name]["agg"] = aggregate_metrics(D_arr, M_arr, warmup=warmup)
        # Convert ell_trace to numpy array for easier downstream use
        results[name]["ell_trace"] = np.array(results[name]["ell_trace"])

    return results
