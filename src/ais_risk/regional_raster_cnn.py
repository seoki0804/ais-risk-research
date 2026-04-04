from __future__ import annotations

import csv
import json
import time
from pathlib import Path
from typing import Any

import numpy as np

from .benchmark import (
    _balanced_sample_weights,
    _build_metrics,
    _build_skipped_metrics,
    _choose_threshold,
    _partition_rows_for_benchmark,
    _resolve_torch_device,
    _set_random_seeds,
    load_pairwise_dataset_rows,
)
from .calibration_eval import run_calibration_evaluation
from .regional_raster_dataset import (
    RasterConfig,
    build_raster_samples,
    stack_raster_samples,
    summarize_raster_tensor,
    truncate_rows,
)

try:
    import torch
    from torch import nn
    from torch.utils.data import DataLoader, TensorDataset, WeightedRandomSampler
except Exception:  # pragma: no cover
    torch = None
    nn = None
    DataLoader = None
    TensorDataset = None
    WeightedRandomSampler = None


if nn is not None:
    class RegionalRiskCNN(nn.Module):
        def __init__(self, in_channels: int = 5, scalar_dim: int = 5) -> None:
            super().__init__()
            self.features = nn.Sequential(
                nn.Conv2d(in_channels, 16, kernel_size=3, padding=1),
                nn.ReLU(),
                nn.MaxPool2d(2),
                nn.Conv2d(16, 32, kernel_size=3, padding=1),
                nn.ReLU(),
                nn.MaxPool2d(2),
                nn.Conv2d(32, 64, kernel_size=3, padding=1),
                nn.ReLU(),
                nn.AdaptiveAvgPool2d((1, 1)),
            )
            self.scalar_tower = nn.Sequential(
                nn.Linear(scalar_dim, 16),
                nn.ReLU(),
            )
            self.head = nn.Sequential(
                nn.Linear(64 + 16, 32),
                nn.ReLU(),
                nn.Linear(32, 1),
            )

        def forward(self, inputs: torch.Tensor, scalars: torch.Tensor) -> torch.Tensor:
            hidden = self.features(inputs)
            hidden = hidden.view(hidden.size(0), -1)
            scalar_hidden = self.scalar_tower(scalars)
            return self.head(torch.cat([hidden, scalar_hidden], dim=1))
else:  # pragma: no cover
    class RegionalRiskCNN:  # type: ignore[override]
        def __init__(self, *_: Any, **__: Any) -> None:
            raise RuntimeError("PyTorch is not installed.")


def _select_gradcam_candidate_indices(
    labels: np.ndarray,
    scores: np.ndarray,
    threshold: float,
    max_per_bucket: int = 3,
) -> list[tuple[str, int]]:
    preds = scores >= float(threshold)
    candidates: list[tuple[str, int]] = []
    bucket_defs = [
        ("tp", np.where((labels == 1) & preds)[0], lambda idx: float(scores[idx])),
        ("fp", np.where((labels == 0) & preds)[0], lambda idx: float(scores[idx])),
        ("fn", np.where((labels == 1) & (~preds))[0], lambda idx: -float(scores[idx])),
        ("tn", np.where((labels == 0) & (~preds))[0], lambda idx: float(scores[idx])),
    ]
    for bucket_name, bucket_indices, sort_key in bucket_defs:
        ordered = sorted(bucket_indices.tolist(), key=sort_key, reverse=True)
        for index in ordered[: max(0, int(max_per_bucket))]:
            candidates.append((bucket_name, int(index)))
    return candidates


