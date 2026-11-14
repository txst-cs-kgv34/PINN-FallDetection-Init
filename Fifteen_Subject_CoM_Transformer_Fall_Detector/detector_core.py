from __future__ import annotations

import csv
import json
import math
import os
import random
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path
from typing import Any, Iterable, Sequence

import numpy as np
import pandas as pd
import torch
from sklearn.metrics import (
    accuracy_score,
    average_precision_score,
    balanced_accuracy_score,
    confusion_matrix,
    f1_score,
    precision_score,
    recall_score,
    roc_auc_score,
)
from torch.utils.data import Dataset, Sampler


SCENARIO_SOURCES = {
    "real_fall_real_adl": {"real_adl", "real_fall"},
    "synthetic_fall_real_adl": {"real_adl", "synthetic_fall"},
    "real_synthetic_fall_real_adl": {
        "real_adl",
        "real_fall",
        "synthetic_fall",
    },
}

SCENARIO_ALIASES = {
    "real": "real_fall_real_adl",
    "synthetic": "synthetic_fall_real_adl",
    "syn": "synthetic_fall_real_adl",
    "combined": "real_synthetic_fall_real_adl",
    "real+synthetic": "real_synthetic_fall_real_adl",
}


def canonical_scenario(name: str) -> str:
    result = SCENARIO_ALIASES.get(name, name)
    if result not in SCENARIO_SOURCES:
        choices = ", ".join(SCENARIO_SOURCES)
        raise ValueError(f"Unknown scenario {name!r}. Choose one of: {choices}")
    return result


def load_config(path: Path) -> dict[str, Any]:
    path = path.resolve()
    config = json.loads(path.read_text())
    base = path.parent
    for key in ("data_root", "output_root"):
        value = Path(config[key]).expanduser()
        if not value.is_absolute():
            value = base / value
        config[key] = str(value.resolve())
    config["config_path"] = str(path)
    return config


def read_manifest(data_root: Path) -> list[dict[str, str]]:
    manifest = data_root / "dataset_manifest.csv"
    if not manifest.is_file():
        raise FileNotFoundError(
            f"Missing {manifest}. Run the data-preparation directory first."
        )
    with manifest.open(newline="", encoding="utf-8") as handle:
        rows = list(csv.DictReader(handle))
    required = {
        "sample_id",
        "label",
        "source_kind",
        "subject",
        "source_subject",
        "data_file",
        "sample_rate_hz",
        "duration_s",
        "quality_approved",
    }
    missing = required - set(rows[0] if rows else [])
    if missing:
        raise ValueError(f"Manifest is missing columns: {sorted(missing)}")
    return rows


def logical_group(row: dict[str, str], config: dict[str, Any]) -> str:
    subject = row.get("source_subject") or row["subject"]
    return config.get("paired_subject_groups", {}).get(subject, subject)


def fold_partitions(
    rows: Sequence[dict[str, str]], config: dict[str, Any], fold_index: int
) -> dict[str, set[str]]:
    folds = config["folds"]
    if not 0 <= fold_index < len(folds):
        raise IndexError(f"fold_index must be between 0 and {len(folds) - 1}")
    test = set(folds[fold_index]["test_groups"])
    validation = set(folds[(fold_index + 1) % len(folds)]["test_groups"])
    all_groups = {logical_group(row, config) for row in rows}
    train = all_groups - test - validation
    unknown = (test | validation) - all_groups
    if unknown:
        raise ValueError(f"Configured split groups not present in manifest: {sorted(unknown)}")
    if not train or test & validation or train & test or train & validation:
        raise ValueError("Train, validation, and test groups must be non-empty and disjoint")
    return {"train": train, "validation": validation, "test": test}


def _is_quality_approved(row: dict[str, str]) -> bool:
    if row["source_kind"] != "synthetic_fall":
        return True
    return row.get("quality_approved", "").strip().lower() in {"true", "1", "yes"}


