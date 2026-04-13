# SST Baseline Comparator Note

This report compares three forward-looking paths under the same current source-anchored assumptions:

- explicit `69 kV AC -> SST -> 800 VDC` baseline,
- direct `69 kV AC -> 800 VDC` perimeter alternative,
- `69 kV AC -> 69 kV DC backbone -> isolated DC pod -> 800 VDC`.

The explicit SST baseline currently lands at `91.82%` full-load efficiency.
The direct perimeter alternative lands at `91.90%`.
The MVDC backbone lands at `92.17%`.

Relative to the explicit SST baseline, the direct perimeter alternative changes annual loss by `-850.30 MWh/year`.
Relative to the SST baseline, the MVDC backbone changes annual loss by `-3610.99 MWh/year`.

This comparison is still proxy-dependent. It separates the architectural question into three steps instead of collapsing the advanced AC-fed case into one shortcut assumption.