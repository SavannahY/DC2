# 1 GW Single-Site Stress Case

This note records a `1 GW` delivered IT single-site stress case using the
existing single-path architecture model:

```bash
python3 /Users/zhengjieyang/Documents/DC2/dc_backbone_model.py --it-load-mw 1000
```

Machine-readable output is stored in
[one_gw_single_site_report.json](/Users/zhengjieyang/Documents/DC2/one_gw_single_site_report.json).

## Results

| Scenario | Full-load efficiency | Full-load input MW | Annual loss | Annual loss cost |
| --- | ---: | ---: | ---: | ---: |
| Scenario 1: Traditional AC-centric | `84.03%` | `1,190.09 MW` | `1,665.17 GWh/year` | `$154.69M/year` |
| Scenario 2: `69 kV AC -> 800 VDC` perimeter conversion | `87.58%` | `1,141.87 MW` | `1,242.78 GWh/year` | `$115.45M/year` |
| Scenario 3: Proposed MVDC backbone | `87.69%` | `1,140.36 MW` | `1,229.54 GWh/year` | `$114.22M/year` |

Relative to Scenario 2, the current `1 GW` single-site Scenario 3 result is:

- `+0.116` efficiency percentage points
- `-13.25 GWh/year` annualized loss
- `-$1.23M/year` annualized loss cost

## Interpretation

The `1 GW` single-site case is directionally favorable for Scenario 3, but the
margin over Scenario 2 is still modest. That means this is **not** the strongest
way to prove the MVDC-backbone thesis.

The stronger use of the `1 GW` case is as a **stress boundary**:

- it shows what happens when the load is very large and highly concentrated
- it highlights how much source-side power still has to be delivered even after
  conversion improvements
- it helps separate the “single very large site” question from the “shared
  multi-node campus backbone” question

## Public-network implication

The same `1 GW` single-site source draw does **not** fit comfortably on the
current public RTS-GMLC single-POI benchmark screen.

Using the published RTS network with the current single-POI benchmark bus:

- Scenario 3 single-site source draw: about `1,140.36 MW`
- Scenario 2 single-site source draw: about `1,141.87 MW`
- Scenario 1 single-site source draw: about `1,190.09 MW`

The resulting public-network stress screen gives:

- Scenario 3: worst final branch loading about `152.15%`
- Scenario 2: worst final branch loading about `152.30%`
- Scenario 1: worst final branch loading about `156.96%`

So, under the current public RTS benchmark, a `1 GW` single-site case is better
interpreted as:

- **too large for the present single-POI public benchmark**
- a reason to move to a stronger subtransmission/interconnection architecture
- but not by itself proof that a backbone architecture is superior

## Why this matters for the paper

For a public research-facing white paper, the `1 GW` single-site case should be
used carefully.

Good use:

- as an extreme stress case
- to show that the problem becomes more infrastructure-constrained at very large
  site size
- to motivate why simple facility-edge conversion is not the whole story

Bad use:

- as the main proof that Scenario 3 always beats Scenario 2

The current evidence remains stronger for the **multi-node campus** claim than
for the **single concentrated site** claim.
