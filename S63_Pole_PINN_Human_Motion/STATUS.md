# Delivery status

- Manual phase observations copied and validated for S63A11T01-T05.
- Five raw A11 trials copied byte-for-byte from `S63_PINN_audit`.
- S63 male CoM adapter executed successfully.
- All five six-column pole-compatible TSV files decoded successfully.
- Usable pre-20-degree windows: T01 0.73 s, T02 1.22 s, T03 0.69 s, T04 1.10 s, T05 0.33 s.
- Core SHA-256 matches the S43 pole source.
- Source defaults remain 7,000/5,000/5,000 epochs for Stages 1/2/3 and 100 generated trajectories.
- Python syntax, shell syntax, phase-note structure, raw-data shape, and adapter contracts passed locally.
- TensorFlow training smoke and the full run were intentionally not executed in this workspace. Run them on the MacBook using `run_on_mac.sh`.
