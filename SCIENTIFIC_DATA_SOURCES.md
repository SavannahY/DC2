# Scientific Data Sources for the DC Backbone Model

As of April 8, 2026, these are the strongest public sources I found to support the model.

## How to use this register

- `Tier A`: government, standards, national lab, or official technical specifications
- `Tier B`: peer-reviewed journal or conference paper
- `Tier C`: preprint or vendor technical article; useful, but should not be treated as sole proof

Use `Tier A` and `Tier B` for the main argument. Use `Tier C` mainly for scenario targets, current product direction, or sensitivity bounds.

## 1. Demand and scale assumptions

### 1.1 Global and regional electricity demand from data centers

- `Tier A` IEA, *Energy and AI* (2025)
  - Data centers used about `415 TWh` in `2024`, about `1.5%` of global electricity consumption.
  - Base case reaches about `945 TWh` by `2030`.
  - Accelerated-server electricity consumption is projected to grow about `30%/year`.
  - The United States and China account for nearly `80%` of global growth to 2030.
  - U.S. data-center electricity consumption rises by about `240 TWh` versus 2024.
  - Source:
    - https://www.iea.org/reports/energy-and-ai/energy-demand-from-ai
    - https://www.iea.org/data-and-statistics/data-product/energy-and-ai

- `Tier A` IEA chart notes (2025)
  - Conventional data center capacity considered: `25 MW`
  - Hyperscale data center capacity considered: `100 MW`
  - Largest under-construction data center considered: around `2,000 MW`
  - Largest planned data center considered: `5,000 MW`
  - Source:
    - https://www.iea.org/data-and-statistics/charts/data-centre-electricity-consumption-in-household-electricity-consumption-equivalents-2024

### 1.2 U.S. demand trajectory

- `Tier A` Berkeley Lab / DOE summary of the 2024 U.S. Data Center Energy Usage Report
  - U.S. data centers used `176 TWh` in `2023`
  - Projected `325–580 TWh` by `2028`
  - About `4.4%` of total U.S. electricity in `2023`
  - Expected `6.7–12%` of total U.S. electricity by `2028`
  - Source:
    - https://newscenter.lbl.gov/2025/01/15/berkeley-lab-report-evaluates-increase-in-electricity-demand-from-data-centers/

## 2. Rack, cluster, and campus power anchors

### 2.1 AI-factory rack and scalable-unit power

- `Tier A` NVIDIA DGX SuperPOD GB200 reference architecture, published June 16, 2025 and updated Nov. 19, 2025
  - One Scalable Unit contains `8 DGX GB200 rack systems`
  - One Scalable Unit requires `1.2 MW` TDP
  - Architecture scales to `128+ racks` and `9,216 GPUs`
  - Source:
    - https://docs.nvidia.com/dgx-superpod/reference-architecture-scalable-infrastructure-gb200/latest/dgx-superpod-architecture.html

Modeling note:

- The source does not state per-rack power directly.
- A simple inference from `1.2 MW / 8 racks` is about `150 kW per rack` average across that scalable unit.
- Treat that as an inference, not a quoted fact.

### 2.2 800 VDC rack and facility targets

- `Tier C` NVIDIA technical blog, May 20, 2025
  - NVIDIA states its 800 VDC architecture is intended to support `1 MW IT racks and beyond`, starting in `2027`
  - It states today’s racks exceed `200 kW`
  - It claims a `1 MW` rack at `54 VDC` would require up to `200 kg` of copper busbar
  - It claims `800 VDC` can transmit `85%` more power through the same conductor size than `415 VAC`
  - It claims copper requirements can drop by `45%`
  - It claims up to `5%` end-to-end efficiency gain
  - It states the architecture converts `13.8 kV AC` directly to `800 VDC` at the data-center perimeter
  - It also states energy storage is part of the architecture to address subsecond GPU fluctuations
  - Source:
    - https://developer.nvidia.com/blog/nvidia-800-v-hvdc-architecture-will-power-the-next-generation-of-ai-factories/

Modeling note:

- These are official NVIDIA targets, but they are not independent validation.
- Use them as scenario assumptions or sensitivity bounds, not as proof of performance.

## 3. Conversion-stage efficiency inputs

### 3.1 UPS efficiency curves you can use now

- `Tier A` Schneider Electric Galaxy VX technical specifications, 2025
  - For large 380–440 V UPS systems, normal-operation efficiency is typically around `95–96%`
  - eConversion / ECO modes reach roughly `98.5–99.3%`, depending on load point and rating
  - The spec provides load-point tables at `25%`, `50%`, `75%`, and `100%`
  - Source:
    - https://www.productinfo.schneider-electric.com/galaxyvx_iec/5ac76feb46e0fb00011d4e36/990-5850E%20400%20V%20Technical%20Specifications/English/990-5850N_EN.pdf

