# Verified top-two selection reference

The selector was checked against the complete A10-A13 V2 and A14 physics result
layouts. It found the expected candidate pools and used validation loss only:

- Planar: 15 eligible nonzero-lambda candidates per fold (three lambdas x five
  optimization seeds), with lambda=0 excluded.
- Rotation: five eligible direct-physics A14 candidates per fold.
- Selected: two planar and two rotation generators per fold, 20 total.

The reference selection from the reviewed result packages is:

| Group | Fold | Validation subjects | Rank | Seed | Lambda | Validation MSE |
|:--|--:|:--|--:|--:|--:|--:|
| Planar | 1 | S44, S62 | 1 | 2 | 1e-2 | 2.16010874 |
| Planar | 1 | S44, S62 | 2 | 3 | 1e-4 | 2.27859908 |
| Planar | 2 | S57, S46 | 1 | 5 | 1e-3 | 1.64998755 |
| Planar | 2 | S57, S46 | 2 | 5 | 1e-4 | 1.67880614 |
| Planar | 3 | S55, S48 | 1 | 1 | 1e-3 | 1.72105292 |
| Planar | 3 | S55, S48 | 2 | 5 | 1e-4 | 1.73048800 |
| Planar | 4 | S45, S59 | 1 | 2 | 1e-2 | 2.00817028 |
| Planar | 4 | S45, S59 | 2 | 2 | 1e-3 | 2.03253314 |
| Planar | 5 | S34, S32 | 1 | 5 | 1e-4 | 2.08335230 |
| Planar | 5 | S34, S32 | 2 | 2 | 1e-4 | 2.13376957 |
| Rotation | 1 | S63 | 1 | 4 | 1e-2 | 3.11939262 |
| Rotation | 1 | S63 | 2 | 1 | 1e-2 | 3.98686976 |
| Rotation | 2 | S62 | 1 | 3 | 1e-2 | 3.12863734 |
| Rotation | 2 | S62 | 2 | 2 | 1e-2 | 3.13359039 |
| Rotation | 3 | S57 | 1 | 5 | 1e-2 | 2.91801162 |
| Rotation | 3 | S57 | 2 | 3 | 1e-2 | 3.05494307 |
| Rotation | 4 | S55 | 1 | 2 | 1e-2 | 6.25878894 |
| Rotation | 4 | S55 | 2 | 5 | 1e-2 | 6.73400617 |
| Rotation | 5 | S43 | 1 | 1 | 1e-2 | 2.45718372 |
| Rotation | 5 | S43 | 2 | 2 | 1e-2 | 2.58370597 |

The local `outputs/generator_selection/SELECTION_SUMMARY.md` is authoritative.
The selector stops if candidate counts, subject splits, physics status,
validation-only flags, or checkpoint files do not match the documented
protocol.

