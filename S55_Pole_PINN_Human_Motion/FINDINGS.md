# Findings: S55 pre-run preparation

## Current status

The S55 pole-PINN project is prepared and validated through input construction. The full four-stage training run and the Stage-3 gain sweep have not yet been executed.

## Subject and trial scope

- Subject: S55
- Sex: male
- Weight: 145 lb
- Height: 5 ft 5 in
- Activity: A11 front fall
- Included trials: T01–T05
- Excluded trials: none
- Manual phases: complete and ordered for every included trial

## Subject isolation

The project contains exactly five raw skeleton files: `S55A11T01.csv` through `S55A11T05.csv`. No S57, S62, S63, or other-subject motion file is present.

Three independent checks guard against cross-subject contamination:

1. `tests/validate_project.py` requires the raw inventory to equal the five declared S55 filenames.
2. The adapter requires the generated `SubjectB_*.tsv` inventory to equal the files declared in `config/S55_A11_experiment_scope.json`.
3. Both the full-run launcher and gain-sweep launcher stop if the actual TSV inventory differs from that same S55-only list. The gain sweep additionally checks that the saved full-run metadata records the exact validated input list.

## Data provenance and missing values

The raw project inputs were copied from the repaired layer of `S55_PINN_audit`. The individual A11 repair manifests report zero repaired rows and no gaps for all five trials. Therefore, the S55 front-fall model uses complete observed A11 rows; no A11 coordinate was forward-filled or linearly interpolated.

## Adapter validation

The adapter successfully generated five pole-compatible inputs. The preserved loader's pre-20° rule leaves:

| Trial | Usable samples | Usable duration |
|---|---:|---:|
| S55A11T01 | 147 | 1.46 s |
| S55A11T02 | 54 | 0.53 s |
| S55A11T03 | 136 | 1.35 s |
| S55A11T04 | 134 | 1.33 s |
| S55A11T05 | 153 | 1.52 s |

The 0.50-second eligibility gate retains every manually accepted trial without padding. T02 is substantially shorter than the other trials and should be reported when interpreting pooled metrics or the common support used by distribution comparisons.

## Architecture check

The core pole-PINN source hash is:

```text
604985d2344350789929c3554f9ce4351b826f69be1dfe9dee0b20acb586e0a9
```

It matches the locked reference. The full-run settings remain 7,000 Stage-1 epochs, 5,000 Stage-2 epochs, 5,000 Stage-3 epochs, and 100 generated trajectories.

## Pending results

After the full run, this file should be updated with:

- identified `Kp_theta`, `Kd_theta`, `Kp_x`, `Kd_x`, `Pi`, and fixed `tau`;
- Stage-1 and Stage-3 reconstruction metrics;
- the 100-trajectory validity and distribution analysis; and
- full 11-chunk gain-sweep rankings and trial-level sensitivity.