- `Tier A` Vertiv PowerUPS 9000, released December 2024 / current product page
  - Double-conversion efficiency up to `97.5%`
  - Dynamic online mode up to `99%`
  - Source:
    - https://www.vertiv.com/en-us/products-catalog/critical-power/uninterruptible-power-supplies-ups/vertiv-powerups-9000/
    - https://www.vertiv.com/en-us/about/news-and-insights/corporate-news/vertiv-introduces-compact-high-power-density-ups-for-large-data-centers-and-other-critical-applications/

These are appropriate for the traditional AC and UPS-based baseline cases.

### 3.2 Rack-level AC/DC shelf efficiency

- `Tier A` Open Compute Project, Delta 18 kW ORv3 power shelf
  - Over `97.5%` AC-DC efficiency
  - `48/50 VDC` output
  - Source:
    - https://www.opencompute.org/products/431/delta-18kw-1ou-open-rack-v3-power-shelf

This is useful as a modern rack-level AC/DC benchmark, but it is not a direct substitute for 800 VDC rack conversion.

### 3.3 Advanced converter research

- `Tier A` OSTI / ARPA-E-funded Berkeley technical report, 2024
  - Reports direct-step-down and series-stacked approaches that achieve component-level efficiency well above `99%`
  - Source:
    - https://www.osti.gov/biblio/2329526

- `Tier B` IEEE / OSTI mirrored paper on AC vs. `380 VDC` data-center distribution, 2018
  - Supports the thesis that reducing conversion stages improves efficiency and reliability
  - Source:
    - https://www.osti.gov/pages/biblio/1482212

- `Tier B` Rothmund et al., `99% Efficient 10 kV SiC-Based 7 kV/400 V DC Transformer for Future Data Centers`, 2019
  - Still one of the most important public benchmarks for MV-to-LV DC transformer efficiency
  - Source:
    - https://doi.org/10.1109/JESTPE.2018.2886139
    - OSTI discovery page showing the citation:
    - https://www.osti.gov/biblio/1974603

### 3.4 Recent 10 kV MVAC to 800 VDC architecture study

- `Tier C` arXiv, January 23, 2026
  - Models a `10 kV MVAC` to `800 V LVDC` chain using a three-phase AC/DC stage and DAB DC/DC stage
  - Reports tight `800 VDC` regulation, lower input-side energy consumption than a UPS baseline, and useful capacitance tradeoff data
  - Source:
    - https://arxiv.org/abs/2601.16502

This is not peer reviewed yet, but it is directly relevant to your proposed architecture and much more recent than older SST literature.

## 4. Dynamic load behavior and grid interaction

### 4.1 AI training load swings are real and grid-relevant

- `Tier C` arXiv, *Power Stabilization for AI Training Datacenters*, August 2025
  - Large AI training jobs span `tens of thousands of GPUs`
  - Synchronous compute and communication phases create large periodic power swings
  - The paper explicitly warns that the frequency spectrum of these swings can align with critical utility frequencies
  - Source:
    - https://arxiv.org/abs/2508.14318

This is the strongest public source I found for why your model must include transient and spectral analysis, not just annual energy loss.

### 4.2 DOE / PNNL now treats data centers as EMT-study-worthy dynamic loads

- `Tier A` PNNL-38817, January 2026
  - Includes exemplar AI-training site-level active-power waveforms and frequency-spectrum analysis
  - Explicitly frames data centers as a grid-study problem requiring EMT-grade models for some conditions
  - Source:
    - https://www.energy.gov/sites/default/files/2026-01/Data_Center_EMT_Models.pdf

This is a very important source because it moves the discussion from opinion to official power-system modeling practice.

### 4.3 Measured oscillation case from a real data-center-rich grid region

- `Tier B` Sustainable Energy, Grids and Networks, Volume 43, 2025
  - Reports measured `14.7–14.8 Hz` oscillations associated with a data-center-rich region in Dominion Energy territory
  - The abstract attributes the root cause to instability of a `10–11 Hz` mode related to the data center UPS system interacting with grid conditions
  - Source:
    - https://www.sciencedirect.com/science/article/abs/pii/S2352467725001171

This is one of the best publicly visible pieces of evidence that data-center power-electronics interactions can create nontrivial grid modes.

### 4.4 Reliability operators now treat large AI loads as a new risk class

- `Tier A` NERC white paper, July 2025
  - Large loads examined range from `several MW` to `several GW`
  - Highlights uncertainty in forecasting and modeling AI-data-center loads
  - Notes concentration of large loads at single points can amplify disturbances
  - Source:
    - https://www.nerc.com/globalassets/who-we-are/standing-committees/rstc/whitepaper-characteristics-and-risks-of-emerging-large-loads.pdf

