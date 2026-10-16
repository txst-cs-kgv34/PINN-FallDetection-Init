# Current status

## Completed

- Created a standalone S43 pole-PINN transfer experiment.
- Preserved `source/pinn_pole_synthetic_data_generation.py` byte-for-byte with
  SHA-256 `604985d2344350789929c3554f9ce4351b826f69be1dfe9dee0b20acb586e0a9`.
- Copied the four approved A11 trials (T02–T05), S43 demographic metadata, and
  manual A11 phase annotations into the experiment.
- Implemented an external adapter that derives female segment-weighted CoM,
  subject-forward `x(t)`, and CoM angle `theta(t)` without adding a smoothing
  function or nuisance torque.
- Generated four six-column, 250 Hz TSVs compatible with the unchanged pole
  loader.
- Verified with the original `read_tsv()` and `load_trials()` implementation
  that all four trials are accepted:

| Trial | Samples at 100 Hz | Usable duration |
|---|---:|---:|
| S43A11T02 | 502 | 5.01 s |
| S43A11T03 | 440 | 4.39 s |
| S43A11T04 | 310 | 3.09 s |
| S43A11T05 | 270 | 2.69 s |

- Executed an end-to-end smoke run through original Stages 1–4 on CPU.
- Produced Stage 1 and Stage 3 weights, Stage 2 controller output, plots, and
  three 30-second synthetic trajectory files.

## What the smoke run proves

The complete supplied program can consume the S43-derived inputs and execute
all four stages without shape, differentiation, dependency, or serialization
errors. It does not prove trajectory quality: two epochs per stage leave the
network severely undertrained, and the smoke trajectories have extreme values.

## Next step

Run `python runner/run_pipeline.py --mode full` on a GPU-capable machine. Full
mode restores the exact supplied settings: 7,000 Stage 1 epochs, 5,000 Stage 2
epochs, 5,000 Stage 3 epochs, default batch sizes, 30-second horizon, and 100
generated trajectories. Afterward, inspect reconstruction, loss histories,
physics residuals, angle/position ranges, and the fraction of trajectories
remaining within a declared plausibility envelope before calling the output
usable synthetic motion.

The resulting parameters remain effective parameters of the unchanged pole-
cart equations. They must not be reported as human physiological controller
gains or the generated files as validated human falls.
