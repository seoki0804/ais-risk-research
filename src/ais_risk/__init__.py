"""AIS risk model benchmarking package (tracked pipeline subset)."""

from __future__ import annotations

import importlib
from typing import Any

__all__ = [
    "run_pairwise_benchmark",
    "run_pairwise_transfer_benchmark",
    "run_calibration_evaluation",
    "run_data_algorithm_quality_review",
    "run_error_taxonomy_for_recommended_models",
    "run_out_of_time_recommendation_check",
    "run_regional_raster_cnn_benchmark",
    "run_reliability_report_for_recommended_models",
    "run_reviewer_quality_audit",
    "run_significance_report",
    "run_threshold_robustness_report",
    "run_transfer_override_seed_stress_test",
    "run_unseen_area_evidence_report",
    "run_cross_region_transfer_recommendation_check",
    "run_all_supported_models",
    "run_all_models_seed_sweep",
]

_EXPORT_MAP = {
    "run_pairwise_benchmark": (".benchmark", "run_pairwise_benchmark"),
    "run_pairwise_transfer_benchmark": (".benchmark", "run_pairwise_transfer_benchmark"),
    "run_calibration_evaluation": (".calibration_eval", "run_calibration_evaluation"),
    "run_data_algorithm_quality_review": (
        ".data_algorithm_quality_review",
        "run_data_algorithm_quality_review",
    ),
    "run_error_taxonomy_for_recommended_models": (
        ".error_taxonomy_report",
        "run_error_taxonomy_for_recommended_models",
    ),
    "run_out_of_time_recommendation_check": (
        ".out_of_time_eval",
        "run_out_of_time_recommendation_check",
    ),
    "run_regional_raster_cnn_benchmark": (
        ".regional_raster_cnn",
        "run_regional_raster_cnn_benchmark",
    ),
    "run_reliability_report_for_recommended_models": (
        ".reliability_report",
        "run_reliability_report_for_recommended_models",
    ),
    "run_reviewer_quality_audit": (".reviewer_quality_audit", "run_reviewer_quality_audit"),
    "run_significance_report": (".significance_report", "run_significance_report"),
    "run_threshold_robustness_report": (
        ".threshold_robustness_report",
        "run_threshold_robustness_report",
    ),
    "run_transfer_override_seed_stress_test": (
        ".transfer_override_seed_stress_test",
        "run_transfer_override_seed_stress_test",
    ),
    "run_unseen_area_evidence_report": (
        ".unseen_area_evidence_report",
        "run_unseen_area_evidence_report",
    ),
    "run_cross_region_transfer_recommendation_check": (
        ".transfer_recommendation_eval",
        "run_cross_region_transfer_recommendation_check",
    ),
    "run_all_supported_models": (".all_models", "run_all_supported_models"),
    "run_all_models_seed_sweep": (".all_models_seed_sweep", "run_all_models_seed_sweep"),
}


def __getattr__(name: str) -> Any:
    mapping = _EXPORT_MAP.get(name)
    if mapping is None:
        raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
    module_name, attr_name = mapping
    module = importlib.import_module(module_name, __name__)
    value = getattr(module, attr_name)
    globals()[name] = value
    return value
