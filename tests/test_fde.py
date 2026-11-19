"""Checks of the solver against closed-form solutions."""
import numpy as np
from math import gamma

from stimodel.fde import solve_fde
from stimodel.models import ChlamydiaParams, SyphilisParams


def mittag_leffler(alpha, z, terms=80):
    return sum(z ** k / gamma(alpha * k + 1) for k in range(terms))


def test_integer_order_matches_exponential():
    t, y = solve_fde(lambda t, y: -y, [1.0], 0.0, 2.0, 0.01, 1.0)
    assert abs(y[-1, 0] - np.exp(-2.0)) < 1e-4


def test_fractional_matches_mittag_leffler():
    # D^alpha y = -y, y(0) = 1 has solution E_alpha(-t^alpha)
    for alpha in (0.6, 0.8, 0.95):
        t, y = solve_fde(lambda t, y: -y, [1.0], 0.0, 2.0, 0.005, alpha)
        exact = mittag_leffler(alpha, -(2.0 ** alpha))
        assert abs(y[-1, 0] - exact) < 2e-3, (alpha, y[-1, 0], exact)


def test_population_is_conserved():
    for p in (ChlamydiaParams(beta1=4.0, tau=2.0), SyphilisParams(beta=10.0, tau=5.0)):
        for alpha in (1.0, 0.8):
            t, y = solve_fde(lambda t, y: p.rhs(y), p.initial_state(1e-3), 0, 10, 0.05, alpha)
            assert np.allclose(y.sum(axis=1), 1.0, atol=1e-8)
            assert y.min() > -1e-9


def test_chlamydia_dies_out_below_threshold():
    p = ChlamydiaParams(beta1=1.0, tau=2.0)       # R0 about 0.5
    assert p.r0() < 1
    t, y = solve_fde(lambda t, y: p.rhs(y), p.initial_state(1e-3), 0, 30, 0.05, 1.0)
    assert y[-1, 3] < 1e-6
