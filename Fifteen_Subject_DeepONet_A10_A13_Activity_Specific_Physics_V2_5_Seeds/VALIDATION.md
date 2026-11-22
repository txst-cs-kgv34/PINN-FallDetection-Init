# Validation checklist

Before seed 1, the package must verify:

- exactly 257 strict-primary trials: A10=58, A11=64, A12=68, A13=67;
- signed axes exactly A10 back, A11 forward, A12 left, A13 right;
- no target-derived onset-to-contact direction in coordinate construction;
- four independently parameterized controller heads and one shared operator;
- leakage-free 10/2/3 train/validation/test subject roles in every fold;
- every subject tested exactly once per seed;
- weights exactly `{0, 1e-4, 1e-3, 1e-2}`;
- identical initialization within every seed-fold;
- identical optimizer, schedule, batches, and checkpoint rule across arms;
- validation averaged over subject-activity cells;
- residual normalization by `g/l` and `g`;
- no test access before validation-only selection;
- exact target equality between selected V2 and matched lambda=0 evaluation.

Run:

```bash
./run_on_mac.sh validate
./run_on_mac.sh test
./run_on_mac.sh smoke mps
```

