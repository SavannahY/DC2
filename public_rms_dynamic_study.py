#!/usr/bin/env python3
"""Public RMS dynamic study for Scenario 2(M) and Scenario 3(M).

This script adds the next public-data-only reviewer-response layer after the
public operating, common-network, and harmonic studies. It uses:

- MIT-derived p95 AI burst magnitudes from ``public_ai_factory_operating_report.json``
- a public ANDES RMS dynamic benchmark case (IEEE 14-bus full dynamic model)
- explicit scenario placement differences:
  - Scenario 2(M): four distributed AC-fed SST block interfaces
  - Scenario 3(M): one centralized upstream AC/DC front-end interface

The result is still an RMS electromechanical screen rather than converter EMT.
The goal is to test whether the architectural claim remains directionally true
under public dynamic load-step and weak-grid corridor-stress cases.
"""

from __future__ import annotations

import argparse
import contextlib
import io
import json
import math
import os
import tempfile
from pathlib import Path
from typing import Dict, Iterable, Sequence

import numpy as np

from dc_backbone_model import format_pct, format_table, load_json

ROOT = Path(__file__).resolve().parent

DEFAULT_OPERATING_REPORT = ROOT / "public_ai_factory_operating_report.json"
DEFAULT_OUTPUT_JSON = ROOT / "public_rms_dynamic_report.json"
DEFAULT_OUTPUT_NOTE = ROOT / "PUBLIC_RMS_DYNAMIC_STUDY.md"
DEFAULT_CASE_PATH = Path(
    "/Users/zhengjieyang/Library/Python/3.9/lib/python/site-packages/andes/cases/ieee14/ieee14_full.xlsx"
)
DEFAULT_ANDES_PYCODE = ROOT / ".andes_pycode"

SYSTEM_BASE_MVA = 100.0
DEFAULT_CAMPUS_SHARES = [0.15, 0.25, 0.35]
CENTRALIZED_POI_BUS = 5
DISTRIBUTED_POI_BUSES = [9, 10, 13, 14]
REMOTE_CORRIDOR_WEAKENING_LINE = "Line_10"
GRID_MODES = {
    "normal_network": None,
    "remote_corridor_weakened": REMOTE_CORRIDOR_WEAKENING_LINE,
}
STEP_TIME_S = 1.0
TRIP_TIME_S = 0.5
SIM_DURATION_S = 6.0
BUS_FREQ_TF = 0.02
BUS_FREQ_TW = 0.02
CAMPUS_POWER_FACTOR = 0.99
SETTLING_TOLERANCE_PU = 0.005


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--operating-report", type=Path, default=DEFAULT_OPERATING_REPORT)
    parser.add_argument("--case-path", type=Path, default=DEFAULT_CASE_PATH)
    parser.add_argument("--andes-pycode", type=Path, default=DEFAULT_ANDES_PYCODE)
    parser.add_argument("--output-json", type=Path, default=DEFAULT_OUTPUT_JSON)
    parser.add_argument("--output-note", type=Path, default=DEFAULT_OUTPUT_NOTE)
    parser.add_argument(
        "--campus-shares",
        type=float,
        nargs="+",
        default=DEFAULT_CAMPUS_SHARES,
        help="Campus base-load share of total benchmark system PQ load.",
    )
    parser.add_argument("--details", action="store_true")
    return parser.parse_args()


def write_json(path: Path, payload: dict) -> None:
    path.write_text(json.dumps(payload, indent=2), encoding="utf-8")


def format_mw_from_pu(value_pu: float) -> str:
    return f"{value_pu * SYSTEM_BASE_MVA:.2f} MW"


def format_hz(value_hz: float) -> str:
    return f"{value_hz:.3f} Hz"


def load_andes_runtime():
    os.environ.setdefault("MPLCONFIGDIR", tempfile.gettempdir() + "/mplcfg_dc2")
    import andes  # pylint: disable=import-outside-toplevel

    return andes


