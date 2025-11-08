import os
import math
import yaml
import pytest

# Mark this golden test as xfail until you fill the expected numbers in the YAML.
# Remove the xfail marker once aligned with the lender pack.
# pytestmark = pytest.mark.xfail(reason="Fill expected metrics in dutchbay_lendercase_2025Q4.yaml and remove xfail.", strict=False)

def load_yaml(path: str):
    with open(path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)

def test_lendercase_golden():
    # Paths
    yml = "inputs/scenarios/dutchbay_lendercase_2025Q4.yaml"
    data = load_yaml(yml)

    # Expected block in YAML
    exp = data.get("expected_metrics") or {}
    required = ["project_irr", "equity_irr", "min_dscr", "llcr", "plcr"]
    missing = [k for k in required if k not in exp]
    assert not missing, f"Add expected_metrics.{missing} to {yml}"

    # Import model (assumes these functions exist in your package)
    from dutchbay_v13.core import build_financial_model

    # Build with YAML params (strip expected_metrics before passing)
    params = {k:v for k,v in data.items() if k != "expected_metrics"}
    outputs = build_financial_model(params)

    # Compare with a small tolerance
    def close(a, b, tol=1e-6):
        return a is not None and b is not None and abs(float(a) - float(b)) <= tol

    assert close(outputs.get("project_irr"), exp["project_irr"]), f"project_irr mismatch: got {outputs.get('project_irr')}, want {exp['project_irr']}"
    assert close(outputs.get("equity_irr"), exp["equity_irr"]), f"equity_irr mismatch: got {outputs.get('equity_irr')}, want {exp['equity_irr']}"
    assert close(outputs.get("min_dscr"), exp["min_dscr"]), f"min_dscr mismatch: got {outputs.get('min_dscr')}, want {exp['min_dscr']}"
    assert close(outputs.get("llcr"), exp["llcr"]), f"llcr mismatch: got {outputs.get('llcr')}, want {exp['llcr']}"
    assert close(outputs.get("plcr"), exp["plcr"]), f"plcr mismatch: got {outputs.get('plcr')}, want {exp['plcr']}"
