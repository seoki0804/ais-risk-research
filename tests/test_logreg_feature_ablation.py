from __future__ import annotations

import csv
import json

from ais_risk.logreg_feature_ablation import _feature_dict_with_drops, run_logreg_feature_ablation


def _write_pairwise_csv(path):
    fieldnames = [
        "timestamp",
        "own_mmsi",
        "target_mmsi",
        "own_segment_id",
        "target_segment_id",
        "own_vessel_type",
        "target_vessel_type",
        "own_is_interpolated",
        "target_is_interpolated",
        "local_target_count",
        "distance_nm",
        "dcpa_nm",
        "tcpa_min",
        "relative_speed_knots",
        "relative_bearing_deg",
        "bearing_abs_deg",
        "course_difference_deg",
        "encounter_type",
        "rule_score",
        "rule_component_distance",
        "rule_component_dcpa",
        "rule_component_tcpa",
        "rule_component_bearing",
        "rule_component_relspeed",
        "rule_component_encounter",
        "rule_component_density",
        "future_min_distance_nm",
        "future_time_to_min_min",
        "future_points_used",
        "label_future_conflict",
    ]
    rows = []
    owns = [
        ("100", "cargo", "tanker"),
        ("200", "cargo", "passenger"),
        ("300", "cargo", "tug"),
    ]
    for own_index, (own_mmsi, own_type, positive_target_type) in enumerate(owns):
        for i in range(20):
            label = 1 if i < 10 else 0
            timestamp = f"2023-08-01T00:{own_index:02d}:{i:02d}Z"
            target_type = positive_target_type if label else "service"
            rows.append(
                {
                    "timestamp": timestamp,
                    "own_mmsi": own_mmsi,
                    "target_mmsi": f"{own_index}{i:03d}",
                    "own_segment_id": f"{own_mmsi}-seg",
                    "target_segment_id": f"target-{i}",
                    "own_vessel_type": own_type,
                    "target_vessel_type": target_type,
                    "own_is_interpolated": "0",
                    "target_is_interpolated": "0",
                    "local_target_count": "1",
                    "distance_nm": "0.2" if label else "3.0",
                    "dcpa_nm": "0.1" if label else "2.0",
                    "tcpa_min": "2.0" if label else "15.0",
                    "relative_speed_knots": "6.0" if label else "1.0",
                    "relative_bearing_deg": "20.0" if label else "150.0",
                    "bearing_abs_deg": "20.0" if label else "150.0",
                    "course_difference_deg": "15.0" if label else "100.0",
                    "encounter_type": "crossing" if label else "diverging",
                    "rule_score": "0.8" if label else "0.1",
                    "rule_component_distance": "0.1" if label else "0.01",
                    "rule_component_dcpa": "0.1" if label else "0.01",
                    "rule_component_tcpa": "0.1" if label else "0.01",
                    "rule_component_bearing": "0.1" if label else "0.01",
                    "rule_component_relspeed": "0.1" if label else "0.01",
                    "rule_component_encounter": "0.1" if label else "0.01",
                    "rule_component_density": "0.1" if label else "0.01",
                    "future_min_distance_nm": "0.1" if label else "2.5",
                    "future_time_to_min_min": "3.0" if label else "10.0",
                    "future_points_used": "4",
                    "label_future_conflict": str(label),
                }
            )
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def test_feature_dict_with_drops_excludes_future_only_support_fields():
    payload = _feature_dict_with_drops(
        {
            "distance_nm": "1.0",
            "dcpa_nm": "0.5",
            "tcpa_min": "2.0",
            "relative_speed_knots": "10.0",
            "relative_bearing_deg": "15.0",
            "bearing_abs_deg": "15.0",
            "course_difference_deg": "20.0",
            "local_target_count": "3",
            "rule_score": "0.8",
            "rule_component_distance": "0.1",
            "rule_component_dcpa": "0.1",
            "rule_component_tcpa": "0.1",
            "rule_component_bearing": "0.1",
            "rule_component_relspeed": "0.1",
            "rule_component_encounter": "0.1",
            "rule_component_density": "0.1",
            "future_points_used": "6",
            "encounter_type": "crossing",
            "own_vessel_type": "cargo",
            "target_vessel_type": "tanker",
            "own_is_interpolated": "0",
            "target_is_interpolated": "1",
        },
        dropped_fields=set(),
    )
    assert "future_points_used" not in payload


def test_run_logreg_feature_ablation_writes_summary(tmp_path):
    dataset_path = tmp_path / "pairwise.csv"
    _write_pairwise_csv(dataset_path)
    output_prefix = tmp_path / "ablation"

    summary = run_logreg_feature_ablation(
        input_path=dataset_path,
        output_prefix=output_prefix,
        variants=[
            ("baseline", set()),
            ("drop_target_vessel_type", {"target_vessel_type"}),
        ],
        split_strategy="own_ship",
        random_seed=42,
    )

    summary_json = tmp_path / "ablation_summary.json"
    summary_md = tmp_path / "ablation_summary.md"
    assert summary_json.exists()
    assert summary_md.exists()
    payload = json.loads(summary_json.read_text(encoding="utf-8"))
    assert payload["split_strategy"] == "own_ship"
    assert len(payload["variants"]) == 2
    assert payload["variants"][0]["variant_name"] == "baseline"
    assert payload["variants"][1]["dropped_fields"] == ["target_vessel_type"]
    assert payload["variants"][0]["metrics"]["f1"] >= 0.0
    assert payload["variants"][1]["feature_count"] < payload["variants"][0]["feature_count"]
