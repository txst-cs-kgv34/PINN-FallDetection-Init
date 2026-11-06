# Validation

The delivered artifacts passed:

```bash
python scripts/verify_audit.py --run findings/S45_audit_repaired --source repaired_data/S45
python scripts/verify_inspection.py --run findings/S45_audit_repaired --inspection inspections/S45_candidates_repaired
python -m compileall -q scripts
```

Validated status: 25 numeric trials, 8413 analyzed frames, 0 repaired frames, and 25 inspected trials. Manual A11 phase labels remain pending.
