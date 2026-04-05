# 문서명
DMA 첫 실데이터 착수 런북(DMA First Dataset Runbook)

# 문서 목적
DMA historical AIS를 기준으로 첫 실데이터를 적재하고, 스키마 점검부터 workflow, pairwise benchmark, 연구일지 생성까지 한 번에 수행하는 실행 순서를 고정한다.

# 대상 독자
연구자, 데이터사이언티스트, ML 엔지니어

# 작성 버전
v1.0

# 핵심 요약
- [확정] 첫 실데이터의 핵심은 다운로드 자체보다 `dataset_id 고정`, `manifest 기록`, `재현 가능한 실행 순서`다.
- [확정] 첫 실행은 `DMA 1주치 + 단일 해역 집중`이 적당하다.
- [확정] benchmark 결과는 바로 연구일지(`research_log_cli`)로 변환해 남긴다.
- [추가 검증 필요] 실제 DMA raw 파일 컬럼 스키마는 schema probe로 확정해야 한다.

## 1. 배경 및 문제 정의

기능이 많은 프로젝트일수록 실데이터 착수 시점에서 절차가 흔들린다. 이 런북은 첫 데이터셋을 동일 방식으로 재실행할 수 있도록 `입력`, `폴더 구조`, `명령 순서`, `완료 기준`을 고정한다.

## 2. 목표와 비목표

### 2.1 목표

| 항목 | 설명 | 상태 |
|---|---|---|
| RB-01 | 첫 DMA dataset manifest 생성 | [확정] |
| RB-02 | schema probe -> preprocess -> trajectory -> workflow 실행 | [확정] |
| RB-03 | pairwise benchmark와 연구일지 자동 생성 | [확정] |

### 2.2 비목표

| 항목 | 설명 | 상태 |
|---|---|---|
| 다중 해역 동시 착수 | 첫 턴에서는 하지 않음 | [확정] |
| complex model 우선 적용 | baseline 검증 전 보류 | [확정] |

## 3. 핵심 가정과 제약

| 항목 | 내용 | 상태 |
|---|---|---|
| source | DMA historical AIS | [합리적 가정] |
| 기간 | 1주(예: 2023-08-01 ~ 2023-08-07) | [합리적 가정] |
| 실행 장비 | Apple Silicon 단일 장비 | [합리적 가정] |
| 목표 산출물 | workflow summary + pairwise benchmark + research log | [확정] |

## 4. 상세 설계/요구사항/방법론

### 4.1 폴더 및 파일명 규칙

```text
data/raw/dma/{dataset_id}/
data/curated/{dataset_id}_curated.csv
data/curated/{dataset_id}_tracks.csv
outputs/{dataset_id}_workflow/
outputs/{dataset_id}_pairwise_*
research_logs/{date}_{dataset_id}_benchmark.md
```

### 4.2 1회성 준비

```bash
mkdir -p data/raw/dma
mkdir -p data/curated
mkdir -p data/manifests
mkdir -p outputs
mkdir -p research_logs
```

### 4.3 manifest 생성

```bash
PYTHONPATH=src python -m ais_risk.dataset_manifest_cli \
  --source-slug dma \
  --area-slug danish_corridor_a \
  --start-date 2023-08-01 \
  --end-date 2023-08-07 \
  --source-name "Danish Maritime Authority historical AIS" \
  --source-url "https://www.dma.dk/safety-at-sea/navigational-information/ais-data" \
  --license-url "https://www.dma.dk/safety-at-sea/navigational-information/ais-data/ais-data-management-policy-" \
  --area "Danish Corridor A (first draft)"
```

### 4.4 raw 파일 배치

| 항목 | 규칙 |
|---|---|
| raw folder | `data/raw/dma/{dataset_id}/` |
| raw 파일명 | `raw.csv` 또는 `raw_YYYYMMDD.csv` |
| 다중 파일 병합 | 첫 실행은 단일 `raw.csv`로 합쳐도 무방 |

### 4.4.1 DMA zip 다운로드(선택)

