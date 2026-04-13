# Buffer Placement Comparison

This note tests whether the MVDC architecture makes the same total buffer budget more effective by enabling pooled placement.

## Main Result

- Under a coherent 15% burst, Scenario 2(M) with local-only buffering reaches `11.31 MW` source burst and `482.98 MW/s` source ramp.
- Scenario 3(M) with the same local-only budget reaches `11.15 MW` and `462.48 MW/s`.
- Scenario 3(M) with the same total budget but pooled placement reaches `10.55 MW` and `462.82 MW/s`. That is a modest improvement for a fully coherent burst, because all blocks move in the same direction at once.

## Interpretation

- Under the two-block clustered burst, Scenario 2(M) local-only buffering gives `241.47 MW/s`, while the pooled Scenario 3(M) case drops to `31.71 MW/s` with minimum block voltage still near nominal at `0.99973 pu`.
- Under the split-opposition burst, Scenario 2(M) local-only buffering gives `9.92 MW/s`, while the pooled Scenario 3(M) case drops to `0.38 MW/s`.
- This is the stronger architectural Benefit 3 argument: the MVDC backbone makes pooled buffering materially more effective when campus subloads do not move coherently, which is exactly where a shared DC backbone should create value.