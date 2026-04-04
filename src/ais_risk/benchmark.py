from __future__ import annotations

import csv
import json
import math
import random
import time
from pathlib import Path
from typing import Any

import numpy as np
from sklearn.feature_extraction import DictVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.ensemble import ExtraTreesClassifier, HistGradientBoostingClassifier, RandomForestClassifier
from sklearn.metrics import (
    accuracy_score,
    average_precision_score,
    f1_score,
    precision_score,
    recall_score,
    roc_auc_score,
)
from sklearn.preprocessing import StandardScaler

try:
    import torch
    from torch import nn
except Exception:  # pragma: no cover - torch is optional at runtime
    torch = None
    nn = None


DEFAULT_BENCHMARK_MODELS = ["rule_score", "logreg", "hgbt"]
SUPPORTED_BENCHMARK_MODELS = [
    "rule_score",
    "logreg",
    "hgbt",
    "random_forest",
    "extra_trees",
    "torch_mlp",
]


def load_pairwise_dataset_rows(path: str | Path) -> list[dict[str, str]]:
    with Path(path).open("r", encoding="utf-8", newline="") as handle:
        reader = csv.DictReader(handle)
        return [dict(row) for row in reader]


def _feature_dict(row: dict[str, str]) -> dict[str, float | str]:
    return {
        "distance_nm": float(row["distance_nm"]),
        "dcpa_nm": float(row["dcpa_nm"]),
        "tcpa_min": float(row["tcpa_min"]),
        "relative_speed_knots": float(row["relative_speed_knots"]),
        "relative_bearing_deg": float(row["relative_bearing_deg"]),
        "bearing_abs_deg": float(row["bearing_abs_deg"]),
        "course_difference_deg": float(row["course_difference_deg"]),
        "local_target_count": float(row["local_target_count"]),
        "rule_score": float(row["rule_score"]),
        "rule_component_distance": float(row["rule_component_distance"]),
        "rule_component_dcpa": float(row["rule_component_dcpa"]),
        "rule_component_tcpa": float(row["rule_component_tcpa"]),
        "rule_component_bearing": float(row["rule_component_bearing"]),
        "rule_component_relspeed": float(row["rule_component_relspeed"]),
        "rule_component_encounter": float(row["rule_component_encounter"]),
        "rule_component_density": float(row["rule_component_density"]),
        "encounter_type": row["encounter_type"] or "unknown",
        "own_vessel_type": row["own_vessel_type"] or "unknown",
        "target_vessel_type": row["target_vessel_type"] or "unknown",
        "pair_interp_flag": f"{row['own_is_interpolated']}_{row['target_is_interpolated']}",
    }


def _balanced_sample_weights(y: np.ndarray) -> np.ndarray:
    positives = float(np.sum(y == 1))
    negatives = float(np.sum(y == 0))
    if positives == 0 or negatives == 0:
        return np.ones_like(y, dtype=float)
    total = positives + negatives
    pos_weight = total / (2.0 * positives)
    neg_weight = total / (2.0 * negatives)
    return np.where(y == 1, pos_weight, neg_weight).astype(float)


def _split_timestamps(ordered_timestamps: list[str], train_fraction: float, val_fraction: float) -> tuple[set[str], set[str], set[str]]:
    return _split_ordered_values(
        ordered_timestamps,
        train_fraction,
        val_fraction,
        entity_name="timestamps",
    )


def _split_ordered_values(
    ordered_values: list[str],
    train_fraction: float,
    val_fraction: float,
    entity_name: str,
) -> tuple[set[str], set[str], set[str]]:
    count = len(ordered_values)
    if count < 3:
        raise ValueError(f"At least 3 unique {entity_name} values are required for train/val/test splitting.")

    train_count = max(1, int(math.floor(count * train_fraction)))
    val_count = max(1, int(math.floor(count * val_fraction)))
    if train_count + val_count >= count:
        train_count = max(1, count - 2)
        val_count = 1
    test_count = count - train_count - val_count
    if test_count <= 0:
        if train_count > 1:
            train_count -= 1
        elif val_count > 1:
            val_count -= 1
        test_count = count - train_count - val_count
    if test_count <= 0:
        raise ValueError(f"Unable to allocate a non-empty test split from the available {entity_name} values.")

    train_values = set(ordered_values[:train_count])
    val_values = set(ordered_values[train_count : train_count + val_count])
    test_values = set(ordered_values[train_count + val_count :])
    return train_values, val_values, test_values


def _partition_rows_for_benchmark(
    rows: list[dict[str, str]],
    split_strategy: str,
    train_fraction: float,
    val_fraction: float,
) -> tuple[list[dict[str, str]], list[dict[str, str]], list[dict[str, str]], dict[str, Any]]:
    if split_strategy == "timestamp":
        ordered_timestamps = sorted({row["timestamp"] for row in rows})
        train_times, val_times, test_times = _split_ordered_values(
            ordered_timestamps,
            train_fraction,
            val_fraction,
            entity_name="timestamps",
        )
        train_rows = [row for row in rows if row["timestamp"] in train_times]
        val_rows = [row for row in rows if row["timestamp"] in val_times]
        test_rows = [row for row in rows if row["timestamp"] in test_times]
        split_summary = {
            "strategy": split_strategy,
            "train_rows": len(train_rows),
            "val_rows": len(val_rows),
            "test_rows": len(test_rows),
            "train_timestamps": len(train_times),
            "val_timestamps": len(val_times),
            "test_timestamps": len(test_times),
        }
        return train_rows, val_rows, test_rows, split_summary

    if split_strategy == "own_ship":
        ordered_own_ships = sorted({row["own_mmsi"] for row in rows})
        train_owns, val_owns, test_owns = _split_ordered_values(
            ordered_own_ships,
            train_fraction,
            val_fraction,
            entity_name="own_mmsi",
        )
        train_rows = [row for row in rows if row["own_mmsi"] in train_owns]
        val_rows = [row for row in rows if row["own_mmsi"] in val_owns]
        test_rows = [row for row in rows if row["own_mmsi"] in test_owns]
        split_summary = {
            "strategy": split_strategy,
            "train_rows": len(train_rows),
            "val_rows": len(val_rows),
            "test_rows": len(test_rows),
            "train_own_ships": len(train_owns),
            "val_own_ships": len(val_owns),
            "test_own_ships": len(test_owns),
            "train_timestamps": len({row["timestamp"] for row in train_rows}),
            "val_timestamps": len({row["timestamp"] for row in val_rows}),
            "test_timestamps": len({row["timestamp"] for row in test_rows}),
        }
        return train_rows, val_rows, test_rows, split_summary

    raise ValueError(f"Unsupported split_strategy: {split_strategy}")


