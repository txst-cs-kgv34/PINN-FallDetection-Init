# S55 inspection notes

The viewer contains 21 numerically valid trials and 3,562 frames.

## Input failures retained outside the viewer

- `S55A10T01`: 26 completely blank coordinate rows.
- `S55A10T02`: 5 completely blank coordinate rows.
- `S55A13T01`: 1 completely blank coordinate row.
- `S55A14T01`: 48 completely blank coordinate rows.

These trials are retained in the audit manifest but withheld from derived calculations and phase inspection. Silently deleting blank rows would collapse unknown time gaps, so any recovery requires an explicit resampling/re-export decision.

## Manual-review priorities

- Retained clips range from 4.33 s to 7.70 s, so clip duration is generally adequate for phase review.
- `S55A11T02` has the most review-flagged frames (45).
- `S55A11T04` has the largest limb-scale range (45.2%).
- Also inspect `S55A14T03`, `S55A10T04`, `S55A13T03`, and `S55A11T01` carefully for tracking-scale changes.

Raw coordinates are the default player mode. The filtered view is only a 1.5 Hz sensitivity comparison. Exported manual labels should refer to observable skeleton phases; `apparent_contact` is not force-confirmed contact.

Automatic suggestions are available in `analysis_inputs/S55_automatic_phase_suggestions.json`. Their signal checks passed for these clips, but every suggested frame still requires visual confirmation.
