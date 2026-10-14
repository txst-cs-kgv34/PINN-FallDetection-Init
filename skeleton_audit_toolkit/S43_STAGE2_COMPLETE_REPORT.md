# S43 complete Stage 2 report

## Outcome

The complete computational Stage 2 is implemented and verified against the
retained Stage 1. It estimates a delayed, torque-limited PID controller after
freezing Stage 1; compares full PID with nested PD; tests zero perturbation
against a regularized nuisance-torque sensitivity; and forward-simulates every
held-out fall to produce horizontal, vertical, and 2-D CoM path comparisons.

The implementation is complete. The scientific result is that these
skeleton-only trials support, at most, an **effective parsimonious delayed-PD
description**, not a uniquely identified physiological PID controller.

## What was held fixed from Stage 1

| Item | Retained choice |
|---|---|
| Subject | S43; 58.9670081 kg; 1.6256 m |
| Activities | A11 anterior-posterior; A13 medial-lateral |
| Validation | Four whole-trial leave-one-out folds per activity; two seeds |
| Observation processing | Order-6, 1.5 Hz filter; 30 Hz |
| Plant | Fixed onset pivot and length; `I=m*l^2` |
| Passive damping | `b=0 N*m*s/rad` |
| Stage-1 architecture | trajectory 32 x 3; torque 16 x 2 |
| Stage-1 optimization | 300 epochs; learning rate 0.003; 24 collocation points |
| Stage-1 loss weights | physics 0.01; rigid length 0.001; torque L2 0.0001; torque rate 0.001 |

Stage 1 was retrained inside every fold and seed, then saved and frozen. Its
reproduced held-out errors match the retained Stage-1 results to less than
`1e-8` m. No held-out trajectory was used to train Stage 1 or fit Stage 2.

## Equations and implemented objective

The plant equation is

\[
I\ddot\theta = mgl\sin\theta + \tau_{control} +
\tau_{perturbation} - b\dot\theta .
\]

The full controller is

\[
\tau_{raw}(t)=-K_p\theta(t-\Delta)-K_d\dot\theta(t-\Delta)
-K_i\int_0^t\theta(s)\,ds,
\]

\[
\tau_{control}(t)=\operatorname{clip}(\tau_{raw},-\tau_{max},+\tau_{max}).
\]

The PID equation was **not jointly inserted into and used to retrain the
Stage-1 PINN**. This is a deliberate frozen-stage design. On each training
trial, the frozen Stage-1 PINN supplies \(\theta\), \(\dot\theta\),
\(\ddot\theta\), and learned effective torque \(\tau_{eff}\). Stage 2 minimizes
two normalized residuals:

\[
r_{torque}=\tau_{eff}-\tau_{control}-\tau_{nuisance},
\]

\[
r_{dynamics}=I\ddot\theta-mgl\sin\theta+b\dot\theta
-\tau_{control}-\tau_{nuisance}.
\]

This uses the Stage-2 controller in the Stage-1 physics equation while
preventing Stage-2 parameters from changing the Stage-1 trajectory network.
Delay is profiled over 2--6 frames. Three optimizer starts are used for each
delay. Forward validation integrates the delayed equation at 150 Hz and scores
the result at the original 30 Hz sample times.

## The two requested perturbation options

1. **Primary: zero perturbation.** `tau_perturbation=0`, because the recordings
   contain no measured external or recovery forces.
2. **Sensitivity: nuisance torque.** Three smooth raised-cosine coefficients
   are estimated from training trials only with ridge regularization. This asks
   whether conclusions change when an unmeasured smooth torque is allowed; it
   is not a recovered force measurement.

Both options are fitted as full PID and nested PD. The PD comparison tests
whether the integral term improves held-out prediction.

## Mean held-out results

| Activity | PID, zero | PD, zero | PID, nuisance | Frozen Stage 1 | Constant velocity |
|---|---:|---:|---:|---:|---:|
| A11 | 0.2408 m | **0.2406 m** | 0.2430 m | 0.2520 m | 0.4028 m |
| A13 | 0.4518 m | 0.4240 m | 0.4665 m | 0.4467 m | **0.3791 m** |

For A11, Stage 2 improves on the frozen Stage-1 trajectory mean, but full PID
does not improve on PD. For A13, PD is better than full PID, while neither
beats the simple constant-velocity control. The nuisance-torque sensitivity
worsens mean held-out error in both activities.

## Primary PID-zero fits by held-out trial

