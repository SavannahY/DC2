#!/usr/bin/env python3
"""Scenario 3(M): multi-node MVDC backbone model for AI-factory campuses.

This file keeps the existing Scenario 3 path model intact in `dc_backbone_model.py`
and adds a separate network model in which a shared 69 kV DC backbone feeds
multiple DC-native data-center blocks.
"""

from __future__ import annotations

import argparse
import json
import math
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Sequence

from dc_backbone_model import HOURS_PER_YEAR, evaluate_path, find_architecture, load_json


DEFAULT_ASSUMPTIONS_PATH = Path(__file__).resolve().parent / "scientific_assumptions_v1.json"
DEFAULT_TOPOLOGY_PATH = Path(__file__).resolve().parent / "scenario3m_topology.json"


@dataclass(frozen=True)
class Segment:
    name: str
    from_node: str
    to_node: str
    length_m: float
    resistance_ohm_per_km: float
    circuits: int

    @property
    def loop_resistance_ohm(self) -> float:
        per_conductor = self.resistance_ohm_per_km * (self.length_m / 1000.0)
        return 2.0 * per_conductor / float(self.circuits)


@dataclass(frozen=True)
class Block:
    name: str
    tap_node: str
    leaf_node: str
    it_load_mw: float
    branch_segment_name: str


def format_pct(value: float) -> str:
    return f"{100.0 * value:.2f}%"


def format_gwh(value_mwh: float) -> str:
    return f"{value_mwh / 1000.0:.2f} GWh"


def format_money_millions(value_usd: float) -> str:
    return f"${value_usd / 1e6:.2f}M"


def format_table(rows: List[Sequence[str]]) -> str:
    widths = [max(len(str(cell)) for cell in column) for column in zip(*rows)]
    formatted = []
    for row_index, row in enumerate(rows):
        formatted_row = "  ".join(str(cell).ljust(width) for cell, width in zip(row, widths))
        formatted.append(formatted_row)
        if row_index == 0:
            formatted.append("  ".join("-" * width for width in widths))
    return "\n".join(formatted)


def load_topology(path: Path) -> dict:
    return load_json(path)


def scenario3_components(assumptions: dict) -> dict:
    architecture = find_architecture(assumptions, "proposed_mvdc_backbone")
    front_end_stage = architecture["elements"][0]

    for index, element in enumerate(architecture["elements"]):
        if element["type"] == "conductor" and element["name"] == "MVDC backbone":
            return {
                "architecture": architecture,
                "front_end_stage": front_end_stage,
                "backbone_template": element,
                "downstream_elements": architecture["elements"][index + 1 :],
            }

    raise ValueError("Scenario 3 must contain an MVDC backbone conductor")