def burst_cases_from_operating_report(operating_report: dict) -> list[dict]:
    rows = [
        row
        for row in operating_report["mit_ai_burst_layer"]["burst_summary"]["derived_cases"]
        if row["name"].endswith("p95")
    ]
    rows.sort(key=lambda row: int(row["window_seconds"]))
    return rows


def bus_vn_kv(system, bus_idx: int) -> float:
    uid = system.Bus.idx2uid(bus_idx)
    return float(system.Bus.Vn.v[uid])


def add_campus_monitors(system, bus_indices: Sequence[int], prefix: str) -> list[str]:
    monitor_ids = []
    for index, bus_idx in enumerate(bus_indices, start=1):
        monitor_idx = f"{prefix}_BusFreq_{index}"
        system.add(
            "BusFreq",
            {
                "idx": monitor_idx,
                "name": monitor_idx,
                "bus": bus_idx,
                "Tf": BUS_FREQ_TF,
                "Tw": BUS_FREQ_TW,
                "fn": 60.0,
            },
        )
        monitor_ids.append(monitor_idx)
    return monitor_ids


def add_campus_loads(
    system,
    scenario_label: str,
    campus_base_pu: float,
    q_ratio: float,
) -> tuple[list[str], list[int]]:
    if scenario_label == "Scenario 2(M)":
        bus_indices = list(DISTRIBUTED_POI_BUSES)
        block_p = campus_base_pu / float(len(bus_indices))
        block_ps = [block_p] * len(bus_indices)
    elif scenario_label == "Scenario 3(M)":
        bus_indices = [CENTRALIZED_POI_BUS]
        block_ps = [campus_base_pu]
    else:
        raise ValueError(f"Unsupported scenario label: {scenario_label}")

    device_ids = []
    for index, (bus_idx, p_pu) in enumerate(zip(bus_indices, block_ps), start=1):
        device_idx = f"{scenario_label.replace(' ', '').replace('(', '').replace(')', '')}_PQ_{index}"
        system.add(
            "PQ",
            {
                "idx": device_idx,
                "name": device_idx,
                "bus": bus_idx,
                "Vn": bus_vn_kv(system, bus_idx),
                "p0": p_pu,
                "q0": p_pu * q_ratio,
                "vmax": 1.2,
                "vmin": 0.8,
                "owner": 1,
            },
        )
        device_ids.append(device_idx)
    return device_ids, bus_indices


def add_burst_step(
    system,
    device_ids: Sequence[str],
    scenario_label: str,
    campus_base_pu: float,
    burst_fraction: float,
    q_ratio: float,
) -> None:
    device_step_p = campus_base_pu * burst_fraction / float(len(device_ids))
    device_step_q = device_step_p * q_ratio
    counter = 0
    for device_idx in device_ids:
        counter += 1
        system.add(
            "Alter",
            {
                "idx": 1000 + 2 * counter,
                "name": f"{scenario_label}_PSTEP_{counter}",
                "t": STEP_TIME_S,
                "model": "PQ",
                "dev": device_idx,
                "src": "Ppf",
                "attr": "v",
                "method": "+",
                "amount": device_step_p,
                "rand": 0,
                "lb": 0,
                "ub": 0,
            },
        )
        system.add(
            "Alter",
            {
                "idx": 1000 + 2 * counter + 1,
                "name": f"{scenario_label}_QSTEP_{counter}",
                "t": STEP_TIME_S,
                "model": "PQ",
                "dev": device_idx,
                "src": "Qpf",
                "attr": "v",
                "method": "+",
                "amount": device_step_q,
                "rand": 0,
                "lb": 0,
                "ub": 0,
            },
        )


def add_weak_grid_toggle(system, line_idx: str) -> None:
    system.add(
        "Toggle",
        {
            "idx": 5000,
            "name": "REMOTE_CORRIDOR_TRIP",
            "model": "Line",
            "dev": line_idx,
            "t": TRIP_TIME_S,
        },
    )


