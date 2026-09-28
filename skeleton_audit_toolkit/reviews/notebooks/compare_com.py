"""Compare reviewed v4 notebook CoM formula with toolkit, on identical unfiltered S43 poses.
Run from toolkit root: python reviews/notebooks/compare_com.py --notebooks /path/Gait-Analysis-Notebooks.zip
Reads a literal coefficient table with ast.literal_eval; never executes notebook cells.
"""
from pathlib import Path
import argparse,ast,json,zipfile,sys,hashlib
import numpy as np
ROOT=Path(__file__).resolve().parents[2];sys.path.insert(0,str(ROOT/'scripts'))
from core import NAMES,com_proxy,segment_model,write_csv,dump
p=argparse.ArgumentParser(description=__doc__);p.add_argument('--notebooks',type=Path,required=True);a=p.parse_args()
with zipfile.ZipFile(a.notebooks) as z:
    entries=[i for i in z.namelist() if i.endswith('/skeleton_analysis_v4.ipynb') and '__MACOSX' not in i]
    if len(entries)!=1:raise ValueError('Expected one main notebook')
    raw=z.read(entries[0]);nb=json.loads(raw)
tables=[]
for cell in nb['cells']:
    if cell['cell_type']!='code':continue
    for node in ast.parse(''.join(cell['source'])).body:
        if isinstance(node,ast.Assign) and any(isinstance(t,ast.Name) and t.id=='DELEVA_SEGMENTS' for t in node.targets):tables.append(ast.literal_eval(node.value))
if len(tables)!=1:raise ValueError('Expected one coefficient table')
idx={name.upper().replace('NAVEL','NAVAL'):i for i,name in enumerate(NAMES)}
run=ROOT/'findings/S43_audit';exclusions={'S43A10T01'};rows=[];distances=[]
for path in sorted((run/'raw').glob('*.csv')):
    if path.stem in exclusions:continue
    xyz=np.loadtxt(path,delimiter=',').reshape(-1,32,3)*.001
    c=np.zeros((len(xyz),3));total=0
    for name,prox,dist,lm,lf,rm,rf in tables[0]:
        c+=rf*(xyz[:,idx[prox]]+lf*(xyz[:,idx[dist]]-xyz[:,idx[prox]]));total+=rf
    c/=total
    ours=com_proxy(xyz,segment_model('female'))[0];d=np.linalg.norm(c-ours,axis=1);distances.extend(d.tolist())
    rows.append({'trial':path.stem,'frames':len(xyz),'median_3d_difference_m':float(np.median(d)),'max_3d_difference_m':float(d.max())})
summary={'notebook_sha256':hashlib.sha256(raw).hexdigest(),'excluded_trials':sorted(exclusions),'trials':len(rows),'frames':len(distances),
         'median_3d_difference_m':float(np.median(distances)),'max_3d_difference_m':max(distances),
         'method':'Notebook female table/formula versus toolkit female model; same float64 unfiltered coordinates in metres. Isolates coefficient/landmark choices; not accuracy validation and not a complete notebook execution.'}
out=Path(__file__).parent;write_csv(out/'com_model_comparison.csv',rows);dump(out/'com_model_comparison.json',summary);print(json.dumps(summary,indent=2))
