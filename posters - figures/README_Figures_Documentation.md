# Direct Current (DC) Subtransmission Backbone for AI Factories
## Poster Figures Documentation

This folder contains the scripts and rendered figures used in the poster package for the three-scenario comparison:

1. `Scenario 1`: Traditional AC-centric datacenter power path
2. `Scenario 2`: `69 kV AC -> 800 VDC` perimeter conversion
3. `Scenario 3`: Proposed MVDC backbone

All scenario-dependent numbers should be taken from:

- `/Users/zhengjieyang/Documents/DC2/source_backed_model_report.json`

The current reference case is a `100 MW` delivered IT campus. The latest source-backed model values are:

- `Scenario 1`: `87.55%` full-load efficiency, `124.54 GWh/year` loss, `$11.57M/year` loss cost
- `Scenario 2`: `91.96%` full-load efficiency, `76.55 GWh/year` loss, `$7.11M/year` loss cost
- `Scenario 3`: `95.09%` full-load efficiency, `45.26 GWh/year` loss, `$4.20M/year` loss cost

## 1. GPU Power Trace and Server Power Breakdown

**Output**
- `figures/fig1_gpu_power_trace_and_breakdown.png`

**Script**
- `code/gen_fig_gpu_dynamics.py`

**Purpose**
- Motivation figure showing that AI factories are dynamic loads and that GPUs dominate server power.

**Notes**
- The left subplot is illustrative, not a measured facility waveform.
- The right subplot is a simple component-level power split used for communication, not a calibrated plant model.
- This figure is appropriate for motivation, but it should not be cited as proof of grid response on its own.

## 2. Scenario Efficiency Comparison

**Output**
- `figures/fig2_cumulative_efficiency.png`

**Script**
- `code/gen_fig_efficiency_v2.py`

**Purpose**
- Core quantitative figure for the poster. It compares the three poster scenarios using the current source-backed model report.

**Method**
- The script reads `source_backed_model_report.json`.
- It plots full-load end-to-end efficiency for the three scenarios.
- It annotates annual loss energy and annual loss cost for each scenario.
- It highlights the improvement of `Scenario 3` relative to `Scenario 1`.

**Current numbers shown**
- `Scenario 1`: `87.55%`
- `Scenario 2`: `91.96%`
- `Scenario 3`: `95.09%`
- `Scenario 3 vs Scenario 1`: `+7.53` percentage points, `79.27 GWh/year` lower loss, `$7.36M/year` lower loss cost

**Assessment**
- This is now the most important and most defensible poster figure.
- It is consistent with the current calculation and should remain the anchor figure for the poster and white paper.

## 3. Three-Scenario Architecture Diagram

**Output**
- `figures/fig3_three_scenario_architecture.png`

**Script**
- `code/gen_v3_architecture.py`

**Purpose**
- Visual explanation of how the AC/DC boundary moves across the three scenarios.

**Method**
- The script draws one block-flow chain per scenario.
- The titles and stage-count labels are aligned to the current model framing.

**Current framing**
- `Scenario 1`: Traditional AC-centric, `5` major conversion stages
- `Scenario 2`: `69 kV AC -> 800 Vdc`, `3` major conversion stages
- `Scenario 3`: Proposed MVDC backbone, `3` major conversion stages

**Assessment**
- The scenario naming is now aligned to the poster and model.
- This figure is good for communicating the architectural claim.
- It is qualitative, not a substitute for the quantitative efficiency and OpenDSS results.

## 4. Power Capacity: AC vs DC

**Output**
- `figures/fig4_power_capacity_ac_vs_dc.png`

**Script**
- `code/gen_v3_power_capacity.py`

**Purpose**
- Supporting figure showing conductor-level power-capacity advantage for bipolar DC relative to AC under the same conductor current limit.

**Method**
- Uses standard power expressions for three-phase AC and bipolar DC.
- Compares benchmark voltage classes on the same `500 MCM`, `380 A` conductor assumption.

**Assessment**
- This figure is useful as a supporting argument for a DC backbone.
- It is not scenario-output from the Python model; it is a separate physics-based comparison.
- The text using this figure should stay disciplined. At the `34.5/35 kV` benchmark, the current bars imply about `23%` more power capacity for bipolar DC, not `28%`.

## 5. PowerPoint Poster Builder

**Output**
- `poster_v3.pptx`

**Script**
- `code/build_poster_pptx_v3.py`

**Purpose**
- Assembles the poster into an editable PowerPoint layout.

**Current behavior**
- Pulls current scenario values from `source_backed_model_report.json`
- Uses local figure paths in `figures/`
- Uses `Scenario 1`, `Scenario 2`, and `Scenario 3` wording consistently

**Assessment**
- The builder now matches the current model better than the older poster draft.
- The main poster message is now correctly centered on why the MVDC backbone matters, not just why DC is generally efficient.

## 6. What Is Good and What Still Needs Care

**Good now**
- `fig2_cumulative_efficiency.png` is aligned to the current model and should be used.
- `fig3_three_scenario_architecture.png` now matches the current scenario framing and is suitable for the poster.
- `poster_v3.pptx` text now reflects the latest scenario values instead of stale hardcoded numbers.

**Still needs care**
- `fig1_gpu_power_trace_and_breakdown.png` is only a motivation figure and should be described as illustrative.
- No figure in this folder yet directly visualizes the OpenDSS validation results. That is a gap if the poster or white paper wants to emphasize independent AC-boundary validation.
- The older unused scripts in `code/` still contain legacy assumptions and should not be treated as authoritative unless updated.

## 7. Recommended Next Figure

The next figure that would materially strengthen the poster and white paper is an OpenDSS validation figure with three scenario bars for:

- base AC-boundary feeder loss
- base PCC minimum voltage
- peak feeder loss under the selected dynamic stress case

That would give the poster one clear model-based figure and one clear OpenDSS-based figure, which is a stronger academic pairing than relying on efficiency alone.
