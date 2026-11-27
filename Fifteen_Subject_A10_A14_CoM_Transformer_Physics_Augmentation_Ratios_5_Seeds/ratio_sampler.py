from __future__ import annotations

from collections import defaultdict
from typing import Sequence

import numpy as np


FALL_ACTIVITIES = ("A10", "A11", "A12", "A13", "A14")


def balanced_activity_counts(total: int, offset: int = 0) -> dict[str, int]:
    """Distribute a source quota across five activities with at most one-count spread."""
    base, remainder = divmod(int(total), len(FALL_ACTIVITIES))
    result = {activity: base for activity in FALL_ACTIVITIES}
    for index in range(remainder):
        result[FALL_ACTIVITIES[(offset + index) % len(FALL_ACTIVITIES)]] += 1
    return result


class ActivityFamilyBatchSampler:
    """50% ADL batches with exact fall-source quotas and family-safe synthetic draws."""

    def __init__(self, labels: Sequence[int], source_kinds: Sequence[str], activities: Sequence[str], family_ids: Sequence[str], batch_size: int, steps: int, seed: int, real_falls: int, synthetic_falls: int) -> None:
        lengths = {len(labels), len(source_kinds), len(activities), len(family_ids)}
        if len(lengths) != 1:
            raise ValueError("Sampler metadata lengths differ")
        if batch_size <= 0 or batch_size % 2:
            raise ValueError("batch_size must be a positive even integer")
        self.adl_count = batch_size // 2
        if real_falls + synthetic_falls != batch_size - self.adl_count:
            raise ValueError("Fall quotas must fill exactly half of each batch")
        if real_falls < 0 or synthetic_falls < 0:
            raise ValueError("Fall quotas cannot be negative")
        labels_array = np.asarray(labels, dtype=int)
        sources = np.asarray(source_kinds, dtype=object)
        activities_array = np.asarray(activities, dtype=object)
        self.adl_pool = np.flatnonzero((labels_array == 0) & (sources == "real_adl"))
        self.real_by_activity: dict[str, np.ndarray] = {}
        self.synthetic_by_activity_family: dict[str, dict[str, np.ndarray]] = {}
        for activity in FALL_ACTIVITIES:
            self.real_by_activity[activity] = np.flatnonzero((labels_array == 1) & (sources == "real_fall") & (activities_array == activity))
            grouped: dict[str, list[int]] = defaultdict(list)
            for index in np.flatnonzero((labels_array == 1) & (sources == "synthetic_fall") & (activities_array == activity)):
                family = str(family_ids[int(index)])
                if not family:
                    raise ValueError("Synthetic window is missing synthetic_family_id")
                grouped[family].append(int(index))
            self.synthetic_by_activity_family[activity] = {key: np.asarray(value, dtype=int) for key, value in grouped.items()}
        if not len(self.adl_pool):
            raise ValueError("ADL training pool is empty")
        if real_falls and any(not len(self.real_by_activity[a]) for a in FALL_ACTIVITIES):
            raise ValueError("Every fall activity needs real training samples")
        if synthetic_falls and any(not self.synthetic_by_activity_family[a] for a in FALL_ACTIVITIES):
            raise ValueError("Every fall activity needs synthetic training families")
        self.batch_size = int(batch_size)
        self.steps = int(steps)
        self.seed = int(seed)
        self.real_count = int(real_falls)
        self.synthetic_count = int(synthetic_falls)
        self.epoch = 0

    @staticmethod
    def _choice(pool: np.ndarray, count: int, rng: np.random.Generator) -> np.ndarray:
        if count == 0:
            return np.empty(0, dtype=int)
        return rng.choice(pool, size=count, replace=len(pool) < count).astype(int)

    def _draw_real(self, counts: dict[str, int], rng: np.random.Generator) -> np.ndarray:
        return np.concatenate([self._choice(self.real_by_activity[a], counts[a], rng) for a in FALL_ACTIVITIES]) if sum(counts.values()) else np.empty(0, dtype=int)

    def _draw_synthetic(self, counts: dict[str, int], rng: np.random.Generator) -> np.ndarray:
        selected: list[int] = []
        for activity in FALL_ACTIVITIES:
            count = counts[activity]
            if not count:
                continue
            grouped = self.synthetic_by_activity_family[activity]
            families = np.asarray(sorted(grouped), dtype=object)
            chosen = rng.choice(families, size=count, replace=len(families) < count)
            for family in chosen:
                variants = grouped[str(family)]
                selected.append(int(variants[int(rng.integers(0, len(variants)))]))
        return np.asarray(selected, dtype=int)

    def __iter__(self):
        rng = np.random.default_rng(self.seed + self.epoch * 100003)
        epoch_offset = self.epoch
        self.epoch += 1
        for step in range(self.steps):
            offset = (epoch_offset + step) % len(FALL_ACTIVITIES)
            real_counts = balanced_activity_counts(self.real_count, offset)
            synthetic_counts = balanced_activity_counts(self.synthetic_count, offset + 2)
            batch = np.concatenate([
                self._choice(self.adl_pool, self.adl_count, rng),
                self._draw_real(real_counts, rng),
                self._draw_synthetic(synthetic_counts, rng),
            ])
            if len(batch) != self.batch_size:
                raise AssertionError("Sampler constructed an incomplete batch")
            rng.shuffle(batch)
            yield batch.tolist()

    def __len__(self) -> int:
        return self.steps

    def batch_composition(self) -> dict[str, int]:
        return {"real_adl": self.adl_count, "real_fall": self.real_count, "synthetic_fall": self.synthetic_count, "total": self.batch_size}