```bash
export DATASET_ID="dma_danish_corridor_a_2023-08-01_2023-08-07_v1"

# 먼저 dry-run으로 URL 목록만 확인
PYTHONPATH=src python -m ais_risk.dma_fetch_cli \
  --manifest "data/manifests/${DATASET_ID}.md" \
  --timeout-sec 20 \
  --max-attempts 2 \
  --dry-run \
  --summary-json "outputs/${DATASET_ID}_dma_fetch_dry_run.json"

# 실제 다운로드
PYTHONPATH=src python -m ais_risk.dma_fetch_cli \
  --manifest "data/manifests/${DATASET_ID}.md" \
  --timeout-sec 20 \
  --max-attempts 2 \
  --summary-json "outputs/${DATASET_ID}_dma_fetch.json"
```

#### 4.4.1-a 연결 이슈 체크

| 체크 항목 | 방법 |
|---|---|
| DNS/접속 실패 여부 | `outputs/${DATASET_ID}_dma_fetch.json`의 `failures` 확인 |
| base URL 변경 필요 여부 | `--base-url` 또는 `--fallback-base-urls`로 endpoint override 후 1일 구간 재시도 |
| fetch 지연 단축 | `--timeout-sec`, `--max-attempts`를 낮춰 실패 판정을 빠르게 확정 |
| 차선 source 전환 | 지속 실패 시 `docs/18_public_ais_source_shortlist.md` 기준으로 source 전환 |

```bash
PYTHONPATH=src python -m ais_risk.source_probe_cli \
  --output-prefix "outputs/${DATASET_ID}_source_probe" \
  --source-ids dma_ais,noaa_accessais,aishub_api \
  --timeout-seconds 8 \
  --retries 1
```

### 4.4.2 다중 CSV를 raw.csv로 병합

```bash
PYTHONPATH=src python -m ais_risk.raw_merge_cli \
  --input-glob "data/raw/dma/${DATASET_ID}/downloads/**/*.csv" \
  --output "data/raw/dma/${DATASET_ID}/raw.csv" \
  --summary-json "outputs/${DATASET_ID}_raw_merge.json"
```

### 4.5 파이프라인 실행

```bash
export DATASET_ID="dma_danish_corridor_a_2023-08-01_2023-08-07_v1"
export RAW_PATH="data/raw/dma/${DATASET_ID}/raw.csv"

PYTHONPATH=src python -m ais_risk.schema_probe_cli \
  --input "${RAW_PATH}" \
  --output "outputs/${DATASET_ID}_probe.json"

PYTHONPATH=src python -m ais_risk.preprocess_cli \
  --input "${RAW_PATH}" \
  --output "data/curated/${DATASET_ID}_curated.csv"

PYTHONPATH=src python -m ais_risk.trajectory_cli \
  --input "data/curated/${DATASET_ID}_curated.csv" \
  --output "data/curated/${DATASET_ID}_tracks.csv"

PYTHONPATH=src python -m ais_risk.workflow_cli \
  --input "${RAW_PATH}" \
  --config configs/base.toml \
  --output-dir "outputs/${DATASET_ID}_workflow"
```

### 4.6 pairwise benchmark 실행

```bash
PYTHONPATH=src python -m ais_risk.pairwise_dataset_cli \
  --input "data/curated/${DATASET_ID}_tracks.csv" \
  --config configs/base.toml \
  --output "outputs/${DATASET_ID}_pairwise_dataset.csv" \
  --stats-output "outputs/${DATASET_ID}_pairwise_dataset_stats.json" \
  --label-distance-nm 1.6

PYTHONPATH=src python -m ais_risk.benchmark_cli \
  --input "outputs/${DATASET_ID}_pairwise_dataset.csv" \
  --output-prefix "outputs/${DATASET_ID}_pairwise_benchmark" \
  --models rule_score,logreg,hgbt

PYTHONPATH=src python -m ais_risk.benchmark_cli \
  --input "outputs/${DATASET_ID}_pairwise_dataset.csv" \
  --output-prefix "outputs/${DATASET_ID}_pairwise_benchmark_mps" \
  --models rule_score,logreg,hgbt,torch_mlp \
  --torch-device auto
```

### 4.7 연구일지 자동 생성