| Activity | Held-out trial | XY RMSE | Angle RMSE | alpha Kp | beta Kd | kappa Ki | Delay (frames) | gamma limit |
|---|---|---:|---:|---:|---:|---:|---:|---:|
| A11 | T02 | 0.2153 m | 10.64 deg | 0.881 | 0.000 | 0.000 | 5.5 | 0.788 |
| A11 | T03 | 0.1938 m | 8.98 deg | 0.903 | 0.000 | 0.000 | 6.0 | 0.730 |
| A11 | T04 | 0.1931 m | 10.18 deg | 0.906 | 0.000 | 0.000 | 4.5 | 0.807 |
| A11 | T05 | 0.3610 m | 23.84 deg | 0.585 | 0.262 | 0.000 | 2.0 | 0.851 |
| A13 | T01 | 0.2955 m | 17.81 deg | 0.925 | 0.193 | 0.000 | 6.0 | 0.956 |
| A13 | T02 | 1.0733 m | 73.56 deg | 0.000 | 0.438 | 1.362 | 3.0 | 0.790 |
| A13 | T03 | 0.1910 m | 11.25 deg | 0.917 | 0.184 | 0.000 | 6.0 | 0.961 |
| A13 | T05 | 0.2473 m | 14.82 deg | 1.017 | 0.001 | 0.000 | 6.0 | 0.936 |

The table reports means over the two Stage-1 seeds. Greek gain terms are
dimensionless subject-scaled values. They are more comparable than the derived
physical-unit values but are still model-dependent.

## What the results mean

- A11's integral coefficient is effectively zero in every held-out fold.
- A13's apparent nonzero mean Ki comes almost entirely from the failed T02
  generalization fold; three of four trials again estimate Ki at zero.
- The nuisance branch does not improve the activity-level held-out result.
- The selected fits frequently approach parameter lower bounds, showing weak
  practical identifiability and trade-offs among gains, delay, and saturation.
- Good trajectory agreement, where present, does not prove that fitted gains
  are physiological. Stage-2A robustness already showed that parameter bias
  can coexist with a good trajectory.

Therefore, the defensible selected model is **PD with zero perturbation**, and
only as an exploratory effective controller. The full PID result should be
reported as a negative model-complexity test: Ki did not generalize.

## Verification performed

- A separate, correctly specified synthetic fixture with active saturation
  recovered known Kp, Kd, Ki, three-frame delay, and torque limit essentially
  exactly.
- All 16 Stage-1 fold/seed checkpoints were saved and frozen.
- All reproduced Stage-1 held-out scores match the retained Stage 1.
- 64 selected controller fits and 960 delay/start profiles are finite.
- 1,952 prediction rows and eight held-out CoM figures were generated.
- Whole-trial leakage checks pass.

## Recommended thesis conclusion and workaround

Stage 2 is complete as a computational and held-out sensitivity study. It does
not justify a physiological phenotype vector containing uniquely measured Kp,
Kd, Ki, delay, torque limit, and damping. For the present skeleton-only data:

1. Report PD-zero as the parsimonious exploratory result.
2. Report full PID and nuisance torque as negative sensitivity analyses.
3. Do not interpret `b=0` as measured damping; it is the frozen Stage-1 choice.
4. Do not interpret the fitted torque limit as muscular capacity.
5. Treat the A13 T02 failure explicitly rather than averaging it away.

The only strong workaround for physiological identification is new synchronized
information: ground-reaction force and center of pressure, a known external
perturbation, or force/contact instrumentation. More optimization of the same
skeleton trajectories cannot uniquely separate feedback control from unknown
contact and perturbation torques.

## Output map

| Artifact | Purpose |
|---|---|
| `analyses/S43_stage2_full_pid/fold_metrics.csv` | Selected parameters and held-out scores |
| `analyses/S43_stage2_full_pid/control_metrics.csv` | Frozen Stage-1 and constant-velocity controls |
| `analyses/S43_stage2_full_pid/optimization_profiles.csv` | Every delay/start candidate |
| `analyses/S43_stage2_full_pid/held_out_com_predictions.csv` | Real and predicted CoM time series |
| `analyses/S43_stage2_full_pid/stage1_frozen_checkpoints.json` | Saved Stage-1 weights and histories |
| `analyses/S43_stage2_full_pid/plots/` | Eight held-out line/path figures |
| `scripts/run_stage2_full_pid.py` | End-to-end runner |
| `scripts/verify_stage2_full_pid.py` | Independent verification and regression gates |
