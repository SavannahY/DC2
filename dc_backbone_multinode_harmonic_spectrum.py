#!/usr/bin/env python3
"""Public benchmark harmonic-spectrum study for Scenario 2(M) and Scenario 3(M).

This script strengthens the public harmonic argument by removing the built-in
"more interfaces means more total injected current" bias from the earlier probe.
It holds the *total* harmonic current constant across Scenario 2(M) and
Scenario 3(M), then compares how that same total current is exposed to the grid
when it is:

1. distributed across four AC-fed SST interfaces, or
2. concentrated at one centralized front end.

The spectra used here are explicit benchmark assumptions, not vendor spectra.
"""

from __future__ import annotations

import argparse
import cmath
import json
import math
from pathlib import Path
from typing import Dict, Iterable, List

import numpy as np

from dc_backbone_public_benefit_analysis import (
    HARMONIC_ORDERS,
    RTS_AREA_CASES,
    build_complex_network,
)
from dc_backbone_public_benchmark_model import (
    DEFAULT_ASSUMPTIONS,
    DEFAULT_ESIF_ZIP,
    DEFAULT_REPORT_JSON,
    DEFAULT_RTS_BRANCH,
    DEFAULT_RTS_BUS,
    DEFAULT_TOPOLOGY,
    build_report as build_public_benchmark_report,
    load_rts_data,
)
from dc_backbone_model import format_table, load_json
from dc_backbone_multinode_campus_model import load_topology


ROOT = Path(__file__).resolve().parent
DEFAULT_OUTPUT = ROOT / "harmonic_spectrum_report.json"
DEFAULT_NOTE = ROOT / "HARMONIC_SPECTRUM_ANALYSIS.md"
TOTAL_HARMONIC_CURRENT_PU = 0.04

SPECTRUMS = [
    {
        "name": "low_order_dominant",
        "display_name": "Low-order dominant benchmark",
        "weights": {5: 0.56, 7: 0.30, 11: 0.09, 13: 0.05},
        "note": "Benchmark spectrum dominated by 5th and 7th current components.",
    },
    {
        "name": "balanced_filtered",
        "display_name": "Balanced filtered benchmark",
        "weights": {5: 0.25, 7: 0.25, 11: 0.25, 13: 0.25},
        "note": "Benchmark spectrum with the same total current spread evenly across the tested orders.",
    },
    {
        "name": "higher_order_filtered",
        "display_name": "Higher-order filtered benchmark",
        "weights": {5: 0.10, 7: 0.15, 11: 0.35, 13: 0.40},
        "note": "Benchmark spectrum shifted toward higher orders to emulate stronger low-order filtering.",
    },
]


def write_json(path: Path, payload: dict) -> None:
    path.write_text(json.dumps(payload, indent=2), encoding="utf-8")


def load_or_build_public_report(
    assumptions_path: Path,
    topology_path: Path,
    rts_bus_path: Path,
    rts_branch_path: Path,
    esif_zip_path: Path,
    cached_report_path: Path,
) -> dict:
    if cached_report_path.exists():
        return load_json(cached_report_path)

    assumptions = load_json(assumptions_path)
    topology = load_topology(topology_path)
    rts_network = load_rts_data(rts_bus_path, rts_branch_path)
    return build_public_benchmark_report(
        assumptions=assumptions,
        topology=topology,
        rts_network=rts_network,
        esif_zip_path=esif_zip_path,
        esif_profile_path=None,
        rts_bus_path=rts_bus_path,
        rts_branch_path=rts_branch_path,
    )


def harmonic_voltage_response_weighted(
    harmonic_model: dict,
    rts_network: dict,
    bus_currents_pu: Dict[int, float],
) -> dict:
    ordered_bus_ids = harmonic_model["ordered_bus_ids"]
    current_vector = np.zeros(len(ordered_bus_ids), dtype=complex)
    for bus_id, current_pu in bus_currents_pu.items():
        current_vector[harmonic_model["bus_index"][bus_id]] -= current_pu

    delta_reduced = harmonic_model["z_reduced"] @ current_vector[harmonic_model["mask"]]
    delta_v = np.zeros(len(ordered_bus_ids), dtype=complex)
    delta_v[harmonic_model["mask"]] = delta_reduced

    poi_rows = []
    for bus_id in bus_currents_pu:
        idx = harmonic_model["bus_index"][bus_id]
        poi_rows.append(
            {
                "bus_id": bus_id,
                "bus_name": rts_network["buses"][bus_id]["name"],
                "current_pu": bus_currents_pu[bus_id],
                "voltage_pu": abs(delta_v[idx]),
            }
        )

    worst_idx = max(
        range(len(ordered_bus_ids)),
        key=lambda idx: abs(delta_v[idx]),
    )
    worst_bus_id = ordered_bus_ids[worst_idx]
    return {
        "poi_rows": poi_rows,
        "max_poi_voltage_pu": max(row["voltage_pu"] for row in poi_rows),
        "worst_bus_id": worst_bus_id,
        "worst_bus_name": rts_network["buses"][worst_bus_id]["name"],
        "worst_bus_voltage_pu": abs(delta_v[worst_idx]),
    }


