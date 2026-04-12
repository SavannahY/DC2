#!/usr/bin/env python3
"""Public-data-only benefit analysis for the three headline claims.

This script builds on `dc_backbone_public_benchmark_model.py` and separates the
three claimed benefits into distinct public-data-only evidence layers:

1. Efficiency / annual-loss robustness under the public ESIF empirical load
   shape.
2. Power-quality / harmonic sensitivity on the public RTS-GMLC network using a
   standardized current-probe method.
3. Voltage-response sensitivity on the public RTS-GMLC network using a
   linearized complex-voltage screen around the published RTS operating point.

The goal is not to overclaim. This is still a public-data-only sensitivity
study, not a vendor-grade converter model, utility interconnection study, or
EMT proof.
"""

from __future__ import annotations

import argparse
import cmath
import json
import math
from pathlib import Path
from typing import Dict, Iterable, List

import numpy as np

from dc_backbone_public_benchmark_model import (
    DEFAULT_ASSUMPTIONS,
    DEFAULT_ESIF_ZIP,
    DEFAULT_RTS_BRANCH,
    DEFAULT_RTS_BUS,
    DEFAULT_TOPOLOGY,
    DEFAULT_REPORT_JSON,
    RTS_BASE_MVA,
    RTS_MULTI_POI_BUSES,
    RTS_REF_BUS,
    RTS_SINGLE_POI_BUS,
    build_report as build_public_benchmark_report,
)
from dc_backbone_model import format_money_millions, format_pct, format_table

ROOT = Path(__file__).resolve().parent
DEFAULT_OUTPUT = ROOT / "public_benefit_report.json"
DEFAULT_NOTE = ROOT / "PUBLIC_BENEFIT_ANALYSIS.md"
CENTRALIZED_PUBLIC_SUBSTATION_BUS = 112
HARMONIC_ORDERS = [5, 7, 11, 13]
HARMONIC_CURRENT_PU_PER_INTERFACE = 0.01
DYNAMIC_STEP_FRACTION = 0.10


def write_json(path: Path, payload: dict) -> None:
    path.write_text(json.dumps(payload, indent=2), encoding="utf-8")


def build_complex_network(rts_network: dict, harmonic_order: int = 1) -> dict:
    ordered_bus_ids = rts_network["ordered_bus_ids"]
    bus_index = rts_network["bus_index"]
    ref_idx = bus_index[rts_network["ref_bus"]]
    y_matrix = np.zeros((len(ordered_bus_ids), len(ordered_bus_ids)), dtype=complex)

    for branch in rts_network["branches"]:
        z = complex(branch["r_pu"], branch["x_pu"] * harmonic_order)
        y = 1.0 / z
        tap = branch["tap"]
        i = bus_index[branch["from_bus"]]
        j = bus_index[branch["to_bus"]]
        y_matrix[i, i] += y / (tap * tap)
        y_matrix[j, j] += y
        y_matrix[i, j] -= y / tap
        y_matrix[j, i] -= y / tap

    mask = np.ones(len(ordered_bus_ids), dtype=bool)
    mask[ref_idx] = False
    y_reduced = y_matrix[np.ix_(mask, mask)]
    z_reduced = np.linalg.inv(y_reduced)

    base_voltage = np.array(
        [
            rts_network["buses"][bus_id]["v_mag_pu"] * cmath.exp(1j * math.radians(rts_network["buses"][bus_id]["angle_deg"]))
            for bus_id in ordered_bus_ids
        ],
        dtype=complex,
    )
    return {
        "ordered_bus_ids": ordered_bus_ids,
        "bus_index": bus_index,
        "ref_idx": ref_idx,
        "mask": mask,
        "y_reduced": y_reduced,
        "z_reduced": z_reduced,
        "base_voltage": base_voltage,
    }


