from __future__ import annotations

import unittest

from ais_risk.regional_raster_dataset import RasterConfig, build_raster_samples, grid_indices_from_xy, local_xy_nm_from_row


class RegionalRasterDatasetTest(unittest.TestCase):
    def test_local_xy_and_grid_mapping(self) -> None:
        row = {
            "distance_nm": "1.0",
            "relative_bearing_deg": "0.0",
        }
        x_nm, y_nm = local_xy_nm_from_row(row)
        self.assertAlmostEqual(1.0, x_nm, places=6)
        self.assertAlmostEqual(0.0, y_nm, places=6)
        indices = grid_indices_from_xy(x_nm, y_nm, RasterConfig(half_width_nm=3.0, raster_size=6))
        self.assertIsNotNone(indices)

    def test_build_raster_samples_marks_focal_target(self) -> None:
        rows = [
            {
                "timestamp": "2026-03-16T09:00:00Z",
                "own_mmsi": "440000001",
                "target_mmsi": "440000101",
                "distance_nm": "1.0",
                "relative_bearing_deg": "0.0",
                "relative_speed_knots": "5.0",
                "tcpa_min": "4.0",
                "rule_score": "0.7",
                "label_future_conflict": "1",
            },
            {
                "timestamp": "2026-03-16T09:00:00Z",
                "own_mmsi": "440000001",
                "target_mmsi": "440000102",
                "distance_nm": "1.2",
                "relative_bearing_deg": "90.0",
                "relative_speed_knots": "3.0",
                "tcpa_min": "5.0",
                "rule_score": "0.2",
                "label_future_conflict": "0",
            },
        ]
        samples = build_raster_samples(rows, RasterConfig(half_width_nm=3.0, raster_size=16))
        self.assertEqual(2, len(samples))
        first = samples[0].image
        self.assertEqual((5, 16, 16), first.shape)
        self.assertEqual((5,), samples[0].scalar_features.shape)
        self.assertGreater(float(first[3].sum()), 0.0)
        self.assertGreater(float(first[4].sum()), 0.0)


if __name__ == "__main__":
    unittest.main()
