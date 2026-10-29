# Validation

The delivered repaired artifacts were checked with:

```bash
python scripts/verify_audit.py --run findings/S57_audit_repaired --source repaired_data/S57
python scripts/verify_inspection.py --run findings/S57_audit_repaired --inspection inspections/S57_candidates_repaired
python -m compileall -q scripts
```

Expected delivered status: 25 numeric trials, 3,841 analyzed frames, 139
repaired frames represented in the inspection mask, and 25 inspection trials.

Validated A11 phase windows:

```bash
python scripts/validate_phase_notes.py --notes analysis_inputs/S57_phase_notes.json --run findings/S57_audit_repaired --selection configs/S57_A11_phase_selection.json --output analysis_inputs/S57_A11_phase_windows.json
```

Expected status: 3 complete, ordered phase-marked trials; A11T01 and A11T02
are explicitly excluded as incomplete.
