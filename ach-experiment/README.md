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
pytest -q          # number of tests: see `pytest --collect-only -q | tail -1`
```

## Reproducibility
Results are deterministic: per run `seed = base_seed + run*1000`. Pin the exact environment with
`requirements-lock.txt` when reproducing the numbers used in the thesis.

## Real-trace replay (external validity)

Beyond synthetic Zipf, the loader can take an **empirical popularity distribution**. The `TRACE`
series uses `traces/wikipedia_en_20240115.csv`: page-view counts of English Wikipedia (desktop
`en` + mobile `en.m`) summed over one full day, 2024-01-15, from the 24 hourly Wikimedia pageview
dumps (<https://dumps.wikimedia.org/other/pageviews/>). The 50 000 most viewed titles (of 7.34 million;
49.6 % of the day's 291.9 million views) form the key universe (NK = 50 000); the most viewed key
(`Main_Page`) gets ≈ 3.5 % and the top-100 ≈ 12.5 % of requests. Requests are sampled independently
from this distribution on every step; the temporal order of the log is not replayed. SHA-256 sums of
the 24 source dumps are in `traces/wikipedia_en_20240115.csv.sha256`. Rebuild the file with

```bash
python scripts/fetch_real_trace.py wikipedia-hourly --date 2024-01-15 --top 60000 \
    --out traces/wikipedia_en_20240115.csv
```

`traces/sample_real.csv` (identifier frequencies of a Python source-code corpus; used by the unit
tests of the trace loader only) is the trace of earlier versions of the `TRACE` series.

Run the series:

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