def split_scenario_rows(
    rows: Sequence[dict[str, str]],
    config: dict[str, Any],
    scenario: str,
    fold_index: int,
) -> tuple[dict[str, list[dict[str, str]]], dict[str, set[str]]]:
    scenario = canonical_scenario(scenario)
    partitions = fold_partitions(rows, config, fold_index)
    selected: dict[str, list[dict[str, str]]] = {}
    for split, groups in partitions.items():
        allowed = SCENARIO_SOURCES[scenario] if split == "train" else {"real_adl", "real_fall"}
        selected[split] = [
            row
            for row in rows
            if logical_group(row, config) in groups
            and row["source_kind"] in allowed
            and _is_quality_approved(row)
        ]
        labels = {int(row["label"]) for row in selected[split]}
        if labels != {0, 1}:
            raise ValueError(
                f"{split} split for {scenario} must contain labels 0 and 1; got {labels}"
            )
    for split in ("validation", "test"):
        if any(row["source_kind"] == "synthetic_fall" for row in selected[split]):
            raise AssertionError("Synthetic data leaked into validation or test")
    return selected, partitions


def set_reproducible_seed(seed: int) -> None:
    random.seed(seed)
    np.random.seed(seed)
    torch.manual_seed(seed)
    if torch.cuda.is_available():
        torch.cuda.manual_seed_all(seed)


def choose_device(requested: str = "auto") -> torch.device:
    requested = requested.lower()
    if requested == "auto":
        if torch.cuda.is_available():
            requested = "cuda"
        elif getattr(torch.backends, "mps", None) and torch.backends.mps.is_available():
            requested = "mps"
        else:
            requested = "cpu"
    if requested == "cuda" and not torch.cuda.is_available():
        raise RuntimeError("CUDA was requested but is unavailable")
    if requested == "mps" and not (
        getattr(torch.backends, "mps", None) and torch.backends.mps.is_available()
    ):
        raise RuntimeError("MPS was requested but is unavailable")
    if requested not in {"cpu", "cuda", "mps"}:
        raise ValueError("device must be auto, cpu, cuda, or mps")
    return torch.device(requested)


@lru_cache(maxsize=1024)
def load_trajectory(path_string: str) -> tuple[np.ndarray, np.ndarray]:
    with np.load(path_string, allow_pickle=False) as archive:
        values = np.column_stack(
            [archive["theta_rad"].astype(np.float32), archive["x_m"].astype(np.float32)]
        )
        mask = archive["valid_mask"].astype(bool)
    if values.shape[0] != mask.shape[0] or values.shape[1] != 2:
        raise ValueError(f"Malformed trajectory: {path_string}")
    if not np.isfinite(values[mask]).all():
        raise ValueError(f"Non-finite valid values in {path_string}")
    return values, mask


def fit_training_scaler(
    rows: Sequence[dict[str, str]], data_root: Path
) -> dict[str, list[float]]:
    total = np.zeros(2, dtype=np.float64)
    squared = np.zeros(2, dtype=np.float64)
    count = 0
    for row in rows:
        values, mask = load_trajectory(str((data_root / row["data_file"]).resolve()))
        valid = values[mask]
        total += valid.sum(axis=0, dtype=np.float64)
        squared += np.square(valid, dtype=np.float64).sum(axis=0)
        count += len(valid)
    if count == 0:
        raise ValueError("No valid training frames available for normalization")
    mean = total / count
    variance = np.maximum(squared / count - mean * mean, 1e-12)
    return {
        "features": ["theta_rad", "x_m"],
        "mean": mean.tolist(),
        "std": np.sqrt(variance).tolist(),
        "valid_training_frames": int(count),
    }


@dataclass(frozen=True)
class WindowSpec:
    row_index: int
    start_frame: int
    end_frame: int


def window_starts(length: int, window_length: int, stride: int) -> list[int]:
    if length <= window_length:
        return [0]
    starts = list(range(0, length - window_length + 1, stride))
    last = length - window_length
    if starts[-1] != last:
        starts.append(last)
    return starts


