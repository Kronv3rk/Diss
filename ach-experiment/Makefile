.PHONY: setup test lint format typecheck run reproduce tables corrections clean

SERIES := C1 C2 C3 C4a C4b C4c C-DZZ TRACE

setup:
	pip install -e ".[dev]"

test:
	pytest -q

lint:
	ruff check .

format:
	ruff format .

typecheck:
	mypy src || true

run:
	@for s in $(SERIES); do python scripts/run_series.py --series $$s --n-runs 30 --base-seed 42 --output-dir results/$$s; done
	python scripts/run_sensitivity.py --n-runs 10 --output-dir results/C5

reproduce: run
	python scripts/build_all_results.py
	python scripts/apply_corrections.py
	python scripts/make_tables.py

tables:
	python scripts/make_tables.py

corrections:
	python scripts/apply_corrections.py

clean:
	rm -rf .pytest_cache .coverage **/__pycache__
