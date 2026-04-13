#!/usr/bin/env python3
"""Reduced-order public fault-duty screen for the Scenario 3(M) MVDC backbone.

This script addresses the reviewer objection that protection and fault duty are
missing entirely. It does not claim deployable protection coordination. It
builds a public-data-only upper-bound screening model for the proposed MVDC
backbone using:

- the existing Scenario 3(M) multi-node topology and currents,
- public benchmark line-inductance values from open literature,
- public breaker-clearing-time benchmark categories from open HVDC breaker reviews.

The output is a reduced-order interruption-timescale and I^2t screen for
representative backbone and branch fault locations.
"""

from __future__ import annotations

import argparse
import json
import math
from pathlib import Path
from typing import Dict, Sequence

from dc_backbone_model import format_pct, format_table, load_json
from dc_backbone_multinode_campus_model import (
    architecture_for_multinode,
    build_network,
    evaluate_multinode_case,
    load_topology,
)

ROOT = Path(__file__).resolve().parent

DEFAULT_ASSUMPTIONS = ROOT / "scientific_assumptions_v1.json"
DEFAULT_TOPOLOGY = ROOT / "multinode_campus_topology.json"
DEFAULT_OUTPUT_JSON = ROOT / "public_fault_envelope_report.json"
DEFAULT_OUTPUT_NOTE = ROOT / "PUBLIC_FAULT_ENVELOPE.md"

LINE_INDUCTANCE_MH_PER_KM = 0.86
REACTOR_MH_SWEEP = [50.0, 100.0, 200.0]
FAULT_RESISTANCE_SWEEP_OHM = [0.01, 0.05, 0.10]
BREAKER_CATEGORIES_MS = {
    "semiconductor_fast": 2.0,
    "hybrid_reference": 5.0,
    "slower_interruption": 10.0,
    "backup_delayed": 20.0,
}
CURRENT_THRESHOLDS_KA = [2.0, 5.0, 10.0]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--assumptions", type=Path, default=DEFAULT_ASSUMPTIONS)
    parser.add_argument("--topology", type=Path, default=DEFAULT_TOPOLOGY)
    parser.add_argument("--output-json", type=Path, default=DEFAULT_OUTPUT_JSON)
    parser.add_argument("--output-note", type=Path, default=DEFAULT_OUTPUT_NOTE)
    parser.add_argument("--details", action="store_true")
    return parser.parse_args()


def write_json(path: Path, payload: dict) -> None:
    path.write_text(json.dumps(payload, indent=2), encoding="utf-8")


def format_ka(value_a: float) -> str:
    return f"{value_a / 1000.0:.2f} kA"


def format_ms(value_s: float | None) -> str:
    if value_s is None:
        return "N/A"
    return f"{1000.0 * value_s:.2f} ms"


def path_segments_by_node(segments: Sequence, source_node: str) -> Dict[str, list]:
    parent = {segment.to_node: segment for segment in segments}
    out = {source_node: []}
    nodes = {source_node}
    for segment in segments:
        nodes.add(segment.from_node)
        nodes.add(segment.to_node)
    for node in nodes:
        if node == source_node:
            continue
        path = []
        cursor = node
        while cursor != source_node:
            segment = parent[cursor]
            path.append(segment)
            cursor = segment.from_node
        out[node] = list(reversed(path))
    return out


def path_r_ohm(path_segments: Sequence, segment_fraction: float = 1.0) -> float:
    if not path_segments:
        return 0.0
    total = sum(segment.effective_loop_r_ohm for segment in path_segments[:-1])
    total += segment_fraction * path_segments[-1].effective_loop_r_ohm
    return total


def path_l_h(path_segments: Sequence, segment_fraction: float = 1.0) -> float:
    if not path_segments:
        return 0.0
    total_length_km = sum(2.0 * segment.length_m / 1000.0 for segment in path_segments[:-1])
    total_length_km += segment_fraction * 2.0 * path_segments[-1].length_m / 1000.0
    return total_length_km * LINE_INDUCTANCE_MH_PER_KM / 1000.0


