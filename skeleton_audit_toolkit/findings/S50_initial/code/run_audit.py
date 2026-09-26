"""Create a new, reproducible subject audit run; never overwrite an existing run."""
from pathlib import Path
import argparse, json, re, platform, hashlib, shutil
import numpy as np
import matplotlib
from core import analyze, dump
from make_evidence import regenerate
from build_report import report

def run(source,config,output):
    cfg=json.loads(config.read_text())
    if not re.fullmatch(r'S\d+',cfg['subject_id']):raise ValueError('subject_id must be S followed by digits')
    for field in ['fps','mass_lb','height_in']:
        if not isinstance(cfg.get(field),(int,float)) or not np.isfinite(cfg[field]) or cfg[field]<=0:raise ValueError(field+' must be positive')
    if cfg.get('sex')!='male':raise ValueError('Only the documented adult male segment model is implemented')
    if cfg.get('coordinate_units') not in ['mm','m']:raise ValueError('coordinate_units must be mm or m')
    if not source.exists():raise FileNotFoundError(source)
    if source.is_dir() and source.resolve() in output.resolve().parents:raise ValueError('Keep output outside input folder')
    for key in ['joint_step_m','frame_scale_change_fraction','short_clip_seconds']:
        if cfg['screening'][key]<=0:raise ValueError('Screening thresholds must be positive')
    output.mkdir(parents=True,exist_ok=False)
    scripts=output/'code';shutil.copytree(Path(__file__).parent,scripts,ignore=shutil.ignore_patterns('__pycache__'))
    dump(output/'provenance.json',{'python':platform.python_version(),'numpy':np.__version__,'matplotlib':matplotlib.__version__,
         'source':str(source.resolve()),'code_sha256':{p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in scripts.glob('*.py')}})
    summary=analyze(source,cfg,output)
    (output/'research_notes.md').write_text('# Research notes\n\nAppend observations, evidence paths, interpretation, open questions and decisions here. This file is never regenerated.\n')
    regenerate(output);report(output)
    print(json.dumps({k:summary[k] for k in ['nonempty_files','empty_files','missing_files','invalid_files','total_frames']},indent=2))

if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--input',type=Path,required=True);p.add_argument('--config',type=Path,required=True);p.add_argument('--output',type=Path,required=True)
    a=p.parse_args();run(a.input,a.config,a.output)
