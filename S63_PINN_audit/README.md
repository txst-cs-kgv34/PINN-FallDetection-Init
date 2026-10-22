# S63 PINN audit

This directory is the pre-modeling audit for Subject 63. It checks the supplied fall recordings, preserves the original CSV bytes, computes a male segment-mass CoM proxy using the supplied demographics, creates reproducible evidence figures, and provides offline viewers for manual phase marking.

No PINN, controller, Stage 1, Stage 2, Stage 3, or synthetic-fall experiment is included here. The intended next project, `S63_Pole_PINN_Human_Motion`, should begin only after the A11 phase notes have been manually reviewed.

## Subject and recording assumptions

| Field | Value |
|:---|:---|
| Subject | S63 |
| Sex | Male |
| Weight | 180 lb = 81.6466 kg |
| Height | 5 ft 6 in = 66 in = 1.6764 m |
| Nominal sampling rate | 30 FPS |
| Input layout | 32 Azure Kinect joints × XYZ = 96 values per frame |
| Activities | A10 Backfall, A11 Frontfall, A12 Leftfall, A13 Rightfall, A14 Rotatefall |

The 30 FPS rate, millimeter coordinates, Azure Kinect joint order, and dataset limitations are inherited from the previously confirmed SmartFallMM collection metadata. They should be changed in `configs/S63.json` if the S63 export used a different path.

## Audit outcome

- All 25 expected files are present and numerically valid.
- All files have 96 columns, finite values, and at least two frames.
- The archive contains 3,897 frames in total.
- No empty trials, missing trials, invalid trials, or exact cross-trial duplicate frames were found.
- There are 90 within-clip duplicate rows and 318 exploratory review-flagged destination frames. These are inspection cues, not automatic exclusions.
- All five A11 front-fall recordings contain a visible standing-to-fallen sequence in the static evidence.
- `S63A11T04` is the strongest provisional A11 candidate. `T03` and `T02` follow. `T01` and `T05` remain usable candidates but need closer review because their limb-scale variation is higher.
- `S63A10T02` starts already close to a horizontal/fallen pose and should not be used as a complete standing-to-fall trial.

See [`S63_AUDIT_SUMMARY.md`](S63_AUDIT_SUMMARY.md) for the detailed interpretation and [`findings/S63_audit/FINDINGS.md`](findings/S63_audit/FINDINGS.md) for the generated trial-level audit tables and figures.

## Directory map

| Path | Purpose |
|:---|:---|
| `configs/S63.json` | Subject demographics, collection assumptions, activities, and screening thresholds |
| `findings/S63_audit/` | Immutable audit run, copied raw files, measurements, evidence plots, provenance, and generated findings |
| `inspections/S63_candidates/` | Offline viewer containing all 25 trials |
| `inspections/S63_A11_frontfall/` | Focused viewer containing only the five front-fall trials |
| `scripts/` | Reusable audit, plotting, viewer, geometry, filtering, and verification code copied from the S43 workflow |
| `viewer/` | Source assets used to build the self-contained inspection HTML |

## Manual A11 phase marking

1. Open `inspections/S63_A11_frontfall/INSPECT.html` in a browser.
2. Start with the `Raw` display. Use the filtered or overlay views only as a sensitivity comparison.
3. Review each trial in X/−Y and X/Z projections, preferably at 0.25× or 0.5× speed.
4. Mark one frame for each requested observation: `initial_standing`, `fall_onset`, `descent`, `apparent_contact`, and `post_fall`.
5. Add a note when a trial is incomplete, ambiguous, or visibly mistracked.
6. Click **Export notes JSON** before closing the page and return the exported `S63_phase_notes.json` file.

The viewer calls the contact observation `apparent_contact` because no force plate, floor calibration, or original video is available.

## Reproduce the audit

From this directory:

```bash
python -m pip install -r requirements-inspection.txt

python scripts/run_audit.py \
  --input /path/to/S63_FallSamples.zip \
  --config configs/S63.json \
  --output findings/S63_audit_new

python scripts/inspect_trials.py \
  --run findings/S63_audit_new \
  --selection configs/S63_A11_inspection_selection.json \
  --metadata configs/S63_collection_metadata.json \
  --cutoff-hz 1.5 \
  --filter-order 6 \
  --output inspections/S63_A11_frontfall_new
```

The output directories must not already exist. The 1.5 Hz Butterworth result is an optional comparison copied from the S43 inspection workflow; it is not a validated preprocessing choice for the pole pipeline.

## Verify the delivered package

```bash
python scripts/verify_s63_audit.py
python scripts/verify_s63_inspection.py
```

## Interpretation boundary

The calculated CoM is an approximate segment-mass proxy derived from skeleton landmarks and the male anthropometric model. The data do not provide anatomical CoM ground truth, force, ground-reaction force, center of pressure, perturbation torque, corrective torque, camera-to-floor calibration, or tracking-confidence values. These limitations do not prevent trajectory modeling, but they prevent treating apparent contact or inferred controller forces as directly measured quantities.
