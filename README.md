# DC Subtransmission Backbone for AI Factories

This repository contains the research package for a source-anchored evaluation of medium-voltage direct current (MVDC) subtransmission for large AI-factory campuses. It combines:

- a Python architecture model,
- source-tagged assumptions,
- dynamic-load cases for AI factories,
- OpenDSS AC-boundary cross-checks,
- figure-generation code,
- and a public-facing white paper in PDF, Word, and LaTeX formats.

The central question of the repository is:

Can a campus-scale MVDC backbone provide a more coherent power architecture for AI factories than conventional AC-centric distribution or perimeter-only `800 VDC` conversion?

## Repository Scope

The work in this repository is organized around three scenarios:

1. `Scenario 1`: Traditional AC-centric campus distribution
2. `Scenario 2`: `69 kV AC -> 800 VDC` perimeter conversion
3. `Scenario 3`: Proposed MVDC backbone

The repository now also includes a separate exploratory network model:

4. `Scenario 3(M)`: A multi-node `69 kV DC` backbone connecting multiple DC-native data-center blocks

`Scenario 3(M)` is kept separate from the headline three-scenario table on purpose. It is a more explicit campus network model for the proposed backbone only; `Scenario 1` and `Scenario 2` remain equivalent-path comparisons in the main model.

The repository also now includes an apples-to-apples campus comparator:

5. `Scenario 1(M)`, `Scenario 2(M)`, `Scenario 3(M)`: multi-node versions of all three scenarios on the same shared campus topology

The repository also includes a separate public-data-only upgrade layer:

6. `Public-data-only sensitivity`: public ESIF empirical IT-load-shape bins plus a common-network RTS-GMLC stress screen

The modeling package compares these scenarios on:

- end-to-end full-load efficiency,
- annual electrical loss and loss cost,
- simplified dynamic AI-load stress cases,
- and AC-side feeder behavior using OpenDSS at the campus boundary.

## Current Headline Results

At the current `100 MW` delivered IT reference campus:

| Scenario | Full-load efficiency | Annual loss | Annual loss cost |
| --- | ---: | ---: | ---: |
| Scenario 1: Traditional AC-centric | `87.48%` | `125.36 GWh/year` | `$11.65M/year` |
| Scenario 2: `69 kV AC -> 800 VDC` perimeter conversion | `91.90%` | `77.21 GWh/year` | `$7.17M/year` |
| Scenario 3: Proposed MVDC backbone | `92.17%` | `74.45 GWh/year` | `$6.92M/year` |

Relative to `Scenario 2`, the corrected current `Scenario 3` case is directionally better, but only modestly so: about `0.27` percentage points in full-load efficiency and about `2.76 GWh/year` in annualized reference-profile losses.

## Multi-Node Campus Results

Using the shared four-block campus topology in `multinode_campus_topology.json`, the apples-to-apples multi-node comparison currently gives:

| Scenario | Network kind | Full-load efficiency | Annual loss | Annual loss cost |
| --- | --- | ---: | ---: | ---: |
| Scenario 1(M): Traditional AC-centric | `69 kV AC` | `81.11%` | `204.05 GWh/year` | `$18.96M/year` |
| Scenario 2(M): `69 kV AC -> 800 VDC` perimeter conversion | `69 kV AC` | `86.19%` | `140.38 GWh/year` | `$13.04M/year` |
| Scenario 3(M): Multi-node MVDC backbone | `69 kV DC` | `86.69%` | `134.55 GWh/year` | `$12.50M/year` |

This multi-node comparison keeps the original `Scenario 1`, `Scenario 2`, and `Scenario 3` model intact while adding a more explicit campus topology in which multiple data-center blocks are connected on the same backbone. The ranking is preserved, but the margin between `Scenario 2(M)` and `Scenario 3(M)` is modest.

## Proxy Sensitivity

The repository also includes a stress test for the most important proxy converter curves:

- `dc_backbone_proxy_sensitivity.py`
- `proxy_sensitivity_report.json`

Current result:
- Scenario `3` beats Scenario `2` in `69/125` single-path stress cases
- Scenario `3(M)` beats Scenario `2(M)` in `88/125` multi-node stress cases

This means the architecture direction remains credible, but the quantitative ranking is still materially dependent on the assumed front-end and isolated-pod efficiency curves.

## Public-Data-Only Upgrade

The repository now also includes a public-data-only workflow:

