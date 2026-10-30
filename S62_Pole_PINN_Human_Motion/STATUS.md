# Delivery status

> Correction: the first returned full run included five stale S63 TSV inputs and is invalid as an S62-only result. This package removes those files and adds hard inventory checks. A clean full rerun is required before the gain sweep.

- Manual phase observations validated for S62A11T01-T05, including T02 frame 0 standing/frame 1 onset.
- Five repaired-audit-layer A11 CSV files copied and converted successfully.
- All five six-column pole-compatible TSV files pass the unchanged loader-contract decoder.
- Usable pre-20-degree windows: T01 2.96 s, T02 0.23 s, T03 2.62 s, T04 0.64 s, T05 2.28 s.
- Camera-facing orientation is normalized in the skeleton-derived subject frame.
- Post-cutoff tails that exceed the loader's 89-degree encoding range are trimmed without changing training samples.
- Core SHA-256 matches the locked S43/S63 pole source.
- Source defaults remain 7,000/5,000/5,000 epochs for Stages 1/2/3 and 100 generated trajectories.
- Python syntax, shell syntax, phase ordering, raw shape/finite checks, and adapter contracts pass locally.
- TensorFlow was not installed or run in this workspace. Run `smoke`, `full`, and then `gain-sweep` on the MacBook using `run_on_mac.sh`.
