# Validation

## Audit-package validation

The numeric audit, offline inspection package, and Python source compilation passed.

Validated status: 24 numeric trials, 4337 analyzed frames, 391 repaired frames, and 24 inspected trials.

## Manual A11 phase validation

- Notes file: `analysis_inputs/S56_phase_notes_manual.json`
- Marked trials: 5
- Strict ordered-phase result: **pass**
- Validator result: `PASS: 5 complete, ordered phase-marked trials`
- Modeling decision: `usable_with_repair_sensitivity_check`

Retain all five trials with repair masks. Report a sensitivity analysis because some onset-to-contact intervals contain repaired rows; retain T05 as requested rather than excluding it solely for repair count.