- `dc_backbone_public_benchmark_model.py`
- `dc_backbone_public_benefit_analysis.py`
- `public_benchmark_report.json`
- `public_benefit_report.json`
- `PUBLIC_DATA_UPGRADE.md`
- `PUBLIC_BENEFIT_ANALYSIS.md`

This workflow adds two sensitivity layers using only public datasets:

- a public empirical IT-load-shape layer from the NREL ESIF facility dataset
- a common-network screen using the RTS-GMLC benchmark grid

This is important because it cleans two major review blockers without using any private site, utility, or vendor dataset.

Current public-data-only finding:

- Under the public ESIF part-load sensitivity, `Scenario 3` is no longer ahead of `Scenario 2` in the single-path annual-loss comparison.
- Under the same public ESIF part-load sensitivity, `Scenario 3(M)` still remains ahead of `Scenario 2(M)` in the multi-node campus comparison.
- On the public RTS-GMLC benchmark network, both `Scenario 3` and `Scenario 3(M)` impose slightly lower incremental branch stress than their Scenario `2` counterparts because they draw slightly less source-side power.

The repository also now includes a benefit-specific public-data-only screen:

- Benefit 1: empirical ESIF part-load dominance counts
- Benefit 2: public-network harmonic-sensitivity proxy
- Benefit 3: public-network voltage-drop sensitivity proxy
- N-1: local single-branch-outage robustness on the public RTS benchmark
- Dynamic diversity: clustered and partially cancelling multi-block swing patterns

Current benefit-specific public result:

- Benefit 1 is supported more strongly for `Scenario 3(M)` than for single-path `Scenario 3`.
- Benefit 2 is strongly supported at the architecture level in the multi-node case: the centralized-front-end `Scenario 3(M)` has a much lower public-network THDv proxy than the distributed-interface `Scenario 2(M)`.
- Benefit 3 is also supported at the public-network sensitivity level in the multi-node case: `Scenario 3(M)` shows substantially lower POI voltage-drop sensitivity than `Scenario 2(M)` in both the base and `+10%` step screens.
- In the current expansion sweep, `Scenario 3(M)` first becomes more efficient than `Scenario 2(M)` at `2` active blocks / `50 MW`, while the harmonic and voltage advantages widen as the number of blocks increases.
- Across all three mirrored RTS areas, the `Scenario 3(M)` harmonic and voltage advantages persist; the `Scenario 2(M)`-to-`Scenario 3(M)` harmonic proxy ratio remains at least about `4.5x`, and the voltage-drop proxy ratio remains at least about `2.8x`.
- Under local single-branch-outage screens in all three RTS areas, the `Scenario 3(M)` harmonic and voltage advantages persist; the worst-case harmonic proxy ratio remains at least about `6.3x`, and the worst-case voltage-drop proxy ratio remains at least about `3.8x`.
- Under more realistic dynamic diversity patterns, `Scenario 3(M)` keeps a slightly lower grid-facing source swing than `Scenario 2(M)`, but the internal backbone sees larger segment-current redistribution. That sharpens the claim: the benefit is primarily at the upstream AC boundary, not a universal reduction of all internal dynamic stress.

That is a better scientific position than claiming a uniform advantage everywhere. The public-data-only layer strengthens the multi-node backbone argument and weakens the over-broad single-path claim.

## Main Entry Points

If you are new to the repository, start here:

- White paper PDF:
  - `whitepaper/dc_subtransmission_backbone_position_paper.pdf`
- White paper Word version:
  - `whitepaper/dc_subtransmission_backbone_position_paper.docx`
- White paper LaTeX source:
  - `whitepaper/dc_subtransmission_backbone_position_paper.tex`
- Current machine-readable model output:
  - `source_backed_model_report.json`
- Technical memo:
  - `MODEL_RESULTS_MEMO.md`
- Core model:
  - `dc_backbone_model.py`

## Repository Structure

- `dc_backbone_model.py`
  - Main Python model for the three-scenario comparison
  - Includes steady-state calculations, dynamic-load cases, and optional OpenDSS validation
- `dc_backbone_scenario3m_model.py`
  - Separate Scenario `3(M)` network model
  - Keeps the original Scenario `3` unchanged and replaces the single equivalent backbone with an explicit multi-block `69 kV DC` network
- `dc_backbone_multinode_campus_model.py`
  - Apples-to-apples multi-node campus comparison for `Scenario 1(M)`, `Scenario 2(M)`, and `Scenario 3(M)`
