from pathlib import Path
import json,base64,html,zipfile

root=Path(__file__).resolve().parent
rows=json.loads((root/'results/summary.json').read_text())
candidates=json.loads((root/'results/candidate_windows.json').read_text())
commit='c538ee0cfc985ebebab5dae013b544b8bc4ad6fd'
repo='https://github.com/txst-cs-smartfall/SmartFallMM-Dataset'

def picture(name,alt):
    data=base64.b64encode((root/'results'/name).read_bytes()).decode()
    return f'<img src="data:image/png;base64,{data}" alt="{alt}">'

def table(headers,records):
    return '<table><thead><tr>'+''.join(f'<th>{html.escape(str(x))}</th>' for x in headers)+'</tr></thead><tbody>'+''.join('<tr>'+''.join(f'<td>{html.escape(str(x))}</td>' for x in rec)+'</tr>' for rec in records)+'</tbody></table>'

metrics=table(['Trial','Frames','Nominal seconds','Max joint step (m)','Max pelvis step (m)','Flagged trunk/leg transitions¹','Apparent limb-scale range²'],[
    [r['trial'][-3:],r['frames'],f"{r['duration_nominal_s']:.2f}",f"{r['max_any_joint_step_m']:.3f}",f"{r['max_pelvis_step_m']:.3f}",f"{r['transitions_lower_trunk_gt_0p2m']}/{r['frames']-1}",f"{r['max_minus_min_limb_scale_percent_of_min']:.1f}%"] for r in rows])
