# Validation

The delivered artifacts were checked with:

```bash
python scripts/verify_audit.py --run findings/S62_audit --source ../upload/S62_FallSamples.zip
python scripts/verify_inspection.py --run findings/S62_audit --inspection inspections/S62_candidates
python -m compileall -q scripts
```

Expected delivered status: 25 expected files; 18 numeric, 0 empty, 7 invalid; 3,077 analyzed frames; 18 inspection trials.

After manual notes are exported:

```bash
python scripts/validate_phase_notes.py --notes analysis_inputs/S62_phase_notes.json --run findings/S62_audit --selection configs/S62_inspection_selection.json --output analysis_inputs/S62_phase_windows.json
```

## Repaired workflow

```bash
python scripts/verify_audit.py --run findings/S62_audit_repaired --source repaired_data/S62
python scripts/verify_inspection.py --run findings/S62_audit_repaired --inspection inspections/S62_candidates_repaired
python -m compileall -q scripts
```

Expected repaired status: 25 numeric trials, 4,390 analyzed frames, 109 repaired
frames represented in the inspection mask, and 25 inspection trials.

## Validated A11 phase windows

The original notes are preserved. The model-ready derivative omits T02 because
standing and onset are both frame 0.

```bash
python scripts/validate_phase_notes.py --notes analysis_inputs/S62_phase_notes_model_ready.json --run findings/S62_audit_repaired --selection configs/S62_A11_phase_selection.json --output analysis_inputs/S62_A11_phase_windows.json
```

Expected status: 4 complete, ordered phase-marked A11 trials.
