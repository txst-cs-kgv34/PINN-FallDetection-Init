from __future__ import annotations

import unittest
from collections import Counter
from pathlib import Path
import sys

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from source_balanced_sampler import SourceBalancedBatchSampler


class SourceBalancedSamplerTests(unittest.TestCase):
    def make_sampler(self, seed: int = 11) -> tuple[SourceBalancedBatchSampler, list[str]]:
        labels = np.asarray([0] * 100 + [1] * 30 + [1] * 90)
        sources = (
            ["real_adl"] * 100
            + ["real_fall"] * 30
            + ["synthetic_fall"] * 90
        )
        groups = [f"S{index % 5}" for index in range(len(labels))]
        sampler = SourceBalancedBatchSampler(
            labels=labels,
            source_kinds=sources,
            subject_groups=groups,
            batch_size=64,
            steps=8,
            seed=seed,
        )
        return sampler, sources

    def test_exact_quota_in_every_batch(self) -> None:
        sampler, sources = self.make_sampler()
        for batch in sampler:
            self.assertEqual(len(batch), 64)
            self.assertEqual(
                Counter(sources[index] for index in batch),
                Counter({"real_adl": 32, "real_fall": 16, "synthetic_fall": 16}),
            )

    def test_first_epoch_is_reproducible(self) -> None:
        first, _ = self.make_sampler(seed=4)
        second, _ = self.make_sampler(seed=4)
        self.assertEqual(list(first), list(second))

    def test_missing_source_is_rejected(self) -> None:
        with self.assertRaisesRegex(ValueError, "synthetic_fall"):
            SourceBalancedBatchSampler(
                labels=[0, 0, 1, 1],
                source_kinds=["real_adl", "real_adl", "real_fall", "real_fall"],
                subject_groups=["S1", "S2", "S1", "S2"],
                batch_size=4,
                steps=1,
                seed=1,
            )


if __name__ == "__main__":
    unittest.main()
