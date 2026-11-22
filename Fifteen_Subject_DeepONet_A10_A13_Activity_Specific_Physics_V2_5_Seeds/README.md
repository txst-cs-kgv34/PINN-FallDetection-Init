# Fifteen-subject A10-A13 activity-specific physics DeepONet V2

This is the recommended seed-1 follow-up to the completed A11 calibration. It
trains one unified multi-subject, multi-activity DeepONet for A10-A13. The
context encoder, branch, trunk, and trajectory output are shared, while A10,
A11, A12, and A13 have four independently parameterized CartPole controller
heads. It does **not** train four independent trajectory models.

The seed-1 pilot trains four global physics weights from the same original
model state in each fold:

`lambda = {0, 1e-4, 1e-3, 1e-2}`

Only lambda differs. Initialization, batch order, optimizer, learning rate,
maximum epochs, minimum training period, early stopping, validation subjects,
and checkpoint rule are matched. The selected model is compared with the newly
trained matched lambda=0 arm.

## Seed-1 pilot result

The pilot completed successfully: 20/20 candidate models, five
validation-selected evaluations, and five matched lambda=0 evaluations. The
protocol audit found identical initialization hashes and identical
pre-training validation loss across all four lambda arms within every fold.
All 257 selected/no-physics test targets were exactly equal, and all 4,591
training-history rows were finite.

The seed-1 forecasting result is mixed and close to neutral overall:

| Endpoint | Selected V2 | Matched lambda=0 | Relative V2 improvement | Subject wins V2/N/tie | Holm p |
|:--|--:|--:|--:|--:|--:|
| Normalized forecast MSE | 3.6402 | 3.5723 | -1.90% | 6/3/6 | 1.0000 |
| Theta RMSE | 22.2882 degrees | 22.3790 degrees | +0.41% | 5/4/6 | 1.0000 |
| CoM-x RMSE | 30.8745 cm | 30.8838 cm | +0.03% | 5/4/6 | 1.0000 |

The six ties are the test subjects in folds 4 and 5, where validation selected
lambda=0. Across the five folds, the selected weights were lambda=0 twice and
each nonzero candidate once.

Activity behavior was not uniform. A10 and A11 improved descriptively on all
three primary outcomes. A12 improved theta and CoM-x RMSE but was 0.32% worse
on normalized MSE. A13 was worse on all three outcomes: -7.39% normalized MSE,
-5.14% theta RMSE, and -5.94% CoM-x RMSE.

Physics reduced horizontal residual RMSE by 18.14% overall and by 40.82% among
the nine subjects evaluated with nonzero selected lambda. Angular residual
RMSE was essentially unchanged/slightly worse (-0.21% overall). Better
horizontal equation consistency therefore did not yet produce a reliable
forecast advantage.

This one-seed result is not confirmatory. Because the implementation checks
passed and A10-A12 contain potentially useful activity-specific signals, the
recommended next action is to complete seeds 2-5 **without changing the
protocol**. Do not report that V2 physics improves forecasting until the full
five-seed comparison is available.

## What changed from the first unified experiment

1. **Future-free activity axes.** The prediction and physics coordinate is
   defined by activity identity in the fixed standing anatomical frame:

   | Activity | Signed subject-frame axis `[lateral, forward]` |
   |:--|:--|
   | A10 backfall | `[0, -1]` |
   | A11 frontfall | `[0, +1]` |
   | A12 leftfall | `[-1, 0]` |
   | A13 rightfall | `[+1, 0]` |

   The axis is no longer estimated from onset-to-contact target motion.

2. **Activity-specific physics heads.** Four separate controller heads infer
   the delayed CartPole gains. The exact Model B CartPole residual family is
   retained for every activity; only the head parameters differ.

3. **Balanced objectives.** Training forecast loss and normalized residual
   loss average over the activities present in a batch. Sampling is balanced by
   subject-activity cell.

4. **Stronger validation.** Every fold uses 10 training, 2 validation, and 3
   test subjects. Lambda and checkpoints are selected by mean forecast loss
   over validation subject-activity cells, not by one validation subject.

5. **Residual scaling.** Angular acceleration residual is divided by `g/l` and
   horizontal acceleration residual by `g` before the global lambda is applied.

## Data and model scope

- Strict-primary trials: 257 total.
- Counts: A10=58, A11=64, A12=68, A13=67.
- One unified trajectory model, conditioned on activity, demographics, and the
  activity-defined direction.
- Shared DeepONet latent width 96 and 12 Fourier modes.
- Four 0.10-s context windows covering the first 0.40 s.
- Hard initial condition: `q(t) = q0 + qdot0*t + t^2*f(t)`.
- Delayed CartPole constants remain `m=0.0138`, `m0=1`, `l=0.57`, `g=9.81`,
  `tau=0.23`, and `Pi=0.0635`.
- AdamW, learning rate `5e-4`, weight decay `1e-6`, batch size 8.
- Maximum 800 epochs, 100-epoch physics ramp and minimum training period, and
  patience 100.

## Placement

Place this folder at the repository root beside the data and updated audits:

```text
PINN-FallDetection-Init/
├── data/processed/Fifteen_Subject_Real_Fall_Physics_Ready/
├── S30_PINN_audit/ ... S63_PINN_audit/
└── Fifteen_Subject_DeepONet_A10_A13_Activity_Specific_Physics_V2_5_Seeds/
```

## MacBook MPS commands

The launcher uses `~/.venv` by default. Set `PINN_VENV_DIR` if your environment
is elsewhere.

```bash
cd Fifteen_Subject_DeepONet_A10_A13_Activity_Specific_Physics_V2_5_Seeds
chmod +x run.sh run_on_mac.sh
./run_on_mac.sh setup
./run_on_mac.sh validate
./run_on_mac.sh test
./run_on_mac.sh smoke mps
./run_on_mac.sh pilot mps
```

The pilot trains 20 candidates: four lambda arms x five folds x one seed. It
then evaluates five selected checkpoints and their five matched lambda=0
checkpoints. Completed candidates are skipped, so an interrupted run can be
resumed with the same command.

Useful commands:

```bash
./run_on_mac.sh status
./run_on_mac.sh fold 3 mps 1
./run_on_mac.sh seed 1 mps
./run_on_mac.sh compare
./run_on_mac.sh package
```

Use `FORCE=1` only when intentionally replacing completed candidates.

## Run the remaining seeds

Seed 1 is complete. Resume the same experiment with:

```bash
./run_on_mac.sh full mps
```

Completed seed-1 candidates are skipped automatically. Send the generated
full-results file:

`Fifteen_Subject_A10_A13_Activity_Specific_Physics_V2_5_Seeds_Results.zip`

The package includes selection weights, subject and activity comparisons,
boxplots, prediction archives, histories, initialization hashes, and exact
target-equality checks.

## Decision after five seeds

The full review will inspect the three predefined endpoints, activity
consistency, subject outliers, lambda stability, validation-to-test transfer,
and residual changes. If A13 remains systematically worse while A10-A12 remain
promising, the next experiment should compare all-head physics against
activity-head ablations, including A13 lambda=0. That decision must be based on
the five-seed result rather than this single seed.

## A14 boundary

A14 is deliberately excluded. Do not repeat its completed 50-model
physics-versus-no-physics comparison now. After A10-A13 is finalized, the
existing best A14 architecture can be refit on all 49 eligible rotation trials
with its locked settings and five production seeds for synthetic generation.

