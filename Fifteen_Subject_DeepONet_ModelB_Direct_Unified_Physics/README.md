# Model B — 15-subject direct unified physics DeepONet

This repository extends the exact earlier **Model B** condition to 15 subjects:

`S43, S55, S57, S62, S63, S59, S56, S49, S48, S46, S45, S44, S34, S32, S30`

It trains on real phase-marked CoM trajectories with the differentiable delayed
cart-pole biomechanics residual. It does **not** train on Pole-PINN synthetic
trajectories, teacher checkpoints, or gain-sweep targets.

## Do Pole_PINN_Human_Motion or Sweep Gain need to be rerun?

**No.** This Model B condition has `requires_teachers=false`,
`gain_weight=0`, and `synthetic_source_weight=0`. Pole-PINN checkpoints and
selected sweep gains do not enter its loss or inputs.

The five earlier subjects still need their already-created pole-compatible TSV
files. If those TSVs are missing on a new machine, rerun only the deterministic
data-conversion step from the earlier subject repository—not Pole-PINN training
and not the gain sweep. The ten new audit subjects are converted by this
repository's deterministic adapter.

## Exact preserved Model B condition

- Context: first 0.40 s, split into four 0.10-s windows.
- Context channels: theta, forward x, both velocities, and local time.
- Encoder: `Conv1d(5,32) → Conv1d(32,64) → adaptive average pool → 96`.
- Positive controller head: Softplus outputs
  `[Kp_theta, Kd_theta, Kp_x, Kd_x]`.
- DeepONet branch: gains + initial state + demographics + two fixed auxiliaries;
  hidden width 160 and output width `2 × 96`.
- Fourier-time trunk: 12 modes, hidden width 160, latent width 96.
- Hard initial conditions:
  `q(t) = q0 + qdot0*t + t²*f(t)` for theta and x.
- Objective: `L_real_forecast + 0.01 × L_cart_pole_physics`.
- Optimizer: AdamW, learning rate `5e-4`, weight decay `1e-6`, batch size 4,
  maximum 800 epochs, patience 100, gradient clip 5.
- Fixed physics: `m=0.0138 kg`, `m0=1 kg`, `l=0.57 m`, `g=9.81 m/s²`,
  `tau=0.23 s`, `Pi=0.0635 rad`, dead-zone sharpness 50.

The inferred gains are effective model parameters, not measured physiological
control gains.

## Five-fold generalization protocol

With 15 subjects and exactly five folds, each fold holds out three unseen test
subjects. This lets every subject contribute once to the final test result while
retaining one separate real validation subject for checkpoint selection.

| Fold | 11 real training subjects | Real validation | 3 unseen real test subjects |
|---:|:---|:---:|:---|
| 1 | S43, S55, S62, S59, S56, S49, S48, S45, S44, S34, S32 | S63 | S57, S46, S30 |
| 2 | S57, S63, S59, S56, S49, S46, S45, S44, S34, S32, S30 | S62 | S55, S48, S43 |
| 3 | S43, S55, S62, S63, S49, S48, S46, S44, S34, S32, S30 | S57 | S45, S59, S56 |
| 4 | S43, S57, S62, S63, S59, S56, S48, S46, S45, S44, S30 | S55 | S34, S32, S49 |
| 5 | S55, S57, S59, S56, S49, S48, S46, S45, S34, S32, S30 | S43 | S44, S62, S63 |

The split is reproducible from seed 220. A test subject is excluded from both
gradient training and validation selection in its fold. Aggregate means and
standard deviations are computed with equal weight across the 15 held-out
subjects, rather than weighting subjects with more trials more heavily.
The five original Model B subjects serve once each as validation anchors; they
are also tested once in different folds, exactly like the ten added subjects.

## Data placement

Unzip this repository beside the subject directories:

```text
PINN-FallDetection-Init/
├── S43_Pole_PINN_Human_Motion/
├── S55_Pole_PINN_Human_Motion/
├── S57_Pole_PINN_Human_Motion/
├── S62_Pole_PINN_Human_Motion/
├── S63_Pole_PINN_Human_Motion/
├── S59_PINN_audit/
├── S56_PINN_audit/
├── S49_PINN_audit/
├── S48_PINN_audit/
├── S46_PINN_audit/
├── S45_PINN_audit/
├── S44_PINN_audit/
├── S34_PINN_audit/
├── S32_PINN_audit/
├── S30_PINN_audit/
└── Fifteen_Subject_DeepONet_ModelB_Direct_Unified_Physics/
```

For the ten new subjects, `prepare_audit_inputs.py` reads the repaired skeleton
CSV files, demographics, and manual A11 phase notes. It computes sex-specific
segment-mass CoM, defines a fixed standing anatomical frame, uses the foot
midpoint at marked fall onset as the pivot, and derives:

```text
theta = atan2(subject-forward CoM, subject-vertical CoM)
x     = subject-forward CoM relative to the fixed onset pivot
```

This removes camera X/Z orientation before training. It also records every
repaired frame used before apparent contact in the adapter manifest. S49 A11T01
is naturally omitted because it is absent from the accepted phase notes. S58 is
not configured anywhere in this experiment.

## Running locally

