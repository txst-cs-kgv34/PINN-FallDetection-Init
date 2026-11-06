# Validation

The delivered artifacts passed:

```bash
python scripts/verify_audit.py --run findings/S46_audit_repaired --source repaired_data/S46
python scripts/verify_inspection.py --run findings/S46_audit_repaired --inspection inspections/S46_candidates_repaired
python -m compileall -q scripts
```

Validated status: 24 numeric trials, 5381 analyzed frames, 0 repaired frames, and 24 inspected trials. Manual A11 phase labels remain pending.
