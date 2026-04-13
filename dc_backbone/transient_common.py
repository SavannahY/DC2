"""Shared reduced-order transient utilities for the DC backbone study."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Dict, List, Sequence

from dc_backbone_multinode_campus_model import (
    block_tap_input_mw,
    dynamic_load_vectors,
    solve_radial_ac_network,
    solve_radial_dc_network,
)


TIME_STEP_S = 0.01
SIM_DURATION_S = 1.5
EVENT_START_S = 0.25
EVENT_END_S = 0.45
RECOVERY_TOLERANCE_PU = 0.0005
RECOVERY_TOLERANCE_MW = 0.25

PATTERNS = [
    {"name": "coherent_15pct_burst", "mode": "coherent_campus", "amplitude_fraction": 0.15},
    {"name": "largest_block_15pct_burst", "mode": "largest_block_only", "amplitude_fraction": 0.15},
    {"name": "two_block_cluster_15pct_burst", "mode": "two_block_cluster", "amplitude_fraction": 0.15},
    {"name": "split_opposition_15pct_burst", "mode": "split_campus_opposition", "amplitude_fraction": 0.15},
]

LOCAL_BUFFER_CONFIGS = [
    {
        "name": "no_local_buffer",
        "display_name": "No local buffer",
        "power_mw_per_block": 0.0,
        "energy_kwh_per_block": 0.0,
        "smoothing_tau_s": 0.0,
    },
    {
        "name": "moderate_local_buffer",
        "display_name": "Moderate local buffer",
        "power_mw_per_block": 3.0,
        "energy_kwh_per_block": 0.25,
        "smoothing_tau_s": 0.25,
    },
    {
        "name": "strong_local_buffer",
        "display_name": "Strong local buffer",
        "power_mw_per_block": 5.0,
        "energy_kwh_per_block": 0.50,
        "smoothing_tau_s": 0.25,
    },
]


def write_json(path: Path, payload: dict) -> None:
    path.write_text(json.dumps(payload, indent=2), encoding="utf-8")


def target_it_profile(base_it_by_block: Dict[str, float], pattern: dict, time_s: float) -> Dict[str, float]:
    if EVENT_START_S <= time_s < EVENT_END_S:
        high, _ = dynamic_load_vectors(base_it_by_block, pattern["mode"], pattern["amplitude_fraction"])
        return high
    return dict(base_it_by_block)


def tap_targets_by_block(blocks, local_block_elements, assumptions, it_by_block: Dict[str, float]) -> Dict[str, float]:
    targets = {}
    for block in blocks:
        delivered_it_mw = float(it_by_block[block.name])
        targets[block.name] = block_tap_input_mw(local_block_elements, assumptions, delivered_it_mw)["tap_input_mw"]
    return targets


def update_buffer_state(
    target_power_mw: float,
    previous_seen_power_mw: float,
    energy_kwh: float,
    power_rating_mw: float,
    energy_capacity_kwh: float,
    smoothing_tau_s: float,
    dt_s: float,
) -> tuple[float, float, float]:
    if smoothing_tau_s <= 0.0 or power_rating_mw <= 0.0 or energy_capacity_kwh <= 0.0:
        return target_power_mw, 0.0, energy_kwh

    alpha = min(1.0, dt_s / smoothing_tau_s)
    unconstrained_seen_mw = previous_seen_power_mw + alpha * (target_power_mw - previous_seen_power_mw)
    desired_buffer_mw = target_power_mw - unconstrained_seen_mw

    max_discharge_mw = min(power_rating_mw, energy_kwh * 3600.0 / dt_s)
    max_charge_mw = min(power_rating_mw, (energy_capacity_kwh - energy_kwh) * 3600.0 / dt_s)
    buffer_power_mw = max(-max_charge_mw, min(max_discharge_mw, desired_buffer_mw))
    seen_power_mw = target_power_mw - buffer_power_mw
    next_energy_kwh = min(
        energy_capacity_kwh,
        max(0.0, energy_kwh - buffer_power_mw * dt_s / 3600.0),
    )
    return seen_power_mw, buffer_power_mw, next_energy_kwh


def solve_network(campus_architecture, assumptions: dict, topology: dict, segments, load_power_by_leaf_mw: Dict[str, float]) -> dict:
    if campus_architecture.kind == "dc":
        return solve_radial_dc_network(
            source_node=topology["source_node"],
            source_voltage_kv=campus_architecture.source_voltage_kv,
            segments=segments,
            load_power_by_leaf_mw=load_power_by_leaf_mw,
        )
    return solve_radial_ac_network(
        source_node=topology["source_node"],
        source_voltage_kv=campus_architecture.source_voltage_kv,
        segments=segments,
        load_power_by_leaf_mw=load_power_by_leaf_mw,
        power_factor=float(assumptions["global"].get("default_power_factor", 0.98)),
    )


def recovery_time(rows: List[dict], base_min_vpu: float, base_source_input_mw: float) -> float | None:
    for row in rows:
        if row["time_s"] < EVENT_END_S:
            continue
        if (
            row["min_block_voltage_pu"] >= base_min_vpu - RECOVERY_TOLERANCE_PU
            and abs(row["source_input_mw"] - base_source_input_mw) <= RECOVERY_TOLERANCE_MW
        ):
            return row["time_s"] - EVENT_END_S
    return None


def max_ramp_metric(rows: Sequence[dict], key: str) -> float:
    if len(rows) < 2:
        return 0.0
    max_ramp = 0.0
    for previous, current in zip(rows, rows[1:]):
        delta = abs(current[key] - previous[key])
        dt = current["time_s"] - previous["time_s"]
        if dt > 0.0:
            max_ramp = max(max_ramp, delta / dt)
    return max_ramp
