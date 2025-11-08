from __future__ import annotations
import argparse, os, json, datetime as dt
from .config import load_params
from .core import build_financial_model
from .monte_carlo import run_monte_carlo
from .sensitivity import run_sensitivity_analysis
from .optimization import optimize_capital_structure, optimize_debt_pareto, optimize_debt_pareto_yaml
from .charts import tornado_chart, dscr_series, equity_fcf_series
from .report import build_html_report
from .report_pdf import build_pdf_report
from .scenario_runner import run_dir as run_scen_dir, run_matrix as run_scen_matrix

def _stamp(): return dt.datetime.utcnow().strftime("%Y%m%d-%H%M%S")

def main():
    p = argparse.ArgumentParser(description="DutchBay V13 CLI")
    p.add_argument("mode", choices=["baseline","montecarlo","sensitivity","optimize","scenarios","report","api"])
    p.add_argument("--params", default="inputs/baseline.yaml")
    p.add_argument("--n", type=int, default=1000)
    p.add_argument("--tornado-metric", choices=["irr","npv","dscr"], default="irr")
    p.add_argument("--tornado-sort", choices=["abs","asc","desc"], default="abs")
    p.add_argument("--charts", action="store_true")
    p.add_argument("--outdir", default="outputs")
    p.add_argument("--save-annual", action="store_true")
    p.add_argument("--report", action="store_true")
    p.add_argument("--pdf", action="store_true")
    p.add_argument("--pareto", action="store_true")
    p.add_argument("--grid-dr", default="0.50:0.90:0.05")
    p.add_argument("--grid-tenor", default="8:20:1")
    p.add_argument("--grid-grace", default="0:3:1")
    p.add_argument("--grid-file", default="")
    p.add_argument("--format", choices=["csv","jsonl","both"], default="both")
    a = p.parse_args()
    os.makedirs(a.outdir, exist_ok=True)
    if a.mode == "baseline":
        params = load_params(a.params)
        res = build_financial_model(params)
        out = os.path.join(a.outdir, f"baseline_{_stamp()}.json")
        with open(out, "w") as f: json.dump(res, f, indent=2, default=str)
        print(out)
    elif a.mode == "montecarlo":
        df = run_monte_carlo(a.n)
        out = os.path.join(a.outdir, f"mc_{_stamp()}.csv")
        df.to_csv(out, index=False)
        print(out)
    elif a.mode == "sensitivity":
        run_sensitivity_analysis(a.outdir)
        print("sensitivity done")
    elif a.mode == "report":
        out = build_html_report(a.outdir)
        print(str(out))
        if a.pdf:
            print(str(build_pdf_report(a.outdir, out)))
    
if a.mode == "api":
        # Start FastAPI (requires extras: pip install .[web])
        run_api()
    
if a.mode == "optimize":
        if a.pareto:
            r = optimize_debt_pareto(a.grid_dr, a.grid_tenor, a.grid_grace, a.outdir)
            print(f"frontier points: {r.get('frontier_count')} (grid {r.get('grid_count')})")
        else:
            r = optimize_capital_structure()
            print(r.get("message","ok"))

if a.mode == "scenarios":
    # Prefer matrix if present, else directory
    matrix = Path("inputs/scenario_matrix.yaml")
    scen_dir = Path("inputs/scenarios")
    if matrix.exists():
        df = run_scen_matrix(str(matrix), a.outdir, a.format)
    else:
        df = run_scen_dir(str(scen_dir), a.outdir, a.format)
    out = Path(a.outdir) / f"scenarios_{_stamp()}.csv"
    df.to_csv(out, index=False)
    print(out)


if __name__ == "__main__":
    main()
from .api import run as run_api
