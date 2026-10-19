# S43 Pole-PINN Human-Motion Transfer Experiment

This directory applies the supplied pole-balancing PINN pipeline to S43 human
motion while preserving its core implementation. The source file under
`source/` is byte-identical to the repository version; its SHA-256 is recorded
in `CORE_PIPELINE_LOCK.json` and checked by the validator.

## Scope

The first experiment uses S43 A11 front-fall trials T02–T05. T01 remains
excluded because it was manually confirmed as an invalid fall. A11 is kept
separate from lateral and rotational activities so the scalar `x` state has a
consistent subject-forward meaning.

Human inputs are:

- `theta(t)`: angle from the standing-frame vertical to the female
  segment-mass-weighted whole-body CoM, using the foot midpoint at marked fall
  onset as a fixed origin.
- `x(t)`: subject-forward CoM coordinate relative to that origin. The unchanged
  pole loader subsequently centers its first 0.5 seconds.

The adapter performs no Butterworth smoothing and has no nuisance-torque model.
It linearly interpolates 30 Hz skeleton-derived signals to the 250 Hz input
rate expected by the original loader. It then encodes `theta` and `x` as two
synthetic marker positions in a six-column TSV. The first 1,024 rows are padding
that the original loader discards before training.

## Preserved core

The following remain unchanged:

- conditional PINN architecture and hard initial-state construction;
- Stage 1, Stage 2, Stage 3, and Stage 4 sequence;
- data, history, and physics losses;
- cart-pole residual equations and pole physical constants;
- delayed controller structure, fixed `tau = 0.23 s`, and smooth dead zone;
- default full-run epochs, batch sizes, optimization settings, and generation
  horizon;
- generation of 100 trajectories for the full run.

The launcher changes only the input/output paths in full mode. Its smoke mode
temporarily shortens optimization and creates three trajectories to confirm
that all stages execute; smoke outputs are not scientific results.

## Directory map

| Path | Purpose |
|---|---|
| `source/` | Unmodified advisor-supplied main file |
| `adapter/` | S43 skeleton-to-human-CoM-to-pole-TSV conversion |
| `config/` | S43 demographics and retained A11 phase annotations |
| `data/raw/` | Four selected S43 A11 skeleton files |
| `data/derived/A11/` | Human `theta(t)` and `x(t)` audit tables |
| `data/pole_compatible/A11/` | Six-column inputs consumed by the pole loader |
| `tests/` | Core-integrity and input-contract checks |
| `runner/` | Non-core path override and smoke/full entry point |
| `results/` | Adapter validation and model outputs |

## Run

From this directory:

```bash
python -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -r requirements.txt

python adapter/build_s43_pole_inputs.py
python tests/validate_inputs.py
python runner/run_pipeline.py --mode input-check
python runner/run_pipeline.py --mode smoke
python tests/validate_smoke.py
python runner/run_pipeline.py --mode full
```

## Evaluate the completed full run

The post-run evaluator compares `stage1_best.weights.h5` and
`stage3_best.weights.h5` on the same complete measured dataset, writes the
normalized reconstruction-loss evidence, summarizes all 100 synthetic files,
and creates publication-ready line plots:

```bash
python analysis/evaluate_full_run.py
```

Its outputs are under `results/full_run_evaluation/`. To redraw only the saved
synthetic trajectories (no TensorFlow and no retraining required), use:

```bash
python analysis/visualize_trajectories.py --horizon 5
python analysis/visualize_trajectories.py --horizon 30 --count 20
```

The real-versus-synthetic overlay is qualitative. The generated curves use
random initial angles and zero initial velocities, while the measured trials
have trial-specific initial states; the 30-second region is also far beyond
the available 2.69-5.01 second measured windows.

## Compare original and synthetic CoM distributions

The distribution-comparison script creates original-versus-synthetic line
plots and computes marginal Wasserstein-1 distances for CoM angle and forward
CoM position:

```bash
python analysis/compare_original_synthetic_distributions.py
```

Outputs are written to `results/full_run_distribution_comparison/`. The primary
comparison uses 0-2.69 seconds, the interval available for every real and
synthetic trajectory. The script also reports trajectory-bootstrap confidence
intervals, time-resolved distances, real-to-real variability, synthetic
split-half variability, and initial-angle-matched trajectory comparisons.

Wasserstein distances are computed separately for `theta` (degrees) and `x`
(centimeters). They are marginal distribution distances, not a claim of a
joint multivariate Wasserstein metric or held-out clinical validation.

## Interpretation boundary

This is a software/pipeline transfer experiment. Although the observed inputs
come from human CoM motion, the unchanged loss still enforces the supplied
cart-pole equations and pole parameters. Consequently, generated files should
be described as **human-derived kinematic inputs passed through the unchanged
pole PINN**, not as validated physiological human falls. The human inverted-
pendulum equations in the expanded framework remain a later, separate step.