def _vectorize_rows(rows: list[dict[str, str]], vectorizer: DictVectorizer | None = None):
    features = [_feature_dict(row) for row in rows]
    if vectorizer is None:
        vectorizer = DictVectorizer(sparse=False)
        matrix = vectorizer.fit_transform(features)
    else:
        matrix = vectorizer.transform(features)
    labels = np.array([int(row["label_future_conflict"]) for row in rows], dtype=int)
    return matrix.astype(np.float32), labels, vectorizer


def _validate_requested_model_names(model_names: list[str]) -> None:
    invalid = [model_name for model_name in model_names if model_name not in SUPPORTED_BENCHMARK_MODELS]
    if invalid:
        allowed = ",".join(SUPPORTED_BENCHMARK_MODELS)
        invalid_names = ",".join(invalid)
        raise ValueError(f"Unsupported model name(s): {invalid_names}. Supported: {allowed}")


def _fit_predict_proba(
    model: Any,
    x_train: np.ndarray,
    y_train: np.ndarray,
    x_val: np.ndarray,
    x_test: np.ndarray,
    x_target: np.ndarray | None = None,
    sample_weight: np.ndarray | None = None,
) -> tuple[np.ndarray, np.ndarray, np.ndarray | None]:
    if sample_weight is None:
        model.fit(x_train, y_train)
    else:
        model.fit(x_train, y_train, sample_weight=sample_weight)
    val_scores = model.predict_proba(x_val)[:, 1]
    test_scores = model.predict_proba(x_test)[:, 1]
    target_scores = model.predict_proba(x_target)[:, 1] if x_target is not None else None
    return val_scores, test_scores, target_scores


def run_benchmark_on_partitions(
    train_rows: list[dict[str, str]],
    val_rows: list[dict[str, str]],
    test_rows: list[dict[str, str]],
    model_names: list[str] | None = None,
    torch_device: str = "auto",
    random_seed: int | None = 42,
) -> tuple[dict[str, Any], dict[str, np.ndarray]]:
    if not train_rows or not val_rows or not test_rows:
        raise ValueError("Train/val/test rows must all be non-empty.")

    requested_models = model_names or list(DEFAULT_BENCHMARK_MODELS)
    _validate_requested_model_names(requested_models)
    x_train, y_train, vectorizer = _vectorize_rows(train_rows)
    x_val, y_val, _ = _vectorize_rows(val_rows, vectorizer=vectorizer)
    x_test, y_test, _ = _vectorize_rows(test_rows, vectorizer=vectorizer)

    scaler = StandardScaler()
    x_train_scaled = scaler.fit_transform(x_train)
    x_val_scaled = scaler.transform(x_val)
    x_test_scaled = scaler.transform(x_test)

    feature_names = vectorizer.feature_names_
    models_summary: dict[str, Any] = {}
    model_scores: dict[str, np.ndarray] = {}

    if "rule_score" in requested_models:
        started = time.perf_counter()
        val_scores = np.array([float(row["rule_score"]) for row in val_rows], dtype=float)
        test_scores = np.array([float(row["rule_score"]) for row in test_rows], dtype=float)
        threshold = _choose_threshold(y_val, val_scores)
        metrics = _build_metrics(y_test, test_scores, threshold)
        metrics["elapsed_seconds"] = float(time.perf_counter() - started)
        models_summary["rule_score"] = metrics
        model_scores["rule_score"] = test_scores

    if "logreg" in requested_models:
        started = time.perf_counter()
        if len(np.unique(y_train)) < 2:
            metrics = _build_skipped_metrics("train split has only one class")
            metrics["elapsed_seconds"] = float(time.perf_counter() - started)
            models_summary["logreg"] = metrics
        else:
            model = LogisticRegression(
                max_iter=1000,
                class_weight="balanced",
                random_state=None if random_seed is None else int(random_seed),
            )
            val_scores, test_scores, _ = _fit_predict_proba(
                model=model,
                x_train=x_train_scaled,
                y_train=y_train,
                x_val=x_val_scaled,
                x_test=x_test_scaled,
            )
            threshold = _choose_threshold(y_val, val_scores)
            metrics = _build_metrics(y_test, test_scores, threshold)
            metrics["top_positive_features"] = _top_logistic_coefficients(model, feature_names)
            metrics["elapsed_seconds"] = float(time.perf_counter() - started)
            models_summary["logreg"] = metrics
            model_scores["logreg"] = test_scores

    if "hgbt" in requested_models:
        started = time.perf_counter()
        if len(np.unique(y_train)) < 2:
            metrics = _build_skipped_metrics("train split has only one class")
            metrics["elapsed_seconds"] = float(time.perf_counter() - started)
            models_summary["hgbt"] = metrics
        else:
            model = HistGradientBoostingClassifier(
                max_depth=6,
                learning_rate=0.05,
                max_iter=200,
                random_state=None if random_seed is None else int(random_seed),
            )
            sample_weight = _balanced_sample_weights(y_train)
            val_scores, test_scores, _ = _fit_predict_proba(
                model=model,
                x_train=x_train_scaled,
                y_train=y_train,
                x_val=x_val_scaled,
                x_test=x_test_scaled,
                sample_weight=sample_weight,
            )
            threshold = _choose_threshold(y_val, val_scores)
            metrics = _build_metrics(y_test, test_scores, threshold)
            metrics["elapsed_seconds"] = float(time.perf_counter() - started)
            models_summary["hgbt"] = metrics
            model_scores["hgbt"] = test_scores

    if "random_forest" in requested_models:
        started = time.perf_counter()
        if len(np.unique(y_train)) < 2:
            metrics = _build_skipped_metrics("train split has only one class")
            metrics["elapsed_seconds"] = float(time.perf_counter() - started)
            models_summary["random_forest"] = metrics
        else:
            model = RandomForestClassifier(
                n_estimators=300,
                max_depth=16,
                min_samples_leaf=2,
                class_weight="balanced_subsample",
                n_jobs=-1,
                random_state=None if random_seed is None else int(random_seed),
            )
            val_scores, test_scores, _ = _fit_predict_proba(
                model=model,
                x_train=x_train_scaled,
                y_train=y_train,
                x_val=x_val_scaled,
                x_test=x_test_scaled,
            )
            threshold = _choose_threshold(y_val, val_scores)
            metrics = _build_metrics(y_test, test_scores, threshold)
            metrics["elapsed_seconds"] = float(time.perf_counter() - started)
            models_summary["random_forest"] = metrics
            model_scores["random_forest"] = test_scores

    if "extra_trees" in requested_models:
        started = time.perf_counter()
        if len(np.unique(y_train)) < 2:
            metrics = _build_skipped_metrics("train split has only one class")
            metrics["elapsed_seconds"] = float(time.perf_counter() - started)
            models_summary["extra_trees"] = metrics
        else:
            model = ExtraTreesClassifier(
                n_estimators=300,
                max_depth=16,
                min_samples_leaf=2,
                class_weight="balanced",
                n_jobs=-1,
                random_state=None if random_seed is None else int(random_seed),
            )
            val_scores, test_scores, _ = _fit_predict_proba(
                model=model,
                x_train=x_train_scaled,
                y_train=y_train,
                x_val=x_val_scaled,
                x_test=x_test_scaled,
            )
            threshold = _choose_threshold(y_val, val_scores)
            metrics = _build_metrics(y_test, test_scores, threshold)
            metrics["elapsed_seconds"] = float(time.perf_counter() - started)
            models_summary["extra_trees"] = metrics
            model_scores["extra_trees"] = test_scores

    if "torch_mlp" in requested_models:
        started = time.perf_counter()
        if len(np.unique(y_train)) < 2:
            metrics = _build_skipped_metrics("train split has only one class")
            metrics["elapsed_seconds"] = float(time.perf_counter() - started)
            models_summary["torch_mlp"] = metrics
        else:
            val_scores, test_scores, info = _predict_torch_mlp(
                x_train=x_train_scaled,
                y_train=y_train,
                x_val=x_val_scaled,
                y_val=y_val,
                x_test=x_test_scaled,
                requested_device=torch_device,
                random_seed=random_seed,
            )
            threshold = _choose_threshold(y_val, val_scores)
            metrics = _build_metrics(y_test, test_scores, threshold)
            metrics.update(info)
            metrics["elapsed_seconds"] = float(time.perf_counter() - started)
            models_summary["torch_mlp"] = metrics
            model_scores["torch_mlp"] = test_scores

    return models_summary, model_scores


