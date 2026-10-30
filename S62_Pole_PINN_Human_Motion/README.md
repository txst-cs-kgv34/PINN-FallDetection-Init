# S62 Pole-PINN Human-Motion Transfer

This project runs Subject 62's manually marked A11 front-fall motion through the same four-stage pole-balancing PINN used for S63. S62 is male, 155 lb (70.3068 kg), and 5 ft 4 in (1.6256 m). Trials T01-T05 are included, including the corrected T02 marks: frame 0 is `initial_standing` and frame 1 is `fall_onset`.

The core file `source/pinn_pole_synthetic_data_generation.py` is byte-identical to the S63 project and locked by `CORE_PIPELINE_LOCK.json` (SHA-256 `604985d2344350789929c3554f9ce4351b826f69be1dfe9dee0b20acb586e0a9`). The network, equations, losses, controller, delayed feedback, four stages, full-run epochs, 30-second horizon, and 100 generated trajectories are unchanged. Subject-specific Stage-3 gain-sweep code is included under `experiments/stage3_gain_sweep`.

## Important correction after the first returned full run

The first returned full-run archive is not a clean S62 experiment. Its reconstruction table contains the five S62 trials plus five stale S63 trials, for 10 accepted trajectories and 1,290 pooled samples. Consequently, its identified gains, checkpoints, 100 generated falls, and distribution plots are mixed S62/S63 results and must not be used as the S62 baseline or as a gain-sweep teacher.

This corrected package contains exactly `S62A11T01-T05`. The adapter, validator, runner, full-run packager, and gain-sweep launcher now reject any extra `SubjectB_*.tsv` files. See `FINDINGS.md` for the numerical audit and interpretation.

## Inputs, orientation, and adapter

The adapter computes a male segment-mass-weighted whole-body CoM in a subject-centered frame, fixes the foot midpoint at marked fall onset as the pivot, and constructs:

- `theta(t)`: CoM angle from subject-frame vertical;
- `x(t)`: subject-forward CoM displacement from the same fixed pivot.

The subject-forward axis is oriented using the skeleton's nose direction, so S62's camera-facing front falls are normalized into the same body-centered definition used for the other subjects. Camera axes are not treated as the control axes.

There is no smoothing. Linear interpolation converts 30 Hz signals to the 250 Hz format expected by the original loader. The `SubjectB_*.tsv` prefix is only the unchanged loader's filename contract; the files contain S62 data. Raw inputs are the repaired audit copies. Four trials pass 89 degrees only after the loader's 20-degree training cutoff; the adapter removes those unused tails instead of folding them through `arcsin`. The manifest records every such trim, and it does not change any sample used for training.

After the source loader's pre-20-degree trim, usable windows range from 0.23 to 2.96 seconds. `config/S62_runtime_overrides.json` uses a 0.20-second eligibility gate so the manually accepted T02 is retained without padding. T02's very short window is a material limitation and should be reported when comparing S62 with other teachers.

## Run on a MacBook Air M3

Python 3.11 is recommended. The launcher activates the existing home virtual environment at `~/.venv/bin/activate`; it does not create a project-local environment. In Terminal, enter this directory and run:

```bash
chmod +x run_on_mac.sh
./run_on_mac.sh setup
./run_on_mac.sh build
./run_on_mac.sh input-check
./run_on_mac.sh smoke
PYTHONUNBUFFERED=1 ./run_on_mac.sh full
./run_on_mac.sh analyze
./run_on_mac.sh package
./run_on_mac.sh gain-sweep
./run_on_mac.sh gain-sweep-package
```

`smoke` uses two epochs per stage and creates three trajectories only as an execution test. `full` preserves the original 7,000/5,000/5,000 epoch schedule and generates 100 trajectories. The gain sweep must be run only after this corrected full run completes; it will refuse an older checkpoint that lacks subject-only inventory provenance. Checkpoint files make the output folder large; keep adequate free disk space and prevent the laptop from sleeping during `full`.

The clean full-run handoff is `S62_Pole_PINN_full_run_results.zip`. The later chunk-sweep handoff is `S62_Stage3_Gain_Sweep_Results.zip`. If packaging fails, return the complete relevant results directory.

## Interpretation boundary

The measured inputs are human whole-body CoM kinematics, but the preserved loss enforces pole mechanics and pole constants. Treat the generated trajectories as human-derived kinematic inputs passed through the pole PINN, not as validated physiological simulations. The same real trials are used for fitting and post-run comparison, so the analysis is descriptive rather than held-out validation.
