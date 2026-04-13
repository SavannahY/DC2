#!/usr/bin/env python3
"""OpenDSS harmonics-mode benchmark on the public SMART-DS feeder.

This script extends `public_common_network_td_study.py` by running an explicit
harmonics-mode comparison for `Scenario 2(M)` and `Scenario 3(M)` on the same
public SMART-DS feeder model and the same normalized feeder-bank scaling.

The benchmark uses equal total harmonic current across scenarios so that the
result is not merely an artifact of injecting less total harmonic current in
the centralized case. The output is still a benchmark distortion study, not an
IEEE 519 compliance claim.
"""

from __future__ import annotations

import argparse
import json
import math
from pathlib import Path
from typing import Dict, Sequence

import opendssdirect as dss

from dc_backbone_model import format_pct, format_table, load_json
from public_common_network_td_study import (
    DEFAULT_ASSUMPTIONS,
    DEFAULT_OPERATING_REPORT,
    DEFAULT_POWER_FACTOR,
    DEFAULT_SMARTDS_DIR,
    DEFAULT_TARGET_PEAK_FEEDER_LOADING,
    DEFAULT_TOPOLOGY,
    choose_pois,
    feeder_base_summary,
    line_graph,
    load_map_for_scenario,
    load_snapshot_feeder,
    kvar_for_power_factor,
)
from dc_backbone_multinode_campus_model import load_topology

ROOT = Path(__file__).resolve().parent
DEFAULT_OUTPUT_JSON = ROOT / "public_harmonic_frequency_sweep_report.json"
DEFAULT_OUTPUT_NOTE = ROOT / "PUBLIC_HARMONIC_FREQUENCY_SWEEP.md"

TARGET_HARMONIC_RMS_PERCENT = 8.0
FUND_ONLY_SPECTRUM = "fund_only_public"
HARMONIC_FAMILIES = {
    "low_order_dominant": {"orders": [5, 7, 11, 13], "weights": [1.00, 0.80, 0.30, 0.20]},
    "balanced_filtered": {"orders": [5, 7, 11, 13, 17, 19], "weights": [0.60, 0.55, 0.45, 0.40, 0.35, 0.30]},
    "higher_order_filtered": {"orders": [5, 7, 11, 13, 17, 19], "weights": [0.20, 0.25, 0.50, 0.55, 0.60, 0.65]},
}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--assumptions", type=Path, default=DEFAULT_ASSUMPTIONS)
    parser.add_argument("--topology", type=Path, default=DEFAULT_TOPOLOGY)
    parser.add_argument("--operating-report", type=Path, default=DEFAULT_OPERATING_REPORT)
    parser.add_argument("--smartds-dir", type=Path, default=DEFAULT_SMARTDS_DIR)
    parser.add_argument("--power-factor", type=float, default=DEFAULT_POWER_FACTOR)
    parser.add_argument("--target-peak-feeder-loading", type=float, default=DEFAULT_TARGET_PEAK_FEEDER_LOADING)
    parser.add_argument("--output-json", type=Path, default=DEFAULT_OUTPUT_JSON)
    parser.add_argument("--output-note", type=Path, default=DEFAULT_OUTPUT_NOTE)
    parser.add_argument("--details", action="store_true")
    return parser.parse_args()


def write_json(path: Path, payload: dict) -> None:
    path.write_text(json.dumps(payload, indent=2), encoding="utf-8")


def feeder_bank_count(base_feeder_kw: float, scenario2_peak_kw: float, target_peak_loading: float) -> int:
    return max(1, math.ceil(scenario2_peak_kw / (target_peak_loading * base_feeder_kw)))


def normalized_percentages(weights: Sequence[float], target_rms_percent: float) -> list[float]:
    rms = math.sqrt(sum(value * value for value in weights))
    scale = target_rms_percent / rms if rms > 0.0 else 0.0
    return [value * scale for value in weights]


def prepare_feeder_and_positions(
    smartds_dir: Path,
    assumptions: dict,
    topology: dict,
    operating_report: dict,
    power_factor: float,
    target_peak_loading: float,
) -> dict:
    load_snapshot_feeder(smartds_dir)
    base_summary = feeder_base_summary()
    pois = choose_pois(line_graph(), dss.Circuit.AllBusNames()[0])
    peak_fraction = max(float(bin_row["load_fraction"]) for bin_row in operating_report["annual_layer"]["esif_profile"]["load_profile"])
    raw_peak_s2_kw = sum(
        load_map_for_scenario("Scenario 2(M)", peak_fraction, assumptions, topology, pois).values()
    )
    banks = feeder_bank_count(base_summary["total_power_kw"], raw_peak_s2_kw, target_peak_loading)
    p95_fraction = float(operating_report["annual_layer"]["esif_profile"]["meta"]["normalized_p95_fraction"])
    return {
        "base_summary": base_summary,
        "pois": pois,
        "feeder_bank_count": banks,
        "peak_fraction": peak_fraction,
        "p95_fraction": p95_fraction,
    }


