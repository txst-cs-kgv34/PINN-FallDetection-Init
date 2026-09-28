# Review of the shared gait-analysis notebooks

Reviewed 2026-09-28 UTC / 2026-09-27 America/Chicago. All three notebooks in the supplied ZIP were readable. This is a source-code review plus an isolated CoM formula comparison on S43, not a complete rerun of the notebooks or their animation exports. Their example CSV files and researcher-specific local paths are not included in the notebook ZIP. The original notebooks have not been modified.

## 1. What each notebook contains

| Notebook | Input and purpose |
|---|---|
| skeleton_analysis_v4.ipynb | Main SmartFallMM workflow: 32-joint, 96-column CSV assumed millimetres; selects 23 named joints for segment CoM, animation and gait/stability plots. Young example S63A07T01; older example S02A08T01. |
| motion_generation_analysis-Amul.ipynb | Separate generated/real sections; 21 joints/63 columns, or 32 joints mapped to 21; assumes metres. Missing hands are represented at wrists. Loads model outputs; does not generate motion. |
| motion_generation_analysis_Shahriar.ipynb | Ground-truth section maps 32 joints to 21; generated section uses a custom 16-joint/48-column format, with header detection. Both actively divide coordinates by 1,000. Loads model outputs; does not train or run a generator. |

The 23-joint subset called SMPL in the main notebook is a selection/reordering of Kinect landmarks. There is no fitted SMPL mesh, body-shape optimization or volumetric CoM calculation.

## 2. Main notebook walkthrough

The main notebook has 10 cells (six code cells, including a final empty code cell). In zero-based notebook cell numbering:

- Cell 2 defines dependencies, joint labels, connections, the 14-segment coefficient table, data loading, filtering, segment CoM and summary metrics.
- Cell 3 defines plotting functions for relative lateral CoM motion, foot separation, extrapolated CoM margin and static CoM margin.
- Cell 4 defines animate_skeleton(), which runs loading/filtering/CoM/metrics and exports an MP4.
- Cells 6 and 8 run the young and older examples respectively. Both call static CoM-margin plots; their dynamic margin-of-stability calls are commented out.

### Loading and filtering

load_pose() reads a headerless CSV, drops any row containing NaN, casts to float32, reshapes to (frames,32,3), and divides by 1,000. The shape matches our assumed SMM format; file paths, sex and unit verification are still required.

By default, apply_butterworth() independently filters each joint and coordinate using an order-6 Butterworth low-pass filter at 1.5 Hz with a 30 Hz sampling rate. filtfilt() runs the filter forward and backward: offline zero-phase filtering, with twice the specified filter order in the combined response. SciPy recommends second-order-section implementations for improved numerical behavior. This smoothing is not a missing-data or common-scale correction. It may attenuate rapid fall motion and alter segment lengths; cutoff sensitivity must be evaluated before adoption. It also uses future samples, so it is unsuitable as-is for a prospective online predictor. Short clips can fail the default padding requirement.

### Segment and whole-body CoM

For each segment, choose a proximal landmark p, distal landmark d, sex-specific location fraction alpha, and mass fraction w:

    c_segment(t) = p(t) + alpha * [d(t) - p(t)]
    CoM(t) = sum(w * c_segment(t)) / sum(w)

The notebook uses one head and trunk plus bilateral upper arms, forearms, hands, thighs, shanks and feet. It estimates mass distribution by body segments, not by uniformly weighting the available joints.

It does not read subject height or weight. Weight cancels from the normalized position calculation if the segment fractions are fixed. Our toolkit additionally records segment masses in kg and reported stature for diagnostics. Neither method obtains subject-specific mass distribution solely from sex, weight and height. The notebook's division by total_mass already handles rounded female fractions summing to 0.9999.

### Gait summary metrics

compute_gait_metrics() returns:

| Label in notebook | Actual calculation |
|---|---|
| CoM Fore-Aft | Mean camera-Z CoM coordinate, not displacement |
| CoM Width/ML | Maximum minus minimum camera-X CoM coordinate |
| CoM Height | Absolute difference between mean CoM Y and the mean Y of both FOOT landmarks over the clip |
| Walking Speed | Mean norm of finite-difference CoM velocity in camera X/Z |
| Stride Width | Mean absolute camera-X separation of the two FOOT landmarks |
| Base of Support | Mean camera-X/Z distance between the two FOOT landmarks |

These are descriptive coordinate summaries under axis assumptions. The latter three are not automatically valid walking speed, gait-event stride width or physical BoS during a fall.

### Sway and step plots

