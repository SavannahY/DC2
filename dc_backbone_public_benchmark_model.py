#!/usr/bin/env python3
"""Public-data-only upgrade layer for the DC backbone study.

This script adds two separate sensitivity layers using only public data:

1. A public empirical IT-load-shape layer built from the NREL ESIF facility
   dataset (`it_power_kw` column). This replaces the flat full-load year with
   an empirical load-shape sensitivity case.
2. A public common-network screening layer built from the RTS-GMLC bus and
   branch tables. All scenarios are placed on the same published network and
   compared using a linearized DC power-flow stress screen.

The existing path model and multi-node campus model are left unchanged. This
script imports them, applies the public empirical load-shape bins, and writes
separate outputs.
"""

from __future__ import annotations

import argparse
import csv
import io
import json
import math
import zipfile
from pathlib import Path
from typing import Dict, Iterable, List, Sequence

import numpy as np

from dc_backbone_model import (
    deep_copy_jsonable,
    format_gwh,
    format_money_millions,
    format_pct,
    format_table,
    load_json,
    run_model,
)
from dc_backbone_multinode_campus_model import (
    build_report as build_multinode_report,
    load_topology,
)

ROOT = Path(__file__).resolve().parent
DEFAULT_ASSUMPTIONS = ROOT / "scientific_assumptions_v1.json"
DEFAULT_TOPOLOGY = ROOT / "multinode_campus_topology.json"
DEFAULT_RTS_BUS = ROOT / "public_data" / "rts_gmlc" / "bus.csv"
DEFAULT_RTS_BRANCH = ROOT / "public_data" / "rts_gmlc" / "branch.csv"
DEFAULT_ESIF_ZIP = ROOT / "public_data" / "nlr_esif" / "esif_pue_combined.csv.zip"
DEFAULT_PROFILE_JSON = ROOT / "public_data" / "nlr_esif" / "esif_it_profile_bins.json"
DEFAULT_REPORT_JSON = ROOT / "public_benchmark_report.json"

RTS_BASE_MVA = 100.0
RTS_SINGLE_POI_BUS = 110
RTS_MULTI_POI_BUSES = [103, 104, 106, 110]
RTS_REF_BUS = 113


def iter_esif_it_power_kw(zip_path: Path) -> Iterable[float]:
    if not zip_path.exists():
        raise RuntimeError(
            "The raw NREL ESIF zip is not present locally. Download it from "
            "https://data.nrel.gov/system/files/300/1757105566-esif.influx.buildingData.PUE.combined.csv.zip "
            f"and place it at {zip_path}."
        )
    with zipfile.ZipFile(zip_path) as archive:
        with archive.open("esif.influx.buildingData.PUE.combined.csv") as handle:
            reader = csv.DictReader(io.TextIOWrapper(handle, encoding="utf-8", errors="replace"))
            for row in reader:
                raw_value = row["it_power_kw"].strip()
                if not raw_value:
                    continue
                value = float(raw_value)
                if math.isfinite(value) and value > 0.0:
                    yield value