def current_at_time_a(v_fault_v: float, i0_a: float, r_eq_ohm: float, l_eq_h: float, t_s: float) -> float:
    if l_eq_h <= 0.0:
        return v_fault_v / max(r_eq_ohm, 1e-9)
    i_inf = v_fault_v / max(r_eq_ohm, 1e-9)
    tau = l_eq_h / max(r_eq_ohm, 1e-9)
    return i_inf - (i_inf - i0_a) * math.exp(-t_s / tau)


def i2t_a2s(v_fault_v: float, i0_a: float, r_eq_ohm: float, l_eq_h: float, clearing_s: float, steps: int = 2000) -> float:
    if clearing_s <= 0.0:
        return 0.0
    dt = clearing_s / steps
    total = 0.0
    for index in range(steps):
        t_mid = (index + 0.5) * dt
        current = current_at_time_a(v_fault_v, i0_a, r_eq_ohm, l_eq_h, t_mid)
        total += current * current * dt
    return total


def time_to_current_threshold_s(v_fault_v: float, i0_a: float, r_eq_ohm: float, l_eq_h: float, threshold_a: float) -> float | None:
    if threshold_a <= i0_a:
        return 0.0
    i_inf = v_fault_v / max(r_eq_ohm, 1e-9)
    if threshold_a >= i_inf:
        return None
    tau = l_eq_h / max(r_eq_ohm, 1e-9)
    ratio = (i_inf - threshold_a) / (i_inf - i0_a)
    if ratio <= 0.0:
        return None
    return -tau * math.log(ratio)


def representative_fault_locations(topology: dict, segments: Sequence) -> list[dict]:
    longest_block = max(topology["blocks"], key=lambda row: float(row["branch_length_m"]))
    block_leaf = f"block::{longest_block['name']}"
    source_segment = next(segment for segment in segments if segment.name == "source_to_north")
    longest_tap = next(segment for segment in segments if segment.name == f"{longest_block['name']}_tap")
    return [
        {
            "name": "source_backbone_midpoint",
            "kind": "segment_midpoint",
            "target_node": source_segment.to_node,
            "target_segment": source_segment.name,
            "segment_fraction": 0.5,
            "description": "Midpoint of the first shared 69 kV DC backbone segment near the front end.",
        },
        {
            "name": "remote_branch_end",
            "kind": "node_end",
            "target_node": block_leaf,
            "target_segment": longest_tap.name,
            "segment_fraction": 1.0,
            "description": f"Remote-end fault at the longest branch feeding {longest_block['name']}.",
        },
    ]


