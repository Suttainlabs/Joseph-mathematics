# Chlamydia and syphilis forecasting prototype

State-level transmission models for chlamydia and primary and secondary (P&S)
syphilis in the United States, fitted to public CDC surveillance counts.

Status: research prototype. Author: Joseph Egbemhenghe.

## What is here

| Path | Contents |
|---|---|
| `stimodel/fde.py` | Fractional Adams-Bashforth-Moulton solver for Caputo systems |
| `stimodel/models.py` | Chlamydia S-E-V-I-T-R model and multi-stage syphilis model |
| `stimodel/fit.py` | Simulation, least-squares fitting, scenario forecasts |
| `scripts/fetch_data.py` | Builds `data/sti_state_year.csv` from data.cdc.gov and Census files |
| `scripts/run_validation.py` | Rolling-origin backtest and final fits |
| `scripts/make_figures.py` | Figures for the report |
| `scripts/build_dashboard.py` | Builds the static dashboard in `docs/index.html` |
| `tests/` | Solver checks against closed-form solutions |
| `REPORT.md` | Technical report: data, method, results, limitations |
| `ROADMAP.md` | Draft plan for the next stages |

## Reproduce

```
pip install -r requirements.txt
python -m pytest tests
python scripts/fetch_data.py        # about 1 minute, needs internet
python scripts/run_validation.py    # about 25 minutes on 2 cores
python scripts/make_figures.py
python scripts/build_dashboard.py
```

Open `docs/index.html` in a browser. To host it, enable GitHub Pages for the
`docs/` folder of this repository.

## Models

The chlamydia model is the one published in Egbemhenghe, Akor, Atokolo and
Amos (2025), *Numerical Solution of Fractional order Chlamydia Model Via the
Generalized Fractional Adams-Bashforth-Moulton Approach*,
doi:10.5281/zenodo.14716850. The vaccination rate is set to zero because no
chlamydia vaccine is licensed in the United States.

The syphilis model has incubating, primary, secondary and early latent
stages, reversion from early latent to secondary, and treatment.

## Data

CDC NNDSS weekly tables (data.cdc.gov) and U.S. Census Bureau state population
estimates. `data/SOURCES.json` lists each dataset id and the week used.
The series covers 2013 to 2024. DC has no 2013 value and Hawaii no 2024 value
in the source tables.

## Main result so far

On a backtest over the 50 states and DC, the compartmental models forecast
less accurately than repeating the last observed year, and fitting the
fractional order changed accuracy by less than half a percentage point.
`REPORT.md` gives the numbers and the likely reasons.
