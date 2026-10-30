# S62 full-run findings and provenance correction

## Decision

The full-run archive returned on October 30, 2026 cannot be interpreted as an S62-only result. Five stale S63 pole-compatible TSV files were present beside the five intended S62 files. Because the unchanged loader uses `SubjectB_*.tsv`, it accepted all ten files.

The returned Stage-1/Stage-3 checkpoints, identified controller, generated trajectories, and comparison figures are therefore mixed S62/S63 artifacts. They must not seed the S62 gain sweep. A clean full rerun is required from this corrected package.

## Evidence from the returned archive

- Intended S62 inputs: T01-T05.
- Actual accepted inputs: 5 S62 trials plus 5 S63 trials.
- Pooled evaluation: 10 trajectories and 1,290 samples.
- The reconstruction CSV explicitly lists `SubjectB_S63A11T01.tsv` through `T05.tsv`.
- The distribution analysis reports 10 original trajectories and a shared interval of only 0.23 s.

The mixed run identified:

| Parameter | Mixed-run value |
|---|---:|
| Kp theta | 145.1020 |
| Kd theta | 15.0720 |
| Kp x | 14.9113 |
| Kd x | 15.0716 |
| Pi | 3.6315 deg |
| Tau | 0.23 s |

These values are retained only as audit evidence and are not valid S62-only estimates.

## Reconstruction and generation warning

The mixed Stage-1 checkpoint reconstructed the pooled training data closely (`normalized loss = 0.00843`), but after Stage 3 the normalized reconstruction loss increased to `0.56534`, a factor of `67.07`. Stage-3 pooled RMSE was `7.03 deg` for theta and `17.43 cm` for x.

All 100 generated trajectories were finite, but their unsupported 30-second extrapolations were extreme: theta ranged from `-280.7` to `366.2 deg`, and x ranged from `-37.78` to `29.76 m`. These are not plausible human-fall magnitudes and reinforce that the long horizon is an extrapolation check, not physiological validation.

The S62 T02 usable window remains only 0.23 s. Even after the contamination is removed, it will determine the common-window distribution comparison unless a separate sensitivity analysis excludes it. This should be disclosed, not silently changed.

## Correction implemented

- Removed all S63-derived TSV and derived-signal files from the S62 project.
- Added exact input-inventory checks to the adapter, validation, runner, packager, and gain sweep.
- The corrected accepted inventory is exactly `SubjectB_S62A11T01.tsv` through `T05.tsv`.
- The gain sweep dynamically reads the new clean S62 gains, Pi, and tau after the corrected full run.
- S62 camera-facing orientation continues to be normalized in the skeleton-derived subject frame.

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
