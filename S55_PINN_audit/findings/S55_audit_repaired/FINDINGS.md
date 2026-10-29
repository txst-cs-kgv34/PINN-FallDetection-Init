# S55 audit findings

Clips passing numeric input checks: 25; empty: 0; missing expected: 0; invalid: 0; analyzed frames: 4240.

Review-flagged destination frames: 673. Duplicate rows within clips: 68.

These are data-quality screening results, not validated fall labels or anatomical CoM. This run audits the repaired numeric copies; the untouched original audit remains in `../S55_audit`. Invalid trials would remain in `raw/` and `manifest.json` but be withheld from calculations.

## Blank-row repair assessment

The repair layer replaced 80 fully blank frames in 11 gaps and preserved a
frame-level mask in `../../repaired_data/S55/repaired_frames.csv`. Gaps of 1–3
frames were forward-filled; longer internal gaps were linearly interpolated.
S55A10T01 has 26/105 repaired frames (24.8%) and S55A14T01 has 48/212
(22.6%); exclude both from primary parameter estimation or report a sensitivity
analysis. S55A10T02 has 5/214 (2.3%) and S55A13T01 has 1/147 (0.7%).

| Trial | Status | Frames | Span (s) | Review frames | Duplicate rows | Scale range (%) |
|---|---|---:|---:|---:|---:|---:|
| S55A10T01 | numeric | 105 | 3.466666666666667 | 44 | 5 | 77.80902583392017 |
| S55A10T02 | numeric | 214 | 7.1 | 69 | 5 | 75.5848531920878 |
| S55A10T03 | numeric | 146 | 4.833333333333333 | 22 | 3 | 41.37787879214952 |
| S55A10T04 | numeric | 152 | 5.033333333333333 | 36 | 0 | 21.216961836840742 |
| S55A10T05 | numeric | 202 | 6.7 | 28 | 1 | 16.79771833065795 |
| S55A11T01 | numeric | 141 | 4.666666666666667 | 28 | 6 | 39.186123063988006 |
| S55A11T02 | numeric | 131 | 4.333333333333333 | 45 | 0 | 25.540087471220986 |
| S55A11T03 | numeric | 155 | 5.133333333333334 | 31 | 1 | 28.87789328743913 |
| S55A11T04 | numeric | 147 | 4.866666666666666 | 32 | 5 | 45.19195107161635 |
| S55A11T05 | numeric | 168 | 5.566666666666666 | 29 | 9 | 30.286981241928835 |
| S55A12T01 | numeric | 205 | 6.8 | 16 | 0 | 22.330821792864253 |
| S55A12T02 | numeric | 194 | 6.433333333333334 | 15 | 3 | 21.03548452981363 |
| S55A12T03 | numeric | 209 | 6.933333333333334 | 14 | 1 | 10.328893620490366 |
| S55A12T04 | numeric | 202 | 6.7 | 25 | 4 | 15.944298814556145 |
| S55A12T05 | numeric | 232 | 7.7 | 32 | 3 | 19.7020753994005 |
| S55A13T01 | numeric | 147 | 4.866666666666666 | 23 | 1 | 47.22151695875261 |
| S55A13T02 | numeric | 181 | 6.0 | 20 | 0 | 17.527239513330816 |
| S55A13T03 | numeric | 151 | 5.0 | 24 | 1 | 43.42259117590845 |
| S55A13T04 | numeric | 173 | 5.733333333333333 | 23 | 3 | 22.998464161563746 |
| S55A13T05 | numeric | 131 | 4.333333333333333 | 18 | 1 | 30.411680157384026 |
| S55A14T01 | numeric | 212 | 7.033333333333333 | 21 | 2 | 18.98003118040139 |
| S55A14T02 | numeric | 179 | 5.933333333333334 | 12 | 4 | 18.304035800031283 |
| S55A14T03 | numeric | 136 | 4.5 | 41 | 2 | 28.88364849781986 |
| S55A14T04 | numeric | 177 | 5.866666666666666 | 17 | 7 | 15.69545886029804 |
| S55A14T05 | numeric | 150 | 4.966666666666667 | 8 | 1 | 10.480922317690556 |

## Temporal audit

| Trial | Distinct poses | Repeated transitions (%) | Longest constant span (s) |
|---|---:|---:|---:|
| S55A10T01 | 100 | 4.81 | 0.067 |
| S55A10T02 | 209 | 2.35 | 0.067 |
| S55A10T03 | 143 | 2.07 | 0.067 |
| S55A10T04 | 152 | 0.00 | 0.000 |
| S55A10T05 | 201 | 0.50 | 0.033 |
| S55A11T01 | 135 | 4.29 | 0.067 |
| S55A11T02 | 131 | 0.00 | 0.000 |
| S55A11T03 | 154 | 0.65 | 0.033 |
| S55A11T04 | 142 | 3.42 | 0.100 |
| S55A11T05 | 159 | 5.39 | 0.067 |
| S55A12T01 | 205 | 0.00 | 0.000 |
| S55A12T02 | 191 | 1.55 | 0.033 |
| S55A12T03 | 208 | 0.48 | 0.033 |
| S55A12T04 | 198 | 1.99 | 0.067 |
| S55A12T05 | 229 | 1.30 | 0.033 |
| S55A13T01 | 146 | 0.68 | 0.033 |
| S55A13T02 | 181 | 0.00 | 0.000 |
| S55A13T03 | 150 | 0.67 | 0.033 |
| S55A13T04 | 170 | 1.74 | 0.033 |
| S55A13T05 | 130 | 0.77 | 0.033 |
| S55A14T01 | 210 | 0.95 | 0.033 |
| S55A14T02 | 175 | 2.25 | 0.067 |
| S55A14T03 | 134 | 1.48 | 0.033 |
| S55A14T04 | 170 | 3.98 | 0.100 |
| S55A14T05 | 149 | 0.67 | 0.033 |

Exact repeats mean identical exported coordinates, not confirmed biological stillness. See results/constant_pose_runs.csv for inclusive zero-based frame ranges. No repeats are deleted.

## Evidence and reproducibility

- results/manifest.json: source paths, hashes and parsing errors.
- results/trial_summary.csv: clip-level measurements.
- results/review_events.csv (when flags exist): exact frame pairs for inspection.
- results/com/: per-frame CoM and camera displacements.
- results/segment_mass_model.csv and segment_model.json: full mass and landmark mapping.
- results/landmark_sensitivity.csv: alternative mappings, not uncertainty bounds.
- config.json and code/: frozen configuration and scripts.

## Questions for the team

Confirm XYZ units/order, camera-to-floor orientation, original timestamps, missing/trimmed recordings and body-tracking confidence. Determine whether changing limb scale is in the raw export or preprocessing. Review full event coverage before selecting PINN trials. No ground contact, BoS, joint forces or external perturbations are inferred here.

## Evidence figures

![A10_skeleton_snapshots](results/plots/A10_skeleton_snapshots.png)

![A11_skeleton_snapshots](results/plots/A11_skeleton_snapshots.png)

![A12_skeleton_snapshots](results/plots/A12_skeleton_snapshots.png)

![A13_skeleton_snapshots](results/plots/A13_skeleton_snapshots.png)

![A14_skeleton_snapshots](results/plots/A14_skeleton_snapshots.png)

![real_CoM_comparison](results/plots/real_CoM_comparison.png)

![shared_limb_scaling](results/plots/shared_limb_scaling.png)

![temporal_repeats](results/plots/temporal_repeats.png)

![tracking_diagnostics](results/plots/tracking_diagnostics.png)

