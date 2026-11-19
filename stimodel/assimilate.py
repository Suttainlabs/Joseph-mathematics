"""Data assimilation: estimate the contact rate year by year.

The annual reported rate of year t is treated as the model's instantaneous
reporting rate at the middle of year t. For each one-year interval between
mid-years, the contact rate beta is the value that carries the model from the
state it had reached to the next year's reported rate. The result is a time
series of beta for each state: the model's reading of how transmission
changed. Forecasting then means forecasting beta (learn.py) and running the
model forward.

Matching mid-year points, not whole-year integrals, is deliberate. Solving
for a piecewise-constant beta that reproduces each year's integral is an
unstable inversion: the estimates alternate high and low with growing
amplitude. Point matching does not have that problem.

If a reported rate falls faster than the model can follow even with no new
infections, beta is set to its floor and that year is flagged as not matched.
"""
from __future__ import annotations

from dataclasses import dataclass

import numpy as np
from scipy.optimize import brentq

from .fde import FracStepper
from .models import MODELS

STEPS_PER_YEAR = 50
H = 1.0 / STEPS_PER_YEAR
BURN_IN_YEARS = 3
MAX_FORECAST_YEARS = 6


BETA_FLOOR = 1e-4


def _run_year(stepper, model, beta, tau):
    """Advance one year; return the reporting rate at the end of it."""
    with np.errstate(all="ignore"):
        states = stepper.advance(STEPS_PER_YEAR, lambda y: model.rhs(y, beta, tau))
    return float(model.reported(states[-1], tau))


def _solve_beta(stepper, model, target, tau, guess):
    """Contact rate that brings the reporting rate to `target` one year on.
    Returns (beta, matched)."""
    n0 = stepper.n

    def gap(logb):
        stepper.rewind(n0)
        rate = _run_year(stepper, model, np.exp(logb), tau)
        return (rate if np.isfinite(rate) else 1e9) - target

    lo, hi = np.log(guess) - 0.5, np.log(guess) + 0.5
    glo, ghi = gap(lo), gap(hi)
    while ghi <= 0 and hi < np.log(1e4):
        hi += 1.0; ghi = gap(hi)
    while glo >= 0 and lo > np.log(BETA_FLOOR):
        lo = max(lo - 1.5, np.log(BETA_FLOOR)); glo = gap(lo)
    if glo >= 0 or ghi <= 0:                          # target is out of the model's reach
        logb, matched = (lo if glo >= 0 else hi), False
    else:
        logb, matched = brentq(gap, lo, hi, xtol=1e-7, rtol=1e-9), True
    stepper.rewind(n0)
    _run_year(stepper, model, np.exp(logb), tau)
    return float(np.exp(logb)), matched


@dataclass
class Track:
    disease: str
    alpha: float
    years: np.ndarray            # observation years
    rates: np.ndarray            # reported cases per person per year
    beta: np.ndarray             # contact rate over the year leading up to each mid-year
    beta_star: np.ndarray        # contact rate that would have held each year's rate level
    matched: np.ndarray          # False where the model could not reach the reported rate
    stepper: FracStepper
    year_end: np.ndarray         # stepper index at each mid-year

    def forecast(self, origin_idx, betas, tau_mult=1.0):
        """Run forward from year `origin_idx` with the given contact rates
        (one per future year). Returns the reporting rate for each year."""
        model = MODELS[self.disease]
        s = self.stepper.copy_until(int(self.year_end[origin_idx]))
        out = []
        for b in betas:
            out.append(_run_year(s, model, b, model.tau * tau_mult))
        return np.array(out)

    def start_forecast(self, origin_idx):
        """A stepper positioned at year `origin_idx`, for step-by-step forecasting."""
        return self.stepper.copy_until(int(self.year_end[origin_idx]))


def stationary_beta(stepper, disease, rate, guess):
    """Contact rate that would keep the reporting rate at `rate` for the
    coming year. Leaves the stepper where it was."""
    model = MODELS[disease]
    n0 = stepper.n
    b, _ = _solve_beta(stepper, model, rate, model.tau, guess)
    stepper.rewind(n0)
    return b


def step_year(stepper, disease, beta, tau_mult=1.0):
    """Advance a forecast stepper one year; returns the reporting rate."""
    model = MODELS[disease]
    return _run_year(stepper, model, beta, model.tau * tau_mult)


def assimilate(disease, years, rates, alpha=1.0) -> Track:
    model = MODELS[disease]
    tau = model.tau
    rates = np.maximum(np.asarray(rates, dtype=float), 1e-8)
    n_years = len(years)
    total = (BURN_IN_YEARS + n_years + MAX_FORECAST_YEARS) * STEPS_PER_YEAR
    s = FracStepper(model.start(rates[0], tau), H, alpha, total)
    guess = tau + model.mu                            # contact rate at the epidemic threshold
    for _ in range(BURN_IN_YEARS):                    # settle on the first observed rate
        guess, _ = _solve_beta(s, model, rates[0], tau, guess)
    beta, ends, matched = [guess], [s.n], [True]
    star = [stationary_beta(s, disease, rates[0], guess)]
    for r in rates[1:]:
        guess, ok = _solve_beta(s, model, r, tau, max(guess, 10 * BETA_FLOOR))
        beta.append(guess); ends.append(s.n); matched.append(ok)
        star.append(stationary_beta(s, disease, r, max(guess, 10 * BETA_FLOOR)))
    return Track(disease, alpha, np.asarray(years), rates, np.array(beta), np.array(star),
                 np.array(matched), s, np.array(ends))
