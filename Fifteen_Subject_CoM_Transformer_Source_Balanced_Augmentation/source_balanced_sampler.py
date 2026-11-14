from __future__ import annotations

from collections import defaultdict
from typing import Sequence

import numpy as np


class SourceBalancedBatchSampler:
    """Create 50% ADL batches and explicitly control real/synthetic fall shares."""

    def __init__(
        self,
        labels: Sequence[int],
        source_kinds: Sequence[str],
        subject_groups: Sequence[str],
        batch_size: int,
        steps: int,
        seed: int,
        real_parts: int = 1,
        synthetic_parts: int = 1,
        subject_balanced_within_source: bool = False,
    ) -> None:
        if len(labels) != len(source_kinds) or len(labels) != len(subject_groups):
            raise ValueError("labels, source_kinds, and subject_groups must have equal length")
        if batch_size < 4 or batch_size % 2:
            raise ValueError("batch_size must be an even integer of at least 4")
        if real_parts < 0 or synthetic_parts < 0 or real_parts + synthetic_parts <= 0:
            raise ValueError("fall source ratio parts must be non-negative with a positive sum")

        labels_array = np.asarray(labels, dtype=int)
        sources = np.asarray(source_kinds, dtype=object)
        self.pools = {
            "real_adl": np.flatnonzero(labels_array == 0),
            "real_fall": np.flatnonzero(
                (labels_array == 1) & (sources == "real_fall")
            ),
            "synthetic_fall": np.flatnonzero(
                (labels_array == 1) & (sources == "synthetic_fall")
            ),
        }
        for name, pool in self.pools.items():
            if not len(pool):
                raise ValueError(f"Training pool {name!r} is empty")

        self.batch_size = int(batch_size)
        self.steps = int(steps)
        self.seed = int(seed)
        self.epoch = 0
        self.subject_balanced = bool(subject_balanced_within_source)
        self.subject_groups = list(subject_groups)

        self.adl_per_batch = self.batch_size // 2
        fall_per_batch = self.batch_size - self.adl_per_batch
        ratio_total = real_parts + synthetic_parts
        self.real_falls_per_batch = int(round(fall_per_batch * real_parts / ratio_total))
        self.synthetic_falls_per_batch = fall_per_batch - self.real_falls_per_batch
        if self.real_falls_per_batch == 0 or self.synthetic_falls_per_batch == 0:
            raise ValueError(
                "This experiment requires both real and synthetic falls in every batch"
            )

        self.by_subject: dict[str, dict[str, np.ndarray]] = {}
        for source, pool in self.pools.items():
            grouped: dict[str, list[int]] = defaultdict(list)
            for index in pool:
                grouped[self.subject_groups[int(index)]].append(int(index))
            self.by_subject[source] = {
                subject: np.asarray(indices, dtype=int)
                for subject, indices in grouped.items()
            }

    def _draw(self, source: str, count: int, rng: np.random.Generator) -> np.ndarray:
        pool = self.pools[source]
        if not self.subject_balanced:
            return rng.choice(pool, count, replace=len(pool) < count)
        grouped = self.by_subject[source]
        subjects = sorted(grouped)
        selected = np.empty(count, dtype=int)
        for position in range(count):
            subject = subjects[int(rng.integers(0, len(subjects)))]
            subject_pool = grouped[subject]
            selected[position] = int(subject_pool[int(rng.integers(0, len(subject_pool)))])
        return selected

    def __iter__(self):
        rng = np.random.default_rng(self.seed + self.epoch)
        self.epoch += 1
        for _ in range(self.steps):
            batch = np.concatenate(
                [
                    self._draw("real_adl", self.adl_per_batch, rng),
                    self._draw("real_fall", self.real_falls_per_batch, rng),
                    self._draw(
                        "synthetic_fall", self.synthetic_falls_per_batch, rng
                    ),
                ]
            )
            rng.shuffle(batch)
            yield batch.tolist()

    def __len__(self) -> int:
        return self.steps

    def batch_composition(self) -> dict[str, int]:
        return {
            "real_adl": self.adl_per_batch,
            "real_fall": self.real_falls_per_batch,
            "synthetic_fall": self.synthetic_falls_per_batch,
            "total": self.batch_size,
        }

