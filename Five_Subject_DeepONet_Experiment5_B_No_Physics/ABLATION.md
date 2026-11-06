# Matched Model B ablation

This repository is derived from Experiment 2 / Model B. Its purpose is to
isolate the contribution of the explicit biomechanics residual.

## Scientific change

Only the physics contribution to the optimization objective is removed:

```json
"use_physics": false,
"physics_weight": 0.0
```

The experiment name, model ID, result filename, documentation, and validation
rules are renamed so that this run cannot overwrite or be confused with the
completed Model B run. Those are provenance changes, not model changes.

## Preserved from Model B

- the complete `operator_core.py` implementation;
- the convolutional four-window context encoder;
- the positive four-coordinate controller head with Softplus;
- the gain scaling constants;
- the DeepONet branch and Fourier-time trunk;
- the hard initial-position and initial-velocity trajectory form;
- demographics, initial-state, auxiliary, and query-time inputs;
- the five subject folds and real A11 trials;
- preprocessing, masks, normalization, optimizer, learning rate, batch size,
  epoch budget, early stopping, random seeds, and validation rule;
- real held-out test-subject metrics and equal-subject aggregation.

The biomechanics residual function remains in `operator_core.py` solely to
keep the shared Model B source implementation unchanged. Because both
`use_physics` and `physics_weight` are zero, it is not evaluated or added to
the training objective in this experiment.

## Interpretation

Without a physics loss or gain labels, the four positive controller outputs
are not identifiable as physiological gains. In this ablation they should be
reported as positive latent controller coordinates.

The controlled comparisons are:

- **Model B-no-physics vs Model B:** effect of the explicit biomechanics
  residual while holding the architecture and training protocol fixed.
- **Model A vs Model B-no-physics:** effect of changing the unconstrained
  four-dimensional latent head to Model B's positive controller head.