def _write_gradcam_artifacts(
    output_root: Path,
    images: np.ndarray,
    scalar_features: np.ndarray,
    labels: np.ndarray,
    scores: np.ndarray,
    metadata: list[dict[str, str]],
    threshold: float,
) -> tuple[str, str]:
    artifact_npz_path = output_root.with_name(f"{output_root.name}_gradcam_candidates.npz")
    metadata_jsonl_path = output_root.with_name(f"{output_root.name}_gradcam_candidates.jsonl")
    candidates = _select_gradcam_candidate_indices(labels, scores, threshold)
    selected_images: list[np.ndarray] = []
    selected_scalars: list[np.ndarray] = []
    selected_labels: list[int] = []
    selected_scores: list[float] = []
    selected_preds: list[int] = []
    with metadata_jsonl_path.open("w", encoding="utf-8") as handle:
        for bucket_name, index in candidates:
            selected_images.append(images[index])
            selected_scalars.append(scalar_features[index])
            selected_labels.append(int(labels[index]))
            selected_scores.append(float(scores[index]))
            selected_preds.append(int(float(scores[index]) >= float(threshold)))
            row = dict(metadata[index])
            row["bucket"] = bucket_name
            row["test_index"] = str(index)
            row["score"] = f"{float(scores[index]):.6f}"
            row["pred"] = str(int(float(scores[index]) >= float(threshold)))
            handle.write(json.dumps(row, ensure_ascii=True) + "\n")
    np.savez_compressed(
        artifact_npz_path,
        images=np.stack(selected_images, axis=0).astype(np.float32) if selected_images else np.zeros((0, 5, 1, 1), dtype=np.float32),
        scalar_features=np.stack(selected_scalars, axis=0).astype(np.float32) if selected_scalars else np.zeros((0, 5), dtype=np.float32),
        labels=np.array(selected_labels, dtype=np.int64),
        scores=np.array(selected_scores, dtype=np.float32),
        preds=np.array(selected_preds, dtype=np.int64),
        threshold=np.array([float(threshold)], dtype=np.float32),
    )
    return str(artifact_npz_path), str(metadata_jsonl_path)


def _build_loader(
    images: np.ndarray,
    scalar_features: np.ndarray,
    labels: np.ndarray,
    batch_size: int,
    shuffle: bool,
    balance_batches: bool,
) -> Any:
    dataset = TensorDataset(
        torch.tensor(images, dtype=torch.float32),
        torch.tensor(scalar_features, dtype=torch.float32),
        torch.tensor(labels.reshape(-1, 1), dtype=torch.float32),
    )
    if balance_batches:
        class_weights = _balanced_sample_weights(labels).astype(np.float32)
        sampler = WeightedRandomSampler(
            weights=torch.tensor(class_weights, dtype=torch.float32),
            num_samples=len(labels),
            replacement=True,
        )
        return DataLoader(dataset, batch_size=batch_size, sampler=sampler, shuffle=False)
    return DataLoader(dataset, batch_size=batch_size, shuffle=shuffle)


if torch is not None:
    class _BinaryFocalLoss(nn.Module):
        def __init__(self, alpha_pos: float = 0.75, gamma: float = 2.0) -> None:
            super().__init__()
            self.alpha_pos = float(alpha_pos)
            self.gamma = float(gamma)

        def forward(self, logits: torch.Tensor, targets: torch.Tensor) -> torch.Tensor:
            probs = torch.sigmoid(logits)
            probs = torch.clamp(probs, min=1e-6, max=1.0 - 1e-6)
            pt = torch.where(targets >= 0.5, probs, 1.0 - probs)
            alpha_t = torch.where(
                targets >= 0.5,
                torch.full_like(targets, self.alpha_pos),
                torch.full_like(targets, 1.0 - self.alpha_pos),
            )
            focal_weight = alpha_t * torch.pow(1.0 - pt, self.gamma)
            bce = -(targets * torch.log(probs) + (1.0 - targets) * torch.log(1.0 - probs))
            return torch.mean(focal_weight * bce)


