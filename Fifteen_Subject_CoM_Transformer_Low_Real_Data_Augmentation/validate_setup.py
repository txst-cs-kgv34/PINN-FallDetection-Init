from __future__ import annotations

import argparse
import math
from collections import Counter
from pathlib import Path
from typing import Sequence

import pandas as pd

from base_detector_imports import prepare_base_imports
from subset_selection import select_stratified_subset


def resolve(config_path: Path, value: str) -> Path:
    path = Path(value).expanduser()
    return (path if path.is_absolute() else config_path.parent / path).resolve()


def main(argv: Sequence[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description="Validate low-real-data inputs and subset policy.")
    parser.add_argument("--config", type=Path, default=Path(__file__).with_name("config.json"))
    parser.add_argument("--prior-csv", type=Path)
    args = parser.parse_args(argv)

    config_path, raw, base_root = prepare_base_imports(args.config)
    import detector_core as base_core

    config = base_core.load_config(config_path)
    data_root = Path(config["data_root"])
    rows = base_core.read_manifest(data_root)
    source_counts = Counter(row["source_kind"] for row in rows)
    if set(source_counts) != {"real_adl", "real_fall", "synthetic_fall"}:
        raise ValueError(f"Unexpected manifest sources: {dict(source_counts)}")

    fold_records = []
    for fold_index, fold in enumerate(config["folds"]):
        selected, partitions = base_core.split_scenario_rows(
            rows, config, "real_synthetic_fall_real_adl", fold_index
        )
        real_falls = [row for row in selected["train"] if row["source_kind"] == "real_fall"]
        namespace = f"{config['subset_seed']}|{fold['name']}|low-real-data"
        choose = lambda fraction: select_stratified_subset(
            real_falls,
            fraction=fraction,
            group_key=lambda row: base_core.logical_group(row, config),
            item_id=lambda row: row["sample_id"],
            namespace=namespace,
        )
        chosen25, chosen50 = choose(0.25), choose(0.50)
        ids25 = {row["sample_id"] for row in chosen25}
        ids50 = {row["sample_id"] for row in chosen50}
        if not ids25 < ids50:
            raise AssertionError(f"{fold['name']}: 25% subset must be a proper subset of 50%")
        training_ids = {row["sample_id"] for row in real_falls}
        if not ids50 <= training_ids:
            raise AssertionError(f"{fold['name']}: subset contains non-training data")
        train_groups = {base_core.logical_group(row, config) for row in real_falls}
        for fraction, chosen in ((0.25, chosen25), (0.50, chosen50)):
            target = max(
                len(train_groups), int(math.floor(fraction * len(real_falls) + 0.5))
            )
            if len(chosen) != target:
                raise AssertionError(
                    f"{fold['name']} {fraction}: selected {len(chosen)}, expected {target}"
                )
            groups = {base_core.logical_group(row, config) for row in chosen}
            if groups != train_groups:
                raise AssertionError(f"{fold['name']} {fraction}: missing training subject group")
        for split in ("validation", "test"):
            if any(row["source_kind"] == "synthetic_fall" for row in selected[split]):
                raise AssertionError(f"Synthetic leakage into {fold['name']} {split}")
        fold_records.append((fold["name"], len(real_falls), len(chosen25), len(chosen50), len(train_groups)))

    prior_path = args.prior_csv.expanduser().resolve() if args.prior_csv else resolve(config_path, raw["prior_comparison_csv"])
    if not prior_path.is_file():
        raise FileNotFoundError(f"Missing frozen reference table: {prior_path}")
    prior = pd.read_csv(prior_path)
    references = prior[prior["scenario"].isin(["real_fall_real_adl", "source_balanced_1to1"])]
    counts = references.groupby(["fold", "seed"])["scenario"].nunique()
    expected = len(config["folds"]) * len(config["seeds"])
    if int((counts == 2).sum()) < expected:
        raise ValueError("Frozen references do not contain all 25 paired fold/seed settings")

    print("Low-real-data experiment validation passed.")
    print(f"Base detector code: {base_root}")
    print(f"Data root: {data_root}")
    print(f"Manifest source counts: {dict(source_counts)}")
    for name, available, count25, count50, groups in fold_records:
        print(f"{name}: available real falls={available}, selected 25%={count25}, selected 50%={count50}, training groups={groups}")
    print(f"Frozen reference runs available: {len(references)} (expected 50)")
    print("New runs planned: 100 (4 conditions x 5 folds x 5 seeds)")


if __name__ == "__main__":
    main()
