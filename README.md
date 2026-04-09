# DC Subtransmission Backbone for AI Factories

This repository contains the source-backed modeling, figure-generation code, poster assets, and white paper package for the MVDC backbone study for AI factories.

## Main contents

- `dc_backbone_model.py`
  - Python comparison model for the three scenarios
  - includes steady-state calculations, dynamic-load cases, and optional OpenDSS validation
- `scientific_assumptions_v1.json`
  - source-tagged assumptions used by the model
- `source_backed_model_report.json`
  - latest machine-readable results generated from the model
- `SCIENTIFIC_DATA_SOURCES.md`
  - public-source register for the main assumptions
- `MODEL_RESULTS_MEMO.md`
  - concise technical memo summarizing the current results
- `posters - figures/`
  - figure-generation scripts, rendered figures, and editable poster outputs
- `whitepaper/`
  - LaTeX manuscript, bibliography, renderer, figures, and exported PDF/DOCX outputs

## Scenario framing

The current work compares three scenarios:

1. `Scenario 1`: Traditional AC-centric campus distribution
2. `Scenario 2`: `69 kV AC -> 800 VDC` perimeter conversion
3. `Scenario 3`: Proposed MVDC backbone

## Reproducing the model

Basic run:

```bash
python3 dc_backbone_model.py
```

Detailed run:

```bash
python3 dc_backbone_model.py --details
```

Run with OpenDSS validation:

```bash
python3 dc_backbone_model.py --run-opendss
```

Write the technical memo:

```bash
python3 dc_backbone_model.py --write-memo MODEL_RESULTS_MEMO.md
```

## White paper outputs

The current public-facing white paper files are:

- `whitepaper/dc_subtransmission_backbone_position_paper.tex`
- `whitepaper/dc_subtransmission_backbone_position_paper.pdf`
- `whitepaper/dc_subtransmission_backbone_position_paper.docx`

The PDF and DOCX can be regenerated with:

```bash
python3 whitepaper/render_whitepaper_outputs.py
```
