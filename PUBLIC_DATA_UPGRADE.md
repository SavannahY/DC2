# Public-Data-Only Upgrade

This repository now includes a separate public-data-only workflow in
[dc_backbone_public_benchmark_model.py](/Users/zhengjieyang/Documents/DC2/dc_backbone_public_benchmark_model.py).
It is intentionally separate from the existing source-backed baseline models so
that the original white paper calculations remain reproducible.

## What this adds

The public-data-only workflow addresses two of the strongest review blockers
without relying on any private utility, vendor, or site dataset.

1. It replaces the flat full-load year with a public empirical IT-load-shape
   sensitivity case built from the NREL ESIF public `it_power_kw` time series.
2. It places all scenarios on the same published benchmark network using the
   RTS-GMLC bus and branch tables.

## Public datasets used

- RTS-GMLC benchmark network:
  - [public_data/rts_gmlc/bus.csv](/Users/zhengjieyang/Documents/DC2/public_data/rts_gmlc/bus.csv)
  - [public_data/rts_gmlc/branch.csv](/Users/zhengjieyang/Documents/DC2/public_data/rts_gmlc/branch.csv)
  - Source: [RTS-GMLC GitHub repository](https://github.com/GridMod/RTS-GMLC)
- NREL ESIF facility dataset:
  - Derived profile bins: [public_data/nlr_esif/esif_it_profile_bins.json](/Users/zhengjieyang/Documents/DC2/public_data/nlr_esif/esif_it_profile_bins.json)
  - Source: [NREL data.gov entry](https://catalog.data.gov/dataset/nlr-hpc-facility-power-usage-effectiveness-pue-data)
  - The raw ESIF zip is downloaded locally by the workflow but is not committed to GitHub because of file size.

## What this improves scientifically

- It removes the flat `100%` load-year assumption from the annual-loss
  sensitivity case.
- It puts Scenarios `1/2/3` and `1(M)/2(M)/3(M)` on the same public benchmark
  network instead of comparing them only through local equivalent feeders.
- It makes it harder to overclaim. The public empirical shape does not
  automatically favor Scenario 3, and that is useful information.

## Current public-data-only findings

### Public ESIF empirical load-shape layer

- The ESIF-derived empirical IT-load-shape bins are normalized to the public
  `99.5%` quantile of the `it_power_kw` series.
- Normalized mean IT load fraction: `40.81%`
- Normalized `95th` percentile load fraction: `90.38%`

### Single-path annualized results under the public ESIF load shape

- Scenario 1: `69.21 GWh/year`
- Scenario 2: `46.29 GWh/year`
- Scenario 3: `46.53 GWh/year`

This is important. Under this public empirical part-load sensitivity case,
Scenario 3 is no longer ahead of Scenario 2 in the single-path comparison. That
means the single-path `Scenario 3 > Scenario 2` claim is sensitive to converter
part-load assumptions.

### Multi-node annualized results under the public ESIF load shape

- Scenario 1(M): `86.40 GWh/year`
- Scenario 2(M): `59.58 GWh/year`
- Scenario 3(M): `59.02 GWh/year`

This is also important. The multi-node `Scenario 3(M)` still remains ahead of
`Scenario 2(M)` under the same public empirical load-shape sensitivity. That
supports the position that the stronger benefit of Scenario 3 comes from the
shared backbone architecture, not from a single-path converter-chain claim.

### RTS-GMLC common-network stress screen

Single-point interconnection at RTS bus `110` (`Allen`, `138 kV`) with the RTS
reference bus `113` as the balancing bus:

- Scenario 1: max incremental branch loading `11.07%`
- Scenario 2: max incremental branch loading `10.53%`
- Scenario 3: max incremental branch loading `10.50%`

Multi-node campus interconnection using RTS buses `103`, `104`, `106`, and
`110` as an illustrative `138 kV` campus cluster:

- Scenario 1(M): max incremental branch loading `16.01%`
- Scenario 2(M): max incremental branch loading `15.07%`
- Scenario 3(M): max incremental branch loading `14.98%`

These numbers do not prove deployment readiness. They do show, under a common
public network, that lower source-side demand translates into lower incremental
corridor stress.

## What this does not prove

- It does not replace vendor-grade converter efficiency curves.
- It does not make the ESIF dataset an AI-factory-specific workload trace.
- It does not replace an EMT model.
- It does not resolve IEEE 519 compliance, protection, grounding, or fault
  interruption questions.

## Why this matters for the paper

This upgrade sharpens the argument in two ways.

- It strengthens the paper where the result holds up under public-data-only
  stress: the multi-node backbone case remains directionally favorable.
- It weakens the paper where the result is fragile: the single-path Scenario 3
  advantage over Scenario 2 is not robust under this public empirical part-load
  sensitivity.

That is a better scientific position than presenting the original architecture
comparison as uniformly dominant.

## Follow-on public benefit screen

The repository now also includes:

- [dc_backbone_public_benefit_analysis.py](/Users/zhengjieyang/Documents/DC2/dc_backbone_public_benefit_analysis.py)
- [public_benefit_report.json](/Users/zhengjieyang/Documents/DC2/public_benefit_report.json)
- [PUBLIC_BENEFIT_ANALYSIS.md](/Users/zhengjieyang/Documents/DC2/PUBLIC_BENEFIT_ANALYSIS.md)

This follow-on layer uses the same public RTS-GMLC and ESIF inputs to test the
three headline benefits separately:

- efficiency robustness under the ESIF empirical load shape
- harmonic-sensitivity proxy on the RTS public network
- voltage-drop sensitivity proxy on the RTS public network

That is the right next step if the goal is to make each benefit claim more
explicitly evidence-backed without relying on any private dataset.
