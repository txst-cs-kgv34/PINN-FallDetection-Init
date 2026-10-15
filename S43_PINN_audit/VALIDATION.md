# Validation and reproducibility checks

Run all commands from the repository root after installing both Stage 1 and
Stage 2 requirements.

## Fast checks

```bash
python scripts/verify_s43_audit.py
python scripts/verify_inspection.py
python scripts/verify_phase_baseline.py
python scripts/verify_stage1_activity_comparison.py
python scripts/verify_stage2_gradient_pid.py
python scripts/verify_stage2_fixed_delay_profile.py
```

These checks validate the retained data hashes, inspection payload, phase
windows, archived result counts, leakage guards, finite optimizer outputs,
synthetic known-parameter recovery, frozen-checkpoint coverage, and the
fixed-delay decision.

## Stage 1 executable smoke test

```bash
python scripts/verify_stage1_inverted_pendulum.py
```

This trains small two-epoch A11 and A13 models in temporary directories. It
checks the hard initial state, angle definition, numerical controls,
activity-specific axes, all four leave-one-trial-out folds, and finite output.

The checkpoint export path can be tested separately:

```bash
python scripts/export_stage1_checkpoints.py \
  --smoke --output checkpoints/S43_stage1_smoke.json
```

Remove the smoke file after inspection; the exporter refuses to overwrite an
existing checkpoint file.

## Browser viewer check

The viewer test requires Node.js, Playwright, and its Chromium binary:

```bash
npm install
npx playwright install chromium
npm run verify-viewer
```

The scientific pipeline does not depend on the browser test at runtime.

## Expected retained decisions

| Check | Expected result |
|---|---|
| S43 raw audit integrity | Pass: 25 numeric 96-column trials, 6080 frames total |
| Stage 1 fold separation | Pass |
| Revised Stage 2 synthetic recovery | Pass |
| Revised Stage 2 finite held-out simulation | Pass, 16/16 |
| Real-data controller identification gate | Fail |
| Delay identified away from a boundary | Fail |
| Fixed-delay profiles with an interior minimum | 0/16 |

The failed scientific gates are retained findings, not software failures.

## Dependency boundary

Active top-level scripts may import other top-level scripts in `scripts/`, but
must not import code from removed pilot or superseded Stage 2 branches. Frozen
Stage 1 evaluation for revised Stage 2 is isolated in `scripts/frozen_stage1.py`.
The active pipeline has no imports of the removed full-PID least-squares,
nuisance-torque, saturation, Stage 2A, or initial pilot-PINN modules.