def _safe_auc(y_true: np.ndarray, scores: np.ndarray) -> float | None:
    if len(np.unique(y_true)) < 2:
        return None
    return float(roc_auc_score(y_true, scores))


def _safe_average_precision(y_true: np.ndarray, scores: np.ndarray) -> float | None:
    if len(np.unique(y_true)) < 2:
        return None
    return float(average_precision_score(y_true, scores))


def _choose_threshold(y_true: np.ndarray, scores: np.ndarray) -> float:
    best_threshold = 0.5
    best_f1 = -1.0
    for step in range(5, 96, 5):
        threshold = step / 100.0
        predictions = (scores >= threshold).astype(int)
        current_f1 = f1_score(y_true, predictions, zero_division=0)
        if current_f1 > best_f1:
            best_threshold = threshold
            best_f1 = current_f1
    return float(best_threshold)


def _build_metrics(y_true: np.ndarray, scores: np.ndarray, threshold: float) -> dict[str, float | None]:
    predictions = (scores >= threshold).astype(int)
    return {
        "threshold": float(threshold),
        "auroc": _safe_auc(y_true, scores),
        "auprc": _safe_average_precision(y_true, scores),
        "accuracy": float(accuracy_score(y_true, predictions)),
        "precision": float(precision_score(y_true, predictions, zero_division=0)),
        "recall": float(recall_score(y_true, predictions, zero_division=0)),
        "f1": float(f1_score(y_true, predictions, zero_division=0)),
        "positive_rate_predicted": float(np.mean(predictions)) if len(predictions) else 0.0,
    }


def _build_skipped_metrics(reason: str) -> dict[str, Any]:
    return {
        "status": "skipped",
        "reason": reason,
    }


def _format_metric(value: Any) -> str:
    if isinstance(value, float):
        return f"{value:.4f}"
    return str(value)


def _top_logistic_coefficients(model: LogisticRegression, feature_names: list[str], top_k: int = 8) -> list[dict[str, float]]:
    coefficients = model.coef_[0]
    top_indices = np.argsort(coefficients)[-top_k:][::-1]
    return [{"feature": feature_names[index], "coefficient": float(coefficients[index])} for index in top_indices]


def _resolve_torch_device(requested: str) -> str:
    if requested == "cpu":
        return "cpu"
    if torch is None:
        raise RuntimeError("PyTorch is not installed.")
    if requested == "mps":
        if not torch.backends.mps.is_available():
            raise RuntimeError("PyTorch MPS backend is not available on this machine.")
        return "mps"
    if requested == "auto":
        if torch.backends.mps.is_available():
            return "mps"
        return "cpu"
    raise ValueError(f"Unsupported torch device: {requested}")


def _set_random_seeds(random_seed: int | None) -> None:
    if random_seed is None:
        return
    seed_value = int(random_seed)
    random.seed(seed_value)
    np.random.seed(seed_value)
    if torch is not None:
        torch.manual_seed(seed_value)


def _train_torch_mlp(
    x_train: np.ndarray,
    y_train: np.ndarray,
    x_val: np.ndarray,
    y_val: np.ndarray,
    requested_device: str = "auto",
    epochs: int = 40,
    learning_rate: float = 1e-3,
    hidden_dim: int = 64,
    random_seed: int | None = 42,
) -> tuple[np.ndarray, dict[str, Any]]:
    if torch is None or nn is None:
        raise RuntimeError("PyTorch is not installed.")

    _set_random_seeds(random_seed)
    resolved_device = _resolve_torch_device(requested_device)
    device = torch.device(resolved_device)
    x_train_tensor = torch.tensor(x_train, dtype=torch.float32, device=device)
    y_train_tensor = torch.tensor(y_train.reshape(-1, 1), dtype=torch.float32, device=device)
    x_val_tensor = torch.tensor(x_val, dtype=torch.float32, device=device)

    class MLP(nn.Module):
        def __init__(self, input_dim: int, hidden_dim_value: int) -> None:
            super().__init__()
            self.network = nn.Sequential(
                nn.Linear(input_dim, hidden_dim_value),
                nn.ReLU(),
                nn.Linear(hidden_dim_value, hidden_dim_value),
                nn.ReLU(),
                nn.Linear(hidden_dim_value, 1),
            )

        def forward(self, inputs: torch.Tensor) -> torch.Tensor:
            return self.network(inputs)

    model = MLP(x_train.shape[1], hidden_dim).to(device)
    optimizer = torch.optim.Adam(model.parameters(), lr=learning_rate)
    positives = max(1.0, float(np.sum(y_train == 1)))
    negatives = max(1.0, float(np.sum(y_train == 0)))
    pos_weight = torch.tensor([negatives / positives], dtype=torch.float32, device=device)
    loss_fn = nn.BCEWithLogitsLoss(pos_weight=pos_weight)

    best_state = None
    best_val_loss = float("inf")
    for _ in range(epochs):
        model.train()
        optimizer.zero_grad(set_to_none=True)
        logits = model(x_train_tensor)
        loss = loss_fn(logits, y_train_tensor)
        loss.backward()
        optimizer.step()

        model.eval()
        with torch.no_grad():
            val_logits = model(x_val_tensor)
            val_targets = torch.tensor(y_val.reshape(-1, 1), dtype=torch.float32, device=device)
            val_loss = float(loss_fn(val_logits, val_targets).item())
        if val_loss < best_val_loss:
            best_val_loss = val_loss
            best_state = {key: value.detach().cpu().clone() for key, value in model.state_dict().items()}

    if best_state is not None:
        model.load_state_dict(best_state)
    model.eval()
    with torch.no_grad():
        val_scores = torch.sigmoid(model(x_val_tensor)).detach().cpu().numpy().reshape(-1)
    return val_scores, {"device": resolved_device, "epochs": int(epochs), "hidden_dim": int(hidden_dim)}


