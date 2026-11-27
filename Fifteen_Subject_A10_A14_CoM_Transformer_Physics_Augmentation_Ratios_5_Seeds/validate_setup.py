#!/usr/bin/env python3
from __future__ import annotations

import argparse
from collections import Counter
from pathlib import Path

import numpy as np

import detector_core as core
from ratio_sampler import ActivityFamilyBatchSampler, FALL_ACTIVITIES


HERE=Path(__file__).resolve().parent


def main() -> None:
    parser=argparse.ArgumentParser(description="Validate dataset, folds, source quotas, and leakage guards."); parser.add_argument("--config",type=Path,default=HERE/"config.json"); parser.add_argument("--data-root",type=Path); args=parser.parse_args()
    config=core.load_config(args.config)
    if args.data_root: config["data_root"]=str(args.data_root.expanduser().resolve())
    root=Path(config["data_root"]); rows=core.read_manifest(root); counts=Counter(row["source_kind"] for row in rows)
    expected={"real_adl":545,"real_fall":322,"synthetic_fall":1380}
    if dict(counts)!=expected: raise ValueError(f"Counts {dict(counts)} != {expected}")
    for row in rows:
        values,mask=core.load_trajectory(str((root/row["data_file"]).resolve()))
        if not mask.any() or values.shape[1]!=2: raise ValueError(f"Invalid trajectory {row['sample_id']}")
    for fold_index in range(len(config["folds"])):
        for condition,quotas in config["conditions"].items():
            split,_=core.split_rows(rows,config,fold_index,int(quotas["synthetic_falls"])>0)
            if any(row["source_kind"]=="synthetic_fall" for name in ("validation","test") for row in split[name]): raise AssertionError("Synthetic leakage")
            scaler=core.fit_real_training_scaler(split["train"],root); dataset=core.TrajectoryWindowDataset(split["train"],root,scaler,int(config["window_length"]),int(config["adl_stride"]),True,int(config["max_train_adl_windows_per_trial"]))
            sources=[];activities=[];families=[]
            for spec in dataset.specs:
                row=dataset.rows[spec.row_index]; sources.append(row["source_kind"]); activities.append(row["activity_code"]); families.append(row.get("synthetic_family_id",""))
            sampler=ActivityFamilyBatchSampler(dataset.labels,sources,activities,families,int(config["batch_size"]),3,11,int(quotas["real_falls"]),int(quotas["synthetic_falls"]))
            for batch in sampler:
                batch_sources=Counter(sources[index] for index in batch)
                expected_batch={"real_adl":30,"real_fall":int(quotas["real_falls"])}
                if quotas["synthetic_falls"]: expected_batch["synthetic_fall"]=int(quotas["synthetic_falls"])
                if dict(batch_sources)!=expected_batch: raise AssertionError((condition,batch_sources))
                for source in ("real_fall","synthetic_fall"):
                    selected=[activities[index] for index in batch if sources[index]==source]
                    if selected:
                        activity_counts=Counter(selected)
                        if set(activity_counts)!=set(FALL_ACTIVITIES) or max(activity_counts.values())-min(activity_counts.values())>1: raise AssertionError((condition,source,activity_counts))
    print(f"PASS: {len(rows)} trajectories, five leakage-safe folds, three exact-ratio conditions")


if __name__=="__main__":
    main()
