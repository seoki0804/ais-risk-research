from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
from typing import Any


def _read_json(path: str | Path) -> dict[str, Any]:
    return json.loads(Path(path).read_text(encoding="utf-8"))


def _fmt(value: Any, digits: int = 4) -> str:
    if value is None:
        return "n/a"
    if isinstance(value, float):
        return f"{value:.{digits}f}"
    return str(value)


def _select_best_model(summary: dict[str, Any]) -> tuple[str, dict[str, Any]] | tuple[None, None]:
    best_name = None
    best_metrics = None
    best_f1 = -1.0
    for model_name, metrics in summary.get("models", {}).items():
        if metrics.get("status") == "skipped":
            continue
        current_f1 = float(metrics.get("f1", -1.0))
        if current_f1 > best_f1:
            best_name = model_name
            best_metrics = metrics
            best_f1 = current_f1
    return best_name, best_metrics


def _build_model_bullets(summary: dict[str, Any]) -> list[str]:
    bullets: list[str] = []
    for model_name, metrics in summary.get("models", {}).items():
        if metrics.get("status") == "skipped":
            bullets.append(f"- `{model_name}`: skipped, reason=`{metrics['reason']}`")
            continue
        extras = []
        if metrics.get("device"):
            extras.append(f"device={metrics['device']}")
        bullets.append(
            "- `{name}`: AUROC={auroc}, AUPRC={auprc}, F1={f1}, Precision={precision}, Recall={recall}{extra}".format(
                name=model_name,
                auroc=_fmt(metrics.get("auroc")),
                auprc=_fmt(metrics.get("auprc")),
                f1=_fmt(metrics.get("f1")),
                precision=_fmt(metrics.get("precision")),
                recall=_fmt(metrics.get("recall")),
                extra=f", {', '.join(extras)}" if extras else "",
            )
        )
    return bullets


def _clean_manifest_value(text: str) -> str:
    return text.strip().strip("`").strip()


