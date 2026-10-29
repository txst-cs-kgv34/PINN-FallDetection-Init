# S57 A11 manual phase status

The user reported A11T01 and A11T02 as incomplete and intentionally did not
mark phases for them. They are explicitly excluded in
`../configs/S57_A11_phase_selection.json`.

The supplied notes for T03–T05 each contain five ordered phases and pass
structural, frame-bound, nominal-time, and strict phase-order validation.
Validated modeling windows are in `S57_A11_phase_windows.json` and `.csv`.

No marked phase frame was repaired. Three marks coincide with raw audit review
flags and remain marked for inspection: T03 apparent-contact frame 73, T03
post-fall frame 93, and T05 descent frame 75. See
`S57_A11_phase_quality_flags.csv`.
