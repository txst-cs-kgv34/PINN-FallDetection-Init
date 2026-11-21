# Validation contract

The code enforces the following before calibration:

- exactly 64 strict-primary A11 trials;
- the same 15 subjects, five folds, and five seeds as the completed diagnostic;
- 25 complete no-physics warm-start checkpoints;
- the weight grid `0`, `1e-4`, `1e-3`, and `1e-2`;
- no overlap between training, validation, and test subjects;
- no test access during candidate fine-tuning or weight selection; and
- exact target equality with the existing no-physics predictions after the
  selected model is evaluated.

Run:

```bash
./run_on_mac.sh validate
./run_on_mac.sh test
./run_on_mac.sh smoke mps
```

The smoke run is an execution check only. It must not be used for a scientific
claim or weight decision.

