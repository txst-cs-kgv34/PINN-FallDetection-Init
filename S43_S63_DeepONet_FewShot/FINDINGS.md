# Findings: physics-informed conditional DeepONet with few-shot gain inference

## Executive conclusion

The full pooled experiment is a strong **known-anchor, new-initial-condition**
proof of concept. With four context windows, the unified model reduces
normalized gain RMSE by 95.6%, theta forecast RMSE by 50.0%, and x forecast
RMSE by 90.5% relative to the training-mean-gain baseline. Its mean prediction
for every gain is within approximately 1.1% of the corresponding teacher gain.

The teacher-holdout experiments answer a harder question and are negative for
gain generalization. When one complete teacher/gain anchor is removed, the
context encoder generally selects or averages gains it has already seen rather
than reconstructing the missing anchor. Increasing the context from one to
four windows does not resolve this. The current system therefore learns the
three observed regimes well, but it has not learned a continuously
generalizable map from motion windows to unseen control gains.

## Experimental inventory

| Experiment | Training teachers | Test data | Split sizes (train/validation/test) | What it tests |
|---|---|---|---:|---|
| Full pooled | S43 chunk 1, S63 chunk 1, S63 chunk 6 | 15 unseen initial conditions per teacher | 210 / 45 / 45 | Known gains, new initial conditions |
| Hold out S43 chunk 1 | S63 chunks 1 and 6 | All 100 S43 chunk 1 trajectories | 170 / 30 / 100 | Missing gain anchor and closest available subject holdout |
| Hold out S63 chunk 1 | S43 chunk 1 and S63 chunk 6 | All 100 S63 chunk 1 trajectories | 170 / 30 / 100 | Missing S63 gain anchor |
| Hold out S63 chunk 6 | S43 chunk 1 and S63 chunk 1 | All 100 S63 chunk 6 trajectories | 170 / 30 / 100 | Missing high-gain S63 anchor |

All experiments use 3-second, 100 Hz synthetic teacher trajectories generated
from 100 matched initial conditions. Context windows come from the first second;
forecast errors are evaluated after the context region.

In the teacher-holdout runs, the omitted teacher contributes no training or
validation trajectories. However, the two retained teachers use the same
matched initial-condition bank, so counterparts of the held-out initial states
can occur in training. The holdout therefore tests transfer to an unseen
teacher/gain anchor under a familiar initial-condition distribution.

## Experiment A: full pooled model

### Aggregate few-shot results

Each row aggregates 45 held-out trajectories: 15 from each teacher.

| Windows | Gain RMSE | Gain baseline | Improvement | Theta RMSE (deg) | Theta baseline | Improvement | x RMSE (cm) | x baseline | Improvement |
|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| 1 | 0.065565 | 0.150660 | 56.5% | 1.862 | 3.416 | 45.5% | 7.222 | 12.242 | 41.0% |
| 2 | 0.011775 | 0.150660 | 92.2% | **1.697** | 3.416 | **50.3%** | 1.506 | 12.242 | 87.7% |
| 4 | **0.006612** | 0.150660 | **95.6%** | 1.709 | 3.416 | 50.0% | **1.169** | 12.242 | **90.5%** |

The largest change occurs from one to two windows. One window frequently
confuses the two S63 controllers, whereas two and four windows identify all 45
test cases with the nearest correct gain anchor. Four windows give the best
aggregate gain and x errors, while two windows give the smallest theta error;
the theta difference between two and four windows is only 0.012 degrees.

### Four-window results by teacher

| Teacher | Gain RMSE | Theta RMSE (deg) | Oracle theta (deg) | x RMSE (cm) | Oracle x (cm) |
|---|---:|---:|---:|---:|---:|
| S43 chunk 1 | 0.009019 | 1.279 | 1.241 | 0.974 | 0.949 |
| S63 chunk 1 | **0.003695** | 1.706 | 1.697 | **1.151** | 1.121 |
| S63 chunk 6 | 0.007122 | 2.143 | 2.121 | 1.382 | 1.337 |

The few-shot forecast is close to the true-gain oracle for every known anchor.
That is the expected pattern when gain inference and the conditional forward
operator are both working within their trained support.

### Four-window mean gain estimates

Parentheses show absolute relative error.

| Teacher | `Kp_theta` true -> predicted | `Kd_theta` true -> predicted | `Kp_x` true -> predicted | `Kd_x` true -> predicted |
|---|---:|---:|---:|---:|
| S43 chunk 1 | 145.138 -> 146.270 (0.78%) | 15.035 -> 15.057 (0.15%) | 5.043 -> 5.025 (0.36%) | 15.046 -> 15.136 (0.60%) |
| S63 chunk 1 | 145.109 -> 146.128 (0.70%) | 15.049 -> 15.045 (0.02%) | 14.933 -> 14.910 (0.16%) | 15.048 -> 15.008 (0.27%) |
| S63 chunk 6 | 197.826 -> 199.954 (1.08%) | 23.355 -> 23.472 (0.50%) | 13.859 -> 13.731 (0.92%) | 23.355 -> 23.556 (0.86%) |

