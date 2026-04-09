#!/usr/bin/env python3
"""Generate a 3-scenario efficiency figure from the current model report."""
from __future__ import annotations

import json
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np


BASE_DIR = Path(__file__).resolve().parents[2]
FIG_DIR = Path(__file__).resolve().parents[1] / "figures"
REPORT_PATH = BASE_DIR / "source_backed_model_report.json"
OUTPUT_PATH = FIG_DIR / "fig2_cumulative_efficiency.png"


def load_report() -> dict:
    return json.loads(REPORT_PATH.read_text(encoding="utf-8"))


def scenario_short_name(name: str) -> str:
    mapping = {
        "Traditional AC-centric": "Scenario 1\nTraditional AC",
        "NVIDIA-style 69 kV AC -> 800 VDC perimeter conversion": "Scenario 2\n69 kV AC -> 800 VDC",
        "Proposed MVDC backbone": "Scenario 3\nMVDC Backbone",
    }
    return mapping.get(name, name)


def main() -> None:
    report = load_report()
    results = report["results"]

    scenario_names = [scenario_short_name(result["display_name"]) for result in results]
    full_eff = np.array([result["full_load_total_efficiency"] * 100.0 for result in results])
    annual_loss_gwh = np.array([result["annual_loss_mwh"] / 1000.0 for result in results])
    annual_cost_musd = np.array([result["annual_loss_cost_usd"] / 1e6 for result in results])

    delta_eff_pp = full_eff[2] - full_eff[0]
    delta_loss_gwh = annual_loss_gwh[0] - annual_loss_gwh[2]
    delta_cost_musd = annual_cost_musd[0] - annual_cost_musd[2]

    colors = ["#6B6B6B", "#1565C0", "#2E7D32"]
    edge_colors = ["#4A4A4A", "#0D47A1", "#1B5E20"]

    fig, ax = plt.subplots(figsize=(12, 6.8))
    fig.patch.set_facecolor("white")

    x = np.arange(len(scenario_names))
    bars = ax.bar(x, full_eff, color=colors, edgecolor=edge_colors, linewidth=1.4, width=0.6)

    for idx, bar in enumerate(bars):
        ax.text(
            bar.get_x() + bar.get_width() / 2,
            bar.get_height() + 0.55,
            f"{full_eff[idx]:.2f}%",
            ha="center",
            va="bottom",
            fontsize=14,
            fontweight="bold",
            color=edge_colors[idx],
        )
        ax.text(
            bar.get_x() + bar.get_width() / 2,
            78.2,
            f"Loss: {annual_loss_gwh[idx]:.2f} GWh/yr\nCost: ${annual_cost_musd[idx]:.2f}M/yr",
            ha="center",
            va="bottom",
            fontsize=10,
            color="#333333",
        )

    ax.annotate(
        f"Scenario 3 vs 1\n+{delta_eff_pp:.2f} pts\n-{delta_loss_gwh:.2f} GWh/yr\n-${delta_cost_musd:.2f}M/yr",
        xy=(2, full_eff[2]),
        xytext=(1.63, 88.4),
        fontsize=11.5,
        fontweight="bold",
        color="#1B5E20",
        ha="left",
        va="center",
        bbox=dict(boxstyle="round,pad=0.45", facecolor="#E8F5E9", edgecolor="#2E7D32", lw=1.5),
        arrowprops=dict(arrowstyle="->", color="#2E7D32", lw=1.5),
    )

    ax.set_xticks(x)
    ax.set_xticklabels(scenario_names, fontsize=12, fontweight="bold")
    ax.set_ylabel("Full-Load End-to-End Efficiency (%)", fontsize=13, fontweight="bold")
    ax.set_ylim(77.5, 100.5)
    ax.set_title("Scenario Comparison: End-to-End Full-Load Efficiency", fontsize=16, fontweight="bold")
    ax.grid(axis="y", alpha=0.25)
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)

    ax.text(
        0.99,
        0.015,
        "Source: source_backed_model_report.json (100 MW IT reference campus, April 2026)",
        transform=ax.transAxes,
        fontsize=8,
        color="gray",
        ha="right",
        style="italic",
    )

    plt.tight_layout()
    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    plt.savefig(OUTPUT_PATH, dpi=220, bbox_inches="tight", facecolor="white", edgecolor="none")
    plt.close()
    print(f"Efficiency chart saved to {OUTPUT_PATH}")


if __name__ == "__main__":
    main()
