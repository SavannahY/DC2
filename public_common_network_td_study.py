#!/usr/bin/env python3
"""Public common-network T&D study for Scenario 2(M) and Scenario 3(M).

This script is the second public-data-only reviewer-response layer. It places
the advanced AC-fed SST baseline and the proposed MVDC backbone on the same
public SMART-DS feeder model and compares them on:

- annualized incremental feeder losses,
- peak-bin branch loading,
- POI voltage sensitivity,
- MIT-derived burst sensitivity,
- and surviving N-1 contingency performance.

The study uses a public SMART-DS feeder snapshot model. This is still not a
utility-specific interconnection study, but it is materially stronger than the
earlier surrogate feeder cross-checks because both scenarios live on the same
published T&D network.
"""

from __future__ import annotations

import argparse
import heapq
import json
import math
import re
from pathlib import Path
from typing import Dict, Iterable, List, Sequence

import opendssdirect as dss

from dc_backbone_model import format_gwh, format_money_millions, format_pct, format_table, load_json
from dc_backbone_multinode_campus_model import (
    architecture_for_multinode,
    block_tap_input_mw,
    build_network,
    evaluate_source_stage_input_mw,
    load_topology,
    solve_radial_dc_network,
)

ROOT = Path(__file__).resolve().parent

DEFAULT_ASSUMPTIONS = ROOT / "scientific_assumptions_v1.json"
DEFAULT_TOPOLOGY = ROOT / "multinode_campus_topology.json"
DEFAULT_OPERATING_REPORT = ROOT / "public_ai_factory_operating_report.json"
DEFAULT_SMARTDS_DIR = ROOT / "public_data" / "smart_ds_sfo_sample"
DEFAULT_OUTPUT_JSON = ROOT / "public_common_network_td_report.json"
DEFAULT_OUTPUT_NOTE = ROOT / "PUBLIC_COMMON_NETWORK_TD_STUDY.md"

SMARTDS_MASTER = "Master.dss"
SMARTDS_LOADS = "Loads.dss"
SMARTDS_SNAPSHOT_LOADS = "Loads_snapshot.dss"
ANNUAL_SUMMARY_TOP_BINS = 4
SURVIVING_N_MINUS_1_LIMIT = 6
DEFAULT_POWER_FACTOR = 0.99
MIN_CONNECTED_VPU = 0.80
DEFAULT_TARGET_PEAK_FEEDER_LOADING = 0.80


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--assumptions", type=Path, default=DEFAULT_ASSUMPTIONS)
    parser.add_argument("--topology", type=Path, default=DEFAULT_TOPOLOGY)
    parser.add_argument("--operating-report", type=Path, default=DEFAULT_OPERATING_REPORT)
    parser.add_argument("--smartds-dir", type=Path, default=DEFAULT_SMARTDS_DIR)
    parser.add_argument("--output-json", type=Path, default=DEFAULT_OUTPUT_JSON)
    parser.add_argument("--output-note", type=Path, default=DEFAULT_OUTPUT_NOTE)
    parser.add_argument("--power-factor", type=float, default=DEFAULT_POWER_FACTOR)
    parser.add_argument(
        "--target-peak-feeder-loading",
        type=float,
        default=DEFAULT_TARGET_PEAK_FEEDER_LOADING,
        help="Target fraction of base feeder MW used to size the equivalent feeder-bank count.",
    )
    parser.add_argument("--details", action="store_true")
    return parser.parse_args()


def write_json(path: Path, payload: dict) -> None:
    path.write_text(json.dumps(payload, indent=2), encoding="utf-8")


def ensure_snapshot_loads(smartds_dir: Path) -> Path:
    source = smartds_dir / SMARTDS_LOADS
    target = smartds_dir / SMARTDS_SNAPSHOT_LOADS
    text = source.read_text(encoding="utf-8")
    text = re.sub(r"\s+yearly=[^\s]+", "", text)
    text = re.sub(r"\s+daily=[^\s]+", "", text)
    text = re.sub(r"\s+duty=[^\s]+", "", text)
    target.write_text(text, encoding="utf-8")
    return target


