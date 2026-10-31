# S57 Pole-PINN Human-Motion Transfer

This project runs Subject 57's manually marked A11 front-fall motion through the same four-stage pole-balancing PINN used for S63. S57 is male, 180 lb (81.6466 kg), and 5 ft 8 in (1.7272 m). Only the complete trials T03-T05 are included; T01-T02 are explicitly excluded as incomplete.

The core file `source/pinn_pole_synthetic_data_generation.py` is byte-identical to the S63 project and locked by `CORE_PIPELINE_LOCK.json` (SHA-256 `604985d2344350789929c3554f9ce4351b826f69be1dfe9dee0b20acb586e0a9`). The network, equations, losses, controller, delayed feedback, four stages, full-run epochs, 30-second horizon, and 100 generated trajectories are unchanged. Subject-specific Stage-3 gain-sweep code is included under `experiments/stage3_gain_sweep`.

## Completed clean rerun and gain sweep

The corrected rerun and all 11 gain chunks completed successfully with exactly `S57A11T03-T05` (609 measured samples). The first mixed S57/S63 archive is superseded and must not be used.

The clean full run identified gains `(145.061, 15.056, 5.063, 15.057)`, Pi `3.6295 deg`, and tau `0.23 s`. Stage 1 reconstructed the fitted data closely (`normalized loss = 0.002222`), but Stage 3 increased it to `1.269441`, showing a large data-fit versus physics-refinement tradeoff.

The sweep's primary combined reconstruction metric selects chunk 10, the Subject-B endpoint `(240, 30, 13, 30)`, with normalized MSE `1.098801`. Relative to chunk 1, it improves x error but worsens theta error and the Stage-3 objective, so it is not a universally superior control set. See `FINDINGS.md` for the full numerical interpretation and teacher-selection cautions.

## Inputs and adapter

The adapter computes a male segment-mass-weighted whole-body CoM in a subject-centered frame, fixes the foot midpoint at marked fall onset as the pivot, and constructs:

- `theta(t)`: CoM angle from subject-frame vertical;
- `x(t)`: subject-forward CoM displacement from the same fixed pivot.

There is no smoothing. Linear interpolation converts 30 Hz signals to the 250 Hz format expected by the original loader. The `SubjectB_*.tsv` prefix is only the unchanged loader's filename contract; the files contain S57 data. Raw inputs are the repaired audit copies, although these three A11 files required no missing-row repair.

The source loader trims shortly before the first `|theta| >= 20 deg` crossing. The resulting usable windows are 1.87, 2.07, and 2.12 seconds. The original 2.0-second eligibility gate would reject T03, so `config/S57_runtime_overrides.json` uses the documented 0.25-second gate without padding or architecture changes.

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

The clean full-run handoff is `S57_Pole_PINN_full_run_results.zip`. The later chunk-sweep handoff is `S57_Stage3_Gain_Sweep_Results.zip`. If packaging fails, return the complete relevant results directory.

## Interpretation boundary

The measured inputs are human whole-body CoM kinematics, but the preserved loss enforces pole mechanics and pole constants. Treat the generated trajectories as human-derived kinematic inputs passed through the pole PINN, not as validated physiological simulations. The same real trials are used for fitting and post-run comparison, so the analysis is descriptive rather than held-out validation.