```bash
PYTHONPATH=src python -m ais_risk.research_log_cli \
  --benchmark-summary "outputs/${DATASET_ID}_pairwise_benchmark_summary.json" \
  --pairwise-stats "outputs/${DATASET_ID}_pairwise_dataset_stats.json" \
  --dataset-manifest "data/manifests/${DATASET_ID}.md" \
  --output "research_logs/$(date +%F)_${DATASET_ID}_benchmark.md" \
  --topic "${DATASET_ID}_benchmark"

PYTHONPATH=src python -m ais_risk.study_journal_cli \
  --study-summary "outputs/${DATASET_ID}_study_summary.json" \
  --output "research_logs/$(date +%F)_${DATASET_ID}_study_journal.md" \
  --topic "${DATASET_ID}_study_iteration"
```

### 4.8 원클릭 실행(권장)

```bash
PYTHONPATH=src python -m ais_risk.study_run_cli \
  --manifest "data/manifests/${DATASET_ID}.md" \
  --config configs/base.toml \
  --output-root outputs \
  --benchmark-models rule_score,logreg,hgbt,torch_mlp \
  --pairwise-label-distance-nm 1.6 \
  --pairwise-split-strategy own_ship \
  --run-error-analysis \
  --error-analysis-top-k-each 20 \
  --run-stratified-eval \
  --run-calibration-eval \
  --run-own-ship-loo \
  --run-own-ship-case-eval \
  --own-ship-case-eval-repeat-count 5 \
  --build-study-journal \
  --study-journal-output "research_logs/$(date +%F)_${DATASET_ID}_study_journal.md" \
  --run-validation-suite \
  --update-validation-leaderboard \
  --fetch-dma \
  --fetch-summary-json "outputs/${DATASET_ID}_dma_fetch.json" \
  --raw-merge-summary-json "outputs/${DATASET_ID}_raw_merge.json" \
  --run-mps-benchmark
```

위 명령은 `workflow -> pairwise dataset -> benchmark -> research log`를 순서대로 실행하고 최종 `study_summary`를 저장한다.
`raw.csv`가 없다면 manifest 기준 다운로드 폴더(`data/raw/dma/{dataset_id}/downloads`)의 CSV를 먼저 병합해 자동으로 생성한다.
`--pairwise-split-strategy own_ship`를 쓰면 own-ship holdout 기준으로 검증되어 반복 비교 검증에 더 적합하다.
`--run-error-analysis`를 쓰면 모델별 FP/FN 상위 사례를 `*_pairwise_error_analysis_cases.csv`로 추출한다.
`--run-stratified-eval`를 쓰면 encounter type/거리 구간별 성능 테이블을 `*_pairwise_stratified_eval_*`로 생성한다.
`--run-calibration-eval`를 쓰면 예측 확률의 Brier/ECE와 reliability bin 테이블을 `*_pairwise_calibration_eval_*`로 생성한다.
`--run-own-ship-loo`를 쓰면 holdout own ship을 바꿔가며 반복 검증한 요약(`*_own_ship_loo_summary.*`)도 함께 생성된다.
`--run-own-ship-case-eval`를 쓰면 own ship 고정 반복 검증 요약(`*_pairwise_own_ship_case_eval_*`)을 함께 생성한다.
특정 own ship 1척만 집중 검증하려면 `--own-ship-case-eval-mmsis <MMSI> --own-ship-case-eval-repeat-count 5`를 함께 지정한다.
`--run-validation-suite`를 쓰면 timestamp/own_ship/LOO 세 검증을 한 요약(`*_validation_suite_summary.*`)로 함께 저장한다.
`--update-validation-leaderboard`를 쓰면 누적 실행 결과를 `outputs/validation_leaderboard.csv/.md`로 갱신한다.
calibration 비교 중심 리더보드가 필요하면 `validation_leaderboard_cli --sort-by calibration_best_ece --ascending`으로 별도 파일을 생성한다.
own ship 고정 반복 검증 비교가 필요하면 `validation_leaderboard_cli --sort-by own_ship_case_f1_mean|own_ship_case_f1_std_repeat_mean --ascending`으로 별도 파일을 생성한다.
리더보드 기본 경보 규칙은 `own_ship_case_f1_std>0.10`, `own_ship_case_f1_ci95_width>0.20`, `calibration_best_ece>0.15`이며 필요하면 CLI threshold 옵션으로 조정한다.

