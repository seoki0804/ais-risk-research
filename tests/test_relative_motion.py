from __future__ import annotations

import unittest

from ais_risk.models import VesselState
from ais_risk.relative_motion import compute_relative_kinematics


class RelativeMotionTest(unittest.TestCase):
    def test_head_on_case_has_positive_tcpa(self) -> None:
        own = VesselState(mmsi="1", lat=35.0000, lon=129.0000, sog=12.0, cog=0.0, heading=0.0)
        target = VesselState(mmsi="2", lat=35.0200, lon=129.0000, sog=12.0, cog=180.0, heading=180.0)

        kin = compute_relative_kinematics(own, target)

        self.assertEqual(kin.encounter_type, "head_on")
        self.assertGreater(kin.tcpa_min, 0.0)
        self.assertLess(kin.dcpa_nm, 0.2)


if __name__ == "__main__":
    unittest.main()