### Interpretation

The pooled model can represent and recognize the three controllers supplied
during training. This is meaningful evidence that the conditional DeepONet and
few-shot encoder can form one model over the existing PINN teachers. It is not
evidence of interpolation between gains, extrapolation beyond them, or
generalization to a new subject because every test gain anchor was present in
training.

## Experiment B: leave-one-teacher-out models

### All few-shot results

Values in parentheses are the corresponding training-mean-gain baseline. The
oracle is the same across window counts because it receives the true gain.

| Held-out teacher | Windows | Gain RMSE (baseline) | Theta RMSE, deg (baseline / oracle) | x RMSE, cm (baseline / oracle) |
|---|---:|---:|---:|---:|
| S43 chunk 1 | 1 | 0.267401 (0.258964) | 10.010 (10.129 / 9.428) | 37.237 (34.705 / 39.376) |
| S43 chunk 1 | 2 | 0.260309 (0.258964) | 9.857 (10.129 / 9.428) | 37.397 (34.705 / 39.376) |
| S43 chunk 1 | 4 | 0.258838 (0.258964) | 9.838 (10.129 / 9.428) | 37.340 (34.705 / 39.376) |
| S63 chunk 1 | 1 | 0.224326 (0.176425) | 2.655 (3.927 / 3.409) | 24.160 (22.605 / 21.213) |
| S63 chunk 1 | 2 | 0.223897 (0.176425) | 2.657 (3.927 / 3.409) | 24.154 (22.605 / 21.213) |
| S63 chunk 1 | 4 | 0.223938 (0.176425) | 2.659 (3.927 / 3.409) | 24.155 (22.605 / 21.213) |
| S63 chunk 6 | 1 | **0.223454** (0.242580) | 3.262 (5.215 / 6.646) | **23.609** (24.669 / 18.968) |
| S63 chunk 6 | 2 | 0.224212 (0.242580) | 3.231 (5.215 / 6.646) | 23.626 (24.669 / 18.968) |
| S63 chunk 6 | 4 | 0.224402 (0.242580) | **3.226** (5.215 / 6.646) | 23.639 (24.669 / 18.968) |

### Four-window predicted gains

| Held-out teacher | True gains `[Kp_theta, Kd_theta, Kp_x, Kd_x]` | Mean predicted gains | Relative errors |
|---|---|---|---|
| S43 chunk 1 | `[145.138, 15.035, 5.043, 15.046]` | `[161.082, 17.834, 14.518, 17.828]` | `[11.0%, 18.6%, 187.9%, 18.5%]` |
| S63 chunk 1 | `[145.109, 15.049, 14.933, 15.048]` | `[197.794, 23.343, 13.882, 23.372]` | `[36.3%, 55.1%, 7.0%, 55.3%]` |
| S63 chunk 6 | `[197.826, 23.355, 13.859, 23.355]` | `[144.858, 15.046, 14.953, 15.039]` | `[26.8%, 35.6%, 7.9%, 35.6%]` |

### Holdout-specific interpretation

#### S43 chunk 1 held out

This is the closest available new-subject test, but it also removes the only
training anchor with `Kp_x` near 5. The prediction stays near the two S63
training anchors and misses `Kp_x` by 188%. Four windows are effectively tied
with the mean-gain baseline for gain error, improve theta by only 2.9%, and
worsen x by 7.6%. The current model does not generalize to this missing anchor
or establish new-subject performance.

#### S63 chunk 1 held out

The encoder predicts almost exactly the remaining S63 chunk 6 controller,
including its high theta gains. Its four-window gain RMSE is 26.9% worse than
the mean-gain baseline, and its x forecast is 6.9% worse. Although theta RMSE
improves by 32.3%, that improvement accompanies incorrect gains and therefore
cannot be interpreted as gain recovery.

#### S63 chunk 6 held out

The encoder returns the low-gain region represented by S43 chunk 1 and S63
chunk 1. Gain RMSE is only 7.5% better than the mean baseline and remains large;
the three theta-related gains are wrong by approximately 27-36%. Theta and x
forecasts improve by 38.1% and 4.2%, respectively, but this again reflects
off-anchor behavior of the learned forward surrogate, not correct physical
parameter identification.

### Why some holdout forecasts look better with incorrect gains

