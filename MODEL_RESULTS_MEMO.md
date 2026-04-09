# Standalone Technical Results Memo for the DC Backbone Model

<!-- source_ids: white_paper_local_2026, iea_2025_energy_ai, nvidia_dgx_superpod_gb200_2025, nvidia_800vdc_blog_2025, user_specified_69kv_scenario_2026 -->
## 1. Title and model status

This memo summarizes the current source-backed model for `/Users/zhengjieyang/Documents/DC2` using `scientific_assumptions_v1.json` as the assumptions file.

Model status: `source_backed_v1`.

Model caution: This file mixes public-source values with explicitly labeled engineering proxies where public data is not available. Dynamic frequencies are source-backed; dynamic amplitudes are sensitivity cases, not measured universal constants. The advanced architectures use an NVIDIA-style 800 VDC downstream structure, while the 69 kV subtransmission assumption is a user-specified scenario input rather than a direct NVIDIA-published value.

In the current scenario, the two forward-looking architectures use an NVIDIA-style `800 VDC` downstream structure. The campus-side subtransmission assumption is set to `69.0 kV AC` for the AC-fed advanced case and `69.0 kV DC` for the proposed MVDC backbone. That `69 kV` assumption is a local scenario choice, not a direct NVIDIA-published voltage value.

The memo is intended for coauthors. It is reader-facing and does not require direct use of the terminal, raw JSON, or the Python source.

<!-- source_ids: iea_2025_energy_ai, eia_electricity_monthly_2026_01, nvidia_dgx_superpod_gb200_2025, pnnl_38817_2026, segan_2025_14_8hz -->
## 2. Executive findings

The reference campus is `100.0 MW` of delivered IT load. That corresponds to about `83.3` NVIDIA scalable units and about `667` racks.

The proposed MVDC backbone has the strongest steady-state result in the current model at `95.09%` full-load efficiency, versus `87.55%` for the least-efficient baseline.

At the current U.S. industrial electricity-price anchor of `$92.9/MWh`, the modeled annual electrical-loss cost spans from `$11,569,463` in the traditional AC case to `$4,204,934` in the proposed MVDC case.

The model also treats AI factories as dynamic loads. It evaluates a representative `1.0 Hz` reference case inside the PNNL `0.1-5 Hz` study band and a measured `14.8 Hz` case from a data-center oscillation paper. These cases show that dynamic behavior must be modeled explicitly, not inferred from annual energy numbers alone.

Dynamic-amplitude values in this memo are sensitivity cases. They are not presented as universal measured constants for all AI workloads.

<!-- source_ids: white_paper_local_2026, nvidia_800vdc_blog_2025, user_specified_69kv_scenario_2026 -->
## 3. Compared architectures

| Architecture | Description | Native buffer anchor |
| --- | --- | --- |
| Traditional AC-centric | AC remains the dominant campus distribution domain and power quality ownership is distributed across multiple downstream AC interfaces. This baseline is intentionally not modeled as an 800 VDC data-center architecture. | LV AC distribution |
| NVIDIA-style 69 kV AC -> 800 VDC perimeter conversion | This comparison case is modeled as a direct 69 kV AC to 800 VDC perimeter-conversion path feeding the 800 VDC facility side, which more literally matches the NVIDIA-style architecture direction than the earlier AC-fed pod proxy. | 800 VDC facility bus |
| Proposed MVDC backbone | The AC/DC boundary moves to a common subtransmission front end. Downstream distribution is DC-native with an NVIDIA-style 800 VDC facility bus, while harmonics/PF are handled once at the grid interface. In this scenario, the subtransmission backbone voltage is set to 69 kV. | MVDC backbone |

<!-- source_ids: iea_2025_energy_ai, eia_electricity_monthly_2026_01, nvidia_dgx_superpod_gb200_2025, schneider_galaxy_vx_2025, ocp_delta_orv3, rothmund_2019_dc_transformer, pnnl_38817_2026, segan_2025_14_8hz, white_paper_local_2026 -->
## 4. Source-backed input anchors

The current assumptions mix directly sourced values, source-anchored proxies, local white-paper assumptions, and project-specific gaps that still require measured data.

