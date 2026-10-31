# Delivery status

- Corrected subject-only full run completed and analyzed.
- Input inventory validated as exactly S57A11T03-T05; incomplete T01-T02 and stale S63 files are absent.
- Full 7,000/5,000/5,000 Stage 1/2/3 schedule completed with 100 generated trajectories.
- All 11 Stage-3 gain chunks completed from the same clean Stage-1 checkpoint.
- Primary sweep result: chunk 10 minimizes pooled normalized reconstruction MSE, with the theta/objective tradeoff documented in `FINDINGS.md`.
- Core SHA-256 remains locked at `604985d2344350789929c3554f9ce4351b826f69be1dfe9dee0b20acb586e0a9`.
- The first mixed S57/S63 run is superseded and must not be reused.
