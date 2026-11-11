# Validation-only generator selection

Selected the top 2 seed-specific checkpoints within each fold.
Ranking used only `best_validation_value` from `training_selection.json`.
No test error, test RMSE, or test-subject performance was used.

| Fold | Validation subject | Rank | Seed index | Base seed | Best epoch | Validation normalized MSE |
|---:|---|---:|---:|---:|---:|---:|
| 1 | S63 | 1 | 3 | 20261103 | 34 | 0.42238793 |
| 1 | S63 | 2 | 1 | 20261101 | 32 | 0.42455480 |
| 2 | S62 | 1 | 5 | 20261105 | 285 | 0.81513379 |
| 2 | S62 | 2 | 2 | 20261102 | 290 | 0.82756846 |
| 3 | S57 | 1 | 4 | 20261104 | 105 | 0.65761699 |
| 3 | S57 | 2 | 5 | 20261105 | 104 | 0.70399364 |
| 4 | S55 | 1 | 3 | 20261103 | 47 | 0.74257302 |
| 4 | S55 | 2 | 5 | 20261105 | 30 | 0.75559469 |
| 5 | S43 | 1 | 3 | 20261103 | 33 | 0.96350451 |
| 5 | S43 | 2 | 4 | 20261104 | 40 | 0.99776161 |

These checkpoints are candidate generators. Their generated trajectories must pass the predefined synthetic-data quality checks before downstream fall-detector training.