def extend_rts_network_with_voltage(rts_network: dict) -> dict:
    network = dict(rts_network)
    buses = {}
    for bus_id, row in rts_network["buses"].items():
        buses[bus_id] = dict(row)
        buses[bus_id]["v_mag_pu"] = row["v_mag_pu"] if "v_mag_pu" in row else row["v_mag_pu"]
    network["buses"] = buses
    return network


def scenario_lookup(public_report: dict) -> dict:
    single = {entry["display_name"]: entry for entry in public_report["single_path_public_profile_results"]["results"]}
    multi = {entry["scenario_label"]: entry for entry in public_report["multinode_public_profile_results"]["architectures"]}
    return {"single": single, "multi": multi}


def additional_load_currents(
    network_model: dict,
    rts_network: dict,
    load_withdrawals_mw: Dict[int, float],
    power_factor: float,
) -> np.ndarray:
    ordered_bus_ids = network_model["ordered_bus_ids"]
    current_vector = np.zeros(len(ordered_bus_ids), dtype=complex)
    q_sign = math.tan(math.acos(power_factor))
    for bus_id, mw in load_withdrawals_mw.items():
        p_pu = mw / RTS_BASE_MVA
        q_pu = p_pu * q_sign
        v = network_model["base_voltage"][network_model["bus_index"][bus_id]]
        current_vector[network_model["bus_index"][bus_id]] += np.conj(complex(p_pu, -q_pu) / np.conj(v))
    return current_vector


def solve_voltage_sensitivity(
    network_model: dict,
    rts_network: dict,
    load_withdrawals_mw: Dict[int, float],
    power_factor: float,
) -> dict:
    current_vector = additional_load_currents(network_model, rts_network, load_withdrawals_mw, power_factor)
    delta_reduced = network_model["z_reduced"] @ current_vector[network_model["mask"]]
    delta_v = np.zeros(len(network_model["ordered_bus_ids"]), dtype=complex)
    delta_v[network_model["mask"]] = delta_reduced
    final_v = network_model["base_voltage"] + delta_v

    poi_rows = []
    for bus_id in load_withdrawals_mw:
        idx = network_model["bus_index"][bus_id]
        poi_rows.append(
            {
                "bus_id": bus_id,
                "bus_name": rts_network["buses"][bus_id]["name"],
                "base_voltage_pu": abs(network_model["base_voltage"][idx]),
                "final_voltage_pu": abs(final_v[idx]),
                "drop_pct_points": (abs(network_model["base_voltage"][idx]) - abs(final_v[idx])) * 100.0,
            }
        )

    worst_bus_idx = min(
        [idx for idx in range(len(final_v)) if idx != network_model["ref_idx"]],
        key=lambda idx: abs(final_v[idx]),
    )
    worst_bus_id = network_model["ordered_bus_ids"][worst_bus_idx]
    return {
        "load_withdrawals_mw": load_withdrawals_mw,
        "poi_rows": poi_rows,
        "max_poi_drop_pct_points": max(row["drop_pct_points"] for row in poi_rows),
        "worst_bus_id": worst_bus_id,
        "worst_bus_name": rts_network["buses"][worst_bus_id]["name"],
        "worst_bus_final_voltage_pu": abs(final_v[worst_bus_idx]),
        "worst_bus_drop_pct_points": (
            abs(network_model["base_voltage"][worst_bus_idx]) - abs(final_v[worst_bus_idx])
        )
        * 100.0,
    }


def harmonic_voltage_response(
    harmonic_model: dict,
    rts_network: dict,
    poi_buses: Iterable[int],
    current_pu_per_interface: float,
) -> dict:
    current_vector = np.zeros(len(harmonic_model["ordered_bus_ids"]), dtype=complex)
    for bus_id in poi_buses:
        current_vector[harmonic_model["bus_index"][bus_id]] -= current_pu_per_interface
    delta_reduced = harmonic_model["z_reduced"] @ current_vector[harmonic_model["mask"]]
    delta_v = np.zeros(len(harmonic_model["ordered_bus_ids"]), dtype=complex)
    delta_v[harmonic_model["mask"]] = delta_reduced

    poi_voltage_rows = []
    for bus_id in poi_buses:
        idx = harmonic_model["bus_index"][bus_id]
        poi_voltage_rows.append(
            {
                "bus_id": bus_id,
                "bus_name": rts_network["buses"][bus_id]["name"],
                "voltage_pu": abs(delta_v[idx]),
            }
        )
    worst_voltage = max(abs(value) for value in delta_v)
    return {
        "poi_count": len(list(poi_buses)),
        "poi_rows": poi_voltage_rows,
        "max_bus_voltage_pu": worst_voltage,
        "max_poi_voltage_pu": max(row["voltage_pu"] for row in poi_voltage_rows),
    }