class TrajectoryWindowDataset(Dataset):
    def __init__(
        self,
        rows: Sequence[dict[str, str]],
        data_root: Path,
        scaler: dict[str, list[float]],
        window_length: int,
        adl_stride: int,
        training: bool,
        max_train_adl_windows_per_trial: int | None,
    ) -> None:
        self.rows = list(rows)
        self.data_root = data_root
        self.window_length = int(window_length)
        self.mean = np.asarray(scaler["mean"], dtype=np.float32)
        self.std = np.asarray(scaler["std"], dtype=np.float32)
        self.specs: list[WindowSpec] = []
        for row_index, row in enumerate(self.rows):
            length = int(row["sample_count"])
            if int(row["label"]) == 1:
                starts = [max(0, length - self.window_length)]
            else:
                starts = window_starts(length, self.window_length, adl_stride)
                if training and max_train_adl_windows_per_trial:
                    cap = int(max_train_adl_windows_per_trial)
                    if len(starts) > cap:
                        indices = np.linspace(0, len(starts) - 1, cap).round().astype(int)
                        starts = [starts[index] for index in sorted(set(indices.tolist()))]
            for start in starts:
                self.specs.append(
                    WindowSpec(row_index, int(start), min(length, int(start) + self.window_length))
                )
        self.labels = [int(self.rows[spec.row_index]["label"]) for spec in self.specs]

    def __len__(self) -> int:
        return len(self.specs)

    def __getitem__(self, index: int):
        spec = self.specs[index]
        row = self.rows[spec.row_index]
        path = (self.data_root / row["data_file"]).resolve()
        values, source_mask = load_trajectory(str(path))
        segment = values[spec.start_frame : spec.end_frame]
        segment_mask = source_mask[spec.start_frame : spec.end_frame]
        output = np.zeros((self.window_length, 2), dtype=np.float32)
        mask = np.zeros(self.window_length, dtype=bool)
        pad_left = self.window_length - len(segment)
        output[pad_left:] = (segment - self.mean) / self.std
        mask[pad_left:] = segment_mask
        output[~mask] = 0.0
        metadata = {
            "sample_id": row["sample_id"],
            "subject": row["subject"],
            "source_subject": row.get("source_subject", row["subject"]),
            "source_kind": row["source_kind"],
            "activity_code": row.get("activity_code", ""),
            "start_frame": spec.start_frame,
            "end_frame": spec.end_frame,
            "duration_s": float(row["duration_s"]),
        }
        return (
            torch.from_numpy(output),
            torch.from_numpy(mask),
            torch.tensor(int(row["label"]), dtype=torch.float32),
            metadata,
        )


def collate_windows(batch):
    features, masks, labels, metadata = zip(*batch)
    return torch.stack(features), torch.stack(masks), torch.stack(labels), list(metadata)


class BalancedBatchSampler(Sampler[list[int]]):
    def __init__(self, labels: Sequence[int], batch_size: int, steps: int, seed: int):
        if batch_size < 2 or batch_size % 2:
            raise ValueError("batch_size must be an even integer of at least 2")
        self.positive = np.flatnonzero(np.asarray(labels) == 1)
        self.negative = np.flatnonzero(np.asarray(labels) == 0)
        if not len(self.positive) or not len(self.negative):
            raise ValueError("Balanced sampling requires both classes")
        self.batch_size = int(batch_size)
        self.steps = int(steps)
        self.seed = int(seed)
        self.epoch = 0

    def __iter__(self):
        rng = np.random.default_rng(self.seed + self.epoch)
        self.epoch += 1
        half = self.batch_size // 2
        for _ in range(self.steps):
            positive = rng.choice(self.positive, half, replace=len(self.positive) < half)
            negative = rng.choice(self.negative, half, replace=len(self.negative) < half)
            batch = np.concatenate([positive, negative])
            rng.shuffle(batch)
            yield batch.tolist()

    def __len__(self) -> int:
        return self.steps


def balanced_bce_loss(logits: torch.Tensor, labels: torch.Tensor) -> torch.Tensor:
    losses = torch.nn.functional.binary_cross_entropy_with_logits(
        logits, labels, reduction="none"
    )
    class_losses = [losses[labels == value].mean() for value in (0.0, 1.0) if (labels == value).any()]
    return torch.stack(class_losses).mean()


