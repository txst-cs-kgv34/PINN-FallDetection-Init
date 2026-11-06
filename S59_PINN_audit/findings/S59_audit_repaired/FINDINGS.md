# S59 audit findings

Clips passing numeric input checks: 21; empty: 0; missing expected: 4; invalid: 0; analyzed frames: 4181.

Review-flagged destination frames: 402. Duplicate rows within clips: 96.

These are data-quality screening results, not validated fall labels or anatomical CoM. The audit does not repair inputs itself; when a derived repaired-data directory is supplied, consult its repair manifest and frame mask. Invalid trials remain in raw/ and manifest.json but are withheld from calculations.

| Trial | Status | Frames | Span (s) | Review frames | Duplicate rows | Scale range (%) |
|---|---|---:|---:|---:|---:|---:|
| S59A10T01 | numeric | 189 | 6.266666666666667 | 36 | 0 | 27.602472539804744 |
| S59A10T02 | numeric | 224 | 7.433333333333334 | 40 | 1 | 37.41617645337012 |
| S59A10T03 | numeric | 231 | 7.666666666666667 | 17 | 8 | 46.18454641364869 |
| S59A10T04 | numeric | 241 | 8.0 | 36 | 15 | 36.67982072090501 |
| S59A10T05 | numeric | 122 | 4.033333333333333 | 17 | 1 | 31.934738294060814 |
| S59A11T01 | numeric | 166 | 5.5 | 15 | 1 | 22.036763108082248 |
| S59A11T02 | numeric | 206 | 6.833333333333333 | 17 | 12 | 18.98439998393764 |
| S59A11T03 | numeric | 130 | 4.3 | 9 | 3 | 21.491867519717346 |
| S59A11T04 | numeric | 241 | 8.0 | 15 | 10 | 21.53560046343921 |
| S59A11T05 | numeric | 240 | 7.966666666666667 | 14 | 10 | 22.230977666013008 |
| S59A12T01 | numeric | 251 | 8.333333333333334 | 3 | 1 | 23.52683470510284 |
| S59A12T02 | numeric | 136 | 4.5 | 17 | 0 | 43.484154066453144 |
| S59A12T03 | numeric | 236 | 7.833333333333333 | 23 | 4 | 29.220290390266612 |
| S59A12T04 | numeric | 207 | 6.866666666666666 | 30 | 1 | 18.410296274718576 |
| S59A12T05 | numeric | 218 | 7.233333333333333 | 39 | 6 | 35.931753949417036 |
| S59A13T01 | numeric | 171 | 5.666666666666667 | 17 | 6 | 14.222157366850375 |
| S59A13T02 | numeric | 201 | 6.666666666666667 | 9 | 3 | 99.50136963833849 |
| S59A13T03 | numeric | 223 | 7.4 | 7 | 4 | 9.901382411556693 |
| S59A13T04 | numeric | 223 | 7.4 | 12 | 1 | 15.279900779379352 |
| S59A13T05 | numeric | 168 | 5.566666666666666 | 14 | 2 | 13.161142534122238 |
| S59A14T01 | numeric | 157 | 5.2 | 15 | 7 | 18.420298944844937 |
| S59A14T02 | missing | 0 | — | — | — | — |
| S59A14T03 | missing | 0 | — | — | — | — |
| S59A14T04 | missing | 0 | — | — | — | — |
| S59A14T05 | missing | 0 | — | — | — | — |

## Temporal audit

| Trial | Distinct poses | Repeated transitions (%) | Longest constant span (s) |
|---|---:|---:|---:|
| S59A10T01 | 189 | 0.00 | 0.000 |
| S59A10T02 | 223 | 0.45 | 0.033 |
| S59A10T03 | 223 | 3.48 | 0.100 |
| S59A10T04 | 226 | 6.25 | 0.167 |
| S59A10T05 | 121 | 0.83 | 0.033 |
| S59A11T01 | 165 | 0.61 | 0.033 |
| S59A11T02 | 194 | 5.85 | 0.133 |
| S59A11T03 | 127 | 2.33 | 0.067 |
| S59A11T04 | 231 | 4.17 | 0.100 |
| S59A11T05 | 230 | 4.18 | 0.167 |
| S59A12T01 | 250 | 0.40 | 0.033 |
| S59A12T02 | 136 | 0.00 | 0.000 |
| S59A12T03 | 232 | 1.70 | 0.033 |
| S59A12T04 | 206 | 0.49 | 0.033 |
| S59A12T05 | 212 | 2.76 | 0.167 |
| S59A13T01 | 165 | 3.53 | 0.100 |
| S59A13T02 | 198 | 1.50 | 0.033 |
| S59A13T03 | 219 | 1.80 | 0.033 |
| S59A13T04 | 222 | 0.45 | 0.033 |
| S59A13T05 | 166 | 1.20 | 0.067 |
| S59A14T01 | 150 | 4.49 | 0.100 |

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

The supplied archive contains 21 numeric trials out of 25 expected. The derived repair layer replaced 9 fully blank frames across 4 gaps. Original files were not modified. Short gaps of 1–3 frames use the preceding valid row; longer internal gaps use per-coordinate linear interpolation; boundary gaps use the nearest valid row. Entire missing or empty trials are never synthesized.

See `../../REPAIR_ASSESSMENT.md` for trial-level repair fractions, boundary carries, and missing/empty trials.

<!-- MANUAL_A11_PHASE_UPDATE_START -->
## Manual A11 phase update

- Marked trials: 5.
- Strict phase-order validation: **pass**.
- Manual observation: All A11 trials were phase marked.
- Camera-axis interpretation: `camera_x`.
- Modeling decision: `usable`.
- Recommendation: Usable for the planned A11 analysis, subject to the existing audit flags and the provisional nature of skeleton-observed contact.

See `../../analysis_inputs/FRONTFALL_PHASE_STATUS.md` for trial-level repair overlap and phase frames. The automatic suggestions are superseded by the manual notes.
<!-- MANUAL_A11_PHASE_UPDATE_END -->
