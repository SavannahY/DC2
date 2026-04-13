# Public-Only Modeling Plan for Reviewer Criticisms

Updated: April 11, 2026

This note maps the current harsh-review criticisms to modeling work that can be done with public data only. The goal is not to pretend that public data fully replaces vendor or site data. The goal is to identify which reviewer points can be materially strengthened now, what datasets and tools support that work, and what remains fundamentally blocked without private inputs.

## Current Status in This Repo

Implemented:

- Work Package A: public annual plus burst operating study
- Work Package B: public common-network T&D study
- Work Package C: public harmonic frequency-sweep study
- Work Package D: public RMS dynamic benchmark
- Work Package F: public fault and protection envelope study

Still open:

- Work Package E: narrow EMT study on a public case
- stronger public uncertainty propagation around converter proxies
- tighter public harmonic spectrum families tied to published converter examples

## Bottom Line

Using public data only, the repository can be pushed further in a credible way on:

- realistic annual and sub-minute load profiles,
- common-network interconnection studies,
- harmonic sensitivity and frequency-sweep studies,
- RMS and reduced-order dynamic studies,
- weak-grid and N-1 robustness,
- and fault/protection envelope studies.

Using public data only, the repository still cannot fully close:

- vendor-grade converter efficiency and control fidelity,
- utility-specific PCC compliance claims,
- deployable protection settings,
- or final site-specific investment conclusions.

That means the realistic target is:

- a much stronger public benchmark paper,
- not a deployment-certified design paper.

## Reviewer Criticism to Modeling Response Matrix

| Reviewer criticism | Public-only modeling response | Public datasets / tools | What this would prove |
| --- | --- | --- | --- |
| OpenDSS was overstated as validation | Replace surrogate AC-boundary screens with a shared synthetic transmission or T\&D interconnection study | RTS-GMLC, Texas2k Series25, Texas7k, Texas Combined T\&D, SMART-DS, OpenDSS, pandapower, ANDES | Scenario 2(M) and 3(M) can be compared on the same published network, not only on stylized local feeders |
| Dynamic model is not a true dynamic simulation | Add RMS dynamic studies first, then open EMT if feasible | ANDES, Texas2k Series25 dynamics cases, ACTIVSg2000 dynamics, ParaEMT, PNNL DML report | Whether the centralized AC/DC boundary remains favorable under finite-bandwidth dynamic response and weak-grid disturbances |
| Single-path comparison is too collapsed | Keep multi-node model, then move to public large-scale T\&D or multi-substation studies | SMART-DS, Texas7k-TD, Combined T\&D synthetic dataset, PNNL Data Center Atlas | The backbone value survives when campus and interconnection topology become more realistic |
| Proxy uncertainty could dominate ranking | Replace point assumptions with literature-based public ranges and uncertainty propagation | public converter papers, Rothmund DC transformer paper, generic EMT/load-model reports, Monte Carlo / LHS | Whether the sign of the architecture result is robust to public parameter uncertainty |
| Annual-loss study looked like a fake operating study | Replace flat reference year with public annual and burst traces | MIT Datacenter Challenge / MIT Supercloud dataset, ACTIVSg time series, NREL ESIF, SMART-DS time series | Whether Scenario 3(M) remains favorable under realistic utilization and burst structure |
| Harmonics not proven scientifically | Move from one probe to benchmark spectra and frequency sweeps on public feeders | OpenDSS harmonics mode, SMART-DS feeders, Texas7k-TD, public benchmark spectra families | Whether the centralized AC interface remains less sensitive under equal-total harmonic injection and resonance sweeps |
| Protection / grounding still open | Add public fault-envelope and interruption-feasibility study | open MVDC fault papers, public DCCB test-system paper/data, reduced-order fault-energy model | Whether Scenario 3(M) is at least plausible from a fault-energy and interruption-timescale perspective |

## Public Datasets and Tools Checked

### 1. Annual and fast load profiles

Use these to replace the flat full-load year and simple burst assumptions.

- MIT Datacenter Challenge / MIT Supercloud Dataset
  - official data page: <https://dcc.mit.edu/data/>
  - official GitHub description: <https://github.com/MIT-AI-Accelerator/MIT-Supercloud-Dataset>
  - public paper / citation anchor: Samsi et al., 2021
  - useful for:
    - job-level and node-level power traces,
    - GPU-heavy workload bursts,
    - empirical burst statistics,
    - clustering coherent vs non-coherent block patterns

- ACTIVSg time series data
  - official page: <https://electricgrids.engr.tamu.edu/activsg-time-series-data/>
  - useful for:
    - annual load-shape realism,
    - seasonal and hourly variation,
    - coupling campus studies to realistic transmission load time series

- NREL ESIF public IT-power series
  - already in the repo as the first public empirical layer
  - useful for:
    - generic public annualization,
    - part-load bins,
    - baseline sensitivity when AI-specific traces are not available

- SMART-DS time series
  - official OEDI dataset page: <https://data.openei.org/submissions/2981>
  - useful for:
    - feeder-level time series loads,
    - geographically realistic distribution scenarios,
    - T\&D coupling studies

