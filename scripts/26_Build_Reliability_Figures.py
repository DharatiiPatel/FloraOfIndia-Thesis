#!/usr/bin/env python3
"""Reliability chapter figures. No fabricated MCMC: forest is skipped until
scripts/25_Reliability_Ecology.R has written reliability_mcmc_effects.csv.
"""

from __future__ import annotations

import csv
import json
import os
from pathlib import Path

os.environ.setdefault("MPLCONFIGDIR", "/tmp/mplconfig")
Path(os.environ["MPLCONFIGDIR"]).mkdir(parents=True, exist_ok=True)

import matplotlib as mpl  # noqa: E402

mpl.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
from matplotlib.patches import FancyBboxPatch  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
REL = ROOT / "Processed Data" / "experiments" / "reliability"
FIG = ROOT / "Results" / "figures" / "reliability"
TAB = ROOT / "Results" / "tables" / "reliability"
FIG.mkdir(parents=True, exist_ok=True)
TAB.mkdir(parents=True, exist_ok=True)

INK = "#1b1b1b"
MUTED = "#6e6e6e"


def _save(fig, stem: str) -> None:
    fig.savefig(FIG / f"{stem}.png", dpi=400, bbox_inches="tight")
    fig.savefig(FIG / f"{stem}.pdf", bbox_inches="tight")
    plt.close(fig)


def fig_pipeline() -> None:
    fig, ax = plt.subplots(figsize=(10.2, 3.2))
    ax.set_xlim(0, 10)
    ax.set_ylim(0, 3)
    ax.axis("off")
    boxes = [
        (0.15, 1.1, 1.7, 1.2, "Three LLM\nextractors"),
        (2.1, 1.1, 1.8, 1.2, "Fixed ecology\nspecies list"),
        (4.15, 1.1, 1.9, 1.2, "Agreement\n7B = 72B = Llama"),
        (6.3, 1.1, 1.8, 1.2, "Source-text\nvalidator"),
        (8.3, 1.1, 1.5, 1.2, "Ecology on\nhigh-conf."),
    ]
    for x, y, w, h, t in boxes:
        ax.add_patch(FancyBboxPatch(
            (x, y), w, h, boxstyle="round,pad=0.03,rounding_size=0.08",
            facecolor="#eef4f5", edgecolor="#1f6f78", linewidth=1.2,
        ))
        ax.text(x + w / 2, y + h / 2, t, ha="center", va="center",
                fontsize=8.5, color=INK)
    for i in range(len(boxes) - 1):
        x0 = boxes[i][0] + boxes[i][2]
        x1 = boxes[i + 1][0]
        ax.annotate("", xy=(x1 - 0.02, 1.7), xytext=(x0 + 0.02, 1.7),
                    arrowprops=dict(arrowstyle="->", color="#1f6f78", lw=1.4))
    ax.text(5, 0.35,
            "Keyword baseline is a benchmark only. UNKNOWN is never coded as not-white/yellow/redtype.\n"
            "High confidence = three-LLM agreement on a known class, using Qwen-7B labels in the ecology models.",
            ha="center", va="center", fontsize=7.5, color=MUTED)
    ax.set_title("Reliability protocol (not a new extractor)", fontsize=11,
                 color=INK, loc="left", pad=8)
    fig.tight_layout()
    _save(fig, "fig15_reliability_pipeline")


