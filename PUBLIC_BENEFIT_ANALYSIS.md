# Public Benefit Analysis

This note summarizes how far the available public datasets can support the three headline benefits.

## Benefit 1: Efficiency / loss reduction

- Single-path result under the public ESIF load shape: Scenario 3 is better than Scenario 2 for `25.0%` of annualized hours, but its total annualized loss is slightly worse by `+236.72 MWh`.
- Multi-node result under the same public ESIF load shape: Scenario 3(M) is better than Scenario 2(M) for `31.2%` of annualized hours and improves annualized loss by `-559.50 MWh`.
- Interpretation: the public data supports the campus-backbone efficiency claim more strongly than the simple single-path claim.

## Benefit 2: Power quality / harmonics

- Public-network harmonic-sensitivity proxy: Scenario 2(M) has a THDv proxy of `0.04088 pu` with four distributed AC interfaces, while Scenario 3(M) has `0.00533 pu` with one centralized AC interface.
- Interpretation: under the same per-interface harmonic-source assumption, the centralized-front-end architecture reduces aggregate grid-facing harmonic exposure because it collapses multiple AC interfaces into one.
- Limitation: this is still a structural harmonic-sensitivity screen, not an IEEE 519 compliance study.

## Benefit 3: Voltage response / upstream AC boundary

- Public-network voltage sensitivity at full load: Scenario 2(M) shows a maximum POI voltage-drop proxy of `2.807` percentage points, while Scenario 3(M) shows `0.511`.
- With a `+10%` load step: Scenario 2(M) rises to `3.071` percentage points and Scenario 3(M) rises to `0.556`.
- Interpretation: moving the AC/DC boundary upstream to one centralized subtransmission interface improves the public-network voltage-sensitivity screen.
- Limitation: this is a linearized network-voltage sensitivity around the published RTS operating point, not an EMT or converter-control study.

## Scaling evidence

- In the current expansion sweep, Scenario 3(M) first turns more efficient than Scenario 2(M) at `2` active blocks / `50 MW`.
- At four blocks / 100 MW, the harmonic proxy is `0.04088 pu` for Scenario 2(M) and `0.00533 pu` for Scenario 3(M).
- At four blocks / 100 MW, the base voltage-drop proxy is `2.807` percentage points for Scenario 2(M) and `0.511` for Scenario 3(M).