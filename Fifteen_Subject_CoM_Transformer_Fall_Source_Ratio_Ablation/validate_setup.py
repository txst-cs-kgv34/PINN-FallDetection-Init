from __future__ import annotations

import argparse
import json
from collections import Counter
from pathlib import Path
from typing import Any, Sequence

import pandas as pd

from base_detector_imports import prepare_base_imports
from source_ratio_sampler import SourceRatioBatchSampler


def resolve(config_path: Path, value: str) -> Path:
    path = Path(value).expanduser()
    return path.resolve() if path.is_absolute() else (config_path.parent / path).resolve()


def make_experiment_config(base: dict[str, Any], experiment: dict[str, Any]) -> dict[str, Any]:
    config = dict(base)
    config["experiment_name"] = str(experiment["experiment_name"])
    config["fall_source_ratio"] = dict(experiment["fall_source_ratio"])
    return config


def count_1to1_runs(root: Path) -> int:
    return len(list((root / "source_balanced_1to1").glob("fold_*/seed_*/metrics.json")))


def main(argv: Sequence[str] | None = None) -> None:
    parser = argparse.ArgumentParser(
        description="Validate data, splits, ratio quotas, and frozen reference results."
    )
    parser.add_argument(
        "--config", type=Path, default=Path(__file__).with_name("config.json")
    )
    parser.add_argument("--prior-output-root", type=Path)
    parser.add_argument("--balanced-1to1-output-root", type=Path)
    args = parser.parse_args(argv)

    config_path, raw_config, base_root = prepare_base_imports(args.config)
    import detector_core as base_core
    import train_scenario as base_train

    base_config = base_core.load_config(config_path)
    rows = base_core.read_manifest(Path(base_config["data_root"]))
    counts = Counter(row["source_kind"] for row in rows)
    if set(counts) != {"real_adl", "real_fall", "synthetic_fall"}:
        raise ValueError(f"Unexpected manifest sources: {dict(counts)}")

    summaries: dict[str, dict[str, int | float]] = {}
    for experiment in raw_config["experiments"]:
        config = make_experiment_config(base_config, experiment)
        ratio = config["fall_source_ratio"]
        fold_summary = None
        for fold_index, fold in enumerate(config["folds"]):
            selected, _ = base_core.split_scenario_rows(
                rows, config, "real_synthetic_fall_real_adl", fold_index
            )
            train_sources = Counter(row["source_kind"] for row in selected["train"])
            if set(train_sources) != {"real_adl", "real_fall", "synthetic_fall"}:
                raise ValueError(f"{fold['name']} lacks a training source: {train_sources}")
            for split in ("validation", "test"):
                sources = {row["source_kind"] for row in selected[split]}
                if "synthetic_fall" in sources:
                    raise AssertionError(
                        f"Synthetic leakage into {fold['name']} {split}"
                    )

            scaler = base_core.fit_training_scaler(
                selected["train"], Path(config["data_root"])
            )
            dataset = base_train.make_dataset(
                selected["train"], config, scaler, training=True
            )
            source_kinds = [
                dataset.rows[spec.row_index]["source_kind"] for spec in dataset.specs
            ]
            subject_groups = [
                base_core.logical_group(dataset.rows[spec.row_index], config)
                for spec in dataset.specs
            ]
            sampler = SourceRatioBatchSampler(
                labels=dataset.labels,
                source_kinds=source_kinds,
                subject_groups=subject_groups,
                batch_size=int(config["batch_size"]),
                steps=int(config["steps_per_epoch"]),
                seed=0,
                real_parts=int(ratio["real"]),
                synthetic_parts=int(ratio["synthetic"]),
                subject_balanced_within_source=bool(
                    config.get("subject_balanced_within_source", False)
                ),
            )
            fold_summary = sampler.quota_summary()
            totals = Counter()
            for batch in sampler:
                observed = Counter(source_kinds[index] for index in batch)
                if observed["real_adl"] != fold_summary["real_adl_per_batch"]:
                    raise AssertionError(f"Unexpected ADL quota in {fold['name']}")
                if (
                    observed["real_fall"] + observed["synthetic_fall"]
                    != fold_summary["falls_per_batch"]
                ):
                    raise AssertionError(f"Unexpected fall quota in {fold['name']}")
                totals.update(observed)
            if totals["real_fall"] != fold_summary["real_fall_per_epoch"]:
                raise AssertionError(f"Unexpected real-fall epoch quota in {fold['name']}")
            if totals["synthetic_fall"] != fold_summary["synthetic_fall_per_epoch"]:
                raise AssertionError(
                    f"Unexpected synthetic-fall epoch quota in {fold['name']}"
                )
        assert fold_summary is not None
        summaries[str(config["experiment_name"])] = fold_summary

    prior_root = (
        args.prior_output_root.expanduser().resolve()
        if args.prior_output_root
        else resolve(config_path, raw_config["prior_output_root"])
    )
    prior_csv = prior_root / "comparison" / "combined_run_metrics.csv"
    if not prior_csv.is_file():
        raise FileNotFoundError(f"Missing original detector results: {prior_csv}")
    prior = pd.read_csv(prior_csv)
    original = {
        "real_fall_real_adl",
        "synthetic_fall_real_adl",
        "real_synthetic_fall_real_adl",
    }
    prior = prior[prior["scenario"].isin(original)]
    expected_settings = len(base_config["folds"]) * len(base_config["seeds"])
    complete = prior.groupby(["fold", "seed"])["scenario"].nunique()
    if int((complete == 3).sum()) < expected_settings:
        raise ValueError("Original detector results are incomplete")

    balanced_root = (
        args.balanced_1to1_output_root.expanduser().resolve()
        if args.balanced_1to1_output_root
        else resolve(config_path, raw_config["balanced_1to1_output_root"])
    )
    balanced_runs = count_1to1_runs(balanced_root)
    if balanced_runs < expected_settings:
        raise ValueError(
            f"Balanced 1:1 reference has {balanced_runs}/{expected_settings} runs"
        )

    print("Fall-source ratio experiment validation passed.")
    print(f"Base detector code: {base_root}")
    print(f"Manifest counts: {dict(counts)}")
    for name, summary in summaries.items():
        print(f"{name}: {json.dumps(summary, sort_keys=True)}")
    print(f"Frozen original runs available: {len(prior)} (expected 75)")
    print(f"Frozen balanced 1:1 runs available: {balanced_runs} (expected 25)")
    print(f"New runs planned: {2 * expected_settings} (2 ratios x 5 folds x 5 seeds)")


if __name__ == "__main__":
    main()