def evaluate_fault_envelope(assumptions: dict, topology: dict) -> dict:
    architecture = architecture_for_multinode(assumptions, "proposed_mvdc_backbone")
    segments, _ = build_network(topology, architecture, assumptions)
    base_case = evaluate_multinode_case(
        assumptions,
        topology,
        architecture,
        {row["name"]: float(row["it_load_mw"]) for row in topology["blocks"]},
    )

    path_map = path_segments_by_node(segments, topology["source_node"])
    source_voltage_v = architecture.source_voltage_kv * 1000.0
    locations = representative_fault_locations(topology, segments)
    rows = []

    for location in locations:
        path = path_map[location["target_node"]]
        path_r = path_r_ohm(path, location["segment_fraction"])
        path_l = path_l_h(path, location["segment_fraction"])
        affected_segment = location["target_segment"]
        prefault_current_a = next(
            row["current_a"] for row in base_case["segment_rows"] if row["name"] == affected_segment
        )

        for reactor_mh in REACTOR_MH_SWEEP:
            for fault_r_ohm in FAULT_RESISTANCE_SWEEP_OHM:
                total_r = path_r + fault_r_ohm
                total_l = path_l + reactor_mh / 1000.0
                time_to_thresholds = {
                    f"{threshold_ka:.1f}kA": time_to_current_threshold_s(
                        source_voltage_v, prefault_current_a, total_r, total_l, threshold_ka * 1000.0
                    )
                    for threshold_ka in CURRENT_THRESHOLDS_KA
                }
                breaker_rows = {}
                for breaker_name, clearing_ms in BREAKER_CATEGORIES_MS.items():
                    clearing_s = clearing_ms / 1000.0
                    breaker_rows[breaker_name] = {
                        "clearing_time_ms": clearing_ms,
                        "current_a": current_at_time_a(source_voltage_v, prefault_current_a, total_r, total_l, clearing_s),
                        "i2t_a2s": i2t_a2s(source_voltage_v, prefault_current_a, total_r, total_l, clearing_s),
                    }

                rows.append(
                    {
                        "location_name": location["name"],
                        "location_description": location["description"],
                        "target_segment": affected_segment,
                        "prefault_current_a": prefault_current_a,
                        "path_loop_r_ohm": path_r,
                        "path_loop_l_h": path_l,
                        "reactor_mh": reactor_mh,
                        "fault_resistance_ohm": fault_r_ohm,
                        "total_r_ohm": total_r,
                        "total_l_h": total_l,
                        "time_to_thresholds_s": time_to_thresholds,
                        "breaker_rows": breaker_rows,
                    }
                )

    baseline_rows = [
        row
        for row in rows
        if abs(row["reactor_mh"] - 100.0) < 1e-9 and abs(row["fault_resistance_ohm"] - 0.01) < 1e-9
    ]
    baseline_rows.sort(key=lambda row: row["location_name"])

    worst_hybrid = max(
        rows,
        key=lambda row: row["breaker_rows"]["hybrid_reference"]["current_a"],
    )
    fastest_5ka = min(
        (row for row in rows if row["time_to_thresholds_s"]["5.0kA"] is not None),
        key=lambda row: row["time_to_thresholds_s"]["5.0kA"],
    )

    return {
        "meta": {
            "title": "Reduced-order public MVDC fault-duty screen",
            "updated": "2026-04-11",
            "note": (
                "This is a reduced-order MVDC fault envelope for Scenario 3(M). It does not model "
                "converter current limiting or breaker controls. It is an upper-bound RL interruption "
                "screen using public benchmark ranges for line inductance and breaker clearing time."
            ),
            "public_parameter_basis": {
                "line_inductance_mh_per_km": LINE_INDUCTANCE_MH_PER_KM,
                "reactor_sweep_mh": REACTOR_MH_SWEEP,
                "fault_resistance_sweep_ohm": FAULT_RESISTANCE_SWEEP_OHM,
                "breaker_categories_ms": BREAKER_CATEGORIES_MS,
                "sources": {
                    "line_inductance_example": "https://www.mdpi.com/1996-1073/17/15/3800",
                    "breaker_review": "https://doi.org/10.1186/s41601-023-00304-y",
                },
            },
        },
        "scenario3m_base_case": {
            "source_voltage_kv": architecture.source_voltage_kv,
            "total_it_mw": base_case["total_it_mw"],
            "source_input_mw": base_case["source_input_mw"],
            "efficiency": base_case["total_efficiency"],
            "segment_rows": base_case["segment_rows"],
        },
        "fault_rows": rows,
        "baseline_rows": baseline_rows,
        "headline": {
            "worst_hybrid_reference_case": worst_hybrid,
            "fastest_time_to_5ka": fastest_5ka,
        },
    }


