"""Recompute review tables from saved predictions; no training or test tuning."""
from pathlib import Path
import json, hashlib
import numpy as np
import pandas as pd
from sklearn.metrics import balanced_accuracy_score, recall_score, f1_score, roc_auc_score, average_precision_score, confusion_matrix
ROOT=Path(__file__).resolve().parents[1]; OUT=ROOT/'review'
rows=[]; subject_rows=[]; adl_rows=[]; checks=[]; controls={}; frames=[]
def calc(d,t):
 y=d.label.to_numpy(); s=d.probability.to_numpy(); pred=s>=t
 tn,fp,fn,tp=confusion_matrix(y,pred,labels=[0,1]).ravel()
 both = len(np.unique(y)) == 2
 return dict(balanced_accuracy=balanced_accuracy_score(y,pred) if both else np.nan,sensitivity=tp/(tp+fn) if tp+fn else np.nan,specificity=tn/(tn+fp) if tn+fp else np.nan,f1=f1_score(y,pred,zero_division=0),auroc=roc_auc_score(y,s) if both else np.nan,auprc=average_precision_score(y,s) if both else np.nan,tn=tn,fp=fp,fn=fn,tp=tp)
def check(name,ok): checks.append({'check':name,'passed':bool(ok)})
for p in sorted((ROOT/'outputs').glob('*/fold_*/seed_*/metrics.json')):
 m=json.loads(p.read_text()); folder=p.parent; cfg=json.loads((folder/'run_configuration.json').read_text()); h=pd.read_csv(folder/'history.csv')
 c,f,s=m['condition'],m['fold'],m['seed']; key=f'{c}/{f}/{s}'
 check(key+' history completion',len(h)==m['epochs_completed'] and h.epoch.max()==len(h) and len(h)>1)
 check(key+' best epoch',np.isclose(h.validation_loss.min(),m['best_validation_loss']) and m['best_epoch'] in h.epoch.values)
 groups=cfg['split_groups']; check(key+' disjoint groups',all(not set(groups[a])&set(groups[b]) for a,b in [('train','validation'),('train','test'),('validation','test')]))
 d=pd.read_csv(folder/'test_trial_predictions.csv'); w=pd.read_csv(folder/'test_window_predictions.csv'); v=pd.read_csv(folder/'validation_trial_predictions.csv')
 t=m['validation_threshold']; expected=calc(d,t)
 check(key+' test metrics',all(np.isclose(value,m['test_trial_'+name]) for name,value in expected.items()))
 check(key+' predicted labels',np.array_equal(d.prediction,(d.probability>=t).astype(int)))
 pooled=w.groupby('sample_id').probability.max().sort_index(); check(key+' window max aggregation',np.allclose(pooled,d.set_index('sample_id').probability.sort_index()))
 check(key+' real only evaluation',set(d.source_kind)|set(v.source_kind)<= {'real_adl','real_fall'})
 def group(x): return 'S31_S59_PAIR' if x in ['S31','S59'] else x
 check(key+' heldout membership',set(d.subject.map(group))<=set(groups['test']) and set(v.subject.map(group))<=set(groups['validation']))
 candidates=np.unique(np.r_[0,.5,1,v.probability]); scores=np.array([balanced_accuracy_score(v.label,v.probability>=q) for q in candidates]); best=candidates[np.isclose(scores,scores.max(),atol=1e-12,rtol=0)]; chosen=min(best,key=lambda q:abs(q-.5)); check(key+' validation threshold',np.isclose(chosen,t))
 events=0; seconds=0
 for _,g in w[w.label==0].groupby('sample_id'):
  pred=(g.sort_values('start_frame').probability>=t).to_numpy(); events+=int(np.sum(pred & ~np.r_[False,pred[:-1]])); seconds+=g.duration_s.iloc[0]
 check(key+' false alarm rate',events==m['false_positive_events'] and np.isclose(events/(seconds/60),m['false_positive_events_per_adl_minute']))
 signature={name:hashlib.sha256((folder/name).read_bytes()).hexdigest() for name in ['scaler.json']}
 signature.update(init=m['initialization_sha256'],split=groups,test_ids=sorted(d.sample_id),val_ids=sorted(v.sample_id))
 if (f,s) in controls: check(key+' matched controls',signature==controls[f,s])
 else: controls[f,s]=signature
 row={**m,**{'fixed05_'+k:val for k,val in calc(d,.5).items()},'real_fall_draws_to_best_epoch':m['best_epoch']*32*m['batch_real_fall_windows'],'synthetic_draws_to_best_epoch':m['best_epoch']*32*m['batch_synthetic_fall_windows']}; row.pop('training_pool_counts'); rows.append(row)
 for subject,g in d.assign(subject=d.subject.map(group)).groupby('subject'):
  subject_rows.append(dict(condition=c,fold=f,seed=s,subject=subject,**calc(g,t)))
 for a,g in d[d.label==0].groupby('activity_code'):
  adl_rows.append(dict(condition=c,fold=f,seed=s,activity=a,trials=len(g),fp=int(g.prediction.sum())))
 frames.append(d.assign(condition=c,fold=f,seed=s))
