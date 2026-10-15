# S43 revised Stage 2 report

## Gradient-based inverse controller identification

**Subject:** S43, adult female, 58.967 kg, 1.6256 m  
**Activities:** A11 front fall and A13 right/lateral fall  
**Status:** Software and synthetic recovery checks pass; the real-data controller-identification gate fails.

## Why Stage 2 was revised

The superseded Stage-2 implementation froze Stage 1 but fitted controller parameters with bounded nonlinear least squares after sampling the frozen outputs. It also used the learned Stage-1 effective torque as a fitting target, profiled delay on a discrete frame grid, fitted a torque limit, and included a smooth nuisance-torque sensitivity branch. That branch is excluded from this cleaned codebase.

The advisor-requested revision follows the pole-balancing pattern more directly:

1. Load the exact retained Stage-1 fold/seed checkpoint.
2. Freeze every Stage-1 weight.
3. Make only `Kp`, `Kd`, `Ki`, and continuous response delay trainable.
4. Query the frozen Stage-1 trajectory at both `t` and `t-delay`.
5. Obtain angle, angular velocity, and angular acceleration by automatic differentiation.
6. Substitute the delayed PID torque into the governing equation.
7. Backpropagate the physics-residual loss only into the four controller variables.

The revision does **not** use nuisance torque, effective-torque matching, torque saturation, or Stage-1 retraining.

## Revised equation and loss

The controller is

\[
\tau_{control}(t)=
-K_p\theta_\phi(t-\Delta)
-K_d\dot\theta_\phi(t-\Delta)
-K_i\int_0^t\theta_\phi(s)\,ds,
\]

where \(\theta_\phi\) is the frozen Stage-1 trajectory. The governing residual is

\[
r(t)=I\ddot\theta_\phi(t)-mgl\sin\theta_\phi(t)
+b\dot\theta_\phi(t)-\tau_{control}(t).
\]

The primary assumption is

\[
\tau_{perturbation}(t)=0,
\]

because the recordings contain no measured perturbation input. The loss is the mean squared normalized residual across all training trials:

\[
L_{Stage2}=\frac{1}{N}\sum_j
\left(\frac{r(t_j)}{mgl}\right)^2.
\]

The subject-scaled parameters are

\[
K_p=\alpha mgl,\qquad
K_d=\beta\sqrt{I\,mgl},\qquad
K_i=\kappa\frac{mgl}{1\;s}.
\]

All four quantities are optimized by Adam followed by gradient-supplied L-BFGS. Three initializations are retained for each fold/seed. Delay is continuous and constrained to 0.0333--0.2000 s.

## Data separation and retained Stage 1

- Four whole-trial leave-one-out folds per activity
- Two independently trained Stage-1 seeds per fold
- Three complete trials used for controller identification
- One complete trial held out for forward simulation
- 16 frozen Stage-1 checkpoints
- 48 gradient-optimizer profiles
- 488 held-out prediction rows
- Eight held-out CoM figures

All 16 retained frozen Stage-1 checkpoints are present, have nonempty state dictionaries, and match the activity/trial/seed keys used by revised Stage 2. No held-out trial name appears in its corresponding Stage-1 or controller-training set. The frozen Stage-1 and constant-velocity control metrics are finite.

## Synthetic recovery validation

A zero-perturbation delayed-PID fixture with four different initial states was generated using known parameters. The revised gradient method obtained:

| Parameter | True | Estimated | Error |
|---|---:|---:|---:|
| \(\alpha\) for \(K_p\) | 1.400000 | 1.404851 | 0.347% |
| \(\beta\) for \(K_d\) | 0.450000 | 0.412325 | 8.372% |
| \(\kappa\) for \(K_i\) | 0.120000 | 0.121546 | 1.288% |
| \(\Delta\) | 0.100000 s | 0.091807 s | 8.193 ms |

The synthetic gate passes: all gain errors are below 10%, and delay error is below one 30-Hz frame. This establishes that the gradient implementation can recover a known controller in a correctly specified zero-perturbation simulation.

## Held-out real-data results

Values below are means over four held-out trials and two frozen Stage-1 seeds.

| Activity | Gradient PID | Frozen Stage 1 | Constant velocity |
|---|---:|---:|---:|
| A11 | 0.2767 m | **0.2520 m** | 0.4028 m |
| A13 | 0.3981 m | 0.4467 m | **0.3791 m** |

The gradient controller improves over constant velocity for A11 but is worse than the frozen Stage-1 trajectory. For A13, it improves over frozen Stage 1 but remains worse than constant velocity. Therefore, neither activity passes the requirement that the identified controller beat both controls.

## Trial-level results and effective parameters

Values are means over the two Stage-1 seeds.

