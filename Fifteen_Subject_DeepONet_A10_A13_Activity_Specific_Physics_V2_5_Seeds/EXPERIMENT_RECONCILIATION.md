# Experiment rationale and reporting boundary

This V2 experiment answers a new question: whether one unified A10-A13
DeepONet benefits from a globally calibrated CartPole constraint when each
activity has a future-free anatomical axis and its own controller head.

It is not an exact replication of either the earlier favorable 70-trial A11
Model B pipeline or the completed 64-trial strict-primary A11 V3 calibration.
Those results remain valid for their respective data and preprocessing
pipelines.

The controlled comparison here is internal to V2. All lambda arms start from
the same model state and use the same training protocol. Lambda is chosen using
two validation subjects and a subject-activity-balanced endpoint; held-out test
subjects are accessed only after selection.

Recommended reporting language after seed 1:

> Seed 1 is a prespecified screening pilot for the activity-specific A10-A13
> architecture. Its matched lambda=0 arm controls initialization and training
> schedule. We will decide whether to run the remaining four seeds after
> checking forecast endpoints, activity consistency, and residual behavior.

