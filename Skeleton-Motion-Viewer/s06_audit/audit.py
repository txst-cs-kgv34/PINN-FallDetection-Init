"""Read-only raw-data audit. Run with numpy and matplotlib installed.
All joint names, metre units, and times are provisional Azure Kinect / 30 FPS interpretations.
"""
from pathlib import Path
import numpy as np
import json, csv, hashlib
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

ROOT=Path(__file__).resolve().parent
OUT=ROOT/'results'; OUT.mkdir(exist_ok=True)
NAMES=['pelvis','spine_navel','spine_chest','neck','clavicle_left','shoulder_left','elbow_left','wrist_left','hand_left','handtip_left','thumb_left','clavicle_right','shoulder_right','elbow_right','wrist_right','hand_right','handtip_right','thumb_right','hip_left','knee_left','ankle_left','foot_left','hip_right','knee_right','ankle_right','foot_right','head','nose','eye_left','ear_left','eye_right','ear_right']
BONES={'left_thigh':(18,19),'right_thigh':(22,23),'left_shank':(19,20),'right_shank':(23,24),'left_upper_arm':(5,6),'right_upper_arm':(12,13),'left_forearm':(6,7),'right_forearm':(13,14),'pelvis_chest':(0,2)}
EDGES=[(0,1),(1,2),(2,3),(3,26),(2,4),(4,5),(5,6),(6,7),(7,8),(2,11),(11,12),(12,13),(13,14),(14,15),(0,18),(18,19),(19,20),(20,21),(0,22),(22,23),(23,24),(24,25)]
LOWER=[0,1,2,3,18,19,20,21,22,23,24,25]
CORE=[0,1,2,3,18,22]

def runs(mask):
    # Inclusive row-index ranges for contiguous True samples.
    edges=np.diff(np.r_[False,mask,False].astype(int))
    return list(zip(np.where(edges==1)[0],np.where(edges==-1)[0]-1))

