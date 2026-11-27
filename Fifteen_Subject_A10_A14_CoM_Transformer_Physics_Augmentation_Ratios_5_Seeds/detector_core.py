from __future__ import annotations

import csv
import json
import math
import random
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path
from typing import Any, Iterable, Sequence

import numpy as np
import pandas as pd
import torch
from sklearn.metrics import accuracy_score, average_precision_score, balanced_accuracy_score, confusion_matrix, f1_score, precision_score, recall_score, roc_auc_score
from torch.utils.data import Dataset


FALL_ACTIVITIES = ("A10", "A11", "A12", "A13", "A14")


def load_config(path: Path) -> dict[str, Any]:
    source = path.expanduser().resolve()
    config = json.loads(source.read_text(encoding="utf-8"))
    for key in ("data_root", "output_root"):
        value = Path(config[key]).expanduser()
        config[key] = str((value if value.is_absolute() else source.parent / value).resolve())
    config["config_path"] = str(source)
    return config


def read_manifest(data_root: Path) -> list[dict[str, str]]:
    path = data_root / "dataset_manifest.csv"
    with path.open(newline="", encoding="utf-8") as handle:
        rows = list(csv.DictReader(handle))
    required = {"sample_id", "label", "source_kind", "source_subject", "split_group", "activity_code", "data_file", "sample_count"}
    if not rows or (missing := required - set(rows[0])):
        raise ValueError(f"Manifest is empty or missing columns: {sorted(missing) if rows else sorted(required)}")
    return rows


def logical_group(row: dict[str, str], config: dict[str, Any]) -> str:
    subject = row.get("split_group") or row.get("source_subject") or row["subject"]
    return config.get("paired_subject_groups", {}).get(subject, subject)


def fold_partitions(rows: Sequence[dict[str, str]], config: dict[str, Any], fold_index: int) -> dict[str, set[str]]:
    folds = config["folds"]
    test = set(folds[fold_index]["test_groups"])
    validation = set(folds[(fold_index + 1) % len(folds)]["test_groups"])
    all_groups = {logical_group(row, config) for row in rows}
    train = all_groups - test - validation
    if (test | validation) - all_groups or not train or test & validation:
        raise ValueError("Invalid subject partitions")
    return {"train": train, "validation": validation, "test": test}


def split_rows(rows: Sequence[dict[str, str]], config: dict[str, Any], fold_index: int, include_synthetic_train: bool) -> tuple[dict[str, list[dict[str, str]]], dict[str, set[str]]]:
    partitions = fold_partitions(rows, config, fold_index)
    selected: dict[str, list[dict[str, str]]] = {}
    for split, groups in partitions.items():
        allowed = {"real_adl", "real_fall", "synthetic_fall"} if split == "train" and include_synthetic_train else {"real_adl", "real_fall"}
        selected[split] = [row for row in rows if logical_group(row, config) in groups and row["source_kind"] in allowed and (row["source_kind"] != "synthetic_fall" or row.get("quality_approved", "").lower() == "true")]
        if {int(row["label"]) for row in selected[split]} != {0, 1}:
            raise ValueError(f"{split} lacks both detector classes")
    if any(row["source_kind"] == "synthetic_fall" for split in ("validation", "test") for row in selected[split]):
        raise AssertionError("Synthetic validation/test leakage")
    return selected, partitions


def set_seed(seed: int) -> None:
    random.seed(seed); np.random.seed(seed); torch.manual_seed(seed)
    if torch.cuda.is_available():
        torch.cuda.manual_seed_all(seed)


def choose_device(requested: str) -> torch.device:
    if requested == "auto":
        requested = "cuda" if torch.cuda.is_available() else "mps" if getattr(torch.backends, "mps", None) and torch.backends.mps.is_available() else "cpu"
    if requested == "cuda" and not torch.cuda.is_available():
        raise RuntimeError("CUDA unavailable")
    if requested == "mps" and not (getattr(torch.backends, "mps", None) and torch.backends.mps.is_available()):
        raise RuntimeError("MPS unavailable")
    return torch.device(requested)


