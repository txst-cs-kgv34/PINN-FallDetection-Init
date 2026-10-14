# S43 revised Stage 2 report

## Gradient-based inverse controller identification

**Subject:** S43, adult female, 58.967 kg, 1.6256 m  
**Activities:** A11 front fall and A13 right/lateral fall  
**Status:** Software and synthetic recovery checks pass; the real-data controller-identification gate fails.

## Why Stage 2 was revised

The earlier Stage-2 implementation froze Stage 1 but fitted controller parameters with bounded nonlinear least squares after sampling the frozen outputs. It also used the learned Stage-1 effective torque as a fitting target, profiled delay on a discrete frame grid, fitted a torque limit, and included a smooth nuisance-torque sensitivity branch.

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

The frozen Stage-1 and constant-velocity control metrics reproduce the previous verified package to a maximum difference of \(2.22\times10^{-15}\). No held-out trial name appears in its corresponding controller-training set.

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

## Recommended immediate next step

Do not tune the optimizer to force the delay away from its bound. The next useful check is a predeclared delay-bound/profile diagnostic:

1. Re-evaluate the physics loss over fixed delays from 0.05 to 0.30 s.
2. Re-optimize only \(K_p,K_d,K_i\) at each fixed delay using gradients.
3. Plot loss versus delay for every fold/seed.
4. Determine whether the loss has an interior minimum or continues decreasing with delay.
5. Present this result to the advisor before assigning physiological meaning to \(\Delta\).

If loss continues decreasing, delay is not identified by these trials under the zero-perturbation single-link model. Increasing the bound and reporting the new boundary as an estimate would not solve the problem.

## How Stage 3 may proceed

The framework's fully validated Stage 3 should wait for a Stage-2 controller that generalizes to unseen controlled perturbations. That gate is not passed here.

If an exploratory Stage 3A is still requested, it should be explicitly labeled **assumption-based virtual sensitivity**, not subject-specific physiological recovery prediction:

1. Freeze every revised Stage-2 fold/seed controller separately; do not average incompatible parameters into one controller.
2. Use the same fixed-length, fixed-pivot, \(b=0\) plant.
3. Define initial \(\theta_0\) and \(\dot\theta_0\) grids from observed S43 onset ranges.
4. Apply known synthetic torque pulses with predefined direction, amplitude, onset, duration, and waveform.
5. Forward-simulate without retraining Stage 1 or Stage 2.
6. Report peak angle, peak CoM excursion, time to a predefined mathematical stable region, integrated control effort, divergence rate, and threshold crossing.
7. Propagate uncertainty across all fold/seed controllers and across plausible delay values; report ranges rather than one recovery boundary.
8. Call the outcome a **model recovery envelope**. Do not call it physiological recovery or a clinical fall-risk measure.

The stronger alternative is to stop after the Stage-2 non-identifiability result and collect synchronized controlled perturbation and force/contact measurements before reopening Stage 2 and proceeding to a validated Stage 3.
