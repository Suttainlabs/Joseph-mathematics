"""Machine-learned forecaster, trained on all states together.

One gradient-boosted regression model per infection. Its inputs describe a
state in year t: its last two yearly changes in reported rate, its level
against the other states, national and regional momentum, and case volume.
Its target is a quantity for year t+1, supplied by the caller:

* for the hybrid forecaster, the log ratio of the contact rate that actually
  occurred to the "stationary" contact rate (the one that would have held the
  reported rate level). A prediction of zero therefore means "no change", so
  the learner only has to supply the departure from that default;
* for the rate-only forecaster, the log change in the reported rate.

Only data up to the forecast origin is used to train.
"""
from __future__ import annotations

import numpy as np
from sklearn.ensemble import GradientBoostingRegressor

REGION = {
    "Northeast": "Connecticut Maine Massachusetts New_Hampshire Rhode_Island Vermont "
                 "New_Jersey New_York Pennsylvania",
    "Midwest": "Illinois Indiana Michigan Ohio Wisconsin Iowa Kansas Minnesota Missouri "
               "Nebraska North_Dakota South_Dakota",
    "South": "Delaware District_of_Columbia Florida Georgia Maryland North_Carolina "
             "South_Carolina Virginia West_Virginia Alabama Kentucky Mississippi Tennessee "
             "Arkansas Louisiana Oklahoma Texas",
    "West": "Arizona Colorado Idaho Montana Nevada New_Mexico Utah Wyoming Alaska "
            "California Hawaii Oregon Washington",
}
STATE_REGION = {s.replace("_", " "): r for r, names in REGION.items() for s in names.split()}
FEATURES = ["change_1", "change_2", "level_vs_national", "national_change",
            "regional_change", "log_cases"]


def _features(logv, cases, states, t):
    """Feature rows for every state at year index t (uses indices t-2..t)."""
    d1 = logv[:, t] - logv[:, t - 1]
    d2 = logv[:, t - 1] - logv[:, t - 2]
    w = cases[:, t] / cases[:, t].sum()
    nat = float(np.nansum(w * d1))
    reg = np.array([STATE_REGION[s] for s in states])
    reg_d = np.array([np.nanmean(d1[reg == r]) for r in reg])
    lvl = logv[:, t] - np.nanmean(logv[:, t])
    return np.column_stack([d1, d2, lvl, np.full(len(states), nat), reg_d,
                            np.log(np.maximum(cases[:, t], 1.0))])


def fit_model(logv, cases, states, targets, last_idx, seed=0):
    """Train on features at year index t (2 <= t < last_idx) against
    targets[:, t], the outcome for year t+1."""
    X, y, w = [], [], []
    for t in range(2, last_idx):
        f = _features(logv, cases, states, t)
        ok = np.isfinite(f).all(axis=1) & np.isfinite(targets[:, t])
        X.append(f[ok]); y.append(targets[ok, t]); w.append(np.sqrt(np.maximum(cases[ok, t], 1.0)))
    if not X or sum(len(v) for v in y) < 50:
        return None                                   # too little history to learn from
    X, y, w = np.vstack(X), np.concatenate(y), np.concatenate(w)
    m = GradientBoostingRegressor(loss="huber", n_estimators=150, max_depth=2,
                                  learning_rate=0.05, subsample=0.8, min_samples_leaf=8,
                                  random_state=seed)
    m.fit(X, y, sample_weight=w)
    return m


def predict_step(model, logv, cases, states):
    """Prediction for the year after the last column of logv, one per state."""
    d = np.zeros(len(states))
    if model is None:
        return d
    f = _features(logv, cases, states, logv.shape[1] - 1)
    ok = np.isfinite(f).all(axis=1)
    if ok.any():
        d[ok] = model.predict(f[ok])
    return d
