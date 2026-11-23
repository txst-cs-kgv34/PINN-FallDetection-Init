# Findings: A10-A14 physics synthetic-fall generation and GATE

## Decision

The generated data are suitable for the next detector-augmentation experiment
when, and only when, samples are read from
`final_approved_synthetic_manifest.json`. The accepted pool is large enough for
the planned 60:40 and 40:60 real-to-synthetic fall mixtures. Rejected candidate
files remain audit artifacts and must never enter detector training.

## Main result

- Generated candidates: **2,044**
- GATE-approved trajectories: **1,380 (67.5%)**
- Strict real source trials represented among candidates: **306**
- Strict real source trials with at least one approved variant: **249 (81.4%)**
- Source subjects represented after GATE: **15/15**
- Exact duplicate trajectories: **0**

| Activity | Strict source trials | Sources represented after GATE | Approved variants | Approval rate |
|:--|--:|--:|--:|--:|
| A10 | 58 | 44 | 209 | 55.0% |
| A11 | 64 | 54 | 284 | 67.3% |
| A12 | 68 | 58 | 338 | 75.1% |
| A13 | 67 | 49 | 290 | 64.7% |
| A14 | 49 | 44 | 259 | 75.3% |

## What limited acceptance

The principal filter was kinematic consistency, not the physics residual.

| Gate | Candidate failures |
|:--|--:|
| Kinematic | 457 |
| Continuity | 160 |
| Shape | 111 |
| Direction | 69 |
| Physics residual | 56 |
| Exact duplicate | 0 |

There were 327 kinematic-only failures. A10 had the lowest overall approval
(55.0%) and kinematic pass rate (61.8%), while its physics pass rate remained
97.1%. Therefore the A10 result is not evidence that direct CartPole physics
failed; it shows that many forecasts fell outside the real training envelope
for displacement, peak velocity, or peak acceleration.

## Generator interpretation

Validation rank did not always predict GATE acceptance. That is expected:
validation forecast MSE selects accurate checkpoints, while GATE tests a
different question—whether each generated trajectory remains inside empirical
quality envelopes. Both selected ranks are retained, and only their accepted
individual trajectories are eligible downstream.

The selected checkpoints remain valid. A14 does not need to be retrained for
this detector study: it achieved 259 approved trajectories and the strongest
activity-level approval rate (75.3%, narrowly above A12).

## Coverage caveats

Every subject has approved data overall, but **S56-A11** and **S57-A13** have no
approved synthetic variant. Detector sampling must therefore enforce the
real-to-synthetic ratio over the training fall pool (preferably activity
stratified), not independently within every subject/activity cell.

Accepted variants are not independent real events. A represented source trial
has between one and eight approved variants (median six). A training sampler
must first select a source-trial family and then select one of its variants;
otherwise real trials with eight accepted variants would be over-weighted.

## Leakage controls for the detector study

1. Split subjects before any windowing or augmentation.
2. A synthetic trajectory inherits `source_subject` as `split_group`.
3. Synthetic samples are training-only; validation and test use real data only.
4. Fit normalization on the training partition only.
5. Enforce 60:40 or 40:60 within the fall portion of each training batch; class
   balance between fall and ADL is a separate decision.
6. Sample synthetic source families before generator variants.
7. Report detector performance on unseen real subjects, with per-activity
   sensitivity in addition to pooled metrics.

Passing GATE establishes consistency with the real training-data envelope. It
does not by itself prove that synthetic augmentation improves fall detection;
that claim requires the subject-disjoint downstream comparison.
