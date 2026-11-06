# Validation

The delivered artifacts passed:

```bash
python scripts/verify_audit.py --run findings/S56_audit_repaired --source repaired_data/S56
python scripts/verify_inspection.py --run findings/S56_audit_repaired --inspection inspections/S56_candidates_repaired
python -m compileall -q scripts
```

Validated status: 24 numeric trials, 4337 analyzed frames, 391 repaired frames, and 24 inspected trials. Manual A11 phase labels remain pending.
