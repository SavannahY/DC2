#!/usr/bin/env python3
"""Comparison model for AI-factory power architectures.

This script compares three topologies:
1. Traditional AC-centric
2. AC-fed SST / 800 VDC pod
3. Proposed MVDC backbone

The core model focuses on steady-state architecture comparison:
- stage-by-stage efficiency
- conductor losses
- annual energy loss / cost
- simple architecture scorecard for innovation framing

An optional OpenDSS-backed validation layer can also be enabled to run
quasi-static AC feeder/PCC simulations for the campus-side boundary of
each architecture. That AC-side study complements the analytical model;
it does not replace the DC-side architecture calculations and it is not
an EMT model of the full system.
"""

from __future__ import annotations

import argparse
import json
import math
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Sequence


HOURS_PER_YEAR = 8760.0


@dataclass
class ElementResult:
    name: str
    element_type: str
    load_ratio: float | None
    efficiency: float | None
    downstream_mw: float
    upstream_mw: float
    loss_mw: float


@dataclass
class LoadBinResult:
    name: str
    load_fraction: float
    delivered_it_mw: float
    upstream_input_mw: float
    total_loss_mw: float
    total_efficiency: float
    hours: float
    element_results: List[ElementResult]


def load_json(path: Path) -> dict:
    with path.open("r", encoding="utf-8") as handle:
        return json.load(handle)


def deep_copy_jsonable(value: dict) -> dict:
    return json.loads(json.dumps(value))


def interpolate_efficiency(points: Sequence[Sequence[float]], load_ratio: float) -> float:
    if not points:
        raise ValueError("Efficiency curve has no points")

    sorted_points = sorted((float(x), float(y)) for x, y in points)
    x = max(sorted_points[0][0], min(load_ratio, sorted_points[-1][0]))

    if x <= sorted_points[0][0]:
        return sorted_points[0][1]
    if x >= sorted_points[-1][0]:
        return sorted_points[-1][1]

    for (x0, y0), (x1, y1) in zip(sorted_points, sorted_points[1:]):
        if x0 <= x <= x1:
            span = x1 - x0
            if span == 0:
                return y1
            alpha = (x - x0) / span
            return y0 + alpha * (y1 - y0)

    return sorted_points[-1][1]


def stage_rated_output_mw(stage: dict, base_it_load_mw: float) -> float:
    if "rated_output_mw" in stage:
        return float(stage["rated_output_mw"])
    factor = float(stage.get("rated_output_mw_factor", 1.0))
    return factor * base_it_load_mw


def conductor_loss_mw(segment: dict, downstream_mw: float, default_pf: float) -> float:
    kind = segment["kind"]
    voltage_kv = float(segment["voltage_kv"])
    length_m = float(segment["length_m"])
    resistance_ohm_per_km = float(segment["resistance_ohm_per_km"])
    circuits = float(segment.get("circuits", 1.0))
    if circuits <= 0:
        raise ValueError("circuits must be > 0")
    pf = float(segment.get("power_factor", default_pf))

    voltage_v = voltage_kv * 1000.0
    resistance_total = resistance_ohm_per_km * (length_m / 1000.0)
    downstream_w = downstream_mw * 1e6

    if kind == "ac":
        current_a = downstream_w / (math.sqrt(3.0) * voltage_v * pf)
        # Parallel circuits share current. Total loss scales as I^2 R / n.
        loss_w = 3.0 * current_a * current_a * resistance_total / circuits
    elif kind == "dc":
        current_a = downstream_w / voltage_v
        # Two-conductor loop for point-to-point DC distribution.
        loss_w = 2.0 * current_a * current_a * resistance_total / circuits
    else:
        raise ValueError(f"Unsupported conductor kind: {kind}")

    return loss_w / 1e6


def evaluate_element(
    element: dict,
    downstream_mw: float,
    curves: Dict[str, dict],
    base_it_load_mw: float,
    default_pf: float,
) -> ElementResult:
    element_type = element["type"]
    name = element["name"]

    if element_type == "stage":
        curve_name = element["curve"]
        rated_output = stage_rated_output_mw(element, base_it_load_mw)
        load_ratio = downstream_mw / rated_output if rated_output else 0.0
        efficiency = interpolate_efficiency(curves[curve_name]["points"], load_ratio)
        upstream_mw = downstream_mw / efficiency
        return ElementResult(
            name=name,
            element_type=element_type,
            load_ratio=load_ratio,
            efficiency=efficiency,
            downstream_mw=downstream_mw,
            upstream_mw=upstream_mw,
            loss_mw=upstream_mw - downstream_mw,
        )

    if element_type == "conductor":
        loss_mw = conductor_loss_mw(element, downstream_mw, default_pf)
        upstream_mw = downstream_mw + loss_mw
        return ElementResult(
            name=name,
            element_type=element_type,
            load_ratio=None,
            efficiency=None,
            downstream_mw=downstream_mw,
            upstream_mw=upstream_mw,
            loss_mw=loss_mw,
        )

    raise ValueError(f"Unsupported element type: {element_type}")


def evaluate_load_bin(
    architecture: dict,
    assumptions: dict,
    delivered_it_mw: float,
    load_bin: dict,
) -> LoadBinResult:
    evaluation = evaluate_path(
        elements=architecture["elements"],
        assumptions=assumptions,
        delivered_it_mw=delivered_it_mw,
    )
    upstream_input_mw = evaluation["upstream_input_mw"]
    total_loss_mw = upstream_input_mw - delivered_it_mw
    total_efficiency = delivered_it_mw / upstream_input_mw if upstream_input_mw else 0.0

    return LoadBinResult(
        name=load_bin["name"],
        load_fraction=float(load_bin["load_fraction"]),
        delivered_it_mw=delivered_it_mw,
        upstream_input_mw=upstream_input_mw,
        total_loss_mw=total_loss_mw,
        total_efficiency=total_efficiency,
        hours=HOURS_PER_YEAR * float(load_bin["hours_fraction"]),
        element_results=evaluation["element_results"],
    )


def evaluate_path(
    elements: List[dict],
    assumptions: dict,
    delivered_it_mw: float,
) -> dict:
    curves = assumptions["curves"]
    default_pf = float(assumptions["global"].get("default_power_factor", 0.98))
    base_it_load_mw = float(assumptions["global"]["base_it_load_mw"])

    downstream_mw = delivered_it_mw
    reverse_results: List[ElementResult] = []

    for element in reversed(elements):
        result = evaluate_element(
            element=element,
            downstream_mw=downstream_mw,
            curves=curves,
            base_it_load_mw=base_it_load_mw,
            default_pf=default_pf,
        )
        reverse_results.append(result)
        downstream_mw = result.upstream_mw

    return {
        "upstream_input_mw": downstream_mw,
        "element_results": list(reversed(reverse_results)),
    }


def path_elements_from_anchor(architecture: dict, anchor_name: str) -> List[dict]:
    for index, element in enumerate(architecture["elements"]):
        if element["name"] == anchor_name:
            return architecture["elements"][index:]
    raise ValueError(f"Anchor '{anchor_name}' not found in architecture '{architecture['name']}'")


def evaluate_architecture_input_mw(architecture: dict, assumptions: dict, delivered_it_mw: float) -> float:
    return evaluate_path(
        elements=architecture["elements"],
        assumptions=assumptions,
        delivered_it_mw=delivered_it_mw,
    )["upstream_input_mw"]


def evaluate_subpath_input_mw(
    architecture: dict,
    assumptions: dict,
    anchor_name: str,
    delivered_it_mw: float,
) -> float:
    return evaluate_path(
        elements=path_elements_from_anchor(architecture, anchor_name),
        assumptions=assumptions,
        delivered_it_mw=delivered_it_mw,
    )["upstream_input_mw"]


def marginal_path_efficiency(
    architecture: dict,
    assumptions: dict,
    anchor_name: str,
    delivered_it_mw: float,
    delta_fraction: float,
) -> float:
    low_it_mw = delivered_it_mw * (1.0 - delta_fraction)
    high_it_mw = delivered_it_mw * (1.0 + delta_fraction)
    low_input_mw = evaluate_subpath_input_mw(architecture, assumptions, anchor_name, low_it_mw)
    high_input_mw = evaluate_subpath_input_mw(architecture, assumptions, anchor_name, high_it_mw)
    delta_it_mw = high_it_mw - low_it_mw
    delta_input_mw = high_input_mw - low_input_mw
    if delta_input_mw <= 0:
        raise ValueError("Marginal path efficiency is non-positive")
    return delta_it_mw / delta_input_mw


