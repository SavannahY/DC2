#!/usr/bin/env python3
"""Public annual + burst operating study for AI-factory scenarios.

This script is the first public-data-only modeling layer in the reviewer
response roadmap. It combines:

1. A public annual utilization layer from the NREL ESIF IT-power series.
2. A public AI-workload burst layer derived from labeled MIT Supercloud jobs.

The goal is not to claim that these public datasets are a one-to-one proxy for
any specific AI-factory campus. The goal is to replace the flat reference-year
and hand-picked burst cases with a documented, reproducible public operating
study that later network, harmonic, and dynamic scripts can reuse.
"""

from __future__ import annotations

import argparse
import csv
import json
import math
from collections import Counter
from dataclasses import dataclass
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
from dc_backbone_multinode_campus_model import build_report as build_multinode_report
from dc_backbone_multinode_campus_model import load_topology
from dc_backbone_public_benchmark_model import (
    DEFAULT_ASSUMPTIONS,
    DEFAULT_ESIF_ZIP,
    DEFAULT_PROFILE_JSON,
    DEFAULT_TOPOLOGY,
    build_esif_profile,
    with_public_profile,
)

ROOT = Path(__file__).resolve().parent

DEFAULT_MIT_JOBIDS = ROOT / "public_data" / "mit_supercloud_labelled_jobids.csv"
DEFAULT_MIT_JOB_STATS = ROOT / "public_data" / "mit_supercloud_labelled_job_stats.csv"
DEFAULT_MIT_SLURM_LOG = ROOT / "public_data" / "mit_supercloud_slurm_log.csv"
DEFAULT_MIT_TRES = ROOT / "public_data" / "mit_supercloud_tres_mapping.txt"

DEFAULT_OUTPUT_JSON = ROOT / "public_ai_factory_operating_report.json"
DEFAULT_OUTPUT_NOTE = ROOT / "PUBLIC_AI_FACTORY_OPERATING_STUDY.md"

FIVE_MINUTES = 300
DEFAULT_BURST_WINDOWS_SECONDS = [300, 900, 3600]
SECONDS_PER_HOUR = 3600.0


@dataclass(frozen=True)
class LabeledJob:
    job_id: str
    model: str
    family: str
    start_ts: int
    end_ts: int
    duration_s: int
    gpu_count: float
    cpu_count: float
    node_count: float


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--assumptions", type=Path, default=DEFAULT_ASSUMPTIONS)
    parser.add_argument("--topology", type=Path, default=DEFAULT_TOPOLOGY)
    parser.add_argument("--esif-zip", type=Path, default=DEFAULT_ESIF_ZIP)
    parser.add_argument("--esif-profile-json", type=Path, default=DEFAULT_PROFILE_JSON)
    parser.add_argument("--mit-jobids-csv", type=Path, default=DEFAULT_MIT_JOBIDS)
    parser.add_argument("--mit-job-stats-csv", type=Path, default=DEFAULT_MIT_JOB_STATS)
    parser.add_argument("--mit-slurm-log-csv", type=Path, default=DEFAULT_MIT_SLURM_LOG)
    parser.add_argument("--mit-tres-mapping", type=Path, default=DEFAULT_MIT_TRES)
    parser.add_argument("--output-json", type=Path, default=DEFAULT_OUTPUT_JSON)
    parser.add_argument("--output-note", type=Path, default=DEFAULT_OUTPUT_NOTE)
    parser.add_argument("--sample-seconds", type=int, default=FIVE_MINUTES)
    parser.add_argument(
        "--burst-windows-seconds",
        type=int,
        nargs="+",
        default=DEFAULT_BURST_WINDOWS_SECONDS,
        help="Positive ramp windows used for AI burst extraction.",
    )
    parser.add_argument(
        "--esif-bins",
        type=int,
        default=12,
        help="Number of annual operating bins to derive from the ESIF IT-power series.",
    )
    parser.add_argument(
        "--esif-normalization-quantile",
        type=float,
        default=0.995,
        help="Quantile used to normalize the ESIF IT-power series before clipping to 1.0.",
    )
    parser.add_argument("--details", action="store_true")
    return parser.parse_args()


def write_json(path: Path, payload: dict) -> None:
    path.write_text(json.dumps(payload, indent=2), encoding="utf-8")