summaries=[]; bones=[]; events=[]; dataset={}; perframes=[]
plt.rcParams.update({'font.size':10,'axes.spines.top':False,'axes.spines.right':False})
fig,axes=plt.subplots(5,3,figsize=(15,15),constrained_layout=True)
fig2,ax2=plt.subplots(5,6,figsize=(16,14),constrained_layout=True)
for row,p in enumerate(sorted((ROOT/'raw').glob('S06A08T0*.csv'))):
    a=np.loadtxt(p,delimiter=','); assert a.ndim==2 and a.shape[1]==96
    b=a.reshape(-1,32,3)/1000; n=len(b); t=np.arange(n)/30
    assert np.isfinite(b).all()
    raw=p.read_bytes(); ident=p.stem
    dataset[ident]=b
    d=np.linalg.norm(np.diff(b,axis=0),axis=2)
    length=np.stack([np.linalg.norm(b[:,i]-b[:,j],axis=1) for i,j in BONES.values()],axis=1)
    normlength=length/np.median(length,axis=0)
    scale=np.median(normlength[:,:8],axis=1)
    knee=[]
    for hip,k,ank in [(18,19,20),(22,23,24)]:
        u=b[:,hip]-b[:,k];v=b[:,ank]-b[:,k]
        knee.append(np.degrees(np.arccos(np.clip(np.sum(u*v,1)/(np.linalg.norm(u,axis=1)*np.linalg.norm(v,axis=1)),-1,1))))
    knee=np.array(knee).T
    # Exploratory screening only: neither flag defines physical impossibility or a fall.
    flagged=d[:,LOWER].max(1)>.2
    good=np.ones(n,dtype=bool)
    for k in np.where(flagged)[0]:good[max(0,k-2):min(n,k+4)]=False
    # Also flag temporal bone-scale deviation >10% from each trial's median.
    good &= np.max(np.abs(normlength[:,:8]-1),axis=1)<=.1
    spans=sorted(runs(good),key=lambda x:x[1]-x[0],reverse=True)
    top=np.unravel_index(np.argmax(d),d.shape)
    summary={'trial':ident,'frames':n,'columns':96,'duration_nominal_s':n/30,'first_to_last_s':(n-1)/30,'nonfinite_values':int((~np.isfinite(a)).sum()),'zero_values':int((a==0).sum()),'duplicate_rows':n-len(np.unique(a,axis=0)),'max_any_joint_step_m':float(d.max()),'max_lower_trunk_step_m':float(d[:,LOWER].max()),'max_core_step_m':float(d[:,CORE].max()),'max_pelvis_step_m':float(d[:,0].max()),'transitions_any_gt_0p2m':int((d.max(1)>.2).sum()),'transitions_lower_trunk_gt_0p2m':int(flagged.sum()),'transitions_lower_trunk_gt_0p1m':int((d[:,LOWER].max(1)>.1).sum()),'transitions_lower_trunk_gt_0p3m':int((d[:,LOWER].max(1)>.3).sum()),'max_step_joint':NAMES[top[1]],'max_step_from_index0':int(top[0]),'max_step_to_index0':int(top[0]+1),'limb_scale_min':float(scale.min()),'limb_scale_max':float(scale.max()),'limb_scale_end_start_ratio':float(np.median(scale[-10:])/np.median(scale[:10])),'pelvis_axis_range_m':np.ptp(b[:,0],axis=0).tolist(),'knee_angle_first10_median_deg':np.median(knee[:10],axis=0).tolist(),'knee_angle_middle20pct_median_deg':np.median(knee[int(.4*n):int(.6*n)],axis=0).tolist(),'knee_angle_last10_median_deg':np.median(knee[-10:],axis=0).tolist(),'screened_spans_index0':[[int(x),int(y)] for x,y in spans[:5]],'git_blob_sha1':hashlib.sha1(b'blob '+str(len(raw)).encode()+b'\0'+raw).hexdigest(),'sha256':hashlib.sha256(raw).hexdigest()}
    summaries.append(summary)
    corr=np.corrcoef(normlength[:,:8].T)
    summary['min_pairwise_limb_scale_correlation']=float(corr[np.triu_indices(8,1)].min())
    summary['max_minus_min_limb_scale_percent_of_min']=float(100*(scale.max()/scale.min()-1))
    summary['max_normalized_limb_spread']=float(np.ptp(normlength[:,:8],axis=1).max())
    for i,name in enumerate(BONES):
        v=length[:,i]
        bones.append({'trial':ident,'segment':name,'median_m':float(np.median(v)),'min_m':float(v.min()),'max_m':float(v.max()),'cv_percent':float(100*v.std()/v.mean()),'p95_minus_p05_over_median_percent':float(100*np.ptp(np.quantile(v,[.05,.95]))/np.median(v))})
    for k in np.where(d.max(1)>.2)[0]:
        j=int(d[k].argmax())
        events.append({'trial':ident,'from_index0':int(k),'to_index0':int(k+1),'to_time_nominal_s':float((k+1)/30),'max_joint':NAMES[j],'max_step_m':float(d[k,j]),'lower_trunk_max_m':float(d[k,LOWER].max()),'pelvis_step_m':float(d[k,0]),'joint_count_gt_0p2m':int((d[k]>.2).sum())})
    for k in range(n):
        perframes.append({'trial':ident,'index0':k,'time_nominal_s':k/30,'pelvis_camera_y_m':float(b[k,0,1]),'left_knee_included_angle_deg':float(knee[k,0]),'right_knee_included_angle_deg':float(knee[k,1]),'median_limb_length_ratio':float(scale[k]),'max_step_from_previous_m':float(d[k-1].max()) if k else '', 'screen_pass':bool(good[k])})
    ax=axes[row,0]
    for j,lab in [(0,'Pelvis'),(20,'L ankle'),(24,'R ankle')]:ax.plot(t,-b[:,j,1],label=lab,lw=1)
    ax.set(title=ident+' · '+str(n)+' frames',ylabel='Negative camera Y (m)')
    if row==0:ax.legend(ncol=3,fontsize=8)
    ax=axes[row,1];ax.plot(t[1:],d.max(1),label='Any joint',color='#aa8d7a',lw=1);ax.plot(t[1:],d[:,LOWER].max(1),label='Trunk/legs/feet',color='#b33b27',lw=1)
    ax.axhline(.2,color='gray',ls='--',lw=.8);ax.set(ylim=(0,1.1),ylabel='Frame step (m)')
    if row==0:ax.legend(fontsize=8)
    ax=axes[row,2]
    ax.plot(t,normlength[:,:8],lw=.7,alpha=.5);ax.plot(t,scale,color='black',lw=1.4,label='Median of 8 limbs')
    ax.axhline(1,color='gray',ls='--',lw=.7);ax.set(ylim=(.75,1.25),ylabel='Length / trial median')
    if row==0:ax.legend(fontsize=8)
    for ax in axes[row]:ax.grid(alpha=.2);ax.set_xlabel('Nominal seconds at 30 FPS')
    for col,k in enumerate(np.linspace(0,n-1,6,dtype=int)):
        ax=ax2[row,col];pose=b[k]
        # Per-pose horizontal recentering only, explicitly not a ground-frame reconstruction.
        for i,j in EDGES:ax.plot(pose[[i,j],0]-pose[0,0],-pose[[i,j],1],color='#14677b',lw=1.5)
        ax.set(xlim=(-.85,.85),ylim=(-1,.95),aspect='equal',title=f'{ident[-3:]} frame {k} ({k/30:.2f}s)')
        ax.grid(alpha=.15)
