# Multi-node Transient Comparison

This note turns the internal Scenario 3(M) transient screen into a direct Scenario 2(M) versus Scenario 3(M) comparison.

## Main Result

- For a coherent 15% burst with no local buffer, Scenario 2(M) shows a source-input burst of `16.83 MW` and Scenario 3(M) shows `16.71 MW`.
- With the moderate local buffer, the same coherent burst gives Scenario 2(M) a source ramp of `482.98 MW/s` and Scenario 3(M) `462.48 MW/s`.

## Internal Network Tradeoff

- Under the moderate two-block clustered burst, Scenario 2(M) reaches `1050.93 A` maximum segment current while Scenario 3(M) reaches `1740.38 A`.
- Under the strong-buffer split-opposition burst, Scenario 2(M) minimum block voltage is `0.99984 pu` and Scenario 3(M) is `0.99974 pu`.
- Interpretation: Scenario 3(M) should be argued as an upstream burst-shaping architecture, not as an architecture that removes all internal dynamic stress.