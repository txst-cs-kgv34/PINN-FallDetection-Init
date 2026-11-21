# Fifteen-subject unified A10–A13 and A14 rotation no-physics baseline

This is the paired data-only baseline for `Fifteen_Subject_DeepONet_A10_A13_Unified_A14_Rotation_Physics_5_Seeds`.

It contains the same two models:

1. unified A10–A13 DeepONet, including A11 frontfall; and
2. separate A14 rotation DeepONet predicting theta, direction-aligned x, and yaw.

The trial selection, preprocessing, direction alignment, subject/activity conditioning, architecture, folds, validation subjects, test subjects, seeds, optimizer, epoch limit, patience, and MPS behavior are identical to the physics condition. The only intended changes are:

```text
training.use_physics = false
training.cartpole_physics_weight = 0
training.rotation_physics_weight = 0
```

The model still has the same controller/latent pathway so architecture capacity remains paired. Physics residuals are computed during evaluation only as diagnostics; they are not optimized.

## Run

```bash
cd Fifteen_Subject_DeepONet_A10_A13_Unified_A14_Rotation_No_Physics_5_Seeds
chmod +x run.sh run_on_mac.sh
./run.sh setup
./run.sh validate
./run.sh test
./run.sh smoke mps
./run.sh full mps
```

The full run trains 50 models. Completed fold summaries are skipped automatically.

## Compare with physics

After both folders finish:

```bash
./run.sh compare
```

or directly:

```bash
python compare_with_physics.py \
  --physics-root ../Fifteen_Subject_DeepONet_A10_A13_Unified_A14_Rotation_Physics_5_Seeds
```

The comparison is paired by seed and held-out subject, activity, and trial. Outputs are written to `comparison/` and include CSV tables, JSON statistics, paired t-tests, win fractions, percentage changes, and plots.

## Completed five-seed results

All 50 no-physics models completed: 25 unified A10–A13 fold/seed models and 25 A14 rotation fold/seed models. Together with the matched physics condition, the comparison covers 100 trained models.

The table below averages the five seeds within each held-out subject and then averages subjects. Lower is better.

| Model | Metric | No physics | Physics | Physics change |
|:--|:--|--:|--:|--:|
| A10–A13 | Normalized MSE | 2.914 | 3.314 | +13.7% |
| A10–A13 | Theta RMSE (deg) | 21.423 | 23.484 | +9.6% |
| A10–A13 | x RMSE (cm) | 29.221 | 31.962 | +9.4% |
| A14 | Normalized MSE | 8.869 | 7.976 | -10.1% |
| A14 | Theta RMSE (deg) | 30.784 | 29.859 | -3.0% |
| A14 | x RMSE (cm) | 45.811 | 43.862 | -4.3% |
| A14 | Yaw RMSE (deg) | 127.769 | 120.232 | -5.9% |

The no-physics model is the stronger A10–A13 trajectory forecaster. Physics improves A14 means, particularly yaw, but those subject-level trajectory differences were not significant after Holm correction. Physics also produces much smaller dynamics residuals, as expected from its training objective.

See `FINDINGS.md` and `comparison/COMPARISON.md` for the full interpretation. The combined paired box-plot figure is `comparison/physics_vs_no_physics_subject_boxplots.png`.
