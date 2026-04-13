#!/usr/bin/env python3
"""Reduced-order Scenario 3(M) DC transient screen.

The goal is not EMT fidelity. This script answers a narrower question that is
still useful for the white paper:

If dynamic AI-factory block loads are presented to the MVDC backbone, do modest
local buffers keep the internal DC network in a reasonable operating envelope,
and how much source-side smoothing is obtained in return?
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Dict, List

from dc_backbone_model import format_table, load_json
from dc_backbone.transient_common import (
    EVENT_END_S,
    EVENT_START_S,
    LOCAL_BUFFER_CONFIGS,
    PATTERNS,
    RECOVERY_TOLERANCE_MW,
    RECOVERY_TOLERANCE_PU,
    SIM_DURATION_S,
    TIME_STEP_S,
    max_ramp_metric,
    recovery_time,
    solve_network,
    tap_targets_by_block,
    target_it_profile,
    update_buffer_state,
    write_json,
)
from dc_backbone_multinode_campus_model import (
    DEFAULT_ASSUMPTIONS_PATH,
    DEFAULT_TOPOLOGY_PATH,
    architecture_for_multinode,
    build_network,
    evaluate_source_stage_input_mw,
    load_topology,
)


ROOT = Path(__file__).resolve().parent
DEFAULT_OUTPUT = ROOT / "dc_transient_report.json"
DEFAULT_NOTE = ROOT / "DC_TRANSIENT_ANALYSIS.md"
SCENARIO_NAME = "proposed_mvdc_backbone"
BUFFER_CONFIGS = LOCAL_BUFFER_CONFIGS


def simulate_pattern(assumptions: dict, topology: dict, pattern: dict, config: dict) -> dict:
    architecture = architecture_for_multinode(assumptions, SCENARIO_NAME)
    segments, blocks = build_network(topology, architecture, assumptions)

    base_it_by_block = {block.name: block.it_load_mw for block in blocks}
    base_targets = tap_targets_by_block(blocks, architecture.local_block_elements, assumptions, base_it_by_block)
    base_network = solve_network(
        architecture,
        assumptions,
        topology,
        segments,
        {block.leaf_node: base_targets[block.name] for block in blocks},
    )
    base_source_input_mw = evaluate_source_stage_input_mw(
        architecture.source_stage_elements,
        assumptions,
        base_network["network_source_output_mw"],
    )
    base_min_vpu = min(
        base_network["node_voltage_kv"][f"block::{block.name}"] / architecture.source_voltage_kv for block in blocks
    )

    seen_tap_by_block = dict(base_targets)
    energy_state_by_block = {
        block.name: float(config["energy_kwh_per_block"]) * 0.5 for block in blocks
    }

    step_rows = []
    max_source_input_mw = base_source_input_mw
    max_source_output_mw = base_network["network_source_output_mw"]
    max_segment_current_a = max(base_network["segment_current_a"].values())
    min_block_voltage_pu = base_min_vpu
    max_total_buffer_discharge_mw = 0.0
    max_total_buffer_charge_mw = 0.0
    min_state_of_charge_fraction = 0.5 if config["energy_kwh_per_block"] > 0 else 1.0
    max_state_of_charge_fraction = 0.5 if config["energy_kwh_per_block"] > 0 else 1.0
    worst_segment_name = max(base_network["segment_current_a"], key=base_network["segment_current_a"].get)
    worst_block_name = min(blocks, key=lambda block: base_network["node_voltage_kv"][block.leaf_node]).name

    time_s = 0.0
    while time_s <= SIM_DURATION_S + 1e-12:
        it_profile = target_it_profile(base_it_by_block, pattern, time_s)
        target_taps = tap_targets_by_block(blocks, architecture.local_block_elements, assumptions, it_profile)

        total_discharge_mw = 0.0
        total_charge_mw = 0.0
        for block in blocks:
            seen_tap, buffer_power, next_energy = update_buffer_state(
                target_power_mw=target_taps[block.name],
                previous_seen_power_mw=seen_tap_by_block[block.name],
                energy_kwh=energy_state_by_block[block.name],
                power_rating_mw=float(config["power_mw_per_block"]),
                energy_capacity_kwh=float(config["energy_kwh_per_block"]),
                smoothing_tau_s=float(config["smoothing_tau_s"]),
                dt_s=TIME_STEP_S,
            )
            seen_tap_by_block[block.name] = seen_tap
            energy_state_by_block[block.name] = next_energy
            if buffer_power >= 0.0:
                total_discharge_mw += buffer_power
            else:
                total_charge_mw += abs(buffer_power)

        network = solve_network(
            architecture,
            assumptions,
            topology,
            segments,
            {block.leaf_node: seen_tap_by_block[block.name] for block in blocks},
        )
        source_input_mw = evaluate_source_stage_input_mw(
            architecture.source_stage_elements,
            assumptions,
            network["network_source_output_mw"],
        )
        block_voltage_pu = {
            block.name: network["node_voltage_kv"][block.leaf_node] / architecture.source_voltage_kv for block in blocks
        }

        local_min_block_name = min(block_voltage_pu, key=block_voltage_pu.get)
        local_min_block_vpu = block_voltage_pu[local_min_block_name]
        local_worst_segment = max(network["segment_current_a"], key=network["segment_current_a"].get)
        local_max_segment_current = network["segment_current_a"][local_worst_segment]
        energy_capacity = float(config["energy_kwh_per_block"])
        if energy_capacity > 0.0:
            soc_values = [energy_state_by_block[block.name] / energy_capacity for block in blocks]
            min_state_of_charge_fraction = min(min_state_of_charge_fraction, min(soc_values))
            max_state_of_charge_fraction = max(max_state_of_charge_fraction, max(soc_values))

        max_source_input_mw = max(max_source_input_mw, source_input_mw)
        max_source_output_mw = max(max_source_output_mw, network["network_source_output_mw"])
        if local_max_segment_current > max_segment_current_a:
            max_segment_current_a = local_max_segment_current
            worst_segment_name = local_worst_segment
        if local_min_block_vpu < min_block_voltage_pu:
            min_block_voltage_pu = local_min_block_vpu
            worst_block_name = local_min_block_name
        max_total_buffer_discharge_mw = max(max_total_buffer_discharge_mw, total_discharge_mw)
        max_total_buffer_charge_mw = max(max_total_buffer_charge_mw, total_charge_mw)

        step_rows.append(
            {
                "time_s": round(time_s, 4),
                "source_input_mw": source_input_mw,
                "source_output_mw": network["network_source_output_mw"],
                "min_block_voltage_pu": local_min_block_vpu,
                "worst_block_name": local_min_block_name,
                "max_segment_current_a": local_max_segment_current,
                "worst_segment_name": local_worst_segment,
                "total_buffer_discharge_mw": total_discharge_mw,
                "total_buffer_charge_mw": total_charge_mw,
            }
        )
        time_s += TIME_STEP_S

    return {
        "pattern_name": pattern["name"],
        "mode": pattern["mode"],
        "it_amplitude_fraction": pattern["amplitude_fraction"],
        "buffer_config": config,
        "base_case": {
            "source_input_mw": base_source_input_mw,
            "source_output_mw": base_network["network_source_output_mw"],
            "min_block_voltage_pu": base_min_vpu,
        },
        "summary": {
            "max_source_input_mw": max_source_input_mw,
            "max_source_input_delta_mw": max_source_input_mw - base_source_input_mw,
            "max_source_output_mw": max_source_output_mw,
            "max_source_output_delta_mw": max_source_output_mw - base_network["network_source_output_mw"],
            "max_source_input_ramp_mw_per_s": max_ramp_metric(step_rows, "source_input_mw"),
            "max_source_output_ramp_mw_per_s": max_ramp_metric(step_rows, "source_output_mw"),
            "min_block_voltage_pu": min_block_voltage_pu,
            "worst_block_name": worst_block_name,
            "max_segment_current_a": max_segment_current_a,
            "max_segment_current_ramp_a_per_s": max_ramp_metric(step_rows, "max_segment_current_a"),
            "worst_segment_name": worst_segment_name,
            "max_total_buffer_discharge_mw": max_total_buffer_discharge_mw,
            "max_total_buffer_charge_mw": max_total_buffer_charge_mw,
            "recovery_time_s": recovery_time(step_rows, base_min_vpu, base_source_input_mw),
            "min_state_of_charge_fraction": min_state_of_charge_fraction,
            "max_state_of_charge_fraction": max_state_of_charge_fraction,
        },
        "step_rows": step_rows,
    }


def build_report(assumptions: dict, topology: dict) -> dict:
    pattern_results = []
    for config in BUFFER_CONFIGS:
        for pattern in PATTERNS:
            pattern_results.append(simulate_pattern(assumptions, topology, pattern, config))

    by_buffer = {}
    for config in BUFFER_CONFIGS:
        rows = [row for row in pattern_results if row["buffer_config"]["name"] == config["name"]]
        by_buffer[config["name"]] = {
            "display_name": config["display_name"],
            "patterns": rows,
        }

    return {
        "meta": {
            "title": "Reduced-order Scenario 3(M) DC transient screen",
            "status": "scenario3m_dc_transient_screen_v1",
            "assumption_note": (
                "This is a reduced-order transient screen. Each block load is converted to a tap-power target, "
                "local buffers smooth the tap demand with explicit power/energy limits, and the MVDC backbone is "
                "re-solved quasi-statically at each time step. This is not an EMT or converter-control model."
            ),
            "time_step_s": TIME_STEP_S,
            "simulation_duration_s": SIM_DURATION_S,
            "event_start_s": EVENT_START_S,
            "event_end_s": EVENT_END_S,
            "scenario_name": SCENARIO_NAME,
        },
        "buffer_configs": BUFFER_CONFIGS,
        "patterns": PATTERNS,
        "results": pattern_results,
        "by_buffer": by_buffer,
    }


def build_note(report: dict) -> str:
    baseline_rows = report["by_buffer"]["no_local_buffer"]["patterns"]
    moderate_rows = report["by_buffer"]["moderate_local_buffer"]["patterns"]
    strong_rows = report["by_buffer"]["strong_local_buffer"]["patterns"]

    def pick(rows: List[dict], name: str) -> dict:
        return next(row for row in rows if row["pattern_name"] == name)

    coherent_none = pick(baseline_rows, "coherent_15pct_burst")
    coherent_mod = pick(moderate_rows, "coherent_15pct_burst")
    coherent_strong = pick(strong_rows, "coherent_15pct_burst")
    opposition_mod = pick(moderate_rows, "split_opposition_15pct_burst")

    return "\n".join(
        [
            "# Reduced-order Scenario 3(M) DC Transient Screen",
            "",
            "This note addresses the main remaining dynamic concern: whether the MVDC backbone simply moves stress from the AC boundary into the internal DC network.",
            "",
            "## Benchmark Setup",
            "",
            "- Four 25 MW DC-native blocks on the shared Scenario 3(M) backbone.",
            "- Short burst from 0.25 s to 0.45 s to emulate a fast AI-load excursion rather than a slow permanent step.",
            "- Internal MVDC network solved at each time step; local buffers apply explicit power and energy limits.",
            "",
            "## Key Result",
            "",
            f"- For a coherent 15% campus burst with no local buffer, the minimum block voltage reaches `{coherent_none['summary']['min_block_voltage_pu']:.5f} pu`, the source-input peak rises by `{coherent_none['summary']['max_source_input_delta_mw']:.2f} MW`, and the source-input ramp reaches `{coherent_none['summary']['max_source_input_ramp_mw_per_s']:.2f} MW/s`.",
            f"- With the moderate local buffer, the same event holds the minimum block voltage at `{coherent_mod['summary']['min_block_voltage_pu']:.5f} pu`, reduces the source-input peak delta to `{coherent_mod['summary']['max_source_input_delta_mw']:.2f} MW`, and reduces the source-input ramp to `{coherent_mod['summary']['max_source_input_ramp_mw_per_s']:.2f} MW/s`.",
            f"- With the strong local buffer, the same event holds the minimum block voltage at `{coherent_strong['summary']['min_block_voltage_pu']:.5f} pu`, reduces the source-input peak delta to `{coherent_strong['summary']['max_source_input_delta_mw']:.2f} MW`, and reduces the source-input ramp to `{coherent_strong['summary']['max_source_input_ramp_mw_per_s']:.2f} MW/s`.",
            "",
            "## Internal-Stress Tradeoff",
            "",
            f"- Under the split-campus-opposition burst, the moderate buffer still limits the worst block voltage to `{opposition_mod['summary']['min_block_voltage_pu']:.5f} pu`, but the internal segment-current peak remains a first-order quantity at `{opposition_mod['summary']['max_segment_current_a']:.2f} A`.",
            "- Interpretation: the MVDC backbone can keep internal voltage sag modest with local buffering, but internal current redistribution remains a real design constraint rather than disappearing.",
            "",
            "## Evidence Boundary",
            "",
            "- This strengthens the benefit-3 claim by showing internal MVDC behavior under dynamic block loading, not just AC-boundary voltage screens.",
            "- It is still reduced-order. It does not replace converter-aware EMT, protection, or control validation.",
        ]
    )


def print_summary(report: dict) -> None:
    print("Reduced-order Scenario 3(M) DC transient screen")
    print("-----------------------------------------------")
    rows = [["Buffer", "Pattern", "Min Block Vpu", "Max Source Delta MW", "Max Ramp MW/s", "Max Segment A", "Recovery s"]]
    for result in report["results"]:
        summary = result["summary"]
        rows.append(
            [
                result["buffer_config"]["display_name"],
                result["pattern_name"],
                f"{summary['min_block_voltage_pu']:.5f}",
                f"{summary['max_source_input_delta_mw']:.2f}",
                f"{summary['max_source_input_ramp_mw_per_s']:.2f}",
                f"{summary['max_segment_current_a']:.2f}",
                "n/a" if summary["recovery_time_s"] is None else f"{summary['recovery_time_s']:.2f}",
            ]
        )
    print(format_table(rows))


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run a reduced-order DC transient screen for Scenario 3(M).")
    parser.add_argument("--assumptions", type=Path, default=DEFAULT_ASSUMPTIONS_PATH)
    parser.add_argument("--topology", type=Path, default=DEFAULT_TOPOLOGY_PATH)
    parser.add_argument("--save-json", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--write-note", type=Path, default=DEFAULT_NOTE)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    assumptions = load_json(args.assumptions)
    topology = load_topology(args.topology)
    report = build_report(assumptions, topology)
    print_summary(report)
    if args.save_json:
        write_json(args.save_json, report)
    if args.write_note:
        args.write_note.write_text(build_note(report), encoding="utf-8")


if __name__ == "__main__":
    main()
