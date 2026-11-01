# S55 Pole PINN Human Motion

This project runs Subject 55's five manually phase-marked A11 front-fall trials through the unchanged pole-balancing PINN and includes the 11-chunk Stage-3 fixed-gain sweep. S55 is male, 145 lb (65.7709 kg), and 5 ft 5 in (1.6510 m).

## Subject-only input guarantee

Only `S55A11T01.csv` through `S55A11T05.csv` are included and accepted. They came from `S55_PINN_audit/repaired_data/S55`; the repair manifests report zero repaired rows for all five A11 trials. The adapter and both launchers verify the exact five-file inventory and stop on missing or extra data. The retained `SubjectB_` TSV prefix is only the original loader's naming contract; every input is S55.

The unchanged core is locked to SHA-256:

```text
604985d2344350789929c3554f9ce4351b826f69be1dfe9dee0b20acb586e0a9
```

## Accepted motion windows

| Trial | Samples at 100 Hz | Duration | Initial theta |
|:---|---:|---:|---:|
| S55A11T01 | 147 | 1.46 s | -3.048 deg |
| S55A11T02 | 54 | 0.53 s | -2.028 deg |
| S55A11T03 | 136 | 1.35 s | -4.409 deg |
| S55A11T04 | 134 | 1.33 s | -3.238 deg |
| S55A11T05 | 153 | 1.52 s | -0.628 deg |

The five trials provide 624 measured samples. The 0.50-second eligibility gate retains short trial T02 without padding.

## Completed full-run result

The clean run identified:

| Parameter | Value |
|:---|---:|
| `Kp_theta` | 145.145752 |
| `Kd_theta` | 15.052888 |
| `Kp_x` | 5.059635 |
| `Kd_x` | 15.053013 |
| `Pi` | 3.625025 deg |
| `tau` | 0.23 s |

| Checkpoint | Normalized MSE | Theta RMSE | x RMSE |
|:---|---:|---:|---:|
| Stage 1 | 0.002987 | 0.7108 deg | 1.1668 cm |
| Stage 3/final | 0.483574 | 9.6187 deg | 14.4815 cm |

Stage 1 reconstructs the measured windows well. Stage 3 is substantially worse on the time-aligned reconstruction, especially for T01, T03, and T04. The 100 requested synthetic trajectories were generated and are finite, but all first cross 20 degrees at 4.84-5.15 s, well beyond the 0.53-1.52 s measured support. They should therefore be treated as model extrapolations, not validated 30-second human falls. See `FINDINGS.md` for the full interpretation.

## Completed gain-sweep result

All 11 chunks completed. Ranked by pooled normalized MSE, chunk 5 is best:

| Rank | Chunk | Gain source | Normalized MSE | Theta MSE | x MSE |
|---:|---:|:---|---:|---:|---:|
| 1 | 5 | 44.4% interpolation | **0.430774** | 94.059 deg^2 | **175.175 cm^2** |
| 2 | 10 | Subject-B endpoint | 0.433449 | 94.779 deg^2 | 176.127 cm^2 |
| 3 | 8 | 77.8% interpolation | 0.438054 | 92.794 deg^2 | 180.990 cm^2 |

Chunk 5 improves normalized MSE by 5.52% and x MSE by 9.24% relative to chunk 1, but its theta MSE is 2.30% higher. Chunk 11 has the best theta MSE and the lowest training objective, yet ranks last on the combined metric because of its large x error. The full 11-row ranking and metric-specific winners are in `experiments/stage3_gain_sweep/FINDINGS.md`.

## Run on macOS

The launchers activate the existing home environment at `~/.venv/bin/activate`.

```bash
cd S55_Pole_PINN_Human_Motion
chmod +x run_on_mac.sh experiments/stage3_gain_sweep/run_on_mac.sh experiments/stage3_gain_sweep/package_results.sh

./run_on_mac.sh setup
./run_on_mac.sh build
./run_on_mac.sh input-check
./run_on_mac.sh smoke
./run_on_mac.sh full
./run_on_mac.sh analyze
./run_on_mac.sh package

./run_on_mac.sh gain-sweep
./run_on_mac.sh gain-sweep-package
```

Both full and sweep launchers stream output through `tee` and also save logs under their result directories.