| Classification | Input | Current basis | Source IDs |
| --- | --- | --- | --- |
| Directly source-backed | Reference campus size | 100.0 MW IT | iea_2025_energy_ai |
| Directly source-backed | Electricity price anchor | $92.9/MWh | eia_electricity_monthly_2026_01 |
| Directly source-backed | NVIDIA scalable-unit TDP | 1.2 MW per scalable unit | nvidia_dgx_superpod_gb200_2025 |
| Directly source-backed | Racks per scalable unit | 8 | nvidia_dgx_superpod_gb200_2025 |
| Directly source-backed | Advanced data-center downstream bus | 800 VDC pod / facility bus structure in the forward-looking architectures | nvidia_800vdc_blog_2025 |
| Directly source-backed | Dynamic frequency case: electromechanical_band_reference | 1.0 Hz | pnnl_38817_2026, arxiv_2508_14318 |
| Directly source-backed | Dynamic frequency case: measured_14_8hz_case | 14.8 Hz | segan_2025_14_8hz, pnnl_38817_2026 |
| Source-anchored proxy | double_conversion_ups | Approximate 415 V normal-operation efficiency points from the Schneider Galaxy VX technical specifications. | schneider_galaxy_vx_2025 |
| Source-anchored proxy | server_psu_acdc | Modern AC-DC shelf benchmark anchored to OCP Delta's >97.5% figure at rated conditions. | ocp_delta_orv3 |
| Source-anchored proxy | perimeter_69kvac_to_800vdc | Engineering proxy for a direct 69 kV AC to 800 VDC perimeter-conversion stage in an NVIDIA-style 800 VDC facility architecture. | nvidia_800vdc_blog_2025, rothmund_2019_dc_transformer, user_specified_69kv_scenario_2026 |
| Source-anchored proxy | rack_node_dcdc | Engineering proxy for high-power rack/node DC-DC conversion anchored to modern high-efficiency rack power-conversion practice. | ocp_delta_orv3 |
| Source-anchored proxy | central_mv_acdc | Engineering proxy for centralized subtransmission AC/DC front end anchored to the 800 VDC perimeter-conversion concept and high-efficiency power-conversion literature. In this scenario, the subtransmission voltage is user-set to 69 kV. | nvidia_800vdc_blog_2025, rothmund_2019_dc_transformer, user_specified_69kv_scenario_2026 |
| Source-anchored proxy | isolated_dc_pod | Anchored to 99% DC-transformer-class literature and used as a proxy for an isolated DC pod / DC transformer. | rothmund_2019_dc_transformer |
| Local white-paper assumption | MVDC backbone topology | Common MV AC/DC front end feeding an MVDC campus backbone and isolated DC pods. | white_paper_local_2026 |
| Local scenario assumption | Subtransmission-side voltage | 69.0 kV for the MVDC backbone and 69.0 kV for the AC-fed advanced case. | user_specified_69kv_scenario_2026 |
| Local white-paper assumption | Native buffer anchor locations | Architecture-specific support points selected to reflect the intended electrical domain. | white_paper_local_2026 |
| Local scenario assumption | OpenDSS AC-side surrogate boundary | Uses the first modeled AC feeder when present; otherwise a 20.0 m centralized-front-end AC stub with X/R proxy 1.0. | opendss_epri_2026, opendss_quasi_static_local_2026 |
| Project-specific gap | MV AC/DC rectifier efficiency-vs-load curves | Need measured or vendor-provided curves for the exact front-end design. |  |
| Project-specific gap | Isolated DC pod / DC transformer efficiency curves | Need measured or vendor-provided partial-load data for the chosen topology. |  |
| Project-specific gap | GPU-cluster waveform amplitudes | Dynamic amplitudes in the model are sensitivity cases, not universal measured constants. |  |
| Project-specific gap | MVDC protection and grounding behavior | Need equipment-specific fault-clearing, grounding, and insulation data. |  |
| Project-specific gap | Utility PCC strength and compliance limits | Need interconnection-specific short-circuit strength, THD limits, and study criteria. |  |
| Project-specific gap | Utility-grade 69 kV line and source model | Need site-specific R/X, zero-sequence, and source Thevenin data to replace the current surrogate feeder. |  |

<!-- source_ids: iea_2025_energy_ai, eia_electricity_monthly_2026_01, schneider_galaxy_vx_2025, ocp_delta_orv3, rothmund_2019_dc_transformer, white_paper_local_2026 -->
## 5. Steady-state results

| Architecture | Full-load efficiency | Annual loss (GWh) | Annual loss cost (USD) | AC harmonic-injection points | Major conversion stages |
| --- | --- | --- | --- | --- | --- |
| Traditional AC-centric | 87.55% | 124.54 | $11,569,463 | 4 | 5 |
| NVIDIA-style 69 kV AC -> 800 VDC perimeter conversion | 91.96% | 76.55 | $7,111,571 | 1 | 3 |
| Proposed MVDC backbone | 95.09% | 45.26 | $4,204,934 | 1 | 3 |