def build_dynamic_summary(architecture: dict, assumptions: dict) -> List[dict]:
    dynamic_model = assumptions.get("dynamic_model")
    if not dynamic_model:
        return []

    base_it_load_mw = float(assumptions["global"]["base_it_load_mw"])
    anchor_name = architecture["native_buffer_anchor"]
    marginal_delta_fraction = float(dynamic_model.get("marginal_delta_fraction", 0.01))
    base_input_mw = evaluate_architecture_input_mw(architecture, assumptions, base_it_load_mw)
    native_buffer_marginal_eff = marginal_path_efficiency(
        architecture=architecture,
        assumptions=assumptions,
        anchor_name=anchor_name,
        delivered_it_mw=base_it_load_mw,
        delta_fraction=marginal_delta_fraction,
    )

    cases = []
    for dynamic_case in dynamic_model["cases"]:
        frequency_hz = float(dynamic_case["frequency_hz"])
        emt_relevant = frequency_hz > 5.0
        for amplitude_fraction in dynamic_case["amplitude_sweep_fraction"]:
            amplitude_fraction = float(amplitude_fraction)
            high_it_mw = base_it_load_mw * (1.0 + amplitude_fraction)
            low_it_mw = max(0.0, base_it_load_mw * (1.0 - amplitude_fraction))
            high_input_mw = evaluate_architecture_input_mw(architecture, assumptions, high_it_mw)
            low_input_mw = evaluate_architecture_input_mw(architecture, assumptions, low_it_mw)
            pcc_peak_mw = max(high_input_mw - base_input_mw, base_input_mw - low_input_mw)
            pcc_peak_to_peak_mw = high_input_mw - low_input_mw
            it_peak_mw = base_it_load_mw * amplitude_fraction
            native_buffer_peak_mw = it_peak_mw / native_buffer_marginal_eff
            native_buffer_energy_kwh = native_buffer_peak_mw / (2.0 * math.pi * frequency_hz) / 3.6

            cases.append(
                {
                    "case_name": dynamic_case["name"],
                    "frequency_hz": frequency_hz,
                    "frequency_basis": dynamic_case["frequency_basis"],
                    "source_ids": dynamic_case.get("source_ids", []),
                    "it_amplitude_fraction": amplitude_fraction,
                    "it_peak_mw": it_peak_mw,
                    "raw_pcc_peak_mw": pcc_peak_mw,
                    "raw_pcc_peak_to_peak_mw": pcc_peak_to_peak_mw,
                    "raw_pcc_peak_fraction_of_base_input": pcc_peak_mw / base_input_mw,
                    "native_buffer_anchor": anchor_name,
                    "native_buffer_marginal_efficiency": native_buffer_marginal_eff,
                    "native_buffer_peak_mw": native_buffer_peak_mw,
                    "native_buffer_energy_kwh": native_buffer_energy_kwh,
                    "emt_relevant": emt_relevant,
                }
            )

    return cases


def aggregate_architecture(architecture: dict, assumptions: dict) -> dict:
    base_it_load_mw = float(assumptions["global"]["base_it_load_mw"])
    electricity_price = float(assumptions["global"]["electricity_price_per_mwh"])

    load_bin_results = []
    annual_delivered_mwh = 0.0
    annual_input_mwh = 0.0
    annual_loss_mwh = 0.0
    element_annual_losses_mwh: Dict[str, float] = {}

    for load_bin in assumptions["load_profile"]:
        delivered_it_mw = base_it_load_mw * float(load_bin["load_fraction"])
        result = evaluate_load_bin(architecture, assumptions, delivered_it_mw, load_bin)
        load_bin_results.append(result)

        annual_delivered_mwh += result.delivered_it_mw * result.hours
        annual_input_mwh += result.upstream_input_mw * result.hours
        annual_loss_mwh += result.total_loss_mw * result.hours
        for element_result in result.element_results:
            element_annual_losses_mwh.setdefault(element_result.name, 0.0)
            element_annual_losses_mwh[element_result.name] += element_result.loss_mw * result.hours

    average_efficiency = annual_delivered_mwh / annual_input_mwh if annual_input_mwh else 0.0
    annual_loss_cost = annual_loss_mwh * electricity_price
    full_load = evaluate_load_bin(
        architecture=architecture,
        assumptions=assumptions,
        delivered_it_mw=base_it_load_mw,
        load_bin={"name": "full_load", "load_fraction": 1.0, "hours_fraction": 0.0},
    )

    return {
        "name": architecture["name"],
        "display_name": architecture["display_name"],
        "annual_delivered_mwh": annual_delivered_mwh,
        "annual_input_mwh": annual_input_mwh,
        "annual_loss_mwh": annual_loss_mwh,
        "annual_loss_cost_usd": annual_loss_cost,
        "average_total_efficiency": average_efficiency,
        "full_load_total_efficiency": full_load.total_efficiency,
        "full_load_input_mw": full_load.upstream_input_mw,
        "full_load_loss_mw": full_load.total_loss_mw,
        "full_load_breakdown": [element_result.__dict__ for element_result in full_load.element_results],
        "load_bins": [
            {
                "name": load_bin_result.name,
                "load_fraction": load_bin_result.load_fraction,
                "delivered_it_mw": load_bin_result.delivered_it_mw,
                "upstream_input_mw": load_bin_result.upstream_input_mw,
                "total_loss_mw": load_bin_result.total_loss_mw,
                "total_efficiency": load_bin_result.total_efficiency,
                "hours": load_bin_result.hours,
                "element_results": [
                    element_result.__dict__ for element_result in load_bin_result.element_results
                ],
            }
            for load_bin_result in load_bin_results
        ],
        "element_annual_losses_mwh": element_annual_losses_mwh,
        "innovation_metrics": architecture["innovation_metrics"],
        "native_buffer_anchor": architecture.get("native_buffer_anchor"),
        "dynamic_cases": build_dynamic_summary(architecture, assumptions),
        "notes": architecture.get("notes", ""),
    }


def get_opendss_validation_settings(assumptions: dict) -> dict:
    defaults = {
        "note": (
            "OpenDSS is used as an AC-side quasi-static validation layer for the "
            "source-to-PCC feeder boundary. The downstream DC network remains "
            "represented by an equivalent load at that AC boundary."
        ),
        "source_ids": [],
        "line_x_to_r_ratio": 1.0,
        "zero_sequence_multiplier": 3.0,
        "centralized_front_end_ac_stub_length_m": 20.0,
        "centralized_front_end_ac_stub_circuits": 1,
        "samples_per_cycle": 64,
        "simulated_cycles": 2,
    }
    settings = deep_copy_jsonable(defaults)
    settings.update(assumptions.get("opendss_validation", {}))
    return settings


def get_opendss_harmonics_settings(assumptions: dict) -> dict:
    defaults = {
        "note": (
            "OpenDSS harmonic mode is used as a standardized AC-boundary harmonic-sensitivity scan. "
            "A fixed three-phase harmonic current probe is injected at the PCC and the resulting "
            "harmonic voltage distortion is compared across scenarios."
        ),
        "source_ids": [],
        "harmonic_orders": [5, 7, 11, 13],
        "probe_current_amps_per_phase": 10.0,
        "probe_spectrum_percent": 100.0,
        "scan_type": "pos",
    }
    settings = deep_copy_jsonable(defaults)
    settings.update(assumptions.get("opendss_harmonics_validation", {}))
    settings["harmonic_orders"] = [int(order) for order in settings.get("harmonic_orders", [])]
    return settings


def first_modeled_ac_conductor(assumptions: dict) -> dict:
    for architecture in assumptions["architectures"]:
        for element in architecture["elements"]:
            if element["type"] == "conductor" and element.get("kind") == "ac":
                return element
    raise ValueError("No AC conductor found in the modeled architectures")


def opendss_ac_boundary(architecture: dict, assumptions: dict) -> dict:
    settings = get_opendss_validation_settings(assumptions)

    for index, element in enumerate(architecture["elements"]):
        if element["type"] == "conductor" and element.get("kind") == "ac":
            return {
                "segment": deep_copy_jsonable(element),
                "downstream_elements": architecture["elements"][index + 1 :],
                "is_synthetic_stub": False,
                "boundary_note": f"Uses the first modeled AC feeder segment: {element['name']}.",
            }

    reference_segment = first_modeled_ac_conductor(assumptions)
    x_to_r_ratio = float(settings["line_x_to_r_ratio"])
    synthetic_segment = {
        "type": "conductor",
        "name": "Centralized front-end AC stub",
        "kind": "ac",
        "voltage_kv": float(reference_segment["voltage_kv"]),
        "length_m": float(settings["centralized_front_end_ac_stub_length_m"]),
        "resistance_ohm_per_km": float(reference_segment["resistance_ohm_per_km"]),
        "reactance_ohm_per_km": float(reference_segment["resistance_ohm_per_km"]) * x_to_r_ratio,
        "circuits": int(settings["centralized_front_end_ac_stub_circuits"]),
        "source_ids": settings.get("source_ids", []),
    }
    return {
        "segment": synthetic_segment,
        "downstream_elements": architecture["elements"],
        "is_synthetic_stub": True,
        "boundary_note": (
            "Uses a short synthetic AC stub to represent the centralized front-end "
            "connection at the substation boundary before the architecture becomes DC."
        ),
    }


def evaluate_opendss_equivalent_load_mw(
    architecture: dict,
    assumptions: dict,
    delivered_it_mw: float,
) -> float:
    boundary = opendss_ac_boundary(architecture, assumptions)
    downstream_elements = boundary["downstream_elements"]
    if not downstream_elements:
        return delivered_it_mw
    return evaluate_path(
        elements=downstream_elements,
        assumptions=assumptions,
        delivered_it_mw=delivered_it_mw,
    )["upstream_input_mw"]


