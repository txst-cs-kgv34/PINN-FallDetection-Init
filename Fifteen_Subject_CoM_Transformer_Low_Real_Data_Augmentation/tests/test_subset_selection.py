import unittest

from subset_selection import proportional_allocations, select_stratified_subset


class SubsetSelectionTests(unittest.TestCase):
    def setUp(self):
        sizes = {"A": 8, "B": 7, "C": 5, "D": 4}
        self.items = [
            {"sample_id": f"{group}_{index:02d}", "group": group}
            for group, size in sizes.items()
            for index in range(size)
        ]

    def choose(self, fraction):
        return select_stratified_subset(
            self.items, fraction, lambda row: row["group"],
            lambda row: row["sample_id"], "fixed-namespace",
        )

    def test_exact_nested_deterministic(self):
        chosen25 = self.choose(0.25)
        chosen50 = self.choose(0.50)
        self.assertEqual(len(chosen25), 6)
        self.assertEqual(len(chosen50), 12)
        self.assertLess(
            {row["sample_id"] for row in chosen25},
            {row["sample_id"] for row in chosen50},
        )
        self.assertEqual(chosen25, self.choose(0.25))

    def test_all_groups_represented(self):
        groups = {row["group"] for row in self.choose(0.25)}
        self.assertEqual(groups, {"A", "B", "C", "D"})

    def test_allocations_are_nested_for_every_target(self):
        sizes = {"A": 8, "B": 7, "C": 5, "D": 4}
        previous = proportional_allocations(sizes, 4)
        for target in range(5, sum(sizes.values()) + 1):
            current = proportional_allocations(sizes, target)
            self.assertTrue(all(current[key] >= previous[key] for key in sizes))
            self.assertEqual(sum(current.values()), target)
            previous = current


if __name__ == "__main__":
    unittest.main()
