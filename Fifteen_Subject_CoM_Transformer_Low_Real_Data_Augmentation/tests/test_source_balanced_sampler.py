import unittest
from collections import Counter

from source_balanced_sampler import SourceBalancedBatchSampler


class SourceBalancedSamplerTests(unittest.TestCase):
    def test_exact_quota_and_reproducibility(self):
        labels = [0] * 20 + [1] * 9 + [1] * 30
        sources = ["real_adl"] * 20 + ["real_fall"] * 9 + ["synthetic_fall"] * 30
        groups = [f"S{i % 5}" for i in range(len(labels))]
        kwargs = dict(
            labels=labels, source_kinds=sources, subject_groups=groups,
            batch_size=64, steps=3, seed=13,
        )
        first = list(SourceBalancedBatchSampler(**kwargs))
        second = list(SourceBalancedBatchSampler(**kwargs))
        self.assertEqual(first, second)
        for batch in first:
            self.assertEqual(
                Counter(sources[index] for index in batch),
                Counter({"real_adl": 32, "real_fall": 16, "synthetic_fall": 16}),
            )


if __name__ == "__main__":
    unittest.main()
