# Validation-only top-two generator selection

Only direct-physics checkpoints are eligible. No held-out test metric is read or used.

| Group | Fold | Validation subjects | Rank | Seed | Physics weight | Validation MSE |
|:--|--:|:--|--:|--:|--:|--:|
| planar | 1 | S44, S62 | 1 | 2 | 0.01 | 2.16010874 |
| planar | 1 | S44, S62 | 2 | 3 | 0.0001 | 2.27859908 |
| planar | 2 | S57, S46 | 1 | 5 | 0.001 | 1.64998755 |
| planar | 2 | S57, S46 | 2 | 5 | 0.0001 | 1.67880614 |
| planar | 3 | S55, S48 | 1 | 1 | 0.001 | 1.72105292 |
| planar | 3 | S55, S48 | 2 | 5 | 0.0001 | 1.73048800 |
| planar | 4 | S45, S59 | 1 | 2 | 0.01 | 2.00817028 |
| planar | 4 | S45, S59 | 2 | 2 | 0.001 | 2.03253314 |
| planar | 5 | S34, S32 | 1 | 5 | 0.0001 | 2.08335230 |
| planar | 5 | S34, S32 | 2 | 2 | 0.0001 | 2.13376957 |
| rotation | 1 | S63 | 1 | 4 | 0.01 | 3.11939262 |
| rotation | 1 | S63 | 2 | 1 | 0.01 | 3.98686976 |
| rotation | 2 | S62 | 1 | 3 | 0.01 | 3.12863734 |
| rotation | 2 | S62 | 2 | 2 | 0.01 | 3.13359039 |
| rotation | 3 | S57 | 1 | 5 | 0.01 | 2.91801162 |
| rotation | 3 | S57 | 2 | 3 | 0.01 | 3.05494307 |
| rotation | 4 | S55 | 1 | 2 | 0.01 | 6.25878894 |
| rotation | 4 | S55 | 2 | 5 | 0.01 | 6.73400617 |
| rotation | 5 | S43 | 1 | 1 | 0.01 | 2.45718372 |
| rotation | 5 | S43 | 2 | 2 | 0.01 | 2.58370597 |

Planar candidates are ranked among the 15 nonzero-lambda A10-A13 V2 candidates in each fold.
Rotation candidates are ranked among the five direct-physics A14 seeds in each fold.
Generated trajectories must pass the GATE quality pipeline before detector use.
