# Fifteen-subject real-fall phase dataset

This package consolidates the manually reviewed A10–A14 fall phases for all 15 subjects and prepares compact CoM trajectories for detection and physics-informed experiments. It does not fabricate unavailable trials or complete an incomplete fall.

## Ready-to-use contents

- `manifests/trial_manifest.csv`: authoritative 375-slot inventory, validity decisions, repair quality, phase frames, camera direction, and experiment inclusion flags.
- `features/S##/S##A##T##.csv`: one compact aligned CoM sequence per manually valid fall, including phase segments and repaired-frame masks.
- `annotations/phase_annotations.json`: normalized phase boundaries and decisions.
- `annotations/source_notes/`: exact manual JSON sources used in this build, including existing A11 annotations.
- `subjects/S##/`: subject-wise manifests and notes.
- `splits/loso_folds.json`: subject-grouped leave-one-subject-out folds.
- `manifests/activity_summary.csv`: aggregate counts by activity.

## Inclusion flags

- `include_detection_training`: manually valid fall with complete, ordered, in-bounds phases and a numeric audit source. Repaired rows remain explicitly masked.
- `include_planar_physics_primary`: strict-quality A10–A13 subset.
- `include_planar_physics_sensitivity`: all manually valid A10–A13 trials, including repair-sensitive cases.
- `include_rotation_physics_primary`: strict-quality A14 subset, excluding S44's activity-identity ambiguity.
- `include_rotation_physics_sensitivity`: all manually valid A14 trials.

## Coordinate convention

Azure Kinect camera coordinates are preserved as X, Y-down, and Z. Each valid trial additionally receives an X–Z unit direction from CoM at fall onset to apparent contact. `aligned_progression_m` projects horizontal motion along this direction, `aligned_lateral_m` is the orthogonal horizontal component, and `vertical_from_onset_m` is positive upward. This removes the unsafe assumption that camera X is always the fall axis.

## Recommended experimental use

Use subject-grouped splits only. Start planar physics work with `include_planar_physics_primary == true`, run the sensitivity flag as a separate ablation, and model A14 with a rotational extension rather than pooling it into a single-plane inverted-pendulum residual. For fall detection, filter `include_detection_training == true` and keep the repair mask as an input or loss mask.

See `FINDINGS.md` for reviewed exceptions and counts.
