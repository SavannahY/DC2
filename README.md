# DC Subtransmission Backbone for AI Factories

This repository contains the research package for a source-backed evaluation of medium-voltage direct current (MVDC) subtransmission for large AI-factory campuses. It combines:

- a Python architecture model,
- source-tagged assumptions,
- dynamic-load cases for AI factories,
- OpenDSS AC-boundary validation,
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

The modeling package compares these scenarios on:

- end-to-end full-load efficiency,
- annual electrical loss and loss cost,
- simplified dynamic AI-load stress cases,
- and AC-side feeder behavior using OpenDSS at the campus boundary.

## Current Headline Results

At the current `100 MW` delivered IT reference campus:

| Scenario | Full-load efficiency | Annual loss | Annual loss cost |
| --- | ---: | ---: | ---: |
| Scenario 1: Traditional AC-centric | `87.55%` | `124.54 GWh/year` | `$11.57M/year` |
| Scenario 2: `69 kV AC -> 800 VDC` perimeter conversion | `91.96%` | `76.55 GWh/year` | `$7.11M/year` |
| Scenario 3: Proposed MVDC backbone | `95.09%` | `45.26 GWh/year` | `$4.20M/year` |

Relative to `Scenario 1`, the current `Scenario 3` case improves full-load efficiency by `7.53` percentage points and reduces modeled annual electrical losses by `79.27 GWh/year`.

## Multi-Node Campus Results

Using the shared four-block campus topology in `multinode_campus_topology.json`, the apples-to-apples multi-node comparison currently gives:

| Scenario | Network kind | Full-load efficiency | Annual loss | Annual loss cost |
| --- | --- | ---: | ---: | ---: |
| Scenario 1(M): Traditional AC-centric | `69 kV AC` | `81.19%` | `202.97 GWh/year` | `$18.86M/year` |
| Scenario 2(M): `69 kV AC -> 800 VDC` perimeter conversion | `69 kV AC` | `86.24%` | `139.72 GWh/year` | `$12.98M/year` |
| Scenario 3(M): Multi-node MVDC backbone | `69 kV DC` | `91.97%` | `76.51 GWh/year` | `$7.11M/year` |

This multi-node comparison keeps the original `Scenario 1`, `Scenario 2`, and `Scenario 3` model untouched while adding a more explicit campus topology in which multiple data-center blocks are connected on the same backbone.

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
- `SCIENTIFIC_DATA_SOURCES.md`
  - Public-source register and traceability notes
- `MODEL_RESULTS_MEMO.md`
  - Standalone technical memo summarizing the current source-backed results
- `posters - figures/`
  - Figure-generation scripts, rendered figures, and editable poster outputs
- `whitepaper/`
  - White paper source files, bibliography, renderer, embedded figures, and exported PDF/DOCX outputs

## Running the Model

Basic run:

```bash
python3 dc_backbone_model.py
```

Detailed run:

```bash
python3 dc_backbone_model.py --details
```

Run with OpenDSS AC-boundary validation:

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
