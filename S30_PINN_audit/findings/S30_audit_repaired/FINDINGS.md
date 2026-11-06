# S30 audit findings

Clips passing numeric input checks: 25; empty: 0; missing expected: 0; invalid: 0; analyzed frames: 5571.

Review-flagged destination frames: 841. Duplicate rows within clips: 1260.

These are data-quality screening results, not validated fall labels or anatomical CoM. The audit does not repair inputs itself; when a derived repaired-data directory is supplied, consult its repair manifest and frame mask. Invalid trials remain in raw/ and manifest.json but are withheld from calculations.

| Trial | Status | Frames | Span (s) | Review frames | Duplicate rows | Scale range (%) |
|---|---|---:|---:|---:|---:|---:|
| S30A10T01 | numeric | 226 | 7.5 | 37 | 12 | 18.531866841099976 |
| S30A10T02 | numeric | 205 | 6.8 | 26 | 5 | 55.454647163546596 |
| S30A10T03 | numeric | 206 | 6.833333333333333 | 20 | 64 | 68.53388712750122 |
| S30A10T04 | numeric | 203 | 6.733333333333333 | 44 | 17 | 34.9643513276811 |
| S30A10T05 | numeric | 182 | 6.033333333333333 | 19 | 61 | 39.43292509671288 |
| S30A11T01 | numeric | 229 | 7.6 | 21 | 86 | 23.431897429644888 |
| S30A11T02 | numeric | 251 | 8.333333333333334 | 18 | 88 | 28.246579128675855 |
| S30A11T03 | numeric | 232 | 7.7 | 23 | 67 | 49.96300371971812 |
| S30A11T04 | numeric | 234 | 7.766666666666667 | 25 | 62 | 39.16897124099261 |
| S30A11T05 | numeric | 231 | 7.666666666666667 | 31 | 57 | 40.27178197892294 |
| S30A12T01 | numeric | 206 | 6.833333333333333 | 49 | 2 | 33.86565266910904 |
| S30A12T02 | numeric | 211 | 7.0 | 34 | 2 | 69.84610806044759 |
| S30A12T03 | numeric | 128 | 4.233333333333333 | 36 | 5 | 42.437268768711476 |
| S30A12T04 | numeric | 214 | 7.1 | 58 | 6 | 26.486796739187678 |
| S30A12T05 | numeric | 216 | 7.166666666666667 | 60 | 0 | 28.556708895795936 |
| S30A13T01 | numeric | 203 | 6.733333333333333 | 19 | 2 | 14.521436407344911 |
| S30A13T02 | numeric | 219 | 7.266666666666667 | 20 | 70 | 17.210503112848087 |
| S30A13T03 | numeric | 208 | 6.9 | 35 | 73 | 40.40802019129175 |
| S30A13T04 | numeric | 208 | 6.9 | 22 | 70 | 26.127871205196975 |
| S30A13T05 | numeric | 194 | 6.433333333333334 | 32 | 66 | 23.763066181356617 |
| S30A14T01 | numeric | 335 | 11.133333333333333 | 57 | 86 | 65.52449853854014 |
| S30A14T02 | numeric | 262 | 8.7 | 45 | 84 | 38.73016227366111 |
| S30A14T03 | numeric | 298 | 9.9 | 34 | 127 | 41.367655945262946 |
| S30A14T04 | numeric | 240 | 7.966666666666667 | 48 | 57 | 30.910305997455477 |
| S30A14T05 | numeric | 230 | 7.633333333333334 | 28 | 91 | 69.16228350043343 |

## Temporal audit

| Trial | Distinct poses | Repeated transitions (%) | Longest constant span (s) |
|---|---:|---:|---:|
| S30A10T01 | 214 | 5.33 | 0.367 |
| S30A10T02 | 200 | 2.45 | 0.167 |
| S30A10T03 | 142 | 31.22 | 1.733 |
| S30A10T04 | 186 | 8.42 | 0.333 |
| S30A10T05 | 121 | 33.70 | 2.000 |
| S30A11T01 | 143 | 37.72 | 2.833 |
| S30A11T02 | 163 | 35.20 | 2.933 |
| S30A11T03 | 165 | 29.00 | 2.033 |
| S30A11T04 | 172 | 26.61 | 1.667 |
| S30A11T05 | 174 | 24.78 | 1.367 |
| S30A12T01 | 204 | 0.98 | 0.033 |
| S30A12T02 | 209 | 0.95 | 0.033 |
| S30A12T03 | 123 | 3.94 | 0.100 |
| S30A12T04 | 208 | 2.82 | 0.100 |
| S30A12T05 | 216 | 0.00 | 0.000 |
| S30A13T01 | 201 | 0.99 | 0.067 |
| S30A13T02 | 149 | 32.11 | 2.300 |
| S30A13T03 | 135 | 35.27 | 2.400 |
| S30A13T04 | 138 | 33.82 | 2.300 |
| S30A13T05 | 128 | 34.20 | 2.067 |
| S30A14T01 | 249 | 25.75 | 2.067 |
| S30A14T02 | 178 | 32.18 | 2.800 |
| S30A14T03 | 171 | 42.76 | 4.200 |
| S30A14T04 | 183 | 23.85 | 1.700 |
| S30A14T05 | 139 | 39.74 | 2.667 |

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

<!-- MANUAL_A11_PHASE_UPDATE_START -->
## Manual A11 phase update

- Five A11 trials have complete, strictly ordered manual phase marks.
- Manual observation: All A11 trials were phase marked. Front-fall motion is slightly tilted toward the camera, so it has a camera-Z component in addition to camera X.
- Camera-axis interpretation: `camera_x_with_z_component`.
- Modeling decision: `usable_after_axis_alignment`.
- Recommendation: Use S30 after aligning the subject-specific horizontal fall direction with Model B's progression coordinate (for example, an X-Z rotation or projection onto the observed horizontal fall direction). Do not treat the Z component as generalization error.

See `../../analysis_inputs/FRONTFALL_PHASE_STATUS.md` for the exact phase frames. Automatic phase suggestions are superseded by the manual notes.
<!-- MANUAL_A11_PHASE_UPDATE_END -->
