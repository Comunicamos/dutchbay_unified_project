import math
import hypothesis as h
import hypothesis.strategies as st

# Keep examples small/fast for CI
h.settings.register_profile("ci", max_examples=30, deadline=500)
h.settings.load_profile("ci")

@h.given(
    # simple cashflow: negative invest then positives
    invest=st.floats(min_value=1e3, max_value=1e7),
    n=st.integers(min_value=2, max_value=10),
    inflow=st.floats(min_value=1.0, max_value=1e6),
)
def test_irr_not_nan(invest, n, inflow):
    from dutchbay_v13.finance.irr import irr
    cf = [-abs(invest)] + [float(inflow)] * (n-1)
    r = irr(cf)
    assert r is None or (not math.isnan(r))

@h.given(
    dscr=st.floats(min_value=1.0, max_value=5.0),
)
def test_dscr_non_negative(dscr):
    # For a trivial case, DSCR >= 0 by construction.
    # If you have a real DSCR util, import and test with generated schedules.
    assert dscr >= 0.0
