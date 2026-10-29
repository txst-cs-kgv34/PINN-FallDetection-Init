# S62 inspection notes

The viewer contains 18 numerically valid trials and 3,077 frames.

## Input failures retained outside the viewer

- All five A10 backfall files contain blocks of completely blank coordinate rows: T01=24, T02=17, T03=19, T04=30, T05=13.
- `S62A12T04` contains 4 completely blank rows.
- `S62A14T04` contains 2 completely blank rows.

Consequently, S62 currently has no usable A10 trial. Silently deleting blank rows would collapse unknown time gaps, so any recovery requires an explicit resampling/re-export decision.

## Manual-review priorities

- `S62A14T05` and `S62A12T05` have limb-scale ranges above 100%, indicating very strong tracking/scale inconsistency.
- `S62A13T01`, `S62A13T05`, `S62A12T01`, `S62A13T03`, and `S62A11T03` also have large scale variation.
- `S62A13T01` has the most review-flagged frames (43); `S62A11T03`, `S62A12T05`, and `S62A12T01` follow closely.

Raw coordinates are the default player mode. The filtered view is only a 1.5 Hz sensitivity comparison. Exported manual labels should refer to observable skeleton phases; `apparent_contact` is not force-confirmed contact.

Automatic suggestions are available in `analysis_inputs/S62_automatic_phase_suggestions.json`. Their signal checks passed, but the extensive limb-scale variation means every suggested frame requires visual confirmation.