def parse_master_source_command(master_path: Path) -> str:
    for line in master_path.read_text(encoding="utf-8").splitlines():
        stripped = line.strip()
        if stripped.lower().startswith("new circuit."):
            return stripped
    raise RuntimeError(f"Could not find the `New Circuit` command in {master_path}")


def load_snapshot_feeder(smartds_dir: Path, extra_commands: Sequence[str] = ()) -> None:
    master_path = smartds_dir / SMARTDS_MASTER
    loads_snapshot = ensure_snapshot_loads(smartds_dir)
    source_command = parse_master_source_command(master_path)

    commands = [
        "Clear",
        source_command,
        f"Redirect {smartds_dir / 'LineCodes.dss'}",
        f"Redirect {smartds_dir / 'Lines.dss'}",
        f"Redirect {smartds_dir / 'Transformers.dss'}",
        f"Redirect {loads_snapshot}",
        f"Redirect {smartds_dir / 'Capacitors.dss'}",
        "Set Voltagebases=[0.12, 0.208, 0.48, 7.2, 12.47]",
        "Calcvoltagebases",
    ]
    commands.extend(extra_commands)
    commands.append("Solve mode=snapshot")

    dss.Basic.ClearAll()
    for command in commands:
        dss.Text.Command(command)

    if not dss.Solution.Converged():
        raise RuntimeError("SMART-DS snapshot feeder did not converge")


def bus_kvbase(bus_name: str) -> float:
    dss.Circuit.SetActiveBus(bus_name)
    return float(dss.Bus.kVBase())


def bus_phase_nodes(bus_name: str) -> list[int]:
    dss.Circuit.SetActiveBus(bus_name)
    return [node for node in dss.Bus.Nodes() if node > 0]


def line_graph() -> dict:
    graph: Dict[str, List[dict]] = {}
    for line_name in dss.Lines.AllNames():
        dss.Lines.Name(line_name)
        bus1 = dss.Lines.Bus1().split(".")[0].lower()
        bus2 = dss.Lines.Bus2().split(".")[0].lower()
        graph.setdefault(bus1, []).append({"to": bus2, "line_name": line_name})
        graph.setdefault(bus2, []).append({"to": bus1, "line_name": line_name})
    return graph


def hv_candidate_buses(graph: dict, source_bus: str) -> list[dict]:
    source_bus = source_bus.lower()
    distances = {source_bus: 0}
    queue = [(0, source_bus)]
    while queue:
        distance, bus = heapq.heappop(queue)
        if distance != distances[bus]:
            continue
        for edge in graph.get(bus, []):
            candidate = edge["to"]
            next_distance = distance + 1
            if next_distance < distances.get(candidate, 10**9):
                distances[candidate] = next_distance
                heapq.heappush(queue, (next_distance, candidate))

    rows = []
    for bus_name in dss.Circuit.AllBusNames():
        lowered = bus_name.lower()
        if lowered not in distances:
            continue
        kvbase = bus_kvbase(bus_name)
        phases = bus_phase_nodes(bus_name)
        if abs(kvbase - 7.2) > 0.05:
            continue
        if sorted(set(phases)) != [1, 2, 3]:
            continue
        rows.append(
            {
                "bus": lowered,
                "hop_distance": int(distances[lowered]),
                "degree": len(graph.get(lowered, [])),
            }
        )
    return rows


def choose_pois(graph: dict, source_bus: str) -> dict:
    hv_rows = hv_candidate_buses(graph, source_bus)
    if not hv_rows:
        raise RuntimeError("No 12.47-kV-class three-phase buses were found in the SMART-DS feeder.")

    central_candidates = [row for row in hv_rows if row["hop_distance"] > 0]
    central_candidates.sort(key=lambda row: (row["hop_distance"], -row["degree"], row["bus"]))
    central_bus = central_candidates[0]["bus"]

    def canonical_root(bus_name: str) -> str:
        matches = re.findall(r"p12udt\d+", bus_name)
        return matches[-1] if matches else bus_name

    distributed_candidates = [row for row in hv_rows if row["degree"] == 1 and row["hop_distance"] >= 2]
    if len(distributed_candidates) < 4:
        distributed_candidates = [row for row in hv_rows if row["hop_distance"] >= 2]

    distributed_candidates.sort(
        key=lambda row: (
            row["hop_distance"],
            row["degree"] == 1,
            "-" not in row["bus"],
            "xxx" not in row["bus"],
            row["bus"],
        ),
        reverse=True,
    )
    distributed_buses = []
    seen = set()
    seen_roots = set()
    for row in distributed_candidates:
        root = canonical_root(row["bus"])
        if row["bus"] in seen or row["bus"] == central_bus or root in seen_roots:
            continue
        distributed_buses.append(row["bus"])
        seen.add(row["bus"])
        seen_roots.add(root)
        if len(distributed_buses) == 4:
            break
    if len(distributed_buses) < 4:
        raise RuntimeError("Could not identify four distributed medium-voltage candidate POIs on the SMART-DS feeder.")

    return {
        "source_bus": source_bus.lower(),
        "central_bus": central_bus,
        "distributed_buses": distributed_buses,
    }