def prediction_frame(
    probabilities: Iterable[float],
    labels: Iterable[int],
    metadata: Sequence[dict[str, Any]],
) -> pd.DataFrame:
    records = []
    for probability, label, meta in zip(probabilities, labels, metadata):
        record = dict(meta)
        record["label"] = int(label)
        record["probability"] = float(probability)
        records.append(record)
    return pd.DataFrame.from_records(records)


def aggregate_trials(windows: pd.DataFrame) -> pd.DataFrame:
    if windows.empty:
        return windows.copy()
    aggregations = {
        "label": "first",
        "probability": "max",
        "subject": "first",
        "source_subject": "first",
        "source_kind": "first",
        "activity_code": "first",
        "duration_s": "first",
    }
    return windows.groupby("sample_id", as_index=False).agg(aggregations)


def select_validation_threshold(labels: Sequence[int], probabilities: Sequence[float]) -> float:
    labels_array = np.asarray(labels, dtype=int)
    probabilities_array = np.asarray(probabilities, dtype=float)
    unique = np.unique(probabilities_array)
    candidates = np.unique(np.concatenate(([0.0, 0.5, 1.0], unique)))
    best_score = -math.inf
    best_threshold = 0.5
    for threshold in candidates:
        predictions = (probabilities_array >= threshold).astype(int)
        score = balanced_accuracy_score(labels_array, predictions)
        if score > best_score + 1e-12 or (
            abs(score - best_score) <= 1e-12
            and abs(threshold - 0.5) < abs(best_threshold - 0.5)
        ):
            best_score = float(score)
            best_threshold = float(threshold)
    return best_threshold


def binary_metrics(
    labels: Sequence[int], probabilities: Sequence[float], threshold: float
) -> dict[str, float | int]:
    y_true = np.asarray(labels, dtype=int)
    scores = np.asarray(probabilities, dtype=float)
    y_pred = (scores >= threshold).astype(int)
    tn, fp, fn, tp = confusion_matrix(y_true, y_pred, labels=[0, 1]).ravel()
    result: dict[str, float | int] = {
        "accuracy": float(accuracy_score(y_true, y_pred)),
        "balanced_accuracy": float(balanced_accuracy_score(y_true, y_pred)),
        "sensitivity": float(recall_score(y_true, y_pred, zero_division=0)),
        "specificity": float(tn / (tn + fp)) if tn + fp else float("nan"),
        "precision": float(precision_score(y_true, y_pred, zero_division=0)),
        "f1": float(f1_score(y_true, y_pred, zero_division=0)),
        "tn": int(tn),
        "fp": int(fp),
        "fn": int(fn),
        "tp": int(tp),
    }
    result["auroc"] = (
        float(roc_auc_score(y_true, scores)) if len(np.unique(y_true)) == 2 else float("nan")
    )
    result["auprc"] = (
        float(average_precision_score(y_true, scores))
        if len(np.unique(y_true)) == 2
        else float("nan")
    )
    return result


def false_positive_events_per_adl_minute(
    windows: pd.DataFrame, threshold: float
) -> tuple[float, int, float]:
    adl = windows[windows["label"] == 0].copy()
    events = 0
    duration_s = 0.0
    for _, group in adl.groupby("sample_id"):
        ordered = group.sort_values("start_frame")
        duration_s += float(ordered["duration_s"].iloc[0])
        previous_positive = False
        for row in ordered.itertuples(index=False):
            positive = float(row.probability) >= threshold
            if positive and not previous_positive:
                events += 1
            previous_positive = positive
    minutes = duration_s / 60.0
    rate = events / minutes if minutes > 0 else float("nan")
    return float(rate), int(events), float(minutes)


def json_ready(value: Any) -> Any:
    if isinstance(value, dict):
        return {str(key): json_ready(item) for key, item in value.items()}
    if isinstance(value, (list, tuple, set)):
        return [json_ready(item) for item in value]
    if isinstance(value, Path):
        return str(value)
    if isinstance(value, (np.integer,)):
        return int(value)
    if isinstance(value, (np.floating,)):
        value = float(value)
    if isinstance(value, float) and not math.isfinite(value):
        return None
    return value


def write_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(json_ready(value), indent=2) + "\n", encoding="utf-8")