In a holdout run, the forward DeepONet has never been trained on the omitted
gain/teacher regime. Supplying the true held-out gain therefore queries the
operator outside its supported gain anchors. That is why the oracle can be
worse than a prediction made with incorrect but familiar gains. The effect is
most obvious for held-out S63 chunk 6, where the true-gain oracle theta error is
6.646 degrees but the wrong low-gain prediction gives 3.226 degrees.

This result is a warning: low trajectory error from the neural surrogate does
not guarantee that the inferred gains are physically correct. Gain accuracy
must remain a primary metric, and the forward operator must be trained densely
enough across gain space for its oracle to be trustworthy.

## Training and physics diagnostics

| Run | Epochs completed | Best epoch | Best validation total | Validation data | Validation gain NLL | Validation consistency | Physics first 50 | Physics last 50 |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| Full pooled | 395 | 335 | -0.882371 | 0.006756 | -2.976431 | 0.007604 | 4.2263 | 3.7510 |
| Hold out S43 chunk 1 | 364 | 304 | -0.888706 | 0.007063 | -2.997611 | 0.007029 | 5.7256 | 5.1421 |
| Hold out S63 chunk 1 | 364 | 304 | -0.892460 | 0.005022 | -2.999804 | 0.004919 | 4.2032 | 3.4647 |
| Hold out S63 chunk 6 | 369 | 309 | -0.894565 | 0.003592 | -2.999872 | 0.003611 | 3.2347 | 2.7441 |

The mean training physics residual decreases by approximately 10-18% from the
first 50 to the last 50 epochs, showing that the term was active. This does not
yet establish that physics regularization improved reconstruction or
generalization: validation physics is not evaluated, and there is no matched
zero-physics ablation.

The negative validation totals are not negative physical errors. The total is
dominated by a Gaussian gain negative log-likelihood, which can be negative
when the learned variance is small.

## Quality checks and limitations

1. **Example-trajectory plot bug.** The archived
   `teacher_vs_operator_examples.png` files can pair the first stored target
   with the last stored prediction. CSV/JSON metrics are unaffected. The source
   has been corrected for future regeneration; do not use the existing example
   figures in a report.
2. **Uncertainty is not calibrated.** Many reported standard deviations hit
   the lower clamp implied by `log_variance = -6`: approximately 12.447 for
   `Kp_theta`, 1.494 for each Kd, and 0.996 for `Kp_x`. These are optimization
   bounds, not trustworthy confidence intervals.
3. **Only three gain anchors exist.** A four-dimensional gain-to-trajectory
   operator cannot learn interpolation or extrapolation reliably from three
   points.
4. **Only two subjects exist.** S43 holdout is one test subject and is
   confounded with the unique low-`Kp_x` anchor.
5. **Teacher outputs are synthetic.** They measure agreement with the existing
   PINN teachers, not direct validity against measured human motion.
6. **One training seed was used.** Variation across random initialization is
   unknown.

## Defensible statement for a report

> A single conditional DeepONet represented the three supplied PINN teacher
> regimes and, when those gain anchors were included in training, recovered
> their control gains from four motion windows with no more than approximately
> 1.1% mean relative error per parameter. However, leave-one-teacher-out tests
> showed that the few-shot encoder reverted to known gain anchors rather than
> recovering an omitted controller. The current result supports unified
> modeling and few-shot identification of known regimes, but not generalization
> to unseen gains or subjects.

## Recommended next steps

1. **Increase gain-anchor coverage first.** Export teacher trajectories from
   all usable gain-sweep checkpoints for both subjects, ideally all 10 chunks
   per subject rather than only three selected models. Keep the exact checkpoint
   and gain provenance for every anchor.
2. **Evaluate by held-out gain anchor.** Split entire gain anchors, not
   trajectories, into training/validation/test. Label interpolation tests
   separately from extrapolation tests. Require gain error to beat the
   training-mean baseline and to improve as context windows increase.
3. **Regenerate the example plots.** The plotting bookkeeping fix is already
   in `train_operator.py`. Add an evaluation-only option so local model files
   and teacher arrays can recreate plots without retraining.
4. **Run a physics ablation.** Compare otherwise identical models with physics
   weight 0 and 0.01 across at least three seeds. Report reconstruction, gain,
   forward-oracle, and physics residual metrics on validation and test sets.
5. **Calibrate uncertainty.** Remove dependence on the hard variance floor,
   report empirical interval coverage, and check whether uncertainty rises on
   held-out anchors.
6. **Add a genuinely new subject.** After gain coverage is improved, train on
   multiple subjects and reserve one complete subject for testing. A single S43
   holdout from only two source subjects is not enough for a population claim.

