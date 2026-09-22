# PINN-FallDetection-Init

Initial investigation of physics-informed modeling using SmartFallMM skeleton data.
The repository contains a five-trial audit, reproducible figures, and a motion viewer.

## View a skeleton CSV

Open **`viewer/index.html`** in your browser (double-click the file after cloning or downloading this repository). No installation, server, internet connection or data upload is needed.

1. Click **Open CSV files** and choose one or several files from `s06_audit/raw/`.
2. Press **Play**, drag the timeline, or enter a zero-based frame index.
3. Drag the skeleton to rotate the 3D view. Scroll to zoom. Choose a fixed camera projection if preferred.
4. Use **Center on pelvis** to inspect posture without body translation, or keep it off to see movement through the recorded space.
5. Turn on joint indices or save the current view as a PNG.

The viewer supports headerless, comma-separated **96-column CSVs** in the standard **Azure Kinect 32-joint xyz order**. It rejects malformed/missing/nonfinite coordinates with a line number. It defaults to millimeters and 30 FPS; change these to match your recording. Other skeleton layouts need an explicit joint mapping and are not supported automatically.

You can also run `python -m http.server 8000` from the repository root and open `http://localhost:8000/viewer/`. GitHub's source-code page itself does not run the viewer.

## Recreate the original audit images

The original plotting code is already in **`s06_audit/audit.py`**. From the repository root:

```bash
python -m venv .venv
source .venv/bin/activate  # Windows PowerShell: .venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
python s06_audit/audit.py
python s06_audit/make_report.py
```

| Generated file | What the code plots |
| --- | --- |
| `s06_audit/results/comparison.png` | Pelvis/ankle camera positions, adjacent-frame jumps, and normalized limb lengths across all five trials |
| `s06_audit/results/snapshots.png` | Six evenly spaced skeleton poses per trial in camera X / negative camera Y |
| `s06_audit/results/paths.png` | Pelvis paths in camera XZ, colored by nominal time, with start/end markers |
| `s06_audit/S06A08_All_Trials_Audit.html` | Research report embedding the figures and metrics |

`audit.py` is specific to the five S06 activity-08 trials and also writes CSV/JSON diagnostics. `make_report.py` assembles those outputs and creates an audit ZIP beside `s06_audit/`. Run the audit before the report. Both scripts overwrite generated results but leave raw CSVs unchanged.

## Generate new snapshots or animated GIFs

The general renderer accepts one compatible CSV, including files outside this repository:

```bash
# Six 3D snapshots and a GIF of every frame
python scripts/render_skeleton.py s06_audit/raw/S06A08T03.csv --gif

# Inspect the audited jump using a fixed projection
python scripts/render_skeleton.py s06_audit/raw/S06A08T03.csv \
  --start 60 --end 75 --view xy --snapshots 4 --gif \
  --output-prefix outputs/T03_jump

# A shorter GIF with every third frame; timing accounts for the stride
python scripts/render_skeleton.py s06_audit/raw/S06A08T05.csv \
  --fps 30 --units mm --frame-step 3 --follow-pelvis --gif
```

Default output: `outputs/<CSV-stem>_snapshots.png` and, with `--gif`, `outputs/<CSV-stem>.gif`. Run `python scripts/render_skeleton.py --help` for options. The frame range is inclusive and zero-based. GIF frame stride may omit the final frame if it is not on the selected stride. GIF timing is approximate because the format uses 10 ms increments; use the browser viewer to inspect every source frame.

## Coordinate and research assumptions

- Blue marks anatomical left, orange right, and slate the trunk/face. These are the subject's sides, not screen sides.
- Plots use camera coordinates with negative camera Y displayed upward. The XZ view is a camera projection, not a calibrated floor plane.
- Every view has equal spatial scale on its axes and uses bounds fixed across the selected clip. The viewer does not normalize away changing limb lengths or smooth the data.
- Timestamps, confidence, forces and contact labels are absent from these CSVs. Displayed time is `frame_index / assumed_fps`, not a recovered timestamp.
- Discontinuities and apparent scale changes are data-quality findings, not confirmed falls. No CoM, BoS, force estimation or PINN training is performed by the viewer.
- All five included trials have been explored for quality. Preserve separate evaluation data for later research.

Format references: [SmartFallMM](https://github.com/txst-cs-smartfall/SmartFallMM-Dataset), [Azure Kinect joints](https://learn.microsoft.com/en-us/previous-versions/azure/kinect-dk/body-joints), and [coordinate conventions](https://learn.microsoft.com/en-us/previous-versions/azure/kinect-dk/coordinate-systems). Dataset-specific export conventions still need confirmation.

## Verification

The parser/geometry tests use Node's built-in test runner, with no npm dependencies:

```bash
node --test tests/skeleton.test.js
```

They load the actual T03 sample, check the previously audited jump, verify unit handling, and reject malformed CSVs. Python rendering requires only the dependencies in `requirements.txt`.

## Data acknowledgment

SmartFallMM data: **SmartFall Group, Texas State University**. See `s06_audit/provenance.json` for the exact source revision and file hashes. The repository's code license does not replace the source dataset's rights or acknowledgment requirements.