r=pd.DataFrame(rows); check('75 unique runs',len(r)==75 and not r.duplicated(['condition','fold','seed']).any())
r.to_csv(OUT/'recomputed_run_metrics.csv',index=False)
pd.DataFrame(checks).to_csv(OUT/'audit_checks.csv',index=False)
subjects=pd.DataFrame(subject_rows); subjects.to_csv(OUT/'subject_seed_metrics.csv',index=False)
subjects.groupby(['condition','subject']).mean(numeric_only=True).to_csv(OUT/'subject_mean_metrics.csv')
adl=pd.DataFrame(adl_rows); adl.groupby(['condition','activity'])[['trials','fp']].sum().assign(false_positive_fraction=lambda d:d.fp/d.trials).to_csv(OUT/'adl_activity_errors.csv')
pd.concat(frames).to_csv(OUT/'all_test_trial_predictions.csv',index=False)
metrics=['test_trial_balanced_accuracy','test_trial_sensitivity','test_trial_specificity','test_trial_f1','test_trial_auroc','test_trial_auprc','false_positive_events_per_adl_minute']
summary=r.groupby('condition')[metrics].agg(['mean','std']); summary.to_csv(OUT/'verified_summary.csv')
folds=r.groupby(['condition','fold'])[metrics].mean(); folds.to_csv(OUT/'verified_fold_means.csv')
for c in ['real60_synthetic40','real40_synthetic60']:
 d=folds.loc[c]-folds.loc['real_only']; d.to_csv(OUT/(c+'_fold_deltas.csv'))
 print(c,'BA fold deltas',d.test_trial_balanced_accuracy.round(6).tolist())
print('CHECKS',len(checks),'FAILED',sum(not a['passed'] for a in checks))
print(r.groupby('condition')[['best_epoch','epochs_completed','validation_threshold','fixed05_balanced_accuracy','fixed05_specificity','real_fall_draws_to_best_epoch']].mean().to_string())
print('ADL errors\n',adl.groupby(['condition','activity']).fp.sum().to_string())
print('SUBJECT BA\n',subjects.groupby(['subject','condition']).balanced_accuracy.mean().unstack().round(4).to_string())
json.dump({'runs':len(r),'checks':len(checks),'failed_checks':[a for a in checks if not a['passed']],'unique_test_trials':int(pd.concat(frames).sample_id.nunique()),'unique_fall_trials':int(pd.concat(frames).query('label==1').sample_id.nunique()),'unique_adl_trials':int(pd.concat(frames).query('label==0').sample_id.nunique())},open(OUT/'audit_summary.json','w'),indent=2)