def _train_model(
    train_images: np.ndarray,
    train_scalar_features: np.ndarray,
    train_labels: np.ndarray,
    val_images: np.ndarray,
    val_scalar_features: np.ndarray,
    val_labels: np.ndarray,
    requested_device: str,
    epochs: int,
    batch_size: int,
    learning_rate: float,
    balance_batches: bool,
    loss_type: str,
    focal_gamma: float,
    random_seed: int | None,
) -> tuple[RegionalRiskCNN, np.ndarray, dict[str, Any]]:
    if torch is None or nn is None:
        raise RuntimeError("PyTorch is not installed.")
    _set_random_seeds(random_seed)
    resolved_device = _resolve_torch_device(requested_device)
    device = torch.device(resolved_device)

    model = RegionalRiskCNN(
        in_channels=int(train_images.shape[1]),
        scalar_dim=int(train_scalar_features.shape[1]),
    ).to(device)
    optimizer = torch.optim.Adam(model.parameters(), lr=float(learning_rate))
    sample_weights = _balanced_sample_weights(train_labels)
    positives = max(1.0, float(np.sum(train_labels == 1)))
    negatives = max(1.0, float(np.sum(train_labels == 0)))
    pos_weight_value = max(1e-6, negatives / positives)
    alpha_pos = negatives / (positives + negatives)
    if loss_type == "weighted_bce":
        loss_fn = nn.BCEWithLogitsLoss(pos_weight=torch.tensor([pos_weight_value], dtype=torch.float32, device=device))
    elif loss_type == "focal":
        loss_fn = _BinaryFocalLoss(alpha_pos=alpha_pos, gamma=float(focal_gamma))
    else:
        raise ValueError(f"Unsupported loss_type: {loss_type}")

    train_loader = _build_loader(
        train_images,
        train_scalar_features,
        train_labels,
        batch_size=batch_size,
        shuffle=True,
        balance_batches=balance_batches,
    )
    x_val = torch.tensor(val_images, dtype=torch.float32, device=device)
    x_val_scalars = torch.tensor(val_scalar_features, dtype=torch.float32, device=device)
    y_val_tensor = torch.tensor(val_labels.reshape(-1, 1), dtype=torch.float32, device=device)

    best_state = None
    best_val_loss = float("inf")
    for _ in range(int(epochs)):
        model.train()
        for batch_inputs, batch_scalars, batch_targets in train_loader:
            batch_inputs = batch_inputs.to(device)
            batch_scalars = batch_scalars.to(device)
            batch_targets = batch_targets.to(device)
            optimizer.zero_grad(set_to_none=True)
            logits = model(batch_inputs, batch_scalars)
            loss = loss_fn(logits, batch_targets)
            loss.backward()
            optimizer.step()

        model.eval()
        with torch.no_grad():
            val_logits = model(x_val, x_val_scalars)
            val_loss = float(loss_fn(val_logits, y_val_tensor).item())
        if val_loss < best_val_loss:
            best_val_loss = val_loss
            best_state = {key: value.detach().cpu().clone() for key, value in model.state_dict().items()}

    if best_state is not None:
        model.load_state_dict(best_state)
    model.eval()
    with torch.no_grad():
        val_scores = torch.sigmoid(model(x_val, x_val_scalars)).detach().cpu().numpy().reshape(-1)
    return model, val_scores, {
        "device": resolved_device,
        "epochs": int(epochs),
        "batch_size": int(batch_size),
        "learning_rate": float(learning_rate),
        "balance_batches": bool(balance_batches),
        "loss_type": str(loss_type),
        "focal_gamma": float(focal_gamma),
    }


def _predict_scores(model: RegionalRiskCNN, images: np.ndarray, scalar_features: np.ndarray, requested_device: str) -> np.ndarray:
    resolved_device = _resolve_torch_device(requested_device)
    device = torch.device(resolved_device)
    model = model.to(device)
    model.eval()
    with torch.no_grad():
        tensor = torch.tensor(images, dtype=torch.float32, device=device)
        scalar_tensor = torch.tensor(scalar_features, dtype=torch.float32, device=device)
        scores = torch.sigmoid(model(tensor, scalar_tensor)).detach().cpu().numpy().reshape(-1)
    return scores


def _predict_logits(model: RegionalRiskCNN, images: np.ndarray, scalar_features: np.ndarray, requested_device: str) -> np.ndarray:
    resolved_device = _resolve_torch_device(requested_device)
    device = torch.device(resolved_device)
    model = model.to(device)
    model.eval()
    with torch.no_grad():
        tensor = torch.tensor(images, dtype=torch.float32, device=device)
        scalar_tensor = torch.tensor(scalar_features, dtype=torch.float32, device=device)
        logits = model(tensor, scalar_tensor).detach().cpu().numpy().reshape(-1)
    return logits


def _binary_log_loss_from_logits(y_true: np.ndarray, logits: np.ndarray) -> float:
    signed = np.where(y_true.astype(np.float64) >= 0.5, 1.0, -1.0)
    margin = signed * logits.astype(np.float64)
    return float(np.mean(np.logaddexp(0.0, -margin)))


def _sigmoid_np(values: np.ndarray) -> np.ndarray:
    return 1.0 / (1.0 + np.exp(-np.clip(values, -30.0, 30.0)))


