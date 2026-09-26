"""Meaningful regression and malformed-input tests; no real data are modified."""
from pathlib import Path
import json,hashlib,tempfile
import numpy as np
from core import analyze,segment_model,com_proxy
ROOT=Path(__file__).resolve().parents[1]
s=segment_model();assert np.isclose(sum(r['mass_fraction'] for r in s),1)
x=np.random.default_rng(21).normal(size=(10,32,3));c=com_proxy(x,s)[0]
np.testing.assert_allclose(com_proxy(x*2+3,s)[0],c*2+3)
for name,files,frames in [('S50_initial',19,895),('S06_check',5,1011)]:
    run=ROOT/'findings'/name;v=json.loads((run/'results/study_summary.json').read_text())
    assert (v['nonempty_files'],v['total_frames'])==(files,frames),(name,v['total_frames'])
    for row in json.loads((run/'results/manifest.json').read_text()):
        if row.get('sha256'):assert hashlib.sha256((run/'raw'/(row['trial']+'.csv')).read_bytes()).hexdigest()==row['sha256']
with tempfile.TemporaryDirectory() as td:
    root=Path(td);src=root/'input';src.mkdir()
    cfg=json.loads((ROOT/'configs/S50.json').read_text());cfg.update(subject_id='S123',activities={'A09':'test'},expected_trials={'A09':['T01','T02','T03','T04']})
    (src/'S123A09T01.csv').write_text('')
    (src/'S123A09T02.csv').write_text('1,2,3\n')
    np.savetxt(src/'S123A09T03.csv',np.ones((2,96))*np.nan,delimiter=',')
    out=root/'out';out.mkdir();v=analyze(src,cfg,out)
    assert (v['empty_files'],v['invalid_files'],v['missing_files'],v['total_frames'])==(1,2,1,0)
print('PASS: mass, affine CoM, S50/S06 counts, raw hashes, empty/invalid/missing cases')
