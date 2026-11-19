"""Figures for the technical report (results/figures/)."""
from __future__ import annotations

import json
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
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


def national():
    fits = read_json(RES / "fits.json")
    fig, axes = plt.subplots(1, 2, figsize=(11, 4))
    for ax, dis in zip(axes, TITLES):
        f = fits["fits"][dis]["United States"]
        obs = {int(k): v for k, v in f["observed"].items()}
        first = f["integer"]["first_year"]
        yrs = list(range(first, fits["forecast_to"] + 1))
        ax.axvspan(max(obs) + 0.5, yrs[-1] + 0.5, color="#f6f5f1")
        ax.plot(yrs, f["integer"]["scenarios"]["1.0|1.0"], color=BLUE, lw=2, label="Integer order")
        ax.plot(yrs, f["fractional"]["scenarios"]["1.0|1.0"], color=ORANGE, lw=2, ls="--",
                label=f"Fractional order (alpha = {f['fractional']['alpha']:.2f})")
        ax.plot(list(obs), list(obs.values()), color=INK, lw=2, marker="o", ms=5, label="Reported")
        ax.set_title(f"{TITLES[dis]}, United States", loc="left", fontsize=11)
        ax.set_ylabel("Cases per 100,000")
        ax.set_ylim(bottom=0)
        ax.grid(axis="y", color="#e4e3df")
        ax.spines[["top", "right"]].set_visible(False)
        ax.legend(frameon=False, fontsize=9)
    fig.tight_layout()
    fig.savefig(RES / "figures" / "national_fit.png", dpi=160)


def backtest():
    s = pd.read_csv(RES / "summary.csv")
    order = ["integer", "fractional", "persistence", "trend"]
    labels = ["Model,\ninteger", "Model,\nfractional", "Persistence", "Five-year\ntrend"]
    fig, axes = plt.subplots(1, 4, figsize=(12, 3.6))
    i = 0
    for dis in TITLES:
        for h in (1, 2):
            ax = axes[i]; i += 1
            g = s[(s.disease == dis) & (s.horizon == h)].set_index("model").reindex(order)
            bars = ax.bar(labels, g["median"], color=[BLUE, BLUE, GREY, GREY], width=0.6)
            ax.bar_label(bars, fmt="%.1f%%", fontsize=9)
            ax.set_title(f"{TITLES[dis]}\n{h}-year-ahead", loc="left", fontsize=10)
            ax.tick_params(axis="x", labelsize=8)
            ax.spines[["top", "right"]].set_visible(False)
            ax.set_ylim(0, g["median"].max() * 1.2)
    axes[0].set_ylabel("Median absolute % error")
    fig.tight_layout()
    fig.savefig(RES / "figures" / "backtest.png", dpi=160)


if __name__ == "__main__":
    (RES / "figures").mkdir(parents=True, exist_ok=True)
    national()
    backtest()
    print("figures written")