def build_esif_profile(zip_path: Path, bin_count: int, clip_quantile: float) -> dict:
    values_kw = np.fromiter(iter_esif_it_power_kw(zip_path), dtype=float)
    if values_kw.size == 0:
        raise RuntimeError("No valid ESIF IT-power samples were found in the public dataset.")

    clip_kw = float(np.quantile(values_kw, clip_quantile))
    normalized = np.clip(values_kw / clip_kw, 0.0, 1.0)
    normalized.sort()
    chunks = np.array_split(normalized, bin_count)

    load_profile = []
    hours_fraction_total = 0.0
    for index, chunk in enumerate(chunks, start=1):
        if chunk.size == 0:
            continue
        hours_fraction = float(chunk.size / normalized.size)
        hours_fraction_total += hours_fraction
        load_profile.append(
            {
                "name": f"public_esif_quantile_bin_{index:02d}",
                "load_fraction": round(float(chunk.mean()), 6),
                "hours_fraction": round(hours_fraction, 6),
                "note": (
                    "Empirical IT-load-shape bin built from the public NREL ESIF "
                    "facility `it_power_kw` series. Values are normalized to the "
                    f"{clip_quantile:.3f} quantile and clipped at 1.0."
                ),
            }
        )

    # Preserve exact normalization after rounding.
    if load_profile:
        correction = 1.0 - sum(entry["hours_fraction"] for entry in load_profile)
        load_profile[-1]["hours_fraction"] = round(load_profile[-1]["hours_fraction"] + correction, 6)

    return {
        "meta": {
            "dataset": "NREL ESIF public facility data",
            "dataset_url": "https://data.nrel.gov/system/files/300/1757105566-esif.influx.buildingData.PUE.combined.csv.zip",
            "series": "it_power_kw",
            "note": (
                "This is a public empirical facility IT-power series used as a load-shape "
                "sensitivity layer. It is not a public AI-factory-specific workload trace."
            ),
            "sample_count": int(values_kw.size),
            "bin_count": bin_count,
            "normalization_quantile": clip_quantile,
            "normalization_reference_kw": clip_kw,
            "raw_min_kw": float(values_kw.min()),
            "raw_max_kw": float(values_kw.max()),
            "raw_mean_kw": float(values_kw.mean()),
            "raw_p50_kw": float(np.quantile(values_kw, 0.50)),
            "raw_p95_kw": float(np.quantile(values_kw, 0.95)),
            "raw_p99_kw": float(np.quantile(values_kw, 0.99)),
            "normalized_mean_fraction": float(normalized.mean()),
            "normalized_p50_fraction": float(np.quantile(normalized, 0.50)),
            "normalized_p95_fraction": float(np.quantile(normalized, 0.95)),
            "normalized_p99_fraction": float(np.quantile(normalized, 0.99)),
        },
        "load_profile": load_profile,
    }


def write_json(path: Path, payload: dict) -> None:
    path.write_text(json.dumps(payload, indent=2), encoding="utf-8")


def with_public_profile(assumptions: dict, profile_payload: dict) -> dict:
    updated = deep_copy_jsonable(assumptions)
    updated["meta"]["status"] = "source_backed_v1_public_profile_sensitivity"
    updated["meta"]["warning"] += (
        " Public-data-only sensitivity layer: annual load bins are now derived from the "
        "NREL ESIF public IT-power series rather than a flat full-load year."
    )
    updated["load_profile"] = profile_payload["load_profile"]
    return updated


def load_rts_data(bus_csv: Path, branch_csv: Path) -> dict:
    with bus_csv.open(encoding="utf-8") as handle:
        bus_rows = list(csv.DictReader(handle))
    with branch_csv.open(encoding="utf-8") as handle:
        branch_rows = list(csv.DictReader(handle))

    bus_ids = [int(row["Bus ID"]) for row in bus_rows]
    if RTS_REF_BUS not in bus_ids:
        raise RuntimeError(f"Reference bus {RTS_REF_BUS} was not found in the RTS-GMLC bus table.")

    buses = {}
    for row in bus_rows:
        bus_id = int(row["Bus ID"])
        buses[bus_id] = {
            "id": bus_id,
            "name": row["Bus Name"],
            "base_kv": float(row["BaseKV"]),
            "type": row["Bus Type"],
            "mw_load": float(row["MW Load"]),
            "mvar_load": float(row["MVAR Load"]),
            "v_mag_pu": float(row["V Mag"]),
            "angle_deg": float(row["V Angle"]),
            "area": int(float(row["Area"])),
            "zone": int(float(row["Zone"])),
        }

    branches = []
    for row in branch_rows:
        reactance = float(row["X"])
        if reactance <= 0.0:
            continue
        tap = float(row["Tr Ratio"]) if float(row["Tr Ratio"]) > 0.0 else 1.0
        branches.append(
            {
                "uid": row["UID"],
                "from_bus": int(row["From Bus"]),
                "to_bus": int(row["To Bus"]),
                "r_pu": float(row["R"]),
                "x_pu": reactance,
                "tap": tap,
                "cont_rating_mva": float(row["Cont Rating"]),
                "length_miles": float(row["Length"]),
            }
        )

    ordered_bus_ids = sorted(buses)
    bus_index = {bus_id: idx for idx, bus_id in enumerate(ordered_bus_ids)}
    b_matrix = np.zeros((len(ordered_bus_ids), len(ordered_bus_ids)), dtype=float)

    for branch in branches:
        i = bus_index[branch["from_bus"]]
        j = bus_index[branch["to_bus"]]
        susceptance = 1.0 / branch["x_pu"]
        tap = branch["tap"]
        b_matrix[i, i] += susceptance / (tap * tap)
        b_matrix[j, j] += susceptance
        b_matrix[i, j] -= susceptance / tap
        b_matrix[j, i] -= susceptance / tap

        theta_from = math.radians(buses[branch["from_bus"]]["angle_deg"])
        theta_to = math.radians(buses[branch["to_bus"]]["angle_deg"])
        branch["base_flow_mw"] = RTS_BASE_MVA * ((theta_from / tap) - theta_to) / branch["x_pu"]
        branch["base_loading_pct"] = abs(branch["base_flow_mw"]) / branch["cont_rating_mva"] * 100.0

    return {
        "base_mva": RTS_BASE_MVA,
        "ref_bus": RTS_REF_BUS,
        "buses": buses,
        "branches": branches,
        "ordered_bus_ids": ordered_bus_ids,
        "bus_index": bus_index,
        "b_matrix": b_matrix,
    }


