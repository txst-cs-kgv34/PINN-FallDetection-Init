"""Regenerate every evidence PNG using saved raw data and run configuration."""
from pathlib import Path
import argparse,json
import numpy as np
from core import make_plots,com_proxy

def regenerate(run):
    cfg=json.loads((run/'config.json').read_text());rows=json.loads((run/'results/trial_summary.json').read_text())
    segments=json.loads((run/'segment_model.json').read_text())['segments']
    data={};coms={};scales={}
    for row in rows:
        if not row['frames']:continue
        name=row['trial'];data[name]=np.loadtxt(run/'raw'/(name+'.csv'),delimiter=',',ndmin=2).reshape(-1,32,3)*{'mm':.001,'m':1}[cfg['coordinate_units']]
        coms[name]=com_proxy(data[name],segments)[0]
        frames=json.loads((run/'results/com_proxy_all_frames.json').read_text())
        scales[name]=np.array([f['median_normalized_limb_scale'] for f in frames if f['trial']==name])
    if data:make_plots(cfg,data,coms,scales,rows,run/'results/plots')

if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--run',type=Path,required=True);regenerate(p.parse_args().run)