def add_campus_loads(load_map_kw: Dict[str, float], power_factor: float, prefix: str) -> None:
    for index, (bus_name, kw) in enumerate(load_map_kw.items(), start=1):
        kvar = kvar_for_power_factor(kw, power_factor)
        dss.Text.Command(
            "New Load.{prefix}_{idx} phases=3 conn=wye bus1={bus}.1.2.3 "
            "kV=12.47 model=1 kW={kw:.6f} kvar={kvar:.6f}".format(
                prefix=prefix,
                idx=index,
                bus=bus_name,
                kw=kw,
                kvar=kvar,
            )
        )


def set_all_loads_fund_only() -> None:
    dss.Text.Command(f"New Spectrum.{FUND_ONLY_SPECTRUM} NumHarm=1 Harmonic=(1) %Mag=(100) Angle=(0)")
    for load_name in dss.Loads.AllNames():
        dss.Text.Command(f"Edit Load.{load_name} Spectrum={FUND_ONLY_SPECTRUM}")


def create_harmonic_sources(
    scenario_label: str,
    load_map_kw: Dict[str, float],
    spectrum_name: str,
    benchmark_total_current_a: float,
) -> None:
    per_source_current = benchmark_total_current_a / max(1, len(load_map_kw))
    for index, bus_name in enumerate(load_map_kw.keys(), start=1):
        dss.Text.Command(
            "New Isource.{name}_{idx} phases=3 bus1={bus}.1.2.3 amps={amps:.6f} "
            "angle=0 spectrum={spectrum} scantype=pos".format(
                name=scenario_label.replace(" ", "_").replace("(", "").replace(")", ""),
                idx=index,
                bus=bus_name,
                amps=per_source_current,
                spectrum=spectrum_name,
            )
        )


def create_spectrum(spectrum_name: str, harmonic_orders: Sequence[int], percentages: Sequence[float]) -> None:
    harmonic_terms = " ".join(str(order) for order in harmonic_orders)
    mag_terms = " ".join(f"{value:.6f}" for value in percentages)
    angle_terms = " ".join("0" for _ in harmonic_orders)
    dss.Text.Command(
        "New Spectrum.{name} NumHarm={num} Harmonic=({harm}) %Mag=({mag}) Angle=({ang})".format(
            name=spectrum_name,
            num=len(harmonic_orders),
            harm=harmonic_terms,
            mag=mag_terms,
            ang=angle_terms,
        )
    )


def bus_fundamental_magnitudes(bus_names: Sequence[str]) -> dict:
    magnitudes = {}
    for bus_name in bus_names:
        dss.Circuit.SetActiveBus(bus_name)
        mags = dss.Bus.puVmagAngle()[0::2]
        magnitudes[bus_name] = max(mags) if mags else 0.0
    return magnitudes


def harmonic_bus_magnitude(bus_name: str) -> float:
    dss.Circuit.SetActiveBus(bus_name)
    mags = dss.Bus.puVmagAngle()[0::2]
    return max(mags) if mags else 0.0