### 2. Common-network and T\&D benchmark cases

Use these to move beyond stylized feeder cross-checks.

- RTS-GMLC
  - official repository: <https://github.com/GridMod/RTS-GMLC>
  - useful for:
    - transparent baseline transmission screening,
    - mirrored-area studies,
    - branch loading and voltage sensitivity

- Texas2k Series25
  - official page: <https://electricgrids.engr.tamu.edu/texas2k-series25/>
  - useful for:
    - larger synthetic transmission network,
    - updated 2025 load / renewables / batteries,
    - published dynamics models

- Texas 7k
  - official page: <https://electricgrids.engr.tamu.edu/texas7k/>
  - useful for:
    - large synthetic transmission benchmark with transient stability data

- Texas Combined T\&D dataset / Texas7k-TD
  - official pages:
    - <https://electricgrids.engr.tamu.edu/combined-td-synthetic-dataset/>
    - <https://electricgrids.engr.tamu.edu/texas7k-td/>
  - useful for:
    - explicit transmission-to-distribution coupling,
    - feeder-level AC interface placement,
    - multiple campus POIs on realistic public feeders

- SMART-DS
  - official NREL overview: <https://www.nrel.gov/grid/smart-ds>
  - official OEDI dataset page: <https://data.openei.org/submissions/2981>
  - useful for:
    - very detailed OpenDSS distribution feeders,
    - time-series feeder studies,
    - volt/VAR and harmonic resonance sensitivity

### 3. Dynamic and EMT-capable open tools

Use these to move from quasi-static burst screens to true dynamic studies.

- ANDES
  - official docs: <https://docs.andes.app/en/latest/about.html>
  - useful for:
    - RMS / transient-stability-style simulation,
    - weak-grid sweeps,
    - small-signal and time-domain studies on published dynamic cases

- ParaEMT
  - official repo: <https://github.com/NREL/ParaEMT_public>
  - journal paper: <https://doi.org/10.1109/TPWRD.2023.3342715>
  - useful for:
    - open EMT workflows,
    - grid-side fast transient studies,
    - converter-rich synthetic networks

- OpenDSS harmonics mode
  - official EPRI documentation: <https://opendss.epri.com/HarmonicFlowAnalysis.html>
  - useful for:
    - harmonic spectra,
    - frequency sweeps,
    - resonance sensitivity,
    - feeder-level harmonic propagation

### 4. Data-center-specific public anchors

Use these to keep the work tied to actual data-center / AI-factory context rather than generic large-load abstractions.

- PNNL data center EMT model report
  - official page: <https://www.pnnl.gov/publications/electromagnetic-transient-modeling-large-data-centers-grid-level-studies>
  - useful for:
    - model structure guidance,
    - which data-center interfaces should be represented in EMT,
    - study-boundary guidance
  - important limitation:
    - the publication page clearly documents the DML, but does not clearly expose the model files themselves

- PNNL Data Center Atlas
  - official article: <https://www.pnnl.gov/publications/mapping-future-data-centers-new-public-tool-illuminates-whats-next>
  - official dataset entry: <https://www.osti.gov/biblio/2550666>
  - useful for:
    - public geospatial anchoring of candidate AI-factory sites,
    - location realism,
    - identifying realistic infrastructure-rich regions for scenario placement

### 5. Protection and fault references

Use these only for envelope and plausibility studies, not to claim finished protection design.

- MVDC fault detection review / methods
  - open-access review: <https://doi.org/10.3390/app142311052>
  - useful for:
    - identifying measurable fault features,
    - classifying what protection claims are realistic at the current stage

- DC fault protection reviews
  - open review: <https://doi.org/10.1186/s41601-020-00173-9>
  - useful for:
    - mapping the protection problem space,
    - classifying whether a selective, partial, or non-selective protection posture is being implied

- Public DCCB test-system example
  - Zenodo record: <https://zenodo.org/records/15064135>
  - useful for:
    - public benchmark interruption timescale assumptions,
    - reduced-order breaker-duty and fault-energy envelopes

## What We Can Model Next, Public-Only

### Work Package A. Real annual plus burst operating study

Goal:
- replace the current simple annualization with realistic slow and fast demand structure

Data:
- MIT Datacenter Challenge for fast burst statistics
- ACTIVSg or SMART-DS for annual / seasonal load context
- ESIF as fallback baseline

Model:
- fit annual load bins from ACTIVSg or SMART-DS
- fit burst templates from MIT Supercloud GPU-heavy jobs
- create a two-timescale demand model:
  - annual energy bins
  - sub-minute burst library

Outputs:
- annual loss with realistic utilization
- burst frequency distribution
- architecture dominance frequency by operating regime

What reviewer point it addresses:
- annual-loss realism
- dynamic model credibility

### Work Package B. Common-network interconnection study

Goal:
- replace the current surrogate AC-boundary comparison with a shared public network study

Data:
- Texas2k Series25 or Texas7k
- Texas7k-TD or SMART-DS for explicit feeder placement
- Data Center Atlas for realistic candidate-site selection

