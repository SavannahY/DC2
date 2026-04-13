# Harmonic Spectrum Benchmark

This note strengthens the power-quality claim by holding total harmonic current constant across Scenario 2(M) and Scenario 3(M).

- Total harmonic current per case: `0.0400 pu`.
- Scenario 2(M): total current is distributed across four AC-fed SST interfaces.
- Scenario 3(M): the same total current is injected at one centralized front end.
- Across all tested benchmark spectra and mirrored RTS areas, Scenario 3(M) remains better with a minimum THDv-proxy advantage of `1.12x`.

## Spectrum Cases

### Low-order dominant benchmark

Benchmark spectrum dominated by 5th and 7th current components.

```text
Area    Scenario 2(M) THDv  Scenario 3(M) THDv  Ratio
Area 1  0.00792             0.00413             1.92x
Area 2  0.01472             0.01317             1.12x
Area 3  0.02424             0.02081             1.16x
```

### Balanced filtered benchmark

Benchmark spectrum with the same total current spread evenly across the tested orders.

```text
Area    Scenario 2(M) THDv  Scenario 3(M) THDv  Ratio
Area 1  0.01022             0.00533             1.92x
Area 2  0.01899             0.01700             1.12x
Area 3  0.03129             0.02686             1.16x
```

### Higher-order filtered benchmark

Benchmark spectrum shifted toward higher orders to emulate stronger low-order filtering.

```text
Area    Scenario 2(M) THDv  Scenario 3(M) THDv  Ratio
Area 1  0.01408             0.00734             1.92x
Area 2  0.02618             0.02343             1.12x
Area 3  0.04312             0.03702             1.16x
```

## Interpretation

This is still a public benchmark sensitivity study, not a harmonic compliance study. Its value is narrower and cleaner:

- It shows that centralized AC-boundary ownership remains beneficial even when total harmonic injection is normalized.
- It separates the topological benefit from the trivial 'more interfaces means more injected current' effect.