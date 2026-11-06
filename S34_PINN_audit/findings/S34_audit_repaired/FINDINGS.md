# S34 audit findings

Clips passing numeric input checks: 21; empty: 0; missing expected: 4; invalid: 0; analyzed frames: 5990.

Review-flagged destination frames: 752. Duplicate rows within clips: 1100.

These are data-quality screening results, not validated fall labels or anatomical CoM. The audit does not repair inputs itself; when a derived repaired-data directory is supplied, consult its repair manifest and frame mask. Invalid trials remain in raw/ and manifest.json but are withheld from calculations.

| Trial | Status | Frames | Span (s) | Review frames | Duplicate rows | Scale range (%) |
|---|---|---:|---:|---:|---:|---:|
| S34A10T01 | numeric | 302 | 10.033333333333333 | 33 | 76 | 27.77076316490468 |
| S34A10T02 | numeric | 251 | 8.333333333333334 | 34 | 63 | 24.76688911761642 |
| S34A10T03 | numeric | 283 | 9.4 | 36 | 15 | 29.273519312907226 |
| S34A10T04 | numeric | 332 | 11.033333333333333 | 63 | 20 | 50.69340058528049 |
| S34A10T05 | numeric | 277 | 9.2 | 32 | 76 | 46.69079304139005 |
| S34A11T01 | numeric | 281 | 9.333333333333334 | 47 | 17 | 92.47469504973995 |
| S34A11T02 | numeric | 296 | 9.833333333333334 | 32 | 101 | 56.81044572857521 |
| S34A11T03 | numeric | 293 | 9.733333333333333 | 32 | 113 | 63.53238042155589 |
| S34A11T04 | numeric | 279 | 9.266666666666667 | 26 | 98 | 89.50405406383427 |
| S34A11T05 | numeric | 256 | 8.5 | 30 | 53 | 70.7665561362211 |
| S34A12T01 | numeric | 225 | 7.466666666666667 | 35 | 35 | 24.881742245778817 |
| S34A12T02 | numeric | 280 | 9.3 | 28 | 9 | 18.94778932268235 |
| S34A12T03 | numeric | 308 | 10.233333333333333 | 34 | 79 | 21.953303049165584 |
| S34A12T04 | numeric | 275 | 9.133333333333333 | 35 | 67 | 25.90213039280531 |
| S34A12T05 | numeric | 234 | 7.766666666666667 | 35 | 26 | 17.624159004188698 |
| S34A13T01 | numeric | 329 | 10.933333333333334 | 31 | 1 | 30.547584669659543 |
| S34A13T02 | numeric | 295 | 9.8 | 52 | 0 | 30.640890416142554 |
| S34A13T03 | numeric | 284 | 9.433333333333334 | 40 | 2 | 29.883951279774834 |
| S34A13T04 | numeric | 355 | 11.8 | 34 | 88 | 42.43599897111305 |
| S34A13T05 | numeric | 250 | 8.3 | 34 | 80 | 27.514241004761896 |
| S34A14T04 | numeric | 305 | 10.133333333333333 | 29 | 81 | 117.18717663399842 |
| S34A14T01 | missing | 0 | — | — | — | — |
| S34A14T02 | missing | 0 | — | — | — | — |
| S34A14T03 | missing | 0 | — | — | — | — |
| S34A14T05 | missing | 0 | — | — | — | — |

## Temporal audit

| Trial | Distinct poses | Repeated transitions (%) | Longest constant span (s) |
|---|---:|---:|---:|
| S34A10T01 | 226 | 25.25 | 2.533 |
| S34A10T02 | 188 | 25.20 | 2.100 |
| S34A10T03 | 268 | 5.32 | 0.300 |
| S34A10T04 | 312 | 6.04 | 0.567 |
| S34A10T05 | 201 | 27.54 | 2.200 |
| S34A11T01 | 264 | 6.07 | 0.400 |
| S34A11T02 | 195 | 34.24 | 3.367 |
| S34A11T03 | 180 | 38.70 | 3.767 |
| S34A11T04 | 181 | 35.25 | 2.800 |
| S34A11T05 | 203 | 20.78 | 0.900 |
| S34A12T01 | 190 | 15.62 | 0.833 |
| S34A12T02 | 271 | 3.23 | 0.300 |
| S34A12T03 | 229 | 25.73 | 2.267 |
| S34A12T04 | 208 | 24.45 | 1.867 |
| S34A12T05 | 208 | 11.16 | 0.567 |
| S34A13T01 | 328 | 0.30 | 0.033 |
| S34A13T02 | 295 | 0.00 | 0.000 |
| S34A13T03 | 282 | 0.71 | 0.033 |
| S34A13T04 | 267 | 24.86 | 2.900 |
| S34A13T05 | 170 | 32.13 | 2.667 |
| S34A14T04 | 224 | 26.64 | 1.000 |

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



## Derived blank-row repairs and trial availability

The supplied archive contains 21 numeric trials out of 25 expected. The derived repair layer replaced 0 fully blank frames across 0 gaps. Original files were not modified. Short gaps of 1–3 frames use the preceding valid row; longer internal gaps use per-coordinate linear interpolation; boundary gaps use the nearest valid row. Entire missing or empty trials are never synthesized.

See `../../REPAIR_ASSESSMENT.md` for trial-level repair fractions, boundary carries, and missing/empty trials.
