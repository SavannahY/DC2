# Public Fault Envelope

Updated: April 11, 2026

This note adds a public-data-only protection plausibility layer for the proposed `Scenario 3(M)` MVDC backbone.

## Model scope

The screen starts from the full-load multi-node Scenario 3(M) currents already computed in the repo. It then evaluates representative backbone and branch fault locations with a reduced-order RL current-rise model.

- Backbone voltage: `69.0 kV DC`.
- Public line-inductance benchmark: `0.86 mH/km`.
- Reactor sweep: `50, 100, 200 mH`.
- Breaker benchmark times: `semiconductor_fast=2 ms, hybrid_reference=5 ms, slower_interruption=10 ms, backup_delayed=20 ms`.
- Public source for line inductance example: `https://www.mdpi.com/1996-1073/17/15/3800`.
- Public source for breaker timing categories: `https://doi.org/10.1186/s41601-023-00304-y`.

## Baseline envelope

Baseline rows below use `100 mH` reactor and `0.01 ohm` fault resistance.

Location                  Prefault current  5 ms current  5 ms I^2t   Time to 5 kA
remote_branch_end         0.42 kA           3.81 kA       0.03 MA^2s  6.75 ms     
source_backbone_midpoint  1.66 kA           5.10 kA       0.06 MA^2s  4.85 ms     

## Headline findings

Worst `5 ms` hybrid-reference current in the sweep occurs at `source_backbone_midpoint` with reactor `50 mH` and fault resistance `0.01 ohm`, reaching `8.53 kA`.
Fastest time to `5 kA` in the sweep occurs at `source_backbone_midpoint` with reactor `50 mH` and fault resistance `0.01 ohm`, at `2.43 ms`.

## Interpretation

- This layer does not prove a protection design. It does provide a public-data-only bound on how quickly MVDC backbone current can rise under representative faults.
- It supports the reviewer-response position that protection is a first-order design issue with interruption-timescale consequences, not an ignored afterthought.
- Because converter current limiting is not modeled here, the results should be treated as conservative screening values rather than deployable equipment duty ratings.