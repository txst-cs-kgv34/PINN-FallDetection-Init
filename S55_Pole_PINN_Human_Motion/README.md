# S55 Pole PINN Human Motion

This project runs Subject 55's five manually phase-marked A11 front-fall trials through the same four-stage pole-balancing PINN used for the earlier subjects. S55 is male, 145 lb (65.7709 kg), and 5 ft 5 in (1.6510 m).

The project contains both:

- the complete pole-PINN pipeline that identifies the controller and generates 100 synthetic trajectories; and
- `experiments/stage3_gain_sweep`, which runs the later 11-chunk fixed-gain experiment.

## Subject-only input guarantee

Only these files are included and accepted:

- `S55A11T01.csv`
- `S55A11T02.csv`
- `S55A11T03.csv`
- `S55A11T04.csv`
- `S55A11T05.csv`

They were copied from `S55_PINN_audit/repaired_data/S55`. The audit repair manifests report `repaired_rows = 0` for all five A11 trials. The repaired audit layer is still used for consistent provenance, but no S55 A11 coordinates were filled or interpolated.

The build preflight requires the raw inventory to match those five filenames exactly. The adapter, full-run launcher, and gain-sweep launcher also compare the expected and actual `SubjectB_*.tsv` inventories and stop on any missing or extra file. The `SubjectB_` prefix is only the preserved loader filename contract; every packaged TSV contains S55 data.

## Preserved pipeline

`source/pinn_pole_synthetic_data_generation.py` is byte-identical to the validated S43/S57/S62/S63 core and is locked by `CORE_PIPELINE_LOCK.json`:

```text
604985d2344350789929c3554f9ce4351b826f69be1dfe9dee0b20acb586e0a9
```

The network architecture, equations, losses, controller, delayed feedback, training schedules, 30-second generation horizon, and 100-trajectory output are unchanged. Subject-specific work is confined to the S55 data, demographics, manual phases, adapter, paths, validation, and the documented input-duration gate.

The adapter derives a fixed body coordinate frame from each trial's marked standing pose. Whole-body CoM is calculated with the male segment-mass model. Human theta and forward x are represented relative to the fixed foot midpoint at fall onset, then encoded into the unchanged six-column pole loader format.

## Validated input windows

After the original loader's preprocessing and pre-20° cutoff:

| Trial | Usable samples at 100 Hz | Usable duration |
|---|---:|---:|
| S55A11T01 | 147 | 1.46 s |
| S55A11T02 | 54 | 0.53 s |
| S55A11T03 | 136 | 1.35 s |
| S55A11T04 | 134 | 1.33 s |
| S55A11T05 | 153 | 1.52 s |

`config/S55_runtime_overrides.json` sets `minimum_trial_seconds` to 0.50 so all five manually accepted trials remain eligible without padding.

## Run on the MacBook

The launchers use the existing home virtual environment at `~/.venv/bin/activate`.

```bash
cd S55_Pole_PINN_Human_Motion
chmod +x run_on_mac.sh experiments/stage3_gain_sweep/run_on_mac.sh experiments/stage3_gain_sweep/package_results.sh

./run_on_mac.sh setup
./run_on_mac.sh build
./run_on_mac.sh input-check
./run_on_mac.sh smoke
```

The smoke run is only a wiring test. For the real experiment:

```bash
./run_on_mac.sh full
./run_on_mac.sh analyze
./run_on_mac.sh package
```

Both smoke and full modes stream logs to the terminal through `tee` and save copies under `results/`.

## Run the gain sweep

The gain sweep requires the completed clean full run because chunks 1–10 start from the S55-identified controller and every chunk restores the same S55 Stage-1 checkpoint.

```bash
./run_on_mac.sh gain-sweep
./run_on_mac.sh gain-sweep-package
```

See `experiments/stage3_gain_sweep/README.md` for the chunk definitions and metrics.

## Files to return

Please return both:

1. `S55_Pole_PINN_full_run_results.zip`
2. `S55_Stage3_Gain_Sweep_Results.zip`

The gain sweep should only be started after the clean S55 full run succeeds.