### 4.9 다중 manifest 배치 실행(확장)

```bash
PYTHONPATH=src python -m ais_risk.study_batch_cli \
  --manifest-glob "data/manifests/*.md" \
  --output-prefix "outputs/study_batch_run" \
  --benchmark-models rule_score,logreg,hgbt,torch_mlp \
  --raw-input-template "data/raw/{source_slug}/{dataset_id}/raw.csv" \
  --auto-merge-glob-template "data/raw/{source_slug}/{dataset_id}/downloads/**/*.csv" \
  --pairwise-split-strategy own_ship \
  --run-error-analysis \
  --run-stratified-eval \
  --run-calibration-eval \
  --run-own-ship-loo \
  --run-own-ship-case-eval \
  --own-ship-case-eval-repeat-count 5 \
  --run-validation-suite \
  --update-validation-leaderboard \
  --build-batch-review \
  --batch-review-previous-summary "outputs/study_batch_run_prev_summary.json" \
  --batch-review-own-ship-case-f1-std-threshold 0.10 \
  --batch-review-own-ship-case-f1-ci95-width-threshold 0.20 \
  --batch-review-calibration-ece-threshold 0.15 \
  --build-batch-trend-report \
  --batch-trend-output-prefix "research_logs/$(date +%F)_study_batch_trend" \
  --batch-trend-history-glob "outputs/study_batch*_summary.json" \
  --batch-trend-moving-average-window 3 \
  --batch-trend-delta-own-ship-case-f1-ci95-width-rise-threshold 0.02 \
  --build-study-journals \
  --study-journal-output-template "research_logs/{date}_{dataset_id}_study_journal.md" \
  --batch-review-output "research_logs/$(date +%F)_study_batch_review.md"
```

배치 실행은 manifest별 성공/실패, 핵심 지표를 `outputs/study_batch_run_summary.json/.md`로 저장한다.
`--build-batch-review`를 추가하면 배치 결과를 연구일지 형식으로 `research_logs/*_study_batch_review.md`에 저장한다.
`--build-batch-trend-report`를 추가하면 high alert 및 delta 악화 우선순위를 `*_study_batch_trend_summary.*`로 저장한다.
같은 보고서 상단에는 `Top Moving-Average Deviation (Top 3, Risk Direction)`가 생성되며, LOO F1 하락/ECE 상승/own-ship case std 상승/own-ship case F1 CI95 폭 상승 편차가 큰 데이터셋부터 triage할 수 있다.
`--batch-trend-moving-average-window`로 최근 N회 이동평균 기준의 악화 판단 강도를 조정할 수 있다.

### 4.10 모델셋 스윕 실행(확장)

```bash
PYTHONPATH=src python -m ais_risk.study_sweep_cli \
  --manifest "data/manifests/${DATASET_ID}.md" \
  --raw-input "data/raw/dma/${DATASET_ID}/raw.csv" \
  --output-prefix "outputs/${DATASET_ID}_study_sweep" \
  --output-root "outputs/${DATASET_ID}_study_sweep_runs" \
  --benchmark-modelsets "rule_score,logreg,hgbt;rule_score,logreg,hgbt,torch_mlp" \
  --pairwise-split-strategy own_ship \
  --run-calibration-eval \
  --run-own-ship-loo \
  --run-own-ship-case-eval \
  --own-ship-case-eval-mmsis 440000102 \
  --own-ship-case-eval-min-rows 30 \
  --own-ship-case-eval-repeat-count 5 \
  --build-study-journals \
  --study-journal-output-template "research_logs/{date}_{dataset_id}_{modelset_index}_study_journal.md" \
  --study-journal-note "modelset sweep"
```

스윕 결과는 `*_study_sweep_summary.json/.md/.csv`로 저장되며, 모델셋별 best benchmark F1 / calibration ECE / LOO F1 mean / case F1 mean/std/CI95 width/repeat std mean과 함께 benchmark elapsed/device 지표를 한 표에서 비교할 수 있다.
`--build-study-journals`를 추가하면 모델셋별 연구일지가 자동 생성되어 실험 기록 관리가 쉬워진다.