plot_com_ml_steps() applies a 15-frame moving average to CoM and foot X coordinates, subtracts the foot midpoint, and removes the remaining signal mean. It detects maxima/minima with find_peaks(), each separated from other peaks of the same kind by roughly FPS/3, and labels their count as steps. Alternating extrema are not validated foot-contact events, particularly during falls or turning. Mean removal makes the signal useful for oscillation plots but removes the absolute offset from foot center; do not use that centered curve as a stability margin. The moving average uses zero padding at edges, which can create artificial endpoint changes, and needs a length guard for clips shorter than its window.

### What the notebook calls BoS

There are three different constructions:

1. compute_gait_metrics(): a single mean distance between FOOT_LEFT and FOOT_RIGHT in X/Z.
2. plot_ankle_bos(): despite the function name/title, uses FOOT positions and shades the interval between their X coordinates.
3. plot_com_bos_margin() and plot_margin_of_stability(): use ANKLE X positions as boundaries.

For the static plot, b_left = min(ankle X), b_right = max(ankle X), and:

    margin = min(b_right - CoM_X, CoM_X - b_left)

A positive value means the CoM X coordinate is between those two landmarks. It does not establish that the projected CoM is inside a contact-based support area. Two points/one interval do not provide a foot-shaped support polygon, and the code does not determine which foot is bearing weight. Hands, knees and trunk contacts during a fall are absent from the support calculation.

### Dynamic margin

plot_margin_of_stability() implements the familiar inverted-pendulum expression:

    omega0 = sqrt(g / l)
    XCoM_X = CoM_X + velocity_X / omega0
    margin = min(b_right - XCoM_X, XCoM_X - b_left)

Its l is the clip-average absolute vertical hip-to-ankle difference on the left side. This collapses with sitting, bending or lying and is not a reliable fixed pendulum length across an entire fall. The formula is useful as a future upright-phase model-based diagnostic, after establishing a calibrated ground frame, effective pendulum length and valid support boundaries. A negative notebook margin should not be exported as a confirmed fall or clinical instability label. This calculation does not infer forces or solve PINN dynamics.

### Animation

animate_skeleton() draws the selected joints, links, labels and green CoM marker. FFmpeg is only needed for MP4 export, not CoM mathematics or ordinary plots. The path is hard-coded to /opt/homebrew/bin/ffmpeg and the sample input paths belong to the researcher. The main notebook defaults to save_fps=25 while calculations use 30 FPS; retaining every frame makes its default video play at 5/6 speed (20% longer duration). Set playback FPS equal to data FPS for real-time viewing.

In the other notebooks, the comment that elev=90 gives a floor-plane view is inconsistent with their coordinate placement: Matplotlib looks along plotted Z, so the visible plane is X/Y, while the assumed floor is X/Z. A view change is not ground calibration. Equal geometric scaling and explicit axes should be added for quantitative interpretation.

## 3. Differences from our CoM implementation

These differences should be reconciled with the researcher, rather than silently declaring either SDK approximation exact.

| Choice | Main notebook | Current toolkit |
|---|---|---|
| Head landmark proxy | NECK toward HEAD | HEAD point |
| Trunk landmarks/direction | PELVIS toward NECK | NECK toward midpoint of hips |
| Hand proxy | WRIST toward HAND | HAND point |
| Foot proxy | ANKLE toward FOOT at 0.4014 | ANKLE/FOOT midpoint |
| Female head alpha | 0.5831 | No interpolation: HEAD point |
| Female trunk alpha | 0.4920 on its own endpoints | 0.4964 on toolkit endpoints |
| Female forearm alpha | 0.4592 | 0.4559 |
| Female shank alpha | 0.4416 | 0.4352 |
| Male shank alpha | 0.4459 | 0.4395, with a 0.4459 sensitivity variant |

The toolkit coefficient source is the Visual3D implementation table recorded in its README; that is not a claim that its Kinect proxy mappings reproduce the original anatomical study exactly. The notebooks cite de Leva but do not provide a coefficient-by-coefficient source or endpoint-conversion rationale. Ask which reference/landmark convention justifies their table. If the same two endpoints are reversed, the equivalent fraction is 1-alpha, not alpha; changing PELVIS to midpoint of hips is an additional mapping change.

Controlled comparison: on the 24 remaining S43 trials (5,898 frames), the notebook female formula differs from our female CoM by a median **4.470 mm** and maximum **5.328 mm** in 3D. Both used identical unfiltered coordinates, float64 and metres, isolating coefficient/mapping choices. This is agreement between estimates, not validation against measured anatomical CoM. The notebook's default filtering was intentionally not included. Reproduce with compare_com.py; per-trial differences and input notebook hash are saved alongside this review.

## 4. Additional implementation issues

