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

# Sex-specific anthropometry and complete female pipeline on a numerical fixture.
from run_audit import run as run_pipeline
from core import sensitivity
female=segment_model('female');male=segment_model('male')
expected={'head':(.0668,0.),'trunk':(.4257,.4964),'upper_arm':(.0255,.5754),
          'forearm':(.0138,.4559),'hand':(.0056,0.),'thigh':(.1478,.3612),
          'shank':(.0481,.4352),'foot':(.0129,.5)}
for seg in female:
    base=seg['name'].removesuffix('_left').removesuffix('_right')
    mass,alpha=expected[base]
    assert seg['reported_mass_fraction']==mass and seg['fraction']==alpha
    np.testing.assert_allclose(seg['mass_fraction'],mass/.9999,rtol=1e-14)
np.testing.assert_allclose(sum(s['mass_fraction'] for s in female),1.,atol=1e-14)
for sex in ['unknown','Female','',None]:
    try:segment_model(sex)
    except ValueError:pass
    else:raise AssertionError('Unsupported model accepted')
fc=com_proxy(x,female)[0]
np.testing.assert_allclose(com_proxy(x*2+3,female)[0],fc*2+3)
assert not np.allclose(fc,com_proxy(x,male)[0])
assert 'shank_fraction_0p4459' not in sensitivity(x,female,fc,'female')
# Independent per-frame calculation and unchanged real-male output.
for name in ['S50_initial','S06_check']:
    saved=ROOT/'findings'/name
    cfg=json.loads((saved/'config.json').read_text())
    for p in (saved/'results/com').glob('*.csv'):
        trial=p.name.removesuffix('_com_proxy.csv')
        xyz=np.loadtxt(saved/'raw'/(trial+'.csv'),delimiter=',').reshape(-1,32,3)*.001
        rows=np.genfromtxt(p,delimiter=',',names=True,dtype=None,encoding='utf-8')
        observed=np.column_stack([rows['com_proxy_camera_'+axis+'_m'] for axis in 'xyz'])
        np.testing.assert_allclose(com_proxy(xyz,segment_model(cfg['sex']))[0],observed,atol=1e-12)
with tempfile.TemporaryDirectory() as td:
    work=Path(td);src=work/'raw';src.mkdir()
    # Deterministic numerical coordinates exercise software; not a simulated fall.
    xyz=np.random.default_rng(7).normal(size=(4,32,3))
    np.savetxt(src/'S999A10T01.csv',xyz.reshape(4,96),delimiter=',')
    cfg=json.loads((ROOT/'configs/S50.json').read_text())
    cfg.update(subject_id='S999',sex='female',coordinate_units='m',mass_lb=140,height_in=65,activities={'A10':'Numerical test fixture'},expected_trials={})
    config=work/'config.json';config.write_text(json.dumps(cfg));out=work/'run'
    run_pipeline(src,config,out)
    model=json.loads((out/'segment_model.json').read_text())
    assert model['sex']=='female' and model['model_id'].endswith('_female')
    np.testing.assert_allclose(sum(s['mass_kg'] for s in model['segments']),140*.45359237)
    frame=json.loads((out/'results/com_proxy_all_frames.json').read_text())[0]
    expected_com=sum((m/.9999)*((1-alpha)*xyz[0,seg['a']].mean(0)+alpha*xyz[0,seg['b']].mean(0))
                     for seg in female for m,alpha in [expected[seg['name'].removesuffix('_left').removesuffix('_right')]])
    np.testing.assert_allclose([frame['com_proxy_camera_'+axis+'_m'] for axis in 'xyz'],expected_com)
    assert (out/'REPORT.html').exists() and len(list((out/'results/plots').glob('*.png')))==3
    assert json.loads((out/'config.json').read_text())['sex']=='female'
print('PASS: female coefficients, normalization, independent CoM, exports/figures/report; all male CoM frames unchanged')
