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

## Completed result

All 50 planned models completed. Removing multi-activity pooling did not restore
the earlier A11 physics advantage. With the fixed CartPole weight `0.01`,
physics increased mean held-out normalized MSE by 5.62%, theta RMSE by 5.75%,
and direction-aligned CoM-x RMSE by 7.03% relative to the paired no-physics
condition. None of the three subject-level comparisons was significant after
Holm correction.

Physics nevertheless reduced the angular and horizontal equation residuals by
17.6% and 97.0%, respectively. This means the residual was active and
optimizable, but lower equation residual did not translate into better held-out
trajectory prediction. See `FINDINGS.md` for the full pairing audit, stability
analysis, and V2 decision.

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

## Interpretation and V2 decision

- A11 still favors no physics, so multi-activity pooling is not a sufficient
  explanation for the reversal.
- Do not carry the fixed `0.01` weight unchanged into full V2.
- First calibrate A11 using a data-only warm start, a gradual physics ramp, and
  validation-only candidates `0`, `1e-4`, `1e-3`, and `1e-2`.
- V2 should use activity-defined sagittal/frontal coordinates and
  activity-specific controller/residual heads. The observed onset-to-contact
  direction must not be a forecast input because it is computed from future
  trajectory information.
- Keep A14 separate with its CartPole-plus-yaw residual.
- Smaller CartPole residuals alone are not evidence of better forecasting.
- Test subjects must never select checkpoints, coordinates, or physics weights.
