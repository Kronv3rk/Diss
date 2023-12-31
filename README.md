# Diss

Dissertation repository. The experimental code lives in **[`ach-experiment/`](ach-experiment/)** -
an Adaptive Consistent Hashing (ACH) hash-ring load-balancing simulation. See
[`ach-experiment/README.md`](ach-experiment/README.md) for setup, running, and reproduction,
and [`IMPROVEMENT_PLAN.md`](IMPROVEMENT_PLAN.md) for the quality roadmap.

```bash
cd ach-experiment
pip install -e ".[dev]"
pytest -q
make reproduce      # re-run all series, rebuild results, render tables
```
