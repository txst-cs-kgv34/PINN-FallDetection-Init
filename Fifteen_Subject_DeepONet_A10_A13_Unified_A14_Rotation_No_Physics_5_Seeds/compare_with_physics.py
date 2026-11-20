#!/usr/bin/env python3
"""Paired comparison of the physics and no-physics five-seed experiments."""

from __future__ import annotations

import argparse
import csv
import json
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
from scipy.stats import ttest_rel


ROOT = Path(__file__).resolve().parent
DEFAULT_PHYSICS = ROOT.parent / "Fifteen_Subject_DeepONet_A10_A13_Unified_A14_Rotation_Physics_5_Seeds"


def read_csv(path: Path) -> list[dict[str, str]]:
    if not path.is_file(): raise FileNotFoundError(path)
    with path.open(newline="", encoding="utf-8") as handle: return list(csv.DictReader(handle))


def write_csv(path: Path, rows: list[dict]) -> None:
    keys=[]
    for row in rows:
        for key in row:
            if key not in keys: keys.append(key)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer=csv.DictWriter(handle,fieldnames=keys); writer.writeheader(); writer.writerows(rows)


def parity_view(config: dict) -> dict:
    value=json.loads(json.dumps(config))
    for key in ("experiment_name","display_name","training_regime","result_archive"): value.pop(key,None)
    training=value["training"]
    for key in ("use_physics","cartpole_physics_weight","rotation_physics_weight"): training.pop(key,None)
    return value


def metric_list(group: str) -> list[str]:
    values=["normalized_mse","theta_rmse_deg","theta_mae_deg","x_rmse_cm","x_mae_cm","theta_w1_deg","x_w1_cm"]
    if group=="rotation": values += ["yaw_rmse_deg","yaw_mae_deg","yaw_w1_deg"]
    return values


def compare_table(physics_rows: list[dict[str,str]], baseline_rows: list[dict[str,str]], keys: list[str], metrics: list[str]) -> tuple[list[dict],dict]:
    physics={tuple(row[key] for key in keys):row for row in physics_rows}; baseline={tuple(row[key] for key in keys):row for row in baseline_rows}
    if set(physics)!=set(baseline):
        missing_physics=sorted(set(baseline)-set(physics)); missing_baseline=sorted(set(physics)-set(baseline))
        raise ValueError(f"paired keys differ; missing physics={missing_physics[:5]}, missing baseline={missing_baseline[:5]}")
    output=[]; summary={}
    for key in sorted(physics):
        row={name:value for name,value in zip(keys,key)}
        for metric in metrics:
            p=float(physics[key][metric]); b=float(baseline[key][metric]); delta=p-b
            row[f"physics_{metric}"]=p; row[f"baseline_{metric}"]=b; row[f"physics_minus_baseline_{metric}"]=delta
            row[f"physics_percent_change_{metric}"]=100*delta/b if b!=0 else None
        output.append(row)
    for metric in metrics:
        p=np.asarray([float(physics[key][metric]) for key in sorted(physics)]); b=np.asarray([float(baseline[key][metric]) for key in sorted(baseline)]); delta=p-b
        test=ttest_rel(p,b,nan_policy="omit")
        summary[metric]={"pair_count":int(len(delta)),"physics_mean":float(p.mean()),"baseline_mean":float(b.mean()),"mean_physics_minus_baseline":float(delta.mean()),"mean_percent_change":float(100*delta.mean()/b.mean()) if b.mean()!=0 else None,"physics_win_fraction":float(np.mean(delta<0)),"paired_t_statistic":float(test.statistic),"paired_p_value":float(test.pvalue)}
    return output,summary


def plot_summary(summary: dict, path: Path, title: str) -> None:
    metrics=list(summary); delta=[summary[m]["mean_percent_change"] for m in metrics]
    fig,axis=plt.subplots(figsize=(max(9,len(metrics)*1.2),5.5)); colors=["#2E8B57" if value<0 else "#C94C4C" for value in delta]
    axis.bar(np.arange(len(metrics)),delta,color=colors); axis.axhline(0,color="black",linewidth=.9); axis.set_xticks(np.arange(len(metrics)),metrics,rotation=35,ha="right"); axis.set_ylabel("Physics vs baseline mean change (%)"); axis.set_title(title); axis.grid(axis="y",alpha=.25); fig.tight_layout(); fig.savefig(path,dpi=180); plt.close(fig)


def main() -> None:
    parser=argparse.ArgumentParser(description=__doc__); parser.add_argument("--physics-root",type=Path,default=DEFAULT_PHYSICS); parser.add_argument("--mode",choices=("full",),default="full"); args=parser.parse_args()
    physics_root=args.physics_root.expanduser().resolve(); baseline_root=ROOT
    physics_config=json.loads((physics_root/"experiment.json").read_text()); baseline_config=json.loads((baseline_root/"experiment.json").read_text())
    if parity_view(physics_config)!=parity_view(baseline_config): raise ValueError("physics and baseline configurations differ beyond the intended physics switches")
    destination=baseline_root/"comparison"; destination.mkdir(exist_ok=True); report={"physics_root":str(physics_root),"baseline_root":str(baseline_root),"pairing":"same trial filters, folds, validation subjects, test subjects, seeds, and architecture","groups":{}}
    for group in ("planar","rotation"):
        physics_dir=physics_root/"results"/group/args.mode; baseline_dir=baseline_root/"results"/group/args.mode; metrics=metric_list(group)
        subject_rows,subject_summary=compare_table(read_csv(physics_dir/"multi_seed_subject_metrics.csv"),read_csv(baseline_dir/"multi_seed_subject_metrics.csv"),["seed_index","test_subject"],metrics)
        activity_rows,activity_summary=compare_table(read_csv(physics_dir/"multi_seed_activity_metrics.csv"),read_csv(baseline_dir/"multi_seed_activity_metrics.csv"),["seed_index","activity"],metrics)
        trial_rows,trial_summary=compare_table(read_csv(physics_dir/"multi_seed_trial_metrics.csv"),read_csv(baseline_dir/"multi_seed_trial_metrics.csv"),["seed_index","trial"],metrics)
        write_csv(destination/f"{group}_paired_subject_comparison.csv",subject_rows); write_csv(destination/f"{group}_paired_activity_comparison.csv",activity_rows); write_csv(destination/f"{group}_paired_trial_comparison.csv",trial_rows)
        plot_summary(subject_summary,destination/f"{group}_physics_vs_baseline.png",f"{group.title()} physics vs no-physics baseline")
        report["groups"][group]={"subject_level":subject_summary,"activity_level":activity_summary,"trial_level":trial_summary}
    (destination/"comparison_summary.json").write_text(json.dumps(report,indent=2,sort_keys=True)+"\n")
    print(json.dumps(report,indent=2))


if __name__=="__main__": main()