def solve_incremental_dc_screen(network: dict, load_withdrawals_mw: Dict[int, float]) -> dict:
    ordered_bus_ids = network["ordered_bus_ids"]
    bus_index = network["bus_index"]
    ref_idx = bus_index[network["ref_bus"]]
    injections_mw = np.zeros(len(ordered_bus_ids), dtype=float)

    total_withdrawal = 0.0
    for bus_id, withdrawal_mw in load_withdrawals_mw.items():
        total_withdrawal += withdrawal_mw
        injections_mw[bus_index[bus_id]] -= withdrawal_mw
    injections_mw[ref_idx] += total_withdrawal

    mask = np.ones(len(ordered_bus_ids), dtype=bool)
    mask[ref_idx] = False
    b_reduced = network["b_matrix"][np.ix_(mask, mask)]
    p_reduced = injections_mw[mask] / network["base_mva"]
    theta = np.zeros(len(ordered_bus_ids), dtype=float)
    theta[mask] = np.linalg.solve(b_reduced, p_reduced)

    branch_rows = []
    for branch in network["branches"]:
        from_idx = bus_index[branch["from_bus"]]
        to_idx = bus_index[branch["to_bus"]]
        tap = branch["tap"]
        incremental_flow_mw = (
            network["base_mva"] * ((theta[from_idx] / tap) - theta[to_idx]) / branch["x_pu"]
        )
        final_flow_mw = branch["base_flow_mw"] + incremental_flow_mw
        branch_rows.append(
            {
                "uid": branch["uid"],
                "from_bus": branch["from_bus"],
                "to_bus": branch["to_bus"],
                "cont_rating_mva": branch["cont_rating_mva"],
                "base_flow_mw": branch["base_flow_mw"],
                "base_loading_pct": branch["base_loading_pct"],
                "incremental_flow_mw": incremental_flow_mw,
                "incremental_loading_pct": abs(incremental_flow_mw) / branch["cont_rating_mva"] * 100.0,
                "final_flow_mw": final_flow_mw,
                "final_loading_pct": abs(final_flow_mw) / branch["cont_rating_mva"] * 100.0,
            }
        )

    top_branches = sorted(branch_rows, key=lambda row: abs(row["incremental_flow_mw"]), reverse=True)[:5]
    worst_branch = max(branch_rows, key=lambda row: row["final_loading_pct"])
    max_angle_delta_deg = math.degrees(theta.max() - theta.min())
    return {
        "load_withdrawals_mw": load_withdrawals_mw,
        "total_withdrawal_mw": total_withdrawal,
        "max_incremental_branch_flow_mw": max(abs(row["incremental_flow_mw"]) for row in branch_rows),
        "max_incremental_loading_pct": max(row["incremental_loading_pct"] for row in branch_rows),
        "max_final_loading_pct": worst_branch["final_loading_pct"],
        "worst_branch_uid": worst_branch["uid"],
        "worst_branch_final_loading_pct": worst_branch["final_loading_pct"],
        "max_angle_delta_deg": max_angle_delta_deg,
        "top_incremental_branches": top_branches,
    }


