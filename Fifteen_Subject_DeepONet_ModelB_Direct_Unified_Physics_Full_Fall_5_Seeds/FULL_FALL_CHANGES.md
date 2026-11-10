# Full-fall five-seed rerun

This repository is a new experiment variant. It preserves the five subject
folds, five optimization seeds, Model B architecture, optimizer, and physics
weight while correcting the target interval to standing through apparent
contact.

## Changes relative to the previous five-seed run

- Removed the 20-degree minus 0.08-s cutoff.
- Retained the complete source trajectory through apparent contact.
- Replaced the ambiguous `arcsin` pole-angle decoder with `atan2` and removed
  the 89-degree compatibility trim.
- Added a strict error instead of silently truncating a fall at the configured
  time horizon.
- Kept data loss active through contact.
- Added a separate physics mask excluding only the final 0.03 s at impact.
- Saved angular and horizontal physics residuals separately by time and trial.
- Added full-fall preparation, controller-sign, equilibrium-residual,
  differentiability, and contact-mask tests.

## Run

```bash
chmod +x run.sh run_on_mac.sh
./run.sh setup
./run.sh validate
./run.sh test
./run.sh smoke auto
./run.sh full auto
```

Use `cuda`, `mps`, or `cpu` instead of `auto` when desired. The full command
trains 25 models (`5 seeds × 5 folds`), aggregates them, and creates:

```text
Fifteen_Subject_ModelB_Direct_Unified_Physics_Full_Fall_5_Seeds_Results.zip
```

Return that ZIP for analysis and for the matched full-fall No-Physics rerun.
