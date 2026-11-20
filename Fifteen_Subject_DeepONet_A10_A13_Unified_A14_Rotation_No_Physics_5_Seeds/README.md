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
