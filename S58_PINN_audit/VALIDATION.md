# Validation

## Audit-package validation

The numeric audit, offline inspection package, and Python source compilation passed.

Validated status: 24 numeric trials, 4281 analyzed frames, 2087 repaired frames, and 24 inspected trials.

## Manual A11 phase validation

- Notes file: `analysis_inputs/S58_phase_notes_manual.json`
- Marked trials: 5
- Strict ordered-phase result: **fail**
- Validator result: `FAIL: S58A11T03: phase frames are not strictly increasing; S58A11T04: phase frames are not strictly increasing`
- Modeling decision: `exclude_primary_training_and_generalization`

Do not use S58 for primary full-trajectory training, contact/post-fall supervision, or headline generalization metrics. It may be retained only for an explicitly labeled exploratory pre-contact or censored-data analysis with repaired frames masked.