fig.suptitle('S06 activity 08: raw tracking audit · units and joint mapping provisional',fontsize=16)
fig.savefig(OUT/'comparison.png',dpi=150);plt.close(fig)
fig2.suptitle('Camera X / negative camera Y snapshots · no floor calibration',fontsize=16)
fig2.savefig(OUT/'snapshots.png',dpi=140);plt.close(fig2)
for name,rows in [('summary',summaries),('segments',bones),('jump_events',events),('frame_diagnostics',perframes)]:
    (OUT/(name+'.json')).write_text(json.dumps(rows,indent=2))
    with (OUT/(name+'.csv')).open('w',newline='') as f:
        writer=csv.DictWriter(f,fieldnames=list(rows[0]));writer.writeheader();writer.writerows(rows)
# Exact repeated frames between files would compromise an independent trial split.
cross=[]
keys=list(dataset)
for i,ki in enumerate(keys):
    for kj in keys[i+1:]:
        si={x.tobytes() for x in dataset[ki]}; sj={x.tobytes() for x in dataset[kj]}
        cross.append({'a':ki,'b':kj,'exact_shared_frames':len(si&sj)})
(OUT/'cross_trial_duplicates.json').write_text(json.dumps(cross,indent=2))
fig3,ax3=plt.subplots(1,5,figsize=(16,4.5),constrained_layout=True)
for ax,(name,b) in zip(ax3,dataset.items()):
    ax.plot(b[:,0,0],b[:,0,2],color='#acb9bd',lw=.8)
    sc=ax.scatter(b[:,0,0],b[:,0,2],c=np.arange(len(b))/30,s=8,cmap='viridis')
    ax.scatter(b[0,0,0],b[0,0,2],marker='o',s=85,facecolors='none',edgecolors='#111',label='Start')
    ax.scatter(b[-1,0,0],b[-1,0,2],marker='x',s=65,color='#111',label='End')
    ax.set(title=name[-3:],xlabel='Camera X (m)',ylabel='Camera Z (m)',aspect='equal');ax.grid(alpha=.2)
    fig3.colorbar(sc,ax=ax,label='Nominal seconds',shrink=.6)
    ax.legend(fontsize=8)
fig3.suptitle('Pelvis path in camera XZ · not a calibrated ground plane',fontsize=15)
fig3.savefig(OUT/'paths.png',dpi=140);plt.close(fig3)
# Candidate windows are chosen for further inspection, not certified clean gait.
candidates=[]
for name,lo,hi,label in [('S06A08T05',0,45,'Early walking candidate'),('S06A08T05',0,103,'Longer candidate containing direction change'),('S06A08T01',122,216,'Secondary reconstruction candidate')]:
    b=dataset[name][lo:hi+1]; ds=np.linalg.norm(np.diff(b,axis=0),axis=2)
    le=np.stack([np.linalg.norm(b[:,i]-b[:,j],axis=1) for i,j in list(BONES.values())[:8]],1)
    candidates.append({'trial':name,'from_index0':lo,'to_index0':hi,'label':label,'first_to_last_s':(hi-lo)/30,'max_lower_trunk_step_m':float(ds[:,LOWER].max()),'max_pelvis_step_m':float(ds[:,0].max()),'limb_length_cv_percent_max':float((100*le.std(0)/le.mean(0)).max())})
(OUT/'candidate_windows.json').write_text(json.dumps(candidates,indent=2))
print(json.dumps(summaries,indent=2))
