#!/usr/bin/env python3
"""
fig14 — can flower colour be predicted from environment?

Follows the same design rules as 22_Build_Method_Figures.py: estimates carry
uncertainty, one message per panel, PDF + 400-dpi PNG.

Panel A  macro-F1 under genus-grouped CV, with bootstrap intervals.
         Message: environment models beat the majority floor, but only just.
Panel B  grouped vs ungrouped CV for the genus prior and the best environment
         model. Message: relatedness carries the signal, environment does not,
         and the CV design is what reveals it.
Panel C  permutation importance. Message: PC2 alone carries the signal, which
         independently reproduces the MCMCglmm result.

READS : Processed Data/experiments/prediction_outputs/
WRITES: Processed Data/experiments/figures/fig14_prediction.{png,pdf}
        and Results/figures/methods/ (same publish step as script 22)
"""

from __future__ import annotations

import json
import os
import shutil
from pathlib import Path

os.environ.setdefault("MPLCONFIGDIR", "/tmp/mplconfig")
Path(os.environ["MPLCONFIGDIR"]).mkdir(parents=True, exist_ok=True)

import matplotlib as mpl  # noqa: E402

mpl.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402
from matplotlib.lines import Line2D  # noqa: E402

BASE = Path("/scratch/dp23301/Thesis")
EXP = BASE / "Processed Data" / "experiments"
PRED = EXP / "prediction_outputs"
OUT = EXP / "figures"
OUT.mkdir(parents=True, exist_ok=True)

INK = "#1b1b1b"
MUTED = "#6e6e6e"
GRID = "#dcdcdc"

MODEL_LABELS = {
    "majority": "Majority class",
    "genus_prior": "Genus prior (no environment)",
    "logreg": "Logistic regression (PC1–PC10)",
    "random_forest": "Random forest (PC1–PC10)",
}
MODEL_COLOR = {
    "majority": "#9a9a9a",
    "genus_prior": "#b4622d",
    "logreg": "#2e4a7d",
    "random_forest": "#1f6f78",
}
ORDER = ["majority", "genus_prior", "logreg", "random_forest"]
GROUPED = "genus-grouped"
UNGROUPED = "ungrouped (leaky)"


def style_axis(ax):
    ax.set_facecolor("white")
    for side in ("top", "right"):
        ax.spines[side].set_visible(False)
    for side in ("left", "bottom"):
        ax.spines[side].set_color(GRID)
    ax.tick_params(colors=MUTED, labelsize=8.5)
    ax.xaxis.label.set_color(INK)
    ax.yaxis.label.set_color(INK)


def panel_a(ax, df):
    d = df[df.cv == GROUPED].set_index("model")
    ys = np.arange(len(ORDER))[::-1]
    for y, m in zip(ys, ORDER):
        r = d.loc[m]
        ax.plot([r.macro_f1_lo, r.macro_f1_hi], [y, y],
                color=MODEL_COLOR[m], lw=2.2, solid_capstyle="round", zorder=2)
        ax.plot(r.macro_f1, y, "o", ms=7, color=MODEL_COLOR[m],
                mec="white", mew=1.2, zorder=3)
        ax.text(r.macro_f1_hi + 0.012, y, f"{r.macro_f1:.3f}",
                va="center", ha="left", fontsize=8.5, color=INK)

    floor = d.loc["majority"].macro_f1
    ax.axvline(floor, color=MUTED, ls=":", lw=1.1, zorder=1)
    ax.set_yticks(ys)
    ax.set_yticklabels([MODEL_LABELS[m] for m in ORDER], fontsize=8.5)
    ax.set_xlabel("Macro-F₁ (5-fold, genus-grouped CV)", fontsize=9)
    # data-driven so the value labels never fall outside the axes
    ax.set_xlim(d.macro_f1_lo.min() - 0.05, d.macro_f1_hi.max() + 0.07)
    ax.set_ylim(-0.7, len(ORDER) - 0.3)
    ax.set_title("A  Environment barely beats the floor",
                 loc="left", fontsize=9.5, color=INK, fontweight="bold")
    ax.grid(axis="x", color=GRID, lw=0.6, zorder=0)
    ax.set_axisbelow(True)
    style_axis(ax)