Interpretation:

- The current model supports the thesis that moving the AC/DC boundary upstream reduces cumulative conversion loss.
- The proposed MVDC backbone also has the fewest modeled AC harmonic-injection points and the fewest major conversion stages.
- These steady-state results are only as strong as the converter-curve and conductor assumptions used to produce them.

<!-- source_ids: pnnl_38817_2026, arxiv_2508_14318, segan_2025_14_8hz -->
## 6. Dynamic AI-load results

AI factories are modeled here as dynamic electrical loads because public sources now show that large AI-training sites can exhibit sustained periodic fluctuations and can interact with grid-relevant oscillatory modes.

| Case | Frequency | Basis |
| --- | --- | --- |
| electromechanical_band_reference | 1.0 Hz | Representative test point inside the 0.1-5 Hz range that PNNL identifies as relevant to positive-sequence stability studies. This is a modeling reference point, not a directly measured universal AI-workload frequency. |
| measured_14_8hz_case | 14.8 Hz | Measured oscillation frequency reported in a data-center-rich Dominion Energy region. PNNL cites 5-60 Hz as the main EMT-relevant band for forced oscillation studies. |

| Architecture | Case | Oscillation frequency (Hz) | IT amplitude | Raw PCC peak (MW) | Raw PCC peak (% of base input) | Native buffer (MW) | Native buffer (kWh) |
| --- | --- | --- | --- | --- | --- | --- | --- |
| Traditional AC-centric | electromechanical_band_reference | 1.0 | 5.0% | 5.71 | 5.00% | 5.28 | 0.23 |
| Traditional AC-centric | electromechanical_band_reference | 1.0 | 10.0% | 11.45 | 10.02% | 10.55 | 0.47 |
| Traditional AC-centric | electromechanical_band_reference | 1.0 | 15.0% | 17.19 | 15.05% | 15.83 | 0.70 |
| Traditional AC-centric | measured_14_8hz_case | 14.8 | 2.0% | 2.27 | 1.98% | 2.11 | 0.01 |
| Traditional AC-centric | measured_14_8hz_case | 14.8 | 5.0% | 5.71 | 5.00% | 5.28 | 0.02 |
| Traditional AC-centric | measured_14_8hz_case | 14.8 | 10.0% | 11.45 | 10.02% | 10.55 | 0.03 |
| NVIDIA-style 69 kV AC -> 800 VDC perimeter conversion | electromechanical_band_reference | 1.0 | 5.0% | 5.44 | 5.00% | 5.22 | 0.23 |
| NVIDIA-style 69 kV AC -> 800 VDC perimeter conversion | electromechanical_band_reference | 1.0 | 10.0% | 10.91 | 10.03% | 10.45 | 0.46 |
| NVIDIA-style 69 kV AC -> 800 VDC perimeter conversion | electromechanical_band_reference | 1.0 | 15.0% | 16.38 | 15.06% | 15.67 | 0.69 |
| NVIDIA-style 69 kV AC -> 800 VDC perimeter conversion | measured_14_8hz_case | 14.8 | 2.0% | 2.16 | 1.98% | 2.09 | 0.01 |
| NVIDIA-style 69 kV AC -> 800 VDC perimeter conversion | measured_14_8hz_case | 14.8 | 5.0% | 5.44 | 5.00% | 5.22 | 0.02 |
| NVIDIA-style 69 kV AC -> 800 VDC perimeter conversion | measured_14_8hz_case | 14.8 | 10.0% | 10.91 | 10.03% | 10.45 | 0.03 |
| Proposed MVDC backbone | electromechanical_band_reference | 1.0 | 5.0% | 5.24 | 4.98% | 5.14 | 0.23 |
| Proposed MVDC backbone | electromechanical_band_reference | 1.0 | 10.0% | 10.53 | 10.01% | 10.27 | 0.45 |
| Proposed MVDC backbone | electromechanical_band_reference | 1.0 | 15.0% | 15.82 | 15.04% | 15.41 | 0.68 |
| Proposed MVDC backbone | measured_14_8hz_case | 14.8 | 2.0% | 2.07 | 1.97% | 2.05 | 0.01 |
| Proposed MVDC backbone | measured_14_8hz_case | 14.8 | 5.0% | 5.24 | 4.98% | 5.14 | 0.02 |
| Proposed MVDC backbone | measured_14_8hz_case | 14.8 | 10.0% | 10.53 | 10.01% | 10.27 | 0.03 |

