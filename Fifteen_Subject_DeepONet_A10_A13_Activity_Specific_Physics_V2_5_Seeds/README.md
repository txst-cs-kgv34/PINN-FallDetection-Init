# Fifteen-subject A10-A13 activity-specific physics DeepONet V2

This experiment trains one unified multi-subject, multi-activity DeepONet for
A10-A13. The context encoder, branch, trunk, and trajectory output are shared,
while A10, A11, A12, and A13 have independently parameterized CartPole
controller heads. It does **not** train four independent trajectory models.

Four global physics weights were trained from the same original model state in
every seed-fold:

`lambda = {0, 1e-4, 1e-3, 1e-2}`

Only lambda differs within a matched seed-fold. Initialization, batch order,
optimizer, learning rate, maximum epochs, early stopping, subject split, and
checkpoint rule are matched. Lambda and the checkpoint are selected using only
two validation subjects. The chosen model is then compared with its newly
trained, matched lambda=0 arm on three held-out subjects.

## Full five-seed result

The run is complete: 100/100 candidates, 25 validation-selected evaluations,
and 25 matched lambda=0 evaluations. The primary analysis averages the five
optimization seeds within each of the 15 held-out subjects, so the independent
sample size remains 15 subjects rather than 75 subject-seed cells.

Positive improvement means `matched lambda=0 - selected V2`; positive values
favor selected V2.

| Endpoint | Selected V2 | Matched lambda=0 | Relative V2 improvement | Subject wins V2/N | Bootstrap 95% CI for absolute improvement | Holm p |
|:--|--:|--:|--:|--:|--:|--:|
| Normalized forecast MSE | 3.5870 | 3.6887 | +2.76% | 8/7 | [-0.0659, +0.3102] | 1.0000 |
| Theta RMSE | 23.0432 degrees | 23.2487 degrees | +0.88% | 8/7 | [-0.1720, +0.6486] degrees | 1.0000 |
| CoM-x RMSE | 31.3921 cm | 31.6980 cm | +0.97% | 9/6 | [-0.2367, +0.8814] cm | 1.0000 |

V2 therefore has a **small descriptive forecasting advantage**, not a
statistically confirmed advantage. Three of five seeds favored V2 on all three
primary endpoints; seed 1 was mixed and seed 5 was slightly worse. The
confidence intervals include zero, and all Holm-adjusted p-values are 1.0.

The selected weights were unstable across the 25 seed-folds:

| Selected lambda | 0 | 1e-4 | 1e-3 | 1e-2 |
|:--|--:|--:|--:|--:|
| Count | 9 | 2 | 5 | 9 |

Sixteen of 25 selections used nonzero physics, but the two most frequent
choices were the opposite endpoints, lambda=0 and lambda=1e-2. A single
production lambda cannot be justified from selection frequency alone.

## Activity-level result

Activity rows equalize trials within subject-activity-seed cells. They are
descriptive because lambda was selected globally per fold, not independently
for each activity.

| Activity | Normalized MSE improvement | Theta RMSE improvement | CoM-x RMSE improvement | Current reading |
|:--|--:|--:|--:|:--|
| A10 backfall | +0.32% | +0.31% | +0.22% | Effectively neutral |
| A11 frontfall | -1.16% | -1.13% | -0.82% | No-physics favored |
| A12 leftfall | +2.99% | +2.43% | +2.00% | Clearest physics-favored activity |
| A13 rightfall | +4.76% | +0.63% | +1.16% | Physics-favored in aggregate, but seed-dependent |

The seed-1 A13 concern did not persist in the five-seed average. However, the
activity-by-seed effects are heterogeneous, so these rows do not prove that an
independent activity model should be selected. For synthetic generation, the
chosen policy is to retain direct CartPole physics for all A10-A13 activities
and control sample quality after generation.

## Physics residuals

Across subject-seed evaluations, selected V2 reduced angular residual RMSE
from 15.3236 to 15.2266 (+0.63%) and horizontal residual RMSE from 244.7598 to
189.3938 (+22.62%). Horizontal residual RMSE improved in all five seeds. The
constraint is therefore changing trajectories in the intended direction, but
the much larger residual gain does not translate into a comparably large
forecast gain.

## Interpretation and model decision

The unified architecture remains appropriate. The present result does **not**
support four independent activity models, and it does not support using the
current per-fold lambda selections as one deployable generator.

The production policy is:

