# A11 current-data physics diagnostic — five seeds

This experiment isolates the effect of multi-activity pooling in the completed
A10–A13 DeepONet experiment. It trains the same current planar Model B
architecture on only the 64 strict-primary A11 frontfall trials in
`data/processed/Fifteen_Subject_Real_Fall_Physics_Ready`.

Two exactly paired conditions are trained from this one codebase:

```text
physics:     L = Lforecast + 0.01 × LCartPole
no_physics: L = Lforecast
```

Both conditions retain the same current preprocessing, observed
onset-to-contact direction alignment, activity/direction conditioning,
subject folds, five seeds, optimizer, early stopping, and model widths. This
is intentional: the diagnostic changes the activity scope to A11 only without
also changing the coordinate system or architecture.

## Placement

Keep this folder at the repository root beside `data/` and the fifteen audit
folders:

```text
PINN-FallDetection-Init/
├── data/processed/Fifteen_Subject_Real_Fall_Physics_Ready/
├── S30_PINN_audit/ ... S63_PINN_audit/
└── Fifteen_Subject_DeepONet_A11_Current_Data_Physics_Diagnostic_5_Seeds/
```

The preparation step reads the Physics-Ready trial manifest and the repaired
skeleton CSVs in the audit folders. It does not modify either source.

## Recommended Mac MPS run

The scripts reuse `~/.venv` by default. Set `PINN_VENV_DIR` before running if
your environment is elsewhere.

```bash
cd Fifteen_Subject_DeepONet_A11_Current_Data_Physics_Diagnostic_5_Seeds
chmod +x run.sh run_on_mac.sh
./run_on_mac.sh setup
./run_on_mac.sh validate
./run_on_mac.sh test
./run_on_mac.sh smoke mps
./run_on_mac.sh full mps
```

`full` runs 50 models: 2 conditions × 5 seeds × 5 subject folds. Completed
folds are skipped, so the same command resumes an interrupted run.

Check progress without starting training:

```bash
./run_on_mac.sh status
```

Run smaller units if desired:

```bash
./run_on_mac.sh fold physics 1 mps 1
./run_on_mac.sh seed physics 1 mps
./run_on_mac.sh condition physics mps
./run_on_mac.sh condition no_physics mps
./run_on_mac.sh compare
./run_on_mac.sh package
```

The fold command arguments are condition, fold, device, and seed index.

## Outputs to return

After `full` completes, send back:

```text
Fifteen_Subject_A11_Current_Data_Physics_Diagnostic_5_Seeds_Results.zip
```

The archive contains both paired conditions, prediction arrays, model states,
training histories, subject/trial tables, the combined physics-versus-no-
physics boxplot, statistical comparison, logs, and the prepared-data manifest.

## Interpretation

- If A11 physics again improves held-out trajectory error, the previous
  reversal was mainly caused by multi-activity pooling/shared physics.
- If A11 still favors no physics, the next ablation must examine the new
  coordinate construction, strict-primary trial set, sampling, and effective
  physics-loss scale before building activity-specific V2 physics.
- Smaller CartPole residuals alone are not evidence of better forecasting.
- Test subjects never select checkpoints or physics settings.
