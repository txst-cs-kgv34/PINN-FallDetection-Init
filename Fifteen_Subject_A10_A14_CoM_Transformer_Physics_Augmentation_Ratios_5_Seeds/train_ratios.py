from __future__ import annotations

import argparse
import hashlib
import json
import shutil
import time
from collections import Counter
from pathlib import Path
from typing import Any, Sequence

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import torch
from torch.utils.data import DataLoader

import detector_core as core
from model import CoMTemporalTransformer
from ratio_sampler import ActivityFamilyBatchSampler


HERE = Path(__file__).resolve().parent


def parse_int_list(values: Sequence[str] | None) -> list[int] | None:
    if not values: return None
    result: list[int] = []
    for value in values: result.extend(int(item) for item in value.split(",") if item.strip())
    return result


def build_model(config: dict[str, Any]) -> CoMTemporalTransformer:
    return CoMTemporalTransformer(window_length=int(config["window_length"]), d_model=int(config["d_model"]), nhead=int(config["nhead"]), num_layers=int(config["num_transformer_layers"]), dim_feedforward=int(config["dim_feedforward"]), dropout=float(config["dropout"]))


def model_hash(model: torch.nn.Module) -> str:
    digest = hashlib.sha256()
    for name, value in sorted(model.state_dict().items()):
        digest.update(name.encode("utf-8")); digest.update(value.detach().cpu().numpy().tobytes())
    return digest.hexdigest()


def make_dataset(rows, config, scaler, training: bool) -> core.TrajectoryWindowDataset:
    return core.TrajectoryWindowDataset(rows, Path(config["data_root"]), scaler, int(config["window_length"]), int(config["adl_stride"]), training, int(config["max_train_adl_windows_per_trial"]) if training else None)


@torch.no_grad()
def evaluate(model: torch.nn.Module, loader: DataLoader, device: torch.device) -> tuple[float, pd.DataFrame]:
    model.eval(); logits_all=[]; labels_all=[]; metadata_all=[]
    for features, masks, labels, metadata in loader:
        logits_all.append(model(features.to(device), masks.to(device)).cpu()); labels_all.append(labels.cpu()); metadata_all.extend(metadata)
    logits = torch.cat(logits_all); labels = torch.cat(labels_all)
    loss = float(torch.nn.functional.binary_cross_entropy_with_logits(logits, labels).item())
    return loss, core.prediction_frame(torch.sigmoid(logits).numpy(), labels.numpy().astype(int), metadata_all)


def plot_history(frame: pd.DataFrame, path: Path) -> None:
    figure, axis = plt.subplots(figsize=(7, 4.2)); axis.plot(frame["epoch"], frame["train_loss"], label="training"); axis.plot(frame["epoch"], frame["validation_loss"], label="validation")
    axis.set(xlabel="Epoch", ylabel="Binary cross-entropy", title="Training history"); axis.grid(alpha=.25); axis.legend(); figure.tight_layout(); figure.savefig(path, dpi=180); plt.close(figure)