def panel_b(ax, df, best_env):
    show = ["genus_prior", best_env]
    piv = df.pivot_table(index="model", columns="cv", values="macro_f1")
    ys = np.arange(len(show))[::-1]
    for y, m in zip(ys, show):
        lo, hi = piv.loc[m, GROUPED], piv.loc[m, UNGROUPED]
        ax.annotate("", xy=(hi, y), xytext=(lo, y),
                    arrowprops=dict(arrowstyle="-|>", color=MODEL_COLOR[m],
                                    lw=2.0, shrinkA=0, shrinkB=0))
        ax.plot(lo, y, "o", ms=7, color="white",
                mec=MODEL_COLOR[m], mew=2, zorder=3)
        ax.plot(hi, y, "o", ms=7, color=MODEL_COLOR[m],
                mec="white", mew=1.2, zorder=3)
        ax.text(lo - 0.015, y, f"{lo:.3f}", va="center", ha="right",
                fontsize=8.5, color=MUTED)
        ax.text(hi + 0.015, y, f"{hi:.3f}", va="center", ha="left",
                fontsize=8.5, color=INK)

    ax.set_yticks(ys)
    env_label = MODEL_LABELS[best_env].split(" (")[0]
    ax.set_yticklabels(["Genus prior", f"{env_label}\n(environment)"],
                       fontsize=8.5)
    ax.set_xlabel("Macro-F₁", fontsize=9)
    vals = piv.loc[show, [GROUPED, UNGROUPED]].to_numpy(dtype=float)
    ax.set_xlim(vals.min() - 0.10, vals.max() + 0.12)
    # headroom above the top row so the legend never sits on the data
    ax.set_ylim(-0.65, len(show) + 0.35)
    ax.set_title("B  Relatedness carries the signal",
                 loc="left", fontsize=9.5, color=INK, fontweight="bold")
    ax.legend(handles=[
        Line2D([], [], marker="o", ls="none", mfc="white", mec=INK, mew=2,
               ms=6.5, label="genus-grouped CV"),
        Line2D([], [], marker="o", ls="none", color=INK, ms=6.5,
               label="ungrouped CV (genus leaks)"),
    ], fontsize=7.6, frameon=False, loc="upper center",
        bbox_to_anchor=(0.5, 1.02), ncol=2, columnspacing=1.1,
        handletextpad=0.4)
    ax.grid(axis="x", color=GRID, lw=0.6, zorder=0)
    ax.set_axisbelow(True)
    style_axis(ax)


def panel_c(ax, pi):
    pi = pi.sort_values("importance_mean")
    ys = np.arange(len(pi))
    for y, (_, r) in zip(ys, pi.iterrows()):
        lead = r.variable == "PC2"
        col = "#1f6f78" if lead else "#b9b9b9"
        ax.plot([0, r.importance_mean], [y, y], color=col, lw=1.8, zorder=2)
        ax.plot(r.importance_mean, y, "o", ms=6 if lead else 4.5,
                color=col, mec="white", mew=1.0, zorder=3)
    ax.axvline(0, color=MUTED, lw=0.9, zorder=1)
    ax.set_yticks(ys)
    ax.set_yticklabels(pi.variable, fontsize=8.5)
    ax.set_xlabel("Drop in macro-F₁ when permuted", fontsize=9)
    ax.set_title("C  PC2 is the only useful axis",
                 loc="left", fontsize=9.5, color=INK, fontweight="bold")
    ax.grid(axis="x", color=GRID, lw=0.6, zorder=0)
    ax.set_axisbelow(True)
    style_axis(ax)


def main():
    df = pd.read_csv(PRED / "prediction_cv_summary.csv")
    pi = pd.read_csv(PRED / "prediction_permutation_importance.csv")
    meta = json.loads((PRED / "prediction_run_metadata.json").read_text())
    best_env = meta["best_env_model_grouped"]

    # every number in the title/caption comes from the run, never hardcoded
    grouped = df[df.cv == GROUPED].set_index("model")
    floor_f1 = grouped.loc["majority", "macro_f1"]
    env_f1 = grouped.loc[best_env, "macro_f1"]
    env_balacc = grouped.loc[best_env, "balanced_accuracy"]
    chance_balacc = grouped.loc["majority", "balanced_accuracy"]
    genus_f1 = df[(df.cv == UNGROUPED) & (df.model == "genus_prior")].macro_f1.iat[0]
    # how much further above the majority floor relatedness gets us
    ratio = (genus_f1 - floor_f1) / (env_f1 - floor_f1)
    top_axis = pi.sort_values("importance_mean", ascending=False).variable.iat[0]

    fig = plt.figure(figsize=(13.4, 4.8))
    gs = fig.add_gridspec(1, 3, width_ratios=[1.15, 1.0, 0.8],
                          wspace=0.62, left=0.145, right=0.985,
                          top=0.78, bottom=0.27)
    panel_a(fig.add_subplot(gs[0, 0]), df)
    panel_b(fig.add_subplot(gs[0, 1]), df, best_env)
    panel_c(fig.add_subplot(gs[0, 2]), pi)

    fig.suptitle(
        "Predicting flower colour from environment "
        f"(n = {meta['n_species']:,} species, {meta['n_genera']} genera)",
        x=0.008, ha="left", fontsize=11.5, fontweight="bold", color=INK, y=0.97,
    )
    fig.text(
        0.008, 0.035,
        "Colour–environment associations are statistically robust but weakly "
        f"predictive: the best environment model reaches balanced accuracy "
        f"{env_balacc:.3f} against a {chance_balacc:.3f} chance floor.\n"
        f"Knowing a species' genus lifts macro-F₁ {ratio:.1f}× further above the "
        "majority floor than its entire climate and soil niche, and "
        f"{top_axis} is the only informative axis — independently reproducing the "
        "MCMCglmm result.",
        ha="left", va="bottom", fontsize=8.2, color=MUTED,
    )

    publish = BASE / "Results" / "figures" / "methods"
    publish.mkdir(parents=True, exist_ok=True)
    for ext in ("png", "pdf"):
        fig.savefig(OUT / f"fig14_prediction.{ext}", dpi=400,
                    facecolor="white", bbox_inches=None)
        shutil.copyfile(OUT / f"fig14_prediction.{ext}",
                        publish / f"fig14_prediction.{ext}")
    plt.close(fig)
    print(f"Saved {OUT}/fig14_prediction.png and .pdf")
    print(f"Published to {publish}")


if __name__ == "__main__":
    main()