def build_efficiency_benefit(public_report: dict) -> dict:
    single = scenario_lookup(public_report)["single"]
    multi = scenario_lookup(public_report)["multi"]

    scenario2 = single["NVIDIA-style 69 kV AC -> 800 VDC perimeter conversion"]
    scenario3 = single["Proposed MVDC backbone"]
    single_bin_rows = []
    single_hours_better = 0.0
    for bin2, bin3 in zip(scenario2["load_bins"], scenario3["load_bins"]):
        better = bin3["total_loss_mw"] < bin2["total_loss_mw"]
        if better:
            single_hours_better += bin2["hours"]
        single_bin_rows.append(
            {
                "name": bin2["name"],
                "load_fraction": bin2["delivered_it_mw"] / public_report["single_path_public_profile_results"]["global"]["base_it_load_mw"],
                "scenario2_loss_mw": bin2["total_loss_mw"],
                "scenario3_loss_mw": bin3["total_loss_mw"],
                "scenario3_better": better,
                "hours": bin2["hours"],
            }
        )

    s2m = multi["Scenario 2(M)"]
    s3m = multi["Scenario 3(M)"]
    multi_bin_rows = []
    multi_hours_better = 0.0
    for bin2, bin3 in zip(s2m["annual_summary"]["load_bins"], s3m["annual_summary"]["load_bins"]):
        better = bin3["loss_mw"] < bin2["loss_mw"]
        if better:
            multi_hours_better += bin2["hours"]
        multi_bin_rows.append(
            {
                "name": bin2["name"],
                "load_fraction": bin2["scale"],
                "scenario2m_loss_mw": bin2["loss_mw"],
                "scenario3m_loss_mw": bin3["loss_mw"],
                "scenario3m_better": better,
                "hours": bin2["hours"],
            }
        )

    return {
        "claim": "Scenario 3 should reduce electrical losses.",
        "single_path": {
            "scenario3_minus_scenario2_annual_loss_mwh": scenario3["annual_loss_mwh"] - scenario2["annual_loss_mwh"],
            "scenario3_better_hours": single_hours_better,
            "scenario3_better_hours_fraction": single_hours_better / 8760.0,
            "bin_rows": single_bin_rows,
        },
        "multi_node": {
            "scenario3m_minus_scenario2m_annual_loss_mwh": (
                s3m["annual_summary"]["annual_loss_mwh"] - s2m["annual_summary"]["annual_loss_mwh"]
            ),
            "scenario3m_better_hours": multi_hours_better,
            "scenario3m_better_hours_fraction": multi_hours_better / 8760.0,
            "bin_rows": multi_bin_rows,
        },
    }


