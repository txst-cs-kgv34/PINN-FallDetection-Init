from __future__ import annotations

from collections import defaultdict
from typing import Sequence

import numpy as np


class SourceRatioBatchSampler:
    """Create 50% ADL batches with an epoch-controlled fall-source ratio.

    A batch of 64 contains 32 ADL and 32 fall windows. Ratios such as 40:60
    cannot be represented exactly by 32 integer fall slots in one batch. We
    therefore alternate the two nearest integer quotas and make the epoch total
    equal to the nearest attainable target, without changing batch size or the
    number of optimizer steps.
    """

    def __init__(
        self,
        labels: Sequence[int],
        source_kinds: Sequence[str],
        subject_groups: Sequence[str],
        batch_size: int,
        steps: int,
        seed: int,
        real_parts: int,
        synthetic_parts: int,
        subject_balanced_within_source: bool = False,
    ) -> None:
        if len(labels) != len(source_kinds) or len(labels) != len(subject_groups):
            raise ValueError("labels, source_kinds, and subject_groups must have equal length")
        if batch_size < 4 or batch_size % 2:
            raise ValueError("batch_size must be an even integer of at least 4")
        if steps < 1:
            raise ValueError("steps must be positive")
        if real_parts <= 0 or synthetic_parts <= 0:
            raise ValueError("both real and synthetic fall ratio parts must be positive")

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
        self.real_parts = int(real_parts)
        self.synthetic_parts = int(synthetic_parts)

        self.adl_per_batch = self.batch_size // 2
        self.falls_per_batch = self.batch_size - self.adl_per_batch
        ratio_total = self.real_parts + self.synthetic_parts
        self.target_real_fraction = self.real_parts / ratio_total
        self.target_synthetic_fraction = self.synthetic_parts / ratio_total

        total_fall_slots = self.falls_per_batch * self.steps
        self.real_falls_per_epoch = int(round(total_fall_slots * self.target_real_fraction))
        self.synthetic_falls_per_epoch = total_fall_slots - self.real_falls_per_epoch
        if self.real_falls_per_epoch < self.steps or self.synthetic_falls_per_epoch < self.steps:
            raise ValueError("ratio leaves a source with fewer than one fall slot per batch")

        low = self.real_falls_per_epoch // self.steps
        high_count = self.real_falls_per_epoch - low * self.steps
        self._real_quota_template = np.asarray(
            [low + 1] * high_count + [low] * (self.steps - high_count),
            dtype=int,
        )
        if self._real_quota_template.min() <= 0:
            raise ValueError("every batch must contain at least one real fall")
        if self._real_quota_template.max() >= self.falls_per_batch:
            raise ValueError("every batch must contain at least one synthetic fall")

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
        real_quotas = self._real_quota_template.copy()
        rng.shuffle(real_quotas)
        for real_count in real_quotas:
            synthetic_count = self.falls_per_batch - int(real_count)
            batch = np.concatenate(
                [
                    self._draw("real_adl", self.adl_per_batch, rng),
                    self._draw("real_fall", int(real_count), rng),
                    self._draw("synthetic_fall", synthetic_count, rng),
                ]
            )
            rng.shuffle(batch)
            yield batch.tolist()

    def __len__(self) -> int:
        return self.steps

    def quota_summary(self) -> dict[str, int | float]:
        total_falls = self.real_falls_per_epoch + self.synthetic_falls_per_epoch
        synthetic_quotas = self.falls_per_batch - self._real_quota_template
        return {
            "real_adl_per_batch": self.adl_per_batch,
            "falls_per_batch": self.falls_per_batch,
            "real_fall_per_batch_min": int(self._real_quota_template.min()),
            "real_fall_per_batch_max": int(self._real_quota_template.max()),
            "synthetic_fall_per_batch_min": int(synthetic_quotas.min()),
            "synthetic_fall_per_batch_max": int(synthetic_quotas.max()),
            "real_fall_per_epoch": self.real_falls_per_epoch,
            "synthetic_fall_per_epoch": self.synthetic_falls_per_epoch,
            "effective_real_fraction": self.real_falls_per_epoch / total_falls,
            "effective_synthetic_fraction": self.synthetic_falls_per_epoch / total_falls,
            "total_per_batch": self.batch_size,
            "steps_per_epoch": self.steps,
        }