focus own-ship vs baseline을 한 번에 실행하려면 아래 명령을 사용한다.

```bash
PYTHONPATH=src python -m ais_risk.focus_compare_cli \
  --manifest "data/manifests/${DATASET_ID}.md" \
  --raw-input "data/raw/dma/${DATASET_ID}/raw.csv" \
  --output-prefix "research_logs/$(date +%F)_${DATASET_ID}_focus_compare_bundle" \
  --output-root "outputs/${DATASET_ID}_focus_compare_bundle_runs" \
  --focus-own-ship-case-eval-mmsis <OWN_MMSI> \
  --benchmark-modelsets "rule_score,logreg,hgbt;rule_score,logreg,hgbt,torch_mlp" \
  --pairwise-split-strategy own_ship \
  --run-calibration-eval \
  --run-own-ship-loo \
  --run-own-ship-case-eval \
  --own-ship-case-eval-repeat-count 5 \
  --build-study-journals \
  --study-journal-output-template "research_logs/{date}_{dataset_id}_{modelset_index}_{sweep_type}_study_journal.md"
```

MMSI를 수동 지정하지 않으려면 `--focus-own-ship-case-eval-mmsis` 대신 `--auto-focus-own-ship --auto-focus-rank 1`을 사용한다.

rank 1/2/3을 한 번에 비교하려면 `focus_rank_compare_cli`를 사용한다.
기본 설정에서는 rank 1의 baseline sweep summary를 rank 2/3에서 재사용하여 실행 시간을 줄인다.

```bash
PYTHONPATH=src python -m ais_risk.focus_rank_compare_cli \
  --manifest "data/manifests/${DATASET_ID}.md" \
  --raw-input "data/raw/dma/${DATASET_ID}/raw.csv" \
  --output-prefix "research_logs/$(date +%F)_${DATASET_ID}_focus_rank_compare" \
  --output-root "outputs/${DATASET_ID}_focus_rank_compare_runs" \
  --auto-focus-ranks 1,2,3 \
  --benchmark-modelsets "rule_score,logreg,hgbt;rule_score,logreg,hgbt,torch_mlp" \
  --pairwise-split-strategy own_ship \
  --run-calibration-eval \
  --run-own-ship-loo \
  --run-own-ship-case-eval \
  --own-ship-case-eval-repeat-count 5
```

rank별 baseline을 독립적으로 다시 학습하려면 `--no-reuse-baseline-across-ranks`를 추가한다.

지정한 own-ship MMSI 목록(예: 후보 2~3개)을 반복 검증하려면 `focus_mmsi_compare_cli`를 사용한다.

```bash
PYTHONPATH=src python -m ais_risk.focus_mmsi_compare_cli \
  --manifest "data/manifests/${DATASET_ID}.md" \
  --raw-input "data/raw/dma/${DATASET_ID}/raw.csv" \
  --output-prefix "research_logs/$(date +%F)_${DATASET_ID}_focus_mmsi_compare" \
  --output-root "outputs/${DATASET_ID}_focus_mmsi_compare_runs" \
  --focus-own-ship-mmsis 440000102,440000103,440000001 \
  --benchmark-modelsets "rule_score,logreg,hgbt;rule_score,logreg,hgbt,torch_mlp" \
  --pairwise-split-strategy own_ship \
  --run-calibration-eval \
  --run-own-ship-loo \
  --run-own-ship-case-eval \
  --own-ship-case-eval-repeat-count 5
```

기본 설정에서는 첫 MMSI의 baseline sweep summary를 나머지 MMSI에서 재사용한다. MMSI별 baseline 독립 재학습은 `--no-reuse-baseline-across-mmsis`를 사용한다.
재현성 고정을 위해 focus/rank/mmsi compare 실행에는 `--random-seed 42`를 함께 사용하는 것을 권장한다.

seed 민감도(robustness) 검증은 `focus_seed_compare_cli`로 한 번에 수행한다.

