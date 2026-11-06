# S32 audit findings

Clips passing numeric input checks: 21; empty: 0; missing expected: 4; invalid: 0; analyzed frames: 5527.

Review-flagged destination frames: 747. Duplicate rows within clips: 358.

These are data-quality screening results, not validated fall labels or anatomical CoM. The audit does not repair inputs itself; when a derived repaired-data directory is supplied, consult its repair manifest and frame mask. Invalid trials remain in raw/ and manifest.json but are withheld from calculations.

| Trial | Status | Frames | Span (s) | Review frames | Duplicate rows | Scale range (%) |
|---|---|---:|---:|---:|---:|---:|
| S32A10T01 | numeric | 244 | 8.1 | 41 | 0 | 32.519016437337896 |
| S32A10T02 | numeric | 244 | 8.1 | 22 | 1 | 23.30931338655948 |
| S32A10T03 | numeric | 269 | 8.933333333333334 | 20 | 1 | 26.98510403619421 |
| S32A10T04 | numeric | 258 | 8.566666666666666 | 38 | 8 | 41.305494194621176 |
| S32A10T05 | numeric | 291 | 9.666666666666666 | 63 | 3 | 49.67098123955991 |
| S32A11T01 | numeric | 299 | 9.933333333333334 | 30 | 85 | 36.05039770832163 |
| S32A11T02 | numeric | 289 | 9.6 | 40 | 1 | 33.51645959411829 |
| S32A11T03 | numeric | 284 | 9.433333333333334 | 17 | 113 | 36.07469706268886 |
| S32A11T04 | numeric | 300 | 9.966666666666667 | 40 | 0 | 34.87135856211741 |
| S32A11T05 | numeric | 321 | 10.666666666666666 | 21 | 96 | 14.566743718972619 |
| S32A12T01 | numeric | 233 | 7.733333333333333 | 26 | 0 | 32.57205558086322 |
| S32A12T02 | numeric | 223 | 7.4 | 38 | 0 | 23.16669000769389 |
| S32A12T03 | numeric | 270 | 8.966666666666667 | 40 | 1 | 28.479132606799794 |
| S32A12T04 | numeric | 222 | 7.366666666666666 | 45 | 1 | 18.375207438539753 |
| S32A12T05 | numeric | 230 | 7.633333333333334 | 39 | 0 | 15.614932569263896 |
| S32A13T01 | numeric | 279 | 9.266666666666667 | 23 | 2 | 22.309965169251456 |
| S32A13T02 | numeric | 227 | 7.533333333333333 | 26 | 3 | 17.39341977630806 |
| S32A13T03 | numeric | 242 | 8.033333333333333 | 35 | 0 | 23.142084076081492 |
| S32A13T04 | numeric | 253 | 8.4 | 48 | 23 | 88.30275288348663 |
| S32A13T05 | numeric | 249 | 8.266666666666667 | 44 | 18 | 25.880224983891466 |
| S32A14T03 | numeric | 300 | 9.966666666666667 | 51 | 2 | 40.50371596118736 |
| S32A14T01 | missing | 0 | — | — | — | — |
| S32A14T02 | missing | 0 | — | — | — | — |
| S32A14T04 | missing | 0 | — | — | — | — |
| S32A14T05 | missing | 0 | — | — | — | — |

## Temporal audit

| Trial | Distinct poses | Repeated transitions (%) | Longest constant span (s) |
|---|---:|---:|---:|
| S32A10T01 | 244 | 0.00 | 0.000 |
| S32A10T02 | 243 | 0.41 | 0.033 |
| S32A10T03 | 268 | 0.37 | 0.033 |
| S32A10T04 | 250 | 3.11 | 0.233 |
| S32A10T05 | 288 | 1.03 | 0.033 |
| S32A11T01 | 214 | 28.52 | 2.833 |
| S32A11T02 | 288 | 0.35 | 0.033 |
| S32A11T03 | 171 | 39.93 | 3.733 |
| S32A11T04 | 300 | 0.00 | 0.000 |
| S32A11T05 | 225 | 30.00 | 3.167 |
| S32A12T01 | 233 | 0.00 | 0.000 |
| S32A12T02 | 223 | 0.00 | 0.000 |
| S32A12T03 | 269 | 0.37 | 0.033 |
| S32A12T04 | 221 | 0.45 | 0.033 |
| S32A12T05 | 230 | 0.00 | 0.000 |
| S32A13T01 | 277 | 0.72 | 0.033 |
| S32A13T02 | 224 | 1.33 | 0.100 |
| S32A13T03 | 242 | 0.00 | 0.000 |
| S32A13T04 | 230 | 9.13 | 0.333 |
| S32A13T05 | 231 | 7.26 | 0.133 |
| S32A14T03 | 298 | 0.67 | 0.033 |

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

<!-- MANUAL_A11_PHASE_UPDATE_START -->
## Manual A11 phase update

- Marked trials: 5.
- Strict phase-order validation: **pass**.
- Manual observation: All A11 trials were phase marked. Front-fall progression is toward the camera, primarily along camera Z rather than camera X.
- Camera-axis interpretation: `camera_z`.
- Modeling decision: `usable_after_axis_alignment`.
- Recommendation: Use after mapping the subject-specific horizontal fall direction to the Model B progression coordinate; do not interpret fixed camera X as the sagittal fall coordinate.

See `../../analysis_inputs/FRONTFALL_PHASE_STATUS.md` for trial-level repair overlap and phase frames. The automatic suggestions are superseded by the manual notes.
<!-- MANUAL_A11_PHASE_UPDATE_END -->
