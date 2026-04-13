#!/usr/bin/env python3
"""Reduced-order transient comparison for Scenario 2(M) and Scenario 3(M).

This script is the matched follow-on to `dc_backbone_dc_transient_model.py`.
It applies the same burst patterns and the same local-buffer assumptions to the
two advanced multi-node scenarios:

- Scenario 2(M): AC-fed SST + 800 VDC baseline
- Scenario 3(M): MVDC backbone

The goal is to compare grid-facing burst exposure and internal network stress
under the same reduced-order assumptions.
"""

from __future__ import annotations

import argparse
from pathlib import Path
from typing import List

from dc_backbone.transient_common import (
    EVENT_END_S,
    EVENT_START_S,
    LOCAL_BUFFER_CONFIGS,
    PATTERNS,
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
from dc_backbone_model import format_table, load_json
from dc_backbone_multinode_campus_model import (
    DEFAULT_ASSUMPTIONS_PATH,
    DEFAULT_TOPOLOGY_PATH,
    architecture_for_multinode,
    build_network,
    evaluate_source_stage_input_mw,
    load_topology,
)


ROOT = Path(__file__).resolve().parent
DEFAULT_OUTPUT = ROOT / "multinode_transient_comparison_report.json"
DEFAULT_NOTE = ROOT / "MULTINODE_TRANSIENT_COMPARISON.md"
BUFFER_CONFIGS = LOCAL_BUFFER_CONFIGS
SCENARIOS = [
    ("ac_fed_sst_800vdc", "Scenario 2(M)"),
    ("proposed_mvdc_backbone", "Scenario 3(M)"),
]


def simulate_scenario_pattern(assumptions: dict, topology: dict, scenario_name: str, scenario_label: str, pattern: dict, config: dict) -> dict:
    architecture = architecture_for_multinode(assumptions, scenario_name)
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
        base_network["node_voltage_kv"][f"block::{block.name}"] / architecture.source_voltage_kv
        for block in blocks
    )

    seen_tap_by_block = dict(base_targets)
    energy_state_by_block = {
        block.name: float(config["energy_kwh_per_block"]) * 0.5 for block in blocks
    }

    step_rows = []
    max_source_input_mw = base_source_input_mw
    max_segment_current_a = max(base_network["segment_current_a"].values())
    min_block_voltage_pu = base_min_vpu
    max_total_buffer_discharge_mw = 0.0
    max_total_buffer_charge_mw = 0.0
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

        max_source_input_mw = max(max_source_input_mw, source_input_mw)
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
                "min_block_voltage_pu": local_min_block_vpu,
                "max_segment_current_a": local_max_segment_current,
                "total_buffer_discharge_mw": total_discharge_mw,
                "total_buffer_charge_mw": total_charge_mw,
            }
        )
        time_s += TIME_STEP_S

    return {
        "scenario_name": scenario_name,
        "scenario_label": scenario_label,
        "network_kind": architecture.kind,
        "pattern_name": pattern["name"],
        "mode": pattern["mode"],
        "it_amplitude_fraction": pattern["amplitude_fraction"],
        "buffer_config": config,
        "base_case": {
            "source_input_mw": base_source_input_mw,
            "min_block_voltage_pu": base_min_vpu,
        },
        "summary": {
            "max_source_input_mw": max_source_input_mw,
            "max_source_input_delta_mw": max_source_input_mw - base_source_input_mw,
            "max_source_input_ramp_mw_per_s": max_ramp_metric(step_rows, "source_input_mw"),
            "min_block_voltage_pu": min_block_voltage_pu,
            "worst_block_name": worst_block_name,
            "max_segment_current_a": max_segment_current_a,
            "max_segment_current_ramp_a_per_s": max_ramp_metric(step_rows, "max_segment_current_a"),
            "worst_segment_name": worst_segment_name,
            "max_total_buffer_discharge_mw": max_total_buffer_discharge_mw,
            "max_total_buffer_charge_mw": max_total_buffer_charge_mw,
            "recovery_time_s": recovery_time(step_rows, base_min_vpu, base_source_input_mw),
        },
        "step_rows": step_rows,
    }


def build_comparison_rows(results: List[dict]) -> List[dict]:
    grouped: Dict[tuple[str, str], Dict[str, dict]] = {}
    for row in results:
        key = (row["buffer_config"]["name"], row["pattern_name"])
        grouped.setdefault(key, {})[row["scenario_label"]] = row

    comparison_rows = []
    for (buffer_name, pattern_name), pair in sorted(grouped.items()):
        if "Scenario 2(M)" not in pair or "Scenario 3(M)" not in pair:
            continue
        s2 = pair["Scenario 2(M)"]
        s3 = pair["Scenario 3(M)"]
        comparison_rows.append(
            {
                "buffer_name": buffer_name,
                "pattern_name": pattern_name,
                "scenario2m_max_source_delta_mw": s2["summary"]["max_source_input_delta_mw"],
                "scenario3m_max_source_delta_mw": s3["summary"]["max_source_input_delta_mw"],
                "scenario2m_max_source_ramp_mw_per_s": s2["summary"]["max_source_input_ramp_mw_per_s"],
                "scenario3m_max_source_ramp_mw_per_s": s3["summary"]["max_source_input_ramp_mw_per_s"],
                "scenario2m_min_block_voltage_pu": s2["summary"]["min_block_voltage_pu"],
                "scenario3m_min_block_voltage_pu": s3["summary"]["min_block_voltage_pu"],
                "scenario2m_max_segment_current_a": s2["summary"]["max_segment_current_a"],
                "scenario3m_max_segment_current_a": s3["summary"]["max_segment_current_a"],
            }
        )
    return comparison_rows


