# A10-A14 detector ratio comparison

Completed runs: **75/75**.

All conditions use identical folds, seeds, architecture, optimizer, real-only normalization, and real-only validation/test sets.

| Metric | Best mean condition | Mean |
|:--|:--|--:|
| test_trial_balanced_accuracy | Real only | 0.9619 |
| test_trial_sensitivity | Real only | 0.9432 |
| test_trial_specificity | Real only | 0.9805 |
| test_trial_f1 | Real only | 0.9545 |
| test_trial_auroc | Real only | 0.9870 |
| test_trial_auprc | Real only | 0.9875 |
| false_positive_events_per_adl_minute | Real only | 0.1344 |
| test_A10_sensitivity | Real 40 : Syn 60 | 0.9159 |
| test_A11_sensitivity | Real only | 0.9600 |
| test_A12_sensitivity | Real 60 : Syn 40 | 0.9302 |
| test_A13_sensitivity | Real 60 : Syn 40 | 0.9688 |
| test_A14_sensitivity | Real only | 0.9920 |

Wilcoxon tests use five seed-averaged fold pairs with Holm adjustment. Interpret effect direction and fold consistency alongside p-values.