def _predict_torch_mlp(
    x_train: np.ndarray,
    y_train: np.ndarray,
    x_val: np.ndarray,
    y_val: np.ndarray,
    x_test: np.ndarray,
    requested_device: str = "auto",
    epochs: int = 40,
    learning_rate: float = 1e-3,
    hidden_dim: int = 64,
    random_seed: int | None = 42,
) -> tuple[np.ndarray, np.ndarray, dict[str, Any]]:
    if torch is None or nn is None:
        raise RuntimeError("PyTorch is not installed.")

    _set_random_seeds(random_seed)
    resolved_device = _resolve_torch_device(requested_device)
    device = torch.device(resolved_device)
    x_train_tensor = torch.tensor(x_train, dtype=torch.float32, device=device)
    y_train_tensor = torch.tensor(y_train.reshape(-1, 1), dtype=torch.float32, device=device)
    x_val_tensor = torch.tensor(x_val, dtype=torch.float32, device=device)
    x_test_tensor = torch.tensor(x_test, dtype=torch.float32, device=device)

    class MLP(nn.Module):
        def __init__(self, input_dim: int, hidden_dim_value: int) -> None:
            super().__init__()
            self.network = nn.Sequential(
                nn.Linear(input_dim, hidden_dim_value),
                nn.ReLU(),
                nn.Linear(hidden_dim_value, hidden_dim_value),
                nn.ReLU(),
                nn.Linear(hidden_dim_value, 1),
            )

        def forward(self, inputs: torch.Tensor) -> torch.Tensor:
            return self.network(inputs)

    model = MLP(x_train.shape[1], hidden_dim).to(device)
    optimizer = torch.optim.Adam(model.parameters(), lr=learning_rate)
    positives = max(1.0, float(np.sum(y_train == 1)))
    negatives = max(1.0, float(np.sum(y_train == 0)))
    pos_weight = torch.tensor([negatives / positives], dtype=torch.float32, device=device)
    loss_fn = nn.BCEWithLogitsLoss(pos_weight=pos_weight)

    best_state = None
    best_val_loss = float("inf")
    for _ in range(epochs):
        model.train()
        optimizer.zero_grad(set_to_none=True)
        logits = model(x_train_tensor)
        loss = loss_fn(logits, y_train_tensor)
        loss.backward()
        optimizer.step()

        model.eval()
        with torch.no_grad():
            val_logits = model(x_val_tensor)
            val_targets = torch.tensor(y_val.reshape(-1, 1), dtype=torch.float32, device=device)
            val_loss = float(loss_fn(val_logits, val_targets).item())
        if val_loss < best_val_loss:
            best_val_loss = val_loss
            best_state = {key: value.detach().cpu().clone() for key, value in model.state_dict().items()}

    if best_state is not None:
        model.load_state_dict(best_state)
    model.eval()
    with torch.no_grad():
        val_scores = torch.sigmoid(model(x_val_tensor)).detach().cpu().numpy().reshape(-1)
        test_scores = torch.sigmoid(model(x_test_tensor)).detach().cpu().numpy().reshape(-1)
    return val_scores, test_scores, {"device": resolved_device, "epochs": int(epochs), "hidden_dim": int(hidden_dim)}


def _predict_torch_mlp_transfer(
    x_train: np.ndarray,
    y_train: np.ndarray,
    x_val: np.ndarray,
    y_val: np.ndarray,
    x_test: np.ndarray,
    x_target: np.ndarray,
    requested_device: str = "auto",
    epochs: int = 40,
    learning_rate: float = 1e-3,
    hidden_dim: int = 64,
    random_seed: int | None = 42,
) -> tuple[np.ndarray, np.ndarray, np.ndarray, dict[str, Any]]:
    if torch is None or nn is None:
        raise RuntimeError("PyTorch is not installed.")

    _set_random_seeds(random_seed)
    resolved_device = _resolve_torch_device(requested_device)
    device = torch.device(resolved_device)
    x_train_tensor = torch.tensor(x_train, dtype=torch.float32, device=device)
    y_train_tensor = torch.tensor(y_train.reshape(-1, 1), dtype=torch.float32, device=device)
    x_val_tensor = torch.tensor(x_val, dtype=torch.float32, device=device)
    x_test_tensor = torch.tensor(x_test, dtype=torch.float32, device=device)
    x_target_tensor = torch.tensor(x_target, dtype=torch.float32, device=device)

    class MLP(nn.Module):
        def __init__(self, input_dim: int, hidden_dim_value: int) -> None:
            super().__init__()
            self.network = nn.Sequential(
                nn.Linear(input_dim, hidden_dim_value),
                nn.ReLU(),
                nn.Linear(hidden_dim_value, hidden_dim_value),
                nn.ReLU(),
                nn.Linear(hidden_dim_value, 1),
            )

        def forward(self, inputs: torch.Tensor) -> torch.Tensor:
            return self.network(inputs)

    model = MLP(x_train.shape[1], hidden_dim).to(device)
    optimizer = torch.optim.Adam(model.parameters(), lr=learning_rate)
    positives = max(1.0, float(np.sum(y_train == 1)))
    negatives = max(1.0, float(np.sum(y_train == 0)))
    pos_weight = torch.tensor([negatives / positives], dtype=torch.float32, device=device)
    loss_fn = nn.BCEWithLogitsLoss(pos_weight=pos_weight)

    best_state = None
    best_val_loss = float("inf")
    for _ in range(epochs):
        model.train()
        optimizer.zero_grad(set_to_none=True)
        logits = model(x_train_tensor)
        loss = loss_fn(logits, y_train_tensor)
        loss.backward()
        optimizer.step()

        model.eval()
        with torch.no_grad():
            val_logits = model(x_val_tensor)
            val_targets = torch.tensor(y_val.reshape(-1, 1), dtype=torch.float32, device=device)
            val_loss = float(loss_fn(val_logits, val_targets).item())
        if val_loss < best_val_loss:
            best_val_loss = val_loss
            best_state = {key: value.detach().cpu().clone() for key, value in model.state_dict().items()}

    if best_state is not None:
        model.load_state_dict(best_state)
    model.eval()
    with torch.no_grad():
        val_scores = torch.sigmoid(model(x_val_tensor)).detach().cpu().numpy().reshape(-1)
        test_scores = torch.sigmoid(model(x_test_tensor)).detach().cpu().numpy().reshape(-1)
        target_scores = torch.sigmoid(model(x_target_tensor)).detach().cpu().numpy().reshape(-1)
    return val_scores, test_scores, target_scores, {
        "device": resolved_device,
        "epochs": int(epochs),
        "hidden_dim": int(hidden_dim),
    }