def run_one(condition: str, fold_index: int, seed: int, config: dict[str, Any], rows, device: torch.device, overwrite: bool) -> dict[str, Any]:
    quotas = config["conditions"][condition]
    fold_name = config["folds"][fold_index]["name"]
    run_dir = Path(config["output_root"]) / condition / fold_name / f"seed_{seed:05d}"
    metrics_path = run_dir / "metrics.json"
    if metrics_path.is_file() and not overwrite: return json.loads(metrics_path.read_text(encoding="utf-8"))
    if run_dir.exists() and overwrite: shutil.rmtree(run_dir)
    run_dir.mkdir(parents=True, exist_ok=True)
    core.set_seed(seed)
    split, partitions = core.split_rows(rows, config, fold_index, include_synthetic_train=int(quotas["synthetic_falls"]) > 0)
    scaler = core.fit_real_training_scaler(split["train"], Path(config["data_root"]))
    core.write_json(run_dir / "scaler.json", scaler)
    training = make_dataset(split["train"], config, scaler, True); validation = make_dataset(split["validation"], config, scaler, False); test = make_dataset(split["test"], config, scaler, False)
    source_kinds=[]; activities=[]; families=[]
    for spec in training.specs:
        row = training.rows[spec.row_index]; source_kinds.append(row["source_kind"]); activities.append(row["activity_code"]); families.append(row.get("synthetic_family_id", ""))
    sampler = ActivityFamilyBatchSampler(training.labels, source_kinds, activities, families, int(config["batch_size"]), int(config["steps_per_epoch"]), seed, int(quotas["real_falls"]), int(quotas["synthetic_falls"]))
    loader = DataLoader(training, batch_sampler=sampler, num_workers=int(config["num_workers"]), collate_fn=core.collate_windows)
    evaluation_size = max(128, int(config["batch_size"]))
    val_loader = DataLoader(validation, batch_size=evaluation_size, shuffle=False, num_workers=int(config["num_workers"]), collate_fn=core.collate_windows)
    test_loader = DataLoader(test, batch_size=evaluation_size, shuffle=False, num_workers=int(config["num_workers"]), collate_fn=core.collate_windows)
    model = build_model(config).to(device); initialization_hash = model_hash(model)
    optimizer = torch.optim.AdamW(model.parameters(), lr=float(config["learning_rate"]), weight_decay=float(config["weight_decay"]))
    scheduler = torch.optim.lr_scheduler.ReduceLROnPlateau(optimizer, mode="min", factor=.5, patience=max(2, int(config["early_stopping_patience"]) // 3))
    criterion = torch.nn.BCEWithLogitsLoss(); best_loss=float("inf"); best_epoch=0; stale=0; history=[]; checkpoint=run_dir / "best_model.pt"; started=time.time()
    for epoch in range(1, int(config["max_epochs"]) + 1):
        model.train(); losses=[]
        for features, masks, labels, _ in loader:
            optimizer.zero_grad(set_to_none=True); logits=model(features.to(device), masks.to(device)); loss=criterion(logits, labels.to(device)); loss.backward(); torch.nn.utils.clip_grad_norm_(model.parameters(), float(config["gradient_clip_norm"])); optimizer.step(); losses.append(float(loss.item()))
        validation_loss, _ = evaluate(model, val_loader, device); scheduler.step(validation_loss)
        history.append({"epoch": epoch, "train_loss": float(np.mean(losses)), "validation_loss": validation_loss, "learning_rate": float(optimizer.param_groups[0]["lr"])})
        if validation_loss < best_loss - 1e-6:
            best_loss=validation_loss; best_epoch=epoch; stale=0
            torch.save({"model_state_dict": {k:v.detach().cpu() for k,v in model.state_dict().items()}, "condition": condition, "fold": fold_name, "seed": seed, "best_epoch": best_epoch, "initialization_sha256": initialization_hash}, checkpoint)
        else:
            stale += 1
            if stale >= int(config["early_stopping_patience"]): break
    try: state = torch.load(checkpoint, map_location="cpu", weights_only=False)
    except TypeError: state = torch.load(checkpoint, map_location="cpu")
    model.load_state_dict(state["model_state_dict"]); model.to(device)
    validation_loss, validation_windows = evaluate(model, val_loader, device); test_loss, test_windows = evaluate(model, test_loader, device)
    validation_trials = core.aggregate_trials(validation_windows); threshold = core.select_threshold(validation_trials["label"], validation_trials["probability"]); test_trials = core.aggregate_trials(test_windows)
    for frame in (validation_windows, validation_trials, test_windows, test_trials): frame["prediction"] = (frame["probability"] >= threshold).astype(int)
    metrics: dict[str, Any] = {"condition": condition, "fold": fold_name, "fold_index": fold_index + 1, "seed": seed, "device": str(device), "initialization_sha256": initialization_hash, "best_epoch": best_epoch, "epochs_completed": len(history), "best_validation_loss": best_loss, "final_validation_loss": validation_loss, "test_loss": test_loss, "validation_threshold": threshold, "elapsed_seconds": time.time()-started, "train_trajectory_count": len(split["train"]), "validation_trajectory_count": len(split["validation"]), "test_trajectory_count": len(split["test"]), "train_window_count": len(training), "validation_window_count": len(validation), "test_window_count": len(test), "batch_real_adl_windows": sampler.adl_count, "batch_real_fall_windows": sampler.real_count, "batch_synthetic_fall_windows": sampler.synthetic_count, "training_pool_counts": dict(Counter(source_kinds)), "scaler_fit_sources": scaler["fit_sources"]}
    for prefix, frame in (("validation_window", validation_windows), ("validation_trial", validation_trials), ("test_window", test_windows), ("test_trial", test_trials)):
        metrics.update({f"{prefix}_{key}": value for key, value in core.binary_metrics(frame["label"], frame["probability"], threshold).items()})
    metrics.update(core.activity_sensitivity(test_trials, threshold))
    fp_rate, fp_events, minutes = core.false_positive_events_per_adl_minute(test_windows, threshold); metrics.update(false_positive_events_per_adl_minute=fp_rate, false_positive_events=fp_events, test_adl_minutes=minutes)
    history_frame=pd.DataFrame(history); history_frame.to_csv(run_dir/"history.csv",index=False); validation_windows.to_csv(run_dir/"validation_window_predictions.csv",index=False); validation_trials.to_csv(run_dir/"validation_trial_predictions.csv",index=False); test_windows.to_csv(run_dir/"test_window_predictions.csv",index=False); test_trials.to_csv(run_dir/"test_trial_predictions.csv",index=False); plot_history(history_frame,run_dir/"training_history.png")
    core.write_json(run_dir/"run_configuration.json", {"condition":condition,"fold":fold_name,"seed":seed,"device":str(device),"initialization_sha256":initialization_hash,"batch_composition":sampler.batch_composition(),"split_groups":{k:sorted(v) for k,v in partitions.items()},"config":config}); core.write_json(metrics_path,metrics)
    print(f"[{condition}] {fold_name} seed={seed}: BA={metrics['test_trial_balanced_accuracy']:.4f}, F1={metrics['test_trial_f1']:.4f}, batch={sampler.batch_composition()}")
    return metrics


def refresh_summary(condition: str, output_root: Path) -> None:
    paths=sorted((output_root/condition).glob("fold_*/seed_*/metrics.json")); records=[json.loads(path.read_text()) for path in paths]
    if not records: return
    frame=pd.DataFrame(records).sort_values(["fold_index","seed"]); frame.to_csv(output_root/condition/"run_summary.csv",index=False)
    summary={"condition":condition,"completed_runs":len(frame),"folds":sorted(frame.fold.unique()),"seeds":sorted(int(x) for x in frame.seed.unique()),"batch_composition":{"real_adl":int(frame.batch_real_adl_windows.iloc[0]),"real_fall":int(frame.batch_real_fall_windows.iloc[0]),"synthetic_fall":int(frame.batch_synthetic_fall_windows.iloc[0])},"metrics":{}}
    for column in frame:
        if column.startswith("test_trial_") or column.startswith("test_A") or column=="false_positive_events_per_adl_minute":
            values=pd.to_numeric(frame[column],errors="coerce"); summary["metrics"][column]={"mean":float(values.mean()),"standard_deviation":float(values.std(ddof=1)),"minimum":float(values.min()),"maximum":float(values.max())}
    core.write_json(output_root/condition/"experiment_summary.json",summary)


def main(argv: Sequence[str] | None = None) -> None:
    parser=argparse.ArgumentParser(description="Train real-only and exact 60:40/40:60 fall-source conditions."); parser.add_argument("--config",type=Path,default=HERE/"config.json"); parser.add_argument("--device",default="auto",choices=["auto","cpu","mps","cuda"]); parser.add_argument("--conditions",nargs="*"); parser.add_argument("--folds",nargs="*"); parser.add_argument("--seeds",nargs="*"); parser.add_argument("--overwrite",action="store_true"); parser.add_argument("--max-epochs",type=int); parser.add_argument("--steps-per-epoch",type=int); args=parser.parse_args(argv)
    config=core.load_config(args.config)
    if args.max_epochs is not None: config["max_epochs"]=args.max_epochs
    if args.steps_per_epoch is not None: config["steps_per_epoch"]=args.steps_per_epoch
    conditions=args.conditions or list(config["conditions"]); folds=parse_int_list(args.folds) or list(range(1,len(config["folds"])+1)); seeds=parse_int_list(args.seeds) or [int(x) for x in config["seeds"]]
    unknown=set(conditions)-set(config["conditions"])
    if unknown: raise ValueError(f"Unknown conditions: {sorted(unknown)}")
    device=core.choose_device(args.device); rows=core.read_manifest(Path(config["data_root"])); print(f"Device={device}; conditions={conditions}; folds={folds}; seeds={seeds}")
    for condition in conditions:
        for fold in folds:
            for seed in seeds: run_one(condition,fold-1,seed,config,rows,device,args.overwrite)
        refresh_summary(condition,Path(config["output_root"]))


if __name__ == "__main__":
    main()
