# Findings — pending A11 physics calibration V2

The prior A11-only diagnostic found that fixed-weight physics (`λ=0.01`)
reduced equation residuals but increased mean held-out normalized MSE by 5.62%,
theta RMSE by 5.75%, and CoM-x RMSE by 7.03%. It also showed substantially
higher seed variability and four physics models selected at epoch 10 or
earlier.

This calibration tests the resulting optimization hypothesis without changing
the 64-trial dataset, coordinates, architecture, folds, or seeds.

## Preregistered calibration

- `λ=0`: reuse the matching completed no-physics checkpoint.
- `λ={1e-4, 1e-3, 1e-2}`: warm-start from that same checkpoint.
- Ramp each nonzero weight over 100 epochs.
- Normalize angular residual by `g/l` and horizontal residual by `g`.
- Select the weight and epoch using only the fold's validation subject.
- Evaluate the three held-out test subjects once, after selection.
- Average the five matched seeds within each subject before inference.
- Apply Holm correction across normalized MSE, theta RMSE, and x RMSE.

## Required interpretation

The final result must report:

1. how often each weight was selected across the 25 fold-seed models;
2. selected-policy versus existing no-physics trajectory errors;
3. subject and seed heterogeneity;
4. gradient-ratio and early-checkpoint behavior; and
5. whether the calibration passes the gate for unified A10–A13 V2.

Do not fill this file with smoke-run results. First share the one-seed pilot for
review; the confirmatory conclusion requires all five seeds.