def build_benchmark_summary_markdown(summary: dict[str, Any]) -> str:
    lines = [
        "# Pairwise Benchmark Summary",
        "",
        "## Dataset",
        "",
        f"- Input: `{summary['input_path']}`",
        f"- Row count: `{summary['row_count']}`",
        f"- Positive rate: `{summary['positive_rate']:.4f}`",
        f"- Unique timestamps: `{summary['timestamp_count']}`",
        f"- Random seed: `{summary.get('random_seed', 'n/a')}`",
        f"- Benchmark elapsed (sec): `{summary.get('benchmark_elapsed_seconds', 'n/a')}`",
        "",
        "## Split",
        "",
        f"- Strategy: `{summary['split']['strategy']}`",
        f"- Train rows: `{summary['split']['train_rows']}`",
        f"- Validation rows: `{summary['split']['val_rows']}`",
        f"- Test rows: `{summary['split']['test_rows']}`",
    ]
    if "train_own_ships" in summary["split"]:
        lines.extend(
            [
                f"- Train own ships: `{summary['split']['train_own_ships']}`",
                f"- Validation own ships: `{summary['split']['val_own_ships']}`",
                f"- Test own ships: `{summary['split']['test_own_ships']}`",
            ]
        )
    lines.extend(
        [
            "",
            "## Models",
            "",
        ]
    )
    for model_name, metrics in summary["models"].items():
        if metrics.get("status") == "skipped":
            lines.extend(
                [
                    f"### {model_name}",
                    "",
                    f"- Status: `skipped`",
                    f"- Reason: `{metrics['reason']}`",
                    "",
                ]
            )
            continue
        lines.extend(
            [
                f"### {model_name}",
                "",
                f"- Threshold: `{metrics['threshold']:.2f}`",
                f"- AUROC: `{metrics['auroc'] if metrics['auroc'] is not None else 'n/a'}`",
                f"- AUPRC: `{metrics['auprc'] if metrics['auprc'] is not None else 'n/a'}`",
                f"- F1: `{metrics['f1']:.4f}`",
                f"- Precision: `{metrics['precision']:.4f}`",
                f"- Recall: `{metrics['recall']:.4f}`",
                f"- Elapsed (sec): `{metrics.get('elapsed_seconds', 'n/a')}`",
                "",
            ]
        )
        if metrics.get("top_positive_features"):
            lines.append("- Top positive features:")
            for item in metrics["top_positive_features"]:
                lines.append(f"  - `{item['feature']}`: `{item['coefficient']:.4f}`")
            lines.append("")
        if metrics.get("device"):
            lines.append(f"- Device: `{metrics['device']}`")
            lines.append("")
    return "\n".join(lines).rstrip() + "\n"


def build_transfer_benchmark_summary_markdown(summary: dict[str, Any]) -> str:
    lines = [
        "# Transfer Benchmark Summary",
        "",
        "## Source / Target Datasets",
        "",
        f"- Train input: `{summary['train_input_path']}`",
        f"- Target input: `{summary['target_input_path']}`",
        f"- Source rows: `{summary['source_row_count']}`",
        f"- Source positive rate: `{summary['source_positive_rate']:.4f}`",
        f"- Target rows: `{summary['target_row_count']}`",
        f"- Target positive rate: `{summary['target_positive_rate']:.4f}`",
        f"- Random seed: `{summary.get('random_seed', 'n/a')}`",
        f"- Transfer elapsed (sec): `{summary.get('transfer_elapsed_seconds', 'n/a')}`",
        "",
        "## Source Split",
        "",
        f"- Strategy: `{summary['split']['strategy']}`",
        f"- Train rows: `{summary['split']['train_rows']}`",
        f"- Validation rows: `{summary['split']['val_rows']}`",
        f"- Test rows: `{summary['split']['test_rows']}`",
    ]
    if "train_own_ships" in summary["split"]:
        lines.extend(
            [
                f"- Train own ships: `{summary['split']['train_own_ships']}`",
                f"- Validation own ships: `{summary['split']['val_own_ships']}`",
                f"- Test own ships: `{summary['split']['test_own_ships']}`",
            ]
        )
    lines.extend(
        [
            "",
            "## Models",
            "",
            "| Model | Threshold | SourceTestF1 | SourceTestECE? | TargetTransferF1 | TargetTransferAUPRC | ElapsedSec |",
            "|---|---:|---:|---:|---:|---:|---:|",
        ]
    )
    for model_name, metrics in summary["models"].items():
        if metrics.get("status") == "skipped":
            lines.append(
                "| {model} | n/a | skipped | n/a | skipped | n/a | {elapsed} |".format(
                    model=model_name,
                    elapsed=_format_metric(metrics.get("elapsed_seconds", 0.0)),
                )
            )
            continue
        source_test = metrics["source_test"]
        target_transfer = metrics["target_transfer"]
        lines.append(
            "| {model} | {threshold} | {source_f1} | n/a | {target_f1} | {target_auprc} | {elapsed} |".format(
                model=model_name,
                threshold=_format_metric(metrics.get("threshold", 0.0)),
                source_f1=_format_metric(source_test.get("f1", 0.0)),
                target_f1=_format_metric(target_transfer.get("f1", 0.0)),
                target_auprc=_format_metric(target_transfer.get("auprc", 0.0)),
                elapsed=_format_metric(metrics.get("elapsed_seconds", 0.0)),
            )
        )
    lines.extend(
        [
            "",
            "## Outputs",
            "",
            f"- source_summary_json: `{summary['source_summary_json_path']}`",
            f"- source_summary_md: `{summary['source_summary_md_path']}`",
            f"- source_test_predictions_csv: `{summary['source_test_predictions_csv_path']}`",
            f"- source_val_predictions_csv: `{summary['source_val_predictions_csv_path']}`",
            f"- target_predictions_csv: `{summary['target_predictions_csv_path']}`",
            f"- transfer_summary_json: `{summary['transfer_summary_json_path']}`",
            f"- transfer_summary_md: `{summary['transfer_summary_md_path']}`",
            "",
        ]
    )
    return "\n".join(lines)