def build_network(topology: dict, backbone_template: dict) -> tuple[list[Segment], list[Block]]:
    default_r = float(backbone_template["resistance_ohm_per_km"])
    default_circuits = int(backbone_template.get("circuits", 1))

    segments: List[Segment] = []
    blocks: List[Block] = []

    for record in topology["trunk_segments"]:
        segments.append(
            Segment(
                name=record["name"],
                from_node=record["from"],
                to_node=record["to"],
                length_m=float(record["length_m"]),
                resistance_ohm_per_km=float(record.get("resistance_ohm_per_km", default_r)),
                circuits=int(record.get("circuits", default_circuits)),
            )
        )

    for record in topology["blocks"]:
        block_name = record["name"]
        leaf_node = f"block::{block_name}"
        branch_name = f"{block_name}_tap"
        branch_circuits = int(record.get("branch_circuits", max(1, default_circuits // 2)))
        branch_resistance = float(record.get("branch_resistance_ohm_per_km", default_r))
        segments.append(
            Segment(
                name=branch_name,
                from_node=record["tap_node"],
                to_node=leaf_node,
                length_m=float(record["branch_length_m"]),
                resistance_ohm_per_km=branch_resistance,
                circuits=branch_circuits,
            )
        )
        blocks.append(
            Block(
                name=block_name,
                tap_node=record["tap_node"],
                leaf_node=leaf_node,
                it_load_mw=float(record["it_load_mw"]),
                branch_segment_name=branch_name,
            )
        )

    validate_radial_network(topology["source_node"], segments)
    return segments, blocks


def validate_radial_network(source_node: str, segments: Sequence[Segment]) -> None:
    parent_by_child: Dict[str, str] = {}
    nodes = {source_node}
    for segment in segments:
        nodes.add(segment.from_node)
        nodes.add(segment.to_node)
        if segment.to_node in parent_by_child:
            raise ValueError(f"Node '{segment.to_node}' has more than one upstream segment")
        parent_by_child[segment.to_node] = segment.name

    disconnected = [node for node in nodes if node != source_node and node not in parent_by_child]
    if disconnected:
        raise ValueError(f"Disconnected nodes without upstream segment: {', '.join(sorted(disconnected))}")


def block_tap_input_mw(downstream_elements: Sequence[dict], assumptions: dict, delivered_it_mw: float) -> dict:
    result = evaluate_path(list(downstream_elements), assumptions, delivered_it_mw)
    return {
        "tap_input_mw": result["upstream_input_mw"],
        "local_loss_mw": result["upstream_input_mw"] - delivered_it_mw,
        "element_results": result["element_results"],
    }


def solve_radial_dc_network(
    source_node: str,
    source_voltage_kv: float,
    segments: Sequence[Segment],
    block_power_by_leaf_mw: Dict[str, float],
    max_iterations: int = 200,
    tolerance_v: float = 1.0,
) -> dict:
    children: Dict[str, List[Segment]] = {}
    for segment in segments:
        children.setdefault(segment.from_node, []).append(segment)
    for node in children:
        children[node].sort(key=lambda item: item.name)

    source_voltage_v = source_voltage_kv * 1000.0
    node_voltage_v: Dict[str, float] = {source_node: source_voltage_v}

    all_nodes = {source_node}
    for segment in segments:
        all_nodes.add(segment.from_node)
        all_nodes.add(segment.to_node)
    for node in all_nodes:
        node_voltage_v.setdefault(node, source_voltage_v)

    min_voltage_v = 0.8 * source_voltage_v
    segment_current_a: Dict[str, float] = {}

    for _ in range(max_iterations):
        load_current_a: Dict[str, float] = {}
        for leaf_node, power_mw in block_power_by_leaf_mw.items():
            leaf_voltage = max(min_voltage_v, node_voltage_v[leaf_node])
            load_current_a[leaf_node] = power_mw * 1e6 / leaf_voltage

        next_segment_current_a: Dict[str, float] = {}

        def subtree_current(node: str) -> float:
            total = load_current_a.get(node, 0.0)
            for child_segment in children.get(node, []):
                child_total = subtree_current(child_segment.to_node)
                next_segment_current_a[child_segment.name] = child_total
                total += child_total
            return total

        subtree_current(source_node)

        next_voltage_v: Dict[str, float] = {source_node: source_voltage_v}

        def propagate(node: str) -> None:
            for child_segment in children.get(node, []):
                drop_v = next_segment_current_a[child_segment.name] * child_segment.loop_resistance_ohm
                next_voltage_v[child_segment.to_node] = next_voltage_v[node] - drop_v
                propagate(child_segment.to_node)

        propagate(source_node)

        max_delta_v = max(abs(next_voltage_v[node] - node_voltage_v[node]) for node in all_nodes)
        segment_current_a = next_segment_current_a
        node_voltage_v = {
            node: source_voltage_v if node == source_node else 0.5 * node_voltage_v[node] + 0.5 * next_voltage_v[node]
            for node in all_nodes
        }
        if max_delta_v <= tolerance_v:
            break
    else:
        raise RuntimeError("Scenario 3(M) DC network solver did not converge")

    segment_loss_mw = {
        segment.name: (segment_current_a[segment.name] ** 2) * segment.loop_resistance_ohm / 1e6
        for segment in segments
    }
    total_loss_mw = sum(segment_loss_mw.values())
    total_block_power_mw = sum(block_power_by_leaf_mw.values())

    return {
        "node_voltage_kv": {node: voltage / 1000.0 for node, voltage in node_voltage_v.items()},
        "segment_current_a": segment_current_a,
        "segment_loss_mw": segment_loss_mw,
        "source_output_mw": total_block_power_mw + total_loss_mw,
        "total_backbone_loss_mw": total_loss_mw,
    }


def evaluate_front_end_input_mw(front_end_stage: dict, assumptions: dict, dc_output_mw: float) -> float:
    return evaluate_path([front_end_stage], assumptions, dc_output_mw)["upstream_input_mw"]


def evaluate_multinode_case(
    assumptions: dict,
    topology: dict,
    scenario3: dict,
    block_it_loads_mw: Dict[str, float],
) -> dict:
    segments, blocks = build_network(topology, scenario3["backbone_template"])
    block_lookup = {block.name: block for block in blocks}

    block_power_by_leaf_mw: Dict[str, float] = {}
    block_rows = []
    total_it_mw = 0.0
    total_local_loss_mw = 0.0
    for block in blocks:
        delivered_it_mw = float(block_it_loads_mw.get(block.name, 0.0))
        total_it_mw += delivered_it_mw
        local = block_tap_input_mw(scenario3["downstream_elements"], assumptions, delivered_it_mw)
        total_local_loss_mw += local["local_loss_mw"]
        block_power_by_leaf_mw[block.leaf_node] = local["tap_input_mw"]
        block_rows.append(
            {
                "name": block.name,
                "tap_node": block.tap_node,
                "it_load_mw": delivered_it_mw,
                "tap_input_mw": local["tap_input_mw"],
                "local_loss_mw": local["local_loss_mw"],
            }
        )

    dc_network = solve_radial_dc_network(
        source_node=topology["source_node"],
        source_voltage_kv=float(topology["source_voltage_kv"]),
        segments=segments,
        block_power_by_leaf_mw=block_power_by_leaf_mw,
    )
    front_end_input_mw = evaluate_front_end_input_mw(
        scenario3["front_end_stage"], assumptions, dc_network["source_output_mw"]
    )
    front_end_loss_mw = front_end_input_mw - dc_network["source_output_mw"]

    block_node_voltage = {}
    for block in blocks:
        block_node_voltage[block.name] = dc_network["node_voltage_kv"][block.leaf_node]

    segment_rows = []
    for segment in segments:
        segment_rows.append(
            {
                "name": segment.name,
                "from_node": segment.from_node,
                "to_node": segment.to_node,
                "length_m": segment.length_m,
                "circuits": segment.circuits,
                "current_a": dc_network["segment_current_a"][segment.name],
                "loss_mw": dc_network["segment_loss_mw"][segment.name],
            }
        )

    min_block_voltage_kv = min(block_node_voltage.values()) if block_node_voltage else float(topology["source_voltage_kv"])
    source_voltage_kv = float(topology["source_voltage_kv"])
    total_loss_mw = front_end_loss_mw + dc_network["total_backbone_loss_mw"] + total_local_loss_mw
    total_efficiency = total_it_mw / front_end_input_mw if front_end_input_mw else 0.0

    return {
        "total_it_mw": total_it_mw,
        "front_end_ac_input_mw": front_end_input_mw,
        "front_end_loss_mw": front_end_loss_mw,
        "dc_source_output_mw": dc_network["source_output_mw"],
        "backbone_loss_mw": dc_network["total_backbone_loss_mw"],
        "local_block_loss_mw": total_local_loss_mw,
        "total_loss_mw": total_loss_mw,
        "total_efficiency": total_efficiency,
        "node_voltage_kv": dc_network["node_voltage_kv"],
        "block_node_voltage_kv": block_node_voltage,
        "min_block_voltage_pu": min_block_voltage_kv / source_voltage_kv,
        "segment_rows": segment_rows,
        "block_rows": block_rows,
        "block_tap_power_by_name_mw": {row["name"]: row["tap_input_mw"] for row in block_rows},
        "block_lookup": block_lookup,
    }


def build_expansion_cases(
    assumptions: dict,
    topology: dict,
    scenario3: dict,
    ordered_blocks: Sequence[Block],
) -> List[dict]:
    cases = []
    for count in range(1, len(ordered_blocks) + 1):
        active_blocks = ordered_blocks[:count]
        block_it = {block.name: block.it_load_mw for block in active_blocks}
        result = evaluate_multinode_case(assumptions, topology, scenario3, block_it)
        cases.append(
            {
                "active_blocks": [block.name for block in active_blocks],
                "total_it_mw": result["total_it_mw"],
                "front_end_ac_input_mw": result["front_end_ac_input_mw"],
                "efficiency": result["total_efficiency"],
                "backbone_loss_mw": result["backbone_loss_mw"],
                "min_block_voltage_pu": result["min_block_voltage_pu"],
            }
        )
    return cases


def dynamic_load_vectors(base_it_by_block: Dict[str, float], mode: str, amplitude_fraction: float) -> tuple[dict, dict]:
    if mode == "coherent_campus":
        high = {name: value * (1.0 + amplitude_fraction) for name, value in base_it_by_block.items()}
        low = {name: max(0.0, value * (1.0 - amplitude_fraction)) for name, value in base_it_by_block.items()}
        return high, low

    if mode == "largest_block_only":
        largest_name = max(base_it_by_block, key=base_it_by_block.get)
        high = dict(base_it_by_block)
        low = dict(base_it_by_block)
        high[largest_name] = base_it_by_block[largest_name] * (1.0 + amplitude_fraction)
        low[largest_name] = max(0.0, base_it_by_block[largest_name] * (1.0 - amplitude_fraction))
        return high, low

    raise ValueError(f"Unsupported dynamic mode: {mode}")


def build_dynamic_summary(assumptions: dict, topology: dict, scenario3: dict, base_case: dict, blocks: Sequence[Block]) -> List[dict]:
    dynamic_model = assumptions.get("dynamic_model", {})
    cases = dynamic_model.get("cases", [])
    if not cases:
        return []

    base_it_by_block = {block.name: block.it_load_mw for block in blocks}
    results = []
    for mode in ("coherent_campus", "largest_block_only"):
        for dynamic_case in cases:
            frequency_hz = float(dynamic_case["frequency_hz"])
            for amplitude_fraction in dynamic_case["amplitude_sweep_fraction"]:
                amplitude_fraction = float(amplitude_fraction)
                high_it, low_it = dynamic_load_vectors(base_it_by_block, mode, amplitude_fraction)
                high_case = evaluate_multinode_case(assumptions, topology, scenario3, high_it)
                low_case = evaluate_multinode_case(assumptions, topology, scenario3, low_it)

                source_peak_mw = max(
                    high_case["front_end_ac_input_mw"] - base_case["front_end_ac_input_mw"],
                    base_case["front_end_ac_input_mw"] - low_case["front_end_ac_input_mw"],
                )

                max_segment_current_swing_a = 0.0
                for base_segment in base_case["segment_rows"]:
                    name = base_segment["name"]
                    high_current = next(row["current_a"] for row in high_case["segment_rows"] if row["name"] == name)
                    low_current = next(row["current_a"] for row in low_case["segment_rows"] if row["name"] == name)
                    base_current = base_segment["current_a"]
                    max_segment_current_swing_a = max(
                        max_segment_current_swing_a,
                        abs(high_current - base_current),
                        abs(base_current - low_current),
                    )

                affected_blocks = list(base_it_by_block)
                if mode == "largest_block_only":
                    affected_blocks = [max(base_it_by_block, key=base_it_by_block.get)]

                distributed_buffer_peak_mw = 0.0
                for block_name in affected_blocks:
                    base_tap = base_case["block_tap_power_by_name_mw"][block_name]
                    high_tap = high_case["block_tap_power_by_name_mw"][block_name]
                    low_tap = low_case["block_tap_power_by_name_mw"][block_name]
                    distributed_buffer_peak_mw += max(high_tap - base_tap, base_tap - low_tap)
                distributed_buffer_energy_kwh = distributed_buffer_peak_mw / (2.0 * math.pi * frequency_hz) / 3.6

                results.append(
                    {
                        "mode": mode,
                        "case_name": dynamic_case["name"],
                        "frequency_hz": frequency_hz,
                        "it_amplitude_fraction": amplitude_fraction,
                        "source_peak_mw": source_peak_mw,
                        "source_peak_fraction_of_base_input": source_peak_mw / base_case["front_end_ac_input_mw"],
                        "max_segment_current_swing_a": max_segment_current_swing_a,
                        "distributed_buffer_peak_mw": distributed_buffer_peak_mw,
                        "distributed_buffer_energy_kwh": distributed_buffer_energy_kwh,
                    }
                )

    return results


def build_annual_summary(assumptions: dict, topology: dict, scenario3: dict, blocks: Sequence[Block]) -> dict:
    electricity_price = float(assumptions["global"]["electricity_price_per_mwh"])
    annual_input_mwh = 0.0
    annual_it_mwh = 0.0
    load_bin_rows = []
    for load_bin in assumptions["load_profile"]:
        scale = float(load_bin["load_fraction"])
        hours = HOURS_PER_YEAR * float(load_bin["hours_fraction"])
        block_it = {block.name: block.it_load_mw * scale for block in blocks}
        case = evaluate_multinode_case(assumptions, topology, scenario3, block_it)
        annual_input_mwh += case["front_end_ac_input_mw"] * hours
        annual_it_mwh += case["total_it_mw"] * hours
        load_bin_rows.append(
            {
                "name": load_bin["name"],
                "scale": scale,
                "hours": hours,
                "it_mw": case["total_it_mw"],
                "source_mw": case["front_end_ac_input_mw"],
                "loss_mw": case["total_loss_mw"],
                "efficiency": case["total_efficiency"],
            }
        )

    annual_loss_mwh = annual_input_mwh - annual_it_mwh
    return {
        "load_bins": load_bin_rows,
        "annual_it_mwh": annual_it_mwh,
        "annual_input_mwh": annual_input_mwh,
        "annual_loss_mwh": annual_loss_mwh,
        "annual_loss_cost_usd": annual_loss_mwh * electricity_price,
        "average_efficiency": annual_it_mwh / annual_input_mwh if annual_input_mwh else 0.0,
    }


def build_report(assumptions: dict, topology: dict) -> dict:
    scenario3 = scenario3_components(assumptions)
    _, ordered_blocks = build_network(topology, scenario3["backbone_template"])
    full_load = evaluate_multinode_case(
        assumptions,
        topology,
        scenario3,
        {block.name: block.it_load_mw for block in ordered_blocks},
    )
    annual = build_annual_summary(assumptions, topology, scenario3, ordered_blocks)
    expansion = build_expansion_cases(assumptions, topology, scenario3, ordered_blocks)
    dynamic = build_dynamic_summary(assumptions, topology, scenario3, full_load, ordered_blocks)

    equivalent_architecture = scenario3["architecture"]
    equivalent_single_path_input_mw = evaluate_path(
        equivalent_architecture["elements"], assumptions, full_load["total_it_mw"]
    )["upstream_input_mw"]
    equivalent_single_path_efficiency = full_load["total_it_mw"] / equivalent_single_path_input_mw

    block_count = len(ordered_blocks)
    return {
        "topology_name": topology["name"],
        "description": topology.get("description", ""),
        "scenario_label": "Scenario 3(M)",
        "source_voltage_kv": float(topology["source_voltage_kv"]),
        "block_count": block_count,
        "full_load": {
            "total_it_mw": full_load["total_it_mw"],
            "front_end_ac_input_mw": full_load["front_end_ac_input_mw"],
            "total_efficiency": full_load["total_efficiency"],
            "front_end_loss_mw": full_load["front_end_loss_mw"],
            "backbone_loss_mw": full_load["backbone_loss_mw"],
            "local_block_loss_mw": full_load["local_block_loss_mw"],
            "total_loss_mw": full_load["total_loss_mw"],
            "min_block_voltage_pu": full_load["min_block_voltage_pu"],
            "block_rows": full_load["block_rows"],
            "segment_rows": full_load["segment_rows"],
        },
        "annual_summary": annual,
        "expansion_cases": expansion,
        "dynamic_summary": dynamic,
        "equivalent_scenario3_reference": {
            "source_input_mw": equivalent_single_path_input_mw,
            "efficiency": equivalent_single_path_efficiency,
            "delta_efficiency_points_vs_scenario3m": 100.0 * (full_load["total_efficiency"] - equivalent_single_path_efficiency),
        },
    }


def print_summary(report: dict) -> None:
    full_load = report["full_load"]
    annual = report["annual_summary"]
    print(
        f"Scenario 3(M): {report['block_count']} DC-native blocks on a shared "
        f"{report['source_voltage_kv']:.1f} kV DC backbone"
    )
    print(
        f"Reference campus: {full_load['total_it_mw']:.1f} MW IT, "
        f"{format_pct(full_load['total_efficiency'])} full-load efficiency, "
        f"{format_gwh(annual['annual_loss_mwh'])} annual loss, "
        f"{format_money_millions(annual['annual_loss_cost_usd'])} annual loss cost"
    )
    print(
        f"Minimum full-load block voltage: {100.0 * full_load['min_block_voltage_pu']:.2f}% of nominal"
    )
    reference = report["equivalent_scenario3_reference"]
    print(
        "Equivalent single-path Scenario 3 reference: "
        f"{format_pct(reference['efficiency'])} full-load efficiency "
        f"({reference['delta_efficiency_points_vs_scenario3m']:+.2f} points vs Scenario 3(M))"
    )


def print_details(report: dict) -> None:
    full_load = report["full_load"]
    print("\nFull-load block summary")
    print("-----------------------")
    print(
        format_table(
            [
                ("Block", "Tap Node", "IT MW", "Tap Input MW", "Local Loss MW"),
                *[
                    (
                        row["name"],
                        row["tap_node"],
                        f"{row['it_load_mw']:.2f}",
                        f"{row['tap_input_mw']:.2f}",
                        f"{row['local_loss_mw']:.2f}",
                    )
                    for row in full_load["block_rows"]
                ],
            ]
        )
    )

    print("\nBackbone segment summary")
    print("------------------------")
    print(
        format_table(
            [
                ("Segment", "From", "To", "Length m", "Circuits", "Current A", "Loss MW"),
                *[
                    (
                        row["name"],
                        row["from_node"],
                        row["to_node"],
                        f"{row['length_m']:.1f}",
                        str(row["circuits"]),
                        f"{row['current_a']:.1f}",
                        f"{row['loss_mw']:.4f}",
                    )
                    for row in full_load["segment_rows"]
                ],
            ]
        )
    )

    print("\nExpansion cases")
    print("---------------")
    print(
        format_table(
            [
                ("Active Blocks", "Total IT MW", "Source MW", "Efficiency", "Backbone Loss MW", "Min Block Vpu"),
                *[
                    (
                        ", ".join(case["active_blocks"]),
                        f"{case['total_it_mw']:.1f}",
                        f"{case['front_end_ac_input_mw']:.2f}",
                        format_pct(case["efficiency"]),
                        f"{case['backbone_loss_mw']:.4f}",
                        f"{case['min_block_voltage_pu']:.4f}",
                    )
                    for case in report["expansion_cases"]
                ],
            ]
        )
    )

    print("\nDynamic campus events")
    print("---------------------")
    print(
        format_table(
            [
                (
                    "Mode",
                    "Case",
                    "Freq Hz",
                    "IT Amp",
                    "Source Peak MW",
                    "Source Peak %",
                    "Max Seg A",
                    "Buffer MW",
                    "Buffer kWh",
                ),
                *[
                    (
                        row["mode"],
                        row["case_name"],
                        f"{row['frequency_hz']:.1f}",
                        f"{100.0 * row['it_amplitude_fraction']:.1f}%",
                        f"{row['source_peak_mw']:.2f}",
                        f"{100.0 * row['source_peak_fraction_of_base_input']:.2f}%",
                        f"{row['max_segment_current_swing_a']:.1f}",
                        f"{row['distributed_buffer_peak_mw']:.2f}",
                        f"{row['distributed_buffer_energy_kwh']:.2f}",
                    )
                    for row in report["dynamic_summary"]
                ],
            ]
        )
    )


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Scenario 3(M) multi-node MVDC backbone model.")
    parser.add_argument(
        "--assumptions",
        type=Path,
        default=DEFAULT_ASSUMPTIONS_PATH,
        help="Path to the shared assumptions JSON.",
    )
    parser.add_argument(
        "--topology",
        type=Path,
        default=DEFAULT_TOPOLOGY_PATH,
        help="Path to the Scenario 3(M) topology JSON.",
    )
    parser.add_argument(
        "--details",
        action="store_true",
        help="Print detailed tables for blocks, segments, expansion, and dynamic events.",
    )
    parser.add_argument(
        "--save-json",
        type=Path,
        help="Optional output path for the machine-readable report JSON.",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    assumptions = load_json(args.assumptions)
    topology = load_topology(args.topology)
    report = build_report(assumptions, topology)
    print_summary(report)
    if args.details:
        print_details(report)
    if args.save_json:
        args.save_json.write_text(json.dumps(report, indent=2), encoding="utf-8")


if __name__ == "__main__":
    main()