def family_from_model(model: str) -> str:
    lowered = model.strip().lower()
    if "bert" in lowered:
        return "language"
    if lowered.startswith("u"):
        return "unet"
    if any(token in lowered for token in ["dimenet", "schnet", "pna", "nnconv", "conv"]):
        return "graph"
    return "vision"


def parse_tres_map(path: Path) -> Dict[int, str]:
    mapping: Dict[int, str] = {}
    with path.open(encoding="utf-8") as handle:
        reader = csv.DictReader(handle)
        for row in reader:
            mapping[int(row["tres_id"].strip())] = row["resource_type"].strip()
    return mapping


def parse_tres_request(raw: str) -> Dict[int, float]:
    parsed: Dict[int, float] = {}
    if not raw:
        return parsed
    for item in raw.split(","):
        if "=" not in item:
            continue
        key_raw, value_raw = item.split("=", 1)
        try:
            parsed[int(key_raw)] = float(value_raw)
        except ValueError:
            continue
    return parsed


def load_labelled_models(jobids_csv: Path) -> Dict[str, str]:
    mapping: Dict[str, str] = {}
    with jobids_csv.open(encoding="utf-8") as handle:
        reader = csv.DictReader(handle)
        for row in reader:
            mapping[row["id_job"].strip()] = row["model"].strip()
    return mapping


def load_labelled_job_stats(path: Path) -> Dict[str, int]:
    if not path.exists():
        return {}
    stats: Dict[str, int] = {}
    with path.open(encoding="utf-8") as handle:
        reader = csv.DictReader(handle)
        for row in reader:
            stats[row["model"].strip()] = int(float(row["count"]))
    return stats


def load_labeled_jobs(
    jobids_csv: Path,
    slurm_log_csv: Path,
    tres_mapping_path: Path,
) -> tuple[list[LabeledJob], dict]:
    if not slurm_log_csv.exists():
        raise FileNotFoundError(
            "MIT Supercloud slurm_log_csv is not present locally. "
            "Download the public scheduler archive from https://dcc.mit.edu/data/ "
            "and place the extracted CSV at "
            f"{slurm_log_csv}."
        )
    labelled_models = load_labelled_models(jobids_csv)
    tres_mapping = parse_tres_map(tres_mapping_path)
    gpu_tres_ids = {
        tres_id
        for tres_id, resource in tres_mapping.items()
        if resource.startswith("gpu:")
    }

    jobs: List[LabeledJob] = []
    with slurm_log_csv.open(encoding="utf-8") as handle:
        reader = csv.DictReader(handle)
        for row in reader:
            job_id = row["id_job"].strip()
            model = labelled_models.get(job_id)
            if model is None:
                continue

            try:
                start_ts = int(row["time_start"])
                end_ts = int(row["time_end"])
            except ValueError:
                continue
            if start_ts <= 0 or end_ts <= start_ts:
                continue

            tres_req = parse_tres_request(row["tres_req"])
            gpu_count = sum(tres_req.get(tres_id, 0.0) for tres_id in gpu_tres_ids)
            if gpu_count <= 0.0:
                continue

            cpu_count = float(row["cpus_req"] or 0.0)
            node_count = float(row["nodes_alloc"] or 0.0)
            jobs.append(
                LabeledJob(
                    job_id=job_id,
                    model=model,
                    family=family_from_model(model),
                    start_ts=start_ts,
                    end_ts=end_ts,
                    duration_s=end_ts - start_ts,
                    gpu_count=gpu_count,
                    cpu_count=cpu_count,
                    node_count=node_count,
                )
            )

    meta = {
        "job_count_total_labeled": len(labelled_models),
        "job_count_valid_timed_gpu": len(jobs),
        "gpu_tres_resources": {str(key): tres_mapping[key] for key in sorted(gpu_tres_ids)},
    }
    return jobs, meta


def time_weighted_quantile(values: np.ndarray, durations_s: np.ndarray, quantile: float) -> float:
    if values.size == 0:
        return 0.0
    order = np.argsort(values)
    sorted_values = values[order]
    sorted_weights = durations_s[order]
    cumulative = np.cumsum(sorted_weights)
    threshold = quantile * cumulative[-1]
    index = int(np.searchsorted(cumulative, threshold, side="left"))
    return float(sorted_values[min(index, sorted_values.size - 1)])