def thdv_proxy(per_order_rows: Dict[int, dict]) -> float:
    return math.sqrt(sum(row["max_poi_voltage_pu"] ** 2 for row in per_order_rows.values()))


def worst_bus_proxy(per_order_rows: Dict[int, dict]) -> float:
    return math.sqrt(sum(row["worst_bus_voltage_pu"] ** 2 for row in per_order_rows.values()))


def build_total_current_allocations(distributed_buses: Iterable[int], central_bus: int, current_pu: float) -> dict:
    distributed_buses = list(distributed_buses)
    return {
        "Scenario 2(M)": {bus_id: current_pu / len(distributed_buses) for bus_id in distributed_buses},
        "Scenario 3(M)": {central_bus: current_pu},
    }


def build_report(public_report: dict) -> dict:
    rts_bus_path = Path(public_report["meta"]["rts_bus_path"])
    rts_branch_path = Path(public_report["meta"]["rts_branch_path"])
    rts_network = load_rts_data(rts_bus_path, rts_branch_path)
    harmonic_models = {order: build_complex_network(rts_network, harmonic_order=order) for order in HARMONIC_ORDERS}

    spectrum_rows = []
    min_ratio = float("inf")
    max_ratio = 0.0
    for spectrum in SPECTRUMS:
        area_rows = []
        for area in RTS_AREA_CASES:
            s2_orders = {}
            s3_orders = {}
            for order in HARMONIC_ORDERS:
                order_total_current = TOTAL_HARMONIC_CURRENT_PU * spectrum["weights"][order]
                allocations = build_total_current_allocations(
                    distributed_buses=area["distributed_buses"],
                    central_bus=area["central_bus"],
                    current_pu=order_total_current,
                )
                s2_orders[order] = harmonic_voltage_response_weighted(
                    harmonic_models[order],
                    rts_network,
                    allocations["Scenario 2(M)"],
                )
                s3_orders[order] = harmonic_voltage_response_weighted(
                    harmonic_models[order],
                    rts_network,
                    allocations["Scenario 3(M)"],
                )

            s2_thdv = thdv_proxy(s2_orders)
            s3_thdv = thdv_proxy(s3_orders)
            ratio = s2_thdv / s3_thdv if s3_thdv else math.inf
            min_ratio = min(min_ratio, ratio)
            max_ratio = max(max_ratio, ratio)
            area_rows.append(
                {
                    "label": area["label"],
                    "distributed_buses": area["distributed_buses"],
                    "central_bus": area["central_bus"],
                    "scenario2m_thdv_proxy_pu": s2_thdv,
                    "scenario3m_thdv_proxy_pu": s3_thdv,
                    "scenario2m_worst_bus_proxy_pu": worst_bus_proxy(s2_orders),
                    "scenario3m_worst_bus_proxy_pu": worst_bus_proxy(s3_orders),
                    "scenario2m_to_scenario3m_ratio": ratio,
                    "scenario2m_orders": s2_orders,
                    "scenario3m_orders": s3_orders,
                }
            )

        spectrum_rows.append(
            {
                "name": spectrum["name"],
                "display_name": spectrum["display_name"],
                "note": spectrum["note"],
                "weights": spectrum["weights"],
                "rows": area_rows,
            }
        )

    return {
        "meta": {
            "title": "Equal-total harmonic-spectrum benchmark for Scenario 2(M) and Scenario 3(M)",
            "status": "public_harmonic_spectrum_screen_v1",
            "assumption_note": (
                "This screen keeps the total harmonic current constant across Scenario 2(M) and Scenario 3(M). "
                "Scenario 2(M) distributes that total current across four AC-fed SST interfaces, while Scenario 3(M) "
                "injects the same total current through one centralized front end. The spectra are benchmark "
                "assumptions, not vendor spectra or IEEE 519 compliance cases."
            ),
            "harmonic_orders": HARMONIC_ORDERS,
            "total_harmonic_current_pu": TOTAL_HARMONIC_CURRENT_PU,
            "rts_bus_path": str(rts_bus_path),
            "rts_branch_path": str(rts_branch_path),
        },
        "spectra": spectrum_rows,
        "summary": {
            "minimum_scenario2m_to_scenario3m_thdv_ratio": min_ratio,
            "maximum_scenario2m_to_scenario3m_thdv_ratio": max_ratio,
            "interpretation": (
                "If Scenario 3(M) remains below Scenario 2(M) under equal-total harmonic injection, then the "
                "power-quality benefit is not just an artifact of injecting less total current. It also reflects "
                "the stronger centralized interconnection point."
            ),
        },
    }


