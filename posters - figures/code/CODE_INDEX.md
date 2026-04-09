# Code Index: Figure Generation Scripts

This file maps each Python script to the figure(s) it produces and its role in the poster.

## Figure Generation Scripts

| Script | Output Figure(s) | Poster Section |
|---|---|---|
| `gen_fig_gpu_dynamics.py` | `fig1_gpu_power_trace_and_breakdown.png` | Motivation (GPU power trace + GB200 pie chart) |
| `gen_fig_efficiency_v2.py` | `fig2_cumulative_efficiency.png` | Benefit 1: Cumulative Efficiency |
| `gen_v3_architecture.py` | `fig3_three_scenario_architecture.png` | Proposed Architecture (3-column diagram, v3) |
| `gen_fig_architecture.py` | `fig3b_architecture_v2.png` | Proposed Architecture (earlier v2 version) |
| `gen_v3_power_capacity.py` | `fig4_power_capacity_ac_vs_dc.png` | Benefit 3: Voltage Mgmt & DC-Native Path |
| `gen_fig_harmonics.py` | `fig5_harmonics_pq_comparison.png` | Benefit 2: Harmonics & PQ (not used in final poster, kept for reference) |
| `gen_fig_voltage_mgmt.py` | `fig6_dc_native_integration.png` | Benefit 3: Voltage Mgmt (not used in final poster, kept for reference) |
| `generate_all_figs.py` | 7 earlier poster figures | Earlier poster version (v1) figure set |

## Poster Builder Scripts

| Script | Output | Description |
|---|---|---|
| `build_poster_pptx_v3.py` | `poster_v3.pptx` | Final poster layout builder (v3, reduced text, balanced) |
| `build_poster_pptx_v2.py` | `poster_v2.pptx` | Earlier poster layout builder (v2, more detailed text) |

## How to Regenerate

All scripts require Python 3.11+ with `matplotlib` and `numpy`. The poster builder scripts additionally require `python-pptx`.

```bash
# Install dependencies
pip3 install matplotlib numpy python-pptx

# Generate individual figures
python3 gen_fig_gpu_dynamics.py
python3 gen_fig_efficiency_v2.py
python3 gen_v3_architecture.py
python3 gen_v3_power_capacity.py

# Build the poster PPTX
python3 build_poster_pptx_v3.py
```
