# Chlamydia and syphilis forecasting prototype

A research prototype of a forecasting framework for chlamydia and primary and
secondary (P&S) syphilis in U.S. states. Author: Joseph Egbemhenghe.

The design has four parts, each a module:

| Part | What it does | Code |
|---|---|---|
| Multi-stage transmission model | Chlamydia (5 compartments) and syphilis (6 compartments, with primary, secondary and early latent stages and reversion) | `stimodel/models.py` |
| Fractional-order solver | Caputo-derivative version of each model, solved by the fractional Adams-Bashforth-Moulton method | `stimodel/fde.py` |
| Data assimilation | Estimates each state's contact rate year by year from CDC surveillance counts | `stimodel/assimilate.py` |
| Machine-learned parameter forecast | Gradient-boosted model, trained on all states, that forecasts next year's contact rate | `stimodel/learn.py` |

`scripts/run_validation.py` joins them: it backtests the combined forecaster
against simpler ones, produces five-year forecasts with error bands, ranks
states, runs treatment and contact-rate scenarios, and solves a small
capacity-allocation exercise. `scripts/build_dashboard.py` turns the results
into `docs/index.html`.

## Reproduce

```
pip install -r requirements.txt
python -m pytest tests
python scripts/fetch_data.py        # about 1 minute, needs internet
python scripts/run_validation.py    # about 2 minutes
python scripts/make_figures.py
python scripts/build_dashboard.py
```

## Where it stands

The pipeline runs end to end on real data for 50 states and DC. In a
five-origin backtest the combined forecaster is more accurate than the
transmission model alone, but it is still less accurate than assuming "next
year equals this year", except for syphilis two years ahead where the two are
about level. The fractional order changes accuracy very little on annual
data. `REPORT.md` has the numbers, the limits and the reasons.

## Data

CDC NNDSS weekly tables (data.cdc.gov) and U.S. Census Bureau state
population estimates, 2013 to 2024. `data/SOURCES.json` lists every dataset
id. National Inpatient Sample data are not used; see `ROADMAP.md`.

## Other files

`REPORT.md` technical report. `WALKTHROUGH.md` reading guide to the code.
`ROADMAP.md` draft plan. `tests/` solver, model and error-path tests.