| Held-out trial | \(\alpha\) | \(\beta\) | \(\kappa\) | Delay | XY RMSE |
|---|---:|---:|---:|---:|---:|
| A11 T02 | 1.0201 | 0.0000 | 0.0000 | 0.2000 s | 0.2623 m |
| A11 T03 | 0.9839 | 0.0000 | 0.0630 | 0.2000 s | 0.2366 m |
| A11 T04 | 1.0009 | 0.1466 | 0.0000 | 0.2000 s | 0.2520 m |
| A11 T05 | 0.8882 | 0.2790 | 0.0000 | 0.2000 s | 0.3557 m |
| A13 T01 | 0.8799 | 0.4063 | 0.0436 | 0.2000 s | 0.3219 m |
| A13 T02 | 0.0000 | 0.5522 | 1.5272 | 0.2000 s | 0.7459 m |
| A13 T03 | 0.8559 | 0.4056 | 0.0665 | 0.2000 s | 0.2237 m |
| A13 T05 | 0.8797 | 0.3545 | 0.0193 | 0.2000 s | 0.3008 m |

All 16 fold/seed fits place delay at the 0.2000-s upper bound. This is not a validated estimate of a 200-ms physiological delay. It means the physics residual continued to prefer a longer delay over the permitted interval.

The integral term is close to zero for most folds but becomes very large for the failed A13 T02 fold. Consequently, \(K_i\) is not consistent across held-out trials. A13 T02 remains a structural generalization failure rather than evidence for strong integral control.

## Validation decision

| Gate | Decision |
|---|---|
| Exact frozen Stage-1 checkpoint reproduction | Pass |
| Whole-trial leakage check | Pass |
| Finite gradients and optimizer outputs | Pass |
| Synthetic known-parameter recovery | Pass |
| Finite held-out forward simulation | Pass, 16/16 |
| Delay identified away from bounds | **Fail, 0/16** |
| Beats both held-out controls for A11 | **Fail** |
| Beats both held-out controls for A13 | **Fail** |
| Consistent PID parameters across trials | **Fail** |

The implementation follows the requested frozen-network gradient design, but the present real data do not support a validated controller phenotype.

## Fixed-delay profile diagnostic

The recommended diagnostic was completed over 11 predeclared delays from 0.05 to 0.30 s. At each delay, only \(K_p,K_d,K_i\) were re-optimized using exact gradients with bounded L-BFGS-B. Every candidate used the same frozen Stage-1 collocation times at or after 0.30 s, so differences in loss do not arise from scoring different time windows.

The synthetic known-delay control selected its exact true delay of 0.100 s. For the S43 data:

- 0 of 16 fold/seed profiles had an interior minimum.
- 16 of 16 profiles selected the 0.300-s upper boundary.
- 16 of 16 profiles were monotonically non-increasing.
- Loss decreased by 34.2--57.9% from 0.05 to 0.30 s.

This confirms that the earlier 0.200-s boundary was not a recovered optimum. Delay is not identifiable from these trajectories under the zero-perturbation, fixed-link model. The fitted gains also change substantially as delay changes, so the gain estimates inherit this uncertainty. Extending the delay bound again would only move the reported boundary and is not recommended.

## Recommended immediate next step

Present the fixed-delay result as the Stage-2 conclusion and obtain advisor approval to treat Stage 3 as an assumption-based virtual sensitivity study. Do not select 0.300 s as the subject's response delay. Carry the complete fixed-delay controller ensemble into Stage 3A so uncertainty in delay and gains remains visible.

## How Stage 3 may proceed

The framework's fully validated Stage 3 would require a Stage-2 controller that generalizes to unseen controlled perturbations. That gate is not passed, and no force/contact collection is available. Stage 3 can nevertheless proceed as **Stage 3A: assumption-based virtual perturbation sensitivity**, not subject-specific physiological recovery prediction.

The recommended design is:

1. Retain all 88 activity-specific controllers per activity: four folds, two seeds and 11 fixed delays. Do not average them or choose the 0.300-s boundary fit.
2. Use the same fixed-length, fixed-pivot, \(b=0\), unsaturated plant for the primary analysis.
3. Define 50 prescribed perturbation scenarios per activity: five dimensionless amplitudes, five durations and two directions. Scale each pulse as \(\tau_p=\gamma mgl\), making the assumed strength transparent and subject-scaled.
4. Cycle the initial \(\theta_0,\dot\theta_0,l\) values through the four observed activity-specific onset states. The total is 100 unique A11/A13 scenarios and 8,800 ensemble simulations.
5. Apply a rectangular torque pulse at a predeclared onset. This is a known hypothetical input, not a reconstructed force or nuisance function.
6. Stop simulations at a predeclared mathematical angle threshold because the fixed-pivot model is invalid after ground contact or stepping.
7. Report peak angle, peak horizontal CoM excursion, mathematical stabilization time, integrated control effort, threshold crossing and divergence.
8. Report median and 5th--95th percentile outcomes across the 88 controllers for each scenario. The width of that interval is the model/identification uncertainty.
9. Include uncontrolled-pendulum and zero-perturbation simulations as numerical controls.
10. Call the result a **model recovery envelope under assumed perturbations**. It is not a clinical fall boundary, measured perturbation response or physiological controller validation.

This approach is scientifically usable for sensitivity questions such as “under this model, which assumed perturbation combinations cause the simulated state to leave a defined region?” It cannot answer “what external force caused this recorded fall?” or “what perturbation can this person physiologically recover from?” See `S43_STAGE3A_ASSUMPTION_BASED_PLAN.md` for the full executable specification.