- `Tier A` NERC Level 2 Industry Recommendation, November 5, 2025
  - Formal industry guidance on large-load interconnection, study, commissioning, and operations
  - Source:
    - https://www.nerc.com/globalassets/programs/bpsa/alerts/2025/nerc-alert-level-2--large-loads.pdf

These sources are useful when you need to justify why a campus-scale AI-factory architecture must consider interconnection behavior, ride-through, and disturbance performance.

## 5. Harmonics and power-quality compliance sources

### 5.1 Current IEEE harmonics standard

- `Tier A` IEEE 519-2022
  - Current harmonics-control standard for PCC steady-state voltage and current distortion limits
  - Source:
    - https://standards.ieee.org/ieee/519/10677/

Modeling note:

- Use this as the compliance framework for the AC-side PCC.
- Your model should produce PCC distortion metrics, not just internal converter metrics.

## 6. Power buffering and fast compensation options

### 6.1 Fast active/reactive support with supercapacitor-backed STATCOM

- `Tier A` Siemens Energy SVC PLUS FS / E-STATCOM product page, current in 2026
  - Installed power `300 MVA`
  - Active power `±200 MW`
  - Reactive power `±300 MVAr`
  - Available energy `400 MJ`
  - Millisecond-class response via supercapacitors and grid-forming control
  - Separate data-center application note states it smooths active-power load patterns at the point of connection
  - Source:
    - https://www.siemens-energy.com/global/en/home/products-services/product/svcplus-frequency-stabilizer.html

This is useful if you want a mitigation case for the AC baseline or hybrid campus design.

### 6.2 Grid-forming BESS for AI data centers

- `Tier C` EPC Power, October 2025 / March 2026
  - Positions grid-forming BESS as a response to extreme load variability and ride-through requirements for AI data centers
  - Mentions deployment blocks from `3 MW` to `100+ MW`
  - Sources:
    - https://www.epcpower.com/insights/solving-ai-data-center-challenges-with-agile-grid-forming-bess
    - https://www.epcpower.com/insights/agile-grid-forming-power-for-data-centers

Use these only as technology-path indicators unless you obtain project-specific test data.

## 7. Facility efficiency and benchmarking metrics

### 7.1 PUE definition and credible benchmark range

- `Tier A` DOE / FEMP Best Practices Guide for Energy-Efficient Data Center Design, 2025
  - Defines PUE formally
  - Notes an average data center PUE of about `1.6`
  - Notes several super-efficient data centers are below `1.1`
  - Cites Uptime Institute’s 2022 large-data-center annual average PUE of `1.55`
  - Source:
    - https://www.osti.gov/servlets/purl/2417618

Use this for facility-level benchmarking only. Do not use PUE as a substitute for electrical-path efficiency.

## 8. What you still cannot get from public sources alone

You will still need measured or vendor-provided data for:

- Centralized MV AC/DC rectifier efficiency versus load
- Isolated DC pod / DC transformer efficiency versus load
- Protection and fault-clearing behavior for MVDC feeders
- Grounding and insulation coordination assumptions
- Busway resistance and ampacity for your actual conductor design
- Real GPU-cluster site-level waveform data for your target workload
- Utility PCC short-circuit strength and interconnection limits
- BESS response limits, thermal derating, and control bandwidth under your chosen topology

These should be treated as `project-specific measured inputs`, not literature values.

## 9. Recommended evidence strategy for the next model revision

Use these sources in three layers:

### Layer A: external hard anchors

- IEA 2025
- Berkeley Lab / DOE 2024-2025
- NERC 2025
- IEEE 519-2022
- PNNL 2026

### Layer B: electrical-architecture proof

- Schneider / Vertiv UPS specs
- OCP power-shelf specs
- OSTI 2024 converter report
- 2018 AC vs 380 VDC paper
- 2019 99% DC transformer paper
- 2026 SST-driven 800 VDC preprint

### Layer C: architecture target and market direction

- NVIDIA 800 VDC blog
- NVIDIA DGX SuperPOD GB200 reference architecture
- Siemens Energy E-STATCOM
- EPC Power BESS material

## 10. Bottom line

The public evidence base is now strong enough to defend:

- large-scale growth in AI-factory electrical demand,
- rising rack and campus power density,
- the need to model dynamic and spectral load behavior,
- the benefit of reducing conversion stages, and
- the importance of centralized power-quality treatment at the PCC.

The public evidence base is not yet strong enough to prove your exact MVDC-backbone efficiency and protection numbers without project-specific converter curves and control data.
