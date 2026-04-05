from __future__ import annotations

import unittest

from ais_risk.geo import latlon_to_local_xy_m, local_xy_to_latlon


class GeoTest(unittest.TestCase):
    def test_local_xy_round_trip_matches_original_point(self) -> None:
        ref_lat = 35.05
        ref_lon = 129.05
        lat = 35.072
        lon = 129.078

        x_m, y_m = latlon_to_local_xy_m(ref_lat, ref_lon, lat, lon)
        recovered_lat, recovered_lon = local_xy_to_latlon(ref_lat, ref_lon, x_m, y_m)

        self.assertAlmostEqual(lat, recovered_lat, places=5)
        self.assertAlmostEqual(lon, recovered_lon, places=5)


if __name__ == "__main__":
    unittest.main()
