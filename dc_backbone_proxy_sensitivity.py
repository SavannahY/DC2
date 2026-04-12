#!/usr/bin/env python3
"""Robustness study for key proxy efficiency assumptions.

This script stress-tests the relative ranking of Scenario 2 / 3 and
Scenario 2(M) / 3(M) under additive efficiency offsets applied to the most
important proxy curves in the advanced architectures.
"""

from __future__ import annotations

import argparse
import json
from itertools import product
from pathlib import Path

from dc_backbone_model import evaluate_path, find_architecture, load_json
from dc_backbone_multinode_campus_model import (
    architecture_for_multinode,
    evaluate_multinode_case,
    load_topology,
)


DEFAULT_ASSUMPTIONS_PATH = Path(__file__).resolve().parent / "scientific_assumptions_v1.json"
DEFAULT_TOPOLOGY_PATH = Path(__file__).resolve().parent / "multinode_campus_topology.json"
DEFAULT_OUTPUT_PATH = Path(__file__).resolve().parent / "proxy_sensitivity_report.json"


def apply_curve_offset(points: list[list[float]], delta_efficiency: float) -> list[list[float]]:
    adjusted = []
    for load_ratio, efficiency in points:
        new_efficiency = max(0.50, min(0.999, float(efficiency) + delta_efficiency))
        adjusted.append([float(load_ratio), new_efficiency])
    return adjusted


def clone_assumptions_with_offsets(assumptions: dict, offsets: dict[str, float]) -> dict:
    cloned = json.loads(json.dumps(assumptions))
    for curve_name, delta in offsets.items():
        cloned["curves"][curve_name]["points"] = apply_curve_offset(
            cloned["curves"][curve_name]["points"], delta
        )
    return cloned


def scenario_efficiency(assumptions: dict, architecture_name: str, delivered_it_mw: float) -> float:
    architecture = find_architecture(assumptions, architecture_name)
    source_mw = evaluate_path(architecture["elements"], assumptions, delivered_it_mw)["upstream_input_mw"]
    return delivered_it_mw / source_mw


def scenario_multinode_efficiency(assumptions: dict, topology: dict, architecture_name: str) -> float:
    campus_architecture = architecture_for_multinode(assumptions, architecture_name)
    _, blocks = build_network_for_architecture(assumptions, topology, architecture_name)
    result = evaluate_multinode_case(
        assumptions,
        topology,
        campus_architecture,
        {block.name: block.it_load_mw for block in blocks},
    )
    return result["total_efficiency"]


def build_network_for_architecture(assumptions: dict, topology: dict, architecture_name: str):
    from dc_backbone_multinode_campus_model import build_network

    campus_architecture = architecture_for_multinode(assumptions, architecture_name)
    return build_network(topology, campus_architecture, assumptions)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Stress-test proxy assumptions in the advanced DC-backbone models.")
    parser.add_argument("--assumptions", type=Path, default=DEFAULT_ASSUMPTIONS_PATH)
    parser.add_argument("--topology", type=Path, default=DEFAULT_TOPOLOGY_PATH)
    parser.add_argument("--save-json", type=Path, default=DEFAULT_OUTPUT_PATH)
    parser.add_argument(
        "--offset-grid",
        nargs="*",
        type=float,
        default=[-0.01, -0.005, 0.0, 0.005, 0.01],
        help="Additive efficiency offsets applied to key proxy curves (fractional units).",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    assumptions = load_json(args.assumptions)
    topology = load_topology(args.topology)
    delivered_it_mw = float(assumptions["global"]["base_it_load_mw"])

    cases = []
    single_path_s3_better = 0
    multinode_s3m_better = 0
    total_cases = 0
    break_even_cases = []

    for perimeter_offset, front_end_offset, dc_pod_offset in product(
        args.offset_grid, args.offset_grid, args.offset_grid
    ):
        offsets = {
            "perimeter_69kvac_to_800vdc": perimeter_offset,
            "central_mv_acdc": front_end_offset,
            "isolated_dc_pod": dc_pod_offset,
        }
        stressed = clone_assumptions_with_offsets(assumptions, offsets)

        s2_eff = scenario_efficiency(stressed, "ac_fed_sst_800vdc", delivered_it_mw)
        s3_eff = scenario_efficiency(stressed, "proposed_mvdc_backbone", delivered_it_mw)
        s2m_eff = scenario_multinode_efficiency(stressed, topology, "ac_fed_sst_800vdc")
        s3m_eff = scenario_multinode_efficiency(stressed, topology, "proposed_mvdc_backbone")

        total_cases += 1
        if s3_eff > s2_eff:
            single_path_s3_better += 1
        if s3m_eff > s2m_eff:
            multinode_s3m_better += 1

        case = {
            "offsets": offsets,
            "single_path": {
                "scenario2_efficiency": s2_eff,
                "scenario3_efficiency": s3_eff,
                "scenario3_beats_scenario2": s3_eff > s2_eff,
            },
            "multinode": {
                "scenario2m_efficiency": s2m_eff,
                "scenario3m_efficiency": s3m_eff,
                "scenario3m_beats_scenario2m": s3m_eff > s2m_eff,
            },
        }
        cases.append(case)
        if not case["single_path"]["scenario3_beats_scenario2"] or not case["multinode"]["scenario3m_beats_scenario2m"]:
            break_even_cases.append(case)

    report = {
        "description": "Additive efficiency-offset stress test for key proxy curves in Scenario 2 and Scenario 3.",
        "offset_grid": args.offset_grid,
        "curve_names": [
            "perimeter_69kvac_to_800vdc",
            "central_mv_acdc",
            "isolated_dc_pod",
        ],
        "total_cases": total_cases,
        "single_path_scenario3_better_fraction": single_path_s3_better / total_cases,
        "multinode_scenario3m_better_fraction": multinode_s3m_better / total_cases,
        "non_dominant_cases": break_even_cases,
        "cases": cases,
    }
    args.save_json.write_text(json.dumps(report, indent=2), encoding="utf-8")

    print(f"Proxy stress-test cases: {total_cases}")
    print(f"Scenario 3 beats Scenario 2 in single-path model: {single_path_s3_better}/{total_cases}")
    print(f"Scenario 3(M) beats Scenario 2(M) in multi-node model: {multinode_s3m_better}/{total_cases}")
    print(f"Cases where dominance fails: {len(break_even_cases)}")


if __name__ == "__main__":
    main()