def _fit_temperature_from_val_logits(val_logits: np.ndarray, val_labels: np.ndarray) -> float:
    candidates = np.exp(np.linspace(np.log(0.25), np.log(8.0), num=31))
    best_temperature = 1.0
    best_loss = float("inf")
    for candidate in candidates:
        scaled_logits = val_logits / float(candidate)
        current_loss = _binary_log_loss_from_logits(val_labels, scaled_logits)
        if current_loss < best_loss:
            best_loss = current_loss
            best_temperature = float(candidate)
    return float(best_temperature)


def build_regional_raster_cnn_summary_markdown(summary: dict[str, Any]) -> str:
    metrics = summary["metrics"]
    lines = [
        "# Regional Raster CNN Baseline Summary",
        "",
        "## Inputs",
        "",
        f"- input_csv: `{summary['input_csv_path']}`",
        f"- split_strategy: `{summary['split_strategy']}`",
        f"- train_fraction: `{summary['train_fraction']:.2f}`",
        f"- val_fraction: `{summary['val_fraction']:.2f}`",
        f"- raster_size: `{summary['raster_config']['raster_size']}`",
        f"- half_width_nm: `{summary['raster_config']['half_width_nm']:.2f}`",
        "",
        "## Split",
        "",
        f"- train_rows: `{summary['split_summary']['train_rows']}`",
        f"- val_rows: `{summary['split_summary']['val_rows']}`",
        f"- test_rows: `{summary['split_summary']['test_rows']}`",
        "",
        "## Metrics",
        "",
    ]
    if metrics.get("status") == "skipped":
        lines.append(f"- status: skipped ({metrics['reason']})")
    else:
        lines.extend(
            [
                f"- threshold: `{metrics['threshold']:.2f}`",
                f"- f1: `{metrics['f1']:.4f}`",
                f"- precision: `{metrics['precision']:.4f}`",
                f"- recall: `{metrics['recall']:.4f}`",
                f"- auroc: `{metrics['auroc']:.4f}`" if metrics.get("auroc") is not None else "- auroc: `None`",
                f"- auprc: `{metrics['auprc']:.4f}`" if metrics.get("auprc") is not None else "- auprc: `None`",
            ]
        )
    temp_metrics = summary.get("temperature_scaling", {}).get("metrics", {})
    lines.extend(
        [
            "",
            "## Temperature Scaling",
            "",
            f"- temperature: `{summary.get('temperature_scaling', {}).get('temperature', 'unknown')}`",
        ]
    )
    if temp_metrics.get("status") == "skipped":
        lines.append(f"- status: skipped ({temp_metrics['reason']})")
    else:
        lines.extend(
            [
                f"- threshold: `{temp_metrics['threshold']:.2f}`",
                f"- f1: `{temp_metrics['f1']:.4f}`",
                f"- precision: `{temp_metrics['precision']:.4f}`",
                f"- recall: `{temp_metrics['recall']:.4f}`",
                f"- auroc: `{temp_metrics['auroc']:.4f}`" if temp_metrics.get("auroc") is not None else "- auroc: `None`",
                f"- auprc: `{temp_metrics['auprc']:.4f}`" if temp_metrics.get("auprc") is not None else "- auprc: `None`",
            ]
        )
    raw_cal = summary.get("calibration_metrics", {})
    temp_cal = summary.get("temperature_scaled_calibration_metrics", {})
    lines.extend(
        [
            "",
            "## Training",
            "",
            f"- device: `{summary['training_info'].get('device', 'unknown')}`",
            f"- epochs: `{summary['training_info'].get('epochs', 'unknown')}`",
            f"- batch_size: `{summary['training_info'].get('batch_size', 'unknown')}`",
            f"- balance_batches: `{summary['training_info'].get('balance_batches', 'unknown')}`",
            f"- loss_type: `{summary['training_info'].get('loss_type', 'unknown')}`",
            f"- focal_gamma: `{summary['training_info'].get('focal_gamma', 'unknown')}`",
            "",
            "## Calibration",
            "",
            f"- raw_brier: `{raw_cal.get('brier_score', 'unknown')}`",
            f"- raw_ece: `{raw_cal.get('ece', 'unknown')}`",
            f"- temp_brier: `{temp_cal.get('brier_score', 'unknown')}`",
            f"- temp_ece: `{temp_cal.get('ece', 'unknown')}`",
            "",
            "## Outputs",
            "",
            f"- summary_json: `{summary['summary_json_path']}`",
            f"- summary_md: `{summary['summary_md_path']}`",
            f"- predictions_csv: `{summary['predictions_csv_path']}`",
            f"- calibration_summary_json: `{summary['calibration_summary_json_path']}`",
            f"- checkpoint_pt: `{summary['checkpoint_path']}`",
            f"- gradcam_candidates_npz: `{summary['gradcam_candidates_npz_path']}`",
            f"- gradcam_candidates_jsonl: `{summary['gradcam_candidates_jsonl_path']}`",
            "",
        ]
    )
    return "\n".join(lines)


