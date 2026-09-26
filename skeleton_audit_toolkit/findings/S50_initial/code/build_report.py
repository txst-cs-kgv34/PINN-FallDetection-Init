"""Regenerate findings and offline HTML; preserve research_notes.md."""
from pathlib import Path
import argparse,json,html

def report(run):
    s=json.loads((run/'results/study_summary.json').read_text());rows=json.loads((run/'results/trial_summary.json').read_text())
    lines=[f"# {s['subject']['subject_id']} audit findings",'',
        f"Usable numeric clips: {s['nonempty_files']}; empty: {s['empty_files']}; missing expected: {s['missing_files']}; invalid: {s['invalid_files']}; analyzed frames: {s['total_frames']}.",'',
        f"Review-flagged destination frames: {s['total_review_flagged_destination_frames']}. Duplicate rows within clips: {s['duplicate_rows_within']}.",'',
        'These are data-quality screening results, not validated fall labels or anatomical CoM. No frames are repaired or interpolated. Invalid trials remain in raw/ and manifest.json but are withheld from calculations.','',
        '| Trial | Status | Frames | Span (s) | Review frames |','|---|---|---:|---:|---:|']
    for r in rows:lines.append(f"| {r['trial']} | {r['status']} | {r['frames']} | {r.get('first_to_last_s','—')} | {r.get('flagged_destination_frames','—')} |")
    lines+=['','## Evidence and reproducibility','','- results/manifest.json: source paths, hashes and parsing errors.','- results/trial_summary.csv: clip-level measurements.','- results/review_events.csv (when flags exist): exact frame pairs for inspection.','- results/com/: per-frame CoM and camera displacements.','- results/segment_mass_model.csv and segment_model.json: full mass and landmark mapping.','- results/landmark_sensitivity.csv: alternative mappings, not uncertainty bounds.','- config.json and code/: frozen configuration and scripts.','',
        '## Questions for the team','','Confirm XYZ units/order, camera-to-floor orientation, original timestamps, missing/trimmed recordings and body-tracking confidence. Determine whether changing limb scale is in the raw export or preprocessing. Review full event coverage before selecting PINN trials. No ground contact, BoS, joint forces or external perturbations are inferred here.','',
        '## Evidence figures','']
    for p in sorted((run/'results/plots').glob('*.png')):lines.append(f'![{p.stem}]({p.relative_to(run).as_posix()})\n')
    (run/'FINDINGS.md').write_text('\n'.join(lines)+'\n')
    text=html.escape('\n'.join(lines[:lines.index('## Evidence figures')]))
    pictures=''.join(f'<h2>{html.escape(p.stem)}</h2><img src="{p.relative_to(run).as_posix()}">' for p in sorted((run/'results/plots').glob('*.png')))
    (run/'REPORT.html').write_text('<!doctype html><meta charset="utf-8"><title>Skeleton audit</title><style>body{font:16px sans-serif;max-width:1200px;margin:30px auto;padding:20px}pre{white-space:pre-wrap}img{width:100%}</style><h1>Skeleton audit</h1><p>See research_notes.md for manual notes.</p><pre>'+text+'</pre>'+pictures)

if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--run',type=Path,required=True);report(p.parse_args().run)