@lru_cache(maxsize=4096)
def load_trajectory(path_string: str) -> tuple[np.ndarray, np.ndarray]:
    with np.load(path_string, allow_pickle=False) as data:
        values = np.column_stack([data["theta_rad"].astype(np.float32), data["x_m"].astype(np.float32)])
        mask = data["valid_mask"].astype(bool)
        if "observed_mask" in data.files:
            mask &= data["observed_mask"].astype(bool)
    if values.shape != (len(mask), 2) or not np.isfinite(values[mask]).all():
        raise ValueError(f"Malformed trajectory: {path_string}")
    return values, mask


def fit_real_training_scaler(rows: Sequence[dict[str, str]], data_root: Path) -> dict[str, Any]:
    real_rows = [row for row in rows if row["source_kind"] in {"real_adl", "real_fall"}]
    total = np.zeros(2, dtype=np.float64); squared = np.zeros(2, dtype=np.float64); count = 0
    for row in real_rows:
        values, mask = load_trajectory(str((data_root / row["data_file"]).resolve()))
        valid = values[mask]
        total += valid.sum(axis=0, dtype=np.float64)
        squared += np.square(valid, dtype=np.float64).sum(axis=0)
        count += len(valid)
    mean = total / count
    variance = np.maximum(squared / count - mean * mean, 1e-12)
    return {"features": ["theta_rad", "x_m"], "mean": mean.tolist(), "std": np.sqrt(variance).tolist(), "valid_real_training_frames": count, "fit_sources": ["real_adl", "real_fall"]}


@dataclass(frozen=True)
class WindowSpec:
    row_index: int
    start: int
    end: int


def window_starts(length: int, width: int, stride: int) -> list[int]:
    if length <= width:
        return [0]
    starts = list(range(0, length - width + 1, stride))
    if starts[-1] != length - width:
        starts.append(length - width)
    return starts


class TrajectoryWindowDataset(Dataset):
    def __init__(self, rows: Sequence[dict[str, str]], data_root: Path, scaler: dict[str, Any], window_length: int, adl_stride: int, training: bool, max_train_adl_windows_per_trial: int | None) -> None:
        self.rows = list(rows); self.data_root = data_root; self.window_length = int(window_length)
        self.mean = np.asarray(scaler["mean"], dtype=np.float32); self.std = np.asarray(scaler["std"], dtype=np.float32)
        self.specs: list[WindowSpec] = []
        for row_index, row in enumerate(self.rows):
            length = int(row["sample_count"])
            starts = [max(0, length - self.window_length)] if int(row["label"]) == 1 else window_starts(length, self.window_length, adl_stride)
            if int(row["label"]) == 0 and training and max_train_adl_windows_per_trial and len(starts) > max_train_adl_windows_per_trial:
                positions = np.linspace(0, len(starts) - 1, max_train_adl_windows_per_trial).round().astype(int)
                starts = [starts[index] for index in sorted(set(positions.tolist()))]
            self.specs.extend(WindowSpec(row_index, start, min(length, start + self.window_length)) for start in starts)
        self.labels = [int(self.rows[spec.row_index]["label"]) for spec in self.specs]

    def __len__(self) -> int:
        return len(self.specs)

    def __getitem__(self, index: int):
        spec = self.specs[index]; row = self.rows[spec.row_index]
        values, source_mask = load_trajectory(str((self.data_root / row["data_file"]).resolve()))
        segment = values[spec.start:spec.end]; segment_mask = source_mask[spec.start:spec.end]
        output = np.zeros((self.window_length, 2), dtype=np.float32); mask = np.zeros(self.window_length, dtype=bool)
        left = self.window_length - len(segment)
        output[left:] = (segment - self.mean) / self.std; mask[left:] = segment_mask; output[~mask] = 0.0
        metadata = {"sample_id": row["sample_id"], "subject": row["subject"], "source_subject": row["source_subject"], "source_kind": row["source_kind"], "activity_code": row["activity_code"], "synthetic_family_id": row.get("synthetic_family_id", ""), "start_frame": spec.start, "end_frame": spec.end, "duration_s": float(row["duration_s"])}
        return torch.from_numpy(output), torch.from_numpy(mask), torch.tensor(int(row["label"]), dtype=torch.float32), metadata


