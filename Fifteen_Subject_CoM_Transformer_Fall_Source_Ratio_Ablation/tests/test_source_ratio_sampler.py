from __future__ import annotations

import unittest
from collections import Counter
from pathlib import Path
import sys

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from source_ratio_sampler import SourceRatioBatchSampler


class SourceRatioSamplerTests(unittest.TestCase):
    def make_sampler(
        self, real: int, synthetic: int, seed: int = 11
    ) -> tuple[SourceRatioBatchSampler, list[str]]:
        labels = np.asarray([0] * 100 + [1] * 30 + [1] * 90)
        sources = (
            ["real_adl"] * 100
            + ["real_fall"] * 30
            + ["synthetic_fall"] * 90
        )
        groups = [f"S{index % 5}" for index in range(len(labels))]
        sampler = SourceRatioBatchSampler(
            labels=labels,
            source_kinds=sources,
            subject_groups=groups,
            batch_size=64,
            steps=32,
            seed=seed,
            real_parts=real,
            synthetic_parts=synthetic,
        )
        return sampler, sources

    def assert_ratio(self, real: int, synthetic: int, expected_real: int) -> None:
        sampler, sources = self.make_sampler(real, synthetic)
        epoch_counts = Counter()
        real_batch_counts = set()
        for batch in sampler:
            observed = Counter(sources[index] for index in batch)
            self.assertEqual(len(batch), 64)
            self.assertEqual(observed["real_adl"], 32)
            self.assertEqual(observed["real_fall"] + observed["synthetic_fall"], 32)
            real_batch_counts.add(observed["real_fall"])
            epoch_counts.update(observed)
        self.assertEqual(epoch_counts["real_adl"], 32 * 32)
        self.assertEqual(epoch_counts["real_fall"], expected_real)
        self.assertEqual(epoch_counts["synthetic_fall"], 32 * 32 - expected_real)
        expected_near = {expected_real // 32, (expected_real + 31) // 32}
        self.assertEqual(real_batch_counts, expected_near)

    def test_40_to_60_epoch_quota(self) -> None:
        self.assert_ratio(40, 60, 410)

    def test_60_to_40_epoch_quota(self) -> None:
        self.assert_ratio(60, 40, 614)

    def test_first_epoch_is_reproducible(self) -> None:
        first, _ = self.make_sampler(40, 60, seed=4)
        second, _ = self.make_sampler(40, 60, seed=4)
        self.assertEqual(list(first), list(second))

    def test_missing_source_is_rejected(self) -> None:
        with self.assertRaisesRegex(ValueError, "synthetic_fall"):
            SourceRatioBatchSampler(
                labels=[0, 0, 1, 1],
                source_kinds=["real_adl", "real_adl", "real_fall", "real_fall"],
                subject_groups=["S1", "S2", "S1", "S2"],
                batch_size=4,
                steps=1,
                seed=1,
                real_parts=40,
                synthetic_parts=60,
            )


if __name__ == "__main__":
    unittest.main()