<!-- source_ids: opendss_epri_2026, opendss_quasi_static_local_2026, white_paper_local_2026 -->
OpenDSS AC-side validation:

A complementary OpenDSS quasi-static study was run for the AC source, the 69 kV feeder or substation stub, and the equivalent AI-factory demand seen at that AC boundary. This validation does not simulate the internal MVDC or 800 VDC network in EMT detail; it tests the feeder-side voltage, current, and loss consequences of each architecture's upstream demand envelope.

| Architecture | Case | Oscillation frequency (Hz) | IT amplitude | OpenDSS source peak (MW) | Max PCC voltage swing from base | Peak feeder loss (MW) | Peak line current (A) |
| --- | --- | --- | --- | --- | --- | --- | --- |
| Traditional AC-centric | electromechanical_band_reference | 1.0 | 15.0% | 17.25 | 0.50% | 0.259 | 1161 |
| Traditional AC-centric | measured_14_8hz_case | 14.8 | 10.0% | 11.49 | 0.33% | 0.236 | 1109 |
| NVIDIA-style 69 kV AC -> 800 VDC perimeter conversion | electromechanical_band_reference | 1.0 | 15.0% | 16.45 | 0.47% | 0.234 | 1104 |
| NVIDIA-style 69 kV AC -> 800 VDC perimeter conversion | measured_14_8hz_case | 14.8 | 10.0% | 10.96 | 0.31% | 0.213 | 1054 |
| Proposed MVDC backbone | electromechanical_band_reference | 1.0 | 15.0% | 15.84 | 0.42% | 0.005 | 1064 |
| Proposed MVDC backbone | measured_14_8hz_case | 14.8 | 10.0% | 10.54 | 0.28% | 0.005 | 1016 |

Limitations:

- The `1.0 Hz` case is a modeling reference point inside the PNNL low-frequency study band. It is not claimed as a measured universal AI-workload frequency.
- The `14.8 Hz` case is a measured data-center oscillation reference, but the model does not claim that all AI factories oscillate at this exact frequency.
- Dynamic amplitudes remain sensitivity cases because publicly available literature does not yet provide a universal MW-swing percentage for all AI workloads.
- The dynamic module estimates raw PCC power ripple and native-buffer requirements. It does not yet model control-loop dynamics, impedance interactions, harmonics, or EMT-grade converter behavior.
- The OpenDSS layer is an RMS/quasi-static AC-boundary study. It validates feeder-side power flow, current, loss, and voltage behavior, but it is not a full EMT simulation of converter controls or MVDC protection.

<!-- source_ids: white_paper_local_2026, pnnl_38817_2026, iea_2025_energy_ai -->
## 7. What is proven vs not yet proven

What the current model supports:

- The proposed MVDC backbone has the best steady-state electrical-path efficiency in the current source-backed model.
- The proposed MVDC backbone centralizes AC-side interaction and reduces modeled AC harmonic-injection points.
- AI-factory power architecture should be evaluated under dynamic-load conditions, not only annual energy-loss accounting.
- The OpenDSS AC-side validation independently confirms lower feeder current, feeder loss, and PCC-voltage swing when the AC boundary is pushed upstream to the centralized front end.

What the current model does not yet prove externally:

- Exact MVDC protection, fault-clearing, and grounding behavior.
- Exact harmonic and power-factor performance at the PCC.
- Exact dynamic attenuation benefits of one architecture over another under real converter-control designs.
- Vendor-accurate partial-load efficiency for the actual MV rectifier and isolated DC pod hardware that would be deployed.

<!-- source_ids: pnnl_38817_2026, segan_2025_14_8hz, white_paper_local_2026 -->
## 8. Next data needed

- Measured or vendor-provided efficiency-versus-load curves for the centralized MV AC/DC front end.
- Measured or vendor-provided efficiency-versus-load curves for the isolated DC pod / DC transformer stage.
- Project waveform data for GPU-cluster power swings, including amplitude, spectrum, duty cycle, and workload dependence.
- Utility-specific PCC data: short-circuit strength, harmonic limits, flicker requirements, and study expectations.
- Protection, grounding, insulation, and fault-isolation data for the targeted MVDC backbone implementation.
- BESS and buffer control bandwidth, thermal limits, and siting assumptions for campus-specific dynamic mitigation studies.

<!-- source_ids: iea_2025_energy_ai, eia_electricity_monthly_2026_01, nvidia_dgx_superpod_gb200_2025, nvidia_800vdc_blog_2025, opendss_epri_2026, opendss_quasi_static_local_2026, pnnl_38817_2026, arxiv_2508_14318, segan_2025_14_8hz, schneider_galaxy_vx_2025, ocp_delta_orv3, rothmund_2019_dc_transformer, white_paper_local_2026, user_specified_69kv_scenario_2026 -->
## 9. Reference appendix

