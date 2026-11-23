from __future__ import annotations

import unittest

from quality_check import PHYSICS_METRICS, SHAPE_METRICS, apply_gate
from quality_metrics import boundary_metric_names, kinematic_distance_metric_names


class QualityPipelineTests(unittest.TestCase):
    def make_row(self, group: str, digest: str, value: float = 0.5) -> dict:
        row = {
            "synthetic_id": f"id-{digest}",
            "model_group": group,
            "fold": 1,
            "activity": "A14" if group == "rotation" else "A10",
            "generator_rank": 1,
            "seed_index": 1,
            "physics_weight": 0.01,
            "source_subject": "S01",
            "source_trial": "trial",
            "trajectory_sha256": digest,
            "direction_consistent": True,
        }
        for metric in SHAPE_METRICS + kinematic_distance_metric_names(group) + boundary_metric_names(group):
            row[metric] = value
        for metric in PHYSICS_METRICS[group]:
            row[f"real_physics_{metric}"] = 0.5
            row[f"synthetic_physics_{metric}"] = value
        return row

    def lookup(self, row: dict, threshold: float = 1.0) -> dict:
        group, fold, activity, rank = row["model_group"], row["fold"], row["activity"], row["generator_rank"]
        lookup = {}
        for metric in SHAPE_METRICS + kinematic_distance_metric_names(group):
            lookup[("distance", group, fold, activity, metric)] = threshold
        for metric in boundary_metric_names(group):
            lookup[("boundary", group, fold, activity, metric)] = threshold
        for metric in PHYSICS_METRICS[group]:
            lookup[("physics", group, fold, activity, rank, metric)] = threshold
        return lookup

    def test_complete_rotation_gate_passes(self):
        row = self.make_row("rotation", "unique")
        decisions = apply_gate(
            [row],
            self.lookup(row),
            {"minimum_kinematic_pass_fraction": 0.75, "reject_exact_duplicates": True},
        )
        self.assertTrue(decisions[0]["overall_quality_pass"])
        self.assertEqual(decisions[0]["physics_metrics_total"], 3)
        self.assertEqual(decisions[0]["kinematic_metrics_total"], 9)

    def test_exact_duplicates_are_rejected(self):
        first = self.make_row("planar", "same")
        second = {**first, "synthetic_id": "id-2", "generator_rank": 2}
        lookup = self.lookup(first)
        for metric in PHYSICS_METRICS["planar"]:
            lookup[("physics", "planar", 1, "A10", 2, metric)] = 1.0
        decisions = apply_gate(
            [first, second],
            lookup,
            {"minimum_kinematic_pass_fraction": 0.75, "reject_exact_duplicates": True},
        )
        self.assertFalse(decisions[0]["overall_quality_pass"])
        self.assertFalse(decisions[1]["duplicate_gate_pass"])


if __name__ == "__main__":
    unittest.main()