def build_harmonic_benefit(public_report: dict, rts_network: dict) -> dict:
    harmonics = {}
    multi_patterns = {
        "Scenario 1(M)": RTS_MULTI_POI_BUSES,
        "Scenario 2(M)": RTS_MULTI_POI_BUSES,
        "Scenario 3(M)": [CENTRALIZED_PUBLIC_SUBSTATION_BUS],
    }
    for order in HARMONIC_ORDERS:
        harmonic_model = build_complex_network(rts_network, harmonic_order=order)
        order_results = {"single_path": {}, "multi_node": {}}
        for display_name in [
            "Traditional AC-centric",
            "NVIDIA-style 69 kV AC -> 800 VDC perimeter conversion",
            "Proposed MVDC backbone",
        ]:
            order_results["single_path"][display_name] = harmonic_voltage_response(
                harmonic_model,
                rts_network,
                [RTS_SINGLE_POI_BUS],
                HARMONIC_CURRENT_PU_PER_INTERFACE,
            )
        for scenario_label, buses in multi_patterns.items():
            order_results["multi_node"][scenario_label] = harmonic_voltage_response(
                harmonic_model,
                rts_network,
                buses,
                HARMONIC_CURRENT_PU_PER_INTERFACE,
            )
        harmonics[order] = order_results

    def thdv_proxy(section: Dict[str, dict], key: str) -> float:
        return math.sqrt(sum(section[order][key]["max_poi_voltage_pu"] ** 2 for order in HARMONIC_ORDERS))

    single_summary = {}
    for name in [
        "Traditional AC-centric",
        "NVIDIA-style 69 kV AC -> 800 VDC perimeter conversion",
        "Proposed MVDC backbone",
    ]:
        single_summary[name] = {
            "thdv_proxy_pu": thdv_proxy({order: harmonics[order]["single_path"] for order in HARMONIC_ORDERS}, name),
            "interface_count": 1,
        }

    multi_summary = {}
    for label, buses in multi_patterns.items():
        multi_summary[label] = {
            "thdv_proxy_pu": thdv_proxy({order: harmonics[order]["multi_node"] for order in HARMONIC_ORDERS}, label),
            "interface_count": len(buses),
            "poi_bus_ids": buses,
            "poi_bus_names": [rts_network["buses"][bus_id]["name"] for bus_id in buses],
        }

    return {
        "claim": "Scenario 3 should centralize AC harmonic ownership and reduce grid-facing harmonic sensitivity.",
        "assumption_note": (
            "A standardized per-interface harmonic current probe is injected on the public RTS network. "
            "For Scenario 3(M), the AC interface is modeled as one centralized subtransmission/front-end "
            f"connection at RTS bus {CENTRALIZED_PUBLIC_SUBSTATION_BUS}. For Scenario 1(M)/2(M), the "
            "AC interfaces are distributed across four 138 kV load buses."
        ),
        "harmonic_orders": HARMONIC_ORDERS,
        "per_interface_current_probe_pu": HARMONIC_CURRENT_PU_PER_INTERFACE,
        "single_path": single_summary,
        "multi_node": multi_summary,
    }


def build_voltage_benefit(public_report: dict, rts_network: dict, power_factor: float) -> dict:
    network_model = build_complex_network(rts_network, harmonic_order=1)
    lookup = scenario_lookup(public_report)

    single_base = {}
    single_step = {}
    for entry in public_report["single_path_public_profile_results"]["results"]:
        base_loads = {RTS_SINGLE_POI_BUS: entry["full_load_input_mw"]}
        step_loads = {RTS_SINGLE_POI_BUS: entry["full_load_input_mw"] * (1.0 + DYNAMIC_STEP_FRACTION)}
        single_base[entry["display_name"]] = solve_voltage_sensitivity(network_model, rts_network, base_loads, power_factor)
        single_step[entry["display_name"]] = solve_voltage_sensitivity(network_model, rts_network, step_loads, power_factor)

    multi_base = {}
    multi_step = {}
    distributed_labels = {"Scenario 1(M)", "Scenario 2(M)"}
    for entry in public_report["multinode_public_profile_results"]["architectures"]:
        total_mw = entry["full_load"]["source_input_mw"]
        if entry["scenario_label"] in distributed_labels:
            base_loads = {bus_id: total_mw / len(RTS_MULTI_POI_BUSES) for bus_id in RTS_MULTI_POI_BUSES}
            step_loads = {
                bus_id: total_mw * (1.0 + DYNAMIC_STEP_FRACTION) / len(RTS_MULTI_POI_BUSES)
                for bus_id in RTS_MULTI_POI_BUSES
            }
        else:
            base_loads = {CENTRALIZED_PUBLIC_SUBSTATION_BUS: total_mw}
            step_loads = {CENTRALIZED_PUBLIC_SUBSTATION_BUS: total_mw * (1.0 + DYNAMIC_STEP_FRACTION)}
        multi_base[entry["scenario_label"]] = solve_voltage_sensitivity(network_model, rts_network, base_loads, power_factor)
        multi_step[entry["scenario_label"]] = solve_voltage_sensitivity(network_model, rts_network, step_loads, power_factor)

    return {
        "claim": "Scenario 3 should reduce AC-side voltage sensitivity by moving the main AC/DC boundary upstream.",
        "assumption_note": (
            "The voltage screen uses a linearized complex-voltage sensitivity around the published RTS base "
            "operating point. Scenario 3(M) is represented with one centralized subtransmission AC interface "
            f"at RTS bus {CENTRALIZED_PUBLIC_SUBSTATION_BUS}; Scenario 1(M)/2(M) use four distributed 138 kV AC interfaces."
        ),
        "power_factor": power_factor,
        "dynamic_step_fraction": DYNAMIC_STEP_FRACTION,
        "single_path": {
            "base_case": single_base,
            "plus_10pct_step": single_step,
        },
        "multi_node": {
            "base_case": multi_base,
            "plus_10pct_step": multi_step,
        },
    }