def build_ai_concurrency_trace(
    jobs: Sequence[LabeledJob],
    sample_seconds: int,
) -> dict:
    if not jobs:
        raise RuntimeError("No valid labeled AI jobs were found in the MIT public dataset.")

    start_ts = min(job.start_ts for job in jobs)
    end_ts = max(job.end_ts for job in jobs)
    n_steps = int(math.ceil((end_ts - start_ts) / sample_seconds)) + 1
    sample_ts = start_ts + np.arange(n_steps, dtype=np.int64) * sample_seconds

    total_delta = np.zeros(n_steps + 1, dtype=float)
    family_delta: Dict[str, np.ndarray] = {}
    for job in jobs:
        start_idx = int((job.start_ts - start_ts) // sample_seconds)
        end_idx = int(math.ceil((job.end_ts - start_ts) / sample_seconds))
        total_delta[start_idx] += job.gpu_count
        total_delta[end_idx] -= job.gpu_count
        family_delta.setdefault(job.family, np.zeros(n_steps + 1, dtype=float))
        family_delta[job.family][start_idx] += job.gpu_count
        family_delta[job.family][end_idx] -= job.gpu_count

    active_gpu = np.cumsum(total_delta[:-1])
    active_gpu_by_family = {
        family: np.cumsum(delta[:-1]) for family, delta in family_delta.items()
    }
    interval_durations = np.full(active_gpu.shape, float(sample_seconds), dtype=float)
    if interval_durations.size:
        interval_durations[-1] = max(1.0, float(end_ts - sample_ts[-1]))

    total_gpu_seconds = float(np.sum(active_gpu * interval_durations))
    family_gpu_seconds = {
        family: float(np.sum(series * interval_durations))
        for family, series in active_gpu_by_family.items()
    }

    active_p95 = time_weighted_quantile(active_gpu, interval_durations, 0.95)
    active_p99 = time_weighted_quantile(active_gpu, interval_durations, 0.99)
    if active_p95 <= 0.0:
        active_p95 = float(np.max(active_gpu))
    if active_p99 <= 0.0:
        active_p99 = float(np.max(active_gpu))

    return {
        "start_ts": int(start_ts),
        "end_ts": int(end_ts),
        "sample_seconds": int(sample_seconds),
        "samples": int(active_gpu.size),
        "duration_days": float((end_ts - start_ts) / 86400.0),
        "active_gpu_series": active_gpu.tolist(),
        "active_gpu_by_family": {family: series.tolist() for family, series in active_gpu_by_family.items()},
        "interval_seconds": interval_durations.tolist(),
        "summary": {
            "max_active_gpu": float(np.max(active_gpu)),
            "mean_active_gpu": float(total_gpu_seconds / np.sum(interval_durations)),
            "p50_active_gpu": time_weighted_quantile(active_gpu, interval_durations, 0.50),
            "p90_active_gpu": time_weighted_quantile(active_gpu, interval_durations, 0.90),
            "p95_active_gpu": active_p95,
            "p99_active_gpu": active_p99,
            "total_gpu_hours": total_gpu_seconds / SECONDS_PER_HOUR,
            "family_gpu_hour_share": {
                family: value / total_gpu_seconds if total_gpu_seconds > 0.0 else 0.0
                for family, value in family_gpu_seconds.items()
            },
        },
    }


def summarize_jobs(jobs: Sequence[LabeledJob], labelled_job_stats: Dict[str, int]) -> dict:
    durations = np.array([job.duration_s for job in jobs], dtype=float)
    gpu_counts = np.array([job.gpu_count for job in jobs], dtype=float)
    nodes = np.array([job.node_count for job in jobs], dtype=float)
    cpus = np.array([job.cpu_count for job in jobs], dtype=float)

    family_counts = Counter(job.family for job in jobs)
    family_gpu_hours = Counter()
    top_model_counts = Counter(job.model for job in jobs)
    for job in jobs:
        family_gpu_hours[job.family] += job.gpu_count * job.duration_s / SECONDS_PER_HOUR

    return {
        "job_count": len(jobs),
        "family_counts": dict(family_counts),
        "family_gpu_hours": dict(family_gpu_hours),
        "model_count_crosscheck": {
            "top_models_in_jobids": top_model_counts.most_common(10),
            "labelled_job_stats_top_models": Counter(labelled_job_stats).most_common(10),
        },
        "duration_hours": {
            "mean": float(np.mean(durations) / SECONDS_PER_HOUR),
            "p50": float(np.quantile(durations, 0.50) / SECONDS_PER_HOUR),
            "p90": float(np.quantile(durations, 0.90) / SECONDS_PER_HOUR),
            "p95": float(np.quantile(durations, 0.95) / SECONDS_PER_HOUR),
            "p99": float(np.quantile(durations, 0.99) / SECONDS_PER_HOUR),
        },
        "requested_gpu_count": {
            "mean": float(np.mean(gpu_counts)),
            "p50": float(np.quantile(gpu_counts, 0.50)),
            "p90": float(np.quantile(gpu_counts, 0.90)),
            "p95": float(np.quantile(gpu_counts, 0.95)),
            "p99": float(np.quantile(gpu_counts, 0.99)),
            "max": float(np.max(gpu_counts)),
        },
        "requested_nodes": {
            "mean": float(np.mean(nodes)),
            "p50": float(np.quantile(nodes, 0.50)),
            "p95": float(np.quantile(nodes, 0.95)),
            "max": float(np.max(nodes)),
        },
        "requested_cpus": {
            "mean": float(np.mean(cpus)),
            "p50": float(np.quantile(cpus, 0.50)),
            "p95": float(np.quantile(cpus, 0.95)),
            "max": float(np.max(cpus)),
        },
    }


def build_burst_summary(
    concurrency_trace: dict,
    windows_seconds: Sequence[int],
) -> dict:
    active = np.array(concurrency_trace["active_gpu_series"], dtype=float)
    sample_seconds = concurrency_trace["sample_seconds"]
    p95_active = concurrency_trace["summary"]["p95_active_gpu"]
    p99_active = concurrency_trace["summary"]["p99_active_gpu"]
    max_active = concurrency_trace["summary"]["max_active_gpu"]

    burst_windows = []
    derived_cases = []
    for window_s in windows_seconds:
        step_count = max(1, int(math.ceil(window_s / sample_seconds)))
        if active.size <= step_count:
            continue
        delta = active[step_count:] - active[:-step_count]
        positive_delta = np.maximum(delta, 0.0)
        positive_events = positive_delta[positive_delta > 0.0]
        if positive_events.size == 0:
            positive_events = np.array([0.0], dtype=float)

        burst_windows.append(
            {
                "window_seconds": int(window_s),
                "sample_steps": int(step_count),
                "positive_event_fraction": float(np.mean(positive_delta > 0.0)),
                "positive_delta_gpu": {
                    "p50": float(np.quantile(positive_delta, 0.50)),
                    "p90": float(np.quantile(positive_delta, 0.90)),
                    "p95": float(np.quantile(positive_delta, 0.95)),
                    "p99": float(np.quantile(positive_delta, 0.99)),
                    "max": float(np.max(positive_delta)),
                },
                "conditional_positive_delta_gpu": {
                    "p50": float(np.quantile(positive_events, 0.50)),
                    "p90": float(np.quantile(positive_events, 0.90)),
                    "p95": float(np.quantile(positive_events, 0.95)),
                    "p99": float(np.quantile(positive_events, 0.99)),
                    "max": float(np.max(positive_events)),
                },
                "positive_delta_fraction_of_p95_active": {
                    "p90": float(np.quantile(positive_delta, 0.90) / p95_active) if p95_active > 0 else 0.0,
                    "p95": float(np.quantile(positive_delta, 0.95) / p95_active) if p95_active > 0 else 0.0,
                    "p99": float(np.quantile(positive_delta, 0.99) / p95_active) if p95_active > 0 else 0.0,
                },
                "conditional_positive_delta_fraction_of_p95_active": {
                    "p90": float(np.quantile(positive_events, 0.90) / p95_active) if p95_active > 0 else 0.0,
                    "p95": float(np.quantile(positive_events, 0.95) / p95_active) if p95_active > 0 else 0.0,
                    "p99": float(np.quantile(positive_events, 0.99) / p95_active) if p95_active > 0 else 0.0,
                },
                "positive_delta_fraction_of_p99_active": {
                    "p90": float(np.quantile(positive_delta, 0.90) / p99_active) if p99_active > 0 else 0.0,
                    "p95": float(np.quantile(positive_delta, 0.95) / p99_active) if p99_active > 0 else 0.0,
                    "p99": float(np.quantile(positive_delta, 0.99) / p99_active) if p99_active > 0 else 0.0,
                },
                "positive_delta_fraction_of_max_active": {
                    "p90": float(np.quantile(positive_delta, 0.90) / max_active) if max_active > 0 else 0.0,
                    "p95": float(np.quantile(positive_delta, 0.95) / max_active) if max_active > 0 else 0.0,
                    "p99": float(np.quantile(positive_delta, 0.99) / max_active) if max_active > 0 else 0.0,
                },
            }
        )

        for quantile_label, quantile_value in [("p90", 0.90), ("p95", 0.95), ("p99", 0.99)]:
            burst_gpu = float(np.quantile(positive_events, quantile_value))
            derived_cases.append(
                {
                    "name": f"mit_ai_burst_{window_s}s_{quantile_label}",
                    "window_seconds": int(window_s),
                    "basis": (
                        "Derived from the public MIT Supercloud labeled AI-job scheduler trace. "
                        "This is a lower-bound AI-specific concurrency burst library, not a direct "
                        "campus power waveform."
                    ),
                    "positive_event_fraction": float(np.mean(positive_delta > 0.0)),
                    "positive_delta_gpu": burst_gpu,
                    "fraction_of_p95_active_gpu": burst_gpu / p95_active if p95_active > 0 else 0.0,
                    "fraction_of_p99_active_gpu": burst_gpu / p99_active if p99_active > 0 else 0.0,
                    "fraction_of_max_active_gpu": burst_gpu / max_active if max_active > 0 else 0.0,
                    "ramp_fraction_of_p95_per_minute": (
                        (burst_gpu / p95_active) / (window_s / 60.0) if p95_active > 0 else 0.0
                    ),
                }
            )

    return {
        "windows": burst_windows,
        "derived_cases": derived_cases,
    }


def load_or_build_esif_profile(
    profile_json_path: Path,
    esif_zip_path: Path,
    bin_count: int,
    clip_quantile: float,
) -> dict:
    if profile_json_path.exists():
        return load_json(profile_json_path)
    payload = build_esif_profile(esif_zip_path, bin_count, clip_quantile)
    write_json(profile_json_path, payload)
    return payload


def build_annual_results(
    assumptions_path: Path,
    topology_path: Path,
    profile_payload: dict,
) -> dict:
    assumptions = load_json(assumptions_path)
    annual_assumptions = with_public_profile(assumptions, profile_payload)
    single_path_report = run_model(annual_assumptions, include_opendss=False)
    topology = load_topology(topology_path)
    multinode_report = build_multinode_report(annual_assumptions, topology)
    return {
        "assumptions": annual_assumptions,
        "single_path_report": single_path_report,
        "multinode_report": multinode_report,
    }


def build_report(args: argparse.Namespace) -> dict:
    profile_payload = load_or_build_esif_profile(
        args.esif_profile_json,
        args.esif_zip,
        args.esif_bins,
        args.esif_normalization_quantile,
    )
    annual_results = build_annual_results(args.assumptions, args.topology, profile_payload)

    labelled_job_stats = load_labelled_job_stats(args.mit_job_stats_csv)
    jobs, mit_meta = load_labeled_jobs(
        args.mit_jobids_csv,
        args.mit_slurm_log_csv,
        args.mit_tres_mapping,
    )
    job_summary = summarize_jobs(jobs, labelled_job_stats)
    concurrency_trace = build_ai_concurrency_trace(jobs, args.sample_seconds)
    burst_summary = build_burst_summary(concurrency_trace, args.burst_windows_seconds)

    single_lookup = {
        result["name"]: result for result in annual_results["single_path_report"]["results"]
    }
    multi_lookup = {
        result["scenario_label"]: result
        for result in annual_results["multinode_report"]["architectures"]
    }

    return {
        "meta": {
            "title": "Public annual + burst operating study for AI-factory scenarios",
            "updated_utc_offset_free": "2026-04-11",
            "scope_note": (
                "This is a public-data-only operating study. ESIF provides an empirical annual "
                "IT-load-shape layer. MIT Supercloud provides a labeled AI-workload burst layer "
                "from public scheduler metadata. This is not a site-specific operating study."
            ),
        },
        "data_sources": {
            "esif": {
                "source": "NREL ESIF public facility IT-power series",
                "series": "it_power_kw",
                "local_zip": str(args.esif_zip),
                "cached_profile_json": str(args.esif_profile_json),
            },
            "mit_supercloud": {
                "jobids_csv": str(args.mit_jobids_csv),
                "job_stats_csv": str(args.mit_job_stats_csv),
                "slurm_log_csv": str(args.mit_slurm_log_csv),
                "tres_mapping": str(args.mit_tres_mapping),
                **mit_meta,
            },
        },
        "annual_layer": {
            "esif_profile": profile_payload,
            "single_path_results": annual_results["single_path_report"],
            "multinode_results": annual_results["multinode_report"],
        },
        "mit_ai_burst_layer": {
            "job_summary": job_summary,
            "concurrency_summary": concurrency_trace["summary"],
            "concurrency_trace_meta": {
                "start_ts": concurrency_trace["start_ts"],
                "end_ts": concurrency_trace["end_ts"],
                "sample_seconds": concurrency_trace["sample_seconds"],
                "samples": concurrency_trace["samples"],
                "duration_days": concurrency_trace["duration_days"],
            },
            "burst_summary": burst_summary,
        },
        "reviewer_response_value": {
            "addresses": [
                "annual-loss realism",
                "public AI-workload burst realism",
                "shared operating-point library for later common-network and RMS studies",
            ],
            "single_path_annual_loss_gwh": {
                "scenario_2": single_lookup["ac_fed_sst_800vdc"]["annual_loss_mwh"] / 1000.0,
                "scenario_3": single_lookup["proposed_mvdc_backbone"]["annual_loss_mwh"] / 1000.0,
            },
            "multinode_annual_loss_gwh": {
                "scenario_2m": multi_lookup["Scenario 2(M)"]["annual_summary"]["annual_loss_mwh"] / 1000.0,
                "scenario_3m": multi_lookup["Scenario 3(M)"]["annual_summary"]["annual_loss_mwh"] / 1000.0,
            },
            "recommended_dynamic_cases": burst_summary["derived_cases"],
        },
    }


def build_note(report: dict) -> str:
    single = {
        result["name"]: result for result in report["annual_layer"]["single_path_results"]["results"]
    }
    multi = {
        result["scenario_label"]: result
        for result in report["annual_layer"]["multinode_results"]["architectures"]
    }
    mit_job_summary = report["mit_ai_burst_layer"]["job_summary"]
    mit_concurrency = report["mit_ai_burst_layer"]["concurrency_summary"]
    burst_cases = report["mit_ai_burst_layer"]["burst_summary"]["derived_cases"]

    single_rows = [
        ["Scenario", "Full-Load Eff.", "Annual Loss", "Annual Loss Cost"],
        [
            "Scenario 2",
            format_pct(single["ac_fed_sst_800vdc"]["full_load_total_efficiency"]),
            format_gwh(single["ac_fed_sst_800vdc"]["annual_loss_mwh"]),
            format_money_millions(single["ac_fed_sst_800vdc"]["annual_loss_cost_usd"]),
        ],
        [
            "Scenario 3",
            format_pct(single["proposed_mvdc_backbone"]["full_load_total_efficiency"]),
            format_gwh(single["proposed_mvdc_backbone"]["annual_loss_mwh"]),
            format_money_millions(single["proposed_mvdc_backbone"]["annual_loss_cost_usd"]),
        ],
    ]
    multi_rows = [
        ["Scenario", "Full-Load Eff.", "Annual Loss", "Annual Loss Cost"],
        [
            "Scenario 2(M)",
            format_pct(multi["Scenario 2(M)"]["full_load"]["total_efficiency"]),
            format_gwh(multi["Scenario 2(M)"]["annual_summary"]["annual_loss_mwh"]),
            format_money_millions(multi["Scenario 2(M)"]["annual_summary"]["annual_loss_cost_usd"]),
        ],
        [
            "Scenario 3(M)",
            format_pct(multi["Scenario 3(M)"]["full_load"]["total_efficiency"]),
            format_gwh(multi["Scenario 3(M)"]["annual_summary"]["annual_loss_mwh"]),
            format_money_millions(multi["Scenario 3(M)"]["annual_summary"]["annual_loss_cost_usd"]),
        ],
    ]

    burst_rows = [["Case", "Window", "Positive event share", "Fraction of p95 active AI load", "Ramp fraction / minute"]]
    for case in burst_cases:
        if case["name"].endswith("p95"):
            burst_rows.append(
                [
                    case["name"],
                    f"{int(case['window_seconds'] / 60)} min",
                    format_pct(case["positive_event_fraction"]),
                    format_pct(case["fraction_of_p95_active_gpu"]),
                    format_pct(case["ramp_fraction_of_p95_per_minute"]),
                ]
            )

    lines = [
        "# Public Annual + Burst Operating Study",
        "",
        "Updated: April 11, 2026",
        "",
        "This note is the first public-data-only operating layer for the reviewer-response roadmap.",
        "It combines:",
        "",
        "- annual utilization bins from the public NREL ESIF `it_power_kw` series,",
        "- labeled AI-workload timing from the public MIT Supercloud scheduler archive,",
        "- and derived burst cases that later common-network, harmonic, and RMS studies can reuse.",
        "",
        "## Why This Matters",
        "",
        "This layer addresses two review weaknesses directly:",
        "",
        "- the earlier annual-loss study looked too much like a flat full-load year,",
        "- and the earlier burst cases were not tied to a public AI-workload dataset.",
        "",
        "This is still not a site-specific operating study. The ESIF dataset is not an AI-factory dataset, and the MIT layer is a labeled AI-workload scheduler study rather than a direct campus power trace. But together they are a much stronger public operating basis than a flat reference year plus hand-picked burst amplitudes.",
        "",
        "## Annual ESIF Layer",
        "",
        f"The cached ESIF profile uses `{len(report['annual_layer']['esif_profile']['load_profile'])}` annual bins and has normalized mean load `{format_pct(report['annual_layer']['esif_profile']['meta']['normalized_mean_fraction'])}` with normalized p95 `{format_pct(report['annual_layer']['esif_profile']['meta']['normalized_p95_fraction'])}`.",
        "",
        "Single-path annualized results under the ESIF profile:",
        "",
        "```text",
        format_table(single_rows),
        "```",
        "",
        "Multi-node annualized results under the same ESIF profile:",
        "",
        "```text",
        format_table(multi_rows),
        "```",
        "",
        "## MIT AI Burst Layer",
        "",
        f"The public MIT scheduler subset contributes `{mit_job_summary['job_count']}` labeled AI jobs over about `{report['mit_ai_burst_layer']['concurrency_trace_meta']['duration_days']:.1f}` days.",
        f"Duration statistics: mean `{mit_job_summary['duration_hours']['mean']:.2f}` h, p50 `{mit_job_summary['duration_hours']['p50']:.2f}` h, p95 `{mit_job_summary['duration_hours']['p95']:.2f}` h, p99 `{mit_job_summary['duration_hours']['p99']:.2f}` h.",
        f"Requested GPU count statistics: mean `{mit_job_summary['requested_gpu_count']['mean']:.2f}`, p50 `{mit_job_summary['requested_gpu_count']['p50']:.2f}`, p95 `{mit_job_summary['requested_gpu_count']['p95']:.2f}`, max `{mit_job_summary['requested_gpu_count']['max']:.0f}`.",
        f"Time-weighted active AI GPU concurrency: mean `{mit_concurrency['mean_active_gpu']:.2f}`, p95 `{mit_concurrency['p95_active_gpu']:.2f}`, max `{mit_concurrency['max_active_gpu']:.2f}`.",
        "",
        "Family mix by labeled job count:",
        "",
        "```text",
        format_table(
            [["Family", "Jobs"]]
            + [[family, str(count)] for family, count in sorted(mit_job_summary["family_counts"].items())]
        ),
        "```",
        "",
        "Representative MIT-derived burst cases for later dynamic studies:",
        "",
        "```text",
        format_table(burst_rows),
        "```",
        "",
        "## How To Use This Layer Next",
        "",
        "- Feed the ESIF annual bins into the common-network and techno-economic studies.",
        "- Feed the MIT-derived burst cases into the harmonic, RMS dynamic, and weak-grid studies.",
        "- Keep the scope disciplined: this is a public operating library, not a substitute for private site telemetry.",
        "",
    ]
    return "\n".join(lines)


def print_summary(report: dict, details: bool) -> None:
    single = {
        result["name"]: result for result in report["annual_layer"]["single_path_results"]["results"]
    }
    multi = {
        result["scenario_label"]: result
        for result in report["annual_layer"]["multinode_results"]["architectures"]
    }
    mit_job_summary = report["mit_ai_burst_layer"]["job_summary"]
    mit_concurrency = report["mit_ai_burst_layer"]["concurrency_summary"]
    burst_windows = report["mit_ai_burst_layer"]["burst_summary"]["windows"]

    print("Public annual + burst operating study")
    print("------------------------------------")
    print(
        "ESIF annual layer: "
        f"mean {format_pct(report['annual_layer']['esif_profile']['meta']['normalized_mean_fraction'])} | "
        f"p95 {format_pct(report['annual_layer']['esif_profile']['meta']['normalized_p95_fraction'])}"
    )
    print(
        "MIT labeled AI layer: "
        f"{mit_job_summary['job_count']} jobs | "
        f"mean duration {mit_job_summary['duration_hours']['mean']:.2f} h | "
        f"p95 active AI GPUs {mit_concurrency['p95_active_gpu']:.2f}"
    )
    print()

    annual_rows = [
        ["Scenario", "Full-Load Eff.", "Annual Loss GWh", "Annual Loss Cost"],
        [
            "Scenario 2",
            format_pct(single["ac_fed_sst_800vdc"]["full_load_total_efficiency"]),
            f"{single['ac_fed_sst_800vdc']['annual_loss_mwh'] / 1000.0:.2f}",
            format_money_millions(single["ac_fed_sst_800vdc"]["annual_loss_cost_usd"]),
        ],
        [
            "Scenario 3",
            format_pct(single["proposed_mvdc_backbone"]["full_load_total_efficiency"]),
            f"{single['proposed_mvdc_backbone']['annual_loss_mwh'] / 1000.0:.2f}",
            format_money_millions(single["proposed_mvdc_backbone"]["annual_loss_cost_usd"]),
        ],
        [
            "Scenario 2(M)",
            format_pct(multi["Scenario 2(M)"]["full_load"]["total_efficiency"]),
            f"{multi['Scenario 2(M)']['annual_summary']['annual_loss_mwh'] / 1000.0:.2f}",
            format_money_millions(multi["Scenario 2(M)"]["annual_summary"]["annual_loss_cost_usd"]),
        ],
        [
            "Scenario 3(M)",
            format_pct(multi["Scenario 3(M)"]["full_load"]["total_efficiency"]),
            f"{multi['Scenario 3(M)']['annual_summary']['annual_loss_mwh'] / 1000.0:.2f}",
            format_money_millions(multi["Scenario 3(M)"]["annual_summary"]["annual_loss_cost_usd"]),
        ],
    ]
    print(format_table(annual_rows))

    if burst_windows:
        print()
        burst_rows = [
            [
                "Window",
                "Positive event share",
                "Conditional p95 +Delta GPUs",
                "Conditional p95 / p95 active",
            ]
        ]
        for window in burst_windows:
            burst_rows.append(
                [
                    f"{int(window['window_seconds'] / 60)} min",
                    format_pct(window["positive_event_fraction"]),
                    f"{window['conditional_positive_delta_gpu']['p95']:.2f}",
                    format_pct(window["conditional_positive_delta_fraction_of_p95_active"]["p95"]),
                ]
            )
        print(format_table(burst_rows))

    if details:
        print()
        print("MIT family counts")
        family_rows = [["Family", "Jobs"]]
        for family, count in sorted(mit_job_summary["family_counts"].items()):
            family_rows.append([family, str(count)])
        print(format_table(family_rows))


def main() -> None:
    args = parse_args()
    report = build_report(args)
    write_json(args.output_json, report)
    args.output_note.write_text(build_note(report), encoding="utf-8")
    print_summary(report, details=args.details)


if __name__ == "__main__":
    main()