def opendss_power_factor_for_architecture(architecture: dict, assumptions: dict) -> float:
    settings = get_opendss_validation_settings(assumptions)
    overrides = settings.get("power_factor_overrides_by_architecture", {})
    if architecture["name"] in overrides:
        return float(overrides[architecture["name"]])
    return float(assumptions["global"].get("default_power_factor", 0.98))


def mw_to_kvar(mw: float, pf: float) -> float:
    pf = max(1e-6, min(abs(pf), 1.0))
    angle = math.acos(pf)
    return mw * 1000.0 * math.tan(angle)


def build_opendss_circuit(dss, segment: dict, pf: float, load_mw: float, assumptions: dict) -> None:
    settings = get_opendss_validation_settings(assumptions)
    resistance_ohm_per_km = float(segment["resistance_ohm_per_km"])
    reactance_ohm_per_km = float(
        segment.get(
            "reactance_ohm_per_km",
            resistance_ohm_per_km * float(settings["line_x_to_r_ratio"]),
        )
    )
    zero_sequence_multiplier = float(settings["zero_sequence_multiplier"])
    resistance_zero_ohm_per_km = float(
        segment.get("resistance_zero_ohm_per_km", resistance_ohm_per_km * zero_sequence_multiplier)
    )
    reactance_zero_ohm_per_km = float(
        segment.get("reactance_zero_ohm_per_km", reactance_ohm_per_km * zero_sequence_multiplier)
    )

    load_kvar = mw_to_kvar(load_mw, pf)
    voltage_kv = float(segment["voltage_kv"])
    length_km = float(segment["length_m"]) / 1000.0

    dss.Text.Command("clear")
    dss.Text.Command(f"new circuit.ai_factory_validation basekv={voltage_kv:.6f} pu=1.0 phases=3 bus1=sourcebus")
    dss.Text.Command(
        "new linecode.validation_line "
        f"nphases=3 r1={resistance_ohm_per_km:.9f} x1={reactance_ohm_per_km:.9f} "
        f"r0={resistance_zero_ohm_per_km:.9f} x0={reactance_zero_ohm_per_km:.9f} units=km"
    )
    dss.Text.Command(
        "new line.source_to_pcc "
        f"bus1=sourcebus bus2=pcc phases=3 length={length_km:.9f} units=km linecode=validation_line"
    )
    dss.Text.Command(
        "new load.ai_factory_equivalent "
        f"bus1=pcc phases=3 conn=wye model=1 kv={voltage_kv:.6f} vminpu=0.0 vmaxpu=2.0 "
        f"kw={load_mw * 1000.0:.6f} kvar={load_kvar:.6f}"
    )
    dss.Text.Command(f"set voltagebases=[{voltage_kv:.6f}]")
    dss.Text.Command("calcvoltagebases")


def solve_opendss_snapshot(dss, load_mw: float, pf: float) -> dict:
    dss.Loads.Name("ai_factory_equivalent")
    dss.Loads.kW(load_mw * 1000.0)
    dss.Loads.kvar(mw_to_kvar(load_mw, pf))
    dss.Solution.Solve()
    if not dss.Solution.Converged():
        raise RuntimeError("OpenDSS solution did not converge")

    dss.Circuit.SetActiveBus("pcc")
    vmag_angle = dss.Bus.puVmagAngle()
    phase_vmags = vmag_angle[0::2][:3]

    dss.Circuit.SetActiveElement("line.source_to_pcc")
    line_losses_w, _ = dss.CktElement.Losses()
    currents_mag_angle = dss.CktElement.CurrentsMagAng()
    current_magnitudes = currents_mag_angle[0::2]

    total_power_kw, total_power_kvar = dss.Circuit.TotalPower()
    source_power_mw = -total_power_kw / 1000.0
    source_reactive_mvar = -total_power_kvar / 1000.0

    return {
        "source_power_mw": source_power_mw,
        "source_reactive_mvar": source_reactive_mvar,
        "pcc_voltage_min_pu": min(phase_vmags),
        "pcc_voltage_max_pu": max(phase_vmags),
        "feeder_loss_mw": line_losses_w / 1e6,
        "peak_line_current_a": max(current_magnitudes) if current_magnitudes else 0.0,
    }


def average_phase_pu_voltage_magnitude(dss, bus_name: str) -> float:
    dss.Circuit.SetActiveBus(bus_name)
    vmag_angle = dss.Bus.puVmagAngle()
    phase_vmags = [abs(value) for value in vmag_angle[0::2][:3]]
    if not phase_vmags:
        return 0.0
    return sum(phase_vmags) / len(phase_vmags)


def peak_phase_current_a(dss, element_name: str) -> float:
    dss.Circuit.SetActiveElement(element_name)
    currents_mag_angle = dss.CktElement.CurrentsMagAng()
    current_magnitudes = [abs(value) for value in currents_mag_angle[0::2]]
    return max(current_magnitudes) if current_magnitudes else 0.0


def harmonic_spectrum_command(settings: dict) -> str:
    harmonic_orders = [1] + [int(order) for order in settings["harmonic_orders"]]
    harmonic_magnitudes = [0.0] + [float(settings["probe_spectrum_percent"])] * len(settings["harmonic_orders"])
    angles = [0.0] * len(harmonic_orders)
    harmonic_orders_str = ", ".join(str(order) for order in harmonic_orders)
    harmonic_magnitudes_str = ", ".join(f"{magnitude:.6f}" for magnitude in harmonic_magnitudes)
    angles_str = ", ".join(f"{angle:.6f}" for angle in angles)
    return (
        "new spectrum.hprobe_scan "
        f"numharm={len(harmonic_orders)} "
        f"harmonic=({harmonic_orders_str}) "
        f"%mag=({harmonic_magnitudes_str}) "
        f"angle=({angles_str})"
    )


def run_opendss_harmonic_validation_for_architecture(architecture: dict, assumptions: dict) -> dict:
    try:
        import opendssdirect as dss
    except ImportError as exc:
        raise RuntimeError(
            "OpenDSS harmonic validation requires opendssdirect.py. Install it with "
            "`python3 -m pip install --user opendssdirect.py`."
        ) from exc

    opendss_settings = get_opendss_validation_settings(assumptions)
    harmonic_settings = get_opendss_harmonics_settings(assumptions)
    boundary = opendss_ac_boundary(architecture, assumptions)
    segment = boundary["segment"]
    pf = opendss_power_factor_for_architecture(architecture, assumptions)
    base_it_load_mw = float(assumptions["global"]["base_it_load_mw"])
    base_equivalent_load_mw = evaluate_opendss_equivalent_load_mw(architecture, assumptions, base_it_load_mw)

    build_opendss_circuit(dss, segment, pf, base_equivalent_load_mw, assumptions)
    base_snapshot = solve_opendss_snapshot(dss, base_equivalent_load_mw, pf)
    base_avg_pu_voltage = average_phase_pu_voltage_magnitude(dss, "pcc")
    voltage_kv = float(segment["voltage_kv"])
    phase_base_voltage_v = voltage_kv * 1000.0 / math.sqrt(3.0)

    dss.Text.Command(harmonic_spectrum_command(harmonic_settings))
    dss.Text.Command(
        "new isource.hprobe "
        f"bus1=pcc phases=3 amps={float(harmonic_settings['probe_current_amps_per_phase']):.6f} "
        f"angle=0 spectrum=hprobe_scan scantype={harmonic_settings['scan_type']}"
    )

    harmonic_rows = []
    voltage_distortion_rss = 0.0
    worst_order = None
    worst_single_pct = -1.0
    max_transfer_impedance = 0.0

    for order in harmonic_settings["harmonic_orders"]:
        dss.Text.Command(f"set harmonics=({int(order)})")
        dss.Text.Command("solve mode=harmonics")
        if not dss.Solution.Converged():
            raise RuntimeError(f"OpenDSS harmonic solution did not converge for harmonic order {order}")

        dss.Circuit.SetActiveBus("pcc")
        pu_vmag_angle = dss.Bus.puVmagAngle()
        phase_vmags = [abs(value) for value in pu_vmag_angle[0::2][:3]]
        avg_voltage_pu = sum(phase_vmags) / len(phase_vmags) if phase_vmags else 0.0
        max_voltage_pu = max(phase_vmags) if phase_vmags else 0.0
        avg_voltage_pct_of_fundamental = (
            avg_voltage_pu / base_avg_pu_voltage * 100.0 if base_avg_pu_voltage else 0.0
        )
        max_voltage_pct_of_fundamental = (
            max_voltage_pu / base_avg_pu_voltage * 100.0 if base_avg_pu_voltage else 0.0
        )
        avg_voltage_v = avg_voltage_pu * phase_base_voltage_v
        transfer_impedance_ohm = (
            avg_voltage_v / float(harmonic_settings["probe_current_amps_per_phase"])
            if float(harmonic_settings["probe_current_amps_per_phase"])
            else 0.0
        )
        peak_current_a = peak_phase_current_a(dss, "line.source_to_pcc")

        harmonic_rows.append(
            {
                "order": int(order),
                "frequency_hz": float(order) * 60.0,
                "pcc_avg_voltage_pu": avg_voltage_pu,
                "pcc_max_voltage_pu": max_voltage_pu,
                "avg_voltage_pct_of_fundamental": avg_voltage_pct_of_fundamental,
                "max_voltage_pct_of_fundamental": max_voltage_pct_of_fundamental,
                "transfer_impedance_ohm_ln": transfer_impedance_ohm,
                "peak_line_current_a": peak_current_a,
            }
        )

        voltage_distortion_rss += (avg_voltage_pu / base_avg_pu_voltage) ** 2 if base_avg_pu_voltage else 0.0
        if max_voltage_pct_of_fundamental > worst_single_pct:
            worst_single_pct = max_voltage_pct_of_fundamental
            worst_order = int(order)
        max_transfer_impedance = max(max_transfer_impedance, transfer_impedance_ohm)

    return {
        "tool": "OpenDSS",
        "method": "harmonic_sensitivity_scan",
        "note": harmonic_settings["note"],
        "source_ids": harmonic_settings.get("source_ids", []),
        "ac_boundary": {
            "name": segment["name"],
            "voltage_kv": voltage_kv,
            "length_m": float(segment["length_m"]),
            "is_synthetic_stub": boundary["is_synthetic_stub"],
            "boundary_note": boundary["boundary_note"],
        },
        "base_case": {
            "equivalent_ac_load_mw": base_equivalent_load_mw,
            "source_power_mw": base_snapshot["source_power_mw"],
            "pcc_voltage_min_pu": base_snapshot["pcc_voltage_min_pu"],
            "base_avg_voltage_pu": base_avg_pu_voltage,
        },
        "probe_current_amps_per_phase": float(harmonic_settings["probe_current_amps_per_phase"]),
        "scan_type": harmonic_settings["scan_type"],
        "harmonic_orders": harmonic_settings["harmonic_orders"],
        "harmonics": harmonic_rows,
        "probe_thdv_percent": math.sqrt(voltage_distortion_rss) * 100.0,
        "worst_single_harmonic_percent": worst_single_pct,
        "worst_single_harmonic_order": worst_order,
        "max_transfer_impedance_ohm_ln": max_transfer_impedance,
        "interpretation": (
            "The scan injects the same harmonic current probe at the PCC for each scenario. "
            "Lower resulting harmonic voltage indicates a less sensitive AC boundary. "
            "This is a structural sensitivity result, not a site-specific converter-spectrum or IEEE 519 compliance result."
        ),
    }