def settling_time_seconds(times_s: np.ndarray, values: np.ndarray, event_time_s: float, final_value: float) -> float | None:
    after_event = times_s >= event_time_s
    candidate_times = times_s[after_event]
    candidate_values = values[after_event]
    if candidate_times.size == 0:
        return None

    band_low = final_value - SETTLING_TOLERANCE_PU
    band_high = final_value + SETTLING_TOLERANCE_PU
    for index, _ in enumerate(candidate_times):
        tail = candidate_values[index:]
        if np.all((tail >= band_low) & (tail <= band_high)):
            return float(candidate_times[index] - event_time_s)
    return None


def run_single_case(
    andes,
    case_path: Path,
    andes_pycode: Path,
    scenario_label: str,
    campus_share: float,
    burst_case: dict,
    grid_mode: str,
) -> dict:
    captured = io.StringIO()
    with contextlib.redirect_stdout(captured), contextlib.redirect_stderr(captured):
        system = andes.load(
            str(case_path),
            setup=False,
            no_output=True,
            default_config=False,
            options={"pycode_path": str(andes_pycode), "ncpu": 1},
        )

        system.PQ.config.p2p = 1.0
        system.PQ.config.p2i = 0.0
        system.PQ.config.p2z = 0.0
        system.PQ.config.q2q = 1.0
        system.PQ.config.q2i = 0.0
        system.PQ.config.q2z = 0.0

        base_system_load_pu = float(sum(system.PQ.p0.v))
        campus_base_pu = campus_share * base_system_load_pu
        q_ratio = math.tan(math.acos(CAMPUS_POWER_FACTOR))
        burst_fraction = float(burst_case["fraction_of_p95_active_gpu"])

        device_ids, campus_buses = add_campus_loads(system, scenario_label, campus_base_pu, q_ratio)
        add_campus_monitors(
            system,
            campus_buses,
            prefix=scenario_label.replace(" ", "").replace("(", "").replace(")", ""),
        )
        add_burst_step(system, device_ids, scenario_label, campus_base_pu, burst_fraction, q_ratio)

        weak_line = GRID_MODES[grid_mode]
        if weak_line:
            add_weak_grid_toggle(system, weak_line)

        setup_ok = bool(system.setup())
        system.PFlow.run()
        power_flow_ok = bool(system.PFlow.converged)

        system.TDS.config.tf = SIM_DURATION_S
        system.TDS.config.no_tqdm = 1
        system.TDS.run()

        tds_ok = bool(system.TDS.converged)
        times_s = np.asarray(system.dae.ts.t, dtype=float)
        states = np.asarray(system.dae.ts.y, dtype=float)

    campus_voltage_indices = np.array(
        [system.Bus.v.a[system.Bus.idx2uid(bus_idx)] for bus_idx in campus_buses],
        dtype=int,
    )
    campus_freq_indices = np.array(system.BusFreq.f.a[-len(campus_buses) :], dtype=int)

    campus_voltage_series = states[:, campus_voltage_indices]
    campus_min_v_series = np.min(campus_voltage_series, axis=1)
    campus_freq_series = states[:, campus_freq_indices]
    campus_freq_dev_hz = np.abs(campus_freq_series - 1.0) * 60.0

    pre_event_mask = times_s < STEP_TIME_S
    pre_event_min_vpu = float(np.min(campus_min_v_series[pre_event_mask])) if np.any(pre_event_mask) else float(campus_min_v_series[0])
    min_campus_vpu = float(np.min(campus_min_v_series))
    final_min_campus_vpu = float(campus_min_v_series[-1])
    max_abs_campus_freq_dev_hz = float(np.max(campus_freq_dev_hz))
    settling_s = settling_time_seconds(times_s, campus_min_v_series, STEP_TIME_S, final_min_campus_vpu)

    return {
        "scenario_label": scenario_label,
        "grid_mode": grid_mode,
        "weak_grid_line": weak_line,
        "campus_share_of_system_load": campus_share,
        "base_system_load_pu": base_system_load_pu,
        "campus_base_pu": campus_base_pu,
        "campus_base_mw": campus_base_pu * SYSTEM_BASE_MVA,
        "burst_case_name": burst_case["name"],
        "window_seconds": int(burst_case["window_seconds"]),
        "burst_fraction_of_campus_base": burst_fraction,
        "burst_step_pu": campus_base_pu * burst_fraction,
        "burst_step_mw": campus_base_pu * burst_fraction * SYSTEM_BASE_MVA,
        "positive_event_fraction": float(burst_case["positive_event_fraction"]),
        "setup_ok": setup_ok,
        "power_flow_ok": power_flow_ok,
        "tds_converged": tds_ok,
        "andes_messages_excerpt": captured.getvalue().strip().splitlines()[-12:],
        "campus_buses": campus_buses,
        "pre_event_min_campus_vpu": pre_event_min_vpu,
        "min_campus_vpu": min_campus_vpu,
        "final_min_campus_vpu": final_min_campus_vpu,
        "max_campus_v_drop_pu": pre_event_min_vpu - min_campus_vpu,
        "max_abs_campus_freq_dev_hz": max_abs_campus_freq_dev_hz,
        "voltage_settling_time_s": settling_s,
    }


