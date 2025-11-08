# Contributing

## Ground rules
- All changes via Pull Request (PR). No direct pushes to `main`.
- CI must be green. Required check: **gate**.
- Economic-impacting changes must reference the term sheet / SPPA / credit paper.
- Golden tests must be updated (or justified) when lender-aligned numbers change.
- No commented-out hacks; no magic constants without explanation.

## Local setup
```bash
python -m venv .venv
source .venv/bin/activate  # .venv\Scripts\activate on Windows
pip install -e .[dev]
pre-commit install
pre-commit run --all-files
pytest
```

## Golden lender case
- Edit `inputs/scenarios/dutchbay_lendercase_2025Q4.yaml` to match the official pack.
- Fill `expected_metrics` values and remove the `xfail` mark in `tests/test_regression_golden.py`.
- In your PR description, reference the document name and date that these numbers align to.

## Release
- Tag `v1.0.0` once CI passes and the lender case is aligned.
- Subsequent tags follow semver (`v1.0.1`, `v1.1.0`, ...).