def dynamic_case_key(case_name: str, amplitude_fraction: float) -> tuple[str, float]:
    return case_name, round(float(amplitude_fraction), 6)


def run_opendss_validation_for_architecture(architecture: dict, result: dict, assumptions: dict) -> dict:
    try:
        import opendssdirect as dss
    except ImportError as exc:
        raise RuntimeError(
            "OpenDSS validation requires opendssdirect.py. Install it with "
            "`python3 -m pip install --user opendssdirect.py`."
        ) from exc

    settings = get_opendss_validation_settings(assumptions)
    boundary = opendss_ac_boundary(architecture, assumptions)
    segment = boundary["segment"]
    pf = opendss_power_factor_for_architecture(architecture, assumptions)
    base_it_load_mw = float(assumptions["global"]["base_it_load_mw"])
    samples_per_cycle = int(settings["samples_per_cycle"])
    simulated_cycles = int(settings["simulated_cycles"])
    if samples_per_cycle <= 1 or simulated_cycles <= 0:
        raise ValueError("OpenDSS validation requires samples_per_cycle > 1 and simulated_cycles > 0")

    base_equivalent_load_mw = evaluate_opendss_equivalent_load_mw(architecture, assumptions, base_it_load_mw)
    build_opendss_circuit(dss, segment, pf, base_equivalent_load_mw, assumptions)
    base_snapshot = solve_opendss_snapshot(dss, base_equivalent_load_mw, pf)

    analytical_lookup = {
        dynamic_case_key(dynamic_case["case_name"], dynamic_case["it_amplitude_fraction"]): dynamic_case
        for dynamic_case in result.get("dynamic_cases", [])
    }

    dynamic_summaries = []
    for dynamic_case in assumptions.get("dynamic_model", {}).get("cases", []):
        frequency_hz = float(dynamic_case["frequency_hz"])
        for amplitude_fraction in dynamic_case["amplitude_sweep_fraction"]:
            amplitude_fraction = float(amplitude_fraction)
            time_step_s = 1.0 / (frequency_hz * samples_per_cycle)
            step_count = samples_per_cycle * simulated_cycles

            source_powers = []
            min_voltages = []
            feeder_losses = []
            feeder_currents = []

            for step in range(step_count + 1):
                time_s = step * time_step_s
                delivered_it_mw = base_it_load_mw * (
                    1.0 + amplitude_fraction * math.sin(2.0 * math.pi * frequency_hz * time_s)
                )
                equivalent_load_mw = evaluate_opendss_equivalent_load_mw(
                    architecture,
                    assumptions,
                    delivered_it_mw,
                )
                snapshot = solve_opendss_snapshot(dss, equivalent_load_mw, pf)
                source_powers.append(snapshot["source_power_mw"])
                min_voltages.append(snapshot["pcc_voltage_min_pu"])
                feeder_losses.append(snapshot["feeder_loss_mw"])
                feeder_currents.append(snapshot["peak_line_current_a"])

            source_peak_mw = max(
                max(source_powers) - base_snapshot["source_power_mw"],
                base_snapshot["source_power_mw"] - min(source_powers),
            )
            base_voltage_pu = base_snapshot["pcc_voltage_min_pu"]
            voltage_swing_pct = max(
                abs(v - base_voltage_pu) / base_voltage_pu * 100.0 for v in min_voltages
            ) if base_voltage_pu else 0.0

            analytical_case = analytical_lookup.get(dynamic_case_key(dynamic_case["name"], amplitude_fraction), {})

            dynamic_summaries.append(
                {
                    "case_name": dynamic_case["name"],
                    "frequency_hz": frequency_hz,
                    "it_amplitude_fraction": amplitude_fraction,
                    "time_step_s": time_step_s,
                    "simulated_duration_s": step_count * time_step_s,
                    "steps": step_count + 1,
                    "source_power_base_mw": base_snapshot["source_power_mw"],
                    "source_power_peak_mw": source_peak_mw,
                    "source_power_peak_to_peak_mw": max(source_powers) - min(source_powers),
                    "source_power_peak_fraction_of_base": (
                        source_peak_mw / base_snapshot["source_power_mw"]
                        if base_snapshot["source_power_mw"]
                        else 0.0
                    ),
                    "minimum_pcc_voltage_pu": min(min_voltages),
                    "maximum_pcc_voltage_pu": max(min_voltages),
                    "max_pcc_voltage_swing_from_base_pct": voltage_swing_pct,
                    "base_feeder_loss_mw": base_snapshot["feeder_loss_mw"],
                    "peak_feeder_loss_mw": max(feeder_losses),
                    "average_feeder_loss_mw": sum(feeder_losses) / len(feeder_losses),
                    "peak_feeder_current_a": max(feeder_currents),
                    "analytical_raw_pcc_peak_mw": analytical_case.get("raw_pcc_peak_mw"),
                    "analytical_raw_pcc_peak_fraction_of_base_input": analytical_case.get(
                        "raw_pcc_peak_fraction_of_base_input"
                    ),
                }
            )

    return {
        "tool": "OpenDSS",
        "tool_version": dss.Basic.Version(),
        "method": "quasi_static_snapshot_series",
        "note": settings["note"],
        "source_ids": settings.get("source_ids", []),
        "power_factor": pf,
        "ac_boundary": {
            "name": segment["name"],
            "voltage_kv": float(segment["voltage_kv"]),
            "length_m": float(segment["length_m"]),
            "resistance_ohm_per_km": float(segment["resistance_ohm_per_km"]),
            "reactance_ohm_per_km": float(
                segment.get(
                    "reactance_ohm_per_km",
                    float(segment["resistance_ohm_per_km"]) * float(settings["line_x_to_r_ratio"]),
                )
            ),
            "circuits": int(segment.get("circuits", 1)),
            "is_synthetic_stub": boundary["is_synthetic_stub"],
            "boundary_note": boundary["boundary_note"],
        },
        "base_snapshot": {
            "equivalent_ac_load_mw": base_equivalent_load_mw,
            **base_snapshot,
        },
        "dynamic_cases": dynamic_summaries,
    }


