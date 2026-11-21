# Validation checklist

The package must satisfy these checks before a full run:

- exactly 64 strict-primary A11 trials;
- leakage-free 11/1/3 grouped subject folds;
- every subject tested exactly once per seed;
- weights exactly `{0, 1e-4, 1e-3, 1e-2}`;
- 800 maximum epochs and `5e-4` learning rate for every arm;
- identical deterministic initialization within a seed-fold;
- identical batch order, optimizer, schedule, minimum training period,
  patience, and validation checkpoint rule;
- residual normalization by `g/l` and `g`;
- no test access before validation-only λ selection;
- exact target equality between selected V3 and matched λ=0 evaluation;
- subject is the independent unit in paired inference.

Run:

```bash
./run_on_mac.sh validate
./run_on_mac.sh test
./run_on_mac.sh smoke mps
```

The smoke test also exercises all four arms and refuses selection if their
initial-state hashes or pre-training validation losses disagree.