| Activity | Synthetic trajectory policy | Role of the activity result |
|:--|:--|:--|
| A10 | Unified A10-A13 with direct CartPole physics | Aggregate forecast effect is neutral, but physics remains part of the common generator |
| A11 | Unified A10-A13 with direct CartPole physics | Aggregate forecast result is reported honestly; physics is retained for physical consistency and quality-gated generation |
| A12 | Unified A10-A13 with direct CartPole physics | Broad positive aggregate benefit |
| A13 | Unified A10-A13 with direct CartPole physics | Positive full-run aggregate; seed-1 reversal resolved |
| A14 | Existing separate rotation-physics DeepONet | Rotation remains a separate dynamics problem |

No A10/A11 physics mask experiment is planned. The no-physics models remain
scientific comparators, not synthetic-data generators. For each common
training/validation scope, rank only the eligible all-head, nonzero-lambda
models by validation subject-activity-balanced forecast MSE and retain the best
two. Do not compare raw validation MSE across different validation folds as if
the validation subjects were identical.

## Synthetic-generation boundary

The current cross-validation checkpoints must be used within their documented
subject scope. The synthetic-data procedure is:

1. Keep direct physics active for A10, A11, A12, and A13.
2. Select the best two eligible nonzero-lambda checkpoints using validation
   performance only. Both selected models must use the same validation split
   or otherwise be ranked through a fold-balanced aggregation.
3. Generate candidates from both selected models and retain only trajectories
   passing the established quality gate: range, smoothness, phase/direction,
   physics residual, endpoint/contact, duplicate, and model-agreement checks.
4. Refit the already selected A14 rotation architecture on all 49 eligible A14
   trials with its locked physics settings and five production seeds. The A14
   physics-versus-no-physics comparison does not need to be repeated.
5. For an unbiased subject-held-out fall-detection study, select/refit each
   generator using only the detector fold's training subjects. Never generate
   detector-training samples with a generator that saw that detector fold's
   test subjects.

The current DeepONet outputs CoM trajectory variables, not a complete skeleton.
If the downstream detector expects full joint sequences, a validated kinematic
decoder is required before augmentation.

See `FINDINGS.md`, `FULL_FIVE_SEED_AUDIT.md`, and
`SYNTHETIC_GENERATOR_PLAN.md` for the detailed interpretation and handoff.

## What changed from the first unified experiment

1. **Future-free activity axes.** Prediction and physics coordinates are
   defined by activity identity in the fixed standing anatomical frame:

   | Activity | Signed subject-frame axis `[lateral, forward]` |
   |:--|:--|
   | A10 backfall | `[0, -1]` |
   | A11 frontfall | `[0, +1]` |
   | A12 leftfall | `[-1, 0]` |
   | A13 rightfall | `[+1, 0]` |

2. **Activity-specific controller heads.** Four heads infer delayed CartPole
   gains. The same Model B CartPole residual family is retained for every
   activity; only the head parameters differ.
3. **Balanced objectives.** Forecast and normalized residual losses average
   over activities present in a batch; sampling is balanced by
   subject-activity cell.
4. **Stronger validation.** Every fold uses 10 training, 2 validation, and 3
   test subjects. Selection uses validation subject-activity-balanced forecast
   MSE.
5. **Residual scaling.** Angular acceleration residual is divided by `g/l` and
   horizontal acceleration residual by `g` before lambda is applied.

## Data and model scope

- Strict-primary trials: 257 total (A10=58, A11=64, A12=68, A13=67).
- One unified trajectory model conditioned on activity, demographics, and the
  activity-defined direction.
- Shared DeepONet latent width 96 and 12 Fourier modes.
- Four 0.10-s context windows covering the first 0.40 s.
- Hard initial condition: `q(t) = q0 + qdot0*t + t^2*f(t)`.
- Delayed CartPole constants: `m=0.0138`, `m0=1`, `l=0.57`, `g=9.81`,
  `tau=0.23`, and `Pi=0.0635`.
- AdamW, learning rate `5e-4`, weight decay `1e-6`, batch size 8.
- Maximum 800 epochs, 100-epoch physics ramp and minimum training period, and
  patience 100.

## Placement and commands

Place this folder at the repository root:

```text
PINN-FallDetection-Init/
├── data/processed/Fifteen_Subject_Real_Fall_Physics_Ready/
├── S30_PINN_audit/ ... S63_PINN_audit/
└── Fifteen_Subject_DeepONet_A10_A13_Activity_Specific_Physics_V2_5_Seeds/
```

The launcher uses `~/.venv` by default. Set `PINN_VENV_DIR` if your environment
is elsewhere.

```bash
cd Fifteen_Subject_DeepONet_A10_A13_Activity_Specific_Physics_V2_5_Seeds
chmod +x run.sh run_on_mac.sh
./run_on_mac.sh validate
./run_on_mac.sh test
./run_on_mac.sh status
./run_on_mac.sh compare
./run_on_mac.sh package
```

Use `FORCE=1` only when intentionally replacing completed candidates.

