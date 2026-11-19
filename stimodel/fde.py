"""Fractional Adams-Bashforth-Moulton predictor-corrector solver.

Solves the Caputo initial value problem

    D^alpha y(t) = f(t, y),   y(t0) = y0,   0 < alpha <= 1

with the scheme of Diethelm, Ford and Freed (2002). With alpha = 1 it reduces
to the classical second-order Adams predictor-corrector, so integer-order and
fractional-order models share one code path.

`FracStepper` is the resumable form used for data assimilation: it keeps the
whole history (a fractional derivative has memory), can be advanced a few
steps at a time with changing parameters, and can be rewound to an earlier
step so that a period can be re-simulated with a different parameter value.
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


class FracStepper:
    def __init__(self, y0, h: float, alpha: float, max_steps: int):
        if not 0 < alpha <= 1:
            raise ValueError("alpha must be in (0, 1]")
        self.h, self.alpha, self.max_steps = h, alpha, max_steps
        y0 = np.asarray(y0, dtype=float)
        self.y = np.empty((max_steps + 1, y0.size))
        self.F = np.empty_like(self.y)
        self.y[0] = y0
        self.n = 0                      # index of the latest computed state
        self._have_f0 = False
        self.b, self.c = abm_weights(alpha, max_steps)
        self.hp = h ** alpha / gamma(alpha + 1)
        self.hc = h ** alpha / gamma(alpha + 2)

    def copy_until(self, n: int) -> "FracStepper":
        """A new stepper holding the history up to step n."""
        s = FracStepper(self.y[0], self.h, self.alpha, self.max_steps)
        s.y[: n + 1] = self.y[: n + 1]
        s.F[: n + 1] = self.F[: n + 1]
        s.n, s._have_f0 = n, True
        return s

    def advance(self, k: int, f):
        """Take k steps with right-hand side f(y). Returns states n..n+k."""
        y, F, a = self.y, self.F, self.alpha
        if not self._have_f0:
            F[0] = f(y[0])
            self._have_f0 = True
        start = self.n
        if start + k > self.max_steps:
            raise ValueError("stepper history is full")
        for n in range(start, start + k):
            yp = y[0] + self.hp * (self.b[n::-1] @ F[: n + 1])
            hist = (n ** (a + 1) - (n - a) * (n + 1) ** a) * F[0]
            if n >= 1:
                hist = hist + self.c[n - 1::-1] @ F[1: n + 1]
            y[n + 1] = y[0] + self.hc * (f(yp) + hist)
            F[n + 1] = f(y[n + 1])
        self.n = start + k
        return y[start: self.n + 1]

    def rewind(self, n: int):
        self.n = n


def solve_fde(f, y0, t0: float, t1: float, h: float, alpha: float = 1.0):
    """Integrate an autonomous-or-not system from t0 to t1. Returns (t, y)."""
    n_steps = int(round((t1 - t0) / h))
    t = t0 + h * np.arange(n_steps + 1)
    s = FracStepper(y0, h, alpha, n_steps)
    # f may depend on t; feed it the time of the state being evaluated
    clock = {"i": 0}

    def g(y):
        return f(t[min(clock["i"], n_steps)], y)

    s.F[0] = f(t[0], s.y[0]); s._have_f0 = True
    for n in range(n_steps):
        clock["i"] = n + 1
        s.advance(1, g)
    return t, s.y.copy()