Python 3.10+ is recommended. `auto` chooses CUDA, then Apple MPS, then CPU.

```bash
cd Fifteen_Subject_DeepONet_ModelB_Direct_Unified_Physics
chmod +x run.sh run_on_mac.sh
./run.sh setup
./run.sh validate
./run.sh test
./run.sh smoke auto
./run.sh full auto
```

Explicit device examples:

```bash
./run.sh smoke cpu
./run.sh fold 1 cuda
./run.sh full cuda
./run.sh full cpu
```

`run_on_mac.sh` remains as a compatibility wrapper and accepts the same modes.

Usage:

```text
./run.sh setup
./run.sh validate
./run.sh prepare
./run.sh smoke [auto|cuda|mps|cpu]
./run.sh fold FOLD_ID [auto|cuda|mps|cpu]
./run.sh full [auto|cuda|mps|cpu]
./run.sh aggregate
./run.sh package
./run.sh test
```

The smoke run uses three epochs and is only an end-to-end check. The full run
always regenerates the deterministic audit inputs before training.

## Synthetic outputs and real comparison

At test time, the model receives only the unseen subject trial's first 0.40 s,
initial state, demographics, fixed auxiliaries, and query times. Its predicted
theta and forward-x continuation is a model-generated—or synthetic—CoM
trajectory in the experiment's reduced coordinates.

For every held-out trial the repository saves:

- `test_predictions/<trial>.npz`: time, real theta/x, predicted theta/x, and
  inferred effective gains;
- `test_predictions/<trial>.png`: overlaid real-versus-synthetic trajectories;
- `test_metrics_by_trial.csv` and `test_metrics_by_subject.csv`;
- theta/x RMSE and MAE, normalized MSE, Wasserstein-1 distances, and 10-degree
  crossing-time error;
- the validation-selected checkpoint and complete training history.

After all folds, `cross_subject_metrics.csv` compares the subject means, while
`cross_subject_results.png` shows subject-wise box plots of the held-out trial
errors. Each box summarizes that subject's trials, black points are individual
trials, the blue line is the trial median, and the orange diamond is the
subject mean. The packaged file is:

```text
Fifteen_Subject_ModelB_Direct_Unified_Physics_Results.zip
```

Raw prepared arrays are omitted by default, while provenance manifests,
predictions, plots, metrics, logs, and model states are retained.

## Completed 15-subject results

The completed run contains 66 held-out test trials. Every configured subject
was tested once, with equal subject weighting in the aggregate statistics.
Detailed analysis is in [`FINDINGS.md`](FINDINGS.md).

| Metric | Mean across 15 subjects | Standard deviation | Median |
|:---|---:|---:|---:|
| Normalized MSE | 0.2584 | 0.3068 | 0.1642 |
| Theta RMSE | 5.70 deg | 2.84 deg | 5.30 deg |
| Forward-x RMSE | 8.87 cm | 4.67 cm | 7.73 cm |
| Theta MAE | 4.96 deg | 2.72 deg | 4.10 deg |
| Forward-x MAE | 7.86 cm | 4.47 cm | 6.70 cm |

Ten of 15 subjects achieved normalized MSE below 0.20 and 13 of 15 were below
0.50. The strongest held-out subjects were S30, S59, S56, S46, and S44. The
main failure cases were S45, S32, and S48. Therefore, the run supports useful
cross-subject generalization, but not uniform generalization to every motion
pattern.

### Saved context-controller parameters

Yes—the four positive effective controls inferred from the context encoding
are saved for every held-out test trial:

```text
Kp_theta, Kd_theta, Kp_x, Kd_x
```

They are available in two places inside each `results/full/fold_##` directory:

- `test_metrics_by_trial.csv` under the columns `inferred_kp_theta`,
  `inferred_kd_theta`, `inferred_kp_x`, and `inferred_kd_x`;
- `test_predictions/<trial>.npz` in `inferred_controller`, in the same order.

The model produces one control vector per trial from that trial's four context
windows plus demographics—not one universal vector per fold. The current run
exports test-trial controls; the trained checkpoint can reproduce controls for
training or validation trials, but those were not separately exported.

The values should remain labeled **effective model controls**, not measured
human gains. They differ substantially between independently trained folds,
and folds 2 and 4 show near-zero collapse for several components. This means
the trajectory predictions can be evaluated, but the control values are not
yet sufficiently identifiable or stable for biomechanical interpretation.

## Interpretation limits

- Apparent contact is based on skeleton/video marking, not force-plate contact.
- One optimization seed remains a pilot; repeated seeds are needed for formal
  uncertainty estimates.
- Forecast duration varies by subject because each trial stops at the
  pre-20-degree cutoff. Short- and long-horizon errors are therefore not
  perfectly comparable.
- Four otherwise available trials were excluded because fewer than 0.40 s of
  usable context remained: S62A11T02, S63A11T05, S56A11T02, and S49A11T04.
- The inferred controls are unsupervised effective parameters and are not
  validated physiological measurements.
- Model predictions should be called synthetic only as a provenance label.
  They should not be used to train a future fall detector until their fidelity,
  diversity, leakage risk, and downstream utility have been evaluated.