```bash
PYTHONPATH=src python -m ais_risk.focus_seed_compare_cli \
  --manifest "data/manifests/${DATASET_ID}.md" \
  --raw-input "data/raw/dma/${DATASET_ID}/raw.csv" \
  --output-prefix "research_logs/$(date +%F)_${DATASET_ID}_focus_seed_compare" \
  --output-root "outputs/${DATASET_ID}_focus_seed_compare_runs" \
  --focus-own-ship-mmsis 440000102,440000103,440000001 \
  --seed-values 42,43,44 \
  --benchmark-modelsets "rule_score,logreg,hgbt;rule_score,logreg,hgbt,torch_mlp" \
  --pairwise-split-strategy own_ship \
  --run-calibration-eval \
  --run-own-ship-loo \
  --run-own-ship-case-eval \
  --own-ship-case-eval-repeat-count 5
```

own-ship MMSI를 매번 수동 지정하지 않으려면 `focus_seed_pipeline_cli`로 후보 선택+seed 검증을 한 번에 실행한다.

```bash
PYTHONPATH=src python -m ais_risk.focus_seed_pipeline_cli \
  --manifest "data/manifests/${DATASET_ID}.md" \
  --raw-input "data/raw/dma/${DATASET_ID}/raw.csv" \
  --output-prefix "research_logs/$(date +%F)_${DATASET_ID}_focus_seed_pipeline" \
  --output-root "outputs/${DATASET_ID}_focus_seed_pipeline_runs" \
  --auto-select-focus-mmsis \
  --auto-select-count 2 \
  --auto-select-start-rank 1 \
  --seed-values 42,43,44 \
  --benchmark-modelsets "rule_score,logreg,hgbt;rule_score,logreg,hgbt,torch_mlp" \
  --pairwise-split-strategy own_ship \
  --run-calibration-eval \
  --run-own-ship-loo \
  --run-own-ship-case-eval \
  --own-ship-case-eval-repeat-count 5 \
  --validation-gate-min-seed-count 3 \
  --validation-gate-min-delta-case-f1-mean 0.0 \
  --validation-gate-max-delta-case-f1-std 0.05 \
  --torch-device mps
```

`focus_seed_pipeline` summary에는 `validation_gate_overall_decision`, `validation_gate_recommended_modelset_key`, `*_validation_gate_rows.csv`가 포함되며, seed robustness 결과를 즉시 pass/fail로 해석할 수 있다.

## 5. 성공 기준 또는 평가 기준

| 항목 | 기준 | 상태 |
|---|---|---|
| manifest 고정 | `data/manifests/{dataset_id}.md` 생성 | [확정] |
| workflow 완료 | `outputs/{dataset_id}_workflow/workflow_summary.json` 생성 | [확정] |
| benchmark 완료 | `outputs/{dataset_id}_pairwise_benchmark_summary.json` 생성 | [확정] |
| 연구일지 완료 | `research_logs/{date}_{dataset_id}_benchmark.md` 생성 | [확정] |

## 6. 리스크와 한계

| 항목 | 내용 | 상태 |
|---|---|---|
| schema mismatch | 실제 컬럼이 예상 alias와 다를 수 있음 | [리스크] |
| class imbalance | label-distance 값에 따라 단일 클래스가 될 수 있음 | [리스크] |
| 과적합된 benchmark | 첫 dataset이 단순하면 metric이 과대평가될 수 있음 | [리스크] |

## 7. 핵심 결정사항

- [확정] 첫 턴은 DMA 1개 dataset을 `dataset_id` 단위로 고정한다.
- [확정] workflow 후 pairwise benchmark와 research log까지 같은 날 완료한다.
- [확정] 결과 해석은 반드시 `single dataset limitation`을 명시한다.

## 8. 오픈 이슈

1. [추가 검증 필요] first area bbox 확정
2. [추가 검증 필요] label-distance threshold 최적값
3. [추가 검증 필요] own-ship holdout split 적용 시점

## 9. 다음 액션

1. 실제 raw 파일을 다운로드해 `data/raw/dma/{dataset_id}/`에 배치한다.
2. schema probe 결과를 manifest에 반영한다.
3. 첫 benchmark 로그를 기반으로 다음 주 multi-area 계획을 수립한다.

설명 팁: 심사자에게는 "첫 실데이터 착수도 코드 실행뿐 아니라 dataset manifest와 연구일지까지 포함한 재현 가능한 runbook으로 관리한다"라고 설명하면 좋다.
