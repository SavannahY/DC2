#!/usr/bin/env python3
"""Equal-budget buffer-placement comparison for Scenario 2(M) and Scenario 3(M).

This script strengthens Benefit 3 more directly than the earlier transient
screens by comparing how the *same total buffer budget* performs when placed in
different locations:

- Scenario 2(M): local buffers only at each AC-fed SST block
- Scenario 3(M): local buffers only
- Scenario 3(M): hybrid placement with smaller local buffers plus one shared
  MVDC/front-end buffer

The question is architectural: does the MVDC backbone make the same total
buffer budget more effective at shaping the upstream source exposure?
"""

from __future__ import annotations

import argparse
from pathlib import Path

from dc_backbone.transient_common import (
    LOCAL_BUFFER_CONFIGS,
    PATTERNS,
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
DEFAULT_OUTPUT = ROOT / "buffer_placement_report.json"
DEFAULT_NOTE = ROOT / "BUFFER_PLACEMENT_ANALYSIS.md"

BUFFER_ARCHITECTURES = [
    {
        "name": "scenario2m_local_only",
        "display_name": "Scenario 2(M) local-only buffer",
        "scenario_name": "ac_fed_sst_800vdc",
        "scenario_label": "Scenario 2(M)",
        "local_power_mw_per_block": 3.0,
        "local_energy_kwh_per_block": 0.25,
        "local_tau_s": 0.25,
        "shared_power_mw": 0.0,
        "shared_energy_kwh": 0.0,
        "shared_tau_s": 0.0,
    },
    {
        "name": "scenario3m_local_only",
        "display_name": "Scenario 3(M) local-only buffer",
        "scenario_name": "proposed_mvdc_backbone",
        "scenario_label": "Scenario 3(M)",
        "local_power_mw_per_block": 3.0,
        "local_energy_kwh_per_block": 0.25,
        "local_tau_s": 0.25,
        "shared_power_mw": 0.0,
        "shared_energy_kwh": 0.0,
        "shared_tau_s": 0.0,
    },
    {
        "name": "scenario3m_hybrid_pooled",
        "display_name": "Scenario 3(M) hybrid pooled buffer",
        "scenario_name": "proposed_mvdc_backbone",
        "scenario_label": "Scenario 3(M) pooled",
        "local_power_mw_per_block": 1.0,
        "local_energy_kwh_per_block": 0.10,
        "local_tau_s": 0.25,
        "shared_power_mw": 8.0,
        "shared_energy_kwh": 0.60,
        "shared_tau_s": 0.20,
    },
]


def simulate_case(assumptions: dict, topology: dict, config: dict, pattern: dict) -> dict:
    architecture = architecture_for_multinode(assumptions, config["scenario_name"])
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
    base_source_output_mw = base_network["network_source_output_mw"]
    base_source_input_mw = evaluate_source_stage_input_mw(
        architecture.source_stage_elements,
        assumptions,
        base_source_output_mw,
    )
    base_min_vpu = min(
        base_network["node_voltage_kv"][f"block::{block.name}"] / architecture.source_voltage_kv for block in blocks
    )

    seen_tap_by_block = dict(base_targets)
    local_energy_by_block = {
        block.name: 0.5 * float(config["local_energy_kwh_per_block"]) for block in blocks
    }
    shared_seen_output_mw = base_source_output_mw
    shared_energy_kwh = 0.5 * float(config["shared_energy_kwh"])

    step_rows = []
    max_source_input_mw = base_source_input_mw
    max_segment_current_a = max(base_network["segment_current_a"].values())
    min_block_voltage_pu = base_min_vpu
    max_local_discharge_mw = 0.0
    max_shared_discharge_mw = 0.0

    time_s = 0.0
    while time_s <= 1.5 + 1e-12:
        it_profile = target_it_profile(base_it_by_block, pattern, time_s)
        target_taps = tap_targets_by_block(blocks, architecture.local_block_elements, assumptions, it_profile)

        local_discharge_mw = 0.0
        for block in blocks:
            seen_tap, buffer_power, next_energy = update_buffer_state(
                target_power_mw=target_taps[block.name],
                previous_seen_power_mw=seen_tap_by_block[block.name],
                energy_kwh=local_energy_by_block[block.name],
                power_rating_mw=float(config["local_power_mw_per_block"]),
                energy_capacity_kwh=float(config["local_energy_kwh_per_block"]),
                smoothing_tau_s=float(config["local_tau_s"]),
                dt_s=TIME_STEP_S,
            )
            seen_tap_by_block[block.name] = seen_tap
            local_energy_by_block[block.name] = next_energy
            if buffer_power > 0.0:
                local_discharge_mw += buffer_power

        network = solve_network(
            architecture,
            assumptions,
            topology,
            segments,
            {block.leaf_node: seen_tap_by_block[block.name] for block in blocks},
        )
        source_output_target_mw = network["network_source_output_mw"]
        source_seen_output_mw, shared_buffer_power_mw, shared_energy_kwh = update_buffer_state(
            target_power_mw=source_output_target_mw,
            previous_seen_power_mw=shared_seen_output_mw,
            energy_kwh=shared_energy_kwh,
            power_rating_mw=float(config["shared_power_mw"]),
            energy_capacity_kwh=float(config["shared_energy_kwh"]),
            smoothing_tau_s=float(config["shared_tau_s"]),
            dt_s=TIME_STEP_S,
        )
        shared_seen_output_mw = source_seen_output_mw
        source_input_mw = evaluate_source_stage_input_mw(
            architecture.source_stage_elements,
            assumptions,
            source_seen_output_mw,
        )
        block_voltage_pu = {
            block.name: network["node_voltage_kv"][block.leaf_node] / architecture.source_voltage_kv for block in blocks
        }
        local_min_block_vpu = min(block_voltage_pu.values())
        local_max_segment_current = max(network["segment_current_a"].values())

        max_source_input_mw = max(max_source_input_mw, source_input_mw)
        max_segment_current_a = max(max_segment_current_a, local_max_segment_current)
        min_block_voltage_pu = min(min_block_voltage_pu, local_min_block_vpu)
        max_local_discharge_mw = max(max_local_discharge_mw, local_discharge_mw)
        max_shared_discharge_mw = max(max_shared_discharge_mw, max(0.0, shared_buffer_power_mw))

        step_rows.append(
            {
                "time_s": round(time_s, 4),
                "source_input_mw": source_input_mw,
                "source_output_mw": source_seen_output_mw,
                "min_block_voltage_pu": local_min_block_vpu,
                "max_segment_current_a": local_max_segment_current,
                "local_buffer_discharge_mw": local_discharge_mw,
                "shared_buffer_discharge_mw": max(0.0, shared_buffer_power_mw),
            }
        )
        time_s += TIME_STEP_S

    return {
        "buffer_architecture": config,
        "pattern_name": pattern["name"],
        "mode": pattern["mode"],
        "it_amplitude_fraction": pattern["amplitude_fraction"],
        "base_case": {
            "source_input_mw": base_source_input_mw,
            "min_block_voltage_pu": base_min_vpu,
        },
        "summary": {
            "max_source_input_delta_mw": max_source_input_mw - base_source_input_mw,
            "max_source_input_ramp_mw_per_s": max_ramp_metric(step_rows, "source_input_mw"),
            "min_block_voltage_pu": min_block_voltage_pu,
            "max_segment_current_a": max_segment_current_a,
            "max_local_buffer_discharge_mw": max_local_discharge_mw,
            "max_shared_buffer_discharge_mw": max_shared_discharge_mw,
            "recovery_time_s": recovery_time(step_rows, base_min_vpu, base_source_input_mw),
        },
        "step_rows": step_rows,
    }


def build_comparison_rows(results: list[dict]) -> list[dict]:
    grouped = {}
    for row in results:
        grouped.setdefault(row["pattern_name"], {})[row["buffer_architecture"]["name"]] = row

    rows = []
    for pattern_name, group in sorted(grouped.items()):
        if not all(key in group for key in ("scenario2m_local_only", "scenario3m_local_only", "scenario3m_hybrid_pooled")):
            continue
        s2 = group["scenario2m_local_only"]["summary"]
        s3_local = group["scenario3m_local_only"]["summary"]
        s3_pool = group["scenario3m_hybrid_pooled"]["summary"]
        rows.append(
            {
                "pattern_name": pattern_name,
                "scenario2m_local_delta_mw": s2["max_source_input_delta_mw"],
                "scenario3m_local_delta_mw": s3_local["max_source_input_delta_mw"],
                "scenario3m_pooled_delta_mw": s3_pool["max_source_input_delta_mw"],
                "scenario2m_local_ramp_mw_per_s": s2["max_source_input_ramp_mw_per_s"],
                "scenario3m_local_ramp_mw_per_s": s3_local["max_source_input_ramp_mw_per_s"],
                "scenario3m_pooled_ramp_mw_per_s": s3_pool["max_source_input_ramp_mw_per_s"],
                "scenario2m_local_min_vpu": s2["min_block_voltage_pu"],
                "scenario3m_local_min_vpu": s3_local["min_block_voltage_pu"],
                "scenario3m_pooled_min_vpu": s3_pool["min_block_voltage_pu"],
            }
        )
    return rows


def build_report(assumptions: dict, topology: dict) -> dict:
    results = []
    for config in BUFFER_ARCHITECTURES:
        for pattern in PATTERNS:
            results.append(simulate_case(assumptions, topology, config, pattern))
    return {
        "meta": {
            "title": "Equal-budget buffer-placement comparison",
            "status": "buffer_placement_comparison_v1",
            "assumption_note": (
                "Scenario 2(M) and Scenario 3(M) are compared under the same total buffer budget. "
                "Scenario 2(M) is restricted to local block buffers. Scenario 3(M) is also tested with a "
                "hybrid placement that splits the same total budget between smaller local buffers and one shared "
                "MVDC/front-end buffer."
            ),
        },
        "buffer_architectures": BUFFER_ARCHITECTURES,
        "patterns": PATTERNS,
        "results": results,
        "comparison_rows": build_comparison_rows(results),
    }


def build_note(report: dict) -> str:
    coherent = next(row for row in report["comparison_rows"] if row["pattern_name"] == "coherent_15pct_burst")
    cluster = next(row for row in report["comparison_rows"] if row["pattern_name"] == "two_block_cluster_15pct_burst")
    opposition = next(row for row in report["comparison_rows"] if row["pattern_name"] == "split_opposition_15pct_burst")
    return "\n".join(
        [
            "# Buffer Placement Comparison",
            "",
            "This note tests whether the MVDC architecture makes the same total buffer budget more effective by enabling pooled placement.",
            "",
            "## Main Result",
            "",
            f"- Under a coherent 15% burst, Scenario 2(M) with local-only buffering reaches `{coherent['scenario2m_local_delta_mw']:.2f} MW` source burst and `{coherent['scenario2m_local_ramp_mw_per_s']:.2f} MW/s` source ramp.",
            f"- Scenario 3(M) with the same local-only budget reaches `{coherent['scenario3m_local_delta_mw']:.2f} MW` and `{coherent['scenario3m_local_ramp_mw_per_s']:.2f} MW/s`.",
            f"- Scenario 3(M) with the same total budget but pooled placement reaches `{coherent['scenario3m_pooled_delta_mw']:.2f} MW` and `{coherent['scenario3m_pooled_ramp_mw_per_s']:.2f} MW/s`. That is a modest improvement for a fully coherent burst, because all blocks move in the same direction at once.",
            "",
            "## Interpretation",
            "",
            f"- Under the two-block clustered burst, Scenario 2(M) local-only buffering gives `{cluster['scenario2m_local_ramp_mw_per_s']:.2f} MW/s`, while the pooled Scenario 3(M) case drops to `{cluster['scenario3m_pooled_ramp_mw_per_s']:.2f} MW/s` with minimum block voltage still near nominal at `{cluster['scenario3m_pooled_min_vpu']:.5f} pu`.",
            f"- Under the split-opposition burst, Scenario 2(M) local-only buffering gives `{opposition['scenario2m_local_ramp_mw_per_s']:.2f} MW/s`, while the pooled Scenario 3(M) case drops to `{opposition['scenario3m_pooled_ramp_mw_per_s']:.2f} MW/s`.",
            "- This is the stronger architectural Benefit 3 argument: the MVDC backbone makes pooled buffering materially more effective when campus subloads do not move coherently, which is exactly where a shared DC backbone should create value.",
        ]
    )


def print_summary(report: dict) -> None:
    print("Equal-budget buffer-placement comparison")
    print("--------------------------------------")
    rows = [[
        "Pattern",
        "S2 Local Delta",
        "S3 Local Delta",
        "S3 Pooled Delta",
        "S2 Local Ramp",
        "S3 Local Ramp",
        "S3 Pooled Ramp",
    ]]
    for row in report["comparison_rows"]:
        rows.append(
            [
                row["pattern_name"],
                f"{row['scenario2m_local_delta_mw']:.2f}",
                f"{row['scenario3m_local_delta_mw']:.2f}",
                f"{row['scenario3m_pooled_delta_mw']:.2f}",
                f"{row['scenario2m_local_ramp_mw_per_s']:.2f}",
                f"{row['scenario3m_local_ramp_mw_per_s']:.2f}",
                f"{row['scenario3m_pooled_ramp_mw_per_s']:.2f}",
            ]
        )
    print(format_table(rows))


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run an equal-budget buffer-placement comparison for Scenario 2(M) and Scenario 3(M).")
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