def summarize_single_path_network(single_path_report: dict, network: dict) -> dict:
    results = {}
    for scenario in single_path_report["results"]:
        results[scenario["display_name"]] = solve_incremental_dc_screen(
            network,
            {RTS_SINGLE_POI_BUS: scenario["full_load_input_mw"]},
        )
    return {
        "poi_bus": RTS_SINGLE_POI_BUS,
        "poi_bus_name": network["buses"][RTS_SINGLE_POI_BUS]["name"],
        "ref_bus": network["ref_bus"],
        "ref_bus_name": network["buses"][network["ref_bus"]]["name"],
        "cases": results,
    }


def summarize_multinode_network(multinode_report: dict, network: dict) -> dict:
    results = {}
    for scenario in multinode_report["architectures"]:
        total_source_mw = scenario["full_load"]["source_input_mw"]
        per_bus = total_source_mw / len(RTS_MULTI_POI_BUSES)
        load_withdrawals = {bus_id: per_bus for bus_id in RTS_MULTI_POI_BUSES}
        results[scenario["scenario_label"]] = solve_incremental_dc_screen(network, load_withdrawals)
    return {
        "poi_buses": RTS_MULTI_POI_BUSES,
        "poi_bus_names": [network["buses"][bus_id]["name"] for bus_id in RTS_MULTI_POI_BUSES],
        "ref_bus": network["ref_bus"],
        "ref_bus_name": network["buses"][network["ref_bus"]]["name"],
        "cases": results,
    }


def build_report(
    assumptions_path: Path,
    topology_path: Path,
    rts_bus_path: Path,
    rts_branch_path: Path,
    esif_zip_path: Path,
    bin_count: int,
    clip_quantile: float,
) -> dict:
    base_assumptions = load_json(assumptions_path)
    public_profile = build_esif_profile(esif_zip_path, bin_count=bin_count, clip_quantile=clip_quantile)
    public_assumptions = with_public_profile(base_assumptions, public_profile)

    single_path_report = run_model(public_assumptions, include_opendss=False)
    topology = load_topology(topology_path)
    multinode_report = build_multinode_report(public_assumptions, topology)
    rts_network = load_rts_data(rts_bus_path, rts_branch_path)

    return {
        "meta": {
            "title": "Public-data-only benchmark upgrade for the DC backbone study",
            "status": "public_profile_and_public_network_sensitivity",
            "assumptions_path": str(assumptions_path),
            "topology_path": str(topology_path),
            "rts_bus_path": str(rts_bus_path),
            "rts_branch_path": str(rts_branch_path),
            "esif_zip_path": str(esif_zip_path),
            "note": (
                "This report adds two public-data-only sensitivity layers: an empirical ESIF "
                "IT-load-shape layer and a common-network RTS-GMLC stress screen. It does not "
                "replace vendor-grade converter data, site-specific utility data, or EMT studies."
            ),
        },
        "public_esif_profile": public_profile,
        "single_path_public_profile_results": single_path_report,
        "multinode_public_profile_results": multinode_report,
        "rts_gmlc_common_network_screen": {
            "dataset_url": "https://github.com/GridMod/RTS-GMLC",
            "base_mva_assumption": RTS_BASE_MVA,
            "single_path": summarize_single_path_network(single_path_report, rts_network),
            "multinode": summarize_multinode_network(multinode_report, rts_network),
        },
    }