def _write_predictions_csv(
    path: str | Path,
    rows: list[dict[str, str]],
    model_scores: dict[str, np.ndarray],
    model_thresholds: dict[str, float],
) -> str:
    output_path = Path(path)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    fieldnames = ["timestamp", "own_mmsi", "target_mmsi", "label_future_conflict"]
    for model_name in model_scores:
        fieldnames.extend([f"{model_name}_score", f"{model_name}_pred"])

    with output_path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        for index, row in enumerate(rows):
            payload = {
                "timestamp": row["timestamp"],
                "own_mmsi": row["own_mmsi"],
                "target_mmsi": row["target_mmsi"],
                "label_future_conflict": row["label_future_conflict"],
            }
            for model_name, scores in model_scores.items():
                threshold = float(model_thresholds[model_name])
                score = float(scores[index])
                payload[f"{model_name}_score"] = f"{score:.6f}"
                payload[f"{model_name}_pred"] = "1" if score >= threshold else "0"
            writer.writerow(payload)

    return str(output_path)


def save_benchmark_outputs(
    output_prefix: str | Path,
    summary: dict[str, Any],
    test_rows: list[dict[str, str]],
    model_scores: dict[str, np.ndarray],
) -> dict[str, str]:
    prefix = Path(output_prefix)
    prefix.parent.mkdir(parents=True, exist_ok=True)

    summary_json_path = prefix.with_name(f"{prefix.name}_summary.json")
    summary_md_path = prefix.with_name(f"{prefix.name}_summary.md")
    predictions_csv_path = prefix.with_name(f"{prefix.name}_test_predictions.csv")

    summary_json_path.write_text(json.dumps(summary, indent=2), encoding="utf-8")
    summary_md_path.write_text(build_benchmark_summary_markdown(summary), encoding="utf-8")
    _write_predictions_csv(
        path=predictions_csv_path,
        rows=test_rows,
        model_scores=model_scores,
        model_thresholds={model_name: float(summary["models"][model_name]["threshold"]) for model_name in model_scores},
    )

    return {
        "summary_json_path": str(summary_json_path),
        "summary_md_path": str(summary_md_path),
        "predictions_csv_path": str(predictions_csv_path),
    }


def run_pairwise_benchmark(
    input_path: str | Path,
    output_prefix: str | Path,
    model_names: list[str] | None = None,
    train_fraction: float = 0.6,
    val_fraction: float = 0.2,
    split_strategy: str = "timestamp",
    torch_device: str = "auto",
    random_seed: int | None = 42,
) -> dict[str, Any]:
    rows = load_pairwise_dataset_rows(input_path)
    if not rows:
        raise ValueError("Pairwise learning dataset is empty.")

    requested_models = model_names or list(DEFAULT_BENCHMARK_MODELS)
    train_rows, val_rows, test_rows, split_summary = _partition_rows_for_benchmark(
        rows=rows,
        split_strategy=split_strategy,
        train_fraction=train_fraction,
        val_fraction=val_fraction,
    )
    if not train_rows or not val_rows or not test_rows:
        raise ValueError("Train/val/test split produced an empty partition.")
    summary: dict[str, Any] = {
        "input_path": str(input_path),
        "row_count": len(rows),
        "positive_rate": float(np.mean([int(row["label_future_conflict"]) for row in rows])),
        "timestamp_count": len({row["timestamp"] for row in rows}),
        "own_ship_count": len({row["own_mmsi"] for row in rows}),
        "split": split_summary,
        "models": {},
        "random_seed": random_seed,
    }

    benchmark_started = time.perf_counter()
    models_summary, model_scores = run_benchmark_on_partitions(
        train_rows=train_rows,
        val_rows=val_rows,
        test_rows=test_rows,
        model_names=requested_models,
        torch_device=torch_device,
        random_seed=random_seed,
    )
    summary["models"] = models_summary
    summary["benchmark_elapsed_seconds"] = float(time.perf_counter() - benchmark_started)

    output_paths = save_benchmark_outputs(output_prefix, summary, test_rows, model_scores)
    summary.update(output_paths)
    return summary


