# S63 Pole-PINN Human-Motion Transfer

This project reruns the same four-stage pole-balancing PINN used for S43 with Subject 63's manually marked A11 front-fall data. S63 is male, 180 lb (81.6466 kg), and 5 ft 6 in (1.6764 m). All five A11 trials, T01-T05, are included.

The core source at `source/pinn_pole_synthetic_data_generation.py` is byte-identical to the S43 project. Its SHA-256 is locked in `CORE_PIPELINE_LOCK.json`. The conditional network, hard initial-state construction, controller, delayed feedback, cart-pole equations, losses, four stages, full-run epochs/batches, 30-second generation horizon, and 100 generated trajectories are unchanged. No Stage-3 gain sweep is included.

## Inputs

The canonical manual phase file is `config/S63_A11_phase_notes.json`. Trial inclusion is kept separately in `config/S63_A11_experiment_scope.json`, so the manual observations remain unchanged.

The adapter computes a male segment-mass-weighted whole-body CoM, defines the foot midpoint at marked fall onset as a fixed origin, and constructs:

- `theta(t)`: CoM angle from subject-frame vertical;
- `x(t)`: subject-forward CoM displacement from the same fixed origin.

It performs no Butterworth smoothing. Linear interpolation converts 30 Hz signals to the 250 Hz input expected by the original loader. The six TSV columns are `x1_mm, y1_mm, z1_mm, x2_mm, y2_mm, z2_mm`; two synthetic marker positions encode `theta` and `x`. The inherited `SubjectB_*.tsv` prefix is only the unchanged loader's filename contract and does not mean these are Subject B recordings.

## S63 duration gate

The unchanged loader trims each trial shortly before the first `|theta| >= 20 deg` crossing and rejects trials shorter than two seconds. All five tightly cropped S63 clips cross that threshold early, leaving approximately 0.35-1.25 seconds. With the original two-second gate, every trial would be discarded.

`config/S63_runtime_overrides.json` therefore sets only `minimum_trial_seconds` to 0.25. This retains the observed data without manufacturing stationary padding. It does not modify the source file or model architecture, but it is a subject-specific input-eligibility change and must be disclosed when reporting the experiment. The brief windows also limit how strongly the fitted controls and real-vs-synthetic comparison can be interpreted.

## Directory map

| Path | Purpose |
|---|---|
| `source/` | Byte-preserved pole pipeline |
| `adapter/` | S63 skeleton-to-CoM-to-six-column-TSV conversion |
| `config/` | Demographics, manual phases, inclusion scope, and the documented duration gate |
| `data/raw/` | Five S63 A11 skeleton trials copied from `S63_PINN_audit` |
| `data/derived/A11/` | Auditable human `theta(t)` and `x(t)` tables created by the adapter |
| `data/pole_compatible/A11/` | Six-column inputs consumed by the unchanged loader |
| `runner/` | Input-check, smoke/full launcher, and result packager |
| `analysis/` | Checkpoint, trajectory, and Wasserstein comparisons after the full run |
| `tests/` | Core-integrity, input-contract, and smoke-output checks |

## MacBook Air M3 run

Open Terminal, change into this directory, and run:

```bash
chmod +x run_on_mac.sh
./run_on_mac.sh setup
./run_on_mac.sh build
./run_on_mac.sh input-check
./run_on_mac.sh smoke
./run_on_mac.sh full
./run_on_mac.sh analyze
./run_on_mac.sh package
```

`setup` creates `.venv` and installs the requirements. `smoke` uses two epochs per training stage and generates only three trajectories; it is an execution test, not a scientific result. `full` retains the original training schedule and generates 100 trajectories. Expect the full run to be the expensive step.

If you prefer individual commands after activating `.venv`, use:

```bash
python adapter/build_s63_pole_inputs.py
python tests/validate_inputs.py
python runner/run_pipeline.py --mode input-check
python runner/run_pipeline.py --mode smoke
python tests/validate_smoke.py
python runner/run_pipeline.py --mode full
python analysis/evaluate_full_run.py
python analysis/compare_original_synthetic_distributions.py
python analysis/visualize_trajectories.py --horizon 5
python runner/package_results.py
```

## Post-run figures

The analysis creates checkpoint reconstruction tables, real-versus-synthetic CoM trajectories, synthetic envelopes, marginal distribution comparisons, and `real_vs_synthetic_means_and_wasserstein.png`. That combined figure places the real and synthetic means beside the time-resolved Wasserstein-1 distance and its time-mean reference line.

Wasserstein distances are computed separately for `theta` in degrees and `x` in centimeters. They are marginal distances, not a joint multivariate metric. Because the common S63 pre-cutoff window is short and the five real trials were used for fitting, these plots are descriptive training-set checks rather than held-out validation.

## Return for analysis

After `full` and `analyze` finish, run `./run_on_mac.sh package` and return `S63_Pole_PINN_full_run_results.zip`. The packager includes the controller parameters, configuration, logs, checkpoints, all 100 synthetic `.npy` trajectories, input-validation evidence, evaluation tables, and comparison figures. If packaging fails, return the complete `results/` directory instead.

## Interpretation boundary

The observed inputs are human CoM trajectories, but the unchanged loss enforces pole mechanics and pole constants. Report the generated files as human-derived kinematic inputs passed through the pole PINN—not as validated physiological simulations of human falls.
