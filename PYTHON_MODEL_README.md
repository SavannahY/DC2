# Python Model README

## What this is

`dc_backbone_model.py` is a comparison model for the poster thesis:

- Traditional AC-centric architecture
- NVIDIA-style `69 kV AC -> 800 VDC` perimeter-conversion architecture
- Proposed MVDC backbone architecture

It is currently good for:

- stage-by-stage efficiency accounting
- conductor loss comparison
- annual loss and energy-cost comparison
- an explicit architecture scorecard that helps frame the innovation claim
- dynamic AI-load stress cases using source-backed reference frequencies
- native-buffer power and energy sizing at the architecture's natural DC or AC support point
- optional OpenDSS quasi-static AC-side validation for feeder current, feeder loss, source swing, and PCC voltage

It is not yet a full EMT, protection, or hardware-in-the-loop model.

## Files

- [dc_backbone_model.py](/Users/zhengjieyang/Documents/DC2/dc_backbone_model.py)
- [scientific_assumptions_v1.json](/Users/zhengjieyang/Documents/DC2/scientific_assumptions_v1.json)
- [base_case_assumptions.json](/Users/zhengjieyang/Documents/DC2/base_case_assumptions.json)
- [MODEL_PLAN_DC_BACKBONE.md](/Users/zhengjieyang/Documents/DC2/MODEL_PLAN_DC_BACKBONE.md)
- [SCIENTIFIC_DATA_SOURCES.md](/Users/zhengjieyang/Documents/DC2/SCIENTIFIC_DATA_SOURCES.md)

## Run

Base case:

```bash
python3 /Users/zhengjieyang/Documents/DC2/dc_backbone_model.py
```

Analytical model plus OpenDSS AC-side validation:

```bash
python3 /Users/zhengjieyang/Documents/DC2/dc_backbone_model.py --run-opendss
```

This now defaults to:

- [scientific_assumptions_v1.json](/Users/zhengjieyang/Documents/DC2/scientific_assumptions_v1.json)

With full-load stage breakdown:

```bash
python3 /Users/zhengjieyang/Documents/DC2/dc_backbone_model.py --details
```

Override the delivered IT load:

```bash
python3 /Users/zhengjieyang/Documents/DC2/dc_backbone_model.py --it-load-mw 300
```

Override the electricity price:

```bash
python3 /Users/zhengjieyang/Documents/DC2/dc_backbone_model.py --energy-price-per-mwh 120
```

Export the full report:

```bash
python3 /Users/zhengjieyang/Documents/DC2/dc_backbone_model.py --save-json /Users/zhengjieyang/Documents/DC2/model_report.json
```

Export the full report with OpenDSS validation included:

```bash
python3 /Users/zhengjieyang/Documents/DC2/dc_backbone_model.py --run-opendss --save-json /Users/zhengjieyang/Documents/DC2/source_backed_model_report.json
```

Write the standalone coauthor memo:

```bash
python3 /Users/zhengjieyang/Documents/DC2/dc_backbone_model.py --write-memo /Users/zhengjieyang/Documents/DC2/MODEL_RESULTS_MEMO.md
```

Write the standalone coauthor memo with OpenDSS validation included:

```bash
python3 /Users/zhengjieyang/Documents/DC2/dc_backbone_model.py --run-opendss --write-memo /Users/zhengjieyang/Documents/DC2/MODEL_RESULTS_MEMO.md
```

## OpenDSS note

The OpenDSS path is intentionally limited to the upstream AC boundary:

- It simulates the `69 kV` feeder or a short substation-side AC stub, depending on the architecture.
- It represents the downstream AI-factory electrical demand as an equivalent AC load at that boundary.
- It validates source power swing, feeder current, feeder loss, and PCC voltage behavior under the same dynamic AI-load envelopes used in the analytical model.
- It does not simulate the internal MVDC backbone or the `800 VDC` facility distribution in EMT detail.

Install the optional dependency once:

```bash
python3 -m pip install --user opendssdirect.py
```

## What to replace first

The current assumptions are partly source-backed and partly engineering proxies. Replace these first:

1. Efficiency curves for each converter and transformer
2. Voltage class, conductor length, and resistance assumptions
3. Buffer placement and control bandwidth assumptions
4. Energy price / tariff assumptions
5. Architecture path details for your target campus

## What to add next

The next high-value upgrades are:

1. Time-series transient load traces for GPU synchronization events
2. Project-specific BESS placement and sizing logic
3. PF / THD calculations tied to PCC requirements
4. CAPEX and lifecycle economics
5. Protection and grounding constraints

## Modeling note

Treat the poster headline values as hypotheses to test, not values to hard-code. This script is structured so you can replace illustrative assumptions with traceable evidence and see whether the thesis still holds.
