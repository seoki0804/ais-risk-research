from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import numpy as np

from .benchmark import _resolve_torch_device
from .regional_raster_cnn import RegionalRiskCNN

try:
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
except Exception:  # pragma: no cover
    matplotlib = None
    plt = None

try:
    import torch
    import torch.nn.functional as F
except Exception:  # pragma: no cover
    torch = None
    F = None


def _load_metadata_jsonl(path: str | Path) -> list[dict[str, str]]:
    rows: list[dict[str, str]] = []
    with Path(path).open("r", encoding="utf-8") as handle:
        for line in handle:
            text = line.strip()
            if text:
                rows.append(json.loads(text))
    return rows


def _select_report_indices(metadata_rows: list[dict[str, str]]) -> list[int]:
    bucket_to_indices: dict[str, list[int]] = {}
    for index, row in enumerate(metadata_rows):
        bucket_to_indices.setdefault(str(row.get("bucket", "")), []).append(index)
    selected: list[int] = []
    for preferred_bucket in ("tp", "tn"):
        if bucket_to_indices.get(preferred_bucket):
            selected.append(bucket_to_indices[preferred_bucket][0])
            break
    for preferred_bucket in ("fp", "fn"):
        if bucket_to_indices.get(preferred_bucket):
            candidate = bucket_to_indices[preferred_bucket][0]
            if candidate not in selected:
                selected.append(candidate)
            break
    if not selected and metadata_rows:
        selected.append(0)
    return selected


def _find_last_conv_layer(model: RegionalRiskCNN) -> torch.nn.Module:
    for module in reversed(list(model.modules())):
        if isinstance(module, torch.nn.Conv2d):
            return module
    raise ValueError("RegionalRiskCNN does not contain a Conv2d layer.")


def _compute_gradcam(
    model: RegionalRiskCNN,
    image: np.ndarray,
    scalar_features: np.ndarray,
    device: str,
) -> np.ndarray:
    if torch is None or F is None:
        raise RuntimeError("PyTorch is required for Grad-CAM report generation.")
    resolved_device = _resolve_torch_device(device)
    torch_device = torch.device(resolved_device)
    model = model.to(torch_device)
    model.eval()

    activations: dict[str, torch.Tensor] = {}
    gradients: dict[str, torch.Tensor] = {}
    layer = _find_last_conv_layer(model)

    def forward_hook(_: torch.nn.Module, __: tuple[torch.Tensor, ...], output: torch.Tensor) -> None:
        activations["value"] = output

    def backward_hook(_: torch.nn.Module, __: tuple[torch.Tensor, ...], grad_output: tuple[torch.Tensor, ...]) -> None:
        gradients["value"] = grad_output[0]

    forward_handle = layer.register_forward_hook(forward_hook)
    backward_handle = layer.register_full_backward_hook(backward_hook)
    try:
        image_tensor = torch.tensor(image[None, ...], dtype=torch.float32, device=torch_device)
        scalar_tensor = torch.tensor(scalar_features[None, ...], dtype=torch.float32, device=torch_device)
        model.zero_grad(set_to_none=True)
        logit = model(image_tensor, scalar_tensor)[0, 0]
        logit.backward()
        activation_value = activations["value"]
        gradient_value = gradients["value"]
        weights = gradient_value.mean(dim=(2, 3), keepdim=True)
        cam = torch.relu((weights * activation_value).sum(dim=1, keepdim=True))
        cam = F.interpolate(cam, size=image_tensor.shape[-2:], mode="bilinear", align_corners=False)
        cam_np = cam.detach().cpu().numpy()[0, 0]
        if float(np.max(cam_np)) > float(np.min(cam_np)):
            cam_np = (cam_np - float(np.min(cam_np))) / (float(np.max(cam_np)) - float(np.min(cam_np)))
        else:
            cam_np = np.zeros_like(cam_np, dtype=np.float32)
        return cam_np.astype(np.float32)
    finally:
        forward_handle.remove()
        backward_handle.remove()


def _plot_case(
    axes: Any,
    image: np.ndarray,
    cam: np.ndarray,
    meta: dict[str, str],
    label: int,
    score: float,
    pred: int,
) -> None:
    occupancy = image[0]
    rule_map = image[1]
    focal_mask = image[3]
    focal_positions = np.argwhere(focal_mask > 0.5)
    focal_point = focal_positions[0] if len(focal_positions) else None

    panels = [
        ("Occupancy", occupancy, "Greys"),
        ("Rule Score", rule_map, "viridis"),
        ("Grad-CAM", occupancy, "Greys"),
    ]
    for axis, (title, panel, cmap) in zip(axes, panels, strict=False):
        axis.imshow(panel, cmap=cmap, interpolation="nearest")
        if title == "Grad-CAM":
            axis.imshow(cam, cmap="jet", alpha=0.55, interpolation="bilinear")
        if focal_point is not None:
            axis.scatter([focal_point[1]], [focal_point[0]], c="red", s=20, marker="x")
        axis.set_xticks([])
        axis.set_yticks([])
        axis.set_title(title, fontsize=9)

    axes[0].set_ylabel(
        "\n".join(
            [
                f"{meta.get('bucket', 'case').upper()}",
                f"{meta.get('timestamp', '')}",
                f"own={meta.get('own_mmsi', '')}",
                f"target={meta.get('target_mmsi', '')}",
                f"label={label} pred={pred}",
                f"score={score:.3f}",
            ]
        ),
        fontsize=8,
    )


