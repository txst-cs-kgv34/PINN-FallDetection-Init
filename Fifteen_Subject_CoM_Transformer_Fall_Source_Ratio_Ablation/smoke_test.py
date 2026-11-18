from __future__ import annotations

from collections import Counter
from pathlib import Path

import numpy as np
import torch

from base_detector_imports import prepare_base_imports
from source_ratio_sampler import SourceRatioBatchSampler


def check_sampler(real: int, synthetic: int, expected_real: int) -> None:
    labels = np.asarray([0] * 80 + [1] * 40 + [1] * 100)
    sources = ["real_adl"] * 80 + ["real_fall"] * 40 + ["synthetic_fall"] * 100
    groups = [f"S{index % 10:02d}" for index in range(len(labels))]
    sampler = SourceRatioBatchSampler(
        labels=labels,
        source_kinds=sources,
        subject_groups=groups,
        batch_size=64,
        steps=32,
        seed=7,
        real_parts=real,
        synthetic_parts=synthetic,
    )
    totals = Counter()
    for batch in sampler:
        observed = Counter(sources[index] for index in batch)
        assert observed["real_adl"] == 32
        assert observed["real_fall"] + observed["synthetic_fall"] == 32
        totals.update(observed)
    assert totals["real_fall"] == expected_real
    assert totals["synthetic_fall"] == 1024 - expected_real


def main() -> None:
    check_sampler(40, 60, 410)
    check_sampler(60, 40, 614)

    config_path, _, _ = prepare_base_imports(
        Path(__file__).with_name("config.json")
    )
    import detector_core as base_core
    import train_scenario as base_train

    config = base_core.load_config(config_path)
    model = base_train.build_model(config)
    features = torch.randn(4, int(config["window_length"]), 2)
    masks = torch.ones(4, int(config["window_length"]), dtype=torch.bool)
    labels_tensor = torch.tensor([0.0, 1.0, 0.0, 1.0])
    logits = model(features, masks)
    loss = torch.nn.BCEWithLogitsLoss()(logits, labels_tensor)
    loss.backward()
    assert logits.shape == (4,)
    assert torch.isfinite(loss)
    print("Smoke test passed; no experiment files were created.")


if __name__ == "__main__":
    main()
