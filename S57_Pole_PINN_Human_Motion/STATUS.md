# Delivery status

- Manual phase observations validated for S57A11T03-T05.
- Incomplete S57A11T01-T02 are explicitly excluded and are not present in the model input directory.
- Three repaired-audit-layer A11 CSV files copied and converted successfully.
- All three six-column pole-compatible TSV files pass the unchanged loader-contract decoder.
- Usable pre-20-degree windows: T03 1.87 s, T04 2.07 s, T05 2.12 s.
- Core SHA-256 matches the locked S43/S63 pole source.
- Source defaults remain 7,000/5,000/5,000 epochs for Stages 1/2/3 and 100 generated trajectories.
- Python syntax, shell syntax, phase ordering, raw shape/finite checks, and adapter contracts pass locally.
- TensorFlow was not installed or run in this workspace. Run `smoke` and `full` on the MacBook using `run_on_mac.sh`.