def build_scaling_sweep(public_report: dict, rts_network: dict, power_factor: float) -> dict:
    harmonic_models = {order: build_complex_network(rts_network, harmonic_order=order) for order in HARMONIC_ORDERS}
    voltage_model = build_complex_network(rts_network, harmonic_order=1)
    multi = scenario_lookup(public_report)["multi"]
    scenario2m = multi["Scenario 2(M)"]
    scenario3m = multi["Scenario 3(M)"]

    rows = []
    for case2, case3 in zip(scenario2m["expansion_cases"], scenario3m["expansion_cases"]):
        count = len(case2["active_blocks"])
        distributed_buses = RTS_MULTI_POI_BUSES[:count]
        scenario2_loads = {bus_id: case2["source_input_mw"] / count for bus_id in distributed_buses}
        scenario3_loads = {CENTRALIZED_PUBLIC_SUBSTATION_BUS: case3["source_input_mw"]}

        scenario2_harm = math.sqrt(
            sum(
                harmonic_voltage_response(
                    harmonic_models[order],
                    rts_network,
                    distributed_buses,
                    HARMONIC_CURRENT_PU_PER_INTERFACE,
                )["max_poi_voltage_pu"]
                ** 2
                for order in HARMONIC_ORDERS
            )
        )
        scenario3_harm = math.sqrt(
            sum(
                harmonic_voltage_response(
                    harmonic_models[order],
                    rts_network,
                    [CENTRALIZED_PUBLIC_SUBSTATION_BUS],
                    HARMONIC_CURRENT_PU_PER_INTERFACE,
                )["max_poi_voltage_pu"]
                ** 2
                for order in HARMONIC_ORDERS
            )
        )
        scenario2_voltage = solve_voltage_sensitivity(voltage_model, rts_network, scenario2_loads, power_factor)
        scenario3_voltage = solve_voltage_sensitivity(voltage_model, rts_network, scenario3_loads, power_factor)

        rows.append(
            {
                "block_count": count,
                "total_it_mw": case2["total_it_mw"],
                "scenario2m_efficiency": case2["efficiency"],
                "scenario3m_efficiency": case3["efficiency"],
                "scenario3m_minus_scenario2m_efficiency_pct_points": (case3["efficiency"] - case2["efficiency"]) * 100.0,
                "scenario2m_network_loss_mw": case2["network_loss_mw"],
                "scenario3m_network_loss_mw": case3["network_loss_mw"],
                "scenario2m_ac_interface_count": count,
                "scenario3m_ac_interface_count": 1,
                "scenario2m_harmonic_thdv_proxy_pu": scenario2_harm,
                "scenario3m_harmonic_thdv_proxy_pu": scenario3_harm,
                "scenario2m_base_max_poi_drop_pct_points": scenario2_voltage["max_poi_drop_pct_points"],
                "scenario3m_base_max_poi_drop_pct_points": scenario3_voltage["max_poi_drop_pct_points"],
            }
        )

    return {
        "claim": "The MVDC-backbone advantage should become clearer as a campus expands from one block to multiple blocks.",
        "rows": rows,
        "interpretation": (
            "This sweep reuses the multi-node expansion cases and applies the same public-network harmonic "
            "and voltage screens at each active-block count."
        ),
    }


