# Files to return after local execution

Run the clean S55 full pipeline first:

```bash
./run_on_mac.sh full
./run_on_mac.sh analyze
./run_on_mac.sh package
```

Return:

```text
S55_Pole_PINN_full_run_results.zip
```

Then run and package the gain sweep:

```bash
./run_on_mac.sh gain-sweep
./run_on_mac.sh gain-sweep-package
```

Return:

```text
S55_Stage3_Gain_Sweep_Results.zip
```

Do not copy checkpoints or TSV inputs from another subject into this project. The validation code intentionally rejects an extra or mismatched subject inventory.