def run_model(assumptions: dict, include_opendss: bool = False) -> dict:
    architectures = assumptions["architectures"]
    results = [aggregate_architecture(architecture, assumptions) for architecture in architectures]

    best_efficiency = max(result["average_total_efficiency"] for result in results)
    for result in results:
        result["efficiency_gap_vs_best_pct_points"] = (
            (best_efficiency - result["average_total_efficiency"]) * 100.0
        )

    reference_context = {}
    global_assumptions = assumptions["global"]
    scalable_unit_mw = global_assumptions.get("scalable_unit_tdp_mw")
    racks_per_scalable_unit = global_assumptions.get("racks_per_scalable_unit")
    if scalable_unit_mw and racks_per_scalable_unit:
        reference_context = {
            "equivalent_scalable_units": global_assumptions["base_it_load_mw"] / scalable_unit_mw,
            "equivalent_racks": global_assumptions["base_it_load_mw"] / scalable_unit_mw * racks_per_scalable_unit,
        }

    if include_opendss:
        architecture_map = {architecture["name"]: architecture for architecture in architectures}
        for result in results:
            result["opendss_validation"] = run_opendss_validation_for_architecture(
                architecture=architecture_map[result["name"]],
                result=result,
                assumptions=assumptions,
            )
            result["opendss_harmonics_validation"] = run_opendss_harmonic_validation_for_architecture(
                architecture=architecture_map[result["name"]],
                assumptions=assumptions,
            )

    return {
        "meta": assumptions.get("meta", {}),
        "global": global_assumptions,
        "sources": assumptions.get("sources", {}),
        "reference_context": reference_context,
        "results": results,
    }


def format_money_millions(value_usd: float) -> str:
    return f"${value_usd / 1e6:,.2f}M"


def format_pct(value: float) -> str:
    return f"{value * 100.0:,.2f}%"


def format_table(rows: List[Sequence[str]]) -> str:
    widths = [max(len(str(row[i])) for row in rows) for i in range(len(rows[0]))]
    rendered = []
    for row in rows:
        rendered.append("  ".join(str(cell).ljust(widths[i]) for i, cell in enumerate(row)))
    return "\n".join(rendered)


def markdown_table(headers: Sequence[str], rows: List[Sequence[str]]) -> str:
    lines = [
        "| " + " | ".join(headers) + " |",
        "| " + " | ".join("---" for _ in headers) + " |",
    ]
    lines.extend("| " + " | ".join(str(cell) for cell in row) + " |" for row in rows)
    return "\n".join(lines)


def source_tag(source_ids: Sequence[str]) -> str:
    unique_ids = []
    for source_id in source_ids:
        if source_id and source_id not in unique_ids:
            unique_ids.append(source_id)
    return f"<!-- source_ids: {', '.join(unique_ids)} -->" if unique_ids else "<!-- source_ids: -->"


def format_money_usd(value_usd: float) -> str:
    return f"${value_usd:,.0f}"


def format_gwh(value_mwh: float) -> str:
    return f"{value_mwh / 1000.0:,.2f}"


def find_architecture(assumptions: dict, architecture_name: str) -> dict:
    for architecture in assumptions["architectures"]:
        if architecture["name"] == architecture_name:
            return architecture
    raise ValueError(f"Unknown architecture: {architecture_name}")


def build_source_classification_rows(assumptions: dict) -> List[Sequence[str]]:
    global_assumptions = assumptions["global"]
    dynamic_cases = assumptions.get("dynamic_model", {}).get("cases", [])
    opendss_settings = get_opendss_validation_settings(assumptions)
    harmonic_settings = get_opendss_harmonics_settings(assumptions)
    advanced_architecture = find_architecture(assumptions, "proposed_mvdc_backbone")
    ac_fed_architecture = find_architecture(assumptions, "ac_fed_sst_800vdc")
    advanced_backbone_voltage = next(
        element["voltage_kv"]
        for element in advanced_architecture["elements"]
        if element["type"] == "conductor" and element["name"] == "MVDC backbone"
    )
    ac_fed_subtransmission_voltage = next(
        element["voltage_kv"]
        for element in ac_fed_architecture["elements"]
        if element["type"] == "conductor" and element["name"] == "MV AC campus feeder"
    )
    direct_rows = [
        (
            "Directly source-backed",
            "Reference campus size",
            f"{global_assumptions['base_it_load_mw']:.1f} MW IT",
            ", ".join(global_assumptions.get("base_it_load_mw_source_ids", [])),
        ),
        (
            "Directly source-backed",
            "Electricity price anchor",
            f"${global_assumptions['electricity_price_per_mwh']:.1f}/MWh",
            ", ".join(global_assumptions.get("electricity_price_per_mwh_source_ids", [])),
        ),
        (
            "Directly source-backed",
            "NVIDIA scalable-unit TDP",
            f"{global_assumptions['scalable_unit_tdp_mw']:.1f} MW per scalable unit",
            ", ".join(global_assumptions.get("scalable_unit_tdp_mw_source_ids", [])),
        ),
        (
            "Directly source-backed",
            "Racks per scalable unit",
            str(global_assumptions["racks_per_scalable_unit"]),
            ", ".join(global_assumptions.get("racks_per_scalable_unit_source_ids", [])),
        ),
        (
            "Directly source-backed",
            "Advanced data-center downstream bus",
            "800 VDC pod / facility bus structure in the forward-looking architectures",
            "nvidia_800vdc_blog_2025",
        ),
    ]
    for dynamic_case in dynamic_cases:
        direct_rows.append(
            (
                "Directly source-backed",
                f"Dynamic frequency case: {dynamic_case['name']}",
                f"{float(dynamic_case['frequency_hz']):.1f} Hz",
                ", ".join(dynamic_case.get("source_ids", [])),
            )
        )

    proxy_curve_names = [
        "double_conversion_ups",
        "server_psu_acdc",
        "perimeter_69kvac_to_800vdc",
        "rack_node_dcdc",
        "central_mv_acdc",
        "isolated_dc_pod",
    ]
    proxy_rows = []
    for curve_name in proxy_curve_names:
        curve = assumptions["curves"][curve_name]
        proxy_rows.append(
            (
                "Source-anchored proxy",
                curve_name,
                curve.get("note", ""),
                ", ".join(curve.get("source_ids", [])),
            )
        )

    local_rows = [
        (
            "Local white-paper assumption",
            "MVDC backbone topology",
            "Common MV AC/DC front end feeding an MVDC campus backbone and isolated DC pods.",
            "white_paper_local_2026",
        ),
        (
            "Local scenario assumption",
            "Subtransmission-side voltage",
            f"{advanced_backbone_voltage:.1f} kV for the MVDC backbone and {ac_fed_subtransmission_voltage:.1f} kV for the AC-fed advanced case.",
            "user_specified_69kv_scenario_2026",
        ),
        (
            "Local white-paper assumption",
            "Native buffer anchor locations",
            "Architecture-specific support points selected to reflect the intended electrical domain.",
            "white_paper_local_2026",
        ),
        (
            "Local scenario assumption",
            "OpenDSS AC-side surrogate boundary",
            (
                f"Uses the first modeled AC feeder when present; otherwise a "
                f"{float(opendss_settings['centralized_front_end_ac_stub_length_m']):.1f} m "
                f"centralized-front-end AC stub with X/R proxy "
                f"{float(opendss_settings['line_x_to_r_ratio']):.1f}."
            ),
            ", ".join(opendss_settings.get("source_ids", [])),
        ),
        (
            "Local harmonic-scan assumption",
            "OpenDSS harmonic probe",
            (
                f"Equal-magnitude PCC current scan at harmonic orders "
                f"{', '.join(str(order) for order in harmonic_settings['harmonic_orders'])} "
                f"using {float(harmonic_settings['probe_current_amps_per_phase']):.1f} A per phase."
            ),
            ", ".join(harmonic_settings.get("source_ids", [])),
        ),
    ]

    missing_rows = [
        (
            "Project-specific gap",
            "MV AC/DC rectifier efficiency-vs-load curves",
            "Need measured or vendor-provided curves for the exact front-end design.",
            "",
        ),
        (
            "Project-specific gap",
            "Isolated DC pod / DC transformer efficiency curves",
            "Need measured or vendor-provided partial-load data for the chosen topology.",
            "",
        ),
        (
            "Project-specific gap",
            "GPU-cluster waveform amplitudes",
            "Dynamic amplitudes in the model are sensitivity cases, not universal measured constants.",
            "",
        ),
        (
            "Project-specific gap",
            "MVDC protection and grounding behavior",
            "Need equipment-specific fault-clearing, grounding, and insulation data.",
            "",
        ),
        (
            "Project-specific gap",
            "Utility PCC strength and compliance limits",
            "Need interconnection-specific short-circuit strength, THD limits, and study criteria.",
            "",
        ),
        (
            "Project-specific gap",
            "Utility-grade 69 kV line and source model",
            "Need site-specific R/X, zero-sequence, and source Thevenin data to replace the current surrogate feeder.",
            "",
        ),
    ]

    return direct_rows + proxy_rows + local_rows + missing_rows


