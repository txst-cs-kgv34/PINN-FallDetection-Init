# A11 DeepONet physics calibration V2 — five seeds

This is the follow-up to
`Fifteen_Subject_DeepONet_A11_Current_Data_Physics_Diagnostic_5_Seeds`.
It determines whether staged optimization and a validation-selected CartPole
weight can improve A11 forecasting without rerunning the completed no-physics
baseline.

Keep this as a **new directory**. Do not overwrite the completed diagnostic;
its checkpoints, metrics, and pairing record are the frozen `λ=0` reference.

## Seed-1 pilot result — stop before seeds 2–5

The pilot completed all 15 candidate fine-tunes and five fold selections. Every
fold selected the unchanged `λ=0` checkpoint:

| Validation fold | Selected weight | Selected epoch after warm start |
|---:|---:|---:|
| 1 | 0 | 0 |
| 2 | 0 | 0 |
| 3 | 0 | 0 |
| 4 | 0 | 0 |
| 5 | 0 | 0 |

All three nonzero candidates also recorded epoch 0 as their best validation
checkpoint in every fold. Consequently, the selected-policy test predictions
are exactly the existing no-physics predictions: normalized MSE `3.4014`, theta
RMSE `21.4531°`, and x RMSE `30.4418 cm` for seed 1.

**Do not run `./run_on_mac.sh full mps` for this warm-start experiment.** The
pilot failed its preregistered gate because no fold selected nonzero physics.
Seeds 2–5 would cost 60 additional fine-tunes without resolving the main
confound described in `FINDINGS.md`.

## Experimental question

For every fold and seed, the calibration starts from the matching completed
no-physics checkpoint and tests three nonzero target weights:

```text
λ = 1e-4, 1e-3, 1e-2
```

The already completed no-physics checkpoint is the fourth candidate, `λ=0`.
The validation subject selects the weight and checkpoint. The three held-out
test subjects are evaluated only after selection.

This produces one deployable selection rule rather than reporting the best
test-set weight after looking at test results.

## What changed from the failed fixed-weight diagnostic

1. Every nonzero candidate is warm-started from the matching validation-selected
   no-physics checkpoint.
2. Physics is ramped linearly from zero to its target weight over 100 epochs.
3. Fine-tuning uses learning rate `1e-4`, at most 300 epochs, and patience 80.
4. Angular and horizontal residuals are trained as separate normalized heads:

   ```text
   angular residual scale   = g / l
   horizontal residual scale = g
   ```

5. The data and physics gradient norms are logged once per epoch, together with
   their effective weighted ratio.
6. `λ=0` remains eligible. If every physics candidate is worse on validation,
   the procedure correctly retains the existing no-physics model.

## What intentionally did not change

- the same 64 strict-primary A11 trials;
- current direction-aligned coordinates and conditioning;
- the same Model B architecture;
- the same five subject folds and five optimization seeds;
- the same forecast target, context window, masks, and CartPole equations; and
- validation forecast MSE as the checkpoint-selection metric.

This calibration was intended to isolate physics weighting and optimization,
but the pilot showed that resuming from an already validation-selected
checkpoint confounds the comparison with optimizer continuation. It does **not**
test activity-defined sagittal/frontal axes. Changing coordinates would
invalidate reuse of the existing no-physics checkpoints and would require a
new matched baseline. That coordinate change belongs in the later full V2
A10–A13 experiment.

## Directory placement

Place this folder beside the completed diagnostic, `data/`, and the audit
folders:

```text
PINN-FallDetection-Init/
├── data/processed/Fifteen_Subject_Real_Fall_Physics_Ready/
├── S30_PINN_audit/ ... S63_PINN_audit/
├── Fifteen_Subject_DeepONet_A11_Current_Data_Physics_Diagnostic_5_Seeds/
│   └── results/no_physics/full/...
└── Fifteen_Subject_DeepONet_A11_Physics_Calibration_V2_5_Seeds/
```

The completed diagnostic must contain all 25 no-physics
`final_best_model_state.pt` files and its multi-seed metric tables. If it is in
another location, set an absolute path before running:

```bash
export A11_BASELINE_ROOT="/absolute/path/to/Fifteen_Subject_DeepONet_A11_Current_Data_Physics_Diagnostic_5_Seeds"
```

## Recommended Mac MPS sequence

Reuse your home environment by default, or set `PINN_VENV_DIR` if needed.

```bash
cd Fifteen_Subject_DeepONet_A11_Physics_Calibration_V2_5_Seeds
chmod +x run.sh run_on_mac.sh
./run_on_mac.sh setup
./run_on_mac.sh validate
./run_on_mac.sh test
./run_on_mac.sh smoke mps
./run_on_mac.sh pilot mps
```

`pilot` runs seed 1 across all five folds: 15 warm-started fine-tunes, five
validation selections, and one exploratory comparison with the existing
no-physics seed-1 result. It packages
`Fifteen_Subject_A11_Physics_Calibration_V2_Seed_01_Pilot_Results.zip`.
Share that pilot ZIP before spending time on the remaining four seeds.

If a future pilot passes the gate, the five-seed command is:

```bash
./run_on_mac.sh full mps
```

It is intentionally **not recommended for the present pilot result**.

The full run contains:

```text
3 nonzero weights × 5 folds × 5 seeds = 75 fine-tunes
5 folds × 5 seeds = 25 validation-selected test evaluations
```

The 25 no-physics models are reused and are not trained again. Interrupted
runs resume automatically. Set `FORCE=1` only when intentionally rerunning a
completed unit.

## Smaller commands

```bash
./run_on_mac.sh fold 1 mps 1
./run_on_mac.sh seed 1 mps
./run_on_mac.sh status
./run_on_mac.sh aggregate
./run_on_mac.sh compare
./run_on_mac.sh package
```

`fold 1 mps 1` means fold 1, MPS, seed index 1.

## Outputs

Candidate folders contain only training/validation information; they do not
contain test metrics. After validation selection, held-out predictions are
written under:

```text
results/selected/full/seed_XX_YYYYYYYY/fold_XX/
```

The final comparison with the existing no-physics baseline is written to:

```text
comparison/full/
```

It includes subject-level paired tables, Holm-adjusted Wilcoxon tests, selected
weight counts, and a combined V2-versus-no-physics box-plot figure. The packaged
result is:

```text
Fifteen_Subject_A11_Physics_Calibration_V2_5_Seeds_Results.zip
```

## Decision rule for the next experiment

- Proceed to the five-seed confirmation only if the seed-1 pilot is stable and
  at least some folds select a nonzero weight without degrading held-out
  trajectory errors severely.
- Proceed to unified A10–A13 V2 only if the five-seed selected policy improves
  or credibly matches the existing no-physics model while reducing instability.
- If `λ=0` dominates, do not search weights on the test data. Move to the
  separately matched activity-defined-coordinate experiment.

The seed-1 result triggered the final rule: `λ=0` was selected in all five
folds. The next useful calibration must train the normalized/ramped physics
candidates from the same initial model state as the baseline, rather than
continuing from a checkpoint that was already selected at its validation
minimum.

