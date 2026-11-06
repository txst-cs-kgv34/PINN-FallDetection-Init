# Validation

The delivered artifacts passed:

```bash
python scripts/verify_audit.py --run findings/S44_audit_repaired --source repaired_data/S44
python scripts/verify_inspection.py --run findings/S44_audit_repaired --inspection inspections/S44_candidates_repaired
python -m compileall -q scripts
```

Validated status: 25 numeric trials, 7322 analyzed frames, 0 repaired frames, and 25 inspected trials. Manual A11 phase labels remain pending.
