"""Fractional Adams-Bashforth-Moulton predictor-corrector solver.

Solves the Caputo initial value problem

    D^alpha y(t) = f(t, y),   y(t0) = y0,   0 < alpha <= 1

with the scheme of Diethelm, Ford and Freed (2002), the same generalized
Adams-Bashforth-Moulton method used in Egbemhenghe et al. (2025),
doi:10.5281/zenodo.14716850. With alpha = 1 the scheme reduces to the
classical second-order Adams predictor-corrector, so the integer-order
model is solved by the same code path as the fractional one.
"""
from __future__ import annotations

from math import gamma

import numpy as np


def abm_weights(alpha: float, n_steps: int):
    """Convolution weights for the predictor (b) and corrector (c)."""
    k = np.arange(1, n_steps + 1, dtype=float)
    b = k ** alpha - (k - 1) ** alpha
    c = (k + 1) ** (alpha + 1) + (k - 1) ** (alpha + 1) - 2 * k ** (alpha + 1)
    return b, c


def solve_fde(f, y0, t0: float, t1: float, h: float, alpha: float = 1.0):
    """Integrate from t0 to t1 with step h. Returns (t, y) with y[i] = y(t[i])."""
    if not 0 < alpha <= 1:
        raise ValueError("alpha must be in (0, 1]")
    n_steps = int(round((t1 - t0) / h))
    t = t0 + h * np.arange(n_steps + 1)
    y0 = np.asarray(y0, dtype=float)
    y = np.empty((n_steps + 1, y0.size))
    F = np.empty_like(y)
    y[0] = y0
    F[0] = f(t[0], y0)
    b, c = abm_weights(alpha, n_steps)
    hp = h ** alpha / gamma(alpha + 1)
    hc = h ** alpha / gamma(alpha + 2)
    for n in range(n_steps):
        # predictor: sum_{j=0..n} b_{n+1-j} F_j
        yp = y0 + hp * (b[n::-1] @ F[: n + 1])
        # corrector: a_0 F_0 + sum_{j=1..n} c_{n+1-j} F_j + f(predictor)
        a0 = n ** (alpha + 1) - (n - alpha) * (n + 1) ** alpha
        hist = a0 * F[0]
        if n >= 1:
            hist = hist + c[n - 1::-1] @ F[1: n + 1]
        y[n + 1] = y0 + hc * (f(t[n + 1], yp) + hist)
        F[n + 1] = f(t[n + 1], y[n + 1])
    return t, y
