# A10-A14 physics synthetic-fall study with GATE

This is a new experiment folder. It preserves the earlier
`Fifteen_Subject_DeepONet_Synthetic_Fall_Study` unchanged while extending its
validated top-two generation and quality-gate workflow to:

- the unified A10-A13 V2 DeepONet with direct CartPole physics active for all
  four planar fall activities; and
- the separate A14 rotation DeepONet with CartPole and yaw residuals.

The no-physics A10-A13 models remain comparison controls and are explicitly
excluded from synthetic generation.

## Expected repository layout

Place this directory at the repository root beside both completed physics
experiments:

```text
PINN-FallDetection-Init/
├── data/processed/Fifteen_Subject_Real_Fall_Physics_Ready/
├── Fifteen_Subject_DeepONet_A10_A13_Activity_Specific_Physics_V2_5_Seeds/
│   ├── outputs/real_data_full/planar/
│   └── results/candidates/full/lambda_*/seed_*/fold_*/
├── Fifteen_Subject_DeepONet_A10_A13_Unified_A14_Rotation_Physics_5_Seeds/
│   ├── outputs/real_data_full/rotation/
│   └── results/rotation/full/seed_*/fold_*/
└── Fifteen_Subject_DeepONet_A10_A14_Physics_Synthetic_Fall_Study_GATED/
```

The prepared `.npz` data beneath each physics experiment must still be present.
Packaged result ZIPs normally omit those prepared arrays, so place the new
folder beside the experiment directories you actually ran on the MacBook.

## Generator selection

Selection happens separately inside every fold because folds have different
validation subjects.

### A10-A13 planar pool

- Candidate pool: 15 nonzero-physics candidates per fold: three lambdas
  `{1e-4, 1e-3, 1e-2}` x five seeds.
- Required architecture: unified A10-A13 model with all four activity-specific
  CartPole controller heads.
- Ranking: `best_validation_forecast_mse`, lower is better.
- Retained: top two per fold.
- Lambda=0 is rejected even if its validation score is lower.

### A14 rotation pool

- Candidate pool: five direct-physics seed models per fold.
- Ranking: validation forecast MSE, lower is better.
- Retained: top two per fold.

No held-out test metric is read for selection. The expected reviewed selection
is recorded in `VERIFIED_SELECTION_REFERENCE.md`; the local selection output is
authoritative.

## Synthetic trajectory construction

Only real contexts from a selected generator's training subjects are used.
Validation and test contexts cause a hard failure.

The observed trajectory is retained through 0.40 seconds. Each model predicts
the remaining trajectory through the source trial's apparent-contact endpoint.
A per-channel C1 decaying bridge corrects position and boundary velocity:

```text
c(s) = [delta_q + (delta_v + delta_q/tau)s] exp(-s/tau)
tau = 0.15 s,  s = t - 0.40 s
```

The correction is applied to theta and CoM-x for A10-A13 and to theta, CoM-x,
and yaw for A14. Generated outputs from the two models remain separate; they
are not averaged.

These are conditional synthetic falls. The model does not predict contact time,
so valid duration and the endpoint are inherited from the source real trial.

## GATE quality protocol

Thresholds are calculated separately by model group, fold, and activity using
training subjects only. This is essential for A10-A13 because back, front,
left, and right falls have different trajectory distributions.

A candidate is approved only if every gate below passes:

1. **Finite and time-valid:** required metrics are finite and the stored time
   series is strictly increasing.
2. **Continuity:** all theta/x boundary position-step and velocity-change
   metrics are below activity/fold real-training p95; A14 must also pass yaw
   continuity.
3. **Shape:** normalized RMSE and normalized DTW are below the corresponding
   within-subject, same-activity real-real p95 thresholds.
4. **Kinematics:** at least 75% of displacement, peak-velocity, and
   peak-acceleration distances pass. A14 includes yaw kinematics.
5. **Direction:** synthetic CoM-x displacement has the same sign as its source
   fall when source displacement is at least 1 cm.
6. **Physics residual:** scaled CartPole angular/horizontal residual RMSEs are
   below generator/activity/fold p95 values from real training trajectories;
   A14 also passes its yaw residual threshold.
7. **Exact duplicate:** repeated trajectory hashes are rejected.

Only `outputs/trajectory_quality/final_approved_synthetic_manifest.json` is
approved for the later detector-data preparation experiment. Rejected files are
retained for audit and must not be used for detector training.

See `GATE_PROTOCOL.md` for formulas and output interpretation.

