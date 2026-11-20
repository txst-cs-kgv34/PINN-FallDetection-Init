# Fifteen-subject unified A10–A13 and A14 rotation physics DeepONet

This folder contains two coordinated five-seed experiments:

1. one unified multi-subject DeepONet for **A10 backfall, A11 frontfall, A12 leftfall, and A13 rightfall**; and
2. one separate A14 rotate-fall DeepONet with the same CartPole residual plus a yaw-rotation residual.

The delayed CartPole equations, fixed constants, four-window 0.40-s context, hard initial-condition construction, Fourier trunk, optimizer, grouped five-fold subject protocol, and five optimization seeds are preserved from `Fifteen_Subject_DeepONet_ModelB_Direct_Unified_Physics_Full_Fall_5_Seeds`.

## Data placement

Place this folder at the repository root beside the 15 updated audit folders:

```text
PINN-FallDetection-Init/
├── data/processed/Fifteen_Subject_Real_Fall_Physics_Ready/
├── S30_PINN_audit/ ... S63_PINN_audit/
└── Fifteen_Subject_DeepONet_A10_A13_Unified_A14_Rotation_Physics_5_Seeds/
```

The strict primary subsets are used in both the physics and no-physics conditions:

| Model | Activities | Trials |
|:--|:--|--:|
| Unified planar | A10, A11, A12, A13 | 257 |
| Rotation | A14 | 49 |

The planar counts are A10=58, A11=64, A12=68, and A13=67. Thus frontfall is included explicitly.

## Coordinates and phases

For every trial, the adapter reconstructs the sex-specific segment-mass CoM from the repaired/raw skeleton, builds a fixed standing anatomical frame, and uses the foot midpoint at marked fall onset as the fixed pivot. Horizontal displacement is projected onto the observed onset-to-contact direction, removing camera X/Z orientation.

```text
theta = atan2(direction-aligned horizontal CoM, subject-vertical CoM)
x     = direction-aligned CoM relative to the onset foot pivot
```

For A14, yaw is estimated from the combined shoulder/hip lateral axis in the same fixed body frame. CartPole physics is applied to theta/x; the additional residual constrains yaw acceleration under learned delayed yaw gains.

Physics uses all valid pre-contact samples except repaired samples and the final 0.03 s at the impact boundary. Forecast data loss starts after the 0.40-s context.

## Preserved Model B settings

- Seeds: `20261101` through `20261105`.
- Five subject-grouped folds; three unseen test subjects per fold and one separate validation subject.
- Context encoder: `Conv1d → Conv1d → adaptive pooling → 96`.
- DeepONet latent width 96; Fourier trunk with 12 modes.
- Hard initial conditions: `q(t)=q0+qdot0*t+t²*f(t)`.
- AdamW, learning rate `5e-4`, weight decay `1e-6`, batch size 4.
- Maximum 800 epochs, patience 100, gradient clipping 5.
- CartPole loss weight `0.01`.
- Model B physics constants: `m=0.0138`, `m0=1`, `l=0.57`, `g=9.81`, `tau=0.23`, `Pi=0.0635`.

Activity one-hot conditioning, continuous subject demographics, and per-trial fall direction are added to the branch/controller conditioning. Subject ID is not an input.

## Run on MacBook MPS

The scripts reuse your home environment at `~/.venv` unless `PINN_VENV_DIR` is set.

```bash
cd Fifteen_Subject_DeepONet_A10_A13_Unified_A14_Rotation_Physics_5_Seeds
chmod +x run.sh run_on_mac.sh
./run.sh setup
./run.sh validate
./run.sh test
./run.sh smoke mps
```

Run the full paired physics experiment:

```bash
./run.sh full mps
```

That trains 50 models: two model groups × five folds × five seeds. Runs resume by skipping completed fold summaries. Use `FORCE=1` to intentionally rerun a completed fold.

Smaller commands:

```bash
./run.sh planar mps
./run.sh rotation mps
./run.sh seed planar 1 mps
./run.sh fold rotation 2 mps 3
./run.sh status
```

After the matching baseline finishes, run the comparison command from the no-physics folder.
