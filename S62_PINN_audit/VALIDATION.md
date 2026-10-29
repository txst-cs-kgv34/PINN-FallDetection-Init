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
