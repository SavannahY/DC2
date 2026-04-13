# DC Subtransmission Backbone for AI Factories

This repository contains the research package for a source-anchored evaluation of medium-voltage direct current (MVDC) subtransmission for large AI-factory campuses. It combines:

- a Python architecture model,
- source-tagged assumptions,
- dynamic-load cases for AI factories,
- OpenDSS AC-boundary cross-checks,
- figure-generation code,
- a public-facing white paper in PDF, Word, and LaTeX formats,
- and a technical-audience PowerPoint deck generated from the same evidence stack.

The central question of the repository is:

Can a campus-scale MVDC backbone provide a more coherent power architecture for AI factories than conventional AC-centric distribution or an AC-fed `SST + 800 VDC` baseline?

## Repository Scope

The work in this repository is organized around three scenarios:

1. `Scenario 1`: Traditional AC-centric campus distribution
2. `Scenario 2`: AC-fed `SST + 800 VDC` baseline
3. `Scenario 3`: Proposed MVDC backbone

The repository now also includes a separate exploratory network model:

4. `Scenario 3(M)`: A multi-node `69 kV DC` backbone connecting multiple DC-native data-center blocks

`Scenario 3(M)` is kept separate from the headline three-scenario table on purpose. It is a more explicit campus network model for the proposed backbone only; `Scenario 1` and `Scenario 2` remain equivalent-path comparisons in the main model.

The repository also now includes an apples-to-apples campus comparator:

5. `Scenario 1(M)`, `Scenario 2(M)`, `Scenario 3(M)`: multi-node versions of all three scenarios on the same shared campus topology

The repository also includes a separate public-data-only upgrade layer:

6. `Public-data-only sensitivity`: public ESIF empirical IT-load-shape bins plus a common-network RTS-GMLC stress screen

It now also includes a public operating-study layer:

7. `Public annual + burst operating study`: ESIF annual utilization bins plus MIT Supercloud labeled AI-job burst statistics

It now also includes two public common-network layers:

8. `Public common-network T&D study`: Scenario `2(M)` vs `3(M)` on a shared SMART-DS feeder-bank benchmark
9. `Public harmonic frequency sweep`: OpenDSS harmonics-mode benchmark on the same SMART-DS feeder-bank benchmark

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
| Scenario 2: AC-fed `SST + 800 VDC` baseline | `91.82%` | `78.06 GWh/year` | `$7.25M/year` |
| Scenario 3: Proposed MVDC backbone | `92.17%` | `74.45 GWh/year` | `$6.92M/year` |

Relative to the `Scenario 2` SST baseline, the current `Scenario 3` case is directionally better, but only modestly so: about `0.35` percentage points in full-load efficiency and about `3.61 GWh/year` in annualized reference-profile losses.

## Multi-Node Campus Results

Using the shared four-block campus topology in `multinode_campus_topology.json`, the apples-to-apples multi-node comparison currently gives:

| Scenario | Network kind | Full-load efficiency | Annual loss | Annual loss cost |
| --- | --- | ---: | ---: | ---: |
| Scenario 1(M): Traditional AC-centric | `69 kV AC` | `81.11%` | `204.05 GWh/year` | `$18.96M/year` |
| Scenario 2(M): AC-fed `SST + 800 VDC` baseline | `69 kV AC` | `85.16%` | `152.70 GWh/year` | `$14.19M/year` |
| Scenario 3(M): Multi-node MVDC backbone | `69 kV DC` | `86.69%` | `134.55 GWh/year` | `$12.50M/year` |

This multi-node comparison keeps the original `Scenario 1`, `Scenario 2`, and `Scenario 3` model intact while adding a more explicit campus topology in which multiple data-center blocks are connected on the same backbone. The ranking is preserved, and the gap between `Scenario 2(M)` and `Scenario 3(M)` is now more visible because the advanced AC-fed baseline is an explicit SST chain rather than a perimeter-conversion shortcut.

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

