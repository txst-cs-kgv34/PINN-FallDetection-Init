# Validation

The delivered artifacts were checked with:

```bash
python scripts/verify_audit.py --run findings/S55_audit --source ../upload/S55_FallSamples.zip
python scripts/verify_inspection.py --run findings/S55_audit --inspection inspections/S55_candidates
python -m compileall -q scripts
```

Expected delivered status: 25 expected files; 21 numeric, 0 empty, 4 invalid; 3,562 analyzed frames; 21 inspection trials.

After manual notes are exported:

```bash
python scripts/validate_phase_notes.py --notes analysis_inputs/S55_phase_notes.json --run findings/S55_audit --selection configs/S55_inspection_selection.json --output analysis_inputs/S55_phase_windows.json
```

## Repaired workflow

```bash
python scripts/verify_audit.py --run findings/S55_audit_repaired --source repaired_data/S55
python scripts/verify_inspection.py --run findings/S55_audit_repaired --inspection inspections/S55_candidates_repaired
python -m compileall -q scripts
```

Expected repaired status: 25 numeric trials, 4,240 analyzed frames, 80 repaired
frames represented in the inspection mask, and 25 inspection trials.

## Validated A11 phase windows

```bash
python scripts/validate_phase_notes.py --notes analysis_inputs/S55_phase_notes.json --run findings/S55_audit_repaired --selection configs/S55_A11_phase_selection.json --output analysis_inputs/S55_A11_phase_windows.json
```

Expected status: 5 complete, ordered phase-marked A11 trials.