observations=table(['Trial','Observed sequence / provisional interpretation','Main issue','Proposed role'],[
['T01','Seated-looking start, rise, walking and direction reversal; upright end','Scale grows during initial rise; a few large pose jumps','Secondary reconstruction candidate after early transition'],
['T02','Seated-looking start and middle, then rise and walking; upright end','Strong discontinuities early in the clip','Investigate source frames; later segment may be usable'],
['T03','Upright start, seated-looking middle, upright end','Major pose discontinuity near 2.27 s','Reference for the first audit and failure analysis'],
['T04','Upright start, seated-looking later interval, possible renewed rise near end','Largest joint jump and widest apparent scale variation','Prioritize source-quality investigation'],
['T05','Upright walking, direction reversal, return, flexion near end','Stable early geometry; shrinking apparent scale near final flexion','Preferred starting trial for exploratory reconstruction']])
windows=table(['Trial','Zero-based frames','Nominal interval','Max trunk/leg step','Largest limb-length CV','Interpretation'],[
[c['trial'][-3:],f"{c['from_index0']}–{c['to_index0']}",f"{c['from_index0']/30:.2f}–{c['to_index0']/30:.2f} s",f"{c['max_lower_trunk_step_m']:.3f} m",f"{c['limb_length_cv_percent_max']:.2f}%",c['label']] for c in candidates])
events=table(['Trial','Largest step: zero-based frame transition','Nominal arrival time','Provisional joint'],[
[r['trial'][-3:],f"{r['max_step_from_index0']} → {r['max_step_to_index0']}",f"{r['max_step_to_index0']/30:.3f} s",r['max_step_joint']] for r in rows])
thresholds=table(['Trial','>0.10 m','>0.20 m','>0.30 m'],[[r['trial'][-3:],r['transitions_lower_trunk_gt_0p1m'],r['transitions_lower_trunk_gt_0p2m'],r['transitions_lower_trunk_gt_0p3m']] for r in rows])
questions=[
('How were activity-08 trials cropped?', 'The files start and finish in different postures and cover different parts of the apparent route. Does each represent a complete timed TUG, a partial phase, or a crop from repeated cycles? Please provide original frame ranges and phase/protocol definitions.'),
('Why do all limb lengths change by a common scale factor?', 'Eight arm/leg segment lengths co-vary almost perfectly in every trial. Was there body-size estimation, normalization, retargeting, smoothing, or rescaling in the acquisition/export pipeline? Can the original unprocessed skeleton and export code be inspected?'),
('What is the exact coordinate and camera convention?', 'Please confirm joint order, millimeters versus another unit, sensor/world frame, body identity, and whether the skeleton uses a single camera, fusion, or switching. Is gravity/floor calibration available?'),
('Can timestamps and tracking confidence be recovered?', 'The 96-column exports omit timestamps, original frame numbers, body IDs and confidence. Were frames ever dropped, resampled, interpolated or concatenated? These details determine whether nominal 30 FPS derivatives are meaningful.'),
('What contact and synchronized measurements are available?', 'For BoS, are foot dimensions, chair location, contact annotations or restricted-access visual checks available? For later forces, are force measurements available? If using matching IMU trials, what alignment procedure and units were used?')]
qs=''.join(f'<li><b>{q}</b><p>{a}</p></li>' for q,a in questions)
page=f'''<!doctype html><html lang="en"><meta charset="utf-8"><title>S06 activity 08: five-trial audit</title>
<style>body{{font:16px/1.6 system-ui,sans-serif;color:#19323e;max-width:1160px;margin:44px auto;padding:0 26px}}h1{{font-size:34px;line-height:1.2}}h2{{margin-top:34px;padding-top:18px;border-top:1px solid #cbd9de}}table{{border-collapse:collapse;width:100%;margin:18px 0;font-size:14px}}td,th{{padding:10px 9px;text-align:left;border-bottom:1px solid #d8e3e7;vertical-align:top}}th{{background:#eaf2f5}}img{{width:100%;height:auto;margin:12px 0}}.note{{padding:18px;background:#edf4f6;border-left:4px solid #176b87}}.small{{font-size:13px;color:#516773}}a{{color:#176b87}}code,pre{{background:#f0f3f4}}pre{{padding:16px;white-space:pre-wrap}}li{{margin-bottom:14px}}@media print{{body{{margin:0}}h2{{break-after:avoid}}tr,img{{break-inside:avoid}}}}</style>
<p class="small">PINN Fall Detection · Evidence for the September 15–22, 2026 weekly meeting · Audit performed September 21</p>
<h1>Five-trial audit of S06 activity 08</h1>
<p class="note"><b>Research decision:</b> use an early segment of trial 05 for the first exploratory motion-reconstruction baseline. Obtain acquisition and crop details before interpreting absolute CoM, support margins or forces. None of the five raw files is certified as a clean complete TUG or ready for direct force estimation.</p>
<h2>Verified scope and assumptions</h2>
<p>Audited all five matching files in <code>old/skeleton/S06A08T0*.csv</code>, T01–T05, at repository commit <code>{commit}</code>. Verified every raw file against its repository Git blob hash. T03 also exactly matches the user's attachment. The audit covers 1,011 frames and 97,056 numeric coordinates. The nominal frame-count coverage totals 33.70 seconds across separate files, not a continuous recording.</p>
<p>Each file has 96 numeric columns, no header, no nonfinite values, no zero-valued entries and no exact duplicate rows. No exact shared frames were found between any pair of trials. This rules out only exact numerical duplicates, not related recordings or other leakage. Original inputs remain unchanged.</p>
<p>Participant metadata supplied by the user: male, 170 lb (77.1107 kg), 5 ft 10 in (1.778 m). The audit assumes standard Azure Kinect joint order, millimeters and nominal 30 FPS for interpretation. The repo specifies 32 xyz joints and 30 FPS, but export-specific coordinates and processing still need confirmation. Time and physical-distance results below are conditional on these assumptions. A negative-Y plot is a camera-axis display, not a calibrated gravity frame.</p>
<h2>Comparison</h2>{metrics}
<p class="small">¹ Number of adjacent-frame transitions where any of 12 pelvis/trunk/hip/knee/ankle/foot joints moves more than 0.20 m. This is an exploratory screening threshold, equivalent to an interval-average speed of 6 m/s at 30 FPS. It is not a validated error or fall criterion. ² (Maximum/minimum − 1) × 100 for the common apparent scale of eight limb lengths, each normalized by its within-trial median. Values describe apparent geometry change, not physiological bone growth. Duration is N/30; first-to-last time is (N−1)/30.</p>
<h2>Main finding: apparent body scale changes within every trial</h2>
<p>Both thighs, both shanks, both upper arms and both forearms change length together almost exactly. The minimum pairwise correlation between their normalized length traces exceeds 0.9999999998 in every trial. The traces differ by less than 0.000006 in normalized units. Thus this is a common scale pattern, rather than independent fluctuations in each limb.</p>
<p>The within-trial maximum/minimum scale ranges are 25.0–43.3%. This is incompatible with treating the raw skeleton as a rigid anthropometric model with fixed segment lengths. It could originate in the tracker, a body-model fitting stage, or export processing; the data alone do not identify its cause. Do not silently rescale the raw coordinates: a correction could alter real translation or contact geometry. Determine the source first and preserve raw-versus-corrected comparisons.</p>
{picture('comparison.png','Five rows comparing camera-axis positions, joint discontinuities and apparent limb scale')}
<h2>Motion coverage differs across the files</h2>{observations}
<p>These descriptions combine skeleton snapshots, knee-angle diagnostics, pelvis position and camera-XZ paths. They are provisional kinematic interpretations. A seated-looking pose does not verify chair contact, and a direction reversal does not by itself establish a protocol-defined turn. No timing or fall-risk assessment is made.</p>
{picture('snapshots.png','Six skeleton snapshots for each of the five trials')}
{picture('paths.png','Pelvis camera-XZ trajectories with start and end markers for all five trials')}
<h2>Discontinuities to show the dataset team</h2>{events}
<p>Inspect the neighboring frames in the original recording and tracker output. The top jumps in T02–T04 are especially concerning. T05 has a lower maximum joint step and lower maximum trunk/pelvis step, but it still contains foot-motion flags. No jump was removed, interpolated or labeled as a fall.</p>
<details><summary>Threshold sensitivity: flagged trunk/leg transitions</summary>{thresholds}<p>The count changes substantially with the threshold. Use the maximum displacements, anatomical location, scale consistency and visual inspection together rather than selecting trials using a single cutoff.</p></details>
<h2>Candidate windows for a reconstruction baseline</h2>{windows}
<p><b>First candidate:</b> T05 frames 0–45 (CSV rows 1–46), nominal 0–1.50 s. Its eight limb lengths have approximately 0.87% coefficient of variation, and the pelvis path initially follows one direction. The interval is short and supports an initial reconstruction demonstration, not a validated gait model. Foot contact and floor alignment remain unresolved.</p>
<p>T05 frames 0–103 offer a longer 3.43 s reconstruction interval, but the path includes a direction change, so they should not be treated as straight walking under one fixed-support pendulum assumption. T01 frames 122–216 provide a secondary interval, also requiring phase checks.</p>
<p>The general screening method marks both sides of any trunk/leg step over 0.20 m with a two-frame neighborhood and excludes frames where any of the eight limb lengths differs more than 10% from that trial's median. Passing this screen does not establish tracking accuracy, correct anatomy, normal gait or correct contact. The selected candidate intervals are fully specified for review.</p>
<h2>Implications for CoM, BoS and PINN work</h2>
<ul><li><b>CoM:</b> use stable reconstructed segment geometry and documented mass fractions. Height and weight support scaling and inertial parameters but cannot repair unknown coordinate processing.</li>
<li><b>BoS:</b> estimate stance/contact and foot support geometry in a floor-aligned frame. The CSV provides neither contact labels nor sole boundaries; apparent chair phases require additional support assumptions.</li>
<li><b>Forces:</b> do not differentiate the uncorrected raw signals and interpret the result as force. Contact loads and inertial assumptions are still required, even after motion reconstruction.</li>
<li><b>First model:</b> compare smoothing and a fixed-segment kinematic fit on the early T05 interval before adding dynamics residuals. Record residuals and sensitivity to the scale treatment.</li>
<li><b>Validation:</b> all five trials have now been explored for quality. Keep this participant's work explicitly exploratory. Define separate training/validation trials before model fitting and obtain additional untouched trials or subjects for final evaluation.</li></ul>
<h2>Questions for the meeting, in priority order</h2><ol>{qs}</ol>
<h2>Suggested progress statement</h2>
<p class="note">We audited all five S06 activity-08 skeleton trials. The files are numerically complete, but we found discontinuities, common changes in apparent body scale and differing movement-phase coverage. Trial 05 has a promising early interval for a reconstruction baseline. We need the acquisition/export and cropping details before making physically grounded CoM, support or force claims.</p>
<h2>Completed work and proposed next steps</h2>
<p><b>Completed:</b> verified downloads, shape/completeness and duplicate checks, per-joint displacement screening, limb-length analysis, knee-angle diagnostics, visual comparison, candidate-window selection and prioritized data questions.</p>
<p><b>Next:</b> clarify metadata, define trial/subject splits, reconstruct the selected interval with fixed segment lengths, compare against raw and smoothed motion, then quantify uncertainty in approximate CoM and support. No PINN was trained, no CoM/BoS/forces were estimated, and no fall trajectories were generated in this audit.</p>
<h2>Sources and reproducibility</h2>
<p>Dataset: <a href="{repo}/tree/{commit}/old/skeleton">SmartFallMM skeleton directory</a> and <a href="{repo}/blob/{commit}/README.md">versioned README</a>. Joint/coordinate interpretation: <a href="https://learn.microsoft.com/en-us/previous-versions/azure/kinect-dk/body-joints">Microsoft body-joint documentation</a> and <a href="https://learn.microsoft.com/en-us/previous-versions/azure/kinect-dk/coordinate-systems">coordinate conventions</a>. Confirm dataset-specific export behavior before adopting these conventions.</p>
<p>The accompanying audit bundle contains the five original CSVs, hash/provenance manifest, audit code, structured metrics, frame-level diagnostics, candidate windows and figures. Run <code>python audit.py</code> followed by <code>python make_report.py</code> with NumPy and Matplotlib installed. All metric definitions and provisional index mappings are in the code. No external downloads occur during these scripts.</p>
</html>'''
report=root/'S06A08_All_Trials_Audit.html'
report.write_text(page)
manifest={'repository':repo,'commit':commit,'analysis_date':'2026-09-21','source_glob':'old/skeleton/S06A08T0*.csv','files':[{'path':'old/skeleton/'+r['trial']+'.csv','git_blob_sha1':r['git_blob_sha1'],'sha256':r['sha256'],'frames':r['frames']} for r in rows],'assumptions':['Standard Azure Kinect joint order','Coordinates in millimeters','Nominal 30 FPS without verified original timestamps'],'raw_modified':False}
(root/'provenance.json').write_text(json.dumps(manifest,indent=2))
(root/'README.md').write_text('''# S06 activity-08 audit

Five-trial exploratory data audit, 21 September 2026.

Open S06A08_All_Trials_Audit.html for the findings, plots and team questions.
Raw data are unchanged and credited to the SmartFall Group, Texas State University.
See provenance.json for repository commit and byte-level identities.

## Reproduce

Requires Python 3, NumPy and Matplotlib. Run:

```bash
python audit.py
python make_report.py
```

The scripts use relative paths and perform no network operations.
Results include CSV/JSON summary, per-segment statistics, jump event indices,
per-frame diagnostics, duplicate comparisons, candidate intervals and PNG plots.

## Interpretation

Units, joint names and time estimates assume standard Azure Kinect exports
and nominal 30 FPS. Thresholds are exploratory, not validated error/fall labels.
No filtering, correction, CoM, BoS, force estimation or model training was performed.
All five trials have been quality-inspected and are exploratory data.
''')
zip_path=root.parent/'S06A08_Audit_Bundle.zip'
with zipfile.ZipFile(zip_path,'w',zipfile.ZIP_DEFLATED) as z:
    for p in sorted(root.rglob('*')):
        if p.is_file() and p.name!='run_summary.txt' and '__pycache__' not in p.parts:
            z.write(p,'s06_audit/'+str(p.relative_to(root)))
print(report)
print(zip_path)
