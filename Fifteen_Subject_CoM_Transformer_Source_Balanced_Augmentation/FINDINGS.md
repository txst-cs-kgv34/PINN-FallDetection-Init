# Source-Balanced Augmentation Findings

## Experiment status

The code is ready, but the 25 full training runs have not yet been executed in this
copy. Populate this document after running `./run.sh all --device <device>` and
sharing the resulting output package.

## Question being tested

The original combined scenario sampled uniformly from a positive pool containing
many more approved synthetic falls than real falls. This experiment changes only
the training-batch composition. Every batch contains equal numbers of real and
synthetic falls while retaining a 1:1 ADL-to-fall class balance.

The primary question is whether source-balanced augmentation improves held-out-real
subject performance compared with:

1. real falls + real ADL;
2. synthetic falls + real ADL;
3. the original combined real/synthetic fall pool + real ADL.

## Interpretation rule

The result should be judged from all five held-out subject folds, not from the best
seed or a single fold. Primary attention should go to balanced accuracy,
sensitivity, specificity, F1, and false-positive events per ADL minute. The paired
fold differences and Holm-adjusted Wilcoxon tests are supporting evidence; with
only five fold-level pairs, effect size and consistency across folds are also
important.