- `dc_backbone_proxy_sensitivity.py`
  - Stress test for the most important proxy efficiency assumptions
- `dc_backbone_public_benchmark_model.py`
  - Public-data-only sensitivity workflow using the RTS-GMLC benchmark grid and NREL ESIF IT-power data
- `dc_backbone_public_benefit_analysis.py`
  - Benefit-specific public-data-only screen for efficiency robustness, harmonic sensitivity, voltage sensitivity, N-1 robustness, and dynamic diversity
- `multinode_campus_topology.json`
  - Shared four-block campus topology used by the multi-node comparison
- `scenario3m_topology.json`
  - Editable topology for the default multi-node Scenario `3(M)` campus
- `scenario3m_default_report.json`
  - Latest generated machine-readable output for the default Scenario `3(M)` topology
- `multinode_campus_report.json`
  - Latest generated machine-readable output for the multi-node campus comparison
- `scientific_assumptions_v1.json`
  - Source-tagged assumptions used by the model
- `source_backed_model_report.json`
  - Latest generated report from the model
- `proxy_sensitivity_report.json`
  - Latest stress-test output for proxy efficiency uncertainty
- `public_benchmark_report.json`
  - Latest output from the public-data-only benchmark workflow
- `PUBLIC_DATA_UPGRADE.md`
  - Notes on what the public-data-only layer improves and what it still does not prove
- `public_benefit_report.json`
  - Latest output from the benefit-specific public-data-only screen
- `PUBLIC_BENEFIT_ANALYSIS.md`
  - Short note on how far the available public datasets support each of the three headline benefits
- `public_data/`
  - Public RTS-GMLC tables and the derived ESIF profile bins
  - The raw ESIF zip is intentionally kept out of GitHub history and regenerated locally from the public URL when needed
- `SCIENTIFIC_DATA_SOURCES.md`
  - Public-source register and traceability notes
- `MODEL_RESULTS_MEMO.md`
  - Standalone technical memo summarizing the current source-backed results
- `posters - figures/`
  - Figure-generation scripts, rendered figures, and editable poster outputs
- `whitepaper/`
  - White paper source files, bibliography, renderer, embedded figures, and exported PDF/DOCX outputs
  - Includes `MOCK_REVIEW_AND_REBUTTAL.md` with an internal harsh-review simulation

## Running the Model

Basic run:

```bash
python3 dc_backbone_model.py
```

Detailed run:

```bash
python3 dc_backbone_model.py --details
```

Run with OpenDSS AC-boundary cross-checks:

```bash
python3 dc_backbone_model.py --run-opendss
```

Run the separate multi-node Scenario `3(M)` model:

```bash
python3 dc_backbone_scenario3m_model.py --details
```

Run the multi-node campus comparison for `Scenario 1(M)`, `2(M)`, and `3(M)`:

```bash
python3 dc_backbone_multinode_campus_model.py --details
```

Run the proxy sensitivity study:

```bash
python3 dc_backbone_proxy_sensitivity.py
```

Run the public-data-only sensitivity workflow:

```bash
python3 dc_backbone_public_benchmark_model.py
```

Run the benefit-specific public-data-only screen:

```bash
python3 dc_backbone_public_benefit_analysis.py
```

Write the results memo:

```bash
python3 dc_backbone_model.py --write-memo MODEL_RESULTS_MEMO.md
```

Regenerate the white paper outputs:

```bash
python3 whitepaper/render_whitepaper_outputs.py
```

## White Paper Package

The white paper package includes:

- `whitepaper/dc_subtransmission_backbone_position_paper.tex`
- `whitepaper/references.bib`
- `whitepaper/dc_subtransmission_backbone_position_paper.pdf`
- `whitepaper/dc_subtransmission_backbone_position_paper.docx`
- `whitepaper/figures/`

The rendered PDF and Word outputs are included in the repository for easy sharing. The LaTeX source and bibliography are also included for revision and reuse.

## Notes on Model Boundaries

This repository does not claim to provide a complete deployment-ready MVDC design. The current work is strongest as:

- an architecture comparison,
- a source-backed efficiency and loss study,
- a dynamic-load sensitivity study,
- and an OpenDSS feeder-boundary validation.

The main remaining research gaps are:

- protection and grounding design,
- converter-grade measured efficiency curves,
- site-specific PCC and harmonic studies,
- and EMT-grade control validation for the centralized front end, DC pod, and buffering layers.