def build_report(assumptions: dict, topology: dict) -> dict:
    results = []
    for scenario_name, scenario_label in SCENARIOS:
        for config in BUFFER_CONFIGS:
            for pattern in PATTERNS:
                results.append(
                    simulate_scenario_pattern(assumptions, topology, scenario_name, scenario_label, pattern, config)
                )
    return {
        "meta": {
            "title": "Reduced-order transient comparison for Scenario 2(M) and Scenario 3(M)",
            "status": "multinode_transient_comparison_v1",
            "assumption_note": (
                "This screen applies the same burst patterns and the same local-buffer assumptions to the two advanced "
                "multi-node scenarios. It compares source burst exposure, source ramp, minimum block voltage, and "
                "maximum segment current under reduced-order quasi-static network solves."
            ),
            "time_step_s": TIME_STEP_S,
            "simulation_duration_s": SIM_DURATION_S,
            "event_start_s": EVENT_START_S,
            "event_end_s": EVENT_END_S,
        },
        "buffer_configs": BUFFER_CONFIGS,
        "patterns": PATTERNS,
        "results": results,
        "comparison_rows": build_comparison_rows(results),
    }


def build_note(report: dict) -> str:
    def find(buffer_name: str, pattern_name: str) -> dict:
        return next(
            row for row in report["comparison_rows"] if row["buffer_name"] == buffer_name and row["pattern_name"] == pattern_name
        )

    coherent_none = find("no_local_buffer", "coherent_15pct_burst")
    coherent_mod = find("moderate_local_buffer", "coherent_15pct_burst")
    cluster_mod = find("moderate_local_buffer", "two_block_cluster_15pct_burst")
    oppose_strong = find("strong_local_buffer", "split_opposition_15pct_burst")

    return "\n".join(
        [
            "# Multi-node Transient Comparison",
            "",
            "This note turns the internal Scenario 3(M) transient screen into a direct Scenario 2(M) versus Scenario 3(M) comparison.",
            "",
            "## Main Result",
            "",
            f"- For a coherent 15% burst with no local buffer, Scenario 2(M) shows a source-input burst of `{coherent_none['scenario2m_max_source_delta_mw']:.2f} MW` and Scenario 3(M) shows `{coherent_none['scenario3m_max_source_delta_mw']:.2f} MW`.",
            f"- With the moderate local buffer, the same coherent burst gives Scenario 2(M) a source ramp of `{coherent_mod['scenario2m_max_source_ramp_mw_per_s']:.2f} MW/s` and Scenario 3(M) `{coherent_mod['scenario3m_max_source_ramp_mw_per_s']:.2f} MW/s`.",
            "",
            "## Internal Network Tradeoff",
            "",
            f"- Under the moderate two-block clustered burst, Scenario 2(M) reaches `{cluster_mod['scenario2m_max_segment_current_a']:.2f} A` maximum segment current while Scenario 3(M) reaches `{cluster_mod['scenario3m_max_segment_current_a']:.2f} A`.",
            f"- Under the strong-buffer split-opposition burst, Scenario 2(M) minimum block voltage is `{oppose_strong['scenario2m_min_block_voltage_pu']:.5f} pu` and Scenario 3(M) is `{oppose_strong['scenario3m_min_block_voltage_pu']:.5f} pu`.",
            "- Interpretation: Scenario 3(M) should be argued as an upstream burst-shaping architecture, not as an architecture that removes all internal dynamic stress.",
        ]
    )


def print_summary(report: dict) -> None:
    print("Reduced-order transient comparison: Scenario 2(M) vs Scenario 3(M)")
    print("------------------------------------------------------------------")
    rows = [[
        "Buffer",
        "Pattern",
        "S2 Delta MW",
        "S3 Delta MW",
        "S2 Ramp MW/s",
        "S3 Ramp MW/s",
        "S2 Min Vpu",
        "S3 Min Vpu",
    ]]
    for row in report["comparison_rows"]:
        rows.append(
            [
                row["buffer_name"],
                row["pattern_name"],
                f"{row['scenario2m_max_source_delta_mw']:.2f}",
                f"{row['scenario3m_max_source_delta_mw']:.2f}",
                f"{row['scenario2m_max_source_ramp_mw_per_s']:.2f}",
                f"{row['scenario3m_max_source_ramp_mw_per_s']:.2f}",
                f"{row['scenario2m_min_block_voltage_pu']:.5f}",
                f"{row['scenario3m_min_block_voltage_pu']:.5f}",
            ]
        )
    print(format_table(rows))


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run a reduced-order transient comparison for Scenario 2(M) and Scenario 3(M).")
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