def build_source_usage_map() -> Dict[str, str]:
    return {
        "iea_2025_energy_ai": "Campus size anchor and AI/data-center demand context.",
        "eia_electricity_monthly_2026_01": "U.S. industrial electricity price anchor for annual loss-cost conversion.",
        "nvidia_dgx_superpod_gb200_2025": "Scalable-unit and rack-count context for the 100 MW reference campus.",
        "nvidia_800vdc_blog_2025": "800 VDC / 13.8 kV architecture direction and conductor-voltage context.",
        "opendss_epri_2026": "OpenDSS method basis for RMS/quasi-static feeder studies.",
        "opendss_quasi_static_local_2026": "Local AC-boundary surrogate choices used for the OpenDSS validation setup.",
        "opendss_harmonic_scan_local_2026": "Local OpenDSS harmonic-sensitivity scan setup and standardized probe-current assumptions.",
        "pnnl_38817_2026": "Dynamic-load study framing and the 0.1-5 Hz versus 5-60 Hz modeling bands.",
        "arxiv_2508_14318": "AI-training load fluctuation motivation and need for dynamic-load modeling.",
        "segan_2025_14_8hz": "Measured 14.8 Hz data-center oscillation reference case.",
        "schneider_galaxy_vx_2025": "Large UPS normal-operation efficiency anchor.",
        "ocp_delta_orv3": "Modern AC-DC conversion efficiency anchor for rack/power-shelf class hardware.",
        "rothmund_2019_dc_transformer": "High-efficiency DC transformer anchor for isolated DC stages.",
        "white_paper_local_2026": "Local MVDC backbone architecture assumptions and intended functional allocation.",
        "user_specified_69kv_scenario_2026": "User-requested 69 kV subtransmission scenario used for the campus-side advanced-case voltage assumptions.",
    }


def build_memo(report: dict, assumptions: dict, assumptions_path: Path) -> str:
    source_usage_map = build_source_usage_map()
    best_result = max(report["results"], key=lambda result: result["full_load_total_efficiency"])
    worst_result = min(report["results"], key=lambda result: result["full_load_total_efficiency"])
    reference_context = report.get("reference_context", {})
    ac_fed_architecture = find_architecture(assumptions, "ac_fed_sst_800vdc")
    proposed_architecture = find_architecture(assumptions, "proposed_mvdc_backbone")
    ac_fed_subtransmission_voltage = next(
        element["voltage_kv"]
        for element in ac_fed_architecture["elements"]
        if element["type"] == "conductor" and element["name"] == "MV AC campus feeder"
    )
    mvdc_backbone_voltage = next(
        element["voltage_kv"]
        for element in proposed_architecture["elements"]
        if element["type"] == "conductor" and element["name"] == "MVDC backbone"
    )

    steady_state_headers = [
        "Architecture",
        "Full-load efficiency",
        "Annual loss (GWh)",
        "Annual loss cost (USD)",
        "AC harmonic-injection points",
        "Major conversion stages",
    ]
    steady_state_rows = []
    compared_architecture_rows = []
    dynamic_rows = []
    dynamic_case_basis_rows = []
    opendss_summary_rows = []
    harmonic_summary_rows = []

    for result in report["results"]:
        architecture = find_architecture(assumptions, result["name"])
        metrics = result["innovation_metrics"]
        steady_state_rows.append(
            (
                result["display_name"],
                format_pct(result["full_load_total_efficiency"]),
                format_gwh(result["annual_loss_mwh"]),
                format_money_usd(result["annual_loss_cost_usd"]),
                str(metrics["ac_harmonic_injection_points"]),
                str(metrics["major_conversion_stages"]),
            )
        )
        compared_architecture_rows.append(
            (
                result["display_name"],
                architecture.get("notes", ""),
                architecture.get("native_buffer_anchor", ""),
            )
        )
        for dynamic_case in result["dynamic_cases"]:
            dynamic_rows.append(
                (
                    result["display_name"],
                    dynamic_case["case_name"],
                    f"{dynamic_case['frequency_hz']:.1f}",
                    f"{dynamic_case['it_amplitude_fraction'] * 100.0:.1f}%",
                    f"{dynamic_case['raw_pcc_peak_mw']:.2f}",
                    f"{dynamic_case['raw_pcc_peak_fraction_of_base_input'] * 100.0:.2f}%",
                    f"{dynamic_case['native_buffer_peak_mw']:.2f}",
                    f"{dynamic_case['native_buffer_energy_kwh']:.2f}",
                )
            )

        opendss_validation = result.get("opendss_validation")
        if opendss_validation:
            strongest_per_case: Dict[str, dict] = {}
            for dynamic_case in opendss_validation["dynamic_cases"]:
                current = strongest_per_case.get(dynamic_case["case_name"])
                if current is None or dynamic_case["it_amplitude_fraction"] > current["it_amplitude_fraction"]:
                    strongest_per_case[dynamic_case["case_name"]] = dynamic_case
            for case_name in sorted(strongest_per_case):
                dynamic_case = strongest_per_case[case_name]
                opendss_summary_rows.append(
                    (
                        result["display_name"],
                        case_name,
                        f"{dynamic_case['frequency_hz']:.1f}",
                        f"{dynamic_case['it_amplitude_fraction'] * 100.0:.1f}%",
                        f"{dynamic_case['source_power_peak_mw']:.2f}",
                        f"{dynamic_case['max_pcc_voltage_swing_from_base_pct']:.2f}%",
                        f"{dynamic_case['peak_feeder_loss_mw']:.3f}",
                        f"{dynamic_case['peak_feeder_current_a']:.0f}",
                    )
                )

        harmonic_validation = result.get("opendss_harmonics_validation")
        if harmonic_validation:
            harmonic_summary_rows.append(
                (
                    result["display_name"],
                    f"{harmonic_validation['probe_thdv_percent']:.2f}%",
                    str(harmonic_validation["worst_single_harmonic_order"]),
                    f"{harmonic_validation['worst_single_harmonic_percent']:.2f}%",
                    f"{harmonic_validation['max_transfer_impedance_ohm_ln']:.2f}",
                )
            )

    seen_cases = set()
    for dynamic_case in report["results"][0]["dynamic_cases"]:
        case_key = dynamic_case["case_name"]
        if case_key in seen_cases:
            continue
        seen_cases.add(case_key)
        dynamic_case_basis_rows.append(
            (
                dynamic_case["case_name"],
                f"{dynamic_case['frequency_hz']:.1f} Hz",
                dynamic_case["frequency_basis"],
            )
        )

    classification_rows = build_source_classification_rows(assumptions)

    appendix_rows = []
    for source_id, source in report["sources"].items():
        appendix_rows.append(
            (
                source_id,
                source["title"],
                source["date"],
                source["type"],
                source["url"],
                source_usage_map.get(source_id, "Used as a model input or context anchor."),
            )
        )

    memo_lines = [
        "# Standalone Technical Results Memo for the DC Backbone Model",
        "",
        source_tag(["white_paper_local_2026", "iea_2025_energy_ai", "nvidia_dgx_superpod_gb200_2025", "nvidia_800vdc_blog_2025", "user_specified_69kv_scenario_2026"]),
        "## 1. Title and model status",
        "",
        f"This memo summarizes the current source-backed model for `/Users/zhengjieyang/Documents/DC2` using `{assumptions_path.name}` as the assumptions file.",
        "",
        f"Model status: `{report['meta'].get('status', 'unknown')}`.",
        "",
        f"Model caution: {report['meta'].get('warning', '')}",
        "",
        f"In the current scenario, the two forward-looking architectures use an NVIDIA-style `800 VDC` downstream structure. "
        f"The campus-side subtransmission assumption is set to `{ac_fed_subtransmission_voltage:.1f} kV AC` for the AC-fed advanced case and "
        f"`{mvdc_backbone_voltage:.1f} kV DC` for the proposed MVDC backbone. That `69 kV` assumption is a local scenario choice, not a direct NVIDIA-published voltage value.",
        "",
        "The memo is intended for coauthors. It is reader-facing and does not require direct use of the terminal, raw JSON, or the Python source.",
        "",
        source_tag(["iea_2025_energy_ai", "eia_electricity_monthly_2026_01", "nvidia_dgx_superpod_gb200_2025", "pnnl_38817_2026", "segan_2025_14_8hz"]),
        "## 2. Executive findings",
        "",
        f"The reference campus is `{report['global']['base_it_load_mw']:.1f} MW` of delivered IT load. "
        f"That corresponds to about `{reference_context.get('equivalent_scalable_units', 0.0):.1f}` NVIDIA scalable units "
        f"and about `{reference_context.get('equivalent_racks', 0.0):.0f}` racks.",
        "",
        f"The proposed MVDC backbone has the strongest steady-state result in the current model at "
        f"`{format_pct(best_result['full_load_total_efficiency'])}` full-load efficiency, versus "
        f"`{format_pct(worst_result['full_load_total_efficiency'])}` for the least-efficient baseline.",
        "",
        f"At the current U.S. industrial electricity-price anchor of "
        f"`${report['global']['electricity_price_per_mwh']:.1f}/MWh`, the modeled annual electrical-loss cost spans from "
        f"`{format_money_usd(worst_result['annual_loss_cost_usd'])}` in the traditional AC case to "
        f"`{format_money_usd(best_result['annual_loss_cost_usd'])}` in the proposed MVDC case.",
        "",
        "The model also treats AI factories as dynamic loads. It evaluates a representative `1.0 Hz` reference case inside the PNNL `0.1-5 Hz` study band and a measured `14.8 Hz` case from a data-center oscillation paper. These cases show that dynamic behavior must be modeled explicitly, not inferred from annual energy numbers alone.",
        "",
        "Dynamic-amplitude values in this memo are sensitivity cases. They are not presented as universal measured constants for all AI workloads.",
        "",
        source_tag(["white_paper_local_2026", "nvidia_800vdc_blog_2025", "user_specified_69kv_scenario_2026"]),
        "## 3. Compared architectures",
        "",
        markdown_table(
            ["Architecture", "Description", "Native buffer anchor"],
            compared_architecture_rows,
        ),
        "",
        source_tag(["iea_2025_energy_ai", "eia_electricity_monthly_2026_01", "nvidia_dgx_superpod_gb200_2025", "schneider_galaxy_vx_2025", "ocp_delta_orv3", "rothmund_2019_dc_transformer", "pnnl_38817_2026", "segan_2025_14_8hz", "white_paper_local_2026"]),
        "## 4. Source-backed input anchors",
        "",
        "The current assumptions mix directly sourced values, source-anchored proxies, local white-paper assumptions, and project-specific gaps that still require measured data.",
        "",
        markdown_table(
            ["Classification", "Input", "Current basis", "Source IDs"],
            classification_rows,
        ),
        "",
        source_tag(["iea_2025_energy_ai", "eia_electricity_monthly_2026_01", "schneider_galaxy_vx_2025", "ocp_delta_orv3", "rothmund_2019_dc_transformer", "white_paper_local_2026"]),
        "## 5. Steady-state results",
        "",
        markdown_table(steady_state_headers, steady_state_rows),
        "",
        "Interpretation:",
        "",
        f"- The current model supports the thesis that moving the AC/DC boundary upstream reduces cumulative conversion loss.",
        f"- The proposed MVDC backbone also has the fewest modeled AC harmonic-injection points and the fewest major conversion stages.",
        f"- These steady-state results are only as strong as the converter-curve and conductor assumptions used to produce them.",
        "",
        source_tag(["pnnl_38817_2026", "arxiv_2508_14318", "segan_2025_14_8hz"]),
        "## 6. Dynamic AI-load results",
        "",
        "AI factories are modeled here as dynamic electrical loads because public sources now show that large AI-training sites can exhibit sustained periodic fluctuations and can interact with grid-relevant oscillatory modes.",
        "",
        markdown_table(
            ["Case", "Frequency", "Basis"],
            dynamic_case_basis_rows,
        ),
        "",
        markdown_table(
            [
                "Architecture",
                "Case",
                "Oscillation frequency (Hz)",
                "IT amplitude",
                "Raw PCC peak (MW)",
                "Raw PCC peak (% of base input)",
                "Native buffer (MW)",
                "Native buffer (kWh)",
            ],
            dynamic_rows,
        ),
        "",
    ]

    if opendss_summary_rows:
        memo_lines.extend(
            [
                source_tag(["opendss_epri_2026", "opendss_quasi_static_local_2026", "white_paper_local_2026"]),
                "OpenDSS AC-side validation:",
                "",
                "A complementary OpenDSS quasi-static study was run for the AC source, the 69 kV feeder or substation stub, and the equivalent AI-factory demand seen at that AC boundary. This validation does not simulate the internal MVDC or 800 VDC network in EMT detail; it tests the feeder-side voltage, current, and loss consequences of each architecture's upstream demand envelope.",
                "",
                markdown_table(
                    [
                        "Architecture",
                        "Case",
                        "Oscillation frequency (Hz)",
                        "IT amplitude",
                        "OpenDSS source peak (MW)",
                        "Max PCC voltage swing from base",
                        "Peak feeder loss (MW)",
                        "Peak line current (A)",
                    ],
                    opendss_summary_rows,
                ),
                "",
            ]
        )

    if harmonic_summary_rows:
        memo_lines.extend(
            [
                source_tag(["opendss_epri_2026", "opendss_harmonic_scan_local_2026", "white_paper_local_2026"]),
                "OpenDSS harmonic-sensitivity scan:",
                "",
                "A standardized harmonic-current probe is injected at the PCC for each scenario using the same harmonic orders and current magnitude. The resulting PCC harmonic voltage is used as a structural sensitivity metric. Lower distortion in this scan means the AC boundary is less sensitive to harmonic current injection. This is useful for comparing scenarios, but it is not a substitute for a vendor-specific converter spectrum study or an IEEE 519 compliance assessment.",
                "",
                markdown_table(
                    [
                        "Architecture",
                        "Probe THDv (%)",
                        "Worst harmonic order",
                        "Worst single harmonic (%)",
                        "Max transfer impedance (ohm L-N)",
                    ],
                    harmonic_summary_rows,
                ),
                "",
            ]
        )

    memo_lines.extend(
        [
            "Limitations:",
            "",
            "- The `1.0 Hz` case is a modeling reference point inside the PNNL low-frequency study band. It is not claimed as a measured universal AI-workload frequency.",
            "- The `14.8 Hz` case is a measured data-center oscillation reference, but the model does not claim that all AI factories oscillate at this exact frequency.",
            "- Dynamic amplitudes remain sensitivity cases because publicly available literature does not yet provide a universal MW-swing percentage for all AI workloads.",
            "- The dynamic module estimates raw PCC power ripple and native-buffer requirements. It does not yet model control-loop dynamics, impedance interactions, or EMT-grade converter behavior.",
            "- The OpenDSS layer now includes both an AC-boundary RMS validation and a standardized harmonic-sensitivity scan. It still does not replace a full converter-spectrum study, an IEEE 519 compliance study, or an EMT simulation of MVDC protection.",
            "",
            source_tag(["white_paper_local_2026", "pnnl_38817_2026", "iea_2025_energy_ai"]),
            "## 7. What is proven vs not yet proven",
            "",
            "What the current model supports:",
            "",
            "- The proposed MVDC backbone has the best steady-state electrical-path efficiency in the current source-backed model.",
            "- The proposed MVDC backbone centralizes AC-side interaction and reduces modeled AC harmonic-injection points.",
            "- AI-factory power architecture should be evaluated under dynamic-load conditions, not only annual energy-loss accounting.",
            "- The OpenDSS AC-side validation independently confirms lower feeder current, feeder loss, and PCC-voltage swing when the AC boundary is pushed upstream to the centralized front end.",
            "",
            "What the current model does not yet prove externally:",
            "",
            "- Exact MVDC protection, fault-clearing, and grounding behavior.",
            "- Exact harmonic and power-factor performance at the PCC under vendor-specific converter spectra and utility interconnection conditions.",
            "- Exact dynamic attenuation benefits of one architecture over another under real converter-control designs.",
            "- Vendor-accurate partial-load efficiency for the actual MV rectifier and isolated DC pod hardware that would be deployed.",
            "",
            source_tag(["pnnl_38817_2026", "segan_2025_14_8hz", "white_paper_local_2026"]),
            "## 8. Next data needed",
            "",
            "- Measured or vendor-provided efficiency-versus-load curves for the centralized MV AC/DC front end.",
            "- Measured or vendor-provided efficiency-versus-load curves for the isolated DC pod / DC transformer stage.",
            "- Project waveform data for GPU-cluster power swings, including amplitude, spectrum, duty cycle, and workload dependence.",
            "- Utility-specific PCC data: short-circuit strength, harmonic limits, flicker requirements, and study expectations.",
            "- Protection, grounding, insulation, and fault-isolation data for the targeted MVDC backbone implementation.",
            "- BESS and buffer control bandwidth, thermal limits, and siting assumptions for campus-specific dynamic mitigation studies.",
            "",
            source_tag(list(report["sources"].keys())),
            "## 9. Reference appendix",
            "",
            markdown_table(
                ["Source ID", "Title", "Date", "Tier", "URL", "How it is used in the model"],
                appendix_rows,
            ),
            "",
        ]
    )
    return "\n".join(memo_lines)