def _build_summary_markdown(summary: dict[str, Any]) -> str:
    lines = [
        "# Regional Grad-CAM Report",
        "",
        "## Inputs",
        "",
        f"- benchmark_summary_json: `{summary['benchmark_summary_json_path']}`",
        f"- checkpoint_pt: `{summary['checkpoint_path']}`",
        f"- candidate_npz: `{summary['gradcam_candidates_npz_path']}`",
        f"- candidate_jsonl: `{summary['gradcam_candidates_jsonl_path']}`",
        "",
        "## Selected Cases",
        "",
    ]
    for case in summary["selected_cases"]:
        lines.extend(
            [
                f"- {case['bucket']}: `{case['timestamp']}__{case['own_mmsi']}__{case['target_mmsi']}`",
                f"  - label=`{case['label']}` pred=`{case['pred']}` score=`{case['score']:.4f}`",
            ]
        )
    lines.extend(
        [
            "",
            "## Outputs",
            "",
            f"- figure_png: `{summary['figure_png_path']}`",
            f"- figure_svg: `{summary['figure_svg_path']}`",
            f"- summary_json: `{summary['summary_json_path']}`",
            f"- summary_md: `{summary['summary_md_path']}`",
            "",
        ]
    )
    return "\n".join(lines)


def run_regional_gradcam_report(
    benchmark_summary_json_path: str | Path,
    output_prefix: str | Path,
    torch_device: str = "auto",
) -> dict[str, Any]:
    if torch is None or plt is None:
        raise RuntimeError("PyTorch and matplotlib are required for Grad-CAM report generation.")
    benchmark_summary = json.loads(Path(benchmark_summary_json_path).read_text(encoding="utf-8"))
    checkpoint_path = Path(benchmark_summary["checkpoint_path"])
    candidate_npz_path = Path(benchmark_summary["gradcam_candidates_npz_path"])
    candidate_jsonl_path = Path(benchmark_summary["gradcam_candidates_jsonl_path"])
    artifacts = np.load(candidate_npz_path, allow_pickle=False)
    images = artifacts["images"].astype(np.float32)
    scalar_features = artifacts["scalar_features"].astype(np.float32)
    labels = artifacts["labels"].astype(np.int64)
    scores = artifacts["scores"].astype(np.float32)
    preds = artifacts["preds"].astype(np.int64)
    metadata_rows = _load_metadata_jsonl(candidate_jsonl_path)

    checkpoint = torch.load(checkpoint_path, map_location="cpu")
    model = RegionalRiskCNN(
        in_channels=int(checkpoint.get("in_channels", images.shape[1] if images.ndim == 4 else 5)),
        scalar_dim=int(checkpoint.get("scalar_dim", scalar_features.shape[1] if scalar_features.ndim == 2 else 5)),
    )
    if checkpoint.get("model_state_dict"):
        model.load_state_dict(checkpoint["model_state_dict"])

    selected_indices = _select_report_indices(metadata_rows)
    output_root = Path(output_prefix)
    output_root.parent.mkdir(parents=True, exist_ok=True)

    fig, axes = plt.subplots(
        nrows=len(selected_indices),
        ncols=3,
        figsize=(9.0, max(3.0, 3.0 * len(selected_indices))),
        squeeze=False,
    )
    selected_cases: list[dict[str, Any]] = []
    for row_index, case_index in enumerate(selected_indices):
        cam = _compute_gradcam(
            model=model,
            image=images[case_index],
            scalar_features=scalar_features[case_index],
            device=torch_device,
        )
        meta = metadata_rows[case_index]
        label = int(labels[case_index])
        pred = int(preds[case_index])
        score = float(scores[case_index])
        _plot_case(axes[row_index], images[case_index], cam, meta, label, score, pred)
        selected_cases.append(
            {
                "bucket": str(meta.get("bucket", "")),
                "timestamp": str(meta.get("timestamp", "")),
                "own_mmsi": str(meta.get("own_mmsi", "")),
                "target_mmsi": str(meta.get("target_mmsi", "")),
                "label": label,
                "pred": pred,
                "score": score,
            }
        )
    fig.suptitle("Regional Raster CNN Grad-CAM", fontsize=12)
    fig.tight_layout()

    figure_png_path = output_root.with_name(f"{output_root.name}_figure.png")
    figure_svg_path = output_root.with_name(f"{output_root.name}_figure.svg")
    fig.savefig(figure_png_path, dpi=180, bbox_inches="tight")
    fig.savefig(figure_svg_path, bbox_inches="tight")
    plt.close(fig)

    summary = {
        "status": "completed",
        "benchmark_summary_json_path": str(Path(benchmark_summary_json_path).resolve()),
        "checkpoint_path": str(checkpoint_path),
        "gradcam_candidates_npz_path": str(candidate_npz_path),
        "gradcam_candidates_jsonl_path": str(candidate_jsonl_path),
        "selected_cases": selected_cases,
        "figure_png_path": str(figure_png_path),
        "figure_svg_path": str(figure_svg_path),
    }
    summary_json_path = output_root.with_name(f"{output_root.name}_summary.json")
    summary_md_path = output_root.with_name(f"{output_root.name}_summary.md")
    summary["summary_json_path"] = str(summary_json_path)
    summary["summary_md_path"] = str(summary_md_path)
    summary_json_path.write_text(json.dumps(summary, indent=2), encoding="utf-8")
    summary_md_path.write_text(_build_summary_markdown(summary), encoding="utf-8")
    return summary
