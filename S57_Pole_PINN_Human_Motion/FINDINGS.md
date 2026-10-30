# S57 full-run findings and provenance correction

## Decision

The full-run archive returned on October 30, 2026 cannot be interpreted as an S57-only result. Five stale S63 pole-compatible TSV files were present beside the three intended S57 files. Because the unchanged loader uses `SubjectB_*.tsv`, it accepted all eight files.

The returned Stage-1/Stage-3 checkpoints, identified controller, generated trajectories, and comparison figures are therefore mixed S57/S63 artifacts. They must not seed the S57 gain sweep. A clean full rerun is required from this corrected package.

## Evidence from the returned archive

- Intended S57 inputs: T03, T04, T05.
- Actual accepted inputs: 3 S57 trials plus 5 S63 trials.
- Pooled evaluation: 8 trajectories and 1,021 samples.
- The reconstruction CSV explicitly lists `SubjectB_S63A11T01.tsv` through `T05.tsv`.
- The distribution analysis reports 8 original trajectories and a shared interval of only 0.33 s.

The mixed run identified:

| Parameter | Mixed-run value |
|---|---:|
| Kp theta | 145.1311 |
| Kd theta | 15.0945 |
| Kp x | 5.2864 |
| Kd x | 15.0948 |
| Pi | 3.6162 deg |
| Tau | 0.23 s |

These values are retained only as audit evidence and are not valid S57-only estimates.

## Reconstruction and generation warning

The mixed Stage-1 checkpoint reconstructed the pooled training data closely (`normalized loss = 0.00993`), but after Stage 3 the normalized reconstruction loss increased to `1.09425`, a factor of `110.15`. Stage-3 pooled RMSE was `13.75 deg` for theta and `22.25 cm` for x.

All 100 generated trajectories were finite, but their unsupported 30-second extrapolations were extreme: theta ranged from `-641.0` to `282.2 deg`, and x ranged from `-81.63` to `84.16 m`. These are not plausible human-fall magnitudes and reinforce that the long horizon is an extrapolation check, not physiological validation.

## Correction implemented

- Removed all S63-derived TSV and derived-signal files from the S57 project.
- Added exact input-inventory checks to the adapter, validation, runner, packager, and gain sweep.
- The corrected accepted inventory is exactly:
  - `SubjectB_S57A11T03.tsv`
  - `SubjectB_S57A11T04.tsv`
  - `SubjectB_S57A11T05.tsv`
- The gain sweep dynamically reads the new clean S57 gains, Pi, and tau after the corrected full run.

## Required next sequence

```bash
./run_on_mac.sh build
./run_on_mac.sh input-check
./run_on_mac.sh smoke
./run_on_mac.sh full
./run_on_mac.sh analyze
./run_on_mac.sh package
./run_on_mac.sh gain-sweep
./run_on_mac.sh gain-sweep-package
```

Do not copy the old `results/full_run` directory into the corrected project. The gain-sweep setup validator deliberately rejects that older checkpoint because it lacks clean subject-only inventory provenance.
