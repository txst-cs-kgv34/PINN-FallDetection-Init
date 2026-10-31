# Delivery status

- Corrected subject-only full run completed and analyzed.
- Input inventory validated as exactly S62A11T01-T05; stale S63 files are absent.
- Full 7,000/5,000/5,000 Stage 1/2/3 schedule completed with 100 generated trajectories.
- All 11 Stage-3 gain chunks completed from the same clean Stage-1 checkpoint.
- Primary sweep result: chunk 11 provides the best balanced pooled reconstruction and Stage-3 objective under the current protocol.
- S62 T02 still limits all-trial distribution comparisons to 0.23 s; this limitation is documented in `FINDINGS.md`.
- Camera-facing orientation remains normalized in the skeleton-derived subject frame.
- Core SHA-256 remains locked at `604985d2344350789929c3554f9ce4351b826f69be1dfe9dee0b20acb586e0a9`.
- The first mixed S62/S63 run is superseded and must not be reused.
