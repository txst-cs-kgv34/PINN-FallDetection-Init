from __future__ import annotations

import unittest

import numpy as np
import torch

from detector_core import select_validation_threshold, window_starts
from model import CoMTemporalTransformer


class DetectorTests(unittest.TestCase):
    def test_model_shape_and_padding_mask(self):
        model = CoMTemporalTransformer(
            window_length=64,
            d_model=8,
            nhead=2,
            num_layers=1,
            dim_feedforward=16,
            dropout=0.0,
        )
        features = torch.randn(3, 64, 2)
        mask = torch.ones(3, 64, dtype=torch.bool)
        mask[0, :10] = False
        logits = model(features, mask)
        self.assertEqual(tuple(logits.shape), (3,))
        self.assertTrue(torch.isfinite(logits).all())

    def test_window_starts_cover_last_frame(self):
        self.assertEqual(window_starts(40, 64, 32), [0])
        self.assertEqual(window_starts(64, 64, 32), [0])
        self.assertEqual(window_starts(100, 64, 32), [0, 32, 36])

    def test_validation_threshold_uses_probabilities(self):
        labels = [0, 0, 1, 1]
        probabilities = [0.1, 0.4, 0.6, 0.9]
        threshold = select_validation_threshold(labels, probabilities)
        predictions = (np.asarray(probabilities) >= threshold).astype(int)
        self.assertListEqual(predictions.tolist(), labels)


if __name__ == "__main__":
    unittest.main()

