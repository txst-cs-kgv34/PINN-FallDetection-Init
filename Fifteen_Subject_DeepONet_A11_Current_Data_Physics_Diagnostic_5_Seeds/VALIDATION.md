# Validation record

The package was checked before delivery with:

- Python compilation for every module;
- shell syntax validation for `run.sh` and `run_on_mac.sh`;
- 12 unit tests covering folds, seeds, A11-only scope, paired condition
  settings, Model B constants, Holm adjustment, and comparison pairing;
- preparation of all 64 strict-primary A11 trials from the current
  Physics-Ready manifest;
- validation of every prepared array, mask, direction vector, initial state,
  and A11 activity vector; and
- an end-to-end fixture test of both five-seed aggregations, exact target
  pairing, Wilcoxon/Holm analysis, combined boxplots, and ZIP packaging.

The delivery ZIP excludes generated fixtures, prepared arrays, and results.
PyTorch-dependent model/residual tests are included and will run in the home
venv after `./run_on_mac.sh setup`; PyTorch was unavailable in the packaging
environment, so those three tests were skipped there.
