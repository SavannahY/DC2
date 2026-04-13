# Public Common-Network T&D Study

Updated: April 11, 2026

This note places `Scenario 2(M)` and `Scenario 3(M)` on the same public SMART-DS feeder and compares them using the public operating library from `public_time_series_ai_factory.py`.

## Feeder and POIs

Base feeder power: `1.59 MW` with `61.04 kW` losses.
Equivalent feeder-bank count used to host the 100 MW campus on this public feeder exemplar: `87`.
Centralized Scenario 3(M) POI: `p12udt1266`.
Distributed Scenario 2(M) POIs:
- `p12udt5877`
- `p12udt5877-p12udt5945x`
- `p12udt5863`
- `p12udt5863-p12udt5940x`

## Annualized feeder impact

```text
Scenario       Weighted feeder losses  Weighted incremental losses  Worst peak loading  Worst peak POI vpu
Scenario 2(M)  0.71                    41.37                        84.29%              0.9724            
Scenario 3(M)  0.54                    26.76                        82.58%              1.0290            
```

## MIT-derived burst sensitivity

```text
Case                    Scenario       Delta feeder MW  Delta max line loading  Burst min POI vpu
mit_ai_burst_300s_p95   Scenario 2(M)  0.23             0.32 pct-pts            0.9689           
mit_ai_burst_300s_p95   Scenario 3(M)  0.22             0.01 pct-pts            1.0290           
mit_ai_burst_900s_p95   Scenario 2(M)  0.62             0.87 pct-pts            0.9618           
mit_ai_burst_900s_p95   Scenario 3(M)  0.58             0.01 pct-pts            1.0289           
mit_ai_burst_3600s_p95  Scenario 2(M)  1.25             1.79 pct-pts            0.9498           
mit_ai_burst_3600s_p95  Scenario 3(M)  1.16             0.03 pct-pts            1.0287           
```

## Surviving N-1 comparison

```text
Scenario       Surviving N-1 cases  Worst surviving min POI vpu  Worst surviving line loading
Scenario 2(M)  5                    0.9725                       84.27%                      
Scenario 3(M)  9                    1.0290                       82.57%                      
```

## Interpretation

- This is a real public feeder comparison, not a surrogate one-line stub.
- The SMART-DS feeder is much smaller than a 100 MW campus, so the study uses an equivalent feeder-bank count to normalize the campus onto repeated copies of the same public feeder.
- It is still not a utility Thevenin study or a site-specific interconnection study.
- The main value is methodological: both scenarios now live on the same published T&D network under the same public operating profile.
