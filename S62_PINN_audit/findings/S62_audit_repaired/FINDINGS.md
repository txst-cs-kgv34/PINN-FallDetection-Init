# S62 audit findings

Clips passing numeric input checks: 25; empty: 0; missing expected: 0; invalid: 0; analyzed frames: 4390.

Review-flagged destination frames: 668. Duplicate rows within clips: 50.

These are data-quality screening results, not validated fall labels or anatomical CoM. This run audits the repaired numeric copies; the untouched original audit remains in `../S62_audit`. Invalid trials would remain in `raw/` and `manifest.json` but be withheld from calculations.

## Blank-row repair assessment

The repair layer replaced 109 fully blank frames in 11 gaps and preserved a
frame-level mask in `../../repaired_data/S62/repaired_frames.csv`. Gaps of 1–3
frames were forward-filled; longer internal gaps were linearly interpolated.
The five A10 trials contain 7.5%–16.7% repaired frames, so A10-derived results
need repair-exclusion or leave-one-trial-out sensitivity analyses. S62A12T04 has
4/151 repaired frames (2.6%) and S62A14T04 has 2/186 (1.1%).

| Trial | Status | Frames | Span (s) | Review frames | Duplicate rows | Scale range (%) |
|---|---|---:|---:|---:|---:|---:|
| S62A10T01 | numeric | 222 | 7.366666666666666 | 18 | 1 | 21.34603200163625 |
| S62A10T02 | numeric | 172 | 5.7 | 24 | 3 | 60.4220530751407 |
| S62A10T03 | numeric | 229 | 7.6 | 24 | 14 | 26.971588111312215 |
| S62A10T04 | numeric | 180 | 5.966666666666667 | 12 | 1 | 33.21765883730174 |
| S62A10T05 | numeric | 173 | 5.733333333333333 | 20 | 6 | 19.156072496277375 |
| S62A11T01 | numeric | 225 | 7.466666666666667 | 30 | 0 | 36.41843191061729 |
| S62A11T02 | numeric | 146 | 4.833333333333333 | 30 | 2 | 38.69770754204789 |
| S62A11T03 | numeric | 201 | 6.666666666666667 | 39 | 0 | 61.31684281455587 |
| S62A11T04 | numeric | 153 | 5.066666666666666 | 23 | 2 | 30.810853269908932 |
| S62A11T05 | numeric | 214 | 7.1 | 29 | 6 | 36.759365226229605 |
| S62A12T01 | numeric | 177 | 5.866666666666666 | 37 | 0 | 67.44769455560254 |
| S62A12T02 | numeric | 144 | 4.766666666666667 | 15 | 2 | 32.44237382765862 |
| S62A12T03 | numeric | 175 | 5.8 | 26 | 0 | 51.59623043508035 |
| S62A12T04 | numeric | 151 | 5.0 | 38 | 0 | 84.55544360770718 |
| S62A12T05 | numeric | 150 | 4.966666666666667 | 39 | 0 | 100.5783739590023 |
| S62A13T01 | numeric | 155 | 5.133333333333334 | 43 | 2 | 78.93686987867396 |
| S62A13T02 | numeric | 177 | 5.866666666666666 | 29 | 2 | 23.851896499706783 |
| S62A13T03 | numeric | 156 | 5.166666666666667 | 26 | 0 | 63.487130107210966 |
| S62A13T04 | numeric | 202 | 6.7 | 15 | 0 | 32.1399522480057 |
| S62A13T05 | numeric | 191 | 6.333333333333333 | 14 | 1 | 70.0686834495184 |
| S62A14T01 | numeric | 159 | 5.266666666666667 | 32 | 0 | 36.39369246774464 |
| S62A14T02 | numeric | 155 | 5.133333333333334 | 31 | 0 | 35.668102827031255 |
| S62A14T03 | numeric | 158 | 5.233333333333333 | 32 | 0 | 50.80186745216126 |
| S62A14T04 | numeric | 186 | 6.166666666666667 | 25 | 4 | 43.21341321475873 |
| S62A14T05 | numeric | 139 | 4.6 | 17 | 4 | 104.50294824322475 |

## Temporal audit

| Trial | Distinct poses | Repeated transitions (%) | Longest constant span (s) |
|---|---:|---:|---:|
| S62A10T01 | 221 | 0.45 | 0.033 |
| S62A10T02 | 169 | 1.75 | 0.033 |
| S62A10T03 | 215 | 6.14 | 0.100 |
| S62A10T04 | 179 | 0.56 | 0.033 |
| S62A10T05 | 167 | 3.49 | 0.067 |
| S62A11T01 | 225 | 0.00 | 0.000 |
| S62A11T02 | 144 | 1.38 | 0.067 |
| S62A11T03 | 201 | 0.00 | 0.000 |
| S62A11T04 | 151 | 1.32 | 0.033 |
| S62A11T05 | 208 | 2.82 | 0.100 |
| S62A12T01 | 177 | 0.00 | 0.000 |
| S62A12T02 | 142 | 1.40 | 0.033 |
| S62A12T03 | 175 | 0.00 | 0.000 |
| S62A12T04 | 151 | 0.00 | 0.000 |
| S62A12T05 | 150 | 0.00 | 0.000 |
| S62A13T01 | 153 | 1.30 | 0.067 |
| S62A13T02 | 175 | 1.14 | 0.033 |
| S62A13T03 | 156 | 0.00 | 0.000 |
| S62A13T04 | 202 | 0.00 | 0.000 |
| S62A13T05 | 190 | 0.53 | 0.033 |
| S62A14T01 | 159 | 0.00 | 0.000 |
| S62A14T02 | 155 | 0.00 | 0.000 |
| S62A14T03 | 158 | 0.00 | 0.000 |
| S62A14T04 | 182 | 2.16 | 0.067 |
| S62A14T05 | 135 | 2.90 | 0.033 |

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