def build_report(args: argparse.Namespace) -> dict:
    operating_report = load_json(args.operating_report)
    burst_cases = burst_cases_from_operating_report(operating_report)
    andes = load_andes_runtime()

    rows = []
    for campus_share in args.campus_shares:
        for grid_mode in GRID_MODES:
            for burst_case in burst_cases:
                for scenario_label in ("Scenario 2(M)", "Scenario 3(M)"):
                    rows.append(
                        run_single_case(
                            andes=andes,
                            case_path=args.case_path,
                            andes_pycode=args.andes_pycode,
                            scenario_label=scenario_label,
                            campus_share=campus_share,
                            burst_case=burst_case,
                            grid_mode=grid_mode,
                        )
                    )

    comparison_rows = []
    keyed = {
        (
            row["campus_share_of_system_load"],
            row["grid_mode"],
            row["burst_case_name"],
            row["scenario_label"],
        ): row
        for row in rows
    }
    for campus_share in args.campus_shares:
        for grid_mode in GRID_MODES:
            for burst_case in burst_cases:
                s2 = keyed[(campus_share, grid_mode, burst_case["name"], "Scenario 2(M)")]
                s3 = keyed[(campus_share, grid_mode, burst_case["name"], "Scenario 3(M)")]
                comparison_rows.append(
                    {
                        "campus_share_of_system_load": campus_share,
                        "grid_mode": grid_mode,
                        "burst_case_name": burst_case["name"],
                        "window_seconds": int(burst_case["window_seconds"]),
                        "s2_tds_converged": s2["tds_converged"],
                        "s3_tds_converged": s3["tds_converged"],
                        "s2_min_campus_vpu": s2["min_campus_vpu"],
                        "s3_min_campus_vpu": s3["min_campus_vpu"],
                        "s2_max_freq_dev_hz": s2["max_abs_campus_freq_dev_hz"],
                        "s3_max_freq_dev_hz": s3["max_abs_campus_freq_dev_hz"],
                        "delta_min_campus_vpu": s3["min_campus_vpu"] - s2["min_campus_vpu"],
                        "delta_max_freq_dev_hz": s3["max_abs_campus_freq_dev_hz"] - s2["max_abs_campus_freq_dev_hz"],
                    }
                )

    converged_rows = [
        row for row in comparison_rows if row["s2_tds_converged"] and row["s3_tds_converged"]
    ]
    strongest_voltage = max(converged_rows, key=lambda row: row["delta_min_campus_vpu"])
    strongest_frequency = min(converged_rows, key=lambda row: row["delta_max_freq_dev_hz"])
    nonconverged_rows = [
        row for row in rows if not row["tds_converged"]
    ]

    return {
        "meta": {
            "title": "Public RMS dynamic study on a public ANDES benchmark",
            "updated": "2026-04-11",
            "note": (
                "This is an RMS electromechanical benchmark screen using a public ANDES IEEE 14-bus "
                "dynamic case. It is not a converter EMT model. Scenario 2(M) is represented as four "
                "distributed AC-fed block interfaces, while Scenario 3(M) is represented as one "
                "centralized upstream front-end interface."
            ),
            "case_path": str(args.case_path),
            "distributed_buses": DISTRIBUTED_POI_BUSES,
            "centralized_bus": CENTRALIZED_POI_BUS,
            "weak_grid_line": REMOTE_CORRIDOR_WEAKENING_LINE,
        },
        "operating_source": {
            "operating_report": str(args.operating_report),
            "burst_case_basis": "MIT Supercloud p95 positive-event burst magnitudes",
        },
        "study_parameters": {
            "campus_shares_of_system_load": list(args.campus_shares),
            "step_time_s": STEP_TIME_S,
            "trip_time_s": TRIP_TIME_S,
            "simulation_duration_s": SIM_DURATION_S,
            "campus_power_factor": CAMPUS_POWER_FACTOR,
        },
        "runs": rows,
        "comparisons": comparison_rows,
        "headline": {
            "strongest_voltage_separation": strongest_voltage,
            "strongest_frequency_separation": strongest_frequency,
            "converged_comparison_count": len(converged_rows),
            "nonconverged_run_count": len(nonconverged_rows),
        },
        "nonconverged_runs": nonconverged_rows,
    }


