# S48 audit findings

Clips passing numeric input checks: 24; empty: 0; missing expected: 0; invalid: 1; analyzed frames: 3463.

Review-flagged destination frames: 904. Duplicate rows within clips: 103.

These are data-quality screening results, not validated fall labels or anatomical CoM. The audit does not repair inputs itself; when a derived repaired-data directory is supplied, consult its repair manifest and frame mask. Invalid trials remain in raw/ and manifest.json but are withheld from calculations.

| Trial | Status | Frames | Span (s) | Review frames | Duplicate rows | Scale range (%) |
|---|---|---:|---:|---:|---:|---:|
| S48A10T01 | numeric | 166 | 5.5 | 26 | 11 | 22.54430108757508 |
| S48A10T02 | numeric | 119 | 3.933333333333333 | 13 | 0 | 34.927216293994604 |
| S48A10T03 | numeric | 114 | 3.7666666666666666 | 46 | 0 | 86.36813428564577 |
| S48A10T04 | numeric | 191 | 6.333333333333333 | 65 | 1 | 116.80351573133403 |
| S48A10T05 | numeric | 142 | 4.7 | 58 | 7 | 87.3628792797214 |
| S48A11T01 | numeric | 186 | 6.166666666666667 | 36 | 0 | 48.47254391646012 |
| S48A11T02 | numeric | 170 | 5.633333333333334 | 62 | 2 | 181.9218484300265 |
| S48A11T03 | numeric | 148 | 4.9 | 43 | 2 | 31.474342960967515 |
| S48A11T04 | numeric | 138 | 4.566666666666666 | 42 | 0 | 39.80436342948508 |
| S48A11T05 | numeric | 130 | 4.3 | 16 | 39 | 28.550561069991588 |
| S48A12T01 | numeric | 42 | 1.3666666666666667 | 13 | 0 | 41.127345516424384 |
| S48A12T02 | numeric | 96 | 3.1666666666666665 | 36 | 11 | 44.07643750902941 |
| S48A12T03 | numeric | 173 | 5.733333333333333 | 34 | 8 | 32.660821125490244 |
| S48A12T04 | numeric | 190 | 6.3 | 34 | 1 | 71.95475172302285 |
| S48A12T05 | numeric | 163 | 5.4 | 28 | 4 | 79.31403831042152 |
| S48A13T01 | numeric | 107 | 3.533333333333333 | 47 | 0 | 76.71221448323902 |
| S48A13T02 | numeric | 89 | 2.933333333333333 | 18 | 1 | 14.602994292268123 |
| S48A13T03 | numeric | 72 | 2.3666666666666667 | 20 | 0 | 33.96554315240412 |
| S48A13T04 | numeric | 172 | 5.7 | 32 | 1 | 35.145047770917536 |
| S48A13T05 | numeric | 110 | 3.6333333333333333 | 25 | 7 | 47.38112824196155 |
| S48A14T01 | numeric | 158 | 5.233333333333333 | 52 | 6 | 74.78554854092 |
| S48A14T02 | numeric | 180 | 5.966666666666667 | 73 | 1 | 53.14237822106816 |
| S48A14T03 | numeric | 185 | 6.133333333333334 | 47 | 1 | 41.092871105916664 |
| S48A14T04 | invalid | 0 | — | — | — | — |
| S48A14T05 | numeric | 222 | 7.366666666666666 | 38 | 0 | 24.01138727948733 |

## Temporal audit

| Trial | Distinct poses | Repeated transitions (%) | Longest constant span (s) |
|---|---:|---:|---:|
| S48A10T01 | 155 | 6.67 | 0.167 |
| S48A10T02 | 119 | 0.00 | 0.000 |
| S48A10T03 | 114 | 0.00 | 0.000 |
| S48A10T04 | 190 | 0.53 | 0.033 |
| S48A10T05 | 135 | 4.96 | 0.067 |
| S48A11T01 | 186 | 0.00 | 0.000 |
| S48A11T02 | 168 | 1.18 | 0.033 |
| S48A11T03 | 146 | 1.36 | 0.067 |
| S48A11T04 | 138 | 0.00 | 0.000 |
| S48A11T05 | 91 | 30.23 | 1.300 |
| S48A12T01 | 42 | 0.00 | 0.000 |
| S48A12T02 | 85 | 11.58 | 0.333 |
| S48A12T03 | 165 | 4.65 | 0.133 |
| S48A12T04 | 189 | 0.53 | 0.033 |
| S48A12T05 | 159 | 2.47 | 0.067 |
| S48A13T01 | 107 | 0.00 | 0.000 |
| S48A13T02 | 88 | 1.14 | 0.033 |
| S48A13T03 | 72 | 0.00 | 0.000 |
| S48A13T04 | 171 | 0.58 | 0.033 |
| S48A13T05 | 103 | 6.42 | 0.067 |
| S48A14T01 | 152 | 3.82 | 0.100 |
| S48A14T02 | 179 | 0.56 | 0.033 |
| S48A14T03 | 184 | 0.54 | 0.033 |
| S48A14T05 | 222 | 0.00 | 0.000 |

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

The supplied archive contains 24 numeric trials out of 25 expected. The derived repair layer replaced 329 fully blank frames across 40 gaps. Original files were not modified. Short gaps of 1–3 frames use the preceding valid row; longer internal gaps use per-coordinate linear interpolation; boundary gaps use the nearest valid row. Entire missing or empty trials are never synthesized.

See `../../REPAIR_ASSESSMENT.md` for trial-level repair fractions, boundary carries, and missing/empty trials.
