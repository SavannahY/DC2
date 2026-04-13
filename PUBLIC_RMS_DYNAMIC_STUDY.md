# Public RMS Dynamic Study

Updated: April 11, 2026

This note adds an RMS electromechanical dynamic layer to the public-data-only reviewer-response package.

## Model scope

The study uses the public ANDES IEEE 14-bus full dynamic benchmark. It adds an AI-campus load block to that case and compares:

- `Scenario 2(M)`: four distributed AC-fed SST block interfaces at buses `9, 10, 13, 14`.
- `Scenario 3(M)`: one centralized upstream AC/DC front-end interface at bus `5`.
- `normal_network`: no topology change before the burst step.
- `remote_corridor_weakened`: trip `Line_10` at `t=0.5s` before the MIT-derived burst step at `t=1.0s`.

The dynamic disturbance magnitudes are taken from the public MIT Supercloud p95 positive-event burst library. They are applied here as benchmark load steps on a public RMS case. This is not a claim that the RMS simulation resolves converter or sub-second control behavior.

## Headline separations

Converged comparison pairs in this benchmark: `14`.
Non-converged runs in this benchmark: `4`.
Strongest converged voltage separation: `mit_ai_burst_900s_p95` under `remote_corridor_weakened` at campus share `25.00%`, where Scenario 3(M) improves minimum campus voltage by `0.2757 pu`.
Strongest converged frequency separation: `mit_ai_burst_300s_p95` under `remote_corridor_weakened` at campus share `15.00%`, where Scenario 3(M) changes the maximum local frequency deviation by `-0.172 Hz` relative to Scenario 2(M). Negative values favor Scenario 3(M).

## Detailed comparison at 25% campus-share benchmark

Campus share  Grid mode                 Burst case              S2 TDS  S3 TDS  S2 min Vpu  S3 min Vpu  S2 max |df|  S3 max |df|
25.00%        normal_network            mit_ai_burst_300s_p95   OK      OK      0.9694      1.0057      0.408 Hz     0.389 Hz   
25.00%        normal_network            mit_ai_burst_900s_p95   OK      OK      0.9222      0.9905      0.602 Hz     0.574 Hz   
25.00%        normal_network            mit_ai_burst_3600s_p95  OK      OK      0.7515      0.9549      0.934 Hz     0.880 Hz   
25.00%        remote_corridor_weakened  mit_ai_burst_300s_p95   OK      OK      0.8538      1.0042      0.486 Hz     0.399 Hz   
25.00%        remote_corridor_weakened  mit_ai_burst_900s_p95   OK      OK      0.7118      0.9875      0.678 Hz     0.584 Hz   
25.00%        remote_corridor_weakened  mit_ai_burst_3600s_p95  STOP    OK      0.8822      0.9506      0.486 Hz     0.890 Hz   

## Share sweep summary

Campus share  Best S3-S2 voltage margin  Best S3-S2 frequency margin
15.00%        0.2086 pu                  -0.172 Hz                  
25.00%        0.2757 pu                  -0.094 Hz                  
35.00%        0.2461 pu                  -0.105 Hz                  

## Interpretation

- The RMS layer is strongest on minimum campus voltage under the remote-corridor weakening stress case.
- This supports the directional claim that moving the AC/DC boundary upstream reduces exposure to remote AC-corridor weakness when campus subloads are otherwise distributed across multiple AC interfaces.
- Several heaviest distributed-load stress cases are non-convergent in the public RMS benchmark. Those should be interpreted as stability-screen failures, not as converged waveform results.
- The RMS layer is not EMT validation. It does not model converter controls, harmonics, or DC fault transients.