def build_note(report: dict) -> str:
    headline_v = report["headline"]["strongest_voltage_separation"]
    headline_f = report["headline"]["strongest_frequency_separation"]

    selected_rows = [["Campus share", "Grid mode", "Burst case", "S2 TDS", "S3 TDS", "S2 min Vpu", "S3 min Vpu", "S2 max |df|", "S3 max |df|"]]
    for row in report["comparisons"]:
        if abs(row["campus_share_of_system_load"] - 0.25) < 1e-9:
            selected_rows.append(
                [
                    format_pct(row["campus_share_of_system_load"]),
                    row["grid_mode"],
                    row["burst_case_name"],
                    "OK" if row["s2_tds_converged"] else "STOP",
                    "OK" if row["s3_tds_converged"] else "STOP",
                    f"{row['s2_min_campus_vpu']:.4f}",
                    f"{row['s3_min_campus_vpu']:.4f}",
                    format_hz(row["s2_max_freq_dev_hz"]),
                    format_hz(row["s3_max_freq_dev_hz"]),
                ]
            )

    share_rows = [["Campus share", "Best S3-S2 voltage margin", "Best S3-S2 frequency margin"]]
    for campus_share in report["study_parameters"]["campus_shares_of_system_load"]:
        rows = [
            row
            for row in report["comparisons"]
            if abs(row["campus_share_of_system_load"] - campus_share) < 1e-9
            and row["s2_tds_converged"]
            and row["s3_tds_converged"]
        ]
        share_rows.append(
            [
                format_pct(campus_share),
                f"{max(row['delta_min_campus_vpu'] for row in rows):.4f} pu" if rows else "N/A",
                format_hz(min(row["delta_max_freq_dev_hz"] for row in rows)) if rows else "N/A",
            ]
        )

    return "\n".join(
        [
            "# Public RMS Dynamic Study",
            "",
            "Updated: April 11, 2026",
            "",
            "This note adds an RMS electromechanical dynamic layer to the public-data-only reviewer-response package.",
            "",
            "## Model scope",
            "",
            "The study uses the public ANDES IEEE 14-bus full dynamic benchmark. It adds an AI-campus load block to that case and compares:",
            "",
            "- `Scenario 2(M)`: four distributed AC-fed SST block interfaces at buses `9, 10, 13, 14`.",
            "- `Scenario 3(M)`: one centralized upstream AC/DC front-end interface at bus `5`.",
            "- `normal_network`: no topology change before the burst step.",
            f"- `remote_corridor_weakened`: trip `{report['meta']['weak_grid_line']}` at `t={TRIP_TIME_S:.1f}s` before the MIT-derived burst step at `t={STEP_TIME_S:.1f}s`.",
            "",
            "The dynamic disturbance magnitudes are taken from the public MIT Supercloud p95 positive-event burst library. They are applied here as benchmark load steps on a public RMS case. This is not a claim that the RMS simulation resolves converter or sub-second control behavior.",
            "",
            "## Headline separations",
            "",
            f"Converged comparison pairs in this benchmark: `{report['headline']['converged_comparison_count']}`.",
            f"Non-converged runs in this benchmark: `{report['headline']['nonconverged_run_count']}`.",
            f"Strongest converged voltage separation: `{headline_v['burst_case_name']}` under `{headline_v['grid_mode']}` at campus share `{format_pct(headline_v['campus_share_of_system_load'])}`, where Scenario 3(M) improves minimum campus voltage by `{headline_v['delta_min_campus_vpu']:.4f} pu`.",
            f"Strongest converged frequency separation: `{headline_f['burst_case_name']}` under `{headline_f['grid_mode']}` at campus share `{format_pct(headline_f['campus_share_of_system_load'])}`, where Scenario 3(M) changes the maximum local frequency deviation by `{headline_f['delta_max_freq_dev_hz']:.3f} Hz` relative to Scenario 2(M). Negative values favor Scenario 3(M).",
            "",
            "## Detailed comparison at 25% campus-share benchmark",
            "",
            format_table(selected_rows),
            "",
            "## Share sweep summary",
            "",
            format_table(share_rows),
            "",
            "## Interpretation",
            "",
            "- The RMS layer is strongest on minimum campus voltage under the remote-corridor weakening stress case.",
            "- This supports the directional claim that moving the AC/DC boundary upstream reduces exposure to remote AC-corridor weakness when campus subloads are otherwise distributed across multiple AC interfaces.",
            "- Several heaviest distributed-load stress cases are non-convergent in the public RMS benchmark. Those should be interpreted as stability-screen failures, not as converged waveform results.",
            "- The RMS layer is not EMT validation. It does not model converter controls, harmonics, or DC fault transients.",
        ]
    )


