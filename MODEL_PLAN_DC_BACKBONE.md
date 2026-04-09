# Model Plan: DC Subtransmission Backbone for AI Factories

## Objective

Build a defensible model that tests the poster's central claim:

Moving the main AC/DC boundary upstream to a centralized MVDC interface, then distributing power on a DC backbone to isolated DC pods and an 800 VDC facility bus, produces measurable system-level gains versus:

1. Traditional AC-centric architecture
2. AC-fed SST / 800 VDC pod architecture

The model should prove four things:

1. It saves energy and operating cost
2. It improves power quality ownership and compliance
3. It simplifies voltage/reactive-power coordination and DC-native resource integration
4. It is an architectural innovation, not just a better component

## Core Hypotheses

H1. End-to-end cumulative efficiency improves because major conversion stages are removed or consolidated.

H2. Harmonics and PF management improve because AC-side power quality is treated once at the common MV AC/DC front end instead of at many downstream AC interfaces.

H3. Backbone voltage control is simpler and more scalable because reactive-power flow is eliminated from downstream feeders and DC-native resources connect without unnecessary reconversion.

H4. The innovation is architectural: it changes the location of the AC/DC boundary and reallocates functions across the campus, producing system-level gains that cannot be achieved by optimizing only the last conversion stage.

## Minimum Comparison Set

Model these three architectures side by side:

### A. Traditional AC-centric

Utility MV AC -> MV/LV transformer -> UPS / switchgear / PDU -> server PSU AC/DC -> board DC/DC

### B. AC-fed SST / 800 VDC pod

Utility MV AC -> grid-side AC/DC -> HF isolated link / SST -> 800 VDC bus -> rack/node DC/DC

### C. Proposed MVDC backbone

Utility MV AC -> centralized MV AC/DC front end -> MVDC backbone -> isolated DC pod / DC transformer -> 800 VDC bus -> rack/node DC/DC

## Data You Need

Split the inputs into seven blocks.

### 1. Electrical topology data

- One-line diagram for each candidate architecture
- Voltage levels at each stage
- Number of stages and their order
- Rated MW per campus, hall, pod, rack
- Feeder lengths and conductor sizes
- Protection zones and isolation boundaries

### 2. Converter and transformer performance data

- Efficiency versus load curve for each converter or transformer, not just nameplate peak efficiency
- Standby / no-load losses
- Partial-load behavior
- Power density and thermal losses
- PF and THD performance at AC interfaces
- Fault current limits / protection response assumptions

Typical devices:

- Utility transformer
- Centralized rectifier / AC-DC front end
- SST or isolated DC transformer
- UPS if present
- Rack or board-level DC/DC stages
- BESS bidirectional converters where applicable

### 3. Conductor and distribution data

- Cable resistance by conductor type, gauge, and length
- Ampacity limits
- Busway losses
- Voltage drop limits
- AC and DC conductor utilization assumptions

This is where you can test the poster's claim that DC can carry more usable power per conductor at MV level.

### 4. Load data

- Campus load target: start with 100 MW and also test 300 MW and 500 MW
- Hall/pod/rack allocation
- IT load composition: GPU, CPU, cooling auxiliaries, networking, storage
- Time-series load traces, not just average load
- Fast transient traces from GPU training synchronization events
- Load factor, diversity factor, ramp rate, duty cycle

You need both:

- Steady-state annualized profile for energy economics
- Fast dynamic profile for voltage stability / buffer sizing

### 5. Power-quality and grid-interface data

- THDi / THDv at each AC interface
- PF at the point of common coupling
- Utility interconnection requirements
- IEEE 519 compliance targets
- Flicker / voltage deviation limits if relevant
- Short-circuit strength at the PCC

### 6. DC-native resource integration data

- BESS power and energy rating
- Battery round-trip efficiency
- Solar PV profile if included
- Buffer placement options: GPU, rack, pod, backbone
- Control response times for buffers and converters

### 7. Economic and deployment data

- Electricity price or tariff assumptions
- Demand charges if relevant
- CAPEX for converters, transformers, busways, switchgear, protection
- Cooling cost impact from electrical losses
- Space / footprint value
- Reliability impact assumptions
- Maintenance intervals and replacement cycles

## Model Structure

Use a layered model. Do not start with a giant simulation.

### Layer 1. Deterministic architecture model

For each architecture, define:

- stages
- ratings
- voltages
- feeder lengths
- interface count

This becomes the canonical architecture table.

### Layer 2. Efficiency and loss model

For each stage:

- Use efficiency as a function of load, eta_i(load)
- Compute cumulative efficiency:

`eta_total = product(eta_i)`

- Compute input power for a required IT output power
- Add conductor losses using `I^2R`
- Add no-load losses

Primary output:

- Total efficiency
- Total MW loss
- Annual MWh loss
- Annual energy cost

This is the first place to test the poster's 81% vs 94.6% illustrative claim. Treat that claim as a hypothesis, not an assumption.

### Layer 3. Power-quality model

For AC sections, quantify:

- harmonic sources
- filtering needs
- PF correction ownership
- PCC compliance margin

Primary outputs:

- Number of AC harmonic injection points
- THDi / THDv at PCC
- PF at PCC
- filtering / correction equipment count

The proof target is not only lower THD. It is centralization of power-quality treatment and fewer AC interfaces that require harmonic mitigation.

### Layer 4. Reactive-power and voltage-control model

For AC architectures:

- model PF, reactive flow, and voltage support requirements across feeders

For MVDC backbone:

- model DC bus regulation, converter droop or master-slave control, and local buffer response

