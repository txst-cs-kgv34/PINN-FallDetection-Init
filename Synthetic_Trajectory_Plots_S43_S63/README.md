# S43 and S63 synthetic-trajectory plots

This standalone utility reads the 100 saved `.npy` trajectories from the
completed S43 and S63 pole-PINN runs and creates line plots without copying or
modifying either dataset.

## Expected layout

Place this plotting directory beside the two subject project directories:

```text
parent_directory/
├── S43_Pole_PINN_Human_Motion/
├── S63_Pole_PINN_Human_Motion/
└── Synthetic_Trajectory_Plots_S43_S63/
```

The default input paths are:

```text
S43_Pole_PINN_Human_Motion/results/full_run/synthetic_subjectB_PINN/
S63_Pole_PINN_Human_Motion/results/full_run/synthetic_subjectB_PINN/
```

Each directory must contain exactly 100 files named `synth_B_*.npy`.

## Data interpretation

Every `.npy` file is expected to have four columns:

| Column | Quantity | Unit used in file |
|---:|---|---|
| 0 | Time | seconds |
| 1 | Pole angle | radians |
| 2 | Pole angle | degrees |
| 3 | Horizontal position | metres |

The script plots column 2 in degrees and converts column 3 from metres to
centimetres.

## Run

From the plotting directory:

```bash
python3 -m pip install -r requirements.txt
python3 plot_synthetic_trajectories.py
```

If the subject directories are elsewhere, provide their synthetic-data folders:

```bash
python3 plot_synthetic_trajectories.py \
  --s43-dir /path/to/S43_Pole_PINN_Human_Motion/results/full_run/synthetic_subjectB_PINN \
  --s63-dir /path/to/S63_Pole_PINN_Human_Motion/results/full_run/synthetic_subjectB_PINN
```

## Outputs

The `plots/` directory receives:

- `S43_100_synthetic_trajectories.png`
- `S63_100_synthetic_trajectories.png`
- `S43_vs_S63_100_synthetic_trajectories.png`
- `trajectory_plot_summary.csv`

Each panel shows all 100 trajectories as translucent colored lines and their
pointwise mean as a solid black line. The comparison figure uses shared vertical
scales within each variable so that visual differences between subjects are not
caused by independent axis scaling.

## Validation performed by the script

Before plotting, the script checks that:

- exactly 100 `.npy` files exist for each subject;
- every array is two-dimensional with four columns;
- values are finite;
- time is strictly increasing;
- the radian and degree columns agree; and
- all trajectories for a subject use the same time grid.
