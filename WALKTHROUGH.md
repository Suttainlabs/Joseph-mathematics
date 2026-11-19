# Code walkthrough

A reading guide for anyone who needs to understand, explain or change this
code. Read the files in this order.

## 1. `stimodel/fde.py` — the solver

Solves D^alpha y = f(t, y) with a Caputo derivative, 0 < alpha <= 1.

- `abm_weights` builds two weight arrays. `b` weights past values of f in the
  predictor; `c` weights them in the corrector. They come from integrating the
  kernel (t - s)^(alpha - 1) exactly over each step.
- `solve_fde` loops over time steps. Each step (a) predicts y with a
  fractional Adams-Bashforth sum over the whole history, (b) evaluates f at
  the prediction, (c) corrects with a fractional Adams-Moulton sum. The sums
  run over all earlier steps because a fractional derivative has memory. That
  is why cost grows with the square of the number of steps.
- With alpha = 1 every `b` weight is 1 and the scheme becomes the ordinary
  second-order predictor-corrector.

Questions to be able to answer: Why does the history sum start at step 0?
What happens to the weights as alpha goes to 1? Why does a small alpha need a
small step when rates are large?

## 2. `stimodel/models.py` — the equations

- `ChlamydiaParams.rhs` is equations (5)/(6) of the 2025 paper with N = 1.
  Compare it line by line with the paper. `vacc = 0`, `beta2 = 0` and the
  death rates are 0 here; those are choices made for U.S. data, and each can
  be argued either way.
- `reported_flux` is the modelling assumption that links the model to
  surveillance: a reported case is an infection entering treatment, tau * I.
- `initial_state` starts the compartments near their quasi-steady ratios so
  the first simulated years are not dominated by a start-up transient.
- `SyphilisParams` follows the same pattern with primary, secondary and early
  latent stages. The fixed rates are placeholders that need sources.

Questions: What is R0 for each model and where does `r0()` come from? Which
fixed rate would you change first, and what source would you cite?

## 3. `stimodel/fit.py` — fitting and forecasting

- `simulate` runs the solver from two years before the first data year and
  integrates `reported_flux` over each calendar year (trapezoid rule) to get
  annual cases per person. If `switch_year` is set, the contact and treatment
  rates are multiplied from that year on; this is how scenarios work.
- `fit` minimises relative errors with `scipy.optimize.least_squares`. The
  parameters are optimised on a log scale so they stay positive. The
  fractional fit starts from the integer-order answer.

Questions: Why relative rather than absolute errors? Why can three parameters
not all be pinned down by twelve annual points? What does it mean that alpha
usually stays near its starting value?

## 4. `scripts/fetch_data.py` — the data

Read the docstring first. The key decision is taking year Y from the
previous-year column of the year Y+1 table. `canon_area` merges New York City
with the rest of New York State and drops regions and territories.

## 5. `scripts/run_validation.py` — the test

`backtest_one` is the experiment: fit through year T, forecast T+1 and T+2,
compare with what was reported, and do the same for two naive forecasters.
`final_one` fits all years and precomputes the scenario grid for the
dashboard.

## 6. `scripts/build_dashboard.py` and `scripts/make_figures.py`

Presentation only. No modelling happens here.

## Exercises that make the code yours

1. Change `omega` in the chlamydia model and rerun one state. Explain the change in the fit.
2. Add a parameter that lowers the contact rate in 2020 only. Does the backtest improve?
3. Replace the data with CDC's finalized AtlasPlus export and compare totals.
4. Write the derivation of `r0()` for the syphilis model and add it as a method with a test.
