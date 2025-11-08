from __future__ import annotations
from typing import List, Tuple
import math
from ..types import Params, DebtTerms, AnnualRow
from .debt import amortization_schedule
from .irr import irr, npv as npv_fn

def _fx_at(p: Params, year: int) -> float:
    return p.fx_initial * ((1.0 + p.fx_depr) ** (year - 1))

def _production_mwh(p: Params, year: int) -> float:
    cf_y = p.cf_p50 * ((1.0 - p.yearly_degradation) ** (year - 1))
    return p.nameplate_mw * p.hours_per_year * cf_y

def _opex_usd(p: Params, year: int, production_mwh: float, fx: float) -> float:
    usd_comp = p.opex_usd_mwh * p.opex_split_usd * ((1.0 + p.opex_esc_usd) ** (year - 1))
    lkr_comp_usd = (p.opex_usd_mwh * p.opex_split_lkr * ((1.0 + p.opex_esc_lkr) ** (year - 1))) / fx
    per_mwh_usd = usd_comp + lkr_comp_usd
    return per_mwh_usd * production_mwh

def _revenue_usd(p: Params, production_mwh: float, fx: float) -> float:
    kwh = production_mwh * 1000.0
    revenue_lkr = kwh * p.tariff_lkr_kwh
    return revenue_lkr / fx

def _sscl_usd(p: Params, revenue_usd: float) -> float:
    return p.sscl_rate * revenue_usd

def build(p: Params, d: DebtTerms) -> Tuple[List[AnnualRow], float, float, float, float, float]:
    years = p.project_life_years
    total_debt = p.total_capex * d.debt_ratio
    equity = p.total_capex - total_debt
    sched = amortization_schedule(total_debt, d, years)

    rows: List[AnnualRow] = []
    dscr_vals: List[float] = []
    proj_cfs: List[float] = [-p.total_capex]
    eq_cfs: List[float] = [-equity]

    for y in range(1, years + 1):
        fx = _fx_at(p, y)
        prod = _production_mwh(p, y)
        rev = _revenue_usd(p, prod, fx)
        opex = _opex_usd(p, y, prod, fx)
        sscl = _sscl_usd(p, rev)

        interest = sched[y-1].interest if y-1 < len(sched) else 0.0
        principal = sched[y-1].principal if y-1 < len(sched) else 0.0
        debt_service = interest + principal

        ebit = rev - opex - sscl
        ebt = ebit - interest
        tax_on_ebt = max(0.0, ebt) * p.tax_rate

        tax_on_ebit = max(0.0, ebit) * p.tax_rate
        cfads = ebit - tax_on_ebit

        equity_fcf = ebit - interest - principal - tax_on_ebt
        dscr = (cfads / debt_service) if debt_service > 1e-9 else None
        if dscr is not None:
            dscr_vals.append(dscr)

        rows.append(AnnualRow(
            year=y, fx_rate=fx, production_mwh=prod, revenue_usd=rev, opex_usd=opex,
            sscl_usd=sscl, ebit_usd=ebit, interest_usd=interest, principal_usd=principal,
            ebt_usd=ebt, tax_usd=tax_on_ebt, cfads_usd=cfads, equity_fcf_usd=equity_fcf,
            debt_service_usd=debt_service, dscr=dscr
        ))

        proj_cfs.append(ebit - tax_on_ebit - principal)
        eq_cfs.append(equity_fcf)

    eq_irr = irr(eq_cfs) or float("nan")
    proj_irr = irr(proj_cfs) or float("nan")
    npv_12 = npv_fn(p.discount_rate, proj_cfs)
    min_dscr = min(d for d in dscr_vals) if dscr_vals else float("inf")
    avg_dscr = sum(dscr_vals)/len(dscr_vals) if dscr_vals else float("inf")
    return rows, eq_irr, proj_irr, npv_12, min_dscr, avg_dscr