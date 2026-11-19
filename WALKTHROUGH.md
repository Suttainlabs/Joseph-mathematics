# Code walkthrough

A reading guide for anyone who needs to understand, explain or change this
code. Read the files in this order.

## 1. `stimodel/fde.py` — the solver

Solves D^alpha y = f(y) with a Caputo derivative, 0 < alpha <= 1.

- `abm_weights` builds the predictor weights `b` and corrector weights `c`.
  They come from integrating the kernel (t - s)^(alpha - 1) over each step.
- `FracStepper.advance` takes steps. Each one predicts with a fractional
  Adams-Bashforth sum over the whole history, then corrects with a fractional
  Adams-Moulton sum. The history sum is the "memory" of a fractional model.
- `rewind` and `copy_until` let a year be re-run with a different contact
  rate. Assimilation and forecasting both depend on that.

Questions to be able to answer: Why does the history sum start at step 0?
What happens to the weights as alpha goes to 1? Why does cost grow with the
square of the number of steps?

## 2. `stimodel/models.py` — the equations

Two dataclasses, `Chlamydia` and `Syphilis`. Each has `rhs(y, beta, tau)`,
`reported(y, tau)` (what surveillance sees: infections entering treatment)
and `start(rate, tau)` (a starting state consistent with a reported rate).
The contact rate `beta` is an argument, not a constant, because it is
estimated from data.

Questions: Which stages transmit in the syphilis model, and why? What does
reversion do to the dynamics? Which fixed rate would you source first?

## 3. `stimodel/assimilate.py` — reading the contact rate off the data

- `_solve_beta` finds, by root-finding on log beta, the contact rate that
  moves the model from where it is to next year's reported rate.
- `assimilate` does that for every year and returns a `Track`: the contact
  rate series, the "stationary" contact rate for each year (the one that
  would have kept cases level), and the stepper with its full history.
- The module docstring explains why mid-year points are matched and not
  whole-year integrals.

Questions: Why is the integral-matching inversion unstable? What does it mean
when `matched` is False? How is beta related to the growth rate of cases?

## 4. `stimodel/learn.py` — the learned forecast

- `_features` builds six inputs per state and year.
- `fit_model` trains one gradient-boosted regressor on all states.
- `predict_step` gives next year's prediction, or zero if there was too
  little history to train.

Questions: Why train on all states together? Why is the target a departure
from the stationary rate and not the rate itself? What would leak future
information into training, and how does the code avoid it?

## 5. `scripts/run_validation.py` — the experiment

`hybrid_forecast` is the loop that joins the parts: stationary rate, learned
departure, one model step, repeat. `run_disease` runs the backtest and the
final forecasts. `intervals` builds error bands from backtest errors and
checks their coverage. `allocation` is the capacity exercise.

## 6. `scripts/fetch_data.py`, `build_dashboard.py`, `make_figures.py`

Data assembly and presentation. Read the `fetch_data.py` docstring for how
each year's count is chosen.

## Exercises that make the code yours

1. Add a seventh feature to the learner (for example the state's 2020 drop) and rerun the backtest. Decide in advance what result would make you keep it.
2. Split each model into two activity groups and see whether scenario sizes become more reasonable.
3. Replace the data with CDC's finalized AtlasPlus export and compare totals.
4. Derive the epidemic threshold of the syphilis model and add it as a tested method.
