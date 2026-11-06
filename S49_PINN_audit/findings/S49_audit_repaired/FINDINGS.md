# S49 audit findings

Clips passing numeric input checks: 23; empty: 0; missing expected: 2; invalid: 0; analyzed frames: 3027.

Review-flagged destination frames: 578. Duplicate rows within clips: 85.

These are data-quality screening results, not validated fall labels or anatomical CoM. The audit does not repair inputs itself; when a derived repaired-data directory is supplied, consult its repair manifest and frame mask. Invalid trials remain in raw/ and manifest.json but are withheld from calculations.

| Trial | Status | Frames | Span (s) | Review frames | Duplicate rows | Scale range (%) |
|---|---|---:|---:|---:|---:|---:|
| S49A10T01 | numeric | 92 | 3.033333333333333 | 5 | 0 | 7.271804693544914 |
| S49A10T02 | numeric | 158 | 5.233333333333333 | 12 | 0 | 11.195123529146201 |
| S49A10T03 | numeric | 103 | 3.4 | 6 | 3 | 14.549404898712304 |
| S49A10T04 | numeric | 172 | 5.7 | 11 | 5 | 17.333905192591814 |
| S49A10T05 | numeric | 77 | 2.533333333333333 | 14 | 0 | 16.53205274266778 |
| S49A11T01 | numeric | 101 | 3.3333333333333335 | 24 | 11 | 66.01534716303372 |
| S49A11T02 | numeric | 244 | 8.1 | 69 | 0 | 33.811605407806965 |
| S49A11T04 | numeric | 180 | 5.966666666666667 | 35 | 13 | 31.18222058726372 |
| S49A11T05 | numeric | 189 | 6.266666666666667 | 47 | 12 | 37.15913901855086 |
| S49A12T02 | numeric | 161 | 5.333333333333333 | 20 | 0 | 24.57088670398644 |
| S49A12T03 | numeric | 164 | 5.433333333333334 | 15 | 3 | 24.011682634042497 |
| S49A12T04 | numeric | 192 | 6.366666666666666 | 17 | 19 | 23.663946655916423 |
| S49A12T05 | numeric | 137 | 4.533333333333333 | 17 | 2 | 28.368332843766098 |
| S49A13T01 | numeric | 99 | 3.2666666666666666 | 38 | 5 | 63.68000545386388 |
| S49A13T02 | numeric | 146 | 4.833333333333333 | 36 | 5 | 41.956738372379036 |
| S49A13T03 | numeric | 79 | 2.6 | 7 | 0 | 13.877029329721413 |
| S49A13T04 | numeric | 116 | 3.8333333333333335 | 13 | 0 | 15.371737807166408 |
| S49A13T05 | numeric | 118 | 3.9 | 13 | 0 | 18.22205814515685 |
| S49A14T01 | numeric | 83 | 2.7333333333333334 | 19 | 3 | 39.186350313534305 |
| S49A14T02 | numeric | 104 | 3.433333333333333 | 39 | 2 | 32.416114204837676 |
| S49A14T03 | numeric | 116 | 3.8333333333333335 | 54 | 1 | 39.67873499977554 |
| S49A14T04 | numeric | 112 | 3.7 | 47 | 1 | 30.351776276478137 |
| S49A14T05 | numeric | 84 | 2.7666666666666666 | 20 | 0 | 34.581278168287334 |
| S49A11T03 | missing | 0 | — | — | — | — |
| S49A12T01 | missing | 0 | — | — | — | — |

## Temporal audit

| Trial | Distinct poses | Repeated transitions (%) | Longest constant span (s) |
|---|---:|---:|---:|
| S49A10T01 | 92 | 0.00 | 0.000 |
| S49A10T02 | 158 | 0.00 | 0.000 |
| S49A10T03 | 100 | 2.94 | 0.033 |
| S49A10T04 | 167 | 2.92 | 0.100 |
| S49A10T05 | 77 | 0.00 | 0.000 |
| S49A11T01 | 90 | 11.00 | 0.333 |
| S49A11T02 | 244 | 0.00 | 0.000 |
| S49A11T04 | 167 | 7.26 | 0.167 |
| S49A11T05 | 177 | 6.38 | 0.100 |
| S49A12T02 | 161 | 0.00 | 0.000 |
| S49A12T03 | 161 | 1.84 | 0.033 |
| S49A12T04 | 173 | 9.95 | 0.200 |
| S49A12T05 | 135 | 1.47 | 0.033 |
| S49A13T01 | 94 | 5.10 | 0.067 |
| S49A13T02 | 141 | 3.45 | 0.100 |
| S49A13T03 | 79 | 0.00 | 0.000 |
| S49A13T04 | 116 | 0.00 | 0.000 |
| S49A13T05 | 118 | 0.00 | 0.000 |
| S49A14T01 | 80 | 3.66 | 0.033 |
| S49A14T02 | 102 | 1.94 | 0.033 |
| S49A14T03 | 115 | 0.87 | 0.033 |
| S49A14T04 | 111 | 0.90 | 0.033 |
| S49A14T05 | 84 | 0.00 | 0.000 |

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

The supplied archive contains 23 numeric trials out of 25 expected. The derived repair layer replaced 55 fully blank frames across 14 gaps. Original files were not modified. Short gaps of 1–3 frames use the preceding valid row; longer internal gaps use per-coordinate linear interpolation; boundary gaps use the nearest valid row. Entire missing or empty trials are never synthesized.

See `../../REPAIR_ASSESSMENT.md` for trial-level repair fractions, boundary carries, and missing/empty trials.

<!-- MANUAL_A11_PHASE_UPDATE_START -->
## Manual A11 phase update

- Marked trials: 3.
- Strict phase-order validation: **pass**.
- Manual observation: A11T01 is an incomplete fall and should be ignored. A11T03 is absent. A11T02, A11T04, and A11T05 were phase marked.
- Camera-axis interpretation: `camera_x`.
- Modeling decision: `three_trials_usable`.
- Recommendation: Exclude A11T01 and the absent A11T03. Use only the three strictly validated marked trials: T02, T04, and T05.

See `../../analysis_inputs/FRONTFALL_PHASE_STATUS.md` for trial-level repair overlap and phase frames. The automatic suggestions are superseded by the manual notes.
<!-- MANUAL_A11_PHASE_UPDATE_END -->
