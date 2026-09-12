"""Regenerate the three slide figures in the deck's palette.

The plots in results/plots/ belong to the exploration notebook and keep matplotlib's
default colours. Slides need the same figures in the deck palette, so they are rebuilt
here into paper/figures/ from the same data.

    python paper/make_figures.py
"""

import sys
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from data_loader import SEED, TARGET, load_jobs, load_vehicles  # noqa: E402
from evaluate import tank_feasibility  # noqa: E402

OUT = Path(__file__).resolve().parent / "figures"
OUT.mkdir(exist_ok=True)

INK = "#12333F"
BRAND = "#0B6E8C"
SUPPORT = "#17A398"
ALERT = "#C25332"
MUTED = "#8DA3AD"
GRID = "#E2EBEF"

plt.rcParams.update({
    "figure.dpi": 200,
    "font.family": "Calibri",
    "font.size": 11,
    "text.color": INK,
    "axes.labelcolor": INK,
    "axes.edgecolor": GRID,
    "axes.linewidth": 1.0,
    "axes.grid": True,
    "axes.axisbelow": True,
    "grid.color": GRID,
    "grid.linewidth": 1.0,
    "xtick.color": INK,
    "ytick.color": INK,
    "xtick.bottom": False,
    "ytick.left": False,
    "axes.spines.top": False,
    "axes.spines.right": False,
    "axes.spines.left": False,
    "legend.frameon": False,
    "savefig.transparent": True,
})


def finish(fig, name):
    fig.tight_layout(pad=0.6)
    fig.savefig(OUT / name, bbox_inches="tight", pad_inches=0.05)
    plt.close(fig)
    print("wrote", (OUT / name).relative_to(ROOT))


def slot_vs_addon(df):
    fig, ax = plt.subplots(1, 2, figsize=(7.6, 3.4))

    slot = df.groupby("slot_type")[TARGET].mean().sort_values()
    ax[0].bar(range(len(slot)), slot.values, color=MUTED, width=0.68)
    ax[0].set_xticks(range(len(slot)))
    ax[0].set_xticklabels([s.replace("_", "\n") for s in slot.index], fontsize=9)
    ax[0].set_ylim(0, 75)
    ax[0].set_ylabel("mean litres per job")
    ax[0].set_title("By slot type — flat", color=INK, fontsize=11, pad=10)
    ax[0].xaxis.grid(False)

    addon = df.groupby("addon_interior_clean")[TARGET].mean()
    ax[1].bar([0, 1], addon.values, color=[MUTED, BRAND], width=0.5)
    ax[1].set_xticks([0, 1])
    ax[1].set_xticklabels(["without\ninterior_clean", "with\ninterior_clean"], fontsize=9)
    ax[1].set_ylim(0, 75)
    ax[1].set_title("By the hidden add-on — not flat", color=INK, fontsize=11, pad=10)
    ax[1].xaxis.grid(False)
    for x, v in zip([0, 1], addon.values):
        ax[1].text(x, v + 1.8, f"{v:.1f} L", ha="center", fontsize=10, color=INK)

    finish(fig, "slot_vs_addon.png")


def functional_form(df):
    ext = df[df.addon_interior_clean == 0]
    base = ext.groupby(["vehicle_size", "dirtiness_level"])[TARGET].mean().unstack()
    order = ["hatchback", "sedan", "suv"]
    colors = {"hatchback": SUPPORT, "sedan": BRAND, "suv": INK}

    fig, ax = plt.subplots(figsize=(6.4, 3.9))
    for size in order:
        ax.plot(base.columns, base.loc[size], marker="o", markersize=6,
                linewidth=2.4, color=colors[size], label=size)
        ax.annotate(size, (base.columns[-1], base.loc[size].iloc[-1]),
                    textcoords="offset points", xytext=(8, -3),
                    fontsize=10, color=colors[size])
    ax.set_xticks(list(base.columns))
    ax.set_xlabel("dirtiness level")
    ax.set_ylabel("mean litres, exterior-only jobs")
    ax.set_xlim(0.85, 4.45)
    ax.xaxis.grid(False)
    ax.set_title("Same ratios at every size — a multiplier, not an offset",
                 color=INK, fontsize=11, pad=10)
    finish(fig, "functional_form.png")


def feasibility(df, vehicles):
    caps = list(vehicles["capacity_litres"])
    feas = tank_feasibility(df[TARGET].to_numpy(), caps, max_jobs=8, seed=SEED)
    colors = [ALERT, BRAND, SUPPORT]

    fig, ax = plt.subplots(figsize=(6.4, 3.9))
    for (_, v), c in zip(vehicles.iterrows(), colors):
        ax.plot(feas.index, feas[v["capacity_litres"]] * 100, marker="o", markersize=5,
                linewidth=2.4, color=c, label=f"{v['vehicle_type']} ({v['capacity_litres']} L)")
    ax.axhline(95, color=MUTED, linestyle=(0, (4, 3)), linewidth=1.4)
    ax.text(8.05, 95, "95%", va="center", fontsize=10, color=MUTED)
    ax.set_xlabel("jobs attempted on one tank")
    ax.set_ylabel("chance all of them fit  (%)")
    ax.set_ylim(-4, 108)
    ax.set_xlim(0.8, 8.6)
    ax.xaxis.grid(False)
    ax.legend(loc="lower left", fontsize=9.5)
    finish(fig, "tank_feasibility.png")


if __name__ == "__main__":
    jobs = load_jobs()
    slot_vs_addon(jobs)
    functional_form(jobs)
    feasibility(jobs, load_vehicles())
