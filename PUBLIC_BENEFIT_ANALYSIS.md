# Public Benefit Analysis

This note summarizes how far the available public datasets can support the three headline benefits.

## Benefit 1: Efficiency / loss reduction

- Single-path result under the public ESIF load shape: Scenario 3 is better than Scenario 2 for `100.0%` of annualized hours and improves total annualized loss by `2550.20 MWh`.
- Multi-node result under the same public ESIF load shape: Scenario 3(M) is better than Scenario 2(M) for `100.0%` of annualized hours and improves annualized loss by `6337.15 MWh`.
- Interpretation: the public data supports the campus-backbone efficiency claim more strongly than the simple single-path claim.

## Benefit 2: Power quality / harmonics

- Public-network harmonic-sensitivity proxy: Scenario 2(M) has a THDv proxy of `0.04088 pu` with four distributed AC interfaces, while Scenario 3(M) has `0.00533 pu` with one centralized AC interface.
- Interpretation: under the same per-interface harmonic-source assumption, the centralized-front-end architecture reduces aggregate grid-facing harmonic exposure because it collapses multiple AC interfaces into one.
- Limitation: this is still a structural harmonic-sensitivity screen, not an IEEE 519 compliance study.

## Benefit 3: Voltage response / upstream AC boundary

- Public-network voltage sensitivity at full load: Scenario 2(M) shows a maximum POI voltage-drop proxy of `2.839` percentage points, while Scenario 3(M) shows `0.511`.
- With a `+10%` load step: Scenario 2(M) rises to `3.107` percentage points and Scenario 3(M) rises to `0.556`.
- Interpretation: moving the AC/DC boundary upstream to one centralized subtransmission interface improves the public-network voltage-sensitivity screen.
- Limitation: this is a linearized network-voltage sensitivity around the published RTS operating point, not an EMT or converter-control study.

## Benefit 3: RMS dynamic benchmark

- Public ANDES RMS benchmark at `25%` campus-share and the MIT `900 s p95` burst:
  - normal network: Scenario 2(M) minimum campus voltage `0.9222 pu`, Scenario 3(M) `0.9905 pu`
  - remote-corridor weakened: Scenario 2(M) `0.7118 pu`, Scenario 3(M) `0.9875 pu`
- The same RMS runs show lower local frequency deviation for Scenario 3(M) in the strongest converged benchmark cases:
  - normal network / `900 s p95`: `0.602 Hz` for Scenario 2(M) versus `0.574 Hz` for Scenario 3(M)
  - remote-corridor weakened / `900 s p95`: `0.678 Hz` for Scenario 2(M) versus `0.584 Hz` for Scenario 3(M)
- Interpretation: the public RMS layer supports the claim that a centralized upstream interface is less exposed to remote AC-corridor weakness than four distributed AC-fed block interfaces.
- Limitation: this is an RMS electromechanical benchmark, not an EMT converter-control model. Some of the heaviest distributed-load stress cases become non-convergent and should be treated as stability-screen failures rather than converged waveform results.

## Protection plausibility

- Reduced-order public fault-duty screen for Scenario 3(M), using the current repo topology and public line-inductance / breaker-time ranges:
  - source-backbone midpoint fault, `100 mH` reactor, `0.01 ohm` fault resistance:
    - prefault current `1.66 kA`
    - `5 ms` current `5.10 kA`
    - time to `5 kA` about `4.85 ms`
  - remote branch-end fault, same benchmark assumptions:
    - prefault current `0.42 kA`
    - `5 ms` current `3.81 kA`
    - time to `5 kA` about `6.75 ms`
- Interpretation: the public protection screen supports the reviewer-response claim that MVDC backbone protection is a first-order interruption-timescale problem, not a trivial detail. It does not yet provide a deployable protection design.

## Scaling evidence

- In the current expansion sweep, Scenario 3(M) first turns more efficient than Scenario 2(M) at `1` active blocks / `25 MW`.
- At four blocks / 100 MW, the harmonic proxy is `0.04088 pu` for Scenario 2(M) and `0.00533 pu` for Scenario 3(M).
- At four blocks / 100 MW, the base voltage-drop proxy is `2.839` percentage points for Scenario 2(M) and `0.511` for Scenario 3(M).

## Location robustness

- Across the three mirrored RTS areas, the Scenario 2(M)-to-Scenario 3(M) harmonic proxy ratio remains at least `4.47x`.
- Across the same three areas, the Scenario 2(M)-to-Scenario 3(M) base voltage-drop proxy ratio remains at least `2.85x`.
- Interpretation: the public-network harmonic and voltage advantages are not tied to one hand-picked benchmark location.

## N-1 contingency robustness

- Across the local single-branch-outage screens, the Scenario 2(M)-to-Scenario 3(M) worst-case harmonic proxy ratio remains at least `6.30x`.
- Across the same outage screens, the Scenario 2(M)-to-Scenario 3(M) worst-case voltage-drop proxy ratio remains at least `3.86x`.
- Interpretation: the centralized-front-end advantage remains visible after local branch outages in the public benchmark network.

## Dynamic diversity

- Under a coherent 10% campus swing at 1 Hz, the source-peak screen is `11.33 MW` for Scenario 2(M) and `11.20 MW` for Scenario 3(M).
- Under a two-block clustered 10% swing at 1 Hz, the source-peak screen is `5.67 MW` for Scenario 2(M) and `5.61 MW` for Scenario 3(M).
- Under a split-campus opposing 10% swing at 1 Hz, both grid-facing source peaks collapse toward zero (`0.043 MW` for Scenario 2(M), `0.032 MW` for Scenario 3(M)), but Scenario 3(M) carries larger internal segment-current redistribution.
- Interpretation: the public model supports the AC-boundary benefit of Scenario 3(M) under diverse block-level patterns, while also showing that some dynamic stress shifts into the internal backbone rather than disappearing.
