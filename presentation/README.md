# Technical Briefing Deck

This folder contains the technical-audience PowerPoint deck for the MVDC backbone study.

## Included Files

- `dc_subtransmission_backbone_technical_briefing.pptx`
  - generated PowerPoint deck for technical review
- `build_technical_briefing.py`
  - script that rebuilds the deck from the current repo reports and manuscript figures
- `figures/`
  - generated chart images embedded in the deck

## Regenerating the Deck

From the project root:

```bash
MPLCONFIGDIR=/tmp python3 presentation/build_technical_briefing.py
```

The generator reads current values from:

- `source_backed_model_report.json`
- `multinode_campus_report.json`
- `public_benefit_report.json`
- `public_common_network_td_report.json`
- `public_harmonic_frequency_sweep_report.json`
- `public_rms_dynamic_report.json`
- `public_fault_envelope_report.json`

It also reuses the architecture and efficiency figures from `whitepaper/figures/`.
