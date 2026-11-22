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

Seed-1 outcome and reporting language:

> Seed 1 was a prespecified screening pilot for the activity-specific A10-A13
> architecture. The selected physics condition was near neutral overall: it
> improved theta and CoM-x RMSE slightly but worsened normalized forecast MSE.
> A10 and A11 improved descriptively, A12 was mixed, and A13 worsened. The
> implementation and pairing audits passed, so we will complete the remaining
> four seeds without changing the protocol before making a model-selection
> claim.

This result does not contradict the earlier favorable 70-trial A11 Model B
finding or the later strict-primary A11 V3 result. It evaluates a different
multi-activity architecture, future-free activity axes, four controller heads,
and a two-validation-subject selection rule. Claims must remain tied to the
specific pipeline and predefined endpoints.