- dropna() silently deletes frames and subsequent calculations still assume uniform 30 FPS. Preserve frame indices/time and missingness instead.
- The notebook treats every gender string other than exactly "male" as female. Validate inputs rather than defaulting silently.
- The camera axes are not automatically anatomical medial-lateral, anterior-posterior or gravity-aligned vertical. This is especially important for turn-and-fall. Azure documents camera right/down/forward, not a calibrated floor frame.
- Mean foot Y across the whole clip is not a floor-plane estimate; taking an absolute value does not correct camera tilt or airborne feet.
- The Amul notebook assumes metres even for its accepted 96-column branch; use explicit units rather than guessing by shape.
- The Shahriar ground-truth comments say not to divide by 1,000, but its active code does divide. Its custom 16-joint branch also divides. Verify each source format.
- The Shahriar 16-joint branch omits the head segment and renormalizes the remaining masses (male total 0.9306, female 0.9331), so its result is not directly the same whole-body model. Its right foot segment uses ANKLE_RIGHT to FOOT_LEFT because FOOT_RIGHT is absent. That crosses the body and needs a reviewed replacement proxy or explicit missing-segment policy.
- Missing hands represented at wrists in the 21-joint branches are documented approximations; the comment calling their error negligible is not supported by a validation test in these notebooks.
- The notebooks define functions/globals again in later sections; extracting explicit input adapters and pure analysis functions would reduce execution-order mistakes.

## 5. What to reuse for the PINN project

| Component | Proposed use |
|---|---|
| Joint-name dictionaries and format adapters | Reuse the design; keep full Kinect32 coordinates internally and validate units/schema |
| Segment-weighted CoM function | Keep the shared method, reconcile coefficients and landmark direction, retain named model versions |
| Skeleton + CoM animation | Reuse the visualization approach with raw/filtered toggle, correct FPS and audit flags |
| Foot/ankle midpoint and separation traces | Add as descriptive camera-coordinate proxies, named accordingly |
| Raw/filtered comparison | Optional diagnostic only; choose cutoff using sensitivity analysis and retain raw provenance |
| Per-frame CoM and support comparisons | Useful later for real-versus-generated comparisons under the same frame/model conventions |
| XCoM/MoS | Defer to calibrated upright/standing phases with a contact/support model; not a whole-fall PINN loss |
| Peak-based step count and clip-mean gait summaries | Not primary metrics for these five fall classes |

Neither notebook resolves our repeated-frame/common-scale issues or estimates ground reaction forces, joint forces, controller gains or perturbations. Smoothing could hide the audit evidence. None implements PINN training or a synthetic motion generator.

## 6. S43 decision and next experiment

Per the user's decision, S43A10T01 is excluded from the future modeling candidate list, while the original raw file and 25-file audit are retained. configs/S43_modeling_selection.json records the exclusion and 24 remaining trials (5,898 frames). The audit runner deliberately audits every file; the selection manifest is for future modeling and does not yet control a training pipeline.

The remaining trials still contain 1,211 duplicate rows and 800 review-flagged destination frames. Excluding T01 does not fix their common-scale changes.

Next: reconcile the coefficient/mapping table with the researcher; establish units, timing, scaling/export history and a ground frame; inspect raw selected trials with CoM and foot traces; then annotate phases and choose complete reliable windows. Start reconstruction before dynamic identification and perturbation simulation. Use matched phase, model and coordinates for future real/generated comparisons; agree on common anatomical proxies when joint layouts differ.

## Sources and review scope

- User-supplied Gait-Analysis-Notebooks.zip; the main analysis above follows named functions and zero-based source-cell indices.
- Current toolkit scripts/core.py and the original S43 audit outputs.
- Microsoft Azure Kinect coordinate systems: https://learn.microsoft.com/en-us/previous-versions/azure/kinect-dk/coordinate-systems
- SciPy filtfilt documentation: https://docs.scipy.org/doc/scipy/reference/generated/scipy.signal.filtfilt.html
- Hof, Gazendam and Sinke (2005), The condition for dynamic stability: https://doi.org/10.1016/j.jbiomech.2004.03.025 ; author institution abstract https://research.rug.nl/en/publications/the-condition-for-dynamic-stability/
- Toolkit parameter source (reviewed when implementing the model; fresh retrieval failed during this review): https://www.has-motion.com/wiki/doku.php?id=visual3d:documentation:definitions:adjusted_zatsiorsky-seluyanov_s_segment_inertia_parameters

No problems reading the attached notebooks. Their external example data were not supplied, so the full original example runs and MP4 exports were not reproduced. No notebook-derived BoS or stability feature has been incorporated into the production audit during this review.
