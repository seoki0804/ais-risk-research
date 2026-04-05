from __future__ import annotations

import unittest

from ais_risk.contours import extract_threshold_segments
from ais_risk.models import GridCellRisk


class ContourTest(unittest.TestCase):
    def test_single_cell_produces_four_boundary_segments(self) -> None:
        cells = (
            GridCellRisk(x_m=0.0, y_m=0.0, risk=0.8, label="danger"),
            GridCellRisk(x_m=100.0, y_m=0.0, risk=0.1, label="safe"),
            GridCellRisk(x_m=-100.0, y_m=0.0, risk=0.1, label="safe"),
            GridCellRisk(x_m=0.0, y_m=100.0, risk=0.1, label="safe"),
            GridCellRisk(x_m=0.0, y_m=-100.0, risk=0.1, label="safe"),
        )
        segments = extract_threshold_segments(cells, threshold=0.5, cell_size_m=100.0)
        self.assertEqual(len(segments), 4)

    def test_two_adjacent_high_cells_remove_shared_edge(self) -> None:
        cells = (
            GridCellRisk(x_m=0.0, y_m=0.0, risk=0.8, label="danger"),
            GridCellRisk(x_m=100.0, y_m=0.0, risk=0.7, label="danger"),
            GridCellRisk(x_m=-100.0, y_m=0.0, risk=0.1, label="safe"),
            GridCellRisk(x_m=200.0, y_m=0.0, risk=0.1, label="safe"),
            GridCellRisk(x_m=0.0, y_m=100.0, risk=0.1, label="safe"),
            GridCellRisk(x_m=100.0, y_m=100.0, risk=0.1, label="safe"),
            GridCellRisk(x_m=0.0, y_m=-100.0, risk=0.1, label="safe"),
            GridCellRisk(x_m=100.0, y_m=-100.0, risk=0.1, label="safe"),
        )
        segments = extract_threshold_segments(cells, threshold=0.5, cell_size_m=100.0)
        self.assertEqual(len(segments), 6)


if __name__ == "__main__":
    unittest.main()
