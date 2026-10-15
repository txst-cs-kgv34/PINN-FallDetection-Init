# S43 PINN audit and framework workflow

This is the canonical, subject-specific codebase for S43. It preserves the
manual inspection and phase-marking work, the framework-aligned Stage 1 model,
the revised gradient-based Stage 2, and the fixed-delay diagnostic. Superseded
pilot PINNs, simulated Stage 2A branches, nuisance-torque fits, torque
saturation, and the earlier least-squares Stage 2 are deliberately excluded.

## Scientific scope

The recordings contain 3-D skeleton trajectories but no ground-reaction force,
center-of-pressure, measured perturbation, or instrumented contact data.
Consequently:

- Stage 1 predicts a reduced-order CoM trajectory and angle under an
  inverted-pendulum equation with a learned effective-torque term.
- Revised Stage 2 freezes Stage 1 and estimates only `Kp`, `Kd`, `Ki`, and
  response delay from exact gradients of the governing-equation residual.
- Perturbation torque is fixed to zero in Stage 2. No nuisance-torque smoothing,
  effective-torque matching, torque saturation, or `tau_max` fit is used.
- The fixed-delay diagnostic shows that delay and gains are not identifiable as
  subject physiology from these data. Stage 3 must therefore remain an
  assumption-based virtual sensitivity analysis.

## Directory map

| Path | Purpose |
|---|---|
| `findings/S43_audit/` | Immutable S43 audit run, raw CSVs, findings, and provenance snapshot |
| `inspections/S43_candidates/` | Offline inspection package used to mark phases |
| `analysis_inputs/` | Manually reviewed phase annotations used by modeling |
| `configs/` | Active S43 workflow configurations |
| `scripts/` | Active audit, inspection, Stage 1, revised Stage 2, and verification code |
| `checkpoints/` | Frozen Stage 1 fold/seed weights consumed by Stage 2 |
| `analyses/` | Retained phase baseline, Stage 1, revised Stage 2, and delay-profile results |
| `reviews/notebooks/` | Reference notebook review material |
| `viewer/`, `tests/` | Local manual-inspection interface and its browser check |

The `findings/S43_audit/code/` directory is a provenance snapshot embedded in
the completed historical audit. It is not the active source tree; use
top-level `scripts/` for new work.

## Environment

Run commands from the `S43_PINN_audit` directory using Python 3.10 or newer.

```bash
python -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -r requirements-stage1.txt -r requirements-stage2-gradient.txt
```

`requirements-stage1.txt` includes the common, inspection, SciPy, and PyTorch
dependencies. `requirements-stage2-gradient.txt` adds Autograd for the frozen
Stage 1 gradient evaluator and controller optimization.

The optional browser regression test has its separate dependency declaration
in `package.json`; it is not required for the scientific Python pipeline.

## Canonical workflow

### 0. Verify the retained audit and phase annotations

```bash
python scripts/verify_s43_audit.py
python scripts/verify_inspection.py
python scripts/verify_phase_baseline.py
```

The inspection package and phase notes are retained because the phase marks
were manually reviewed. To create a new inspection directory, use
`scripts/inspect_trials.py`; do not overwrite the retained directory.

### 1. Run Stage 1 independently for each activity

The archived outputs used four whole-trial folds, two seeds, and the physics
weight sweep recorded in each experiment configuration. The following commands
show the retained A11 and A13 specifications and write to new directories:

```bash
python scripts/run_stage1_inverted_pendulum.py \
  --run findings/S43_audit \
  --config configs/S43.json \
  --selection configs/S43_modeling_selection.json \
  --phase-notes analysis_inputs/S43_A11_phase_notes.json \
  --activity A11 --horizontal-axis forward \
  --output analyses/S43_A11_stage1_rerun

python scripts/run_stage1_inverted_pendulum.py \
  --run findings/S43_audit \
  --config configs/S43.json \
  --selection configs/S43_modeling_selection.json \
  --phase-notes analysis_inputs/S43_phase_notes_with_A13_eligibility.json \
  --activity A13 --horizontal-axis lateral \
  --output analyses/S43_A13_stage1_rerun
```

The retained Stage 1 outputs select physics weight `0.01` for the downstream
checkpoint ensemble. That selection is exploratory and is not independent
validation.

### 2. Export and freeze the selected Stage 1 checkpoints

```bash
python scripts/export_stage1_checkpoints.py \
  --output checkpoints/S43_stage1_frozen_checkpoints_rerun.json
```

This trains only Stage 1, independently in each activity/fold/seed, and writes
16 checkpoints. It does not fit a controller. A quick dependency and data-path
test is available without overwriting the retained checkpoint file:

```bash
python scripts/export_stage1_checkpoints.py \
  --smoke --output checkpoints/S43_stage1_smoke.json
```

If a regenerated checkpoint ensemble is approved for use, update
`stage1.checkpoint_file` in `configs/S43_stage2_gradient_pid.json`. The retained
Stage 2 results reference `checkpoints/S43_stage1_frozen_checkpoints.json`.

### 3. Run revised Stage 2

```bash
python scripts/run_stage2_gradient_pid.py \
  --output analyses/S43_stage2_gradient_pid_rerun
python scripts/verify_stage2_gradient_pid.py
```

The optimizer loads the retained Stage 1 state dictionaries through
`scripts/frozen_stage1.py`, freezes them, and differentiates the controller
physics loss only with respect to `Kp`, `Kd`, `Ki`, and continuous delay.

### 4. Run the fixed-delay diagnostic

```bash
python scripts/run_stage2_fixed_delay_profile.py \
  --output analyses/S43_stage2_fixed_delay_profile_rerun
python scripts/verify_stage2_fixed_delay_profile.py
```

The retained result has no interior delay minimum: all 16 fold/seed profiles
prefer the largest tested delay. Do not report the boundary value as a measured
human response delay and do not average the gains into a subject phenotype.

### 5. Proceed to Stage 3A only with explicit assumptions

Use `S43_STAGE3A_ASSUMPTION_BASED_PLAN.md` as the specification. Carry the full
fixed-delay controller ensemble, prescribe virtual rectangular torque pulses,
and report uncertainty envelopes. Label results as model sensitivity under
assumed perturbations, not measured recovery capacity or a clinical fall
boundary.

## Verification

See `VALIDATION.md` for the complete verifier list, dependency-boundary checks,
and the expected retained-result decisions.