Primary outputs:

- reactive power circulating on feeders
- voltage deviation under load steps
- required buffer power and energy
- control complexity measured by number of regulated interfaces

### Layer 5. Dynamic transient model

Use representative GPU training power traces:

- millisecond to second-scale swings
- synchronized load steps
- periodic bursts

Primary outputs:

- DC bus sag / recovery
- AC PCC ramp seen by utility
- required local storage or capacitance
- control response needed from BESS / pod buffers

This layer is critical because the poster's motivation depends on AI loads being dynamic, not only large.

### Layer 6. Techno-economic model

Combine electrical and economic outputs:

- annual energy savings
- avoided cooling energy
- CAPEX delta
- payback
- NPV / IRR
- sensitivity to converter efficiency, power price, load factor, and cable length

### Layer 7. Innovation proof framework

Create a separate scorecard that compares the three architectures on:

- location of AC/DC boundary
- number of high-power conversion stages
- number of AC harmonic injection points
- need for reactive coordination downstream
- ease of integrating BESS / solar / buffers
- modularity / repeatability of pod expansion

This is how you prove the proposal is an architectural innovation rather than a component swap.

## What Proves the Poster

You should define explicit pass/fail criteria before modeling.

### Claim 1: cumulative efficiency

Proven if the MVDC backbone shows:

- materially higher end-to-end efficiency than both alternatives
- savings that persist across sensitivity cases
- conductor loss improvement at comparable delivered MW

### Claim 2: harmonics and PF ownership improvement

Proven if the MVDC backbone shows:

- fewer AC interfaces that inject harmonics
- centralized PF / harmonic control at the common front end
- easier compliance at PCC than the distributed AC case

### Claim 3: voltage-management simplification

Proven if the MVDC backbone shows:

- no downstream reactive flow on backbone feeders
- fewer controlled AC voltage-support points
- stable DC voltage under realistic AI transients with practical buffering

### Claim 4: DC-native integration benefit

Proven if BESS / PV / rack buffering connect with:

- fewer conversions
- lower round-trip loss
- faster control response
- lower integration complexity

## How To Prove The Innovation

There are three separate burdens of proof.

### 1. Prove it is new at the system level

Create a prior-art architecture matrix:

- traditional AC distribution
- 380 VDC / 400 VDC data center distribution
- 800 VDC facility bus
- AC-fed SST pods
- microgrid DC bus architectures

Then show what is distinct here:

- AC/DC boundary moved to the campus entry / subtransmission level
- MVDC backbone used as the primary campus distribution layer
- isolated DC pods serving the 800 VDC bus
- centralized PQ treatment plus DC-native resource integration on one backbone

### 2. Prove it creates non-obvious value

Do not claim novelty only because it is different. Show combined value that is hard to get simultaneously in the alternatives:

- cumulative efficiency gain
- simplified PQ ownership
- removal of downstream reactive coordination
- native BESS / PV integration
- scalable repeatable pod block

### 3. Prove it is implementable

Innovation is weak if it only works in an idealized spreadsheet. Include:

- protection concept
- fault isolation assumptions
- grounding concept
- control hierarchy
- staged deployment roadmap

## Recommended Work Plan

### Phase 1. Build the baseline model first

Duration: 1 to 2 weeks

- Freeze the three topologies
- Collect efficiency curves and feeder assumptions
- Build a spreadsheet or Python model for steady-state efficiency and annual energy loss
- Recreate the poster's headline numbers with explicit assumptions

Deliverable:

- A traceable baseline model and assumptions table

### Phase 2. Add conductor, PQ, and reactive-power analysis

Duration: 2 to 3 weeks

- Add cable loss and conductor utilization
- Map harmonic sources and PF ownership
- Quantify AC interfaces and reactive coordination points

Deliverable:

- Comparison charts for efficiency, conductor use, THD/PF ownership, and reactive support complexity

### Phase 3. Add transient and buffer analysis

Duration: 2 to 4 weeks

- Add time-series GPU load traces
- Simulate load steps and bursts
- Size local buffers and test bus stability

Deliverable:

- Dynamic response plots and buffer-sizing results

### Phase 4. Add techno-economics and innovation proof

Duration: 1 to 2 weeks

- Add CAPEX and lifecycle assumptions
- Run sensitivity and scenario analysis
- Build the prior-art / innovation matrix

Deliverable:

- Final paper-quality evidence package

## Suggested Evidence Package

If you want this to be credible to utilities, investors, or reviewers, your final package should include:

- one-line diagram for each architecture
- assumptions register
- efficiency curve appendix
- loss waterfall chart
- conductor utilization comparison
- THD / PF ownership map
- voltage / transient plots
- BESS / PV integration block diagram
- sensitivity tornado chart
- innovation matrix versus prior art
- implementation risk register with mitigation plan

## Best First Version

If you want the fastest path to something publishable, start with one headline use case:

- 100 MW AI factory campus
- compare the three architectures
- use one annual load profile and one fast transient profile
- include BESS at pod and backbone levels as two subcases

That is enough to prove or falsify the poster's main thesis without overbuilding the model.

## Immediate Next Step

Build a version 0 model with these tabs or modules:

1. assumptions
2. architecture comparison
3. efficiency curves
4. conductor losses
5. annual energy economics
6. PQ / PF ownership
7. transient cases
8. BESS / PV integration
9. sensitivity analysis
10. innovation matrix

If needed, this can be implemented either as:

- a spreadsheet for rapid iteration
- a Python model for traceability and scenario sweeps
- both, with the spreadsheet as front-end and Python as validation
