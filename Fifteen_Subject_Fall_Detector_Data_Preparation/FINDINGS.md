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

## Real falls

The earlier audit inventory identified 360 available raw fall recordings:

| Activity | Meaning | Available files |
|---|---|---:|
| A10 | Backfall | 75 |
| A11 | Frontfall | 74 |
| A12 | Leftfall | 74 |
| A13 | Rightfall | 74 |
| A14 | Rotatefall | 63 |

The updated preparation script uses all A10-A14 recordings by default. Each local run independently checks the supplied `FallSamples` files, so the accepted count is written after execution rather than assumed in advance.

The previous controlled dataset used 70 A11 trajectories with complete manual phases. That experiment remains reproducible with `--real-fall-scope a11`, preferably using a separate `outputs_a11` directory.

## Synthetic falls

The approved synthetic manifest previously contained 226 quality-qualified A11 trajectories. The updated script reads the current manifest during each run, includes only approved entries, and verifies that the materialized count matches the manifest's `approved_count`.

Synthetic trajectories are conditional variants, not independent recorded subjects. Their source subject and source real trial remain in the detector manifest for leakage control.

## Prepared representation

All accepted data is converted to variable-length 30 Hz `.npz` trajectories containing `theta_rad`, `x_m`, timing, label, activity, and demographic metadata.

- ADL label: `0`.
- Real and synthetic fall label: `1`.
- Default real-fall activities: A10-A14.
- Synthetic activity: A11.

The input skeleton folders are read-only. Prepared trajectories are written only under this directory's selected output path.

## Experimental interpretation

Two distinct comparisons should be retained:

1. **General fall detector:** all real A10-A14 falls, approved synthetic A11 falls, and real ADL.
2. **Activity-matched controlled comparison:** audited real A11 falls, approved synthetic A11 falls, and real ADL.

The general experiment measures whether synthetic front falls help a detector trained with broader real fall directions. The A11-only experiment isolates the real-versus-synthetic comparison without changing fall activity.

## Required leakage rule

Split by `split_group` before creating windows or balancing classes. Every synthetic trajectory must stay in the same partition as its source subject. S31 remains its own split group and must never be assigned S59's identity.

## Status

The preparation code is ready for a local repository-layout run. Detector-specific windowing, normalization, folds, architecture, and training are intentionally deferred until the model design is provided.
