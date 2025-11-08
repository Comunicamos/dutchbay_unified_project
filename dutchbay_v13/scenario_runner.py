from __future__ import annotations
from typing import Dict, Any, List
from pathlib import Path
import datetime as dt
import json
import pandas as pd
import yaml

from .core import build_financial_model
from .types import Params
from .schema import SCHEMA, COMPOSITE_CONSTRAINTS, DEBT_SCHEMA

def _stamp() -> str:
    return dt.datetime.utcnow().strftime("%Y%m%d-%H%M%S")

# ---------------- Validation ----------------

def _validate_params_dict(d: Dict[str, Any], *, where: str = "params") -> Dict[str, Any]:
    """Validate scenario params against SCHEMA and Params defaults; raise friendly errors.
    """
    allowed_defaults = Params().__dict__
    out: Dict[str, Any] = {}
    errors = []
    for k, v in (d or {}).items():
        if k not in allowed_defaults:
            errors.append(f"[{where}] Unknown parameter '{k}'. See docs/schema.md for allowed keys.")
            continue
        meta = SCHEMA.get(k)
        default_val = allowed_defaults[k]
        # type coercion
        if isinstance(default_val, (int, float)):
            try:
                out[k] = float(v)
            except Exception:
                errors.append(f"[{where}.{k}] Expected number, got {type(v).__name__}: {v!r}")
                continue
        elif isinstance(default_val, bool):
            if isinstance(v, bool):
                out[k] = v
            elif isinstance(v, str) and v.lower() in {"true","false"}:
                out[k] = (v.lower() == "true")
            else:
                errors.append(f"[{where}.{k}] Expected boolean (true/false), got {v!r}")
                continue
        else:
            out[k] = v
        # range checks if schema available
        if meta and isinstance(out.get(k, None), (int, float)):
            lo, hi = float(meta["min"]), float(meta["max"])
            val = float(out[k])
            if not (lo <= val <= hi):
                errors.append(f"[{where}.{k}] {val} outside allowed range [{lo}, {hi}].")
    if errors:
        raise ValueError("Scenario validation failed:\n - " + "\n - ".join(errors))
    # composite constraints
    p_all = {**allowed_defaults, **out}
    c_errors = []
    for c in COMPOSITE_CONSTRAINTS:
        try:
            ok = c["check"](p_all)
        except Exception as e:
            ok = False
        if not ok:
            c_errors.append(c["message"])
    if c_errors:
        raise ValueError("Scenario validation failed:\n - " + "\n - ".join(c_errors))
    return out

def _load_yaml(path: Path) -> Dict[str, Any]:
    data = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    if not isinstance(data, dict):
        raise ValueError(f"Scenario YAML must be a mapping at {path}")
    return data

def _merge(base: Dict[str, Any], override: Dict[str, Any]) -> Dict[str, Any]:

def _validate_debt_dict(d: Dict[str, Any], *, where: str = "debt") -> Dict[str, Any]:
    out, errors = {}, []
    for k, v in (d or {}).items():
        meta = DEBT_SCHEMA.get(k)
        if not meta:
            errors.append(f"[{where}] Unknown debt field '{k}'. See docs/schema.md.")
            continue
        ty = meta["type"]
        if ty in ("float", "int"):
            try:
                val = float(v)
            except Exception:
                errors.append(f"[{where}.{k}] Expected number, got {type(v).__name__}: {v!r}")
                continue
            lo, hi = float(meta["min"]), float(meta["max"])
            if not (lo <= val <= hi):
                errors.append(f"[{where}.{k}] {val} outside allowed range [{lo}, {hi}].")
            if ty == "int":
                val = int(round(val))
            out[k] = val
        else:
            out[k] = v
    if errors:
        raise ValueError("Debt validation failed:\n - " + "\n - ".join(errors))
    return out

    out = dict(base)
    out.update(override or {})
    return out

# ---------------- Runners ----------------

def run_scenario(name: str, params: Dict[str, Any], outdir: Path | None = None, save_annual: bool = False) -> Dict[str, Any]:
    p = _validate_params_dict(params, where=f"scenario:{name}")
    debt_params = _validate_debt_dict(params.get('debt', {}), where=f"scenario:{name}.debt") if isinstance(params, dict) else {}
    if 'debt' in params:
        p['debt'] = debt_params
    res = build_financial_model(p)
    row = {
        "scenario": name,
        "equity_irr": res["equity_irr"],
        "project_irr": res["project_irr"],
        "npv_12pct": res["npv_12pct"],
        "min_dscr": res["min_dscr"],
        "avg_dscr": res["avg_dscr"],
        "year1_dscr": res["year1_dscr"],
    }
    if outdir:
        outdir.mkdir(parents=True, exist_ok=True)
        ts = _stamp()
        if save_annual:
            res["annual_data"].to_csv(outdir / f"{name}_annual_{ts}.csv", index=False)
        with open(outdir / f"{name}_summary_{ts}.json", "w") as f:
            json.dump(row, f, indent=2)
    return row

def _write_jsonl(rows: List[Dict[str, Any]], path: Path) -> None:
    with open(path, "w", encoding="utf-8") as f:
        for r in rows:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")  # one JSON object per line

def run_dir(scen_dir: str | Path, outdir: str | Path = "outputs", output_format: str = "both", save_annual: bool = False) -> pd.DataFrame:
    scen_dir = Path(scen_dir)
    outdir = Path(outdir)
    base_params: Dict[str, Any] = {}
    rows: List[Dict[str, Any]] = []
    for path in sorted(scen_dir.glob("*.yaml")):
        override = _load_yaml(path)
        name = path.stem
        params = _merge(base_params, override)
        rows.append(run_scenario(name, params, outdir, save_annual))
    df = pd.DataFrame(rows)
    if not df.empty:
        ts = _stamp()
                if output_format in {"csv","both"}:
            df.to_csv(outdir / f"scenario_dir_results_{ts}.csv", index=False)
        if output_format in {"jsonl","both"}:
            _write_jsonl(rows, outdir / f"scenario_dir_results_{ts}.jsonl")
    return df

def run_matrix(matrix_yaml: str | Path, outdir: str | Path = "outputs", output_format: str = "both", save_annual: bool = False) -> pd.DataFrame:
    outdir = Path(outdir)
    data = yaml.safe_load(Path(matrix_yaml).read_text(encoding="utf-8")) or {}
    scenarios = data.get("scenarios", [])
    if not isinstance(scenarios, list):
        raise ValueError("matrix YAML must contain 'scenarios: [ ... ]'")
    rows: List[Dict[str, Any]] = []
    for i, sc in enumerate(scenarios):
        if not isinstance(sc, dict):
            raise ValueError(f"scenarios[{i}] must be a mapping with 'name' and 'params'")
        name = sc.get("name", f"scenario_{i+1}")
        params = sc.get("params", {})
        rows.append(run_scenario(name, params, outdir, save_annual))
    df = pd.DataFrame(rows)
    if not df.empty:
        ts = _stamp()
                if output_format in {"csv","both"}:
            df.to_csv(outdir / f"scenario_matrix_results_{ts}.csv", index=False)
        if output_format in {"jsonl","both"}:
            _write_jsonl(rows, outdir / f"scenario_matrix_results_{ts}.jsonl")
    return df