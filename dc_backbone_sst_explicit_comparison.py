#!/usr/bin/env python3
"""Compare SST + 800 VDC baseline, direct-perimeter alternative, and MVDC backbone.

This script leaves the main three-scenario white-paper workflow untouched.
It injects one additional explicit SST comparator into the current assumptions
so the user can distinguish:

1. AC-fed SST + 800 VDC baseline
2. Direct 69 kV AC -> 800 VDC perimeter alternative
3. 69 kV AC -> 69 kV DC backbone -> isolated DC pod -> 800 VDC
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import List, Sequence

from dc_backbone_model import (
    deep_copy_jsonable,
    find_architecture,
    format_gwh,
    format_money_millions,
    format_pct,
    format_table,
    load_json,
    run_model,
)


ROOT = Path(__file__).resolve().parent
DEFAULT_ASSUMPTIONS = ROOT / "scientific_assumptions_v1.json"
DEFAULT_OUTPUT = ROOT / "sst_explicit_comparison_report.json"

BASELINE_SST_NAME = "ac_fed_sst_800vdc"
PERIMETER_ALT_NAME = "ac_direct_perimeter_800vdc"
MVDC_NAME = "proposed_mvdc_backbone"
TRADITIONAL_NAME = "traditional_ac"


def build_direct_perimeter_architecture(assumptions: dict) -> dict:
    baseline_architecture = find_architecture(assumptions, BASELINE_SST_NAME)
    mv_feeder = deep_copy_jsonable(baseline_architecture["elements"][0])
    facility_bus = deep_copy_jsonable(baseline_architecture["elements"][3])
    rack_stage = deep_copy_jsonable(baseline_architecture["elements"][4])
    board_stage = deep_copy_jsonable(baseline_architecture["elements"][5])

    return {
        "name": PERIMETER_ALT_NAME,
        "display_name": "Direct 69 kV AC -> 800 VDC perimeter alternative",
        "notes": (
            "This alternative restores the direct 69 kV AC -> 800 VDC perimeter-conversion shortcut so it can be "
            "compared against the explicit SST + 800 VDC baseline and the MVDC backbone."
        ),
        "native_buffer_anchor": "800 VDC facility bus",
        "innovation_metrics": {
            "ac_harmonic_injection_points": 1,
            "major_conversion_stages": 3,
            "downstream_reactive_coordination_points": 1,
            "dc_native_resource_path": "Direct 800 VDC facility-side path, but AC remains upstream of the facility boundary",
        },
        "elements": [
            mv_feeder,
            {
                "type": "stage",
                "name": "Perimeter 69 kV AC -> 800 VDC converter",
                "curve": "perimeter_69kvac_to_800vdc",
                "rated_output_mw_factor": 1.07,
            },
            facility_bus,
            rack_stage,
            board_stage,
        ],
    }


def with_explicit_sst_architecture(base_assumptions: dict) -> dict:
    assumptions = deep_copy_jsonable(base_assumptions)
    architectures = assumptions["architectures"]
    if not any(architecture["name"] == PERIMETER_ALT_NAME for architecture in architectures):
        insert_index = next(
            (index + 1 for index, architecture in enumerate(architectures) if architecture["name"] == BASELINE_SST_NAME),
            len(architectures),
        )
        architectures.insert(insert_index, build_direct_perimeter_architecture(assumptions))
    assumptions.setdefault("meta", {})
    assumptions["meta"]["status"] = f"{assumptions['meta'].get('status', 'unknown')}_with_direct_perimeter_alt"
    assumptions["meta"]["warning"] = (
        assumptions["meta"].get("warning", "")
        + " Direct-perimeter alternative added for SST + 800 VDC baseline vs direct 800 VDC vs MVDC backbone."
    ).strip()
    return assumptions


def filtered_results(report: dict, include_traditional: bool) -> List[dict]:
    desired = [BASELINE_SST_NAME, PERIMETER_ALT_NAME, MVDC_NAME]
    if include_traditional:
        desired = [TRADITIONAL_NAME] + desired
    order = {name: index for index, name in enumerate(desired)}
    return sorted(
        [result for result in report["results"] if result["name"] in order],
        key=lambda result: order[result["name"]],
    )


def comparison_note(results: Sequence[dict]) -> str:
    baseline = next(result for result in results if result["name"] == BASELINE_SST_NAME)
    perimeter = next(result for result in results if result["name"] == PERIMETER_ALT_NAME)
    mvdc = next(result for result in results if result["name"] == MVDC_NAME)

    return "\n".join(
        [
            "# SST Baseline Comparator Note",
            "",
            "This report compares three forward-looking paths under the same current source-anchored assumptions:",
            "",
            "- explicit `69 kV AC -> SST -> 800 VDC` baseline,",
            "- direct `69 kV AC -> 800 VDC` perimeter alternative,",
            "- `69 kV AC -> 69 kV DC backbone -> isolated DC pod -> 800 VDC`.",
            "",
            f"The explicit SST baseline currently lands at `{format_pct(baseline['full_load_total_efficiency'])}` full-load efficiency.",
            f"The direct perimeter alternative lands at `{format_pct(perimeter['full_load_total_efficiency'])}`.",
            f"The MVDC backbone lands at `{format_pct(mvdc['full_load_total_efficiency'])}`.",
            "",
            f"Relative to the explicit SST baseline, the direct perimeter alternative changes annual loss by "
            f"`{perimeter['annual_loss_mwh'] - baseline['annual_loss_mwh']:+.2f} MWh/year`.",
            f"Relative to the SST baseline, the MVDC backbone changes annual loss by "
            f"`{mvdc['annual_loss_mwh'] - baseline['annual_loss_mwh']:+.2f} MWh/year`.",
            "",
            "This comparison is still proxy-dependent. It separates the architectural question into three steps instead of "
            "collapsing the advanced AC-fed case into one shortcut assumption.",
        ]
    )


def print_summary(results: Sequence[dict]) -> None:
    rows = [
        (
            "Architecture",
            "Full-load Eff.",
            "Full-load Input MW",
            "Annual Loss GWh",
            "Annual Loss Cost",
            "AC Interfaces",
            "Major Conv.",
        )
    ]
    for result in results:
        metrics = result["innovation_metrics"]
        rows.append(
            (
                result["display_name"],
                format_pct(result["full_load_total_efficiency"]),
                f"{result['full_load_input_mw']:.2f}",
                format_gwh(result["annual_loss_mwh"]),
                format_money_millions(result["annual_loss_cost_usd"]),
                str(metrics["ac_harmonic_injection_points"]),
                str(metrics["major_conversion_stages"]),
            )
        )
    print("Explicit SST comparison")
    print("-----------------------")
    print(format_table(rows))


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Compare SST + 800 VDC baseline, direct perimeter alternative, and MVDC backbone.")
    parser.add_argument("--assumptions", type=Path, default=DEFAULT_ASSUMPTIONS, help="Base assumptions JSON.")
    parser.add_argument("--save-json", type=Path, default=DEFAULT_OUTPUT, help="Optional path for machine-readable output.")
    parser.add_argument("--save-note", type=Path, help="Optional path for a short Markdown note.")
    parser.add_argument("--include-traditional", action="store_true", help="Also include the traditional AC baseline.")
    parser.add_argument("--run-opendss", action="store_true", help="Include the existing AC-boundary OpenDSS cross-check.")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    base_assumptions = load_json(args.assumptions)
    assumptions = with_explicit_sst_architecture(base_assumptions)
    report = run_model(assumptions, include_opendss=args.run_opendss)
    selected = filtered_results(report, include_traditional=args.include_traditional)
    output = {
        "meta": report["meta"],
        "global": report["global"],
        "reference_context": report.get("reference_context", {}),
        "results": selected,
    }
    if args.save_json:
        args.save_json.write_text(json.dumps(output, indent=2), encoding="utf-8")
    if args.save_note:
        args.save_note.write_text(comparison_note(selected), encoding="utf-8")
    print_summary(selected)


if __name__ == "__main__":
    main()
