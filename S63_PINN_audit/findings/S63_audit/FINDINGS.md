# S63 audit findings

For the interpreted audit conclusions and provisional A11 review order, see [`../../S63_AUDIT_SUMMARY.md`](../../S63_AUDIT_SUMMARY.md). The tables below are the reproducible automated screening output.

Clips passing numeric input checks: 25; empty: 0; missing expected: 0; invalid: 0; analyzed frames: 3897.

Review-flagged destination frames: 318. Duplicate rows within clips: 90.

These are data-quality screening results, not validated fall labels or anatomical CoM. No frames are repaired or interpolated. Invalid trials remain in raw/ and manifest.json but are withheld from calculations.

| Trial | Status | Frames | Span (s) | Review frames | Duplicate rows | Scale range (%) |
|---|---|---:|---:|---:|---:|---:|
| S63A10T01 | numeric | 163 | 5.4 | 11 | 2 | 7.860397078024639 |
| S63A10T02 | numeric | 99 | 3.2666666666666666 | 2 | 6 | 8.723869272762762 |
| S63A10T03 | numeric | 120 | 3.966666666666667 | 25 | 0 | 20.107400013220488 |
| S63A10T04 | numeric | 138 | 4.566666666666666 | 15 | 3 | 12.485644117298712 |
| S63A10T05 | numeric | 172 | 5.7 | 8 | 3 | 9.806884763790325 |
| S63A11T01 | numeric | 131 | 4.333333333333333 | 17 | 5 | 19.364651975394676 |
| S63A11T02 | numeric | 158 | 5.233333333333333 | 18 | 1 | 13.638655136120214 |
| S63A11T03 | numeric | 158 | 5.233333333333333 | 12 | 12 | 11.81230458642004 |
| S63A11T04 | numeric | 185 | 6.133333333333334 | 13 | 1 | 11.551399915312555 |
| S63A11T05 | numeric | 144 | 4.766666666666667 | 17 | 3 | 18.76195421425273 |
| S63A12T01 | numeric | 134 | 4.433333333333334 | 13 | 0 | 15.213902084989982 |
| S63A12T02 | numeric | 189 | 6.266666666666667 | 6 | 3 | 11.610967698038976 |
| S63A12T03 | numeric | 126 | 4.166666666666667 | 8 | 4 | 15.949074419164022 |
| S63A12T04 | numeric | 176 | 5.833333333333333 | 21 | 0 | 33.89060585811663 |
| S63A12T05 | numeric | 155 | 5.133333333333334 | 48 | 6 | 51.015880663786106 |
| S63A13T01 | numeric | 253 | 8.4 | 27 | 1 | 27.835348567385964 |
| S63A13T02 | numeric | 164 | 5.433333333333334 | 4 | 2 | 17.97906072705404 |
| S63A13T03 | numeric | 144 | 4.766666666666667 | 4 | 3 | 7.28066555800031 |
| S63A13T04 | numeric | 120 | 3.966666666666667 | 7 | 1 | 9.878316124049459 |
| S63A13T05 | numeric | 161 | 5.333333333333333 | 5 | 5 | 11.524477511724696 |
| S63A14T01 | numeric | 145 | 4.8 | 3 | 2 | 11.072635699812006 |
| S63A14T02 | numeric | 167 | 5.533333333333333 | 11 | 4 | 9.139978888511703 |
| S63A14T03 | numeric | 153 | 5.066666666666666 | 11 | 4 | 10.459505431375682 |
| S63A14T04 | numeric | 193 | 6.4 | 6 | 10 | 8.808897041723252 |
| S63A14T05 | numeric | 149 | 4.933333333333334 | 6 | 9 | 9.93419225970813 |

## Temporal audit

| Trial | Distinct poses | Repeated transitions (%) | Longest constant span (s) |
|---|---:|---:|---:|
| S63A10T01 | 161 | 1.23 | 0.033 |
| S63A10T02 | 93 | 6.12 | 0.100 |
| S63A10T03 | 120 | 0.00 | 0.000 |
| S63A10T04 | 135 | 2.19 | 0.067 |
| S63A10T05 | 169 | 1.75 | 0.067 |
| S63A11T01 | 126 | 3.85 | 0.067 |
| S63A11T02 | 157 | 0.64 | 0.033 |
| S63A11T03 | 146 | 7.64 | 0.167 |
| S63A11T04 | 184 | 0.54 | 0.033 |
| S63A11T05 | 141 | 2.10 | 0.033 |
| S63A12T01 | 134 | 0.00 | 0.000 |
| S63A12T02 | 186 | 1.60 | 0.067 |
| S63A12T03 | 122 | 3.20 | 0.133 |
| S63A12T04 | 176 | 0.00 | 0.000 |
| S63A12T05 | 149 | 3.90 | 0.100 |
| S63A13T01 | 252 | 0.40 | 0.033 |
| S63A13T02 | 162 | 1.23 | 0.033 |
| S63A13T03 | 141 | 2.10 | 0.033 |
| S63A13T04 | 119 | 0.84 | 0.033 |
| S63A13T05 | 156 | 3.12 | 0.100 |
| S63A14T01 | 143 | 1.39 | 0.067 |
| S63A14T02 | 163 | 2.41 | 0.033 |
| S63A14T03 | 149 | 2.63 | 0.100 |
| S63A14T04 | 183 | 5.21 | 0.067 |
| S63A14T05 | 140 | 6.08 | 0.133 |

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

