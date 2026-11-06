# S45 audit findings

Clips passing numeric input checks: 25; empty: 0; missing expected: 0; invalid: 0; analyzed frames: 8413.

Review-flagged destination frames: 1043. Duplicate rows within clips: 1088.

These are data-quality screening results, not validated fall labels or anatomical CoM. The audit does not repair inputs itself; when a derived repaired-data directory is supplied, consult its repair manifest and frame mask. Invalid trials remain in raw/ and manifest.json but are withheld from calculations.

| Trial | Status | Frames | Span (s) | Review frames | Duplicate rows | Scale range (%) |
|---|---|---:|---:|---:|---:|---:|
| S45A10T01 | numeric | 421 | 14.0 | 43 | 89 | 46.19019885425482 |
| S45A10T02 | numeric | 422 | 14.033333333333333 | 29 | 41 | 36.936832616069594 |
| S45A10T03 | numeric | 331 | 11.0 | 10 | 12 | 23.413365012997602 |
| S45A10T04 | numeric | 333 | 11.066666666666666 | 39 | 2 | 32.484439441181536 |
| S45A10T05 | numeric | 331 | 11.0 | 52 | 22 | 27.19481881044583 |
| S45A11T01 | numeric | 331 | 11.0 | 44 | 13 | 89.85869194158991 |
| S45A11T02 | numeric | 332 | 11.033333333333333 | 44 | 20 | 46.35454036462794 |
| S45A11T03 | numeric | 332 | 11.033333333333333 | 57 | 2 | 45.26870106212466 |
| S45A11T04 | numeric | 332 | 11.033333333333333 | 23 | 89 | 14.182645025869878 |
| S45A11T05 | numeric | 331 | 11.0 | 51 | 7 | 48.57357615821678 |
| S45A12T01 | numeric | 331 | 11.0 | 62 | 14 | 44.87277822968962 |
| S45A12T02 | numeric | 331 | 11.0 | 43 | 7 | 29.10486903675258 |
| S45A12T03 | numeric | 332 | 11.033333333333333 | 35 | 88 | 72.34517918537276 |
| S45A12T04 | numeric | 331 | 11.0 | 55 | 3 | 85.77253705943062 |
| S45A12T05 | numeric | 333 | 11.066666666666666 | 41 | 7 | 33.90110066397381 |
| S45A13T01 | numeric | 332 | 11.033333333333333 | 59 | 6 | 24.097369306415484 |
| S45A13T02 | numeric | 276 | 9.166666666666666 | 47 | 163 | 74.75985758247619 |
| S45A13T03 | numeric | 332 | 11.033333333333333 | 60 | 1 | 50.55116238894941 |
| S45A13T04 | numeric | 331 | 11.0 | 29 | 2 | 23.460060987944797 |
| S45A13T05 | numeric | 331 | 11.0 | 20 | 4 | 43.062423828579895 |
| S45A14T01 | numeric | 331 | 11.0 | 43 | 71 | 18.94907538581869 |
| S45A14T02 | numeric | 332 | 11.033333333333333 | 50 | 22 | 21.331709508914678 |
| S45A14T03 | numeric | 331 | 11.0 | 38 | 40 | 23.81557979163047 |
| S45A14T04 | numeric | 331 | 11.0 | 25 | 277 | 27.373114054183922 |
| S45A14T05 | numeric | 332 | 11.033333333333333 | 44 | 86 | 26.954436643931047 |

## Temporal audit

| Trial | Distinct poses | Repeated transitions (%) | Longest constant span (s) |
|---|---:|---:|---:|
| S45A10T01 | 332 | 21.19 | 2.867 |
| S45A10T02 | 381 | 9.74 | 1.167 |
| S45A10T03 | 319 | 3.64 | 0.400 |
| S45A10T04 | 331 | 0.60 | 0.033 |
| S45A10T05 | 309 | 6.67 | 0.267 |
| S45A11T01 | 318 | 3.94 | 0.267 |
| S45A11T02 | 312 | 6.04 | 0.600 |
| S45A11T03 | 330 | 0.60 | 0.033 |
| S45A11T04 | 243 | 26.89 | 2.967 |
| S45A11T05 | 324 | 2.12 | 0.233 |
| S45A12T01 | 317 | 4.24 | 0.267 |
| S45A12T02 | 324 | 2.12 | 0.067 |
| S45A12T03 | 244 | 26.59 | 2.300 |
| S45A12T04 | 328 | 0.91 | 0.033 |
| S45A12T05 | 326 | 2.11 | 0.133 |
| S45A13T01 | 326 | 1.81 | 0.067 |
| S45A13T02 | 113 | 59.27 | 4.633 |
| S45A13T03 | 331 | 0.30 | 0.033 |
| S45A13T04 | 329 | 0.61 | 0.033 |
| S45A13T05 | 327 | 1.21 | 0.033 |
| S45A14T01 | 260 | 21.52 | 1.933 |
| S45A14T02 | 310 | 6.65 | 0.633 |
| S45A14T03 | 291 | 12.12 | 1.267 |
| S45A14T04 | 54 | 83.94 | 6.600 |
| S45A14T05 | 246 | 25.98 | 2.533 |

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

The supplied archive contains 25 numeric trials out of 25 expected. The derived repair layer replaced 0 fully blank frames across 0 gaps. Original files were not modified. Short gaps of 1–3 frames use the preceding valid row; longer internal gaps use per-coordinate linear interpolation; boundary gaps use the nearest valid row. Entire missing or empty trials are never synthesized.

See `../../REPAIR_ASSESSMENT.md` for trial-level repair fractions, boundary carries, and missing/empty trials.
