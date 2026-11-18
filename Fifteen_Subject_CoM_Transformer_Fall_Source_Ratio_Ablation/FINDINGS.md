# Findings: Fall-Source Ratio Ablation

## Status

Awaiting the completed 40:60 and 60:40 training results.

## Controlled question

With the detector, folds, seeds, real ADL data, real/synthetic fall pools,
training budget, and validation procedure fixed, does changing the fall-source
composition from 50:50 to 40:60 or 60:40 change real held-out fall-detection
performance?

## Planned interpretation

The analysis will compare:

- 40:60 versus the frozen 50:50 baseline;
- 60:40 versus the frozen 50:50 baseline;
- 40:60 versus 60:40;
- each new ratio versus the frozen real-only detector;
- all six scenarios descriptively.

The primary metric is test-trial balanced accuracy. Sensitivity, specificity,
F1, AUROC, AUPRC, and false-positive events per ADL minute are supporting
metrics. Seeds are averaged within each fold before paired fold-level testing.

Because these ratios were proposed after the existing test results were
inspected, this is an exploratory post-hoc ablation. The result may guide a
future validation-selected ratio, but it should not be presented as an
independent confirmatory test of the optimal ratio.
