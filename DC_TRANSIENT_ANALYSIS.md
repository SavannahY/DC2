# Reduced-order Scenario 3(M) DC Transient Screen

This note addresses the main remaining dynamic concern: whether the MVDC backbone simply moves stress from the AC boundary into the internal DC network.

## Benchmark Setup

- Four 25 MW DC-native blocks on the shared Scenario 3(M) backbone.
- Short burst from 0.25 s to 0.45 s to emulate a fast AI-load excursion rather than a slow permanent step.
- Internal MVDC network solved at each time step; local buffers apply explicit power and energy limits.

## Key Result

- For a coherent 15% campus burst with no local buffer, the minimum block voltage reaches `0.99971 pu`, the source-input peak rises by `16.71 MW`, and the source-input ramp reaches `1671.45 MW/s`.
- With the moderate local buffer, the same event holds the minimum block voltage at `0.99972 pu`, reduces the source-input peak delta to `11.15 MW`, and reduces the source-input ramp to `462.48 MW/s`.
- With the strong local buffer, the same event holds the minimum block voltage at `0.99972 pu`, reduces the source-input peak delta to `9.33 MW`, and reduces the source-input ramp to `66.86 MW/s`.

## Internal-Stress Tradeoff

- Under the split-campus-opposition burst, the moderate buffer still limits the worst block voltage to `0.99974 pu`, but the internal segment-current peak remains a first-order quantity at `1660.17 A`.
- Interpretation: the MVDC backbone can keep internal voltage sag modest with local buffering, but internal current redistribution remains a real design constraint rather than disappearing.

## Evidence Boundary

- This strengthens the benefit-3 claim by showing internal MVDC behavior under dynamic block loading, not just AC-boundary voltage screens.
- It is still reduced-order. It does not replace converter-aware EMT, protection, or control validation.