def build_note(report: dict) -> str:
    eff = report["benefits"]["efficiency"]
    harm = report["benefits"]["power_quality"]
    volt = report["benefits"]["voltage_and_dynamic"]
    sweep = report["benefits"]["scaling_sweep"]["rows"]

    single_eff = eff["single_path"]
    multi_eff = eff["multi_node"]
    s2m_h = harm["multi_node"]["Scenario 2(M)"]["thdv_proxy_pu"]
    s3m_h = harm["multi_node"]["Scenario 3(M)"]["thdv_proxy_pu"]
    s2m_v = volt["multi_node"]["base_case"]["Scenario 2(M)"]["max_poi_drop_pct_points"]
    s3m_v = volt["multi_node"]["base_case"]["Scenario 3(M)"]["max_poi_drop_pct_points"]
    s2m_v_step = volt["multi_node"]["plus_10pct_step"]["Scenario 2(M)"]["max_poi_drop_pct_points"]
    s3m_v_step = volt["multi_node"]["plus_10pct_step"]["Scenario 3(M)"]["max_poi_drop_pct_points"]
    first_crossover = next(
        (row for row in sweep if row["scenario3m_minus_scenario2m_efficiency_pct_points"] > 0.0),
        None,
    )

    return "\n".join(
        [
            "# Public Benefit Analysis",
            "",
            "This note summarizes how far the available public datasets can support the three headline benefits.",
            "",
            "## Benefit 1: Efficiency / loss reduction",
            "",
            f"- Single-path result under the public ESIF load shape: Scenario 3 is better than Scenario 2 for `{single_eff['scenario3_better_hours_fraction']:.1%}` of annualized hours, but its total annualized loss is slightly worse by `{single_eff['scenario3_minus_scenario2_annual_loss_mwh']:+.2f} MWh`.",
            f"- Multi-node result under the same public ESIF load shape: Scenario 3(M) is better than Scenario 2(M) for `{multi_eff['scenario3m_better_hours_fraction']:.1%}` of annualized hours and improves annualized loss by `{multi_eff['scenario3m_minus_scenario2m_annual_loss_mwh']:+.2f} MWh`.",
            "- Interpretation: the public data supports the campus-backbone efficiency claim more strongly than the simple single-path claim.",
            "",
            "## Benefit 2: Power quality / harmonics",
            "",
            f"- Public-network harmonic-sensitivity proxy: Scenario 2(M) has a THDv proxy of `{s2m_h:.5f} pu` with four distributed AC interfaces, while Scenario 3(M) has `{s3m_h:.5f} pu` with one centralized AC interface.",
            "- Interpretation: under the same per-interface harmonic-source assumption, the centralized-front-end architecture reduces aggregate grid-facing harmonic exposure because it collapses multiple AC interfaces into one.",
            "- Limitation: this is still a structural harmonic-sensitivity screen, not an IEEE 519 compliance study.",
            "",
            "## Benefit 3: Voltage response / upstream AC boundary",
            "",
            f"- Public-network voltage sensitivity at full load: Scenario 2(M) shows a maximum POI voltage-drop proxy of `{s2m_v:.3f}` percentage points, while Scenario 3(M) shows `{s3m_v:.3f}`.",
            f"- With a `+10%` load step: Scenario 2(M) rises to `{s2m_v_step:.3f}` percentage points and Scenario 3(M) rises to `{s3m_v_step:.3f}`.",
            "- Interpretation: moving the AC/DC boundary upstream to one centralized subtransmission interface improves the public-network voltage-sensitivity screen.",
            "- Limitation: this is a linearized network-voltage sensitivity around the published RTS operating point, not an EMT or converter-control study.",
            "",
            "## Scaling evidence",
            "",
            (
                f"- In the current expansion sweep, Scenario 3(M) first turns more efficient than Scenario 2(M) at `{first_crossover['block_count']}` active blocks / `{first_crossover['total_it_mw']:.0f} MW`."
                if first_crossover
                else "- In the current expansion sweep, Scenario 3(M) does not turn more efficient than Scenario 2(M)."
            ),
            f"- At four blocks / 100 MW, the harmonic proxy is `{s2m_h:.5f} pu` for Scenario 2(M) and `{s3m_h:.5f} pu` for Scenario 3(M).",
            f"- At four blocks / 100 MW, the base voltage-drop proxy is `{s2m_v:.3f}` percentage points for Scenario 2(M) and `{s3m_v:.3f}` for Scenario 3(M).",
        ]
    )


