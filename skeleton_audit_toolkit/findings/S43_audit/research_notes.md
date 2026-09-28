# S43 research review — 2026-09-26

## Decision

S43 improves archive completeness and observed recording length over S50. Use it for visual inspection and pipeline development. Defer physical parameter identification, derivative-based fitting and perturbation-driven synthesis until repeated coordinates and shared scale changes are explained. File completeness is not a training-readiness test.

## Subject and model

Female; 130 lb = 58.9670081 kg; 5 ft 4 in = 1.6256 m. Female anthropometric source fractions are normalized from their rounded total 0.9999. HEAD/HAND and ANKLE/FOOT mappings remain approximations. Age was not provided: confirm adult-model applicability. Nominal 30 FPS and fall labels are inherited from the described study protocol; timestamps, confidence, floor calibration, contact and force measurements are unavailable.

## Main observations

- All 25 expected files (five trials each A10–A14) are present, nonempty, parse as 96 finite XYZ columns, and pass input checks. There are 6,080 frames and no NaN/Inf values.
- First-to-last clip spans are 5.167–10.033 nominal seconds. Zero exact shared frames were found between different trials.
- There are 1,390 duplicate rows beyond the first occurrence of each pose (22.86% of 6,080 rows). All 1,390 are also consecutive repeat transitions (22.96% of 6,055 adjacent-frame transitions). Do not interpret this as a measured dropped-frame rate.
- S43A10T01 has 182 rows but only three distinct poses. Frames 0–179 are identical: 180 rows spanning 5.967 nominal seconds. This clip should be withheld from initial fall-dynamics fitting pending correction or confirmation of the original recording.
- All 25 trials have review flags: 802 destination frames exceed a configured joint-step or scale-change threshold (13.25% of adjacent transitions). Threshold flags are screening signals, not automatic error labels. No flagged frames were removed.
- Common limb-scale range is 9.119–80.396%. The minimum pairwise correlation among the eight limb-length time series across all trials is 0.99999999949. Maximum within-frame spread among their normalized lengths stays below 2.6e-6. This is consistent with common multiplicative scaling; it does not identify its source or prove that each coordinate is wrong. Request the export/preprocessing code.
- S43A14T04 has the largest common-scale range (80.396%). S43A14T01 has the largest adjacent-frame joint step (1.19694 m). Both merit frame-by-frame review.
- All 25 initial head-to-mid-ankle directions are within 60 degrees of camera negative Y. This differs from S50 (18/19 beyond 60 degrees) and is consistent with better initial upright coverage under the camera-axis assumption. It is not a calibrated body inclination or proof that every clip contains a complete fall.
- Inspected A10 snapshots show upright-to-lowered/horizontal sequences in T02–T05, while T01 is nearly constant. Several clips return toward upright by their final snapshots; this alone does not establish a controlled recovery trial or validate the event labels.



## Evidence locations

- results/manifest.json and trial_summary.csv: completeness, hashes, per-trial measurements.
- results/temporal_summary.csv and constant_pose_runs.csv: exact repeated intervals.
- results/review_events.csv: frame pairs and thresholds for manual review.
- results/plots/temporal_repeats.png and shared_limb_scaling.png: repeat and scale evidence.
- results/plots/A10_skeleton_snapshots.png: visual examples above.
- results/plots/real_CoM_comparison.png: camera-axis displacement of female segment CoM proxy, not floor-referenced height.



## Comparison with S50


| Measure                         | S50         | S43          |
| ------------------------------- | ----------- | ------------ |
| Numeric clips / expected        | 19/25       | 25/25        |
| Empty files                     | 6           | 0            |
| Frames                          | 895         | 6,080        |
| Clip span, nominal seconds      | 0.333–3.033 | 5.167–10.033 |
| Duplicate rows within clips     | 6           | 1,390        |
| Flagged destination frames      | 136         | 802          |
| Within-trial common-scale range | 2.35–39.97% | 9.12–80.40%  |


The larger flag count partly reflects many more frames. Counts alone should not rank tracking quality across subjects.

## Questions and next actions for the team

1. Inspect the original S43A10T01 recording and export: why are the first 180 skeleton rows identical?
2. Were skeletons retargeted, normalized, resized or transformed per frame? Can we obtain original SDK positions, timestamps and body-tracking confidence?
3. Confirm XYZ units/order, original sampling cadence and any trimming/padding. Repeated exported coordinates should not be silently deleted and retimed.
4. Confirm subject age/adult-model applicability and camera-to-floor calibration for vertical and horizontal CoM analysis.
5. Annotate fall onset, descent, contact and post-event motion from synchronized video or full skeleton playback. Inspect all frame-level flags in candidate windows before choosing a fall family.
6. After resolving export quality, select complete trials, preserve trial-level evaluation splits, and begin reconstruction before attempting inferred forces or hypothetical perturbations.

No synthetic falls, forces, BoS, PINN training or clinical conclusions were produced in this audit.