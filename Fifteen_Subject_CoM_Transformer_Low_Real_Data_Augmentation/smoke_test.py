from __future__ import annotations

from collections import Counter
from pathlib import Path

import numpy as np
import torch

from base_detector_imports import prepare_base_imports
from source_balanced_sampler import SourceBalancedBatchSampler
from subset_selection import select_stratified_subset


def main() -> None:
    items = [
        {"sample_id": f"S{subject:02d}_F{trial:02d}", "group": f"S{subject:02d}"}
        for subject in range(1, 7)
        for trial in range(1, 9)
    ]
    choose = lambda fraction: select_stratified_subset(
        items, fraction, lambda row: row["group"], lambda row: row["sample_id"], "smoke"
    )
    ids25 = {row["sample_id"] for row in choose(0.25)}
    ids50 = {row["sample_id"] for row in choose(0.50)}
    assert len(ids25) == 12 and len(ids50) == 24 and ids25 < ids50

    labels = np.asarray([0] * 80 + [1] * 40 + [1] * 100)
    sources = ["real_adl"] * 80 + ["real_fall"] * 40 + ["synthetic_fall"] * 100
    sampler = SourceBalancedBatchSampler(
        labels=labels, source_kinds=sources,
        subject_groups=[f"S{i % 10:02d}" for i in range(len(labels))],
        batch_size=64, steps=3, seed=7,
    )
    for batch in sampler:
        assert Counter(sources[index] for index in batch) == Counter(
            {"real_adl": 32, "real_fall": 16, "synthetic_fall": 16}
        )

    config_path, _, _ = prepare_base_imports(Path(__file__).with_name("config.json"))
    import detector_core as base_core
    import train_scenario as base_train

    config = base_core.load_config(config_path)
    model = base_train.build_model(config)
    features = torch.randn(4, int(config["window_length"]), 2)
    masks = torch.ones(4, int(config["window_length"]), dtype=torch.bool)
    targets = torch.tensor([0.0, 1.0, 0.0, 1.0])
    logits = model(features, masks)
    loss = torch.nn.BCEWithLogitsLoss()(logits, targets)
    loss.backward()
    assert logits.shape == (4,) and torch.isfinite(loss)
    print("Smoke test passed on CPU; no experiment files were created.")


if __name__ == "__main__":
    main()