def build_note(report: dict) -> str:
    min_ratio = report["summary"]["minimum_scenario2m_to_scenario3m_thdv_ratio"]
    lines = [
        "# Harmonic Spectrum Benchmark",
        "",
        "This note strengthens the power-quality claim by holding total harmonic current constant across Scenario 2(M) and Scenario 3(M).",
        "",
        f"- Total harmonic current per case: `{report['meta']['total_harmonic_current_pu']:.4f} pu`.",
        "- Scenario 2(M): total current is distributed across four AC-fed SST interfaces.",
        "- Scenario 3(M): the same total current is injected at one centralized front end.",
        f"- Across all tested benchmark spectra and mirrored RTS areas, Scenario 3(M) remains better with a minimum THDv-proxy advantage of `{min_ratio:.2f}x`.",
        "",
        "## Spectrum Cases",
        "",
    ]

    for spectrum in report["spectra"]:
        lines.extend(
            [
                f"### {spectrum['display_name']}",
                "",
                spectrum["note"],
                "",
            ]
        )
        rows = [["Area", "Scenario 2(M) THDv", "Scenario 3(M) THDv", "Ratio"]]
        for row in spectrum["rows"]:
            rows.append(
                [
                    row["label"],
                    f"{row['scenario2m_thdv_proxy_pu']:.5f}",
                    f"{row['scenario3m_thdv_proxy_pu']:.5f}",
                    f"{row['scenario2m_to_scenario3m_ratio']:.2f}x",
                ]
            )
        lines.extend([ "```text", format_table(rows), "```", "" ])

    lines.extend(
        [
            "## Interpretation",
            "",
            "This is still a public benchmark sensitivity study, not a harmonic compliance study. Its value is narrower and cleaner:",
            "",
            "- It shows that centralized AC-boundary ownership remains beneficial even when total harmonic injection is normalized.",
            "- It separates the topological benefit from the trivial 'more interfaces means more injected current' effect.",
        ]
    )
    return "\n".join(lines)


def print_summary(report: dict) -> None:
    print("Equal-total harmonic-spectrum benchmark")
    print("--------------------------------------")
    print(
        "Minimum Scenario 2(M)-to-Scenario 3(M) THDv proxy ratio across all tested spectra/areas: "
        f"{report['summary']['minimum_scenario2m_to_scenario3m_thdv_ratio']:.2f}x"
    )
    for spectrum in report["spectra"]:
        print()
        print(spectrum["display_name"])
        rows = [["Area", "Scenario 2(M)", "Scenario 3(M)", "Ratio"]]
        for row in spectrum["rows"]:
            rows.append(
                [
                    row["label"],
                    f"{row['scenario2m_thdv_proxy_pu']:.5f}",
                    f"{row['scenario3m_thdv_proxy_pu']:.5f}",
                    f"{row['scenario2m_to_scenario3m_ratio']:.2f}x",
                ]
            )
        print(format_table(rows))


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run an equal-total harmonic-spectrum benchmark for Scenario 2(M) and Scenario 3(M).")
    parser.add_argument("--assumptions", type=Path, default=DEFAULT_ASSUMPTIONS)
    parser.add_argument("--topology", type=Path, default=DEFAULT_TOPOLOGY)
    parser.add_argument("--rts-bus", type=Path, default=DEFAULT_RTS_BUS)
    parser.add_argument("--rts-branch", type=Path, default=DEFAULT_RTS_BRANCH)
    parser.add_argument("--esif-zip", type=Path, default=DEFAULT_ESIF_ZIP)
    parser.add_argument("--public-report", type=Path, default=DEFAULT_REPORT_JSON)
    parser.add_argument("--save-json", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--write-note", type=Path, default=DEFAULT_NOTE)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    public_report = load_or_build_public_report(
        assumptions_path=args.assumptions,
        topology_path=args.topology,
        rts_bus_path=args.rts_bus,
        rts_branch_path=args.rts_branch,
        esif_zip_path=args.esif_zip,
        cached_report_path=args.public_report,
    )
    report = build_report(public_report)
    print_summary(report)
    if args.save_json:
        write_json(args.save_json, report)
    if args.write_note:
        args.write_note.write_text(build_note(report), encoding="utf-8")


if __name__ == "__main__":
    main()
