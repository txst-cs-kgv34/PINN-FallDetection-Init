# Validation

The delivered artifacts passed:

```bash
python scripts/verify_audit.py --run findings/S32_audit_repaired --source repaired_data/S32
python scripts/verify_inspection.py --run findings/S32_audit_repaired --inspection inspections/S32_candidates_repaired
python -m compileall -q scripts
```

Validated status: 21 numeric trials, 5527 analyzed frames, 0 repaired frames, and 21 inspected trials. Manual A11 phase labels remain pending.