def scenario_harmonic_result(
    smartds_dir: Path,
    assumptions: dict,
    topology: dict,
    feeder_setup: dict,
    spectrum_name: str,
    harmonic_orders: Sequence[int],
    percentages: Sequence[float],
    scenario_label: str,
    power_factor: float,
    benchmark_total_current_a: float,
) -> dict:
    load_snapshot_feeder(smartds_dir)
    load_fraction = feeder_setup["p95_fraction"]
    raw_load_map_kw = load_map_for_scenario(
        scenario_label, load_fraction, assumptions, topology, feeder_setup["pois"]
    )
    load_map_kw = {
        bus: kw / feeder_setup["feeder_bank_count"] for bus, kw in raw_load_map_kw.items()
    }
    add_campus_loads(load_map_kw, power_factor, scenario_label.lower().replace(" ", "_"))
    dss.Text.Command("Solve mode=snapshot")
    if not dss.Solution.Converged():
        raise RuntimeError(f"Snapshot solution failed before harmonics for {scenario_label}")

    set_all_loads_fund_only()
    create_spectrum(spectrum_name, harmonic_orders, percentages)
    create_harmonic_sources(scenario_label, load_map_kw, spectrum_name, benchmark_total_current_a)

    poi_names = list(load_map_kw.keys())
    fundamental_poi = bus_fundamental_magnitudes(poi_names)
    all_bus_names = dss.Circuit.AllBusNames()
    fundamental_all = bus_fundamental_magnitudes(all_bus_names)

    poi_harmonics = {bus: {} for bus in poi_names}
    all_bus_harmonic_sum = {bus: 0.0 for bus in all_bus_names}
    poi_harmonic_sum = {bus: 0.0 for bus in poi_names}

    for order in harmonic_orders:
        dss.Text.Command(f"Set Harmonics=({order})")
        dss.Text.Command("Solve mode=harmonics")
        if not dss.Solution.Converged():
            raise RuntimeError(f"Harmonics solve failed for order {order} in {scenario_label}")
        for bus_name in all_bus_names:
            magnitude = harmonic_bus_magnitude(bus_name)
            base = fundamental_all.get(bus_name, 0.0)
            ratio = magnitude / base if base > 0.0 else 0.0
            all_bus_harmonic_sum[bus_name] += ratio * ratio
            if bus_name in poi_harmonics:
                poi_harmonics[bus_name][str(order)] = ratio
                poi_harmonic_sum[bus_name] += ratio * ratio

    poi_thdv = {
        bus: math.sqrt(value) for bus, value in poi_harmonic_sum.items()
    }
    worst_bus = max(all_bus_harmonic_sum.items(), key=lambda item: math.sqrt(item[1]))
    return {
        "scenario_label": scenario_label,
        "load_fraction": load_fraction,
        "per_bank_campus_kw": sum(load_map_kw.values()),
        "raw_campus_kw": sum(raw_load_map_kw.values()),
        "poi_buses": poi_names,
        "poi_thdv_proxy": poi_thdv,
        "max_poi_thdv_proxy": max(poi_thdv.values()) if poi_thdv else 0.0,
        "worst_bus": {
            "bus": worst_bus[0],
            "thdv_proxy": math.sqrt(worst_bus[1]),
        },
        "harmonic_ratios_by_poi": poi_harmonics,
    }


def benchmark_total_current_a(
    assumptions: dict,
    topology: dict,
    feeder_setup: dict,
    power_factor: float,
) -> float:
    scenario2_raw_kw = sum(
        load_map_for_scenario("Scenario 2(M)", feeder_setup["p95_fraction"], assumptions, topology, feeder_setup["pois"]).values()
    )
    scenario3_raw_kw = sum(
        load_map_for_scenario("Scenario 3(M)", feeder_setup["p95_fraction"], assumptions, topology, feeder_setup["pois"]).values()
    )
    reference_kw = 0.5 * (scenario2_raw_kw + scenario3_raw_kw) / feeder_setup["feeder_bank_count"]
    return reference_kw / (math.sqrt(3.0) * 12.47 * power_factor)


