# S06 activity-08 audit

Five-trial exploratory data audit, 21 September 2026.

Open S06A08_All_Trials_Audit.html for the findings, plots and team questions.
Raw data are unchanged and credited to the SmartFall Group, Texas State University.
See provenance.json for repository commit and byte-level identities.

## Reproduce

Requires Python 3, NumPy and Matplotlib. Run:

```bash
python audit.py
python make_report.py
```

The scripts use relative paths and perform no network operations.
Results include CSV/JSON summary, per-segment statistics, jump event indices,
per-frame diagnostics, duplicate comparisons, candidate intervals and PNG plots.

## Interpretation

Units, joint names and time estimates assume standard Azure Kinect exports
and nominal 30 FPS. Thresholds are exploratory, not validated error/fall labels.
No filtering, correction, CoM, BoS, force estimation or model training was performed.
All five trials have been quality-inspected and are exploratory data.
