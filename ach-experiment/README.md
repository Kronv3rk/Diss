# ACH - Adaptive Consistent Hashing experiment

Discrete-time simulation that compares **5 load-distribution algorithms** on a hashing ring
under stationary, dynamic, churn and noisy-telemetry regimes. Produces the tables and figures
used in the dissertation (configs reference *Table 3.1 / Table 3.2*).

## Algorithms
`ACH` (proposed) vs baselines `Static-W`, `Static-Wt`, `Dynamic-R`, `Bounded-Loads`.
All five run on the **same** load sequence per seed for a fair comparison.

## Metrics
- **D** = load dispersion `max(ell) − mean(ell)` - lower is better (the headline metric).
- **M_cum** = cumulative key migration after warmup - lower is better (rebalancing cost).
- **pi_chg** = fraction of steps that moved any key.
- Significance: Wilcoxon signed-rank, ACH vs each baseline, with **Holm (FWER)** and
  **Benjamini–Hochberg (FDR)** correction across the family of tests.

## Experiment series
| Series | Scenario |
|---|---|
| C1 | Stationary load |
| C2 | Step + periodic modulation + node degradation |
| C3 | Node churn + hot keys (Zipf) |
| C4a/b/c | Noisy telemetry (σ=0.02 / 0.05 / strong+lag+missing) |
| C5 | Parameter sensitivity sweep (eps_on, kappa, tau, M_max) |
| TRACE | **Real measured popularity** replayed from a corpus trace (external validity) |

## Install
```bash
python -m venv .venv && . .venv/bin/activate     # Windows: .venv\Scripts\activate
pip install -e ".[dev]"                          # installs the package + dev tools
```
Installing as a package means `from src...` works without `PYTHONPATH` hacks.

## Run
```bash
python scripts/calibrate.py                                   # find Lambda for the target imbalance
python scripts/run_all.py --n-runs 30 --base-seed 42          # all series C1–C5
python scripts/run_sensitivity.py --n-runs 10 --output-dir results/C5
python scripts/build_all_results.py                           # aggregate -> results/all_results.json (+ Holm/BH)
python scripts/apply_corrections.py                           # (re)apply multiple-comparison correction
python scripts/make_tables.py                                 # results/tables.md (thesis-ready)
python scripts/plot_traces.py --series C1 --results-dir results/C1 --output-dir plots/C1
```
Or use the shortcuts in the `Makefile` (`make test`, `make lint`, `make reproduce`, `make tables`).

## Test
```bash
pytest -q          # 70 tests; coverage of src ≈ 78%
```

## Reproducibility
Results are deterministic: per run `seed = base_seed + run*1000`. Pin the exact environment with
`requirements-lock.txt` when reproducing the numbers used in the thesis.

## Real-trace replay (external validity)

Beyond synthetic Zipf, the loader replays a **real measured popularity distribution**. The shipped
sample `traces/sample_real.csv` is a real heavy-tailed token-frequency distribution (199k+ unique
keys, top-100 ≈ 38% of requests). Run it with the `TRACE` series:

```bash
python scripts/run_series.py --series TRACE --n-runs 30 --output-dir results/TRACE
```

Swap in a domain trace (Wikipedia/Twitter/SNIA) - fetch on a networked machine and point the config at it:

```bash
python scripts/fetch_real_trace.py wikipedia --days 7 --out traces/wikipedia_real.csv
# then in a config:  trace: traces/wikipedia_real.csv
```

## Layout
```
src/            simulation library (ring, cluster, experiment loop, metrics, telemetry, noise, corrections)
src/algorithms/ the 5 algorithms
scripts/        run / analyze / aggregate / plot / corrections / tables
configs/        base.yaml + per-series YAML (extends: base)
tests/          pytest suite
results/        all_results.json (tracked); per-run JSON is gitignored
```

## License
MIT - see `../LICENSE`.
