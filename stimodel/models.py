"""Multi-stage compartmental models.

Compartments are fractions of the population (they sum to 1); rates are per
year. Each model exposes

    rhs(y, beta, tau)     the right-hand side for a given contact rate beta
                          and diagnosis-and-treatment rate tau
    reported(y, tau)      the rate at which infections are diagnosed, which
                          is what surveillance counts
    start(rate, tau)      a starting state consistent with a reported rate

beta is not a constant of the model. It is estimated year by year from
surveillance data (see assimilate.py) and forecast by a learned model
(see learn.py).
"""
from __future__ import annotations

from dataclasses import dataclass

import numpy as np


@dataclass(frozen=True)
class Chlamydia:
    """Susceptible, exposed, infected (undiagnosed), on treatment, recovered.
    Reinfection is allowed after a short recovered period."""
    tau: float = 1.0        # diagnosis-and-treatment rate (mean 1 year to diagnosis or clearance)
    sigma: float = 12.0     # exposed -> infected
    gamma: float = 12.0     # on treatment -> recovered
    omega: float = 12.0     # recovered -> susceptible
    mu: float = 0.02        # population turnover
    names = ("S", "E", "I", "T", "R")

    def rhs(self, y, beta, tau):
        S, E, I, T, R = y
        lam = beta * I
        return np.array([
            self.mu + self.omega * R - (lam + self.mu) * S,
            lam * S - (self.sigma + self.mu) * E,
            self.sigma * E - (tau + self.mu) * I,
            tau * I - (self.gamma + self.mu) * T,
            self.gamma * T - (self.omega + self.mu) * R,
        ])

    def reported(self, y, tau):
        return tau * y[..., 2]

    def start(self, rate, tau):
        i = rate / tau
        e = i * (tau + self.mu) / self.sigma
        t = rate / self.gamma
        r = rate / self.omega
        return np.array([1 - e - i - t - r, e, i, t, r])


@dataclass(frozen=True)
class Syphilis:
    """Susceptible, incubating, primary, secondary, early latent, treated.
    Primary and secondary cases transmit. Early latent cases can revert to
    secondary. Reported P&S cases are primary and secondary cases entering
    treatment."""
    tau: float = 4.0        # diagnosis-and-treatment rate in primary/secondary (about 3 months)
    sigma: float = 12.0     # incubating -> primary
    k1: float = 8.0         # primary -> secondary (about 6.5 weeks)
    k2: float = 3.4         # secondary -> early latent (about 3.5 months)
    rev: float = 0.5        # early latent -> secondary (reversion)
    k3: float = 1.0         # early latent -> late, non-infectious
    tau_l: float = 1.0      # treatment rate in early latent stage
    omega: float = 0.2      # treated -> susceptible
    mu: float = 0.02
    names = ("S", "E", "I1", "I2", "L", "T")

    def rhs(self, y, beta, tau):
        S, E, I1, I2, L, T = y
        lam = beta * (I1 + I2)
        return np.array([
            self.mu + self.omega * T - (lam + self.mu) * S,
            lam * S - (self.sigma + self.mu) * E,
            self.sigma * E - (self.k1 + tau + self.mu) * I1,
            self.k1 * I1 + self.rev * L - (self.k2 + tau + self.mu) * I2,
            self.k2 * I2 - (self.rev + self.tau_l + self.k3 + self.mu) * L,
            tau * (I1 + I2) + (self.tau_l + self.k3) * L - (self.omega + self.mu) * T,
        ])

    def reported(self, y, tau):
        return tau * (y[..., 2] + y[..., 3])

    def start(self, rate, tau):
        # split primary + secondary = rate / tau by their relative durations
        tot = rate / tau
        i1 = tot * (self.k2 + tau) / (self.k1 + self.k2 + tau)
        i2 = tot - i1
        lat = i2 * self.k2 / (self.rev + self.tau_l + self.k3)
        e = i1 * (self.k1 + tau) / self.sigma
        return np.array([1 - e - i1 - i2 - lat, e, i1, i2, lat, 0.0])


MODELS = {"chlamydia": Chlamydia(), "ps_syphilis": Syphilis()}
