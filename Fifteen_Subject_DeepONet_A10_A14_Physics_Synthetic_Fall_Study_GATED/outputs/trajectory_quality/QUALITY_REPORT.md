# A10-A14 synthetic trajectory GATE report

## Protocol

- A10-A13 use the unified activity-specific direct-CartPole model; A14 uses the separate rotation-physics model.
- The two generators in each fold were selected only by validation forecast MSE.
- Contexts and all thresholds use training subjects only.
- Real-real, boundary, and kinematic thresholds are activity- and fold-specific p95 values.
- Physics thresholds are generator-, activity-, and fold-specific p95 values from real training trajectories.
- Complete approval requires continuity, shape, kinematic, direction, physics-residual, and exact-duplicate gates.
- Kinematic gate requires at least 75% of metrics.

## Counts

- Candidates: 2044
- Approved: 1380/2044 (67.5%)

## Activity summary

| Activity | Candidates | Approved | Approval | Continuity | Shape | Kinematic | Physics | Direction |
|:--|--:|--:|--:|--:|--:|--:|--:|--:|
| A10 | 380 | 209 | 55.0% | 95.8% | 82.1% | 61.8% | 97.1% | 97.9% |
| A11 | 422 | 284 | 67.3% | 91.5% | 97.9% | 78.2% | 95.0% | 96.4% |
| A12 | 450 | 338 | 75.1% | 92.9% | 98.0% | 84.4% | 98.2% | 96.0% |
| A13 | 448 | 290 | 64.7% | 87.9% | 100.0% | 76.1% | 97.3% | 94.9% |
| A14 | 344 | 259 | 75.3% | 93.6% | 92.7% | 87.5% | 98.8% | 98.5% |

## Generator summary

| Group | Fold | Rank | Seed | Candidates | Approved | Rate |
|:--|--:|--:|--:|--:|--:|--:|
| planar | 1 | 1 | 2 | 165 | 100 | 60.6% |
| planar | 1 | 2 | 3 | 165 | 103 | 62.4% |
| planar | 2 | 1 | 5 | 180 | 124 | 68.9% |
| planar | 2 | 2 | 5 | 180 | 124 | 68.9% |
| planar | 3 | 1 | 1 | 179 | 132 | 73.7% |
| planar | 3 | 2 | 5 | 179 | 122 | 68.2% |
| planar | 4 | 1 | 2 | 167 | 109 | 65.3% |
| planar | 4 | 2 | 2 | 167 | 103 | 61.7% |
| planar | 5 | 1 | 5 | 159 | 97 | 61.0% |
| planar | 5 | 2 | 2 | 159 | 107 | 67.3% |
| rotation | 1 | 1 | 4 | 32 | 27 | 84.4% |
| rotation | 1 | 2 | 1 | 32 | 23 | 71.9% |
| rotation | 2 | 1 | 3 | 31 | 25 | 80.6% |
| rotation | 2 | 2 | 2 | 31 | 25 | 80.6% |
| rotation | 3 | 1 | 5 | 35 | 30 | 85.7% |
| rotation | 3 | 2 | 3 | 35 | 29 | 82.9% |
| rotation | 4 | 1 | 2 | 40 | 28 | 70.0% |
| rotation | 4 | 2 | 5 | 40 | 29 | 72.5% |
| rotation | 5 | 1 | 1 | 34 | 21 | 61.8% |
| rotation | 5 | 2 | 2 | 34 | 22 | 64.7% |

Only files listed in `final_approved_synthetic_manifest.json` may enter detector-data preparation.
Passing GATE establishes consistency with training-data quality envelopes; downstream detector utility must still be tested on unseen real subjects.
