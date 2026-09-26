# S06 audit findings

Usable numeric clips: 5; empty: 0; missing expected: 0; invalid: 0; analyzed frames: 1011.

Review-flagged destination frames: 119. Duplicate rows within clips: 0.

These are data-quality screening results, not validated fall labels or anatomical CoM. No frames are repaired or interpolated. Invalid trials remain in raw/ and manifest.json but are withheld from calculations.

| Trial | Status | Frames | Span (s) | Review frames |
|---|---|---:|---:|---:|
| S06A08T01 | numeric | 252 | 8.366666666666667 | 16 |
| S06A08T02 | numeric | 161 | 5.333333333333333 | 24 |
| S06A08T03 | numeric | 195 | 6.466666666666667 | 28 |
| S06A08T04 | numeric | 210 | 6.966666666666667 | 34 |
| S06A08T05 | numeric | 193 | 6.4 | 17 |

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

![A08_skeleton_snapshots](results/plots/A08_skeleton_snapshots.png)

![real_CoM_comparison](results/plots/real_CoM_comparison.png)

![tracking_diagnostics](results/plots/tracking_diagnostics.png)

