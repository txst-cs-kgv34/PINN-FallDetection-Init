# Fall-detector data-preparation findings

## Source-data findings

The initial source audit found 549 ADL CSV filenames. Four were not suitable for preparation, producing an expected 545 accepted ADL trajectories:

- `S48A02T05`: empty file;
- `S49A03T01`: nine-frame blank interval;
- `S56A03T03`: four-frame blank interval;
- `S57A02T03`: six-frame blank interval.

Five isolated blank frames were repairable:

- four isolated frames in `S57A03T02`;
- one isolated frame in `S63A02T04`.

A04 was absent, as expected. A08 contains walking recordings and is retained as a hard-negative ADL activity.

S59 has no ADL data. S31 supplies the replacement ADL recordings but remains S31 in filenames, demographics, manifests, and subject split groups.

## Real A11 front falls

The earlier audit inventory identified 360 available raw fall recordings:

| Activity | Meaning | Available files |
|---|---|---:|
| A10 | Backfall | 75 |
| A11 | Frontfall | 74 |
| A12 | Leftfall | 74 |
| A13 | Rightfall | 74 |
| A14 | Rotatefall | 63 |

The current DeepONet and approved synthetic generator are specific to A11 Frontfall. Therefore, the default preparation script uses the phase-marked A11 files from each `S##_PINN_audit` directory. It includes only trials with a complete ordered manual phase sequence and clips them through apparent contact.

The verified controlled dataset contains 70 real A11 trajectories. Four A11 files without a complete manual phase sequence are excluded. The broader A10-A14 inventory is retained only for a future general fall-detector study and is not part of the current default experiment.

## Synthetic falls

The approved synthetic manifest previously contained 226 quality-qualified A11 trajectories. The updated script reads the current manifest during each run, includes only approved entries, and verifies that the materialized count matches the manifest's `approved_count`.

Synthetic trajectories are conditional variants, not independent recorded subjects. Their source subject and source real trial remain in the detector manifest for leakage control.

## Prepared representation

All accepted data is converted to variable-length 30 Hz `.npz` trajectories containing `theta_rad`, `x_m`, timing, label, activity, and demographic metadata.

- ADL label: `0`.
- Real and synthetic fall label: `1`.
- Default real-fall activity: A11 Frontfall.
- Synthetic activity: A11.

The input skeleton folders are read-only. Prepared trajectories are written only under this directory's selected output path.

## Experimental interpretation

The current comparison is activity matched: audited real A11 falls, approved synthetic A11 falls, and real ADL. This isolates the contribution of synthetic data without changing the fall direction. The optional general A10-A14 experiment should be treated as a later, separate study.

## Required leakage rule

Split by `split_group` before creating windows or balancing classes. Every synthetic trajectory must stay in the same partition as its source subject. S31 remains its own split group and must never be assigned S59's identity.

## Status

The preparation code is ready for a local repository-layout run. Detector-specific windowing, normalization, folds, architecture, and training are intentionally deferred until the model design is provided.
