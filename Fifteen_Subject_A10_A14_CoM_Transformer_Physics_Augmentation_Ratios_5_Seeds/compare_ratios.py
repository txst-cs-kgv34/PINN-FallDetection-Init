#!/usr/bin/env python3
from __future__ import annotations

import argparse
import itertools
import json
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from scipy.stats import wilcoxon

import detector_core as core


HERE = Path(__file__).resolve().parent
LABELS = {"real_only": "Real only", "real60_synthetic40": "Real 60 : Syn 40", "real40_synthetic60": "Real 40 : Syn 60"}


def holm(rows: list[dict]) -> None:
    order=sorted(range(len(rows)),key=lambda i:rows[i]["p_value"]); running=0.0; total=len(rows)
    for rank,index in enumerate(order):
        adjusted=min(1.0,(total-rank)*rows[index]["p_value"]); running=max(running,adjusted); rows[index]["p_value_holm"]=running


def main() -> None:
    parser=argparse.ArgumentParser(description="Compare the three controlled fall-source conditions."); parser.add_argument("--config",type=Path,default=HERE/"config.json"); args=parser.parse_args()
    config=core.load_config(args.config); output=Path(config["output_root"]); conditions=list(config["conditions"]); records=[]
    for condition in conditions:
        for path in sorted((output/condition).glob("fold_*/seed_*/metrics.json")): records.append(json.loads(path.read_text()))
    frame=pd.DataFrame(records)
    expected=len(conditions)*len(config["folds"])*len(config["seeds"])
    if len(frame)!=expected: raise ValueError(f"Expected {expected} completed runs, found {len(frame)}")
    counts=frame.groupby("condition").size().to_dict()
    if any(counts.get(condition)!=len(config["folds"])*len(config["seeds"]) for condition in conditions): raise ValueError(f"Incomplete conditions: {counts}")
    destination=output/"comparison"; destination.mkdir(parents=True,exist_ok=True); frame.sort_values(["condition","fold_index","seed"]).to_csv(destination/"all_run_metrics.csv",index=False)
    metrics=list(config["comparison_metrics"])+[f"test_{activity}_sensitivity" for activity in core.FALL_ACTIVITIES]
    fold_frame=frame.groupby(["condition","fold_index"],as_index=False)[metrics].mean(); fold_frame.to_csv(destination/"fold_seed_averaged_metrics.csv",index=False)
    summary=[]
    for condition in conditions:
        subset=frame[frame.condition==condition]
        for metric in metrics:
            values=pd.to_numeric(subset[metric],errors="coerce"); summary.append({"condition":condition,"metric":metric,"mean":values.mean(),"standard_deviation":values.std(ddof=1),"minimum":values.min(),"maximum":values.max()})
    pd.DataFrame(summary).to_csv(destination/"condition_summary.csv",index=False)
    tests=[]
    for metric in metrics:
        metric_rows=[]
        for first,second in itertools.combinations(conditions,2):
            left=fold_frame[fold_frame.condition==first].sort_values("fold_index")[metric].to_numpy(float); right=fold_frame[fold_frame.condition==second].sort_values("fold_index")[metric].to_numpy(float); differences=right-left
            try: statistic,p_value=wilcoxon(left,right,alternative="two-sided")
            except ValueError: statistic,p_value=0.0,1.0
            metric_rows.append({"metric":metric,"first":first,"second":second,"mean_second_minus_first":float(np.mean(differences)),"median_second_minus_first":float(np.median(differences)),"wilcoxon_statistic":float(statistic),"p_value":float(p_value)})
        holm(metric_rows); tests.extend(metric_rows)
    pd.DataFrame(tests).to_csv(destination/"paired_wilcoxon_holm.csv",index=False)
    display_metrics=["test_trial_balanced_accuracy","test_trial_sensitivity","test_trial_specificity","test_trial_f1","test_trial_auroc","test_trial_auprc"]
    figure,axes=plt.subplots(2,3,figsize=(14,8));
    for axis,metric in zip(axes.flat,display_metrics):
        values=[frame[frame.condition==condition][metric].to_numpy(float) for condition in conditions]; axis.boxplot(values,tick_labels=[LABELS[c] for c in conditions]); axis.set_title(metric.removeprefix("test_trial_").replace("_"," ").title()); axis.tick_params(axis="x",rotation=15); axis.grid(axis="y",alpha=.25)
    figure.suptitle("A10-A14 detector: real/synthetic fall-source ratios"); figure.tight_layout(); figure.savefig(destination/"condition_metric_boxplots.png",dpi=180); plt.close(figure)
    figure,axis=plt.subplots(figsize=(10,5.5)); positions=[]; values=[]; labels=[]; width=.22
    for ai,activity in enumerate(core.FALL_ACTIVITIES):
        for ci,condition in enumerate(conditions): positions.append(ai+(ci-1)*width); values.append(frame[frame.condition==condition][f"test_{activity}_sensitivity"].to_numpy(float)); labels.append(LABELS[condition])
    boxes=axis.boxplot(values,positions=positions,widths=width*.85,patch_artist=True,manage_ticks=False); colors=["#4C78A8","#F58518","#54A24B"]
    for index,box in enumerate(boxes["boxes"]): box.set_facecolor(colors[index%3]); box.set_alpha(.7)
    axis.set_xticks(range(5),core.FALL_ACTIVITIES); axis.set_ylabel("Trial sensitivity"); axis.set_title("Per-activity sensitivity across 25 runs"); axis.grid(axis="y",alpha=.25); axis.legend([boxes["boxes"][i] for i in range(3)],[LABELS[c] for c in conditions],loc="lower left"); figure.tight_layout(); figure.savefig(destination/"per_activity_sensitivity_boxplots.png",dpi=180); plt.close(figure)
    best={}
    summary_frame=pd.DataFrame(summary)
    for metric in metrics:
        subset=summary_frame[summary_frame.metric==metric]; maximize=metric!="false_positive_events_per_adl_minute"; row=subset.loc[subset["mean"].idxmax() if maximize else subset["mean"].idxmin()]; best[metric]={"condition":row.condition,"mean":float(row["mean"])}
    core.write_json(destination/"comparison_summary.json",{"completed_runs":len(frame),"conditions":conditions,"folds":len(config["folds"]),"seeds":config["seeds"],"inference_unit":"seed-averaged fold","best_mean_by_metric":best})
    lines=["# A10-A14 detector ratio comparison","",f"Completed runs: **{len(frame)}/{expected}**.","","All conditions use identical folds, seeds, architecture, optimizer, real-only normalization, and real-only validation/test sets.","","| Metric | Best mean condition | Mean |","|:--|:--|--:|"]
    for metric,value in best.items(): lines.append(f"| {metric} | {LABELS[value['condition']]} | {value['mean']:.4f} |")
    lines.extend(["","Wilcoxon tests use five seed-averaged fold pairs with Holm adjustment. Interpret effect direction and fold consistency alongside p-values."])
    (destination/"COMPARISON.md").write_text("\n".join(lines)+"\n",encoding="utf-8")
    print(f"Saved comparison to {destination}")


if __name__ == "__main__":
    main()
