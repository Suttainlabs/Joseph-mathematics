"""Simulation, fitting and forecasting against annual case rates."""
from __future__ import annotations

from dataclasses import dataclass

import numpy as np
from scipy.optimize import least_squares

from .fde import solve_fde
from .models import MODELS, with_scenario

H = 0.02          # step, years; small enough for the stiffest rates at alpha = 0.6
ALPHA_MIN = 0.6
BURN_IN = 2       # years simulated before the first observation
PER_YEAR = int(round(1 / H))


def simulate(disease, beta, tau, i0, alpha, first_year, last_year,
             switch_year=None, contact_mult=1.0, treat_mult=1.0):
    """Annual diagnosed cases per person for first_year..last_year inclusive.

    If switch_year is given, the contact and treatment rates are multiplied
    by contact_mult and treat_mult from the start of that year onward.
    """
    cls = MODELS[disease]
    key = "beta1" if disease == "chlamydia" else "beta"
    base = cls(**{key: beta, "tau": tau})
    alt = with_scenario(base, contact_mult, treat_mult)
    t0 = first_year - BURN_IN

    def par(t):
        return alt if (switch_year is not None and t >= switch_year - 1e-9) else base

    with np.errstate(all="ignore"):
        t, y = solve_fde(lambda t, y: par(t).rhs(y), base.initial_state(i0),
                         t0, last_year + 1, H, alpha)
    if not np.all(np.isfinite(y)) or y.min() < -1e-6:
        return np.full(last_year - first_year + 1, np.nan)   # numerically unstable
    flux = np.array([par(ti).reported_flux(yi) for ti, yi in zip(t, y)])
    out = []
    for yr in range(first_year, last_year + 1):
        a = (yr - t0) * PER_YEAR
        seg = flux[a: a + PER_YEAR + 1]
        out.append(H * (seg[:-1] + seg[1:]).sum() / 2)   # trapezoid over the year
    return np.array(out)


@dataclass
class Fit:
    disease: str
    beta: float
    tau: float
    i0: float
    alpha: float
    first_year: int
    train_rmse_rel: float

    def predict(self, last_year, **scenario):
        return simulate(self.disease, self.beta, self.tau, self.i0, self.alpha,
                        self.first_year, last_year, **scenario)


BOUNDS = {
    "chlamydia":   ((0.2, 0.2, 1e-5), (60.0, 6.0, 0.05)),
    "ps_syphilis": ((0.5, 0.2, 1e-7), (80.0, 12.0, 0.01)),
}
STARTS = {
    "chlamydia":   [(3.0, 1.5, 0.003), (8.0, 4.0, 0.001)],
    "ps_syphilis": [(8.0, 4.0, 2e-5), (15.0, 8.0, 1e-5)],
}


def fit(disease, years, rates, fractional=False):
    """Least-squares fit of (beta, tau, i0), plus alpha when fractional.

    years: consecutive integer years; rates: cases per person per year.
    Residuals are relative errors, so large and small states are treated alike.
    """
    years = np.asarray(years)
    rates = np.asarray(rates, dtype=float)
    lo, hi = BOUNDS[disease]
    first, last = int(years[0]), int(years[-1])
    idx = years - first

    def resid(x):
        b, tau, i0 = np.exp(x[:3])
        alpha = x[3] if fractional else 1.0
        sim = simulate(disease, b, tau, i0, alpha, first, last)[idx]
        if not np.all(np.isfinite(sim)):
            return np.full(rates.size, 1e3)
        return (sim - rates) / rates

    best = None
    starts = [list(np.log(s)) for s in STARTS[disease]]
    if fractional:
        # warm start from the integer-order solution, so the fractional fit
        # can only match or improve on it in-sample
        base = fit(disease, years, rates, fractional=False)
        starts = [[np.log(base.beta), np.log(base.tau), np.log(base.i0)]]
    for s in starts:
        x0 = list(s) + ([0.97] if fractional else [])
        lb = list(np.log(lo)) + ([ALPHA_MIN] if fractional else [])
        ub = list(np.log(hi)) + ([1.0] if fractional else [])
        try:
            r = least_squares(resid, x0, bounds=(lb, ub), x_scale=1.0,
                              diff_step=1e-3, max_nfev=60)
        except Exception:
            continue
        if best is None or r.cost < best.cost:
            best = r
    b, tau, i0 = np.exp(best.x[:3])
    alpha = float(best.x[3]) if fractional else 1.0
    rmse = float(np.sqrt(np.mean(best.fun ** 2)))
    return Fit(disease, float(b), float(tau), float(i0), alpha, first, rmse)
