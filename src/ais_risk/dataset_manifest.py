from __future__ import annotations

import re
from datetime import date
from pathlib import Path
from typing import Any


def build_dataset_id(
    source_slug: str,
    area_slug: str,
    start_date_text: str,
    end_date_text: str,
    version: str = "v1",
) -> str:
    return f"{source_slug}_{area_slug}_{start_date_text}_{end_date_text}_{version}"


def build_first_dataset_manifest_markdown(
    dataset_id: str,
    source_name: str,
    source_url: str,
    license_url: str,
    area: str,
    start_date_text: str,
    end_date_text: str,
    source_type: str = "historical CSV",
    status_tag: str = "[합리적 가정]",
    author: str = "Codex",
    created_date: str | None = None,
    notes: str = "",
    source_preset: str = "auto",
    vessel_type_filter: str = "cargo,tanker,tug,passenger",
    split_gap_min: int = 10,
    max_interp_gap_min: int = 2,
    step_sec: int = 30,
    raw_root: str = "data/raw",
    curated_root: str = "data/curated",
    outputs_root: str = "outputs",
) -> str:
    created = created_date or date.today().isoformat()
    note_line = notes.strip() if notes.strip() else "[추가 검증 필요]"

    raw_csv_path = f"{raw_root}/{dataset_id}/raw.csv"
    curated_csv_path = f"{curated_root}/{dataset_id}_curated.csv"
    tracks_csv_path = f"{curated_root}/{dataset_id}_tracks.csv"
    probe_json_path = f"{outputs_root}/{dataset_id}_probe.json"
    workflow_dir = f"{outputs_root}/{dataset_id}_workflow"

    return f"""# First Public AIS Dataset Manifest

## 0. 기본 정보

- dataset_id: `{dataset_id}`
- 작성일: {created}
- 작성자: {author}
- source name: {source_name}
- source URL: {source_url}
- license / terms URL: {license_url}
- source type: `{source_type}`
- status: {status_tag}

## 1. 왜 이 소스를 고르는가

- 프로젝트 적합성: [확정] own-ship-centric AIS spatial risk validation에 필요한 raw point/track 데이터를 확보하기 위함.
- own ship 추적 적합성: [추가 검증 필요] stable identifier(MMSI 또는 동등 식별자) 확인 필요.
- 보류 대안: [추가 검증 필요]

## 2. 커버리지

| 항목 | 값 |
|---|---|
| 해역 | {area} |
| bbox | [추가 검증 필요] |
| 시작 시각 | {start_date_text} |
| 종료 시각 | {end_date_text} |
| raw 파일 개수 | [추가 검증 필요] |
| raw 총 용량 | [추가 검증 필요] |

## 3. 스키마 점검

| 항목 | 결과 |
|---|---|
| vessel id column | [추가 검증 필요] |
| timestamp column | [추가 검증 필요] |
| lat/lon column | [추가 검증 필요] |
| sog/cog column | [추가 검증 필요] |
| heading availability | [추가 검증 필요] |
| vessel_type availability | [추가 검증 필요] |
| stable identifier 여부 | [추가 검증 필요] |

## 4. 전처리 계획

| 항목 | 값 |
|---|---|
| source preset | `{source_preset}` |
| column override | [추가 검증 필요] |
| vessel type filter | `{vessel_type_filter}` |
| bbox filter | [추가 검증 필요] |
| time filter | `{start_date_text} ~ {end_date_text}` |
| split gap min | `{split_gap_min}` |
| max interp gap min | `{max_interp_gap_min}` |
| step sec | `{step_sec}` |

## 5. 리스크 메모

- {note_line}

## 6. 실행 기록

```bash
# schema probe
PYTHONPATH=src python -m ais_risk.schema_probe_cli \\
  --input {raw_csv_path} \\
  --output {probe_json_path}

# preprocess
PYTHONPATH=src python -m ais_risk.preprocess_cli \\
  --input {raw_csv_path} \\
  --output {curated_csv_path}

# trajectory
PYTHONPATH=src python -m ais_risk.trajectory_cli \\
  --input {curated_csv_path} \\
  --output {tracks_csv_path}

# workflow
PYTHONPATH=src python -m ais_risk.workflow_cli \\
  --input {raw_csv_path} \\
  --config configs/base.toml \\
  --output-dir {workflow_dir}
```

## 7. 산출물 경로

- raw path: `{raw_root}/{dataset_id}/`
- curated path: `{curated_csv_path}`
- tracks path: `{tracks_csv_path}`
- schema probe path: `{probe_json_path}`
- workflow summary path: `{workflow_dir}/workflow_summary.json`

## 8. 다음 액션

1. 실제 raw file을 적재하고 schema probe 결과를 채운다.
2. stable identifier와 heading/cog coverage를 확인한다.
3. own ship candidate 추천과 pairwise benchmark로 이어간다.
"""


def save_first_dataset_manifest(path: str | Path, text: str) -> str:
    destination = Path(path)
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_text(text, encoding="utf-8")
    return str(destination)


def clean_manifest_value(text: str) -> str:
    return text.strip().strip("`").strip()


def normalize_manifest_key(text: str) -> str:
    normalized = re.sub(r"[^0-9A-Za-z가-힣]+", "_", text.strip().lower())
    normalized = re.sub(r"_+", "_", normalized).strip("_")
    return normalized


def extract_first_iso_date(text: str) -> str | None:
    match = re.search(r"\d{4}-\d{2}-\d{2}", text)
    if not match:
        return None
    return match.group(0)


def infer_source_slug_from_dataset_id(dataset_id: str, fallback: str = "dma") -> str:
    token = dataset_id.split("_", 1)[0].strip().lower()
    if not token:
        return fallback
    return token


def parse_first_dataset_manifest(path: str | Path) -> dict[str, Any]:
    manifest_path = Path(path)
    raw = manifest_path.read_text(encoding="utf-8")

    bullet_values: dict[str, str] = {}
    table_values: dict[str, str] = {}

    for line in raw.splitlines():
        stripped = line.strip()
        if stripped.startswith("- ") and ":" in stripped:
            key_text, value_text = stripped[2:].split(":", 1)
            bullet_values[normalize_manifest_key(key_text)] = clean_manifest_value(value_text)
            continue

        if stripped.startswith("|"):
            parts = [segment.strip() for segment in stripped.split("|")]
            if len(parts) < 4:
                continue
            left = parts[1]
            right = parts[2]
            if left in {"", "---", "항목"}:
                continue
            if set(left.replace(" ", "")) == {"-"}:
                continue
            table_values[left] = clean_manifest_value(right)

    dataset_id = bullet_values.get("dataset_id") or manifest_path.stem
    area = table_values.get("해역", "TBD")
    start_date = extract_first_iso_date(table_values.get("시작 시각", ""))
    end_date = extract_first_iso_date(table_values.get("종료 시각", ""))

    source_slug = infer_source_slug_from_dataset_id(dataset_id)
    table_normalized = {normalize_manifest_key(key): value for key, value in table_values.items()}
    return {
        "dataset_id": dataset_id,
        "manifest_path": str(manifest_path),
        "source_slug": source_slug,
        "area": area,
        "start_date": start_date,
        "end_date": end_date,
        "source_name": bullet_values.get("source_name"),
        "source_url": bullet_values.get("source_url"),
        "license_url": bullet_values.get("license_terms_url"),
        "source_type": bullet_values.get("source_type"),
        "source_preset": table_normalized.get("source_preset"),
        "vessel_type_filter": table_normalized.get("vessel_type_filter"),
    }
