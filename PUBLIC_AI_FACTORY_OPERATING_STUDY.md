# Public Annual + Burst Operating Study

Updated: April 11, 2026

This note is the first public-data-only operating layer for the reviewer-response roadmap.
It combines:

- annual utilization bins from the public NREL ESIF `it_power_kw` series,
- labeled AI-workload timing from the public MIT Supercloud scheduler archive,
- and derived burst cases that later common-network, harmonic, and RMS studies can reuse.

Repository note:

- the large raw MIT scheduler CSV is not committed to GitHub because it exceeds normal repository-size limits,
- the repo keeps the small labeled metadata files and the derived operating report instead,
- and the raw scheduler CSV should be downloaded from `https://dcc.mit.edu/data/` when this study needs to be regenerated from scratch.

## Why This Matters

This layer addresses two review weaknesses directly:

- the earlier annual-loss study looked too much like a flat full-load year,
- and the earlier burst cases were not tied to a public AI-workload dataset.

This is still not a site-specific operating study. The ESIF dataset is not an AI-factory dataset, and the MIT layer is a labeled AI-workload scheduler study rather than a direct campus power trace. But together they are a much stronger public operating basis than a flat reference year plus hand-picked burst amplitudes.

## Annual ESIF Layer

The cached ESIF profile uses `16` annual bins and has normalized mean load `40.81%` with normalized p95 `90.38%`.

Single-path annualized results under the ESIF profile:

```text
Scenario    Full-Load Eff.  Annual Loss  Annual Loss Cost
Scenario 2  91.82%          49.08        $4.56M          
Scenario 3  92.17%          46.53        $4.32M          
```

Multi-node annualized results under the same ESIF profile:

```text
Scenario       Full-Load Eff.  Annual Loss  Annual Loss Cost
Scenario 2(M)  85.16%          65.36        $6.07M          
Scenario 3(M)  86.69%          59.02        $5.48M          
```

## MIT AI Burst Layer

The public MIT scheduler subset contributes `3430` labeled AI jobs over about `150.9` days.
Duration statistics: mean `4.60` h, p50 `2.73` h, p95 `16.13` h, p99 `23.29` h.
Requested GPU count statistics: mean `5.70`, p50 `2.00`, p95 `4.00`, max `424`.
Time-weighted active AI GPU concurrency: mean `11.49`, p95 `64.00`, max `728.00`.

Family mix by labeled job count:

```text
Family    Jobs
graph     131 
language  361 
unet      1431
vision    1507
```

Representative MIT-derived burst cases for later dynamic studies:

```text
Case                    Window  Positive event share  Fraction of p95 active AI load  Ramp fraction / minute
mit_ai_burst_300s_p95   5 min   3.92%                 18.75%                          3.75%                 
mit_ai_burst_900s_p95   15 min  4.98%                 50.00%                          3.33%                 
mit_ai_burst_3600s_p95  60 min  7.14%                 101.56%                         1.69%                 
```

## How To Use This Layer Next

- Feed the ESIF annual bins into the common-network and techno-economic studies.
- Feed the MIT-derived burst cases into the harmonic, RMS dynamic, and weak-grid studies.
- Keep the scope disciplined: this is a public operating library, not a substitute for private site telemetry.