- Under the public ESIF part-load sensitivity, `Scenario 3` remains ahead of the `Scenario 2` SST baseline in the single-path annual-loss comparison.
- Under the same public ESIF part-load sensitivity, `Scenario 3(M)` also remains ahead of `Scenario 2(M)` in the multi-node campus comparison.
- On the public RTS-GMLC benchmark network, both `Scenario 3` and `Scenario 3(M)` impose lower incremental branch stress than their Scenario `2` counterparts because they draw less source-side power.

The repository also now includes a benefit-specific public-data-only screen:

- Benefit 1: empirical ESIF part-load dominance counts
- Benefit 2: public-network harmonic-sensitivity proxy
- Benefit 3: public-network voltage-drop sensitivity proxy
- N-1: local single-branch-outage robustness on the public RTS benchmark
- Dynamic diversity: clustered and partially cancelling multi-block swing patterns
- Equal-total harmonic benchmark: same total harmonic current for `Scenario 2(M)` and `Scenario 3(M)` under multiple benchmark spectra
- Reduced-order DC transient screen: internal `Scenario 3(M)` burst response with explicit local-buffer limits
- Matched transient comparison: direct `Scenario 2(M)` versus `Scenario 3(M)` burst-response comparison under the same reduced-order buffer model

Current benefit-specific public result:

- Benefit 1 is now supported for both the single-path and multi-node comparisons relative to the `Scenario 2` SST baseline, but the multi-node case remains the stronger architecture result.
- Benefit 2 is strongly supported at the architecture level in the multi-node case: the centralized-front-end `Scenario 3(M)` has a much lower public-network THDv proxy than the distributed-interface `Scenario 2(M)`.
- Benefit 3 is also supported at the public-network sensitivity level in the multi-node case: `Scenario 3(M)` shows substantially lower POI voltage-drop sensitivity than `Scenario 2(M)` in both the base and `+10%` step screens.
- In the current expansion sweep, `Scenario 3(M)` is more efficient than `Scenario 2(M)` at every tested campus size from `25 MW` to `100 MW`, while the harmonic and voltage advantages widen as the number of blocks increases.
- Across all three mirrored RTS areas, the `Scenario 3(M)` harmonic and voltage advantages persist; the `Scenario 2(M)`-to-`Scenario 3(M)` harmonic proxy ratio remains at least about `4.5x`, and the voltage-drop proxy ratio remains at least about `2.8x`.
- Under local single-branch-outage screens in all three RTS areas, the `Scenario 3(M)` harmonic and voltage advantages persist; the worst-case harmonic proxy ratio remains at least about `6.3x`, and the worst-case voltage-drop proxy ratio remains at least about `3.8x`.
- Under more realistic dynamic diversity patterns, `Scenario 3(M)` keeps a slightly lower grid-facing source swing than `Scenario 2(M)`, but the internal backbone sees larger segment-current redistribution. That sharpens the claim: the benefit is primarily at the upstream AC boundary, not a universal reduction of all internal dynamic stress.
- Under the equal-total harmonic benchmark, `Scenario 3(M)` still remains better than `Scenario 2(M)` across all tested benchmark spectra and mirrored RTS areas, with a minimum THDv-proxy advantage of about `1.12x`. That means the PQ result is not only an artifact of injecting less total harmonic current.
- Under the reduced-order internal DC transient screen, a moderate local buffer cuts the coherent-burst source-input ramp from about `1671 MW/s` to about `462 MW/s`, and a stronger local buffer cuts it further to about `67 MW/s`, while the minimum block voltage stays near `0.9997 pu`. That strengthens the dynamic argument by showing that fast bursts can be shaped locally without large internal voltage sag.
- Under the matched reduced-order transient comparison, `Scenario 3(M)` is slightly better than `Scenario 2(M)` on source burst magnitude and source ramp, but it also carries much higher internal segment-current peaks. That means the dynamic benefit should be framed as improved upstream burst shaping, not as a uniform internal-stress reduction.

That is a better scientific position than claiming a uniform advantage everywhere. The public-data-only layer strengthens the multi-node backbone argument and weakens the over-broad single-path claim.

## Main Entry Points

If you are new to the repository, start here:

- White paper PDF:
  - `whitepaper/dc_subtransmission_backbone_position_paper.pdf`
- White paper Word version:
  - `whitepaper/dc_subtransmission_backbone_position_paper.docx`
