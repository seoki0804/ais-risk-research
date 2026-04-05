# Data Layout

- `raw/`: 원본 AIS 파일
- `curated/`: 정제/재구성된 데이터
- `splits/`: train/val/test 또는 own-ship holdout 메타데이터
- `manifests/`: dataset freeze 기록과 source 메모

실제 데이터 소스와 라이선스가 확정되면 이 구조에 맞춰 적재한다.

## 권장 raw 적재 구조

```text
data/raw/{source}/{area}/{period}/...
예: data/raw/publicais/harbor_a/2026-01/
```

## 권장 dataset freeze 메모

- `dataset_id`
- source / license
- area / bbox
- start / end
- raw file list
- preprocess filter
- row count / vessel count
- notes

## 권장 curated CSV 스키마

- `mmsi`
- `timestamp`
- `lat`
- `lon`
- `sog`
- `cog`
- `heading`
- `vessel_type`

## 권장 reconstructed CSV 추가 컬럼

- `segment_id`
- `is_interpolated`