def build_benchmark_research_log(
    benchmark_summary_path: str | Path,
    output_path: str | Path,
    pairwise_stats_path: str | Path | None = None,
    dataset_manifest_path: str | Path | None = None,
    date_text: str | None = None,
    author: str = "Codex",
    topic: str = "pairwise_benchmark",
    area_text: str | None = None,
    config_text: str = "configs/base.toml",
) -> str:
    benchmark_summary = _read_json(benchmark_summary_path)
    pairwise_stats = _read_json(pairwise_stats_path) if pairwise_stats_path else {}
    dataset_manifest_exists = dataset_manifest_path is not None and Path(dataset_manifest_path).exists()
    dataset_manifest_text = Path(dataset_manifest_path).read_text(encoding="utf-8") if dataset_manifest_exists else ""

    log_date = date_text or datetime.now().date().isoformat()
    best_model_name, best_model_metrics = _select_best_model(benchmark_summary)

    area_value = area_text or "TBD"
    dataset_id = "unknown_dataset"
    if dataset_manifest_exists:
        for line in dataset_manifest_text.splitlines():
            if line.lower().startswith("- dataset_id:"):
                dataset_id = _clean_manifest_value(line.split(":", 1)[1]) or dataset_id
            if line.lower().startswith("| 해역 |"):
                candidate = _clean_manifest_value(line.split("|")[2])
                if candidate:
                    area_value = candidate
    elif pairwise_stats.get("dataset_path"):
        dataset_id = Path(str(pairwise_stats["dataset_path"])).stem

    model_lines = _build_model_bullets(benchmark_summary)
    best_model_line = "없음"
    if best_model_name and best_model_metrics:
        best_model_line = (
            f"`{best_model_name}` (F1={_fmt(best_model_metrics.get('f1'))}, "
            f"AUROC={_fmt(best_model_metrics.get('auroc'))}, "
            f"AUPRC={_fmt(best_model_metrics.get('auprc'))})"
        )
    split_info = benchmark_summary.get("split", {})
    split_strategy = split_info.get("strategy", "timestamp")
    split_line = (
        f"{split_strategy} split, train/val/test = "
        f"`{split_info.get('train_rows', 0)}` / `{split_info.get('val_rows', 0)}` / `{split_info.get('test_rows', 0)}` rows"
    )
    if split_strategy == "own_ship":
        split_line = (
            f"own_ship split, train/val/test own ships = "
            f"`{split_info.get('train_own_ships', 0)}` / `{split_info.get('val_own_ships', 0)}` / `{split_info.get('test_own_ships', 0)}`, "
            f"rows = `{split_info.get('train_rows', 0)}` / `{split_info.get('val_rows', 0)}` / `{split_info.get('test_rows', 0)}`"
        )

    future_distance_summary = pairwise_stats.get("future_min_distance_summary") or {}
    text = f"""# {log_date} {topic}

## 0. 기본 정보

- 날짜: {log_date}
- 작성자: {author}
- 로그 유형: `daily`
- dataset_id: `{dataset_id}`
- 해역: {area_value}
- 기간: [추가 검증 필요]
- config: `{config_text}`
- model: `rule_score, logreg, hgbt, torch_mlp(optional)`
- output path: `{benchmark_summary.get('summary_json_path', benchmark_summary_path)}`

## 1. 오늘의 목표

- pairwise learning dataset을 만들고 baseline 대비 comparator가 같은 split에서 어떻게 보이는지 확인한다.
- realized future separation label을 기준으로 current-state feature의 예측 가능성을 점검한다.
- 실데이터 benchmark를 남길 수 있는 연구일지 포맷을 고정한다.

## 2. 실행 내용

| 항목 | 내용 |
|---|---|
| 입력 데이터 | `{benchmark_summary['input_path']}` |
| own ship bundle | pairwise dataset 내부 own ship aggregate |
| split | {split_line} |
| scenario | pairwise classifier benchmark, spatial projection 후속 연결 |
| 실행 모델 | {", ".join(benchmark_summary.get("models", {}).keys())} |

## 3. 핵심 결과

| 지표/관찰 | 값 또는 설명 |
|---|---|
| row count | `{benchmark_summary['row_count']}` |
| positive rate | `{_fmt(benchmark_summary['positive_rate'])}` |
| future separation min/median/max | `{_fmt(future_distance_summary.get('min_nm'))}` / `{_fmt(future_distance_summary.get('median_nm'))}` / `{_fmt(future_distance_summary.get('max_nm'))}` NM |
| best model | {best_model_line} |
| rule baseline 상태 | `rule_score` benchmark 포함 |

## 4. 모델별 결과

{chr(10).join(model_lines)}

## 5. 해석

- [확정] pairwise benchmark는 same split에서 baseline과 comparator를 비교할 수 있게 준비되었다.
- [확정] 현재 구현은 `realized future separation`을 label로 사용하므로, 단순 current-state DCPA/TCPA self-reconstruction보다는 validation narrative가 낫다.
- [합리적 가정] best model이 baseline보다 개선되더라도, spatial projection 이후의 설명 가능성 검토가 반드시 뒤따라야 한다.
- [리스크] dataset 규모가 작거나 쉬우면 ML 지표가 과하게 높게 나올 수 있다.
- [추가 검증 필요] 실제 해역에서는 own ship holdout과 area holdout까지 붙여야 한다.

## 6. 실패 또는 이상 현상

- sample-like dataset에서는 지나치게 쉬운 분포가 생길 수 있어 metric이 과대평가될 수 있다.
- label threshold가 잘못 잡히면 단일 클래스 dataset이 만들어질 수 있다.

## 7. 결정사항

- 유지: realized future separation label 기반 pairwise benchmark 구조
- 변경: 실데이터에서는 label threshold를 future distance summary를 보고 정한다
- 보류: complex deep learning comparator

## 8. 다음 액션

1. 첫 실데이터 source를 확정하고 dataset manifest를 채운다.
2. 같은 benchmark를 multi own-ship bundle로 재실행한다.
3. best pairwise comparator를 spatial projection 후단에 연결해 case review를 남긴다.

## 9. 교수/면접관에게 설명한다면

- "pairwise 모델은 현재 상태로 미래 realized minimum separation을 맞추는 comparator이고, 최종 평가는 이것을 own-ship-centric spatial map으로 투영했을 때 설명력이 늘어나는지까지 본다."
"""

    destination = Path(output_path)
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_text(text, encoding="utf-8")
    return str(destination)
