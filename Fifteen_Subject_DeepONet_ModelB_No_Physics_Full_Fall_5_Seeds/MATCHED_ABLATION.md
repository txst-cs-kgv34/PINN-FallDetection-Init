# Matched ablation audit

## Intended causal contrast

The Physics and B-no-physics experiments use identical data, subject roles,
architecture, initialization seeds, optimizer settings, stopping rule, and
test metrics. The only training-objective contrast is:

```text
Physics:     physics_weight = 0.01, use_physics = true
B-no-physics: physics_weight = 0.0,  use_physics = false
```

In B-no-physics, the training loop also gates residual computation with
`use_physics`, so the residual is not merely multiplied by zero after being
constructed: it is not constructed during training.

## Preserved full-fall corrections

- Complete marked source interval through apparent contact.
- 8.0-s grid for smoke and full modes.
- `atan2` angle decoding, preserving trajectories near and beyond 90°.
- Error on grid overflow rather than silent truncation.
- Forecast loss active through the apparent-contact endpoint.
- Separate physics mask excluding the final 0.03 s, used only for post-hoc
  residual diagnostics in this no-physics condition.

## Preserved pairing

- Five grouped held-out folds.
- One real validation subject per fold.
- Three unseen test subjects per fold.
- Base seeds `20261101` through `20261105`.
- Effective fold seed `base_seed + fold_id`.
- 25 trained models in each condition.

## Output compatibility

The no-physics run retains the same metric columns and prediction payloads as
the Physics run. Angular and horizontal residuals are computed after inference
only. This permits direct paired comparisons without implying that residuals
were optimized.

The four positive context outputs retain the same Softplus head and scale
buffers to keep parameter count and computation graph structure matched.
Because no physics loss identifies them, they must be described as latent
conditioning coordinates rather than physiological gains.
