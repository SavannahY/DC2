#!/usr/bin/env python3
"""Apples-to-apples multi-node campus comparison for Scenario 1(M), 2(M), and 3(M)."""

from __future__ import annotations

import argparse
import json
import math
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Sequence

from dc_backbone_model import (
    HOURS_PER_YEAR,
    evaluate_path,
    find_architecture,
    get_opendss_validation_settings,
    load_json,
)


DEFAULT_ASSUMPTIONS_PATH = Path(__file__).resolve().parent / "scientific_assumptions_v1.json"
DEFAULT_TOPOLOGY_PATH = Path(__file__).resolve().parent / "multinode_campus_topology.json"

ARCHITECTURE_ORDER = [
    "traditional_ac",
    "ac_fed_sst_800vdc",
    "proposed_mvdc_backbone",
]


@dataclass(frozen=True)
class Segment:
    name: str
    from_node: str
    to_node: str
    kind: str
    length_m: float
    resistance_ohm_per_km: float
    circuits: int
    reactance_ohm_per_km: float = 0.0

    @property
    def effective_r_ohm(self) -> float:
        return self.resistance_ohm_per_km * (self.length_m / 1000.0) / float(self.circuits)

    @property
    def effective_x_ohm(self) -> float:
        return self.reactance_ohm_per_km * (self.length_m / 1000.0) / float(self.circuits)

    @property
    def effective_loop_r_ohm(self) -> float:
        return 2.0 * self.resistance_ohm_per_km * (self.length_m / 1000.0) / float(self.circuits)


@dataclass(frozen=True)
class Block:
    name: str
    tap_node: str
    leaf_node: str
    it_load_mw: float
    branch_segment_name: str


@dataclass(frozen=True)
class CampusArchitecture:
    name: str
    display_name: str
    kind: str
    source_voltage_kv: float
    source_stage_elements: Sequence[dict]
    backbone_template: dict
    local_block_elements: Sequence[dict]


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
        formatted.append("  ".join(str(cell).ljust(width) for cell, width in zip(row, widths)))
        if row_index == 0:
            formatted.append("  ".join("-" * width for width in widths))
    return "\n".join(formatted)


def load_topology(path: Path) -> dict:
    return load_json(path)


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


def architecture_for_multinode(assumptions: dict, architecture_name: str) -> CampusArchitecture:
    architecture = find_architecture(assumptions, architecture_name)

    if architecture_name == "proposed_mvdc_backbone":
        source_stage_elements = architecture["elements"][:1]
        backbone_template = architecture["elements"][1]
        local_block_elements = architecture["elements"][2:]
        kind = "dc"
    else:
        source_stage_elements = []
        backbone_template = architecture["elements"][0]
        local_block_elements = architecture["elements"][1:]
        kind = "ac"

    return CampusArchitecture(
        name=architecture["name"],
        display_name=architecture["display_name"],
        kind=kind,
        source_voltage_kv=float(backbone_template["voltage_kv"]),
        source_stage_elements=source_stage_elements,
        backbone_template=backbone_template,
        local_block_elements=local_block_elements,
    )


