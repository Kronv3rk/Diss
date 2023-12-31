# CLAUDE.md - Diss / `ach-experiment`

Project guide for AI agents (and humans) working on this dissertation codebase.

## What this is

Research code for the dissertation **"Diss"**. The experiment compares **5 load-distribution
algorithms** on a hashing ring under different load / churn / noise regimes, and produces the
tables and figures used in the thesis (configs reference *Table 3.1 / Table 3.2*).

The proposed method is **ACH**; the others are baselines.

## Repository layout

```
Diss/
├── README.md
├── CLAUDE.md                ← this file
├── .claude/                 ← agents + project skills (see bottom)
└── ach-experiment/
    ├── requirements.txt     numpy, scipy, matplotlib, pandas, pyyaml, pytest
    ├── configs/             base.yaml + series_c1..c5 (+ c4a / c4b / c4c)
    ├── src/                 simulation library
    │   ├── ring.py  cluster.py  experiment.py  load_generator.py
    │   ├── telemetry.py  metrics.py  invariants.py  noise_model.py
    │   └── algorithms/  ach.py  bounded_loads.py  dynamic_r.py  static_w.py  static_weighted.py
    ├── scripts/             entry points (see "Run")
    ├── tests/               pytest suite (57 tests)
    └── results/             all_results.json (per-run JSON is gitignored)
```

## Algorithms

`ach` (proposed) vs baselines `bounded_loads`, `dynamic_r`, `static_w`, `static_weighted`.
All 5 are evaluated on the **same** load sequence per run for a fair comparison.

## Experiment series

| Series | Scenario |
|---|---|
| C1 | Stationary load |
| C2 | Step load + periodic modulation + node degradation |
| C3 | Node churn + hot keys (Zipf skew) |
| C4 | Noisy telemetry - C4a σ=0.02, C4b σ=0.05, C4c strong + lag + missing |
| C5 | Parameter sensitivity sweep (eps_on, kappa, tau, M_max) |

## Key metric & reproducibility

- **D = `metrics.compute_D(ell)`** - load dispersion / imbalance, **lower is better**.
- `analyze.py` reports **mean ± 95% CI** and **Wilcoxon signed-rank p-values** (ACH vs each baseline).
- Deterministic: per run `seed = base_seed + run * 1000`. Same seed ⇒ same result.
- Invariants are checked every step via `invariants.check_all`; violations are logged.

## Setup (the user's Windows machine)

```powershell
cd ach-experiment
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
```

## Run (from `ach-experiment/`)

```bash
python scripts/calibrate.py                                              # find Lambda for target imbalance
python scripts/run_all.py --n-runs 30 --base-seed 42                     # all series C1–C5
python scripts/run_series.py --series C1 --n-runs 30 --output-dir results/C1
python scripts/run_sensitivity.py --n-runs 10 --output-dir results/C5    # C5 sweep
python scripts/build_all_results.py                                      # aggregate → results/all_results.json
python scripts/analyze.py --series C1 --results-dir results/C1           # stats table
python scripts/plot_traces.py --series C1 --results-dir results/C1 --output-dir plots/C1  # SVG figures
```

Scripts self-insert the project dir on `sys.path`, so `from src...` works when invoked as
`python scripts/<x>.py` from `ach-experiment/`.

**Typical pipeline:** `calibrate` → `run_all` → `build_all_results` → `analyze` / `plot_traces`.

## Tests

```bash
cd ach-experiment
pytest -q          # 57 tests, ~0.2s   (needs PYTHONPATH=. or run from this dir)
```

### ⚠️ Cowork sandbox caveat
When run by the **Cowork agent**, the repo sits on a mount that **disallows file deletion**, which
breaks pytest's temp-dir cleanup (`RecursionError`). In Cowork, work on a scratch copy:

```bash
cp -r ach-experiment /tmp/ach && cd /tmp/ach && PYTHONPATH=/tmp/ach pytest -q
```

On the user's own Windows machine this is **not** needed - run `pytest` in place.

## Conventions

- Pure NumPy/SciPy; deterministic via seeds; no network access required.
- `results/run_*.json` are gitignored; only `results/all_results.json` is tracked - rebuild it with
  `build_all_results.py` (never hand-edit it).
- Keep `invariants.check_all` green; `tests/test_invariants.py` guards them.
- Don't break determinism (seed handling) when editing `experiment.py` / `load_generator.py`.

## Agents (`.claude/agents/`)

- **experiment-runner** - run series / sensitivity sweeps, manage YAML configs.
- **results-analyst** - aggregate runs, run statistics, generate figures & tables for the thesis.
- **test-guardian** - run pytest, guard invariants, diagnose failures.
- **sim-code-reviewer** - review changes to `src/` for correctness & determinism.
- **thesis-writer** - turn results into thesis prose / tables / figures (Word `.docx`).

## Skills

Curated project skills are in `.claude/skills/` (gitignored, local-only). The full assembled
toolkit (102 Agent Skills) lives in `../Diss-toolkit/` with `SKILLS_INDEX.md`.
