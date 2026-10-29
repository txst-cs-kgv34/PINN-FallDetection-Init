# S62 A11 manual phase status

The original user-supplied annotations are preserved in `S62_phase_notes.json`.
T01 and T03–T05 contain five strictly ordered phases and are included in the
validated modeling windows.

T02 has both `initial_standing` and `fall_onset` at frame 0. The model adapter
requires standing to precede onset, so T02 is excluded from the current
model-ready set and should be re-marked if it is intended for training. The
filtered validation input is `S62_phase_notes_model_ready.json`; no original
annotation was silently changed.

No marked phase frame was repaired. In the model-ready set, T03 descent frame
86, apparent-contact frame 99, and post-fall frame 124 coincide with raw audit
review flags and remain marked for inspection. T02 has three additional flagged
marks but is already excluded for phase-order failure. See
`S62_A11_phase_quality_flags.csv`.