def build_report(args: argparse.Namespace) -> dict:
    assumptions = load_json(args.assumptions)
    topology = load_topology(args.topology)
    operating_report = load_json(args.operating_report)
    feeder_setup = prepare_feeder_and_positions(
        args.smartds_dir,
        assumptions,
        topology,
        operating_report,
        args.power_factor,
        args.target_peak_feeder_loading,
    )
    benchmark_current_a = benchmark_total_current_a(assumptions, topology, feeder_setup, args.power_factor)

    families = {}
    for family_name, definition in HARMONIC_FAMILIES.items():
        percentages = normalized_percentages(definition["weights"], TARGET_HARMONIC_RMS_PERCENT)
        spectrum_name = f"spectrum_{family_name}"
        scenario2 = scenario_harmonic_result(
            args.smartds_dir,
            assumptions,
            topology,
            feeder_setup,
            spectrum_name,
            definition["orders"],
            percentages,
            "Scenario 2(M)",
            args.power_factor,
            benchmark_current_a,
        )
        scenario3 = scenario_harmonic_result(
            args.smartds_dir,
            assumptions,
            topology,
            feeder_setup,
            spectrum_name,
            definition["orders"],
            percentages,
            "Scenario 3(M)",
            args.power_factor,
            benchmark_current_a,
        )
        ratio = (
            scenario2["max_poi_thdv_proxy"] / scenario3["max_poi_thdv_proxy"]
            if scenario3["max_poi_thdv_proxy"] > 0.0
            else math.inf
        )
        families[family_name] = {
            "orders": definition["orders"],
            "percentages": percentages,
            "scenario_2m": scenario2,
            "scenario_3m": scenario3,
            "max_poi_thdv_ratio_s2_to_s3": ratio,
        }

    return {
        "meta": {
            "title": "Public OpenDSS harmonics-mode feeder benchmark",
            "updated": "2026-04-11",
            "note": (
                "Equal total harmonic current benchmark on the SMART-DS feeder bank. "
                "This is a benchmark THDv proxy study, not an IEEE 519 compliance study."
            ),
        },
        "dataset": {
            "smartds_dir": str(args.smartds_dir),
            "operating_report": str(args.operating_report),
            "power_factor": args.power_factor,
            "feeder_bank_count": feeder_setup["feeder_bank_count"],
            "target_peak_feeder_loading": args.target_peak_feeder_loading,
            "central_bus": feeder_setup["pois"]["central_bus"],
            "distributed_buses": feeder_setup["pois"]["distributed_buses"],
            "p95_load_fraction": feeder_setup["p95_fraction"],
            "benchmark_total_current_a_per_phase": benchmark_current_a,
        },
        "families": families,
    }


def build_note(report: dict) -> str:
    rows = [["Spectrum", "Scenario 2(M) max POI THDv proxy", "Scenario 3(M) max POI THDv proxy", "S2/S3 ratio"]]
    for family_name, payload in report["families"].items():
        rows.append(
            [
                family_name,
                format_pct(payload["scenario_2m"]["max_poi_thdv_proxy"]),
                format_pct(payload["scenario_3m"]["max_poi_thdv_proxy"]),
                f"{payload['max_poi_thdv_ratio_s2_to_s3']:.2f}x",
            ]
        )

    return "\n".join(
        [
            "# Public Harmonic Frequency Sweep",
            "",
            "Updated: April 11, 2026",
            "",
            "This note runs an explicit OpenDSS harmonics-mode benchmark on the same SMART-DS feeder used in the public common-network T&D study.",
            "",
            f"Equivalent feeder-bank count: `{report['dataset']['feeder_bank_count']}`.",
            f"P95 public operating point: `{format_pct(report['dataset']['p95_load_fraction'])}` of the 100 MW campus reference.",
            f"Scenario 3(M) central bus: `{report['dataset']['central_bus']}`.",
            "Scenario 2(M) distributed buses:",
            *[f"- `{bus}`" for bus in report["dataset"]["distributed_buses"]],
            "",
            "Equal-total harmonic-current benchmark result:",
            "",
            "```text",
            format_table(rows),
            "```",
            "",
            "Interpretation:",
            "",
            "- The scenarios are compared on the same feeder and at the same total benchmark harmonic current.",
            "- The result is therefore about network/interface sensitivity, not simply about injecting less total harmonic current.",
            "- This is still a benchmark THDv proxy, not an IEEE 519 compliance study.",
            "",
        ]
    )


def print_summary(report: dict, details: bool) -> None:
    print("Public harmonic frequency sweep")
    print("-------------------------------")
    print(
        f"Feeder-bank count {report['dataset']['feeder_bank_count']} | "
        f"p95 load fraction {format_pct(report['dataset']['p95_load_fraction'])} | "
        f"benchmark current {report['dataset']['benchmark_total_current_a_per_phase']:.2f} A/phase"
    )
    rows = [["Spectrum", "Scenario 2(M)", "Scenario 3(M)", "S2/S3 ratio"]]
    for family_name, payload in report["families"].items():
        rows.append(
            [
                family_name,
                format_pct(payload["scenario_2m"]["max_poi_thdv_proxy"]),
                format_pct(payload["scenario_3m"]["max_poi_thdv_proxy"]),
                f"{payload['max_poi_thdv_ratio_s2_to_s3']:.2f}x",
            ]
        )
    print(format_table(rows))

    if details:
        print()
        for family_name, payload in report["families"].items():
            print(f"{family_name}: {payload['orders']}")


def main() -> None:
    args = parse_args()
    report = build_report(args)
    write_json(args.output_json, report)
    args.output_note.write_text(build_note(report), encoding="utf-8")
    print_summary(report, args.details)


if __name__ == "__main__":
    main()
