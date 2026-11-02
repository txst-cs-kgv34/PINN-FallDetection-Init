"""Export skeleton snapshots and optional GIFs without changing raw coordinates.

Example: python scripts/render_skeleton.py s06_audit/raw/S06A08T03.csv --gif
"""
import argparse
from pathlib import Path
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.animation import FuncAnimation, PillowWriter

PARENTS = [-1,0,1,2,2,4,5,6,7,8,7,2,11,12,13,14,15,14,0,18,19,20,0,22,23,24,3,26,26,26,26,26]
EDGES = [(p,j) for j,p in enumerate(PARENTS) if p >= 0]
LEFT = {4,5,6,7,8,9,10,18,19,20,21}
RIGHT = {11,12,13,14,15,16,17,22,23,24,25}

def load_csv(path, units):
    try:
        data = np.loadtxt(path, delimiter=',', ndmin=2, encoding='utf-8-sig')
    except ValueError as exc:
        raise ValueError('Expected a headerless CSV with 96 numeric columns per frame.') from exc
    if data.shape[0] == 0 or data.shape[1] != 96:
        raise ValueError(f'Expected [frames, 96], received {data.shape}.')
    if not np.isfinite(data).all():
        raise ValueError('The CSV contains NaN or infinite coordinates.')
    return data.reshape(-1,32,3) * (.001 if units == 'mm' else 1.)

def display_coordinates(frames, view, follow):
    points = frames.copy()
    if follow:
        points -= points[:, :1, :]
    if view == 'xy': return points[:, :, [0,1]] * [1,-1]
    if view == 'yz': return points[:, :, [2,1]] * [1,-1]
    if view == 'xz': return points[:, :, [0,2]]
    # Plot height on the Matplotlib vertical axis, retaining camera X and Z.
    return points[:, :, [0,2,1]] * [1,1,-1]

def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('csv', type=Path)
    parser.add_argument('--output-prefix', type=Path, help='Default: outputs/<CSV stem>')
    parser.add_argument('--fps', type=float, default=30, help='Assumed source FPS (default 30)')
    parser.add_argument('--units', choices=['mm','m'], default='mm')
    parser.add_argument('--view', choices=['xy','yz','xz','3d'], default='3d')
    parser.add_argument('--start', type=int, default=0, help='Inclusive zero-based frame')
    parser.add_argument('--end', type=int, help='Inclusive zero-based frame, default last')
    parser.add_argument('--snapshots', type=int, default=6)
    parser.add_argument('--gif', action='store_true')
    parser.add_argument('--frame-step', type=int, default=1, help='GIF sampling stride; preserves nominal timing')
    parser.add_argument('--follow-pelvis', action='store_true', help='Remove pelvis translation for display only')
    args = parser.parse_args()
    if not np.isfinite(args.fps) or args.fps <= 0 or args.fps > 100:
        parser.error('--fps must be positive and at most 100 (GIF time resolution is 10 ms).')
    if not 1 <= args.snapshots <= 12 or args.frame_step < 1:
        parser.error('--snapshots must be 1–12 and --frame-step must be positive.')
    try: raw = load_csv(args.csv,args.units)
    except (ValueError,OSError) as exc: parser.error(str(exc))
    end = len(raw)-1 if args.end is None else args.end
    if not 0 <= args.start <= end < len(raw): parser.error('Frame range must satisfy 0 <= start <= end < frame count.')
    indices = np.arange(args.start,end+1)
    points = display_coordinates(raw[indices],args.view,args.follow_pelvis)
    center = (points.min((0,1))+points.max((0,1)))/2
    radius = max(.1,float(np.ptp(points,axis=(0,1)).max())/2)*1.15
    prefix = args.output_prefix or Path('outputs')/args.csv.stem
    prefix.parent.mkdir(parents=True,exist_ok=True)
    projection = {'projection':'3d'} if args.view=='3d' else {}
    labels = {'xy':['Camera X (m)','−Camera Y (m)'], 'yz':['Camera Z (m)','−Camera Y (m)'], 'xz':['Camera X (m)','Camera Z (m)'], '3d':['Camera X (m)','Camera Z (m)','−Camera Y (m)']}[args.view]
    def setup(ax):
        ax.set_xlim(center[0]-radius,center[0]+radius);ax.set_ylim(center[1]-radius,center[1]+radius)
        ax.set_xlabel(labels[0]);ax.set_ylabel(labels[1]);ax.grid(alpha=.2)
        if args.view=='3d':
            ax.set_zlim(center[2]-radius,center[2]+radius);ax.set_zlabel(labels[2]);ax.set_box_aspect((1,1,1));ax.view_init(elev=15,azim=-60)
        else:ax.set_aspect('equal')
    def lines_for(ax,pose):
        return [ax.plot(*pose[[a,b]].T,color='#007d9c' if b in LEFT else '#c66128' if b in RIGHT else '#344e5d',lw=2)[0] for a,b in EDGES]
    count = min(args.snapshots,len(points))
    fig,axes = plt.subplots(1,count,figsize=(4*count,4.8),subplot_kw=projection,squeeze=False,layout='constrained')
    for ax,i in zip(axes[0],np.linspace(0,len(points)-1,count,dtype=int)):
        setup(ax);lines_for(ax,points[i]);ax.set_title(f'Frame {indices[i]} · {indices[i]/args.fps:.2f} s')
    fig.suptitle(f'{args.csv.name} · {args.fps:g} FPS assumed · camera coordinates, no floor calibration')
    png = Path(str(prefix)+'_snapshots.png');fig.savefig(png,dpi=150);plt.close(fig);print(png)
    if args.gif:
        fig = plt.figure(figsize=(7,6),layout='constrained');ax=fig.add_subplot(111,**projection);setup(ax)
        artists = lines_for(ax,points[0]);title=ax.set_title('')
        def update(i):
            for line,(a,b) in zip(artists,EDGES):
                p=points[i,[a,b]];line.set_data(p[:,0],p[:,1])
                if args.view=='3d':line.set_3d_properties(p[:,2])
            title.set_text(f'{args.csv.stem} · frame {indices[i]} · {indices[i]/args.fps:.3f} s\nCamera coordinates; no floor/contact inference')
            return [*artists,title]
        sequence=list(range(0,len(points),args.frame_step))
        animation=FuncAnimation(fig,update,frames=sequence,interval=1000*args.frame_step/args.fps,blit=False)
        gif=Path(str(prefix)+'.gif');animation.save(gif,writer=PillowWriter(fps=args.fps/args.frame_step),dpi=100);plt.close(fig);print(gif)
        print('GIF timing is approximate (10 ms quantization). Use the browser viewer for frame-accurate inspection.')

if __name__ == '__main__': main()
