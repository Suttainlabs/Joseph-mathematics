"""Rolling-origin backtest and final fits.

For each state (and the national total), each disease and each forecast
origin T, the models are fitted to data up to and including year T and then
forecast years T+1 and T+2. Four forecasters are compared:

  integer     the compartmental model with alpha = 1
  fractional  the same model with the Caputo order alpha fitted in [0.6, 1]
  persistence next year equals the last observed year
  trend       straight line through the last five training years

Outputs (results/): backtest.csv, summary.csv, fits.json, scenarios.json
"""
from __future__ import annotations

import json
import sys
from multiprocessing import Pool
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from stimodel.fit import fit  # noqa: E402

ORIGINS = [2019, 2020, 2021, 2022]
HORIZONS = [1, 2]
FORECAST_TO = 2029
CONTACT = [1.0, 0.9, 0.8]
TREAT = [1.0, 1.1, 1.25, 1.5]


def read_cases():
    """Load the case table, with a clear message if it has not been built."""
    path = ROOT / "data" / "sti_state_year.csv"
    try:
        return pd.read_csv(path)
    except (OSError, pd.errors.ParserError) as e:
        raise SystemExit(f"cannot read {path}: {e}. Run scripts/fetch_data.py first.")


def write_outputs(res, bt, summ, payload):
    """Write the three result files; stop with one message if the folder is not writable."""
    try:
        res.mkdir(exist_ok=True)
        bt.to_csv(res / "backtest.csv", index=False, float_format="%.4f")
        summ.to_csv(res / "summary.csv", index=False)
        with open(res / "fits.json", "w") as fh:
            json.dump(payload, fh)
    except OSError as e:
        raise SystemExit(f"could not write results to {res}: {e}")


def load():
    d = read_cases()
    series = {}
    for (dis, st), g in d.groupby(["disease", "state"]):
        g = g.sort_values("year")
        series[(dis, st)] = (g.year.values, (g.cases / g.population).values)
    # national: sum over states; a state missing in one year (DC 2013, Hawaii
    # 2024) is filled with its nearest reported year so the total is comparable
    for dis, g in d.groupby("disease"):
        wide_c = g.pivot(index="year", columns="state", values="cases").ffill().bfill()
        wide_p = g.pivot(index="year", columns="state", values="population").ffill().bfill()
        series[(dis, "United States")] = (wide_c.index.values,
                                          (wide_c.sum(axis=1) / wide_p.sum(axis=1)).values)
    return series


def backtest_one(args):
    dis, st, years, rates = args
    rows = []
    for T in ORIGINS:
        m = years <= T
        if m.sum() < 6:
            continue
        ty, tr = years[m], rates[m]
        preds = {}
        for name, frac in (("integer", False), ("fractional", True)):
            try:
                f = fit(dis, ty, tr, fractional=frac)
                p = f.predict(T + max(HORIZONS))
                preds[name] = {h: p[T + h - f.first_year] for h in HORIZONS}
                preds[name]["alpha"] = f.alpha
            except Exception as e:  # keep going; record nothing for this model
                print("fit failed", dis, st, T, name, e, file=sys.stderr)
        k = min(5, len(ty))
        slope, icpt = np.polyfit(ty[-k:], tr[-k:], 1)
        preds["persistence"] = {h: tr[-1] for h in HORIZONS}
        preds["trend"] = {h: max(icpt + slope * (T + h), 0.0) for h in HORIZONS}
        for h in HORIZONS:
            obs = rates[years == T + h]
            if obs.size == 0:
                continue
            for name, p in preds.items():
                if not np.isfinite(p[h]):
                    continue
                rows.append({"disease": dis, "state": st, "origin": T, "horizon": h,
                             "target_year": T + h, "model": name,
                             "observed_per_100k": obs[0] * 1e5,
                             "forecast_per_100k": p[h] * 1e5,
                             "abs_pct_error": abs(p[h] - obs[0]) / obs[0] * 100,
                             "alpha": p.get("alpha", np.nan)})
    return rows


def final_one(args):
    dis, st, years, rates = args
    out = {}
    for name, frac in (("integer", False), ("fractional", True)):
        f = fit(dis, years, rates, fractional=frac)
        last = int(years[-1])
        scen = {}
        for c in CONTACT:
            for t in TREAT:
                p = f.predict(FORECAST_TO, switch_year=last + 1, contact_mult=c, treat_mult=t)
                scen[f"{c}|{t}"] = [round(v * 1e5, 3) for v in p]
        out[name] = {"beta": f.beta, "tau": f.tau, "i0": f.i0, "alpha": f.alpha,
                     "train_rmse_rel": f.train_rmse_rel, "first_year": f.first_year,
                     "last_data_year": last, "scenarios": scen}
    out["observed"] = {int(y): round(r * 1e5, 3) for y, r in zip(years, rates)}
    return (dis, st, out)


def main():
    res = ROOT / "results"
    series = load()
    jobs = [(dis, st, y, r) for (dis, st), (y, r) in series.items()]
    with Pool() as pool:
        bt = [row for rows in pool.imap_unordered(backtest_one, jobs, chunksize=2) for row in rows]
        finals = pool.map(final_one, jobs, chunksize=2)
    bt = pd.DataFrame(bt).sort_values(["disease", "state", "origin", "horizon", "model"])
    states_only = bt[bt.state != "United States"]
    summ = (states_only.groupby(["disease", "horizon", "model"]).abs_pct_error
            .agg(median="median", mean="mean", n="count").round(2).reset_index())
    fits = {}
    for dis, st, out in finals:
        fits.setdefault(dis, {})[st] = out
    write_outputs(res, bt, summ, {"contact_multipliers": CONTACT, "treatment_multipliers": TREAT,
                                  "forecast_to": FORECAST_TO, "fits": fits})
    print(summ.to_string(index=False))


if __name__ == "__main__":
    main()