def print_summary(report: dict) -> None:
    reference_context = report.get("reference_context", {})
    if reference_context:
        print(
            "Reference campus: "
            f"{report['global']['base_it_load_mw']:.1f} MW IT "
            f"= {reference_context['equivalent_scalable_units']:.1f} NVIDIA scalable units "
            f"= {reference_context['equivalent_racks']:.0f} racks"
        )
        print()

    rows: List[Sequence[str]] = [
        (
            "Architecture",
            "Avg Eff.",
            "Full-Load Eff.",
            "Full-Load Input MW",
            "Annual Loss GWh",
            "Annual Loss Cost",
            "AC Interfaces",
            "Major Conv.",
        )
    ]

    for result in report["results"]:
        metrics = result["innovation_metrics"]
        rows.append(
            (
                result["display_name"],
                format_pct(result["average_total_efficiency"]),
                format_pct(result["full_load_total_efficiency"]),
                f"{result['full_load_input_mw']:,.2f}",
                f"{result['annual_loss_mwh'] / 1000.0:,.2f}",
                format_money_millions(result["annual_loss_cost_usd"]),
                str(metrics["ac_harmonic_injection_points"]),
                str(metrics["major_conversion_stages"]),
            )
        )

    print(format_table(rows))

    if any(result["dynamic_cases"] for result in report["results"]):
        print()
        print("Dynamic AI-load cases")
        print("---------------------")
        dynamic_rows: List[Sequence[str]] = [
            (
                "Architecture",
                "Case",
                "Freq (Hz)",
                "IT Amp",
                "Raw PCC Peak MW",
                "Raw PCC Peak %",
                "Native Buffer MW",
                "Native Buffer kWh",
            )
        ]

        for result in report["results"]:
            for dynamic_case in result["dynamic_cases"]:
                dynamic_rows.append(
                    (
                        result["display_name"],
                        dynamic_case["case_name"],
                        f"{dynamic_case['frequency_hz']:.1f}",
                        f"{dynamic_case['it_amplitude_fraction'] * 100.0:.1f}%",
                        f"{dynamic_case['raw_pcc_peak_mw']:.2f}",
                        f"{dynamic_case['raw_pcc_peak_fraction_of_base_input'] * 100.0:.2f}%",
                        f"{dynamic_case['native_buffer_peak_mw']:.2f}",
                        f"{dynamic_case['native_buffer_energy_kwh']:.2f}",
                    )
                )

        print(format_table(dynamic_rows))

    if any(result.get("opendss_validation") for result in report["results"]):
        print()
        print("OpenDSS AC-side validation")
        print("--------------------------")
        base_rows: List[Sequence[str]] = [
            (
                "Architecture",
                "AC Boundary",
                "Base Source MW",
                "Base PCC Min Vpu",
                "Base Feeder Loss MW",
                "Peak Current A",
            )
        ]
        stress_rows: List[Sequence[str]] = [
            (
                "Architecture",
                "Case",
                "IT Amp",
                "OpenDSS Source Peak MW",
                "Max PCC Swing %",
                "Peak Feeder Loss MW",
            )
        ]

        for result in report["results"]:
            validation = result.get("opendss_validation")
            if not validation:
                continue
            base = validation["base_snapshot"]
            boundary = validation["ac_boundary"]
            base_rows.append(
                (
                    result["display_name"],
                    boundary["name"],
                    f"{base['source_power_mw']:.2f}",
                    f"{base['pcc_voltage_min_pu']:.4f}",
                    f"{base['feeder_loss_mw']:.3f}",
                    f"{base['peak_line_current_a']:.0f}",
                )
            )

            strongest_per_case: Dict[str, dict] = {}
            for dynamic_case in validation["dynamic_cases"]:
                current = strongest_per_case.get(dynamic_case["case_name"])
                if current is None or dynamic_case["it_amplitude_fraction"] > current["it_amplitude_fraction"]:
                    strongest_per_case[dynamic_case["case_name"]] = dynamic_case

            for case_name in sorted(strongest_per_case):
                dynamic_case = strongest_per_case[case_name]
                stress_rows.append(
                    (
                        result["display_name"],
                        case_name,
                        f"{dynamic_case['it_amplitude_fraction'] * 100.0:.1f}%",
                        f"{dynamic_case['source_power_peak_mw']:.2f}",
                        f"{dynamic_case['max_pcc_voltage_swing_from_base_pct']:.2f}%",
                        f"{dynamic_case['peak_feeder_loss_mw']:.3f}",
                    )
                )

        print(format_table(base_rows))
        print()
        print(format_table(stress_rows))

    if any(result.get("opendss_harmonics_validation") for result in report["results"]):
        print()
        print("OpenDSS harmonic sensitivity")
        print("----------------------------")
        harmonic_rows: List[Sequence[str]] = [
            (
                "Architecture",
                "Probe THDv %",
                "Worst Harmonic",
                "Worst Single Harmonic %",
                "Max Transfer Z (ohm L-N)",
            )
        ]
        for result in report["results"]:
            validation = result.get("opendss_harmonics_validation")
            if not validation:
                continue
            harmonic_rows.append(
                (
                    result["display_name"],
                    f"{validation['probe_thdv_percent']:.2f}%",
                    str(validation["worst_single_harmonic_order"]),
                    f"{validation['worst_single_harmonic_percent']:.2f}%",
                    f"{validation['max_transfer_impedance_ohm_ln']:.2f}",
                )
            )
        print(format_table(harmonic_rows))


