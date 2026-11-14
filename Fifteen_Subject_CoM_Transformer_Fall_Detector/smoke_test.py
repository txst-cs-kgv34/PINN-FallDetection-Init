from __future__ import annotations

import csv
import json
import tempfile
from pathlib import Path

import numpy as np

from compare_scenarios import main as compare_main
from train_scenario import main as train_main


def write_trial(
    path: Path,
    label: int,
    seed: int,
    length: int = 80,
) -> None:
    rng = np.random.default_rng(seed)
    time_s = np.arange(length, dtype=np.float32) / 30.0
    if label:
        progress = np.linspace(0.0, 1.0, length, dtype=np.float32)
        theta = 1.1 * progress**2 + rng.normal(0, 0.015, length)
        x = 0.75 * progress**2 + rng.normal(0, 0.01, length)
    else:
        theta = 0.04 * np.sin(2 * np.pi * 0.8 * time_s) + rng.normal(0, 0.01, length)
        x = 0.03 * np.sin(2 * np.pi * 0.5 * time_s) + rng.normal(0, 0.008, length)
    np.savez_compressed(
        path,
        time_s=time_s,
        theta_rad=theta.astype(np.float32),
        x_m=x.astype(np.float32),
        valid_mask=np.ones(length, dtype=np.uint8),
        label=np.int8(label),
        activity_id=np.int16(11 if label else 8),
        sample_rate_hz=np.float32(30.0),
        mass_kg=np.float32(70.0),
        height_m=np.float32(1.72),
    )


def create_fixture(root: Path) -> tuple[Path, Path]:
    data_root = root / "prepared" / "outputs"
    trials = data_root / "trials"
    trials.mkdir(parents=True)
    rows = []
    subjects = [f"S{index:02d}" for index in range(1, 7)]
    counter = 0
    for subject in subjects:
        for source_kind, label, repetitions in (
            ("real_adl", 0, 2),
            ("real_fall", 1, 1),
            ("synthetic_fall", 1, 2),
        ):
            source_dir = trials / source_kind
            source_dir.mkdir(exist_ok=True)
            for repetition in range(repetitions):
                counter += 1
                sample_id = f"{source_kind}_{subject}_{repetition}"
                relative = Path("trials") / source_kind / f"{sample_id}.npz"
                write_trial(data_root / relative, label, counter)
                rows.append(
                    {
                        "sample_id": sample_id,
                        "label": label,
                        "class_name": "fall" if label else "adl",
                        "source_kind": source_kind,
                        "is_synthetic": source_kind == "synthetic_fall",
                        "subject": subject,
                        "source_subject": subject,
                        "split_group": subject,
                        "activity_id": 11 if label else 8,
                        "activity_code": "A11" if label else "A08",
                        "activity_name": "Front fall" if label else "Walking",
                        "trial": sample_id,
                        "sample_rate_hz": 30.0,
                        "sample_count": 80,
                        "duration_s": 79 / 30,
                        "data_file": str(relative),
                        "quality_approved": "True" if source_kind == "synthetic_fall" else "",
                    }
                )
    fieldnames = list(rows[0])
    with (data_root / "dataset_manifest.csv").open("w", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)
    config = {
        "data_root": str(data_root),
        "output_root": str(root / "detector_outputs"),
        "sample_rate_hz": 30.0,
        "window_length": 64,
        "adl_stride": 32,
        "max_train_adl_windows_per_trial": 2,
        "batch_size": 8,
        "steps_per_epoch": 2,
        "max_epochs": 2,
        "early_stopping_patience": 2,
        "learning_rate": 0.001,
        "weight_decay": 0.0001,
        "gradient_clip_norm": 1.0,
        "d_model": 8,
        "nhead": 2,
        "num_transformer_layers": 1,
        "dim_feedforward": 16,
        "dropout": 0.1,
        "seeds": [7],
        "num_workers": 0,
        "paired_subject_groups": {},
        "folds": [
            {"name": "fold_01", "test_groups": ["S01", "S02"]},
            {"name": "fold_02", "test_groups": ["S03", "S04"]},
            {"name": "fold_03", "test_groups": ["S05", "S06"]},
        ],
        "comparison_metrics": [
            "test_trial_balanced_accuracy",
            "test_trial_sensitivity",
            "test_trial_specificity",
            "test_trial_f1",
            "test_trial_auroc",
            "test_trial_auprc",
            "false_positive_events_per_adl_minute",
        ],
    }
    config_path = root / "smoke_config.json"
    config_path.write_text(json.dumps(config, indent=2))
    return config_path, Path(config["output_root"])


def main() -> None:
    with tempfile.TemporaryDirectory(prefix="com_detector_smoke_") as temporary:
        config_path, output_root = create_fixture(Path(temporary))
        for scenario in ("real", "synthetic", "combined"):
            train_main(
                [
                    "--scenario",
                    scenario,
                    "--config",
                    str(config_path),
                    "--device",
                    "cpu",
                    "--folds",
                    "1",
                    "--seeds",
                    "7",
                    "--overwrite",
                ]
            )
        compare_main(["--config", str(config_path)])
        required = [
            output_root / "comparison" / "scenario_summary.csv",
            output_root / "comparison" / "paired_wilcoxon_holm.csv",
            output_root / "comparison" / "COMPARISON.md",
        ]
        missing = [str(path) for path in required if not path.is_file()]
        if missing:
            raise AssertionError(f"Smoke test did not produce: {missing}")
    print("End-to-end smoke test passed on CPU.")


if __name__ == "__main__":
    main()