- White paper LaTeX source:
  - `whitepaper/dc_subtransmission_backbone_position_paper.tex`
- Technical PowerPoint deck:
  - `presentation/dc_subtransmission_backbone_technical_briefing.pptx`
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
- `dc_backbone_sst_explicit_comparison.py`
  - Separate comparator for direct `69 kV AC -> 800 VDC`, explicit `69 kV AC -> SST -> 800 VDC`, and the MVDC backbone
- `dc_backbone_public_benchmark_model.py`
  - Public-data-only sensitivity workflow using the RTS-GMLC benchmark grid and NREL ESIF IT-power data
- `dc_backbone_public_benefit_analysis.py`
  - Benefit-specific public-data-only screen for efficiency robustness, harmonic sensitivity, voltage sensitivity, N-1 robustness, and dynamic diversity
- `public_time_series_ai_factory.py`
  - Public annual + burst operating study using the NREL ESIF IT-power series and MIT Supercloud labeled AI-job scheduler data
  - Generates a reusable operating library for later common-network, harmonic, and RMS studies
  - The large raw MIT scheduler CSV is intentionally not committed; the repo keeps the smaller labeled metadata files plus the derived operating report
- `public_common_network_td_study.py`
  - Public common-network T&D study placing `Scenario 2(M)` and `Scenario 3(M)` on the same SMART-DS feeder-bank benchmark
  - Reports annualized feeder impact, MIT-derived burst sensitivity, and surviving `N-1` contingencies
- `public_harmonic_frequency_sweep.py`
  - OpenDSS harmonics-mode benchmark on the same SMART-DS feeder-bank benchmark with equal total harmonic current across scenarios
- `public_rms_dynamic_study.py`
  - Public ANDES RMS dynamic benchmark using MIT-derived p95 AI burst steps on a published dynamic case
  - Compares `Scenario 2(M)` and `Scenario 3(M)` under both normal and weakened remote-corridor conditions
- `public_fault_envelope.py`
  - Reduced-order public fault-duty and interruption-timescale screen for the `Scenario 3(M)` MVDC backbone
  - Uses the existing multi-node topology plus public benchmark inductance and breaker-time ranges
- `dc_backbone_multinode_harmonic_spectrum.py`
  - Equal-total harmonic-spectrum benchmark for `Scenario 2(M)` and `Scenario 3(M)` on the public RTS network
- `dc_backbone_dc_transient_model.py`
  - Reduced-order internal MVDC transient screen for `Scenario 3(M)` with explicit local-buffer power and energy limits
- `dc_backbone_multinode_transient_comparison.py`
  - Matched reduced-order transient comparison for `Scenario 2(M)` and `Scenario 3(M)` under the same burst and buffer assumptions
- `dc_backbone_buffer_placement_comparison.py`
  - Equal-budget buffer-placement comparison showing how pooled MVDC buffering changes upstream burst and ramp exposure
- `dc_backbone/`
  - Shared support package for the transient modeling layer
  - Currently includes `transient_common.py` so the transient scripts share one set of patterns, timing assumptions, buffer logic, and helper utilities
- `presentation/`
  - Technical PowerPoint deck, deck generator, and generated slide figures
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
- `sst_explicit_comparison_report.json`
  - Latest machine-readable output for the explicit SST comparator
- `SST_EXPLICIT_COMPARATOR.md`
  - Short note explaining what the explicit SST comparator does and how the three advanced paths rank
- `public_benchmark_report.json`
  - Latest output from the public-data-only benchmark workflow
- `PUBLIC_DATA_UPGRADE.md`
  - Notes on what the public-data-only layer improves and what it still does not prove
- `public_ai_factory_operating_report.json`
  - Machine-readable output for the ESIF + MIT public operating study
- `PUBLIC_AI_FACTORY_OPERATING_STUDY.md`
  - Short note explaining how the public annual and burst operating layers are built and how they should be used
- `public_common_network_td_report.json`
  - Machine-readable output for the SMART-DS feeder-bank common-network T&D study
- `PUBLIC_COMMON_NETWORK_TD_STUDY.md`
  - Short note on the public shared-feeder comparison for `Scenario 2(M)` and `Scenario 3(M)`
