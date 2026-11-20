# Validation record

Validation was completed before packaging this experiment.

## Passed checks

- Repository-relative dataset and audit-folder resolution.
- Strict-primary trial inventory: 257 A10–A13 trials and 49 A14 trials.
- Per-activity planar inventory: A10=58, A11=64, A12=68, A13=67.
- Five-fold subject split integrity: no train/validation/test overlap and every eligible subject appears once as a held-out test subject.
- Five distinct optimization seeds.
- Full preprocessing and prepared-array validation for all 306 trials.
- Physics/no-physics prepared-array parity for all 306 trials.
- Configuration parity beyond the three intended physics switches.
- Paired subject/activity/trial comparison calculations, statistics, and plot generation.
- Python byte-code compilation and shell-script syntax.
- Protocol unit tests.

## Runtime-dependent check

The packaging environment did not contain PyTorch, so the model-shape and differentiable-residual tests were skipped there. They are included in `tests/` and run through `./run.sh test` after `./run.sh setup` installs the pinned requirements in the Mac home virtual environment. Run `./run.sh smoke mps` before the full experiment to exercise both training paths on MPS.

