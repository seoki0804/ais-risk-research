# 문서명
NOAA AccessAIS 첫 실데이터 착수 런북

# 문서 목적
DMA zip endpoint 이슈가 지속될 때 NOAA AccessAIS export CSV로 즉시 연구 루프를 진행할 수 있도록 실행 절차를 고정한다.

# 대상 독자
연구자, 데이터사이언티스트, ML 엔지니어

# 작성 버전
v1.0 (2026-03-09)

# 핵심 요약
- [확정] NOAA 경로는 `study_run_cli`에서 `--source-preset noaa_accessais`로 바로 처리 가능하다.
- [확정] baseline 비교는 `rule_score,logreg,hgbt`를 우선 고정한다.
- [확정] 검증은 `validation_suite + own_ship_case_repeat + leaderboard`를 묶어서 본다.
- [합리적 가정] 첫 NOAA dataset은 단일 harbor/해역 1주치로 시작한다.

## 1. 배경 및 문제 정의

DMA 안내 페이지는 접근 가능하지만 zip 다운로드 endpoint 실패가 지속될 수 있다. 데이터 수집 병목을 줄이기 위해 NOAA AccessAIS export를 병행 경로로 준비한다.

## 2. 목표와 비목표

| 구분 | 내용 | 상태 |
|---|---|---|
| 목표 | NOAA raw CSV 1건으로 end-to-end study run 수행 | [확정] |
| 목표 | own-ship 반복 검증 지표(F1 std/CI95 width)까지 생성 | [확정] |
| 비목표 | NOAA 데이터만으로 실제 항법 안전성 보장 주장 | [확정] |

## 3. 핵심 가정과 제약

| 항목 | 내용 | 상태 |
|---|---|---|
| 입력 형식 | AccessAIS CSV (MMSI/BaseDateTime/LAT/LON/SOG/COG/Heading/VesselType) | [합리적 가정] |
| ID 안정성 | MMSI 유지 | [추가 검증 필요] |
| 실행환경 | 1인 Apple Silicon | [합리적 가정] |

## 4. 상세 설계/요구사항/방법론

### 4.1 Manifest 생성

```bash
PYTHONPATH=src python -m ais_risk.dataset_manifest_cli \
  --source-slug noaa \
  --area-slug us_harbor_a \
  --start-date 2023-08-01 \
  --end-date 2023-08-07 \
  --source-name "NOAA AccessAIS" \
  --source-url "https://coast.noaa.gov/digitalcoast/tools/ais.html" \
  --license-url "https://coast.noaa.gov/digitalcoast/tools/ais.html" \
  --area "US Harbor A (draft)"
```

### 4.2 Raw 파일 배치

| 항목 | 규칙 |
|---|---|
| raw 경로 | `data/raw/noaa/{dataset_id}/raw.csv` |
| 파일명 | AccessAIS export 결과를 `raw.csv`로 저장 |
| 스키마 확인 | `schema_probe_cli`로 필드 매핑 가능 여부 확인 |

MarineCadastre 일별 archive(zip)에서 바로 수집하려면 `noaa_fetch_cli`를 사용한다.

```bash
export DATASET_ID="noaa_us_coastal_all_2023-08-01_2023-08-01_v1"

PYTHONPATH=src python -m ais_risk.noaa_fetch_cli \
  --manifest "data/manifests/${DATASET_ID}.md" \
  --timeout-sec 120 \
  --max-attempts 1 \
  --extract \
  --summary-json "research_logs/$(date +%F)_${DATASET_ID}_noaa_fetch.json"
```

`--extract`를 켜면 `downloads/{date}/` 아래에 CSV가 풀리고, 이후 `raw_merge_cli`로 `raw.csv`를 만든다.

`study_run_cli`에서 NOAA fetch를 직접 실행하려면 아래처럼 `--fetch-noaa`를 사용한다.

```bash
PYTHONPATH=src python -m ais_risk.study_run_cli \
  --manifest "data/manifests/${DATASET_ID}.md" \
  --source-preset noaa_accessais \
  --output-root outputs \
  --raw-input "data/raw/noaa/${DATASET_ID}/raw.csv" \
  --fetch-noaa \
  --fetch-dry-run \
  --fetch-summary-json "research_logs/$(date +%F)_${DATASET_ID}_noaa_fetch_dry_run.json"
```