- `public_harmonic_frequency_sweep_report.json`
  - Machine-readable output for the OpenDSS harmonics-mode benchmark on the SMART-DS feeder-bank model
- `PUBLIC_HARMONIC_FREQUENCY_SWEEP.md`
  - Short note on the equal-total harmonic-current benchmark on the shared SMART-DS feeder-bank model
- `public_rms_dynamic_report.json`
  - Machine-readable output for the public RMS dynamic benchmark on the IEEE 14-bus ANDES case
- `PUBLIC_RMS_DYNAMIC_STUDY.md`
  - Short note on the RMS dynamic comparison for `Scenario 2(M)` and `Scenario 3(M)` under MIT-derived burst steps
- `public_fault_envelope_report.json`
  - Machine-readable output for the reduced-order public MVDC fault-duty screen
- `PUBLIC_FAULT_ENVELOPE.md`
  - Short note on interruption-timescale and current-rise screening for representative `Scenario 3(M)` fault locations
- `public_benefit_report.json`
  - Latest output from the benefit-specific public-data-only screen
- `PUBLIC_BENEFIT_ANALYSIS.md`
  - Short note on how far the available public datasets support each of the three headline benefits
- `harmonic_spectrum_report.json`
  - Latest equal-total harmonic-spectrum benchmark output
- `HARMONIC_SPECTRUM_ANALYSIS.md`
  - Short note showing why the power-quality benefit persists even when total harmonic injection is normalized
- `dc_transient_report.json`
  - Latest reduced-order internal Scenario `3(M)` transient output
- `DC_TRANSIENT_ANALYSIS.md`
  - Short note summarizing how local buffers change internal MVDC burst behavior
- `multinode_transient_comparison_report.json`
  - Latest matched reduced-order transient comparison output for `Scenario 2(M)` and `Scenario 3(M)`
- `MULTINODE_TRANSIENT_COMPARISON.md`
  - Short note summarizing the direct transient comparison between the SST baseline and the MVDC backbone
- `buffer_placement_report.json`
  - Latest equal-budget buffer-placement comparison output
- `BUFFER_PLACEMENT_ANALYSIS.md`
  - Short note summarizing why pooled MVDC buffer placement can be a stronger Benefit 3 argument than local-only comparison
- `public_data/`
  - Public benchmark inputs used by the public-data-only layers
  - Currently includes:
    - RTS-GMLC bus / branch tables
    - NREL ESIF IT-power data and cached annual bins
    - MIT Supercloud labeled AI-job metadata, scheduler log, and TRES mapping
    - SMART-DS SFO sample feeder files used by the shared-feeder OpenDSS studies
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

Run the explicit SST comparator:

```bash
python3 dc_backbone_sst_explicit_comparison.py --include-traditional
```

Run the public-data-only sensitivity workflow:

```bash
python3 dc_backbone_public_benchmark_model.py
```

Run the public annual + burst operating study:

```bash
python3 public_time_series_ai_factory.py --details
```

Run the public common-network T&D study:

```bash
python3 public_common_network_td_study.py
```

Run the public harmonic frequency-sweep study:

```bash
python3 public_harmonic_frequency_sweep.py --details
```

Run the public RMS dynamic benchmark:

```bash
python3 public_rms_dynamic_study.py
```

Run the public reduced-order MVDC fault envelope:

```bash
python3 public_fault_envelope.py --details
```

Run the benefit-specific public-data-only screen:

```bash
python3 dc_backbone_public_benefit_analysis.py
```

Run the equal-total harmonic-spectrum benchmark:

```bash
python3 dc_backbone_multinode_harmonic_spectrum.py
```

Run the reduced-order Scenario `3(M)` DC transient screen:

```bash
python3 dc_backbone_dc_transient_model.py
```

Run the matched reduced-order transient comparison for `Scenario 2(M)` and `Scenario 3(M)`:

```bash
python3 dc_backbone_multinode_transient_comparison.py
```

Run the equal-budget buffer-placement comparison:

```bash
python3 dc_backbone_buffer_placement_comparison.py
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