## MacBook MPS commands

The launcher uses `~/.venv` by default. Set `PINN_VENV_DIR` if your environment
is elsewhere.

```bash
cd Fifteen_Subject_DeepONet_A10_A14_Physics_Synthetic_Fall_Study_GATED
chmod +x run.sh run_on_mac.sh

./run_on_mac.sh setup      # skip if your home venv already has the requirements
./run_on_mac.sh test
./run_on_mac.sh smoke
./run_on_mac.sh validate
./run_on_mac.sh select
./run_on_mac.sh generate mps
./run_on_mac.sh quality
./run_on_mac.sh package
```

Or run the main workflow after tests:

```bash
./run_on_mac.sh pipeline mps
./run_on_mac.sh package
```

The stages are intentionally separable. If generation is interrupted, rerun
`generate`; it deterministically rewrites the same files for the same selected
checkpoints and source trials.

## Custom sibling paths

If either physics experiment is elsewhere:

```bash
./run_on_mac.sh select \
  --planar-dir "/absolute/path/to/A10_A13_V2" \
  --rotation-dir "/absolute/path/to/A14_Physics"

./run_on_mac.sh generate mps \
  --planar-dir "/absolute/path/to/A10_A13_V2" \
  --rotation-dir "/absolute/path/to/A14_Physics"

./run_on_mac.sh quality \
  --planar-dir "/absolute/path/to/A10_A13_V2" \
  --rotation-dir "/absolute/path/to/A14_Physics"
```

## Main outputs

```text
outputs/
├── generator_selection/
│   ├── generator_selection.json
│   ├── SELECTION_SUMMARY.md
│   ├── planar/{all_generator_rankings.csv,selected_generators.csv}
│   ├── rotation/{all_generator_rankings.csv,selected_generators.csv}
│   └── selected_generators/{planar,rotation}/fold_*/rank_*/
├── synthetic_trajectories/
│   ├── synthetic_manifest.json
│   ├── synthetic_manifest.csv
│   ├── planar/fold_*/rank_*/*.npz
│   └── rotation/fold_*/rank_*/*.npz
└── trajectory_quality/
    ├── QUALITY_REPORT.md
    ├── quality_summary.json
    ├── quality_thresholds.csv
    ├── quality_decisions.csv
    ├── generator_quality_summary.csv
    ├── activity_quality_summary.csv
    ├── real_real_distances.csv
    ├── synthetic_real_distances.csv
    ├── selected_generator_diversity.csv
    ├── final_approved_synthetic_manifest.json
    ├── final_approved_synthetic_manifest.csv
    ├── real_real_vs_synthetic_real.png
    └── activity_quality_pass_rates.png
```

`package` creates:

```text
Fifteen_Subject_DeepONet_A10_A14_Physics_Synthetic_Fall_Study_GATED_Results.zip
```

The results archive excludes copied `.pt` files but includes all generated
trajectories, selection provenance, gate thresholds, decisions, summaries,
plots, and the approved-only manifest. Share that ZIP for review before the
detector-data preparation folder is created.

## Detector-study boundary

Do not mix synthetic variants across subject partitions. Every accepted sample
inherits its real source subject and must remain in that source subject's
training partition. After these results are reviewed, the next folder will
construct real-only and real/synthetic detector datasets—including the planned
40:60 and 60:40 ratios—from the approved manifest only.

## Completed full-run result

The MacBook MPS run produced 2,044 candidates and GATE approved 1,380
(67.5%). All 15 source subjects remain represented. The approved set covers
249 of the 306 strict physics-source trials, with one to eight accepted model
variants per represented source trial.

| Activity | Candidates | Approved | Approval |
|:--|--:|--:|--:|
| A10 | 380 | 209 | 55.0% |
| A11 | 422 | 284 | 67.3% |
| A12 | 450 | 338 | 75.1% |
| A13 | 448 | 290 | 64.7% |
| A14 | 344 | 259 | 75.3% |
| **Total** | **2,044** | **1,380** | **67.5%** |

A10 is the limiting activity because its kinematic pass rate is 61.8%; its
physics pass rate is still 97.1%. Across all activities, 457 candidates failed
the kinematic gate, compared with 160 continuity, 111 shape, 69 direction, and
56 physics failures. No exact duplicate was found. These results support using
the approved set for detector augmentation; they do not support relaxing GATE
or retraining a model solely to increase candidate acceptance.

See `FINDINGS.md` for the reviewed interpretation and downstream safeguards.