실수집 시에는 `--fetch-dry-run`을 제거하고 필요하면 `--fetch-extract`를 추가한다.

### 4.3 Study Run (권장 기본)

```bash
export DATASET_ID="noaa_us_harbor_a_2023-08-01_2023-08-07_v1"

PYTHONPATH=src python -m ais_risk.study_run_cli \
  --manifest "data/manifests/${DATASET_ID}.md" \
  --raw-input "data/raw/noaa/${DATASET_ID}/raw.csv" \
  --config configs/base.toml \
  --source-preset noaa_accessais \
  --output-root outputs \
  --benchmark-models rule_score,logreg,hgbt,torch_mlp \
  --pairwise-split-strategy own_ship \
  --run-calibration-eval \
  --run-own-ship-loo \
  --run-own-ship-case-eval \
  --own-ship-case-eval-repeat-count 5 \
  --run-validation-suite \
  --update-validation-leaderboard \
  --build-study-journal \
  --study-journal-output "research_logs/$(date +%F)_${DATASET_ID}_study_journal.md" \
  --torch-device auto
```

### 4.4 모델셋 스윕 + 자동 저널

```bash
PYTHONPATH=src python -m ais_risk.study_sweep_cli \
  --manifest "data/manifests/${DATASET_ID}.md" \
  --raw-input "data/raw/noaa/${DATASET_ID}/raw.csv" \
  --source-preset noaa_accessais \
  --output-prefix "outputs/${DATASET_ID}_study_sweep" \
  --output-root "outputs/${DATASET_ID}_study_sweep_runs" \
  --benchmark-modelsets "rule_score,logreg,hgbt;rule_score,logreg,hgbt,torch_mlp" \
  --pairwise-split-strategy own_ship \
  --run-calibration-eval \
  --run-own-ship-loo \
  --run-own-ship-case-eval \
  --own-ship-case-eval-repeat-count 5 \
  --build-study-journals \
  --study-journal-output-template "research_logs/{date}_{dataset_id}_{modelset_index}_study_journal.md"
```

## 5. 성공 기준 또는 평가 기준

| 항목 | 기준 | 상태 |
|---|---|---|
| workflow 완료 | `outputs/{dataset_id}_workflow/workflow_summary.json` 생성 | [확정] |
| validation suite 생성 | `*_validation_suite_summary.json` 생성 | [확정] |
| own_ship_case 반복 지표 | `f1_std`, `f1_ci95_width` 확인 가능 | [확정] |
| 연구일지 생성 | `research_logs/*_study_journal.md` 생성 | [확정] |

## 6. 리스크와 한계

| 항목 | 내용 | 상태 |
|---|---|---|
| 컬럼 변형 | NOAA export 컬럼명이 다를 수 있어 `--column-map` 필요 가능 | [리스크] |
| class imbalance | 특정 기간/해역에서 positive 빈도가 낮을 수 있음 | [리스크] |
| 일반화 한계 | 단일 해역 성능으로 전체 해역 일반화 불가 | [리스크] |

## 7. 핵심 결정사항

1. [확정] DMA 장애 시 NOAA를 메인 루프로 선진행.
2. [확정] baseline 우선, `torch_mlp`는 확장 비교 모델로 유지.
3. [확정] 단일 성능보다 반복 안정성/보정(calibration) 지표를 함께 평가.

## 8. 오픈 이슈

1. [추가 검증 필요] AccessAIS 최신 export 필드의 실제 컬럼명.
2. [추가 검증 필요] harbor 선택 기준(bbox/교통밀도) 확정.
3. [추가 검증 필요] own_ship_case CI95 임계치의 NOAA 해역 적정값.

## 9. 다음 액션

1. AccessAIS export 1건을 `data/raw/noaa/{dataset_id}/raw.csv`로 저장.
2. 위 study_run 명령으로 첫 결과셋 생성.
3. 결과를 leaderboard에 반영해 DMA/NOAA 비교 트랙 시작.

## 교수/면접관 설명 팁

“데이터 소스 리스크가 생겨도 검증 프레임은 유지한 채 source만 교체 가능한 구조로 설계했다.”