def print_details(report: dict) -> None:
    for result in report["results"]:
        print()
        print(result["display_name"])
        print("-" * len(result["display_name"]))
        print(f"Average efficiency: {format_pct(result['average_total_efficiency'])}")
        print(f"Full-load efficiency: {format_pct(result['full_load_total_efficiency'])}")
        print(f"Annual loss cost: {format_money_millions(result['annual_loss_cost_usd'])}")
        if result.get("native_buffer_anchor"):
            print(f"Native buffer anchor: {result['native_buffer_anchor']}")
        print("Innovation metrics:")
        for key, value in result["innovation_metrics"].items():
            print(f"  - {key}: {value}")

        print("Full-load breakdown:")
        for element in result["full_load_breakdown"]:
            if element["element_type"] == "stage":
                print(
                    "  - "
                    f"{element['name']}: "
                    f"load_ratio={element['load_ratio']:.3f}, "
                    f"eff={format_pct(element['efficiency'])}, "
                    f"loss={element['loss_mw']:.3f} MW"
                )
            else:
                print(
                    "  - "
                    f"{element['name']}: "
                    f"loss={element['loss_mw']:.3f} MW"
                )

        if result["dynamic_cases"]:
            print("Dynamic cases:")
            for dynamic_case in result["dynamic_cases"]:
                print(
                    "  - "
                    f"{dynamic_case['case_name']} @ {dynamic_case['frequency_hz']:.1f} Hz, "
                    f"IT amplitude={dynamic_case['it_amplitude_fraction'] * 100.0:.1f}%, "
                    f"raw PCC peak={dynamic_case['raw_pcc_peak_mw']:.2f} MW "
                    f"({dynamic_case['raw_pcc_peak_fraction_of_base_input'] * 100.0:.2f}%), "
                    f"native buffer={dynamic_case['native_buffer_peak_mw']:.2f} MW / "
                    f"{dynamic_case['native_buffer_energy_kwh']:.2f} kWh, "
                    f"native path eff={format_pct(dynamic_case['native_buffer_marginal_efficiency'])}"
                )

        harmonic_validation = result.get("opendss_harmonics_validation")
        if harmonic_validation:
            print("OpenDSS harmonic sensitivity:")
            print(
                "  - "
                f"probe THDv={harmonic_validation['probe_thdv_percent']:.2f}%, "
                f"worst harmonic={harmonic_validation['worst_single_harmonic_order']} "
                f"({harmonic_validation['worst_single_harmonic_percent']:.2f}%), "
                f"max transfer Z={harmonic_validation['max_transfer_impedance_ohm_ln']:.2f} ohm L-N"
            )
            for harmonic in harmonic_validation["harmonics"]:
                print(
                    "    - "
                    f"h={harmonic['order']}: "
                    f"avg PCC={harmonic['avg_voltage_pct_of_fundamental']:.2f}%, "
                    f"max PCC={harmonic['max_voltage_pct_of_fundamental']:.2f}%, "
                    f"transfer Z={harmonic['transfer_impedance_ohm_ln']:.2f} ohm L-N"
                )


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Compare AI-factory power architectures.")
    parser.add_argument(
        "--assumptions",
        type=Path,
        default=Path(__file__).with_name("scientific_assumptions_v1.json"),
        help="Path to the assumptions JSON file.",
    )
    parser.add_argument(
        "--it-load-mw",
        type=float,
        help="Override the base delivered IT load in MW.",
    )
    parser.add_argument(
        "--energy-price-per-mwh",
        type=float,
        help="Override the energy price in USD/MWh.",
    )
    parser.add_argument(
        "--details",
        action="store_true",
        help="Print stage-by-stage full-load breakdown.",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Print the full report as JSON.",
    )
    parser.add_argument(
        "--save-json",
        type=Path,
        help="Write the full report to a JSON file.",
    )
    parser.add_argument(
        "--write-memo",
        type=Path,
        help="Write a standalone Markdown memo for coauthors.",
    )
    parser.add_argument(
        "--run-opendss",
        action="store_true",
        help="Run the optional OpenDSS AC-side validation study and include it in the report output.",
    )
    return parser.parse_args()


def apply_overrides(assumptions: dict, args: argparse.Namespace) -> dict:
    assumptions = deep_copy_jsonable(assumptions)

    if args.it_load_mw is not None:
        assumptions["global"]["base_it_load_mw"] = args.it_load_mw

    if args.energy_price_per_mwh is not None:
        assumptions["global"]["electricity_price_per_mwh"] = args.energy_price_per_mwh

    return assumptions


def main() -> None:
    args = parse_args()
    assumptions = load_json(args.assumptions)
    assumptions = apply_overrides(assumptions, args)
    report = run_model(assumptions, include_opendss=args.run_opendss)

    if args.json:
        print(json.dumps(report, indent=2))
    else:
        print_summary(report)
        if args.details:
            print_details(report)

    if args.save_json:
        args.save_json.write_text(json.dumps(report, indent=2), encoding="utf-8")

    if args.write_memo:
        args.write_memo.write_text(build_memo(report, assumptions, args.assumptions), encoding="utf-8")


if __name__ == "__main__":
    main()