def print_summary(report: dict) -> None:
    profile = report["public_esif_profile"]["meta"]
    print("Public ESIF load-shape layer")
    print("---------------------------")
    print(
        "Empirical IT-power samples: "
        f"{profile['sample_count']:,} | normalized mean {profile['normalized_mean_fraction']:.2%} | "
        f"normalized p95 {profile['normalized_p95_fraction']:.2%}"
    )
    print()

    print("Single-path scenarios with public ESIF load shape")
    print("------------------------------------------------")
    single_rows = []
    for entry in report["single_path_public_profile_results"]["results"]:
        single_rows.append(
            [
                entry["display_name"],
                format_pct(entry["full_load_total_efficiency"]),
                format_gwh(entry["annual_loss_mwh"]),
                format_money_millions(entry["annual_loss_cost_usd"]),
            ]
        )
    print(
        format_table(
            [
                ["Scenario", "Full-Load Eff.", "Annual Loss GWh", "Annual Loss Cost"],
                *single_rows,
            ]
        )
    )
    print()

    print("Multi-node scenarios with public ESIF load shape")
    print("-----------------------------------------------")
    multi_rows = []
    for entry in report["multinode_public_profile_results"]["architectures"]:
        multi_rows.append(
            [
                entry["scenario_label"],
                format_pct(entry["full_load"]["total_efficiency"]),
                format_gwh(entry["annual_summary"]["annual_loss_mwh"]),
                format_money_millions(entry["annual_summary"]["annual_loss_cost_usd"]),
            ]
        )
    print(
        format_table(
            [
                ["Scenario", "Full-Load Eff.", "Annual Loss GWh", "Annual Loss Cost"],
                *multi_rows,
            ]
        )
    )
    print()

    print("RTS-GMLC common-network screen")
    print("------------------------------")
    single_screen = report["rts_gmlc_common_network_screen"]["single_path"]
    single_rows = []
    for name, entry in single_screen["cases"].items():
        single_rows.append(
            [
                name,
                f"{entry['total_withdrawal_mw']:.2f}",
                f"{entry['max_incremental_branch_flow_mw']:.2f}",
                f"{entry['max_incremental_loading_pct']:.2f}%",
                f"{entry['max_final_loading_pct']:.2f}%",
                entry["worst_branch_uid"],
            ]
        )
    print(
        format_table(
            [
                [
                    "Single-path case",
                    "POI MW",
                    "Max Branch Delta MW",
                    "Max Incremental Loading",
                    "Worst Final Loading",
                    "Worst Branch",
                ],
                *single_rows,
            ]
        )
    )
    print()

    multi_screen = report["rts_gmlc_common_network_screen"]["multinode"]
    multi_rows = []
    for name, entry in multi_screen["cases"].items():
        multi_rows.append(
            [
                name,
                f"{entry['total_withdrawal_mw']:.2f}",
                f"{entry['max_incremental_branch_flow_mw']:.2f}",
                f"{entry['max_incremental_loading_pct']:.2f}%",
                f"{entry['max_final_loading_pct']:.2f}%",
                entry["worst_branch_uid"],
            ]
        )
    print(
        format_table(
            [
                [
                    "Multi-node case",
                    "Total MW",
                    "Max Branch Delta MW",
                    "Max Incremental Loading",
                    "Worst Final Loading",
                    "Worst Branch",
                ],
                *multi_rows,
            ]
        )
    )


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run the public-data-only benchmark upgrade workflow.")
    parser.add_argument("--assumptions", type=Path, default=DEFAULT_ASSUMPTIONS)
    parser.add_argument("--topology", type=Path, default=DEFAULT_TOPOLOGY)
    parser.add_argument("--rts-bus", type=Path, default=DEFAULT_RTS_BUS)
    parser.add_argument("--rts-branch", type=Path, default=DEFAULT_RTS_BRANCH)
    parser.add_argument("--esif-zip", type=Path, default=DEFAULT_ESIF_ZIP)
    parser.add_argument("--bin-count", type=int, default=16)
    parser.add_argument("--clip-quantile", type=float, default=0.995)
    parser.add_argument("--save-json", type=Path, default=DEFAULT_REPORT_JSON)
    parser.add_argument("--save-profile-json", type=Path, default=DEFAULT_PROFILE_JSON)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    report = build_report(
        assumptions_path=args.assumptions,
        topology_path=args.topology,
        rts_bus_path=args.rts_bus,
        rts_branch_path=args.rts_branch,
        esif_zip_path=args.esif_zip,
        bin_count=args.bin_count,
        clip_quantile=args.clip_quantile,
    )
    write_json(args.save_json, report)
    write_json(args.save_profile_json, report["public_esif_profile"])
    print_summary(report)


if __name__ == "__main__":
    main()
