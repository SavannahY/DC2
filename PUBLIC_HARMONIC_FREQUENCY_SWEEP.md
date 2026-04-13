# Public Harmonic Frequency Sweep

Updated: April 11, 2026

This note runs an explicit OpenDSS harmonics-mode benchmark on the same SMART-DS feeder used in the public common-network T&D study.

Equivalent feeder-bank count: `87`.
P95 public operating point: `90.38%` of the 100 MW campus reference.
Scenario 3(M) central bus: `p12udt1266`.
Scenario 2(M) distributed buses:
- `p12udt5877`
- `p12udt5877-p12udt5945x`
- `p12udt5863`
- `p12udt5863-p12udt5940x`

Equal-total harmonic-current benchmark result:

```text
Spectrum               Scenario 2(M) max POI THDv proxy  Scenario 3(M) max POI THDv proxy  S2/S3 ratio
low_order_dominant     1.27%                             0.02%                             64.49x     
balanced_filtered      2.67%                             0.03%                             77.75x     
higher_order_filtered  4.23%                             0.05%                             83.69x     
```

Interpretation:

- The scenarios are compared on the same feeder and at the same total benchmark harmonic current.
- The result is therefore about network/interface sensitivity, not simply about injecting less total harmonic current.
- This is still a benchmark THDv proxy, not an IEEE 519 compliance study.