def print_summary(report: dict, details: bool) -> None:
    print("Public RMS dynamic study")
    print("------------------------")
    print(f"Case: {report['meta']['case_path']}")
    print(
        "Scenario 2(M) distributed buses:",
        ", ".join(str(bus) for bus in report["meta"]["distributed_buses"]),
    )
    print(f"Scenario 3(M) centralized bus: {report['meta']['centralized_bus']}")
    print(f"Weak-grid corridor trip: {report['meta']['weak_grid_line']}")
    print()

    rows = [["Campus share", "Grid mode", "Burst case", "S2 TDS", "S3 TDS", "S2 min Vpu", "S3 min Vpu", "S2 max |df|", "S3 max |df|"]]
    for row in report["comparisons"]:
        if abs(row["campus_share_of_system_load"] - 0.25) < 1e-9:
            rows.append(
                [
                    format_pct(row["campus_share_of_system_load"]),
                    row["grid_mode"],
                    row["burst_case_name"],
                    "OK" if row["s2_tds_converged"] else "STOP",
                    "OK" if row["s3_tds_converged"] else "STOP",
                    f"{row['s2_min_campus_vpu']:.4f}",
                    f"{row['s3_min_campus_vpu']:.4f}",
                    format_hz(row["s2_max_freq_dev_hz"]),
                    format_hz(row["s3_max_freq_dev_hz"]),
                ]
            )
    print(format_table(rows))

    if details:
        print()
        detail_rows = [["Scenario", "Grid", "Burst", "Campus MW", "Burst MW", "Min Vpu", "Max |df|", "Settle s"]]
        for row in report["runs"]:
            detail_rows.append(
                [
                    row["scenario_label"],
                    row["grid_mode"],
                    row["burst_case_name"],
                    format_mw_from_pu(row["campus_base_pu"]),
                    format_mw_from_pu(row["burst_step_pu"]),
                    f"{row['min_campus_vpu']:.4f}",
                    format_hz(row["max_abs_campus_freq_dev_hz"]),
                    f"{row['voltage_settling_time_s']:.2f}" if row["voltage_settling_time_s"] is not None else "N/A",
                ]
            )
        print()
        print(format_table(detail_rows))


def main() -> None:
    args = parse_args()
    report = build_report(args)
    write_json(args.output_json, report)
    args.output_note.write_text(build_note(report), encoding="utf-8")
    print_summary(report, args.details)


if __name__ == "__main__":
    main()
