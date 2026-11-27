#!/usr/bin/env python3
from __future__ import annotations

import argparse
from pathlib import Path

import torch
from torch.utils.data import DataLoader

import detector_core as core
from model import CoMTemporalTransformer
from ratio_sampler import ActivityFamilyBatchSampler


HERE=Path(__file__).resolve().parent


def main() -> None:
    parser=argparse.ArgumentParser(description="Run one forward/backward batch for every ratio condition."); parser.add_argument("--config",type=Path,default=HERE/"config.json"); parser.add_argument("--data-root",type=Path); parser.add_argument("--device",default="cpu",choices=["cpu","mps","cuda","auto"]); args=parser.parse_args()
    config=core.load_config(args.config)
    if args.data_root: config["data_root"]=str(args.data_root.expanduser().resolve())
    rows=core.read_manifest(Path(config["data_root"])); device=core.choose_device(args.device)
    for condition,quotas in config["conditions"].items():
        core.set_seed(11); split,_=core.split_rows(rows,config,0,int(quotas["synthetic_falls"])>0); scaler=core.fit_real_training_scaler(split["train"],Path(config["data_root"])); dataset=core.TrajectoryWindowDataset(split["train"],Path(config["data_root"]),scaler,int(config["window_length"]),int(config["adl_stride"]),True,int(config["max_train_adl_windows_per_trial"]))
        sources=[];activities=[];families=[]
        for spec in dataset.specs:
            row=dataset.rows[spec.row_index]; sources.append(row["source_kind"]); activities.append(row["activity_code"]); families.append(row.get("synthetic_family_id",""))
        sampler=ActivityFamilyBatchSampler(dataset.labels,sources,activities,families,int(config["batch_size"]),1,11,int(quotas["real_falls"]),int(quotas["synthetic_falls"])); loader=DataLoader(dataset,batch_sampler=sampler,collate_fn=core.collate_windows,num_workers=0); features,masks,labels,_=next(iter(loader))
        model=CoMTemporalTransformer(int(config["window_length"]),d_model=int(config["d_model"]),nhead=int(config["nhead"]),num_layers=int(config["num_transformer_layers"]),dim_feedforward=int(config["dim_feedforward"]),dropout=float(config["dropout"])).to(device); logits=model(features.to(device),masks.to(device)); loss=torch.nn.functional.binary_cross_entropy_with_logits(logits,labels.to(device)); loss.backward(); print(condition,sampler.batch_composition(),float(loss.item()))
    print("Smoke test PASS")


if __name__=="__main__":
    main()