def run_pairwise_transfer_benchmark(
    train_input_path: str | Path,
    target_input_path: str | Path,
    output_prefix: str | Path,
    model_names: list[str] | None = None,
    train_fraction: float = 0.6,
    val_fraction: float = 0.2,
    split_strategy: str = "own_ship",
    torch_device: str = "auto",
    random_seed: int | None = 42,
) -> dict[str, Any]:
    source_rows = load_pairwise_dataset_rows(train_input_path)
    target_rows = load_pairwise_dataset_rows(target_input_path)
    if not source_rows:
        raise ValueError("Source pairwise learning dataset is empty.")
    if not target_rows:
        raise ValueError("Target pairwise learning dataset is empty.")

    requested_models = model_names or list(DEFAULT_BENCHMARK_MODELS)
    _validate_requested_model_names(requested_models)
    train_rows, val_rows, test_rows, split_summary = _partition_rows_for_benchmark(
        rows=source_rows,
        split_strategy=split_strategy,
        train_fraction=train_fraction,
        val_fraction=val_fraction,
    )
    if not train_rows or not val_rows or not test_rows:
        raise ValueError("Source train/val/test split produced an empty partition.")

    x_train, y_train, vectorizer = _vectorize_rows(train_rows)
    x_val, y_val, _ = _vectorize_rows(val_rows, vectorizer=vectorizer)
    x_test, y_test, _ = _vectorize_rows(test_rows, vectorizer=vectorizer)
    x_target, y_target, _ = _vectorize_rows(target_rows, vectorizer=vectorizer)

    scaler = StandardScaler()
    x_train_scaled = scaler.fit_transform(x_train)
    x_val_scaled = scaler.transform(x_val)
    x_test_scaled = scaler.transform(x_test)
    x_target_scaled = scaler.transform(x_target)

    feature_names = vectorizer.feature_names_
    source_models_summary: dict[str, Any] = {}
    source_val_scores: dict[str, np.ndarray] = {}
    source_test_scores: dict[str, np.ndarray] = {}
    target_transfer_scores: dict[str, np.ndarray] = {}
    transfer_models_summary: dict[str, Any] = {}
    model_thresholds: dict[str, float] = {}

    transfer_started = time.perf_counter()

    for model_name in requested_models:
        started = time.perf_counter()
        if model_name == "rule_score":
            val_scores = np.array([float(row["rule_score"]) for row in val_rows], dtype=float)
            test_scores = np.array([float(row["rule_score"]) for row in test_rows], dtype=float)
            target_scores = np.array([float(row["rule_score"]) for row in target_rows], dtype=float)
            threshold = _choose_threshold(y_val, val_scores)
            source_metrics = _build_metrics(y_test, test_scores, threshold)
            source_metrics["elapsed_seconds"] = float(time.perf_counter() - started)
            target_metrics = _build_metrics(y_target, target_scores, threshold)
            target_metrics["threshold"] = float(threshold)
            source_models_summary[model_name] = source_metrics
            source_val_scores[model_name] = val_scores
            source_test_scores[model_name] = test_scores
            target_transfer_scores[model_name] = target_scores
            model_thresholds[model_name] = float(threshold)
            transfer_models_summary[model_name] = {
                "status": "completed",
                "threshold": float(threshold),
                "elapsed_seconds": float(time.perf_counter() - started),
                "source_test": source_metrics,
                "target_transfer": target_metrics,
            }
            continue

        if model_name == "logreg":
            if len(np.unique(y_train)) < 2:
                skipped = _build_skipped_metrics("train split has only one class")
                skipped["elapsed_seconds"] = float(time.perf_counter() - started)
                source_models_summary[model_name] = skipped
                transfer_models_summary[model_name] = skipped
                continue
            model = LogisticRegression(
                max_iter=1000,
                class_weight="balanced",
                random_state=None if random_seed is None else int(random_seed),
            )
            val_scores, test_scores, target_scores = _fit_predict_proba(
                model=model,
                x_train=x_train_scaled,
                y_train=y_train,
                x_val=x_val_scaled,
                x_test=x_test_scaled,
                x_target=x_target_scaled,
            )
            if target_scores is None:
                raise RuntimeError("target scores should not be None for transfer benchmark.")
            threshold = _choose_threshold(y_val, val_scores)
            source_metrics = _build_metrics(y_test, test_scores, threshold)
            source_metrics["top_positive_features"] = _top_logistic_coefficients(model, feature_names)
            source_metrics["elapsed_seconds"] = float(time.perf_counter() - started)
            target_metrics = _build_metrics(y_target, target_scores, threshold)
            target_metrics["threshold"] = float(threshold)
            source_models_summary[model_name] = source_metrics
            source_val_scores[model_name] = val_scores
            source_test_scores[model_name] = test_scores
            target_transfer_scores[model_name] = target_scores
            model_thresholds[model_name] = float(threshold)
            transfer_models_summary[model_name] = {
                "status": "completed",
                "threshold": float(threshold),
                "elapsed_seconds": float(time.perf_counter() - started),
                "source_test": source_metrics,
                "target_transfer": target_metrics,
            }
            continue

        if model_name == "hgbt":
            if len(np.unique(y_train)) < 2:
                skipped = _build_skipped_metrics("train split has only one class")
                skipped["elapsed_seconds"] = float(time.perf_counter() - started)
                source_models_summary[model_name] = skipped
                transfer_models_summary[model_name] = skipped
                continue
            model = HistGradientBoostingClassifier(
                max_depth=6,
                learning_rate=0.05,
                max_iter=200,
                random_state=None if random_seed is None else int(random_seed),
            )
            sample_weight = _balanced_sample_weights(y_train)
            val_scores, test_scores, target_scores = _fit_predict_proba(
                model=model,
                x_train=x_train_scaled,
                y_train=y_train,
                x_val=x_val_scaled,
                x_test=x_test_scaled,
                x_target=x_target_scaled,
                sample_weight=sample_weight,
            )
            if target_scores is None:
                raise RuntimeError("target scores should not be None for transfer benchmark.")
            threshold = _choose_threshold(y_val, val_scores)
            source_metrics = _build_metrics(y_test, test_scores, threshold)
            source_metrics["elapsed_seconds"] = float(time.perf_counter() - started)
            target_metrics = _build_metrics(y_target, target_scores, threshold)
            target_metrics["threshold"] = float(threshold)
            source_models_summary[model_name] = source_metrics
            source_val_scores[model_name] = val_scores
            source_test_scores[model_name] = test_scores
            target_transfer_scores[model_name] = target_scores
            model_thresholds[model_name] = float(threshold)
            transfer_models_summary[model_name] = {
                "status": "completed",
                "threshold": float(threshold),
                "elapsed_seconds": float(time.perf_counter() - started),
                "source_test": source_metrics,
                "target_transfer": target_metrics,
            }
            continue

        if model_name == "random_forest":
            if len(np.unique(y_train)) < 2:
                skipped = _build_skipped_metrics("train split has only one class")
                skipped["elapsed_seconds"] = float(time.perf_counter() - started)
                source_models_summary[model_name] = skipped
                transfer_models_summary[model_name] = skipped
                continue
            model = RandomForestClassifier(
                n_estimators=300,
                max_depth=16,
                min_samples_leaf=2,
                class_weight="balanced_subsample",
                n_jobs=-1,
                random_state=None if random_seed is None else int(random_seed),
            )
            val_scores, test_scores, target_scores = _fit_predict_proba(
                model=model,
                x_train=x_train_scaled,
                y_train=y_train,
                x_val=x_val_scaled,
                x_test=x_test_scaled,
                x_target=x_target_scaled,
            )
            if target_scores is None:
                raise RuntimeError("target scores should not be None for transfer benchmark.")
            threshold = _choose_threshold(y_val, val_scores)
            source_metrics = _build_metrics(y_test, test_scores, threshold)
            source_metrics["elapsed_seconds"] = float(time.perf_counter() - started)
            target_metrics = _build_metrics(y_target, target_scores, threshold)
            target_metrics["threshold"] = float(threshold)
            source_models_summary[model_name] = source_metrics
            source_val_scores[model_name] = val_scores
            source_test_scores[model_name] = test_scores
            target_transfer_scores[model_name] = target_scores
            model_thresholds[model_name] = float(threshold)
            transfer_models_summary[model_name] = {
                "status": "completed",
                "threshold": float(threshold),
                "elapsed_seconds": float(time.perf_counter() - started),
                "source_test": source_metrics,
                "target_transfer": target_metrics,
            }
            continue

        if model_name == "extra_trees":
            if len(np.unique(y_train)) < 2:
                skipped = _build_skipped_metrics("train split has only one class")
                skipped["elapsed_seconds"] = float(time.perf_counter() - started)
                source_models_summary[model_name] = skipped
                transfer_models_summary[model_name] = skipped
                continue
            model = ExtraTreesClassifier(
                n_estimators=300,
                max_depth=16,
                min_samples_leaf=2,
                class_weight="balanced",
                n_jobs=-1,
                random_state=None if random_seed is None else int(random_seed),
            )
            val_scores, test_scores, target_scores = _fit_predict_proba(
                model=model,
                x_train=x_train_scaled,
                y_train=y_train,
                x_val=x_val_scaled,
                x_test=x_test_scaled,
                x_target=x_target_scaled,
            )
            if target_scores is None:
                raise RuntimeError("target scores should not be None for transfer benchmark.")
            threshold = _choose_threshold(y_val, val_scores)
            source_metrics = _build_metrics(y_test, test_scores, threshold)
            source_metrics["elapsed_seconds"] = float(time.perf_counter() - started)
            target_metrics = _build_metrics(y_target, target_scores, threshold)
            target_metrics["threshold"] = float(threshold)
            source_models_summary[model_name] = source_metrics
            source_val_scores[model_name] = val_scores
            source_test_scores[model_name] = test_scores
            target_transfer_scores[model_name] = target_scores
            model_thresholds[model_name] = float(threshold)
            transfer_models_summary[model_name] = {
                "status": "completed",
                "threshold": float(threshold),
                "elapsed_seconds": float(time.perf_counter() - started),
                "source_test": source_metrics,
                "target_transfer": target_metrics,
            }
            continue

        if model_name == "torch_mlp":
            if len(np.unique(y_train)) < 2:
                skipped = _build_skipped_metrics("train split has only one class")
                skipped["elapsed_seconds"] = float(time.perf_counter() - started)
                source_models_summary[model_name] = skipped
                transfer_models_summary[model_name] = skipped
                continue
            val_scores, test_scores, target_scores, info = _predict_torch_mlp_transfer(
                x_train=x_train_scaled,
                y_train=y_train,
                x_val=x_val_scaled,
                y_val=y_val,
                x_test=x_test_scaled,
                x_target=x_target_scaled,
                requested_device=torch_device,
                random_seed=random_seed,
            )
            threshold = _choose_threshold(y_val, val_scores)
            source_metrics = _build_metrics(y_test, test_scores, threshold)
            source_metrics.update(info)
            source_metrics["elapsed_seconds"] = float(time.perf_counter() - started)
            target_metrics = _build_metrics(y_target, target_scores, threshold)
            target_metrics["threshold"] = float(threshold)
            target_metrics.update(info)
            source_models_summary[model_name] = source_metrics
            source_val_scores[model_name] = val_scores
            source_test_scores[model_name] = test_scores
            target_transfer_scores[model_name] = target_scores
            model_thresholds[model_name] = float(threshold)
            transfer_models_summary[model_name] = {
                "status": "completed",
                "threshold": float(threshold),
                "elapsed_seconds": float(time.perf_counter() - started),
                "source_test": source_metrics,
                "target_transfer": target_metrics,
            }
            continue

        raise ValueError(f"Unsupported model name: {model_name}")

    source_summary: dict[str, Any] = {
        "input_path": str(train_input_path),
        "row_count": len(source_rows),
        "positive_rate": float(np.mean([int(row["label_future_conflict"]) for row in source_rows])),
        "timestamp_count": len({row["timestamp"] for row in source_rows}),
        "own_ship_count": len({row["own_mmsi"] for row in source_rows}),
        "split": split_summary,
        "models": source_models_summary,
        "random_seed": random_seed,
        "benchmark_elapsed_seconds": float(time.perf_counter() - transfer_started),
    }

    prefix = Path(output_prefix)
    prefix.parent.mkdir(parents=True, exist_ok=True)
    source_summary_json_path = prefix.with_name(f"{prefix.name}_source_summary.json")
    source_summary_md_path = prefix.with_name(f"{prefix.name}_source_summary.md")
    source_test_predictions_csv_path = prefix.with_name(f"{prefix.name}_source_test_predictions.csv")
    source_val_predictions_csv_path = prefix.with_name(f"{prefix.name}_source_val_predictions.csv")
    target_predictions_csv_path = prefix.with_name(f"{prefix.name}_target_predictions.csv")
    transfer_summary_json_path = prefix.with_name(f"{prefix.name}_transfer_summary.json")
    transfer_summary_md_path = prefix.with_name(f"{prefix.name}_transfer_summary.md")

    source_summary_json_path.write_text(json.dumps(source_summary, indent=2), encoding="utf-8")
    source_summary_md_path.write_text(build_benchmark_summary_markdown(source_summary), encoding="utf-8")
    _write_predictions_csv(
        path=source_test_predictions_csv_path,
        rows=test_rows,
        model_scores=source_test_scores,
        model_thresholds=model_thresholds,
    )
    _write_predictions_csv(
        path=source_val_predictions_csv_path,
        rows=val_rows,
        model_scores=source_val_scores,
        model_thresholds=model_thresholds,
    )
    _write_predictions_csv(
        path=target_predictions_csv_path,
        rows=target_rows,
        model_scores=target_transfer_scores,
        model_thresholds=model_thresholds,
    )

    transfer_summary: dict[str, Any] = {
        "train_input_path": str(train_input_path),
        "target_input_path": str(target_input_path),
        "source_row_count": len(source_rows),
        "source_positive_rate": float(np.mean([int(row["label_future_conflict"]) for row in source_rows])),
        "target_row_count": len(target_rows),
        "target_positive_rate": float(np.mean([int(row["label_future_conflict"]) for row in target_rows])),
        "source_timestamp_count": len({row["timestamp"] for row in source_rows}),
        "target_timestamp_count": len({row["timestamp"] for row in target_rows}),
        "source_own_ship_count": len({row["own_mmsi"] for row in source_rows}),
        "target_own_ship_count": len({row["own_mmsi"] for row in target_rows}),
        "split": split_summary,
        "models": transfer_models_summary,
        "random_seed": random_seed,
        "transfer_elapsed_seconds": float(time.perf_counter() - transfer_started),
        "source_summary_json_path": str(source_summary_json_path),
        "source_summary_md_path": str(source_summary_md_path),
        "source_test_predictions_csv_path": str(source_test_predictions_csv_path),
        "source_val_predictions_csv_path": str(source_val_predictions_csv_path),
        "target_predictions_csv_path": str(target_predictions_csv_path),
        "transfer_summary_json_path": str(transfer_summary_json_path),
        "transfer_summary_md_path": str(transfer_summary_md_path),
    }
    transfer_summary_json_path.write_text(json.dumps(transfer_summary, indent=2), encoding="utf-8")
    transfer_summary_md_path.write_text(build_transfer_benchmark_summary_markdown(transfer_summary), encoding="utf-8")

    transfer_summary.update(
        {
            "transfer_summary_json_path": str(transfer_summary_json_path),
            "transfer_summary_md_path": str(transfer_summary_md_path),
        }
    )
    return transfer_summary