def build_report(public_benchmark_report: dict) -> dict:
    rts_network = public_benchmark_report["rts_network"] if "rts_network" in public_benchmark_report else None
    if rts_network is None:
        # Rebuild from the public paths recorded in the benchmark report.
        from dc_backbone_public_benchmark_model import load_rts_data

        rts_network = load_rts_data(
            Path(public_benchmark_report["meta"]["rts_bus_path"]),
            Path(public_benchmark_report["meta"]["rts_branch_path"]),
        )

    # Add explicit voltage fields if the loader did not preserve them in the cached network object.
    if "v_mag_pu" not in next(iter(rts_network["buses"].values())):
        raise RuntimeError("RTS network buses are missing voltage fields needed for the public benefit analysis.")

    power_factor = public_benchmark_report["single_path_public_profile_results"]["global"]["default_power_factor"]

    report = {
        "meta": {
            "title": "Public-data-only benefit analysis",
            "status": "public_benefit_screen_v1",
            "note": (
                "This report tests the three headline benefits with the currently available public datasets. "
                "It strengthens some claims and weakens others. It is not a substitute for converter-aware EMT, "
                "site-specific PCC analysis, or vendor-grade efficiency data."
            ),
            "inputs": public_benchmark_report["meta"],
        },
        "benefits": {
            "efficiency": build_efficiency_benefit(public_benchmark_report),
            "power_quality": build_harmonic_benefit(public_benchmark_report, rts_network),
            "voltage_and_dynamic": build_voltage_benefit(public_benchmark_report, rts_network, power_factor),
            "scaling_sweep": build_scaling_sweep(public_benchmark_report, rts_network, power_factor),
        },
    }
    report["summary_note"] = build_note(report)
    return report


