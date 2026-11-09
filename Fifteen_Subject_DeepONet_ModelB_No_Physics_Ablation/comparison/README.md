# Model B physics versus no-physics comparison

This directory contains a paired analysis of the completed 15-subject Model B
physics experiment and its matched no-physics ablation.

## Files

- `comparison_summary.json`: design/target verification, subject-level summary,
  bootstrap confidence intervals, paired Wilcoxon results, and win counts.
- `paired_subject_metrics.csv`: one paired row per held-out subject.
- `paired_trial_metrics.csv`: one paired row per held-out trial. These repeated
  trials are descriptive and are not treated as independent inference units.
- `training_selection_comparison.csv`: validation-selected epoch and validation
  normalized MSE for each fold and condition.
- `physics_vs_no_physics_paired_subject_means.png`: paired mean errors for all
  15 held-out subjects.
- `physics_vs_no_physics_trial_boxplots.png`: side-by-side held-out trial error
  distributions for each subject.

For every `physics_improvement_*` column, the definition is:

```text
no-physics error - physics error
```

Positive values favor physics; negative values favor no-physics. Lower raw
error is always better.

The inferential comparison uses the 15 paired subject means. The bootstrap is
deterministic (seed 20261109, 100,000 resamples), and the Wilcoxon signed-rank
test is two-sided.