def build_network(
    topology: dict,
    campus_architecture: CampusArchitecture,
    assumptions: dict,
) -> tuple[list[Segment], list[Block]]:
    settings = get_opendss_validation_settings(assumptions)
    default_r = float(campus_architecture.backbone_template["resistance_ohm_per_km"])
    default_circuits = int(campus_architecture.backbone_template.get("circuits", 1))
    default_x = 0.0
    if campus_architecture.kind == "ac":
        default_x = default_r * float(settings.get("line_x_to_r_ratio", 1.0))

    segments: List[Segment] = []
    blocks: List[Block] = []

    for record in topology["shared_segments"]:
        segments.append(
            Segment(
                name=record["name"],
                from_node=record["from"],
                to_node=record["to"],
                kind=campus_architecture.kind,
                length_m=float(record["length_m"]),
                resistance_ohm_per_km=float(record.get("resistance_ohm_per_km", default_r)),
                circuits=int(record.get("circuits", default_circuits)),
                reactance_ohm_per_km=float(record.get("reactance_ohm_per_km", default_x)),
            )
        )

    for record in topology["blocks"]:
        branch_name = f"{record['name']}_tap"
        leaf_node = f"block::{record['name']}"
        segments.append(
            Segment(
                name=branch_name,
                from_node=record["tap_node"],
                to_node=leaf_node,
                kind=campus_architecture.kind,
                length_m=float(record["branch_length_m"]),
                resistance_ohm_per_km=float(record.get("branch_resistance_ohm_per_km", default_r)),
                circuits=int(record.get("branch_circuits", max(1, default_circuits // 2))),
                reactance_ohm_per_km=float(record.get("branch_reactance_ohm_per_km", default_x)),
            )
        )
        blocks.append(
            Block(
                name=record["name"],
                tap_node=record["tap_node"],
                leaf_node=leaf_node,
                it_load_mw=float(record["it_load_mw"]),
                branch_segment_name=branch_name,
            )
        )

    validate_radial_network(topology["source_node"], segments)
    return segments, blocks


def block_tap_input_mw(local_block_elements: Sequence[dict], assumptions: dict, delivered_it_mw: float) -> dict:
    result = evaluate_path(list(local_block_elements), assumptions, delivered_it_mw)
    return {
        "tap_input_mw": result["upstream_input_mw"],
        "local_loss_mw": result["upstream_input_mw"] - delivered_it_mw,
        "element_results": result["element_results"],
    }


def evaluate_source_stage_input_mw(source_stage_elements: Sequence[dict], assumptions: dict, delivered_mw: float) -> float:
    if not source_stage_elements:
        return delivered_mw
    return evaluate_path(list(source_stage_elements), assumptions, delivered_mw)["upstream_input_mw"]


def solve_radial_dc_network(
    source_node: str,
    source_voltage_kv: float,
    segments: Sequence[Segment],
    load_power_by_leaf_mw: Dict[str, float],
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
        load_current_a = {}
        for leaf_node, power_mw in load_power_by_leaf_mw.items():
            leaf_voltage = max(min_voltage_v, node_voltage_v[leaf_node])
            load_current_a[leaf_node] = power_mw * 1e6 / leaf_voltage

        next_segment_current_a: Dict[str, float] = {}

        def subtree_current(node: str) -> float:
            total = load_current_a.get(node, 0.0)
            for child in children.get(node, []):
                child_total = subtree_current(child.to_node)
                next_segment_current_a[child.name] = child_total
                total += child_total
            return total

        subtree_current(source_node)

        next_voltage_v = {source_node: source_voltage_v}

        def propagate(node: str) -> None:
            for child in children.get(node, []):
                drop_v = next_segment_current_a[child.name] * child.effective_loop_r_ohm
                next_voltage_v[child.to_node] = next_voltage_v[node] - drop_v
                propagate(child.to_node)

        propagate(source_node)

        max_delta = max(abs(next_voltage_v[node] - node_voltage_v[node]) for node in all_nodes)
        segment_current_a = next_segment_current_a
        node_voltage_v = {
            node: source_voltage_v if node == source_node else 0.5 * node_voltage_v[node] + 0.5 * next_voltage_v[node]
            for node in all_nodes
        }
        if max_delta <= tolerance_v:
            break
    else:
        raise RuntimeError("DC radial network solver did not converge")

    segment_loss_mw = {
        segment.name: (segment_current_a[segment.name] ** 2) * segment.effective_loop_r_ohm / 1e6
        for segment in segments
    }
    total_loss_mw = sum(segment_loss_mw.values())

    return {
        "node_voltage_kv": {node: value / 1000.0 for node, value in node_voltage_v.items()},
        "segment_current_a": segment_current_a,
        "segment_loss_mw": segment_loss_mw,
        "network_source_output_mw": sum(load_power_by_leaf_mw.values()) + total_loss_mw,
        "network_loss_mw": total_loss_mw,
    }


def solve_radial_ac_network(
    source_node: str,
    source_voltage_kv: float,
    segments: Sequence[Segment],
    load_power_by_leaf_mw: Dict[str, float],
    power_factor: float,
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
    sin_phi = math.sqrt(max(0.0, 1.0 - power_factor * power_factor))

    for _ in range(max_iterations):
        load_current_a = {}
        for leaf_node, power_mw in load_power_by_leaf_mw.items():
            leaf_voltage = max(min_voltage_v, node_voltage_v[leaf_node])
            load_current_a[leaf_node] = power_mw * 1e6 / (math.sqrt(3.0) * leaf_voltage * power_factor)

        next_segment_current_a: Dict[str, float] = {}

        def subtree_current(node: str) -> float:
            total = load_current_a.get(node, 0.0)
            for child in children.get(node, []):
                child_total = subtree_current(child.to_node)
                next_segment_current_a[child.name] = child_total
                total += child_total
            return total

        subtree_current(source_node)

        next_voltage_v = {source_node: source_voltage_v}

        def propagate(node: str) -> None:
            for child in children.get(node, []):
                drop_v = math.sqrt(3.0) * next_segment_current_a[child.name] * (
                    child.effective_r_ohm * power_factor + child.effective_x_ohm * sin_phi
                )
                next_voltage_v[child.to_node] = next_voltage_v[node] - drop_v
                propagate(child.to_node)

        propagate(source_node)

        max_delta = max(abs(next_voltage_v[node] - node_voltage_v[node]) for node in all_nodes)
        segment_current_a = next_segment_current_a
        node_voltage_v = {
            node: source_voltage_v if node == source_node else 0.5 * node_voltage_v[node] + 0.5 * next_voltage_v[node]
            for node in all_nodes
        }
        if max_delta <= tolerance_v:
            break
    else:
        raise RuntimeError("AC radial network solver did not converge")

    segment_loss_mw = {
        segment.name: 3.0 * (segment_current_a[segment.name] ** 2) * segment.effective_r_ohm / 1e6
        for segment in segments
    }
    total_loss_mw = sum(segment_loss_mw.values())

    return {
        "node_voltage_kv": {node: value / 1000.0 for node, value in node_voltage_v.items()},
        "segment_current_a": segment_current_a,
        "segment_loss_mw": segment_loss_mw,
        "network_source_output_mw": sum(load_power_by_leaf_mw.values()) + total_loss_mw,
        "network_loss_mw": total_loss_mw,
    }


def evaluate_multinode_case(
    assumptions: dict,
    topology: dict,
    campus_architecture: CampusArchitecture,
    block_it_loads_mw: Dict[str, float],
) -> dict:
    segments, blocks = build_network(topology, campus_architecture, assumptions)
    default_pf = float(assumptions["global"].get("default_power_factor", 0.98))

    block_rows = []
    load_power_by_leaf_mw: Dict[str, float] = {}
    total_it_mw = 0.0
    total_local_loss_mw = 0.0

    for block in blocks:
        delivered_it_mw = float(block_it_loads_mw.get(block.name, 0.0))
        total_it_mw += delivered_it_mw
        local = block_tap_input_mw(campus_architecture.local_block_elements, assumptions, delivered_it_mw)
        total_local_loss_mw += local["local_loss_mw"]
        load_power_by_leaf_mw[block.leaf_node] = local["tap_input_mw"]
        block_rows.append(
            {
                "name": block.name,
                "tap_node": block.tap_node,
                "it_load_mw": delivered_it_mw,
                "tap_input_mw": local["tap_input_mw"],
                "local_loss_mw": local["local_loss_mw"],
            }
        )

    if campus_architecture.kind == "dc":
        network = solve_radial_dc_network(
            source_node=topology["source_node"],
            source_voltage_kv=campus_architecture.source_voltage_kv,
            segments=segments,
            load_power_by_leaf_mw=load_power_by_leaf_mw,
        )
    else:
        network = solve_radial_ac_network(
            source_node=topology["source_node"],
            source_voltage_kv=campus_architecture.source_voltage_kv,
            segments=segments,
            load_power_by_leaf_mw=load_power_by_leaf_mw,
            power_factor=default_pf,
        )

    source_input_mw = evaluate_source_stage_input_mw(
        campus_architecture.source_stage_elements,
        assumptions,
        network["network_source_output_mw"],
    )
    source_stage_loss_mw = source_input_mw - network["network_source_output_mw"]
    total_loss_mw = source_stage_loss_mw + network["network_loss_mw"] + total_local_loss_mw

    segment_rows = []
    for segment in segments:
        segment_rows.append(
            {
                "name": segment.name,
                "from_node": segment.from_node,
                "to_node": segment.to_node,
                "kind": segment.kind,
                "length_m": segment.length_m,
                "circuits": segment.circuits,
                "current_a": network["segment_current_a"][segment.name],
                "loss_mw": network["segment_loss_mw"][segment.name],
            }
        )

    block_node_voltage_kv = {
        row["name"]: network["node_voltage_kv"][f"block::{row['name']}"] for row in block_rows
    }

    return {
        "total_it_mw": total_it_mw,
        "source_input_mw": source_input_mw,
        "source_stage_loss_mw": source_stage_loss_mw,
        "network_source_output_mw": network["network_source_output_mw"],
        "network_loss_mw": network["network_loss_mw"],
        "local_block_loss_mw": total_local_loss_mw,
        "total_loss_mw": total_loss_mw,
        "total_efficiency": total_it_mw / source_input_mw if source_input_mw else 0.0,
        "segment_rows": segment_rows,
        "block_rows": block_rows,
        "block_node_voltage_kv": block_node_voltage_kv,
        "min_block_voltage_pu": min(block_node_voltage_kv.values()) / campus_architecture.source_voltage_kv,
        "block_tap_power_by_name_mw": {row["name"]: row["tap_input_mw"] for row in block_rows},
    }


def build_expansion_cases(
    assumptions: dict,
    topology: dict,
    campus_architecture: CampusArchitecture,
    ordered_blocks: Sequence[Block],
) -> List[dict]:
    cases = []
    for count in range(1, len(ordered_blocks) + 1):
        active_blocks = ordered_blocks[:count]
        result = evaluate_multinode_case(
            assumptions,
            topology,
            campus_architecture,
            {block.name: block.it_load_mw for block in active_blocks},
        )
        cases.append(
            {
                "active_blocks": [block.name for block in active_blocks],
                "total_it_mw": result["total_it_mw"],
                "source_input_mw": result["source_input_mw"],
                "efficiency": result["total_efficiency"],
                "network_loss_mw": result["network_loss_mw"],
                "min_block_voltage_pu": result["min_block_voltage_pu"],
            }
        )
    return cases


def dynamic_load_vectors(base_it_by_block: Dict[str, float], mode: str, amplitude_fraction: float) -> tuple[dict, dict]:
    block_names = list(base_it_by_block)
    if mode == "coherent_campus":
        high = {name: value * (1.0 + amplitude_fraction) for name, value in base_it_by_block.items()}
        low = {name: max(0.0, value * (1.0 - amplitude_fraction)) for name, value in base_it_by_block.items()}
        return high, low
    if mode == "largest_block_only":
        largest_name = max(base_it_by_block, key=base_it_by_block.get)
        high = dict(base_it_by_block)
        low = dict(base_it_by_block)
        high[largest_name] = high[largest_name] * (1.0 + amplitude_fraction)
        low[largest_name] = max(0.0, low[largest_name] * (1.0 - amplitude_fraction))
        return high, low
    if mode == "two_block_cluster":
        selected = block_names[: min(2, len(block_names))]
        high = dict(base_it_by_block)
        low = dict(base_it_by_block)
        for name in selected:
            high[name] = high[name] * (1.0 + amplitude_fraction)
            low[name] = max(0.0, low[name] * (1.0 - amplitude_fraction))
        return high, low
    if mode == "split_campus_opposition":
        midpoint = len(block_names) // 2
        positive = block_names[:midpoint]
        negative = block_names[midpoint:]
        high = dict(base_it_by_block)
        low = dict(base_it_by_block)
        for name in positive:
            high[name] = high[name] * (1.0 + amplitude_fraction)
            low[name] = max(0.0, low[name] * (1.0 - amplitude_fraction))
        for name in negative:
            high[name] = max(0.0, high[name] * (1.0 - amplitude_fraction))
            low[name] = low[name] * (1.0 + amplitude_fraction)
        return high, low
    if mode == "one_up_one_down":
        first = block_names[0]
        last = block_names[-1]
        high = dict(base_it_by_block)
        low = dict(base_it_by_block)
        high[first] = high[first] * (1.0 + amplitude_fraction)
        high[last] = max(0.0, high[last] * (1.0 - amplitude_fraction))
        low[first] = max(0.0, low[first] * (1.0 - amplitude_fraction))
        low[last] = low[last] * (1.0 + amplitude_fraction)
        return high, low
    raise ValueError(f"Unsupported dynamic mode: {mode}")


def build_dynamic_summary(
    assumptions: dict,
    topology: dict,
    campus_architecture: CampusArchitecture,
    base_case: dict,
    ordered_blocks: Sequence[Block],
) -> List[dict]:
    dynamic_model = assumptions.get("dynamic_model", {})
    cases = dynamic_model.get("cases", [])
    if not cases:
        return []

    base_it_by_block = {block.name: block.it_load_mw for block in ordered_blocks}
    rows = []
    for mode in (
        "coherent_campus",
        "largest_block_only",
        "two_block_cluster",
        "split_campus_opposition",
        "one_up_one_down",
    ):
        for dynamic_case in cases:
            frequency_hz = float(dynamic_case["frequency_hz"])
            for amplitude_fraction in dynamic_case["amplitude_sweep_fraction"]:
                high_it, low_it = dynamic_load_vectors(base_it_by_block, mode, float(amplitude_fraction))
                high_case = evaluate_multinode_case(assumptions, topology, campus_architecture, high_it)
                low_case = evaluate_multinode_case(assumptions, topology, campus_architecture, low_it)

                source_peak_mw = max(
                    high_case["source_input_mw"] - base_case["source_input_mw"],
                    base_case["source_input_mw"] - low_case["source_input_mw"],
                )
                max_segment_current_swing_a = 0.0
                for segment in base_case["segment_rows"]:
                    name = segment["name"]
                    high_current = next(row["current_a"] for row in high_case["segment_rows"] if row["name"] == name)
                    low_current = next(row["current_a"] for row in low_case["segment_rows"] if row["name"] == name)
                    max_segment_current_swing_a = max(
                        max_segment_current_swing_a,
                        abs(high_current - segment["current_a"]),
                        abs(segment["current_a"] - low_current),
                    )

                affected_blocks = list(base_it_by_block)
                if mode == "largest_block_only":
                    affected_blocks = [max(base_it_by_block, key=base_it_by_block.get)]
                elif mode == "two_block_cluster":
                    affected_blocks = list(base_it_by_block)[: min(2, len(base_it_by_block))]
                elif mode == "one_up_one_down":
                    names = list(base_it_by_block)
                    affected_blocks = [names[0], names[-1]]
                distributed_buffer_peak_mw = 0.0
                for block_name in affected_blocks:
                    base_tap = base_case["block_tap_power_by_name_mw"][block_name]
                    high_tap = high_case["block_tap_power_by_name_mw"][block_name]
                    low_tap = low_case["block_tap_power_by_name_mw"][block_name]
                    distributed_buffer_peak_mw += max(high_tap - base_tap, base_tap - low_tap)
                distributed_buffer_energy_kwh = distributed_buffer_peak_mw / (2.0 * math.pi * frequency_hz) / 3.6

                rows.append(
                    {
                        "mode": mode,
                        "case_name": dynamic_case["name"],
                        "frequency_hz": frequency_hz,
                        "it_amplitude_fraction": float(amplitude_fraction),
                        "source_peak_mw": source_peak_mw,
                        "source_peak_fraction_of_base_input": source_peak_mw / base_case["source_input_mw"],
                        "max_segment_current_swing_a": max_segment_current_swing_a,
                        "distributed_buffer_peak_mw": distributed_buffer_peak_mw,
                        "distributed_buffer_energy_kwh": distributed_buffer_energy_kwh,
                    }
                )
    return rows


def build_annual_summary(
    assumptions: dict,
    topology: dict,
    campus_architecture: CampusArchitecture,
    ordered_blocks: Sequence[Block],
) -> dict:
    electricity_price = float(assumptions["global"]["electricity_price_per_mwh"])
    annual_it_mwh = 0.0
    annual_input_mwh = 0.0
    load_bin_rows = []
    for load_bin in assumptions["load_profile"]:
        scale = float(load_bin["load_fraction"])
        hours = HOURS_PER_YEAR * float(load_bin["hours_fraction"])
        result = evaluate_multinode_case(
            assumptions,
            topology,
            campus_architecture,
            {block.name: block.it_load_mw * scale for block in ordered_blocks},
        )
        annual_it_mwh += result["total_it_mw"] * hours
        annual_input_mwh += result["source_input_mw"] * hours
        load_bin_rows.append(
            {
                "name": load_bin["name"],
                "scale": scale,
                "hours": hours,
                "it_mw": result["total_it_mw"],
                "source_mw": result["source_input_mw"],
                "loss_mw": result["total_loss_mw"],
                "efficiency": result["total_efficiency"],
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
    report = {
        "topology_name": topology["name"],
        "description": topology.get("description", ""),
        "campus_topology": topology,
        "architectures": [],
    }

    for architecture_name in ARCHITECTURE_ORDER:
        campus_architecture = architecture_for_multinode(assumptions, architecture_name)
        _, ordered_blocks = build_network(topology, campus_architecture, assumptions)
        full_load = evaluate_multinode_case(
            assumptions,
            topology,
            campus_architecture,
            {block.name: block.it_load_mw for block in ordered_blocks},
        )
        annual = build_annual_summary(assumptions, topology, campus_architecture, ordered_blocks)
        dynamic = build_dynamic_summary(assumptions, topology, campus_architecture, full_load, ordered_blocks)
        expansion = build_expansion_cases(assumptions, topology, campus_architecture, ordered_blocks)

        report["architectures"].append(
            {
                "name": campus_architecture.name,
                "display_name": campus_architecture.display_name,
                "scenario_label": {
                    "traditional_ac": "Scenario 1(M)",
                    "ac_fed_sst_800vdc": "Scenario 2(M)",
                    "proposed_mvdc_backbone": "Scenario 3(M)",
                }[campus_architecture.name],
                "network_kind": campus_architecture.kind,
                "source_voltage_kv": campus_architecture.source_voltage_kv,
                "full_load": full_load,
                "annual_summary": annual,
                "dynamic_summary": dynamic,
                "expansion_cases": expansion,
            }
        )

    return report


def print_summary(report: dict) -> None:
    topology = report["campus_topology"]
    total_it = sum(block["it_load_mw"] for block in topology["blocks"])
    print(
        f"Multi-node campus comparison: {len(topology['blocks'])} blocks, "
        f"{total_it:.1f} MW total IT on a shared campus topology"
    )
    print(
        format_table(
            [
                ("Scenario", "Kind", "Source kV", "Full-load Eff.", "Source MW", "Annual Loss", "Annual Cost", "Min Block Vpu"),
                *[
                    (
                        entry["scenario_label"],
                        entry["network_kind"].upper(),
                        f"{entry['source_voltage_kv']:.1f}",
                        format_pct(entry["full_load"]["total_efficiency"]),
                        f"{entry['full_load']['source_input_mw']:.2f}",
                        format_gwh(entry["annual_summary"]["annual_loss_mwh"]),
                        format_money_millions(entry["annual_summary"]["annual_loss_cost_usd"]),
                        f"{entry['full_load']['min_block_voltage_pu']:.4f}",
                    )
                    for entry in report["architectures"]
                ],
            ]
        )
    )


def print_details(report: dict) -> None:
    for entry in report["architectures"]:
        print(f"\n{entry['scenario_label']} - {entry['display_name']}")
        print("-" * (len(entry["scenario_label"]) + len(entry["display_name"]) + 3))
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
                        for row in entry["full_load"]["block_rows"]
                    ],
                ]
            )
        )
        print()
        print(
            format_table(
                [
                    ("Segment", "Kind", "From", "To", "Length m", "Circuits", "Current A", "Loss MW"),
                    *[
                        (
                            row["name"],
                            row["kind"],
                            row["from_node"],
                            row["to_node"],
                            f"{row['length_m']:.1f}",
                            str(row["circuits"]),
                            f"{row['current_a']:.1f}",
                            f"{row['loss_mw']:.4f}",
                        )
                        for row in entry["full_load"]["segment_rows"]
                    ],
                ]
            )
        )
        print()
        print(
            format_table(
                [
                    ("Active Blocks", "Total IT MW", "Source MW", "Efficiency", "Network Loss MW", "Min Block Vpu"),
                    *[
                        (
                            ", ".join(case["active_blocks"]),
                            f"{case['total_it_mw']:.1f}",
                            f"{case['source_input_mw']:.2f}",
                            format_pct(case["efficiency"]),
                            f"{case['network_loss_mw']:.4f}",
                            f"{case['min_block_voltage_pu']:.4f}",
                        )
                        for case in entry["expansion_cases"]
                    ],
                ]
            )
        )
        print()
        print(
            format_table(
                [
                    ("Mode", "Case", "Freq Hz", "IT Amp", "Source Peak MW", "Source Peak %", "Max Seg A", "Buffer MW", "Buffer kWh"),
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
                        for row in entry["dynamic_summary"]
                    ],
                ]
            )
        )


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Compare multi-node campus versions of Scenarios 1, 2, and 3.")
    parser.add_argument("--assumptions", type=Path, default=DEFAULT_ASSUMPTIONS_PATH, help="Path to the assumptions JSON.")
    parser.add_argument("--topology", type=Path, default=DEFAULT_TOPOLOGY_PATH, help="Path to the shared campus topology JSON.")
    parser.add_argument("--details", action="store_true", help="Print detailed per-scenario tables.")
    parser.add_argument("--save-json", type=Path, help="Optional path for a machine-readable report.")
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