def print_summary(report: dict) -> None:
    eff = report["benefits"]["efficiency"]
    harm = report["benefits"]["power_quality"]
    volt = report["benefits"]["voltage_and_dynamic"]
    sweep = report["benefits"]["scaling_sweep"]["rows"]
    print("Public benefit analysis")
    print("-----------------------")
    print("Benefit 1: Efficiency / loss reduction")
    print(
        f"Single-path Scenario 3 better than Scenario 2 for {eff['single_path']['scenario3_better_hours_fraction']:.1%} "
        f"of annualized hours; annualized loss difference {eff['single_path']['scenario3_minus_scenario2_annual_loss_mwh']:+.2f} MWh."
    )
    print(
        f"Multi-node Scenario 3(M) better than Scenario 2(M) for {eff['multi_node']['scenario3m_better_hours_fraction']:.1%} "
        f"of annualized hours; annualized loss difference {eff['multi_node']['scenario3m_minus_scenario2m_annual_loss_mwh']:+.2f} MWh."
    )
    print()

    print("Benefit 2: Power quality / harmonics")
    pq_rows = [
        [
            "Scenario 2(M)",
            str(harm["multi_node"]["Scenario 2(M)"]["interface_count"]),
            f"{harm['multi_node']['Scenario 2(M)']['thdv_proxy_pu']:.5f}",
        ],
        [
            "Scenario 3(M)",
            str(harm["multi_node"]["Scenario 3(M)"]["interface_count"]),
            f"{harm['multi_node']['Scenario 3(M)']['thdv_proxy_pu']:.5f}",
        ],
    ]
    print(format_table([["Case", "AC Interfaces", "THDv Proxy (pu)"], *pq_rows]))
    print()

    print("Benefit 3: Voltage response / upstream AC boundary")
    volt_rows = [
        [
            "Scenario 2(M)",
            f"{volt['multi_node']['base_case']['Scenario 2(M)']['max_poi_drop_pct_points']:.3f}",
            f"{volt['multi_node']['plus_10pct_step']['Scenario 2(M)']['max_poi_drop_pct_points']:.3f}",
        ],
        [
            "Scenario 3(M)",
            f"{volt['multi_node']['base_case']['Scenario 3(M)']['max_poi_drop_pct_points']:.3f}",
            f"{volt['multi_node']['plus_10pct_step']['Scenario 3(M)']['max_poi_drop_pct_points']:.3f}",
        ],
    ]
    print(format_table([["Case", "Base Max POI Drop (pct-pts)", "+10% Step Max POI Drop"], *volt_rows]))
    print()

    print("Scaling sweep: Scenario 2(M) vs Scenario 3(M)")
    sweep_rows = []
    for row in sweep:
        sweep_rows.append(
            [
                str(row["block_count"]),
                f"{row['total_it_mw']:.0f}",
                f"{row['scenario3m_minus_scenario2m_efficiency_pct_points']:+.3f}",
                f"{row['scenario2m_harmonic_thdv_proxy_pu']:.5f}",
                f"{row['scenario3m_harmonic_thdv_proxy_pu']:.5f}",
                f"{row['scenario2m_base_max_poi_drop_pct_points']:.3f}",
                f"{row['scenario3m_base_max_poi_drop_pct_points']:.3f}",
            ]
        )
    print(
        format_table(
            [
                [
                    "Blocks",
                    "IT MW",
                    "S3(M)-S2(M) Eff. pts",
                    "S2(M) THDv",
                    "S3(M) THDv",
                    "S2(M) Vdrop",
                    "S3(M) Vdrop",
                ],
                *sweep_rows,
            ]
        )
    )


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run the public-data-only benefit analysis.")
    parser.add_argument("--assumptions", type=Path, default=DEFAULT_ASSUMPTIONS)
    parser.add_argument("--topology", type=Path, default=DEFAULT_TOPOLOGY)
    parser.add_argument("--rts-bus", type=Path, default=DEFAULT_RTS_BUS)
    parser.add_argument("--rts-branch", type=Path, default=DEFAULT_RTS_BRANCH)
    parser.add_argument("--esif-zip", type=Path, default=DEFAULT_ESIF_ZIP)
    parser.add_argument("--public-benchmark-json", type=Path, default=DEFAULT_REPORT_JSON)
    parser.add_argument("--save-json", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--save-note", type=Path, default=DEFAULT_NOTE)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    if args.public_benchmark_json.exists():
        public_benchmark_report = json.loads(args.public_benchmark_json.read_text())
    else:
        public_benchmark_report = build_public_benchmark_report(
            assumptions_path=args.assumptions,
            topology_path=args.topology,
            rts_bus_path=args.rts_bus,
            rts_branch_path=args.rts_branch,
            esif_zip_path=args.esif_zip,
            bin_count=16,
            clip_quantile=0.995,
        )
    report = build_report(public_benchmark_report)
    write_json(args.save_json, report)
    args.save_note.write_text(report["summary_note"], encoding="utf-8")
    print_summary(report)


if __name__ == "__main__":
    main()
