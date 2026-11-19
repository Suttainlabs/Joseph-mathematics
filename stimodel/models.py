"""Compartmental models. All compartments are fractions of the population
(they sum to 1) and all rates are per year.

Chlamydia: the S-E-V-I-T-R model of Egbemhenghe, Akor, Atokolo and Amos
(2025), doi:10.5281/zenodo.14716850, equations (5)-(6).

Syphilis: a multi-stage model with incubating, primary, secondary and early
latent stages, reversion from early latent back to secondary, and treatment.
"""
from __future__ import annotations

from dataclasses import dataclass, replace

import numpy as np


@dataclass(frozen=True)
class ChlamydiaParams:
    beta1: float            # effective contact rate, susceptible x infected   (fitted)
    tau: float              # diagnosis-and-treatment rate of infected         (fitted)
    beta2: float = 0.0      # contact rate with people on treatment; set to 0
    sigma: float = 12.0     # exposed -> infected
    gamma: float = 12.0     # on treatment -> recovered
    omega: float = 12.0     # recovered -> susceptible (no lasting immunity)
    mu: float = 0.02        # population turnover
    delta1: float = 0.0     # disease-induced death, infected
    delta2: float = 0.0     # disease-induced death, on treatment
    vacc: float = 0.0       # vaccination rate; 0 because no chlamydia vaccine is licensed
    wane: float = 0.5       # vaccine waning rate (inactive while vacc = 0)

    names = ("S", "E", "V", "I", "T", "R")

    def rhs(self, y):
        S, E, V, I, T, R = y
        lam = self.beta1 * I + self.beta2 * T          # N = 1
        return np.array([
            self.mu + self.wane * V + self.omega * R - (lam + self.vacc + self.mu) * S,
            lam * S - (self.sigma + self.mu) * E,
            self.vacc * S - (self.wane + self.mu) * V,
            self.sigma * E - (self.tau + self.delta1 + self.mu) * I,
            self.tau * I - (self.gamma + self.delta2 + self.mu) * T,
            self.gamma * T - (self.omega + self.mu) * R,
        ])

    def reported_flux(self, y):
        """Rate at which infections are diagnosed (what surveillance counts)."""
        return self.tau * y[..., 3]

    def initial_state(self, i0):
        e0 = i0 * (self.tau + self.mu) / self.sigma
        t0 = i0 * self.tau / self.gamma
        r0 = t0 * self.gamma / self.omega
        return np.array([1 - e0 - i0 - t0 - r0, e0, 0.0, i0, t0, r0])

    def r0(self):
        """Basic reproduction number with vacc = 0."""
        k1 = self.sigma + self.mu
        k2 = self.tau + self.delta1 + self.mu
        k3 = self.gamma + self.delta2 + self.mu
        return self.sigma / k1 * (self.beta1 / k2 + self.beta2 * self.tau / (k2 * k3))


@dataclass(frozen=True)
class SyphilisParams:
    beta: float             # effective contact rate, primary + secondary     (fitted)
    tau: float              # diagnosis-and-treatment rate, primary/secondary  (fitted)
    sigma: float = 12.0     # incubating -> primary
    k1: float = 8.0         # primary -> secondary (about 6.5 weeks)
    k2: float = 3.4         # secondary -> early latent (about 3.5 months)
    rev: float = 0.5        # early latent -> secondary (reversion)
    k3: float = 1.0         # early latent -> late, non-infectious
    tau_l: float = 1.0      # treatment rate in early latent stage
    omega: float = 0.2      # treated/removed -> susceptible
    mu: float = 0.02

    names = ("S", "E", "I1", "I2", "L", "T")

    def rhs(self, y):
        S, E, I1, I2, L, T = y
        lam = self.beta * (I1 + I2)
        return np.array([
            self.mu + self.omega * T - (lam + self.mu) * S,
            lam * S - (self.sigma + self.mu) * E,
            self.sigma * E - (self.k1 + self.tau + self.mu) * I1,
            self.k1 * I1 + self.rev * L - (self.k2 + self.tau + self.mu) * I2,
            self.k2 * I2 - (self.rev + self.tau_l + self.k3 + self.mu) * L,
            self.tau * (I1 + I2) + (self.tau_l + self.k3) * L - (self.omega + self.mu) * T,
        ])

    def reported_flux(self, y):
        return self.tau * (y[..., 2] + y[..., 3])

    def initial_state(self, i0):
        i1 = i0
        i2 = i1 * self.k1 / (self.k2 + self.tau)
        lat = i2 * self.k2 / (self.rev + self.tau_l + self.k3)
        e0 = i1 * (self.k1 + self.tau) / self.sigma
        return np.array([1 - e0 - i1 - i2 - lat, e0, i1, i2, lat, 0.0])


MODELS = {"chlamydia": ChlamydiaParams, "ps_syphilis": SyphilisParams}
# name of the transmission and treatment parameters in each model
BETA = {"chlamydia": "beta1", "ps_syphilis": "beta"}


def with_scenario(params, contact_mult: float = 1.0, treat_mult: float = 1.0):
    """Scale the contact rate and the diagnosis-and-treatment rate."""
    key = "beta1" if hasattr(params, "beta1") else "beta"
    return replace(params, **{key: getattr(params, key) * contact_mult,
                              "tau": params.tau * treat_mult})