| Source ID | Title | Date | Tier | URL | How it is used in the model |
| --- | --- | --- | --- | --- | --- |
| iea_2025_energy_ai | IEA Energy and AI | 2025-04-10 | Tier A | https://www.iea.org/reports/energy-and-ai/energy-demand-from-ai | Campus size anchor and AI/data-center demand context. |
| eia_electricity_monthly_2026_01 | EIA Electricity Monthly Update with Data for January 2026 | 2026-03-24 | Tier A | https://www.eia.gov/electricity/monthly/update/end-use.php | U.S. industrial electricity price anchor for annual loss-cost conversion. |
| nvidia_dgx_superpod_gb200_2025 | NVIDIA DGX SuperPOD GB200 Reference Architecture | 2025-11-19 | Tier A | https://docs.nvidia.com/dgx-superpod/reference-architecture-scalable-infrastructure-gb200/latest/dgx-superpod-architecture.html | Scalable-unit and rack-count context for the 100 MW reference campus. |
| nvidia_800vdc_blog_2025 | NVIDIA 800 VDC Architecture Will Power the Next Generation of AI Factories | 2025-05-20 | Tier C | https://developer.nvidia.com/blog/nvidia-800-v-hvdc-architecture-will-power-the-next-generation-of-ai-factories/ | 800 VDC / 13.8 kV architecture direction and conductor-voltage context. |
| opendss_epri_2026 | OpenDSS Overview | 2026-04-08 | Tier A | https://opendss.epri.com/OpenDSSOverview.html | OpenDSS method basis for RMS/quasi-static feeder studies. |
| opendss_quasi_static_local_2026 | Local OpenDSS AC-boundary validation setup | 2026-04-08 | Local | file:///Users/zhengjieyang/Documents/DC2/dc_backbone_model.py | Local AC-boundary surrogate choices used for the OpenDSS validation setup. |
| pnnl_38817_2026 | Electromagnetic Transient Modeling of Data Centers | 2026-01-01 | Tier A | https://www.energy.gov/sites/default/files/2026-01/Data_Center_EMT_Models.pdf | Dynamic-load study framing and the 0.1-5 Hz versus 5-60 Hz modeling bands. |
| arxiv_2508_14318 | Power Stabilization for AI Training Datacenters | 2025-08-20 | Tier C | https://arxiv.org/abs/2508.14318 | AI-training load fluctuation motivation and need for dynamic-load modeling. |
| segan_2025_14_8hz | Understanding the inception of 14.7 Hz oscillations emerging from a data center | 2025-01-01 | Tier B | https://www.sciencedirect.com/science/article/abs/pii/S2352467725001171 | Measured 14.8 Hz data-center oscillation reference case. |
| schneider_galaxy_vx_2025 | Galaxy VX Technical Specifications | 2025-07-01 | Tier A | https://www.productinfo.schneider-electric.com/galaxyvx_iec/5ac76feb46e0fb00011d4e36/990-5850E%20400%20V%20Technical%20Specifications/English/990-5850N_EN.pdf | Large UPS normal-operation efficiency anchor. |
| ocp_delta_orv3 | Delta 18kW 1OU Open Rack v3 Power Shelf | 2026-01-01 | Tier A | https://www.opencompute.org/products/431/delta-18kw-1ou-open-rack-v3-power-shelf | Modern AC-DC conversion efficiency anchor for rack/power-shelf class hardware. |
| rothmund_2019_dc_transformer | 99% Efficient 10 kV SiC-Based 7 kV/400 V DC Transformer for Future Data Centers | 2019-01-01 | Tier B | https://doi.org/10.1109/JESTPE.2018.2886139 | High-efficiency DC transformer anchor for isolated DC stages. |
| white_paper_local_2026 | Direct Current Subtransmission Backbone for AI Factories white paper | 2026-04-07 | Local | file:///Users/zhengjieyang/Documents/DC2/DC_Subtransmission_Backbone_for_AI_Factories_White_Paper_scrubbed.docx | Local MVDC backbone architecture assumptions and intended functional allocation. |
| user_specified_69kv_scenario_2026 | User-specified 69 kV subtransmission scenario | 2026-04-08 | Local | local-conversation | User-requested 69 kV subtransmission scenario used for the campus-side advanced-case voltage assumptions. |
