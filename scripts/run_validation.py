"""Backtest, final forecasts, hotspots and intervention allocation.

Pipeline for each infection and each fractional order alpha:

1. Assimilate: estimate each state's contact rate year by year (stimodel/assimilate.py).
2. Learn: train a gradient-boosted model on all states to forecast how far
   next year's contact rate departs from the rate that would hold cases level
   (stimodel/learn.py).
3. Forecast: run the transmission model forward with the forecast contact rates.

Rolling-origin backtest. For each origin year T the learner sees data up to T
only, and years T+1 and T+2 are forecast. Forecasters compared:

  hybrid        transmission model + learned contact rate   (the proposed design)
  momentum      transmission model, contact rate held at its last value
  ml_rate       the same learner applied to reported rates, no transmission model
  persistence   next year equals the last observed year
  trend         straight line through the last five years

Outputs in results/: backtest.csv, summary.csv, forecasts.json
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from stimodel.assimilate import assimilate, stationary_beta, step_year  # noqa: E402
from stimodel.learn import fit_model, predict_step  # noqa: E402

ALPHAS = [1.0, 0.8]
ORIGINS = [2019, 2020, 2021, 2022, 2023]
HORIZONS = [1, 2]
FORECAST_YEARS = 5
PRIMARY = "hybrid_a1.0"
TREAT = [1.0, 1.1, 1.2, 1.3]
CONTACT = [1.0, 0.95, 0.9]
AVERT_YEARS = 3


def read_cases():
    """Load the case table, with a clear message if it has not been built."""
    path = ROOT / "data" / "sti_state_year.csv"
    try:
        return pd.read_csv(path)
    except (OSError, pd.errors.ParserError) as e:
        raise SystemExit(f"cannot read {path}: {e}. Run scripts/fetch_data.py first.")


def write_outputs(res, bt, summ, payload):
    """Write the result files; stop with one message if the folder is not writable."""
    try:
        res.mkdir(exist_ok=True)
        bt.to_csv(res / "backtest.csv", index=False, float_format="%.4f")
        summ.to_csv(res / "summary.csv", index=False)
        with open(res / "forecasts.json", "w") as fh:
            json.dump(payload, fh)
    except OSError as e:
        raise SystemExit(f"could not write results to {res}: {e}")


def matrices(d, disease):
    """State-by-year arrays. A state missing one year in the source (DC 2013,
    Hawaii 2024) is filled from its nearest year for model input only;
    `observed` marks the real values, and only those are scored."""
    g = d[d.disease == disease]
    cases = g.pivot(index="state", columns="year", values="cases")
    pop = g.pivot(index="state", columns="year", values="population")
    observed = cases.notna().values
    cases = cases.ffill(axis=1).bfill(axis=1)
    pop = pop.ffill(axis=1).bfill(axis=1)
    return (list(cases.index), cases.columns.values.astype(int), cases.values.astype(float),
            pop.values.astype(float), observed)


def hybrid_forecast(tracks, model, log_rate, cases, states, i, horizon):
    """Transmission model driven by the learned contact rate. Each year: find
    the contact rate that would hold the state's rate level, scale it by the
    learner's predicted departure, and step the model. Returns (rates, betas),
    each of shape (n_states, horizon)."""
    n = len(states)
    lv, cs = log_rate[:, : i + 1].copy(), cases[:, : i + 1].copy()
    steppers = [t.start_forecast(i) for t in tracks]
    cur = np.array([t.rates[i] for t in tracks])
    guess = np.array([t.beta[i] for t in tracks])
    rates, betas = np.zeros((n, horizon)), np.zeros((n, horizon))
    for h in range(horizon):
        dev = predict_step(model, lv, cs, states)
        for s in range(n):
            star = stationary_beta(steppers[s], tracks[s].disease, cur[s], max(guess[s], 1e-3))
            betas[s, h] = guess[s] = star * np.exp(dev[s])
            rates[s, h] = step_year(steppers[s], tracks[s].disease, betas[s, h])
        lv = np.column_stack([lv, np.log(np.maximum(rates[:, h], 1e-9))])
        cs = np.column_stack([cs, cs[:, -1] * rates[:, h] / np.maximum(cur, 1e-12)])
        cur = rates[:, h].copy()
    return rates, betas


def run_disease(d, disease):
    states, years, cases, pop, observed = matrices(d, disease)
    rates = cases / pop
    log_rate = np.log(np.maximum(rates, 1e-9))
    n = len(states)
    rows = []

    def score(name, origin, h, pred, alpha=np.nan):
        j = np.where(years == origin + h)[0]
        if j.size == 0:
            return
        j = j[0]
        for s, st in enumerate(states):
            if observed[s, j] and np.isfinite(pred[s]) and rates[s, j] > 0:
                rows.append({"disease": disease, "state": st, "origin": origin, "horizon": h,
                             "target_year": origin + h, "model": name, "alpha": alpha,
                             "observed_per_100k": rates[s, j] * 1e5,
                             "forecast_per_100k": pred[s] * 1e5,
                             "abs_pct_error": abs(pred[s] - rates[s, j]) / rates[s, j] * 100,
                             "log_error": float(np.log(max(pred[s], 1e-12) / rates[s, j]))})

    tracks = {a: [assimilate(disease, years, rates[s], a) for s in range(n)] for a in ALPHAS}
    growth = np.full_like(log_rate, np.nan)
    growth[:, :-1] = np.diff(log_rate, axis=1)                 # target for the rate-only learner
    deviation = {}                                             # target for the hybrid learner
    for a in ALPHAS:
        beta = np.array([t.beta for t in tracks[a]])
        star = np.array([t.beta_star for t in tracks[a]])
        dev = np.full_like(log_rate, np.nan)
        dev[:, :-1] = np.log(beta[:, 1:] / star[:, :-1])
        deviation[a] = dev
    hmax = max(HORIZONS)
    for origin in ORIGINS:
        i = int(np.where(years == origin)[0][0])
        k = min(5, i + 1)
        for h in HORIZONS:
            score("persistence", origin, h, rates[:, i])
            tr = np.array([max(np.polyval(np.polyfit(years[i - k + 1: i + 1],
                                                     rates[s, i - k + 1: i + 1], 1), origin + h), 0)
                           for s in range(n)])
            score("trend", origin, h, tr)
        # learner on reported rates, no transmission model
        m = fit_model(log_rate, cases, states, growth, i)
        lv, cs = log_rate[:, : i + 1].copy(), cases[:, : i + 1].copy()
        for h in range(1, hmax + 1):
            dlt = predict_step(m, lv, cs, states)
            lv = np.column_stack([lv, lv[:, -1] + dlt])
            cs = np.column_stack([cs, cs[:, -1] * np.exp(dlt)])
            if h in HORIZONS:
                score("ml_rate", origin, h, np.exp(lv[:, -1]))
        # transmission model, with and without the learner
        for a in ALPHAS:
            mb = fit_model(log_rate, cases, states, deviation[a], i)
            hyb, _ = hybrid_forecast(tracks[a], mb, log_rate, cases, states, i, hmax)
            mom = np.array([tracks[a][s].forecast(i, [tracks[a][s].beta[i]] * hmax)
                            for s in range(n)])
            for h in HORIZONS:
                score(f"hybrid_a{a}", origin, h, hyb[:, h - 1], a)
                score(f"momentum_a{a}", origin, h, mom[:, h - 1], a)

    # ---- final forecasts from the last data year, primary forecaster
    a = float(PRIMARY.split("_a")[1])
    i = len(years) - 1
    mb = fit_model(log_rate, cases, states, deviation[a], i)
    _, paths = hybrid_forecast(tracks[a], mb, log_rate, cases, states, i, FORECAST_YEARS)
    beta = np.array([t.beta for t in tracks[a]])
    out = {}
    for s, st in enumerate(states):
        scen = {}
        for c in CONTACT:
            for t in TREAT:
                f = tracks[a][s].forecast(i, paths[s] * c, tau_mult=t)
                scen[f"{c}|{t}"] = [round(v * 1e5, 3) for v in f]
        last_real = int(years[np.where(observed[s])[0][-1]])
        out[st] = {"observed": {int(y): round(r * 1e5, 3)
                                for y, r, o in zip(years, rates[s], observed[s]) if o},
                   "beta": [round(b, 4) for b in beta[s]],
                   "last_reported_year": last_real, "population": int(pop[s, i]),
                   "last_cases": int(cases[s, i]), "scenarios": scen}
    names = ["change_1", "change_2", "level_vs_national", "national_change",
             "regional_change", "log_cases"]
    importance = dict(zip(names, [round(float(v), 3) for v in mb.feature_importances_]))
    return rows, out, importance, int(years[-1])


def intervals(bt):
    """80% interval multipliers from backtest errors of the primary forecaster,
    and their coverage when each origin is left out in turn."""
    out = {}
    p = bt[bt.model == PRIMARY]
    for (dis, h), g in p.groupby(["disease", "horizon"]):
        lo, hi = np.quantile(g.log_error, [0.1, 0.9])
        cover = []
        for o in sorted(g.origin.unique()):
            tr, te = g[g.origin != o], g[g.origin == o]
            a, b = np.quantile(tr.log_error, [0.1, 0.9])
            cover.append(((te.log_error >= a) & (te.log_error <= b)).mean())
        out[f"{dis}|{h}"] = {"lo": round(float(np.exp(-hi)), 4), "hi": round(float(np.exp(-lo)), 4),
                             "coverage_leave_one_origin_out": round(float(np.mean(cover)), 3)}
    return out


def allocation(fc):
    """Illustrative allocation of extra diagnosis-and-treatment capacity.
    Budget: enough to raise the rate by 10% in every state. Cost of raising a
    state's rate by a fraction u is taken as u x its latest case count (extra
    treatment throughput). Capacity is handed out in 10-point steps to the
    state where the next step averts the most cases per unit cost."""
    states = list(fc)
    levels = [1.0, 1.1, 1.2, 1.3]

    def cases_over(st, mult):
        s = fc[st]
        return sum(s["scenarios"][f"1.0|{mult}"][:AVERT_YEARS]) / 1e5 * s["population"]

    averted = {st: [cases_over(st, 1.0) - cases_over(st, m) for m in levels] for st in states}
    cost = {st: fc[st]["last_cases"] * 0.1 for st in states}            # per 10-point step
    budget = sum(cost.values())
    level = {st: 0 for st in states}
    spent = 0.0
    while True:
        best, best_ratio = None, 0.0
        for st in states:
            if level[st] < 3 and spent + cost[st] <= budget + 1e-9:
                gain = averted[st][level[st] + 1] - averted[st][level[st]]
                if gain / cost[st] > best_ratio:
                    best, best_ratio = st, gain / cost[st]
        if best is None:
            break
        level[best] += 1
        spent += cost[best]
    uniform = sum(averted[st][1] for st in states)
    targeted = sum(averted[st][level[st]] for st in states)
    return {"uplift_pct": {st: level[st] * 10 for st in states},
            "averted": {st: round(averted[st][level[st]]) for st in states},
            "cases_averted_uniform": round(uniform), "cases_averted_targeted": round(targeted),
            "years": AVERT_YEARS, "budget_share_spent": round(spent / budget, 3)}


def main():
    d = read_cases()
    rows, fits, imp, alloc = [], {}, {}, {}
    last_year = None
    for disease in ("chlamydia", "ps_syphilis"):
        r, out, importance, last_year = run_disease(d, disease)
        rows += r
        fits[disease], imp[disease] = out, importance
        alloc[disease] = allocation(out)
        print(disease, "done", flush=True)
    bt = pd.DataFrame(rows).sort_values(["disease", "state", "origin", "horizon", "model"])
    summ = (bt.groupby(["disease", "horizon", "model"]).abs_pct_error
            .agg(median="median", mean="mean", n="count").round(2).reset_index())
    payload = {"primary": PRIMARY, "last_data_year": last_year,
               "forecast_years": list(range(last_year + 1, last_year + 1 + FORECAST_YEARS)),
               "contact_multipliers": CONTACT, "treatment_multipliers": TREAT,
               "intervals": intervals(bt), "feature_importance": imp,
               "allocation": alloc, "fits": fits}
    write_outputs(ROOT / "results", bt, summ, payload)
    print(summ.pivot_table(index="model", columns=["disease", "horizon"], values="median").to_string())


if __name__ == "__main__":
    main()