Model:
- select several substations / feeder groups as candidate campus POIs
- place Scenario 2(M) and Scenario 3(M) on the same public T\&D system
- compute:
  - branch loading,
  - POI voltage sensitivity,
  - weak-grid metrics,
  - N-1 robustness

Outputs:
- same-network comparison across multiple public locations
- location-robustness figures that are no longer tied only to RTS

What reviewer point it addresses:
- OpenDSS overstated as validation
- common-network realism

### Work Package C. Frequency-sweep and benchmark-spectrum harmonic study

Goal:
- move from a single THDv proxy to a more journal-defensible harmonic study

Data:
- SMART-DS or Texas7k-TD feeders
- OpenDSS harmonics mode
- benchmark harmonic spectra families, explicitly documented as public assumptions

Model:
- equal-total current spectra
- multi-order frequency sweeps
- sensitivity to shunt capacitance / feeder impedance / feeder location
- local N-1 harmonic sensitivity

Outputs:
- worst-case harmonic amplification ratios
- resonance frequencies by scenario
- sensitivity surfaces instead of a single probe number

What reviewer point it addresses:
- power-quality claim becomes more scientific
- still not IEEE 519 compliance, but much stronger than topology plus a single probe

### Work Package D. RMS dynamic study on published dynamic grids

Goal:
- move from reduced-order burst screens to a true time-domain power-system dynamic layer

Data:
- Texas2k Series25 or ACTIVSg2000 with dynamics
- ANDES
- MIT Supercloud-derived burst templates for forcing functions

Model:
- represent Scenario 2(M) and Scenario 3(M) as aggregate front-end dynamic loads
- add finite ramp and bandwidth limits to the front ends
- sweep:
  - weak-grid strength,
  - burst amplitude,
  - coherence level,
  - local vs pooled buffering

Outputs:
- source MW ramps,
- voltage excursions,
- damping / recovery time,
- possibly small-signal or forced-oscillation screening

What reviewer point it addresses:
- dynamic model is not a true power-system dynamic simulation

### Work Package E. Open EMT study, if kept narrow

Goal:
- add a public EMT layer for the strongest remaining dynamic criticism

Data / tools:
- ParaEMT
- PNNL DML report for model structure
- published generic inverter / rectifier assumptions

Model:
- narrow scope only:
  - one shared front end,
  - one AC source,
  - one or two representative blocks,
  - short bursts and disturbance events

Outputs:
- fast transient current,
- voltage recovery,
- control / time-step sensitivity

Important limitation:
- this can materially strengthen the paper,
- but without vendor/site data it still should not be described as deployment-grade EMT validation

What reviewer point it addresses:
- strongest response to the dynamic-model criticism

### Work Package F. Public fault and protection envelope study

Goal:
- address the criticism that protection is missing, without pretending to finish the problem

Data:
- public MVDC fault-protection literature
- public breaker test-circuit assumptions

Model:
- reduced-order fault-current rise and energy envelope
- compare required interruption speed and fault energy for:
  - local block faults,
  - backbone segment faults,
  - front-end faults

Outputs:
- fault-energy envelope table,
- required interruption-timescale table,
- architecture discussion of selective vs partial-selective protection

What reviewer point it addresses:
- shows the protection issue is being handled as an engineering question rather than ignored

## Recommended Order

If the constraint is public data only, the best order is:

1. Work Package A: realistic annual plus burst operating study
2. Work Package B: common-network interconnection study
3. Work Package C: stronger harmonic frequency-sweep study
4. Work Package D: RMS dynamic study in ANDES
5. Work Package F: public fault and protection envelope study
6. Work Package E: narrow EMT study

This order is pragmatic:

- A and B directly answer the strongest “too stylized” criticism.
- C makes the PQ claim harder to dismiss.
- D upgrades the dynamic claim from reduced-order to real time-domain simulation.
- F makes the paper less vulnerable on protection.
- E is high value but can consume time quickly, so it should be done after the public benchmark layers are solid.

## What Can Actually Be Claimed After These Public-Only Upgrades

If the work above is completed successfully, the strongest defensible claim becomes:

> Under multiple public benchmark datasets and public dynamic assumptions, the campus-scale MVDC backbone is a more credible architecture than an AC-fed SST plus 800 VDC baseline for centralizing AC-boundary power-quality management, reducing upstream voltage sensitivity, and using pooled buffering to suppress non-coherent campus bursts.

That is stronger than the current white paper.

It is still narrower than:

> the MVDC backbone is proven deployment-ready and superior in all practical conditions.

That stronger statement still needs private or vendor-grade data.

## What I Should Implement Next in This Repo

The next public-only work item with the best return is:

1. `public_emt_screen.py`
   - a narrow public EMT follow-on using ParaEMT or another open EMT-capable workflow
   - focus on one or two benchmark disturbances only, not a full control-design paper

Supporting work that would also improve robustness:

2. wider public uncertainty propagation
   - expand the current proxy sensitivity into Monte Carlo ranges tied to public converter literature

3. stronger public harmonic spectrum families
   - replace generic benchmark spectra with several published AFE / converter spectrum families where openly available

That sequence would answer the remaining strongest reviewer points without requiring private site or vendor data.
