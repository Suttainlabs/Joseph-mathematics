"""Checks of the solver and models against known results."""
from math import gamma

import numpy as np

from stimodel.assimilate import assimilate
from stimodel.fde import FracStepper, solve_fde
from stimodel.models import MODELS


def mittag_leffler(alpha, z, terms=80):
    return sum(z ** k / gamma(alpha * k + 1) for k in range(terms))


def test_integer_order_matches_exponential():
    t, y = solve_fde(lambda t, y: -y, [1.0], 0.0, 2.0, 0.01, 1.0)
    assert abs(y[-1, 0] - np.exp(-2.0)) < 1e-4


def test_fractional_matches_mittag_leffler():
    for alpha in (0.6, 0.8, 0.95):
        t, y = solve_fde(lambda t, y: -y, [1.0], 0.0, 2.0, 0.005, alpha)
        assert abs(y[-1, 0] - mittag_leffler(alpha, -(2.0 ** alpha))) < 2e-3


def test_stepper_rewind_reproduces_the_same_path():
    f = lambda y: np.array([-0.7 * y[0]])
    s = FracStepper([1.0], 0.02, 0.8, 200)
    first = s.advance(100, f)[-1].copy()
    s.rewind(40)
    again = s.advance(60, f)[-1]
    assert np.allclose(first, again)
    c = s.copy_until(40)
    assert np.allclose(c.advance(60, f)[-1], first)


def test_population_is_conserved():
    for m, beta in ((MODELS["chlamydia"], 1.3), (MODELS["ps_syphilis"], 6.0)):
        for alpha in (1.0, 0.8):
            s = FracStepper(m.start(0.004 if m.tau == 1 else 1e-4, m.tau), 0.02, alpha, 500)
            y = s.advance(500, lambda y: m.rhs(y, beta, m.tau))
            assert np.allclose(y.sum(axis=1), 1.0, atol=1e-8)
            assert y.min() > -1e-9


def test_assimilation_reproduces_the_data():
    years = np.arange(2013, 2025)
    for disease, rates in (("chlamydia", np.linspace(0.0044, 0.0055, 12)),
                           ("ps_syphilis", np.geomspace(5e-5, 1.8e-4, 12))):
        for alpha in (1.0, 0.8):
            tr = assimilate(disease, years, rates, alpha)
            back = [tr.forecast(i - 1, [tr.beta[i]])[0] for i in range(1, 12)]
            assert np.allclose(back, rates[1:], rtol=1e-4)
            assert np.all(tr.beta > 0) and tr.matched.all()
            assert np.abs(np.diff(np.log(tr.beta))).max() < 0.5      # no sawtooth


def test_learner_declines_to_fit_on_too_little_history():
    from stimodel.learn import STATE_REGION, fit_model, predict_step
    states = sorted(STATE_REGION)[:10]
    rng = np.random.default_rng(0)
    logv = np.log(rng.uniform(1e-4, 5e-3, (10, 6)))
    cases = rng.uniform(50, 5000, (10, 6))
    target = np.full_like(logv, np.nan)
    target[:, :-1] = np.diff(logv, axis=1)
    assert fit_model(logv, cases, states, target, 3) is None        # 10 rows only
    assert np.all(predict_step(None, logv, cases, states) == 0)     # falls back to "no change"
    assert len(STATE_REGION) == 51
