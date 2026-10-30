# Files to return after the Mac full run

Run these commands after `full` finishes:

```bash
./run_on_mac.sh analyze
./run_on_mac.sh package
```

Return the single file `S62_Pole_PINN_full_run_results.zip`.

The packager verifies and includes the identified controller parameters, configuration, logs, Stage 1 and Stage 3 checkpoints, final teacher weights, all 100 `synth_B_*.npy` trajectories, input-validation evidence, evaluation tables, and comparison figures. These are sufficient for the current analysis and for preparing a later gain sweep or teacher model.

If packaging fails, return the complete `results/` directory and the error printed by `./run_on_mac.sh package`.

After the corrected full run has been reviewed, run the Stage-3 sweep and return `S62_Stage3_Gain_Sweep_Results.zip`. Do not use the earlier mixed S62/S63 full-run checkpoint as its baseline.
