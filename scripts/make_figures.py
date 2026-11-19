"""Figures for the technical report (results/figures/)."""
from __future__ import annotations

import json
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
RES = ROOT / "results"
INK, BLUE, ORANGE, GREY = "#0b0b0b", "#2a78d6", "#eb6834", "#8a8984"
TITLES = {"chlamydia": "Chlamydia", "ps_syphilis": "Primary and secondary syphilis"}


def read_json(path):
    """Load a results file, with a clear message if an earlier step was skipped."""
    try:
        with open(path) as f:
            return json.load(f)
    except FileNotFoundError:
        raise SystemExit(f"{path} not found; run the earlier pipeline steps first")
    except (OSError, json.JSONDecodeError) as e:
        raise SystemExit(f"cannot read {path}: {e}")


def read_summary(path):
    """Load the backtest summary table, with a clear message if it is missing or damaged."""
    try:
        return pd.read_csv(path)
    except (OSError, pd.errors.ParserError) as e:
        raise SystemExit(f"cannot read {path}: {e}. Run scripts/run_validation.py first.")


def save_figure(fig, name):
    """Save a figure under results/figures, stopping with a message if that fails."""
    path = RES / "figures" / name
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        fig.savefig(path, dpi=160)
    except OSError as e:
        raise SystemExit(f"could not write {path}: {e}")


def contact_rates():
    """Estimated contact rate by year: median and middle half of states."""
    fc = read_json(RES / "forecasts.json")
    fig, axes = plt.subplots(1, 2, figsize=(11, 3.8))
    for ax, dis in zip(axes, TITLES):
        fits = fc["fits"][dis]
        beta = np.array([v["beta"] for v in fits.values()])
        years = np.arange(fc["last_data_year"] - beta.shape[1] + 1, fc["last_data_year"] + 1)
        q1, med, q3 = np.percentile(beta, [25, 50, 75], axis=0)
        ax.fill_between(years, q1, q3, color=BLUE, alpha=0.18, lw=0, label="Middle half of states")
        ax.plot(years, med, color=BLUE, lw=2, marker="o", ms=4, label="Median state")
        ax.set_title(f"{TITLES[dis]}: estimated contact rate", loc="left", fontsize=11)
        ax.set_ylabel("Contact rate (per year)")
        ax.grid(axis="y", color="#e4e3df")
        ax.spines[["top", "right"]].set_visible(False)
        ax.legend(frameon=False, fontsize=9)
    fig.tight_layout()
    save_figure(fig, "contact_rates.png")


def backtest():
    s = read_summary(RES / "summary.csv")
    order = ["hybrid_a1.0", "hybrid_a0.8", "ml_rate", "persistence", "trend"]
    labels = ["Hybrid", "Hybrid,\norder 0.8", "Learner\nonly", "Persist-\nence", "Trend"]
    fig, axes = plt.subplots(1, 4, figsize=(13.5, 3.6))
    i = 0
    for dis in TITLES:
        for h in (1, 2):
            ax = axes[i]; i += 1
            g = s[(s.disease == dis) & (s.horizon == h)].set_index("model").reindex(order)
            bars = ax.bar(labels, g["median"], color=[BLUE, BLUE, GREY, GREY, GREY], width=0.6)
            ax.bar_label(bars, fmt="%.1f%%", fontsize=9)
            ax.set_title(f"{TITLES[dis]}\n{h}-year-ahead", loc="left", fontsize=10)
            ax.tick_params(axis="x", labelsize=8)
            ax.spines[["top", "right"]].set_visible(False)
            ax.set_ylim(0, g["median"].max() * 1.2)
    axes[0].set_ylabel("Median absolute % error")
    fig.tight_layout()
    save_figure(fig, "backtest.png")


if __name__ == "__main__":
    contact_rates()
    backtest()
    print("figures written")