def fig_agreement(summary: dict, rows: list[dict]) -> None:
    n = summary["primary_ecology_n"]
    vals = [
        ("Ecology species", n),
        ("Three-LLM coverage", summary["three_llm_coverage_n"]),
        ("Known colour, all 3 LLMs", summary["common_known_support_n"]),
        ("High confidence (agree)", summary["high_confidence_n"]),
        ("Disagreement", summary["disagreement_n"]),
    ]
    fig, ax = plt.subplots(figsize=(7.2, 3.6))
    y = range(len(vals))[::-1]
    ax.barh(list(y), [v[1] for v in vals], color="#1f6f78", height=0.62)
    ax.set_yticks(list(y))
    ax.set_yticklabels([v[0] for v in vals], fontsize=9)
    ax.set_xlabel("Number of species")
    for yi, (_, v) in zip(y, vals):
        ax.text(v + max(8, n * 0.01), yi, str(v), va="center", fontsize=8, color=INK)
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)
    n_unsup = summary.get("unsupported_known_colour_n", 0)
    ax.set_title(
        f"Three-LLM overlap and confidence  |  unsupported 7B colours: {n_unsup}",
        fontsize=10, loc="left",
    )
    fig.tight_layout()
    _save(fig, "fig16_agreement_counts")

    # compact table
    tab_path = TAB / "agreement_validation_table.csv"
    with tab_path.open("w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["quantity", "n", "note"])
        w.writerow(["primary_ecology", n, "published 7B ecology set"])
        w.writerow(["three_llm_coverage", summary["three_llm_coverage_n"],
                    "72B and Llama exist (not fascicle-only increment)"])
        w.writerow(["common_known_support", summary["common_known_support_n"],
                    "all three LLMs give WHITE/YELLOW/REDTYPE; 7B label used"])
        w.writerow(["high_confidence", summary["high_confidence_n"],
                    "7B, 72B, Llama identical known class"])
        w.writerow(["disagreement", summary["disagreement_n"],
                    "descriptive only; not a third ecology model"])
        w.writerow(["unsupported_known_colour", n_unsup,
                    "7B known class, no floral-window colour evidence"])
        w.writerow(["wrong_context_evidence", summary.get("wrong_context_n", 0),
                    "colour near fruit/leaf/indument, not floral term"])
        w.writerow(["agreement_rate_on_coverage_known",
                    summary.get("agreement_rate_on_coverage_known", ""),
                    "among coverage rows where 7B is known"])


def fig_forest(effects_path: Path) -> None:
    with effects_path.open(encoding="utf-8") as f:
        rows = list(csv.DictReader(f))
    # order
    want = [
        ("WHITE", "PC2"), ("YELLOW", "PC2"), ("REDTYPE", "PC3"),
        ("WHITE", "alt_scaled"), ("YELLOW", "alt_scaled"), ("REDTYPE", "alt_scaled"),
    ]
    labels = []
    fig, ax = plt.subplots(figsize=(7.4, 5.2))
    y = 0
    yticks = []
    yticklabels = []
    for color, effect in want:
        for subset, col, marker in (
            ("common_known", "#2e4a7d", "o"),
            ("high_confidence", "#1f6f78", "s"),
        ):
            hit = [r for r in rows if r["color"] == color and r["effect"] == effect
                   and r["subset"] == subset]
            if not hit:
                continue
            r = hit[0]
            mean, lo, hi = float(r["mean"]), float(r["lower"]), float(r["upper"])
            ax.plot([lo, hi], [y, y], color=col, lw=1.6)
            ax.scatter([mean], [y], color=col, marker=marker, s=28, zorder=3)
            yticks.append(y)
            lab = f"{color} ~ {effect.replace('alt_scaled', 'elevation')}  ({subset}, n={r['n']})"
            yticklabels.append(lab)
            y -= 1
        y -= 0.35
    ax.axvline(0, color="#bbbbbb", lw=1)
    ax.set_yticks(yticks)
    ax.set_yticklabels(yticklabels, fontsize=7.5)
    ax.set_xlabel("Posterior mean and 95% CI (threshold MCMCglmm, genus RE)")
    ax.set_title("Fixed common support vs high-confidence subset", loc="left", fontsize=11)
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)
    fig.tight_layout()
    _save(fig, "fig17_reliability_forest")


def main() -> None:
    summary = json.loads((REL / "summary.json").read_text())
    with (REL / "species_reliability.csv").open(encoding="utf-8-sig") as f:
        rows = list(csv.DictReader(f))
    fig_pipeline()
    fig_agreement(summary, rows)
    effects = REL / "reliability_mcmc_effects.csv"
    if effects.exists():
        fig_forest(effects)
        print("wrote forest from", effects)
    else:
        print("SKIP forest: run Rscript scripts/25_Reliability_Ecology.R")
    print("figures ->", FIG)


if __name__ == "__main__":
    main()