def build_note(report: dict) -> str:
    baseline_table = [["Location", "Prefault current", "5 ms current", "5 ms I^2t", "Time to 5 kA"]]
    for row in report["baseline_rows"]:
        hybrid = row["breaker_rows"]["hybrid_reference"]
        baseline_table.append(
            [
                row["location_name"],
                format_ka(row["prefault_current_a"]),
                format_ka(hybrid["current_a"]),
                f"{hybrid['i2t_a2s'] / 1e6:.2f} MA^2s",
                format_ms(row["time_to_thresholds_s"]["5.0kA"]),
            ]
        )

    headline = report["headline"]
    worst_hybrid = headline["worst_hybrid_reference_case"]
    fastest_5ka = headline["fastest_time_to_5ka"]

    return "\n".join(
        [
            "# Public Fault Envelope",
            "",
            "Updated: April 11, 2026",
            "",
            "This note adds a public-data-only protection plausibility layer for the proposed `Scenario 3(M)` MVDC backbone.",
            "",
            "## Model scope",
            "",
            "The screen starts from the full-load multi-node Scenario 3(M) currents already computed in the repo. It then evaluates representative backbone and branch fault locations with a reduced-order RL current-rise model.",
            "",
            f"- Backbone voltage: `{report['scenario3m_base_case']['source_voltage_kv']:.1f} kV DC`.",
            f"- Public line-inductance benchmark: `{report['meta']['public_parameter_basis']['line_inductance_mh_per_km']:.2f} mH/km`.",
            f"- Reactor sweep: `{', '.join(f'{value:.0f}' for value in report['meta']['public_parameter_basis']['reactor_sweep_mh'])} mH`.",
            f"- Breaker benchmark times: `{', '.join(f'{name}={value:.0f} ms' for name, value in report['meta']['public_parameter_basis']['breaker_categories_ms'].items())}`.",
            f"- Public source for line inductance example: `{report['meta']['public_parameter_basis']['sources']['line_inductance_example']}`.",
            f"- Public source for breaker timing categories: `{report['meta']['public_parameter_basis']['sources']['breaker_review']}`.",
            "",
            "## Baseline envelope",
            "",
            "Baseline rows below use `100 mH` reactor and `0.01 ohm` fault resistance.",
            "",
            format_table(baseline_table),
            "",
            "## Headline findings",
            "",
            f"Worst `5 ms` hybrid-reference current in the sweep occurs at `{worst_hybrid['location_name']}` with reactor `{worst_hybrid['reactor_mh']:.0f} mH` and fault resistance `{worst_hybrid['fault_resistance_ohm']:.2f} ohm`, reaching `{format_ka(worst_hybrid['breaker_rows']['hybrid_reference']['current_a'])}`.",
            f"Fastest time to `5 kA` in the sweep occurs at `{fastest_5ka['location_name']}` with reactor `{fastest_5ka['reactor_mh']:.0f} mH` and fault resistance `{fastest_5ka['fault_resistance_ohm']:.2f} ohm`, at `{format_ms(fastest_5ka['time_to_thresholds_s']['5.0kA'])}`.",
            "",
            "## Interpretation",
            "",
            "- This layer does not prove a protection design. It does provide a public-data-only bound on how quickly MVDC backbone current can rise under representative faults.",
            "- It supports the reviewer-response position that protection is a first-order design issue with interruption-timescale consequences, not an ignored afterthought.",
            "- Because converter current limiting is not modeled here, the results should be treated as conservative screening values rather than deployable equipment duty ratings.",
        ]
    )


def print_summary(report: dict, details: bool) -> None:
    print("Public fault envelope")
    print("---------------------")
    print(
        f"Scenario 3(M) base case: {report['scenario3m_base_case']['total_it_mw']:.1f} MW IT at "
        f"{report['scenario3m_base_case']['source_voltage_kv']:.1f} kV DC"
    )
    print()

    rows = [["Location", "Prefault current", "5 ms current", "Time to 5 kA"]]
    for row in report["baseline_rows"]:
        hybrid = row["breaker_rows"]["hybrid_reference"]
        rows.append(
            [
                row["location_name"],
                format_ka(row["prefault_current_a"]),
                format_ka(hybrid["current_a"]),
                format_ms(row["time_to_thresholds_s"]["5.0kA"]),
            ]
        )
    print(format_table(rows))

    if details:
        print()
        detail_rows = [["Location", "Reactor", "Fault R", "2 ms current", "5 ms current", "10 ms current", "20 ms current"]]
        for row in report["fault_rows"]:
            detail_rows.append(
                [
                    row["location_name"],
                    f"{row['reactor_mh']:.0f} mH",
                    f"{row['fault_resistance_ohm']:.2f} ohm",
                    format_ka(row["breaker_rows"]["semiconductor_fast"]["current_a"]),
                    format_ka(row["breaker_rows"]["hybrid_reference"]["current_a"]),
                    format_ka(row["breaker_rows"]["slower_interruption"]["current_a"]),
                    format_ka(row["breaker_rows"]["backup_delayed"]["current_a"]),
                ]
            )
        print()
        print(format_table(detail_rows))


def main() -> None:
    args = parse_args()
    assumptions = load_json(args.assumptions)
    topology = load_topology(args.topology)
    report = evaluate_fault_envelope(assumptions, topology)
    write_json(args.output_json, report)
    args.output_note.write_text(build_note(report), encoding="utf-8")
    print_summary(report, args.details)


if __name__ == "__main__":
    main()