def collate_windows(batch):
    features, masks, labels, metadata = zip(*batch)
    return torch.stack(features), torch.stack(masks), torch.stack(labels), list(metadata)


def prediction_frame(probabilities: Iterable[float], labels: Iterable[int], metadata: Sequence[dict[str, Any]]) -> pd.DataFrame:
    records = []
    for probability, label, item in zip(probabilities, labels, metadata):
        row = dict(item); row.update(label=int(label), probability=float(probability)); records.append(row)
    return pd.DataFrame.from_records(records)


def aggregate_trials(windows: pd.DataFrame) -> pd.DataFrame:
    return windows.groupby("sample_id", as_index=False).agg({"label": "first", "probability": "max", "subject": "first", "source_subject": "first", "source_kind": "first", "activity_code": "first", "duration_s": "first"})


def select_threshold(labels: Sequence[int], probabilities: Sequence[float]) -> float:
    y = np.asarray(labels, dtype=int); scores = np.asarray(probabilities, dtype=float)
    best = (-math.inf, 0.5)
    for threshold in np.unique(np.concatenate(([0.0, 0.5, 1.0], scores))):
        value = float(balanced_accuracy_score(y, scores >= threshold))
        if value > best[0] + 1e-12 or (abs(value - best[0]) <= 1e-12 and abs(threshold - 0.5) < abs(best[1] - 0.5)):
            best = value, float(threshold)
    return best[1]


def binary_metrics(labels: Sequence[int], probabilities: Sequence[float], threshold: float) -> dict[str, float | int]:
    y = np.asarray(labels, dtype=int); scores = np.asarray(probabilities, dtype=float); pred = (scores >= threshold).astype(int)
    tn, fp, fn, tp = confusion_matrix(y, pred, labels=[0, 1]).ravel()
    return {"accuracy": float(accuracy_score(y, pred)), "balanced_accuracy": float(balanced_accuracy_score(y, pred)), "sensitivity": float(recall_score(y, pred, zero_division=0)), "specificity": float(tn / (tn + fp)) if tn + fp else float("nan"), "precision": float(precision_score(y, pred, zero_division=0)), "f1": float(f1_score(y, pred, zero_division=0)), "auroc": float(roc_auc_score(y, scores)) if len(np.unique(y)) == 2 else float("nan"), "auprc": float(average_precision_score(y, scores)) if len(np.unique(y)) == 2 else float("nan"), "tn": int(tn), "fp": int(fp), "fn": int(fn), "tp": int(tp)}


def activity_sensitivity(trials: pd.DataFrame, threshold: float) -> dict[str, float | int]:
    result: dict[str, float | int] = {}
    for activity in FALL_ACTIVITIES:
        subset = trials[(trials["label"] == 1) & (trials["activity_code"] == activity)]
        result[f"test_{activity}_fall_count"] = int(len(subset))
        result[f"test_{activity}_sensitivity"] = float(np.mean(subset["probability"].to_numpy() >= threshold)) if len(subset) else float("nan")
    return result


def false_positive_events_per_adl_minute(windows: pd.DataFrame, threshold: float) -> tuple[float, int, float]:
    events = 0; duration_s = 0.0
    for _, group in windows[windows["label"] == 0].groupby("sample_id"):
        ordered = group.sort_values("start_frame"); duration_s += float(ordered["duration_s"].iloc[0]); previous = False
        for probability in ordered["probability"]:
            positive = float(probability) >= threshold
            if positive and not previous: events += 1
            previous = positive
    minutes = duration_s / 60.0
    return float(events / minutes if minutes else float("nan")), int(events), float(minutes)


def json_ready(value: Any) -> Any:
    if isinstance(value, dict): return {str(k): json_ready(v) for k, v in value.items()}
    if isinstance(value, (list, tuple, set)): return [json_ready(v) for v in value]
    if isinstance(value, Path): return str(value)
    if isinstance(value, np.integer): return int(value)
    if isinstance(value, np.floating): value = float(value)
    if isinstance(value, float) and not math.isfinite(value): return None
    return value


def write_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(json_ready(value), indent=2) + "\n", encoding="utf-8")
