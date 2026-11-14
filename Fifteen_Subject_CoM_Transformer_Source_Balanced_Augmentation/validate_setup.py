from __future__ import annotations

import argparse
from collections import Counter
from pathlib import Path
from typing import Sequence

import pandas as pd

from base_detector_imports import prepare_base_imports
from source_balanced_sampler import SourceBalancedBatchSampler


def main(argv: Sequence[str] | None = None) -> None:
    parser = argparse.ArgumentParser(
        description="Validate source-balanced inputs, splits, quotas, and prior results."
    )
    parser.add_argument(
        "--config", type=Path, default=Path(__file__).with_name("config.json")
    )
    parser.add_argument("--prior-output-root", type=Path)
    args = parser.parse_args(argv)

    config_path, raw_config, base_root = prepare_base_imports(args.config)
    import detector_core as base_core
    import train_scenario as base_train

    config = base_core.load_config(config_path)
    data_root = Path(config["data_root"])
    rows = base_core.read_manifest(data_root)
    counts = Counter(row["source_kind"] for row in rows)
    if set(counts) != {"real_adl", "real_fall", "synthetic_fall"}:
        raise ValueError(f"Unexpected manifest sources: {dict(counts)}")

    ratio = config["fall_source_ratio"]
    expected_composition = None
    for fold_index, fold in enumerate(config["folds"]):
        selected, partitions = base_core.split_scenario_rows(
            rows, config, "real_synthetic_fall_real_adl", fold_index
        )
        train_sources = Counter(row["source_kind"] for row in selected["train"])
        if set(train_sources) != {"real_adl", "real_fall", "synthetic_fall"}:
            raise ValueError(f"{fold['name']} lacks a training source: {train_sources}")
        for split in ("validation", "test"):
            sources = {row["source_kind"] for row in selected[split]}
            if "synthetic_fall" in sources:
                raise AssertionError(f"Synthetic leakage into {fold['name']} {split}")

        scaler = base_core.fit_training_scaler(selected["train"], data_root)
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
        sampler = SourceBalancedBatchSampler(
            labels=dataset.labels,
            source_kinds=source_kinds,
            subject_groups=subject_groups,
            batch_size=int(config["batch_size"]),
            steps=2,
            seed=0,
            real_parts=int(ratio["real"]),
            synthetic_parts=int(ratio["synthetic"]),
            subject_balanced_within_source=bool(
                config.get("subject_balanced_within_source", False)
            ),
        )
        expected_composition = sampler.batch_composition()
        for batch in sampler:
            observed = Counter(source_kinds[index] for index in batch)
            if dict(observed) != {
                "real_adl": expected_composition["real_adl"],
                "real_fall": expected_composition["real_fall"],
                "synthetic_fall": expected_composition["synthetic_fall"],
            }:
                raise AssertionError(
                    f"Unexpected batch quota in {fold['name']}: {dict(observed)}"
                )

    if args.prior_output_root:
        prior_root = args.prior_output_root.expanduser().resolve()
    else:
        prior_root = Path(raw_config["prior_output_root"]).expanduser()
        if not prior_root.is_absolute():
            prior_root = (config_path.parent / prior_root).resolve()
    prior_csv = prior_root / "comparison" / "combined_run_metrics.csv"
    if not prior_csv.is_file():
        raise FileNotFoundError(
            f"Missing prior results table: {prior_csv}. Copy the completed original "
            "detector outputs into its sibling directory or pass --prior-output-root."
        )
    prior = pd.read_csv(prior_csv)
    old_names = {
        "real_fall_real_adl",
        "synthetic_fall_real_adl",
        "real_synthetic_fall_real_adl",
    }
    prior = prior[prior["scenario"].isin(old_names)]
    settings = prior.groupby(["fold", "seed"])["scenario"].nunique()
    completed_settings = int((settings == 3).sum())
    expected_settings = len(config["folds"]) * len(config["seeds"])
    if completed_settings < expected_settings:
        raise ValueError(
            f"Prior results have {completed_settings}/{expected_settings} complete "
            "fold/seed settings across the three original scenarios."
        )

    print("Source-balanced experiment validation passed.")
    print(f"Base detector code: {base_root}")
    print(f"Data root: {data_root}")
    print(f"Manifest counts: {dict(counts)}")
    print(f"Batch composition: {expected_composition}")
    print(f"Prior runs available: {len(prior)} (expected 75)")
    print(f"New runs planned: {expected_settings} (5 folds x 5 seeds)")


if __name__ == "__main__":
    main()
