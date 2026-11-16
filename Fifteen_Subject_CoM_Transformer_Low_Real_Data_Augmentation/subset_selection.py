from __future__ import annotations

import hashlib
import math
from collections import defaultdict
from typing import Callable, Sequence, TypeVar


T = TypeVar("T")


def _stable_key(namespace: str, group: str, item_id: str) -> str:
    value = f"{namespace}|{group}|{item_id}".encode("utf-8")
    return hashlib.sha256(value).hexdigest()


def proportional_allocations(
    group_sizes: dict[str, int], target: int
) -> dict[str, int]:
    """Nested deterministic apportionment with at least one item per group."""
    if not group_sizes or any(size <= 0 for size in group_sizes.values()):
        raise ValueError("group_sizes must contain positive counts")
    total = sum(group_sizes.values())
    target = max(len(group_sizes), min(int(target), total))
    allocations = {group: 1 for group in sorted(group_sizes)}
    while sum(allocations.values()) < target:
        eligible = [
            group
            for group in sorted(group_sizes)
            if allocations[group] < group_sizes[group]
        ]
        if not eligible:
            break
        group = max(
            eligible,
            key=lambda name: (
                group_sizes[name] / (allocations[name] + 1),
                -sorted(group_sizes).index(name),
            ),
        )
        allocations[group] += 1
    return allocations


def select_stratified_subset(
    items: Sequence[T],
    fraction: float,
    group_key: Callable[[T], str],
    item_id: Callable[[T], str],
    namespace: str,
) -> list[T]:
    if not 0 < fraction <= 1:
        raise ValueError("fraction must be in (0, 1]")
    grouped: dict[str, list[T]] = defaultdict(list)
    for item in items:
        grouped[str(group_key(item))].append(item)
    if not grouped:
        raise ValueError("Cannot select from an empty item collection")
    target = int(math.floor(fraction * len(items) + 0.5))
    allocations = proportional_allocations(
        {group: len(values) for group, values in grouped.items()}, target
    )
    selected: list[T] = []
    for group in sorted(grouped):
        ranked = sorted(
            grouped[group],
            key=lambda item: (
                _stable_key(namespace, group, item_id(item)),
                item_id(item),
            ),
        )
        selected.extend(ranked[: allocations[group]])
    return sorted(selected, key=item_id)


def selection_digest(items: Sequence[dict[str, str]]) -> str:
    identifiers = "\n".join(sorted(row["sample_id"] for row in items))
    return hashlib.sha256(identifiers.encode("utf-8")).hexdigest()
