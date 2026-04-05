# First Public AIS Dataset Draft

## 0. 기본 정보

- dataset_id: `dma_first_historical_candidate_v1`
- 작성일: 2026-03-07
- 작성자: Codex
- source name: Danish Maritime Authority historical AIS
- source URL: https://www.dma.dk/safety-at-sea/navigational-information/ais-data
- license / terms URL: https://www.dma.dk/safety-at-sea/navigational-information/ais-data/ais-data-management-policy-
- source type: `historical CSV`
- status: [합리적 가정]

## 1. 왜 이 소스를 고르는가

- 프로젝트 적합성: [확정] 공식 페이지에서 continuously updated historical AIS data를 free CSV zip으로 접근 가능하다고 명시한다.
- own ship 추적 적합성: [합리적 가정] historical AIS raw point 기반이므로 stable vessel identifier와 repeated own-ship validation에 적합할 가능성이 높다.
- 포기한 대안: [확정] 한국 공공데이터의 선박 AIS 동적정보는 MMSI가 특수문자로 대체된다고 공식 설명이 있어 1차 source로는 보류한다.

## 2. 커버리지

| 항목 | 값 |
|---|---|
| 해역 | [합리적 가정] Danish waters 내 busy traffic corridor 1곳 |
| bbox | [추가 검증 필요] 실제 다운로드 후 확정 |
| 시작 시각 | [합리적 가정] 2023-08-01 |
| 종료 시각 | [합리적 가정] 2023-08-07 |
| raw 파일 개수 | [합리적 가정] 7 daily zip files |
| raw 총 용량 | [추가 검증 필요] 다운로드 후 기록 |

## 3. 스키마 점검

| 항목 | 결과 |
|---|---|
| vessel id column | [추가 검증 필요] actual CSV 확인 필요 |
| timestamp column | [추가 검증 필요] actual CSV 확인 필요 |
| lat/lon column | [추가 검증 필요] actual CSV 확인 필요 |
| sog/cog column | [추가 검증 필요] actual CSV 확인 필요 |
| heading availability | [추가 검증 필요] actual CSV 확인 필요 |
| vessel_type availability | [추가 검증 필요] actual CSV 확인 필요 |
| stable identifier 여부 | [합리적 가정] 있음 |

## 4. 전처리 계획

| 항목 | 값 |
|---|---|
| source preset | `auto` |
| column override | 다운로드 후 schema probe 결과를 보고 결정 |
| vessel type filter | [합리적 가정] `cargo,tanker,tug,passenger` |
| bbox filter | first harbor/corridor bbox를 다운로드 후 설정 |
| time filter | first week only |
| split gap min | `10` |
| max interp gap min | `2` |
| step sec | `30` |

## 5. 리스크 메모

- [리스크] DMA historical CSV actual schema가 현재 alias와 다를 수 있다.
- [리스크] 해역을 너무 넓게 잡으면 single-machine 실험이 무거워질 수 있다.
- [추가 검증 필요] 첫 주간 데이터만으로 own ship candidate 수가 충분한지 확인 필요.

## 6. 실행 기록

```bash
# schema probe
PYTHONPATH=src python -m ais_risk.schema_probe_cli \
  --input data/raw/dma/first_batch/raw.csv \
  --output outputs/dma_first_probe.json

# preprocess
PYTHONPATH=src python -m ais_risk.preprocess_cli \
  --input data/raw/dma/first_batch/raw.csv \
  --output data/curated/dma_first_curated.csv

# trajectory
PYTHONPATH=src python -m ais_risk.trajectory_cli \
  --input data/curated/dma_first_curated.csv \
  --output data/curated/dma_first_tracks.csv

# workflow
PYTHONPATH=src python -m ais_risk.workflow_cli \
  --input data/raw/dma/first_batch/raw.csv \
  --config configs/base.toml \
  --output-dir outputs/dma_first_workflow
```

## 7. 산출물 경로

- raw path: `data/raw/dma/first_batch/`
- curated path: `data/curated/dma_first_curated.csv`
- tracks path: `data/curated/dma_first_tracks.csv`
- schema probe path: `outputs/dma_first_probe.json`
- workflow summary path: `outputs/dma_first_workflow/workflow_summary.json`

## 8. 다음 액션

1. DMA historical AIS에서 실제 first-week raw zip을 받는다.
2. schema probe 결과로 actual 컬럼을 확인한다.
3. bbox를 좁혀 first dense corridor dataset을 freeze한다.