def run_regional_raster_cnn_benchmark(
    input_path: str | Path,
    output_prefix: str | Path,
    split_strategy: str = "own_ship",
    train_fraction: float = 0.6,
    val_fraction: float = 0.2,
    half_width_nm: float = 3.0,
    raster_size: int = 64,
    torch_device: str = "auto",
    random_seed: int | None = 42,
    epochs: int = 20,
    batch_size: int = 64,
    learning_rate: float = 1e-3,
    balance_batches: bool = True,
    loss_type: str = "weighted_bce",
    focal_gamma: float = 2.0,
    max_train_rows: int | None = None,
    max_val_rows: int | None = None,
    max_test_rows: int | None = None,
) -> dict[str, Any]:
    rows = load_pairwise_dataset_rows(input_path)
    train_rows, val_rows, test_rows, split_summary = _partition_rows_for_benchmark(
        rows=rows,
        split_strategy=split_strategy,
        train_fraction=train_fraction,
        val_fraction=val_fraction,
    )
    train_rows = truncate_rows(train_rows, max_train_rows)
    val_rows = truncate_rows(val_rows, max_val_rows)
    test_rows = truncate_rows(test_rows, max_test_rows)
    if not train_rows or not val_rows or not test_rows:
        raise ValueError("Train/val/test rows must all remain non-empty after truncation.")

    output_root = Path(output_prefix)
    output_root.parent.mkdir(parents=True, exist_ok=True)
    config = RasterConfig(half_width_nm=float(half_width_nm), raster_size=int(raster_size))

    train_samples = build_raster_samples(train_rows, config)
    val_samples = build_raster_samples(val_rows, config)
    test_samples = build_raster_samples(test_rows, config)
    train_images, train_scalar_features, train_labels, train_metadata = stack_raster_samples(train_samples)
    val_images, val_scalar_features, val_labels, _ = stack_raster_samples(val_samples)
    test_images, test_scalar_features, test_labels, test_metadata = stack_raster_samples(test_samples)

    started = time.perf_counter()
    checkpoint_path = output_root.with_name(f"{output_root.name}_checkpoint.pt")
    if len(np.unique(train_labels)) < 2:
        metrics = _build_skipped_metrics("train split has only one class")
        training_info: dict[str, Any] = {"device": "n/a", "epochs": 0, "batch_size": int(batch_size)}
        test_scores = np.zeros_like(test_labels, dtype=np.float32)
        if torch is not None:
            torch.save({}, checkpoint_path)
    else:
        model, val_scores, training_info = _train_model(
            train_images=train_images,
            train_scalar_features=train_scalar_features,
            train_labels=train_labels,
            val_images=val_images,
            val_scalar_features=val_scalar_features,
            val_labels=val_labels,
            requested_device=torch_device,
            epochs=epochs,
            batch_size=batch_size,
            learning_rate=learning_rate,
            balance_batches=balance_batches,
            loss_type=loss_type,
            focal_gamma=focal_gamma,
            random_seed=random_seed,
        )
        threshold = _choose_threshold(val_labels, val_scores)
        val_logits = _predict_logits(model, val_images, val_scalar_features, requested_device=torch_device)
        test_logits = _predict_logits(model, test_images, test_scalar_features, requested_device=torch_device)
        test_scores = _sigmoid_np(test_logits)
        metrics = _build_metrics(test_labels, test_scores, threshold)
        metrics["elapsed_seconds"] = float(time.perf_counter() - started)
        temperature_value = _fit_temperature_from_val_logits(val_logits, val_labels)
        val_scores_temp = _sigmoid_np(val_logits / temperature_value)
        test_scores_temp = _sigmoid_np(test_logits / temperature_value)
        threshold_temp = _choose_threshold(val_labels, val_scores_temp)
        metrics_temp = _build_metrics(test_labels, test_scores_temp, threshold_temp)
        torch.save(
            {
                "model_state_dict": model.state_dict(),
                "in_channels": int(train_images.shape[1]),
                "scalar_dim": int(train_scalar_features.shape[1]),
            },
            checkpoint_path,
        )

    if len(np.unique(train_labels)) < 2:
        temperature_value = 1.0
        test_scores_temp = np.zeros_like(test_labels, dtype=np.float32)
        metrics_temp = _build_skipped_metrics("train split has only one class")

    predictions_csv_path = output_root.with_name(f"{output_root.name}_predictions.csv")
    with predictions_csv_path.open("w", encoding="utf-8", newline="") as handle:
        fieldnames = [
            "timestamp",
            "own_mmsi",
            "target_mmsi",
            "label_future_conflict",
            "cnn_score",
            "cnn_pred",
            "cnn_temp_score",
            "cnn_temp_pred",
        ]
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        threshold_value = float(metrics.get("threshold", 0.5)) if metrics.get("status") != "skipped" else 0.5
        threshold_temp_value = float(metrics_temp.get("threshold", 0.5)) if metrics_temp.get("status") != "skipped" else 0.5
        for meta, label, score, score_temp in zip(test_metadata, test_labels, test_scores, test_scores_temp, strict=False):
            writer.writerow(
                {
                    "timestamp": meta["timestamp"],
                    "own_mmsi": meta["own_mmsi"],
                    "target_mmsi": meta["target_mmsi"],
                    "label_future_conflict": int(label),
                    "cnn_score": f"{float(score):.6f}",
                    "cnn_pred": int(float(score) >= threshold_value),
                    "cnn_temp_score": f"{float(score_temp):.6f}",
                    "cnn_temp_pred": int(float(score_temp) >= threshold_temp_value),
                }
            )

    gradcam_candidates_npz_path, gradcam_candidates_jsonl_path = _write_gradcam_artifacts(
        output_root=output_root,
        images=test_images,
        scalar_features=test_scalar_features,
        labels=test_labels,
        scores=test_scores,
        metadata=test_metadata,
        threshold=threshold_value,
    )
    calibration_prefix = output_root.with_name(f"{output_root.name}_calibration")
    calibration_summary = run_calibration_evaluation(
        predictions_csv_path=predictions_csv_path,
        output_prefix=calibration_prefix,
        model_names=["cnn", "cnn_temp"],
        num_bins=10,
    )

    summary = {
        "status": "completed",
        "input_csv_path": str(Path(input_path).resolve()),
        "output_prefix": str(output_root),
        "split_strategy": split_strategy,
        "train_fraction": float(train_fraction),
        "val_fraction": float(val_fraction),
        "split_summary": split_summary,
        "raster_config": {
            "half_width_nm": float(config.half_width_nm),
            "raster_size": int(config.raster_size),
            "occupancy_clip": float(config.occupancy_clip),
            "speed_clip": float(config.speed_clip),
        },
        "train_raster_summary": summarize_raster_tensor(train_images),
        "val_raster_summary": summarize_raster_tensor(val_images),
        "test_raster_summary": summarize_raster_tensor(test_images),
        "training_info": training_info,
        "metrics": metrics,
        "temperature_scaling": {
            "temperature": float(temperature_value),
            "metrics": metrics_temp,
        },
        "predictions_csv_path": str(predictions_csv_path),
        "calibration_summary_json_path": str(calibration_summary["summary_json_path"]),
        "calibration_summary_md_path": str(calibration_summary["summary_md_path"]),
        "calibration_bins_csv_path": str(calibration_summary["calibration_bins_csv_path"]),
        "calibration_metrics": calibration_summary["models"]["cnn"],
        "temperature_scaled_calibration_metrics": calibration_summary["models"]["cnn_temp"],
        "checkpoint_path": str(checkpoint_path),
        "gradcam_candidates_npz_path": gradcam_candidates_npz_path,
        "gradcam_candidates_jsonl_path": gradcam_candidates_jsonl_path,
    }
    summary_json_path = output_root.with_name(f"{output_root.name}_summary.json")
    summary_md_path = output_root.with_name(f"{output_root.name}_summary.md")
    summary["summary_json_path"] = str(summary_json_path)
    summary["summary_md_path"] = str(summary_md_path)
    summary_json_path.write_text(json.dumps(summary, indent=2), encoding="utf-8")
    summary_md_path.write_text(build_regional_raster_cnn_summary_markdown(summary), encoding="utf-8")
    return summary