def line_loading_rows() -> list[dict]:
    rows = []
    for line_name in dss.Lines.AllNames():
        dss.Lines.Name(line_name)
        bus1 = dss.Lines.Bus1().split(".")[0]
        bus2 = dss.Lines.Bus2().split(".")[0]
        currents = dss.CktElement.CurrentsMagAng()
        magnitude_values = currents[0::2]
        terminal_currents = magnitude_values[: max(1, len(magnitude_values) // 2)]
        peak_current = max(terminal_currents) if terminal_currents else 0.0
        normal_amps = float(dss.CktElement.NormalAmps())
        loading_pct = 100.0 * peak_current / normal_amps if normal_amps > 0.0 else 0.0
        losses_kw = dss.CktElement.Losses()[0] / 1000.0
        rows.append(
            {
                "line_name": line_name,
                "bus1": bus1,
                "bus2": bus2,
                "peak_current_a": peak_current,
                "normal_amps": normal_amps,
                "loading_pct": loading_pct,
                "loss_kw": losses_kw,
            }
        )
    rows.sort(key=lambda row: row["loading_pct"], reverse=True)
    return rows


def system_voltage_rows() -> list[dict]:
    rows = []
    for bus_name in dss.Circuit.AllBusNames():
        dss.Circuit.SetActiveBus(bus_name)
        kvbase = dss.Bus.kVBase()
        if kvbase <= 0.0:
            continue
        pu_values = dss.Bus.puVmagAngle()[0::2]
        rows.append(
            {
                "bus": bus_name,
                "kvbase_ln": kvbase,
                "min_vpu": min(pu_values) if pu_values else 0.0,
                "max_vpu": max(pu_values) if pu_values else 0.0,
            }
        )
    rows.sort(key=lambda row: row["min_vpu"])
    return rows


def feeder_base_summary() -> dict:
    line_rows = line_loading_rows()
    voltage_rows = system_voltage_rows()
    losses_kw, losses_kvar = dss.Circuit.Losses()
    total_kw, total_kvar = dss.Circuit.TotalPower()
    return {
        "bus_count": len(dss.Circuit.AllBusNames()),
        "line_count": len(dss.Lines.AllNames()),
        "load_count": dss.Loads.Count(),
        "total_power_kw": -float(total_kw),
        "total_power_kvar": -float(total_kvar),
        "total_losses_kw": float(losses_kw) / 1000.0,
        "total_losses_kvar": float(losses_kvar) / 1000.0,
        "max_line_loading_pct": line_rows[0]["loading_pct"],
        "worst_line": line_rows[0],
        "min_system_vpu": voltage_rows[0]["min_vpu"],
        "worst_bus": voltage_rows[0],
    }


def kvar_for_power_factor(kw: float, power_factor: float) -> float:
    if power_factor <= 0.0 or power_factor > 1.0:
        raise ValueError("power_factor must be in (0, 1]")
    angle = math.acos(power_factor)
    return kw * math.tan(angle)


def add_campus_loads(load_map_kw: Dict[str, float], power_factor: float, load_prefix: str) -> None:
    for index, (bus_name, kw) in enumerate(load_map_kw.items(), start=1):
        kvar = kvar_for_power_factor(kw, power_factor)
        dss.Text.Command(
            "New Load.{name}_{idx} phases=3 conn=wye bus1={bus}.1.2.3 "
            "kV=12.47 model=1 kW={kw:.6f} kvar={kvar:.6f}".format(
                name=load_prefix,
                idx=index,
                bus=bus_name,
                kw=kw,
                kvar=kvar,
            )
        )


def load_map_for_scenario(
    scenario_label: str,
    load_fraction: float,
    assumptions: dict,
    topology: dict,
    poi_definition: dict,
) -> dict:
    if scenario_label == "Scenario 2(M)":
        architecture = architecture_for_multinode(assumptions, "ac_fed_sst_800vdc")
        per_block_kw: Dict[str, float] = {}
        for block_record, bus_name in zip(topology["blocks"], poi_definition["distributed_buses"]):
            delivered_it_mw = float(block_record["it_load_mw"]) * load_fraction
            tap = block_tap_input_mw(architecture.local_block_elements, assumptions, delivered_it_mw)
            per_block_kw[bus_name] = tap["tap_input_mw"] * 1000.0
        return per_block_kw

    if scenario_label != "Scenario 3(M)":
        raise ValueError(f"Unsupported scenario label: {scenario_label}")

    architecture = architecture_for_multinode(assumptions, "proposed_mvdc_backbone")
    segments, blocks = build_network(topology, architecture, assumptions)
    leaf_loads = {}
    for block in blocks:
        base_record = next(record for record in topology["blocks"] if record["name"] == block.name)
        delivered_it_mw = float(base_record["it_load_mw"]) * load_fraction
        tap = block_tap_input_mw(architecture.local_block_elements, assumptions, delivered_it_mw)
        leaf_loads[block.leaf_node] = tap["tap_input_mw"]

    dc_network = solve_radial_dc_network(
        topology["source_node"],
        architecture.source_voltage_kv,
        segments,
        leaf_loads,
    )
    ac_input_mw = evaluate_source_stage_input_mw(
        architecture.source_stage_elements,
        assumptions,
        dc_network["network_source_output_mw"],
    )
    return {poi_definition["central_bus"]: ac_input_mw * 1000.0}


def scenario_snapshot(
    smartds_dir: Path,
    assumptions: dict,
    topology: dict,
    poi_definition: dict,
    scenario_label: str,
    load_fraction: float,
    power_factor: float,
    feeder_bank_count: int,
    open_line_name: str | None = None,
) -> dict:
    extra_commands = []
    if open_line_name:
        extra_commands.append(f"Open Line.{open_line_name} term=1")
    load_snapshot_feeder(smartds_dir, extra_commands=extra_commands)

    raw_load_map_kw = load_map_for_scenario(scenario_label, load_fraction, assumptions, topology, poi_definition)
    load_map_kw = {bus: kw / feeder_bank_count for bus, kw in raw_load_map_kw.items()}
    add_campus_loads(load_map_kw, power_factor, load_prefix=scenario_label.replace(" ", "_").replace("(", "").replace(")", ""))
    dss.Text.Command("Solve mode=snapshot")

    converged = bool(dss.Solution.Converged())
    line_rows = line_loading_rows()
    voltage_rows = system_voltage_rows()
    losses_kw, losses_kvar = dss.Circuit.Losses()
    total_kw, total_kvar = dss.Circuit.TotalPower()

    poi_voltage_rows = []
    for bus_name in load_map_kw:
        dss.Circuit.SetActiveBus(bus_name)
        pu_values = dss.Bus.puVmagAngle()[0::2]
        poi_voltage_rows.append(
            {
                "bus": bus_name,
                "min_vpu": min(pu_values) if pu_values else 0.0,
                "max_vpu": max(pu_values) if pu_values else 0.0,
            }
        )
    poi_voltage_rows.sort(key=lambda row: row["min_vpu"])

    return {
        "scenario_label": scenario_label,
        "load_fraction": load_fraction,
        "feeder_bank_count": feeder_bank_count,
        "open_line_name": open_line_name,
        "converged": converged,
        "campus_load_map_kw": load_map_kw,
        "raw_campus_load_map_kw": raw_load_map_kw,
        "campus_total_kw": sum(load_map_kw.values()),
        "raw_campus_total_kw": sum(raw_load_map_kw.values()),
        "total_power_kw": -float(total_kw),
        "total_power_kvar": -float(total_kvar),
        "total_losses_kw": float(losses_kw) / 1000.0,
        "total_losses_kvar": float(losses_kvar) / 1000.0,
        "max_line_loading_pct": line_rows[0]["loading_pct"],
        "worst_line": line_rows[0],
        "min_system_vpu": voltage_rows[0]["min_vpu"],
        "worst_bus": voltage_rows[0],
        "poi_voltage_rows": poi_voltage_rows,
        "min_poi_vpu": poi_voltage_rows[0]["min_vpu"] if poi_voltage_rows else 0.0,
        "top_lines": line_rows[:10],
    }


def annualized_study(
    smartds_dir: Path,
    assumptions: dict,
    topology: dict,
    poi_definition: dict,
    operating_report: dict,
    power_factor: float,
    feeder_bank_count: int,
) -> dict:
    load_bins = operating_report["annual_layer"]["esif_profile"]["load_profile"]
    scenario_labels = ["Scenario 2(M)", "Scenario 3(M)"]
    scenarios = {label: [] for label in scenario_labels}
    total_hours = 0.0

    for load_bin in load_bins:
        hours = float(load_bin["hours_fraction"]) * 8760.0
        total_hours += hours
        load_fraction = float(load_bin["load_fraction"])
        for label in scenario_labels:
            snapshot = scenario_snapshot(
                smartds_dir,
                assumptions,
                topology,
                poi_definition,
                label,
                load_fraction,
                power_factor,
                feeder_bank_count,
            )
            snapshot["hours"] = hours
            snapshot["bin_name"] = load_bin["name"]
            scenarios[label].append(snapshot)

    summary = {}
    for label, rows in scenarios.items():
        weighted_loss_mwh = sum(row["total_losses_kw"] * row["hours"] / 1000.0 for row in rows)
        weighted_campus_loss_mwh = sum(
            (row["total_losses_kw"] - base_losses_for_fraction(smartds_dir, row["load_fraction"])) * feeder_bank_count * row["hours"] / 1000.0
            for row in rows
        )
        peak = max(rows, key=lambda row: row["load_fraction"])
        top_bins = sorted(rows, key=lambda row: row["load_fraction"], reverse=True)[:ANNUAL_SUMMARY_TOP_BINS]
        summary[label] = {
            "weighted_total_losses_mwh": weighted_loss_mwh,
            "weighted_incremental_losses_mwh": weighted_campus_loss_mwh,
            "weighted_incremental_losses_per_bank_mwh": sum(
                (row["total_losses_kw"] - base_losses_for_fraction(smartds_dir, row["load_fraction"])) * row["hours"] / 1000.0
                for row in rows
            ),
            "peak_bin": peak,
            "weighted_mean_max_line_loading_pct": sum(row["max_line_loading_pct"] * row["hours"] for row in rows) / total_hours,
            "worst_peak_line_loading_pct": max(row["max_line_loading_pct"] for row in rows),
            "worst_peak_poi_vpu": min(row["min_poi_vpu"] for row in rows),
            "top_bins": top_bins,
        }
    return summary


_BASE_LOSS_CACHE: Dict[float, float] = {}


def base_losses_for_fraction(smartds_dir: Path, load_fraction: float) -> float:
    if load_fraction in _BASE_LOSS_CACHE:
        return _BASE_LOSS_CACHE[load_fraction]
    load_snapshot_feeder(smartds_dir)
    dss.Text.Command(f"Set LoadMult={load_fraction:.6f}")
    dss.Text.Command("Solve mode=snapshot")
    if not dss.Solution.Converged():
        raise RuntimeError("Base feeder did not converge under scaled load multiplier")
    losses_kw = dss.Circuit.Losses()[0] / 1000.0
    _BASE_LOSS_CACHE[load_fraction] = float(losses_kw)
    return _BASE_LOSS_CACHE[load_fraction]


def burst_sensitivity_study(
    smartds_dir: Path,
    assumptions: dict,
    topology: dict,
    poi_definition: dict,
    operating_report: dict,
    power_factor: float,
    feeder_bank_count: int,
) -> list[dict]:
    p95_fraction = float(operating_report["annual_layer"]["esif_profile"]["meta"]["normalized_p95_fraction"])
    burst_cases = [
        case
        for case in operating_report["mit_ai_burst_layer"]["burst_summary"]["derived_cases"]
        if case["name"].endswith("p95")
    ]
    rows = []
    for case in burst_cases:
        for label in ["Scenario 2(M)", "Scenario 3(M)"]:
            base = scenario_snapshot(
                smartds_dir,
                assumptions,
                topology,
                poi_definition,
                label,
                p95_fraction,
                power_factor,
                feeder_bank_count,
            )
            burst_fraction = p95_fraction * (1.0 + float(case["fraction_of_p95_active_gpu"]))
            burst = scenario_snapshot(
                smartds_dir,
                assumptions,
                topology,
                poi_definition,
                label,
                burst_fraction,
                power_factor,
                feeder_bank_count,
            )
            rows.append(
                {
                    "scenario_label": label,
                    "case_name": case["name"],
                    "window_seconds": case["window_seconds"],
                    "positive_event_fraction": case["positive_event_fraction"],
                    "base_load_fraction": p95_fraction,
                    "burst_load_fraction": burst_fraction,
                    "delta_total_power_kw": burst["total_power_kw"] - base["total_power_kw"],
                    "delta_max_line_loading_pct_points": burst["max_line_loading_pct"] - base["max_line_loading_pct"],
                    "delta_min_poi_vpu": burst["min_poi_vpu"] - base["min_poi_vpu"],
                    "base_min_poi_vpu": base["min_poi_vpu"],
                    "burst_min_poi_vpu": burst["min_poi_vpu"],
                    "base_max_line_loading_pct": base["max_line_loading_pct"],
                    "burst_max_line_loading_pct": burst["max_line_loading_pct"],
                }
            )
    return rows


def n_minus_one_study(
    smartds_dir: Path,
    assumptions: dict,
    topology: dict,
    poi_definition: dict,
    operating_report: dict,
    power_factor: float,
    feeder_bank_count: int,
) -> dict:
    peak_fraction = max(float(bin_row["load_fraction"]) for bin_row in operating_report["annual_layer"]["esif_profile"]["load_profile"])
    scenario_rows = {}
    for label in ["Scenario 2(M)", "Scenario 3(M)"]:
        base = scenario_snapshot(
            smartds_dir,
            assumptions,
            topology,
            poi_definition,
            label,
            peak_fraction,
            power_factor,
            feeder_bank_count,
        )
        candidate_lines = [row["line_name"] for row in base["top_lines"][:10]]
        surviving = []
        failed = []
        for line_name in candidate_lines:
            result = scenario_snapshot(
                smartds_dir,
                assumptions,
                topology,
                poi_definition,
                label,
                peak_fraction,
                power_factor,
                feeder_bank_count,
                open_line_name=line_name,
            )
            connected = result["converged"] and result["min_poi_vpu"] >= MIN_CONNECTED_VPU
            entry = {
                "line_name": line_name,
                "connected": connected,
                "max_line_loading_pct": result["max_line_loading_pct"],
                "min_poi_vpu": result["min_poi_vpu"],
                "min_system_vpu": result["min_system_vpu"],
                "worst_line": result["worst_line"]["line_name"],
            }
            if connected:
                surviving.append(entry)
            else:
                failed.append(entry)
        surviving.sort(key=lambda row: (row["min_poi_vpu"], -row["max_line_loading_pct"]))
        scenario_rows[label] = {
            "peak_load_fraction": peak_fraction,
            "base": base,
            "candidate_outages": candidate_lines,
            "surviving_contingencies": surviving[:SURVIVING_N_MINUS_1_LIMIT],
            "surviving_count": len(surviving),
            "failed_or_disconnected_count": len(failed),
            "worst_surviving": surviving[0] if surviving else None,
        }
    return scenario_rows


def build_report(args: argparse.Namespace) -> dict:
    assumptions = load_json(args.assumptions)
    topology = load_topology(args.topology)
    operating_report = load_json(args.operating_report)

    load_snapshot_feeder(args.smartds_dir)
    base_summary = feeder_base_summary()
    graph = line_graph()
    pois = choose_pois(graph, dss.Circuit.AllBusNames()[0])
    peak_fraction = max(float(bin_row["load_fraction"]) for bin_row in operating_report["annual_layer"]["esif_profile"]["load_profile"])
    raw_peak_s2 = load_map_for_scenario("Scenario 2(M)", peak_fraction, assumptions, topology, pois)
    feeder_bank_count = max(
        1,
        math.ceil(sum(raw_peak_s2.values()) / (args.target_peak_feeder_loading * base_summary["total_power_kw"])),
    )

    annual_summary = annualized_study(
        args.smartds_dir,
        assumptions,
        topology,
        pois,
        operating_report,
        args.power_factor,
        feeder_bank_count,
    )
    burst_summary = burst_sensitivity_study(
        args.smartds_dir,
        assumptions,
        topology,
        pois,
        operating_report,
        args.power_factor,
        feeder_bank_count,
    )
    n_minus_one = n_minus_one_study(
        args.smartds_dir,
        assumptions,
        topology,
        pois,
        operating_report,
        args.power_factor,
        feeder_bank_count,
    )

    return {
        "meta": {
            "title": "Public common-network T&D study on a SMART-DS feeder",
            "updated": "2026-04-11",
            "note": (
                "This is a public common-network T&D screen. Scenario 2(M) is represented as "
                "four distributed AC-fed SST block interfaces on the same feeder. Scenario 3(M) "
                "is represented as one centralized AC/DC front-end interface on the same feeder."
            ),
            "dataset": "SMART-DS SFO P12U feeder sample",
        },
        "dataset": {
            "smartds_dir": str(args.smartds_dir),
            "operating_report": str(args.operating_report),
            "power_factor": args.power_factor,
            "feeder_bank_count": feeder_bank_count,
            "target_peak_feeder_loading": args.target_peak_feeder_loading,
        },
        "feeder_base_summary": base_summary,
        "poi_definition": pois,
        "annual_summary": annual_summary,
        "burst_summary": burst_summary,
        "n_minus_one": n_minus_one,
    }


def build_note(report: dict) -> str:
    annual = report["annual_summary"]
    burst_rows = [["Case", "Scenario", "Delta feeder MW", "Delta max line loading", "Burst min POI vpu"]]
    for row in report["burst_summary"]:
        if row["case_name"].endswith("p95"):
            burst_rows.append(
                [
                    row["case_name"],
                    row["scenario_label"],
                    f"{row['delta_total_power_kw'] / 1000.0:.2f}",
                    f"{row['delta_max_line_loading_pct_points']:.2f} pct-pts",
                    f"{row['burst_min_poi_vpu']:.4f}",
                ]
            )

    annual_rows = [
        ["Scenario", "Weighted feeder losses", "Weighted incremental losses", "Worst peak loading", "Worst peak POI vpu"],
        [
            "Scenario 2(M)",
            format_gwh(annual["Scenario 2(M)"]["weighted_total_losses_mwh"]),
            format_gwh(annual["Scenario 2(M)"]["weighted_incremental_losses_mwh"]),
            f"{annual['Scenario 2(M)']['worst_peak_line_loading_pct']:.2f}%",
            f"{annual['Scenario 2(M)']['worst_peak_poi_vpu']:.4f}",
        ],
        [
            "Scenario 3(M)",
            format_gwh(annual["Scenario 3(M)"]["weighted_total_losses_mwh"]),
            format_gwh(annual["Scenario 3(M)"]["weighted_incremental_losses_mwh"]),
            f"{annual['Scenario 3(M)']['worst_peak_line_loading_pct']:.2f}%",
            f"{annual['Scenario 3(M)']['worst_peak_poi_vpu']:.4f}",
        ],
    ]

    n1_rows = [["Scenario", "Surviving N-1 cases", "Worst surviving min POI vpu", "Worst surviving line loading"]]
    for label in ["Scenario 2(M)", "Scenario 3(M)"]:
        worst = report["n_minus_one"][label]["worst_surviving"]
        n1_rows.append(
            [
                label,
                str(report["n_minus_one"][label]["surviving_count"]),
                f"{worst['min_poi_vpu']:.4f}" if worst else "N/A",
                f"{worst['max_line_loading_pct']:.2f}%" if worst else "N/A",
            ]
        )

    return "\n".join(
        [
            "# Public Common-Network T&D Study",
            "",
            "Updated: April 11, 2026",
            "",
            "This note places `Scenario 2(M)` and `Scenario 3(M)` on the same public SMART-DS feeder and compares them using the public operating library from `public_time_series_ai_factory.py`.",
            "",
            "## Feeder and POIs",
            "",
            f"Base feeder power: `{report['feeder_base_summary']['total_power_kw'] / 1000.0:.2f} MW` with `{report['feeder_base_summary']['total_losses_kw']:.2f} kW` losses.",
            f"Equivalent feeder-bank count used to host the 100 MW campus on this public feeder exemplar: `{report['dataset']['feeder_bank_count']}`.",
            f"Centralized Scenario 3(M) POI: `{report['poi_definition']['central_bus']}`.",
            "Distributed Scenario 2(M) POIs:",
            *[f"- `{bus}`" for bus in report["poi_definition"]["distributed_buses"]],
            "",
            "## Annualized feeder impact",
            "",
            "```text",
            format_table(annual_rows),
            "```",
            "",
            "## MIT-derived burst sensitivity",
            "",
            "```text",
            format_table(burst_rows),
            "```",
            "",
            "## Surviving N-1 comparison",
            "",
            "```text",
            format_table(n1_rows),
            "```",
            "",
            "## Interpretation",
            "",
            "- This is a real public feeder comparison, not a surrogate one-line stub.",
            "- The SMART-DS feeder is much smaller than a 100 MW campus, so the study uses an equivalent feeder-bank count to normalize the campus onto repeated copies of the same public feeder.",
            "- It is still not a utility Thevenin study or a site-specific interconnection study.",
            "- The main value is methodological: both scenarios now live on the same published T&D network under the same public operating profile.",
            "",
        ]
    )


def print_summary(report: dict, details: bool) -> None:
    annual = report["annual_summary"]
    print("Public common-network T&D study")
    print("-------------------------------")
    print(
        "Base SMART-DS feeder: "
        f"{report['feeder_base_summary']['total_power_kw'] / 1000.0:.2f} MW | "
        f"losses {report['feeder_base_summary']['total_losses_kw']:.2f} kW | "
        f"min vpu {report['feeder_base_summary']['min_system_vpu']:.4f}"
    )
    print(f"Equivalent feeder-bank count: {report['dataset']['feeder_bank_count']}")
    print(f"Scenario 3(M) central POI: {report['poi_definition']['central_bus']}")
    print(f"Scenario 2(M) distributed POIs: {', '.join(report['poi_definition']['distributed_buses'])}")
    print()

    rows = [
        ["Scenario", "Weighted incr. feeder loss", "Worst peak loading", "Worst peak POI vpu", "Surviving N-1"],
        [
            "Scenario 2(M)",
            f"{annual['Scenario 2(M)']['weighted_incremental_losses_mwh'] / 1000.0:.3f} GWh",
            f"{annual['Scenario 2(M)']['worst_peak_line_loading_pct']:.2f}%",
            f"{annual['Scenario 2(M)']['worst_peak_poi_vpu']:.4f}",
            str(report["n_minus_one"]["Scenario 2(M)"]["surviving_count"]),
        ],
        [
            "Scenario 3(M)",
            f"{annual['Scenario 3(M)']['weighted_incremental_losses_mwh'] / 1000.0:.3f} GWh",
            f"{annual['Scenario 3(M)']['worst_peak_line_loading_pct']:.2f}%",
            f"{annual['Scenario 3(M)']['worst_peak_poi_vpu']:.4f}",
            str(report["n_minus_one"]["Scenario 3(M)"]["surviving_count"]),
        ],
    ]
    print(format_table(rows))

    if details:
        print()
        burst_rows = [["Case", "Scenario", "Delta feeder MW", "Burst min POI vpu"]]
        for row in report["burst_summary"]:
            if row["case_name"].endswith("p95"):
                burst_rows.append(
                    [
                        row["case_name"],
                        row["scenario_label"],
                        f"{row['delta_total_power_kw'] / 1000.0:.2f}",
                        f"{row['burst_min_poi_vpu']:.4f}",
                    ]
                )
        print(format_table(burst_rows))


def main() -> None:
    args = parse_args()
    report = build_report(args)
    write_json(args.output_json, report)
    args.output_note.write_text(build_note(report), encoding="utf-8")
    print_summary(report, args.details)


if __name__ == "__main__":
    main()
