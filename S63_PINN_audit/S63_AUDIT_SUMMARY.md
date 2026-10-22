# S63 audit summary and provisional trial assessment

## Decision

Manual phase marking is complete for all five A11 front-fall trials. The returned notes contain the five requested observations for T01-T05 and passed frame/time/range checks. The pole-transfer project may therefore proceed with all five manually marked trials; no automated audit flag is being used as an exclusion rule.

## Dataset inventory

| Activity | Description | Trials | Frames | Clip-span range |
|:---|:---|---:|---:|:---|
| A10 | Backfall | 5/5 | 692 | 3.27–5.70 s |
| A11 | Frontfall | 5/5 | 776 | 4.33–6.13 s |
| A12 | Leftfall | 5/5 | 780 | 4.17–6.27 s |
| A13 | Rightfall | 5/5 | 842 | 3.97–8.40 s |
| A14 | Rotatefall | 5/5 | 807 | 4.80–6.40 s |
| **Total** |  | **25/25** | **3,897** | **3.27–8.40 s** |

All 25 recordings contain finite numeric data with 96 columns. There are no empty, missing, or invalid files and no exact cross-trial duplicate frames.

## Data-quality findings

- The audit marked 318 destination frames (8.16% of all frames) for review because at least one joint moved more than 0.2 m between adjacent nominal frames or the median limb scale changed by more than 3%. These thresholds are screening heuristics copied from S43, not physiological limits.
- There are 90 exact duplicate rows (2.31% of frames). The longest constant-pose span is only 0.167 s, so S63 does not contain an S43A10T01-style frozen recording.
- A12 has the clearest tracking-scale concern. `S63A12T05` has a 51.02% limb-scale range and 48 flagged frames; `S63A12T04` has a 33.89% scale range.
- `S63A13T01` is much longer than the other right-fall clips (8.40 s) and has a 27.84% limb-scale range, so it should be checked before any future A13 model.
- `S63A10T02` begins at a head-to-ankle angle of about 79.4° and the static evidence shows an already horizontal pose. It does not provide a complete standing-to-fall sequence and should be excluded from a full-fall A10 model.
- The A14 trials are comparatively consistent by the audit metrics: each has an 8.81–11.07% scale range and 3–11 flagged frames.

## A11 front-fall assessment

| Provisional priority | Trial | Frames | Span (s) | Flagged frames | Flagged (%) | Exact duplicate rows | Limb-scale range (%) | Max filtered-vs-raw CoM change | Interpretation |
|---:|:---|---:|---:|---:|---:|---:|---:|---:|:---|
| 1 | S63A11T04 | 185 | 6.13 | 13 | 7.03 | 1 | 11.55 | 4.27 cm | Best initial candidate: longest coverage, lowest flag rate, minimal repeats, and lowest scale variation. |
| 2 | S63A11T03 | 158 | 5.23 | 12 | 7.59 | 12 | 11.81 | 4.14 cm | Strong geometry and low flag count; review the short repeated-coordinate runs. |
| 3 | S63A11T02 | 158 | 5.23 | 18 | 11.39 | 1 | 13.64 | 5.09 cm | Complete fall and low repeats; moderate number of joint-step flags. |
| 4 | S63A11T05 | 144 | 4.77 | 17 | 11.81 | 3 | 18.76 | 5.47 cm | Complete fall, but higher scale variation warrants careful raw/overlay review. |
| 5 | S63A11T01 | 131 | 4.33 | 17 | 12.98 | 5 | 19.36 | 5.20 cm | Complete fall but shortest clip, highest A11 flag rate, and highest A11 scale variation. |

This order is a review priority, not a final training eligibility decision. The static four-frame evidence indicates that all five A11 trials begin upright and end fallen. Manual playback is still required to confirm phase continuity, onset visibility, apparent contact, and post-fall coverage.

## How to use the inspection viewer

Open `inspections/S63_A11_frontfall/INSPECT.html`. It is self-contained and works offline. It provides:

- raw, filtered, and overlay skeleton playback;
- X/−Y, X/Z, and Z/−Y projections;
- frame-by-frame stepping and slow playback;
- navigation to the next audit flag;
- foot-separation and CoM-relative-to-foot-midpoint traces;
- manual labels for initial standing, fall onset, descent, apparent contact, and post-fall movement; and
- JSON export of the marked frames.

Raw is the authoritative view. The optional 1.5 Hz forward-backward Butterworth trace shows sensitivity to smoothing and must not be interpreted as a correction or as the required preprocessing for the pole pipeline.

## Phase-note handoff

The exported notes are stored at `analysis_inputs/S63_A11_phase_notes.json`. They cover T01-T05. The separate `S63_Pole_PINN_Human_Motion` project copies this file, uses S63's male anthropometric model and demographics, preserves the S43 pole-pipeline architecture, and keeps later Stage-3 gain-sweep experiments out of scope.
