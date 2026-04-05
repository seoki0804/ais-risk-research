# 문서명
AIS Own-Ship 중심 반복 검증 프로토콜 v2

# 문서 목적
데이터 수집 이후 모델 강화 과정에서, own-ship 기준 반복 검증을 일관된 기준으로 수행하기 위한 실행 프로토콜을 고정한다.

# 대상 독자
연구기획자, 데이터사이언티스트, ML 엔지니어, 지도교수/심사자

# 작성 버전
v2.1 (2026-03-10)

# 핵심 요약
- [확정] 단일 split 성능 대신 `timestamp + own_ship + own_ship_LOO + own_ship_case_repeat` 4축 검증을 기본으로 사용한다.
- [확정] own-ship case는 `F1 mean`뿐 아니라 `F1 std`, `F1 CI95 width`, `F1 std repeat mean`을 함께 본다.
- [확정] 리더보드 경보 규칙은 `own_ship_case_f1_std`, `own_ship_case_f1_ci95_width`, `calibration_best_ece`를 병행한다.
- [합리적 가정] Apple Silicon(MPS) 사용 시 `torch_mlp`는 비교 모델(확장안)로 운용하고 baseline(rule/logreg/hgbt)을 우선 유지한다.
- [확정] auto-focus rank(1/2/3) 비교에서는 baseline sweep을 공유 재사용해 focus own-ship 차이 검증을 우선한다.
- [확정] 재현성 강화를 위해 기본 `random_seed=42`를 고정하고 동일 입력 재실행 시 결과 일관성을 확인한다.

## 1. 배경 및 문제 정의

pairwise AIS 위험 학습은 split 전략에 따라 성능 변동이 크다. 특히 own-ship 중심 의사결정 지원에서는 단일 benchmark 수치보다 holdout own-ship 일반화와 반복 안정성이 더 중요하다.

## 2. 목표와 비목표

| 구분 | 내용 | 상태 |
|---|---|---|
| 목표 | 반복 가능한 검증 루프(수집→학습→검증→일지)를 고정 | [확정] |
| 목표 | 불확실성(분산/CI) 기반 경보로 과신 방지 | [확정] |
| 비목표 | AIS-only로 실선 자동조타 안전성 보장 주장 | [확정] |

## 3. 핵심 가정과 제약

| 항목 | 내용 | 상태 |
|---|---|---|
| 데이터 | 공개 AIS만 사용 | [확정] |
| 라벨 | future separation 기반 conflict proxy | [확정] |
| 실행환경 | 개인 장비(Apple Silicon) | [합리적 가정] |
| 실선 검증 | 시뮬레이터/실선 제어 데이터 없음 | [확정] |

## 4. 상세 설계/요구사항/방법론

### 4.1 검증 계층(필수)

| 계층 | 목적 | 핵심 출력 |
|---|---|---|
| Timestamp split | 시간축 분리 기본 성능 | benchmark F1/AUROC/AUPRC |
| Own-ship split | unseen own ship 일반화 | own_ship split metrics |
| Own-ship LOO | holdout ship 반복 일반화 | LOO fold metrics + aggregate |
| Own-ship case repeat | 고정 own ship 반복 안정성 | F1 mean/std + CI95 width + repeat std |

### 4.2 실행 커맨드(권장 기본 루프)

```bash
PYTHONPATH=src python -m ais_risk.study_run_cli \
  --manifest data/manifests/<dataset_id>.md \
  --raw-input data/raw/<source>/<dataset_id>/raw.csv \
  --config configs/base.toml \
  --source-preset auto \
  --output-root outputs/<run_tag> \
  --benchmark-models rule_score,logreg,hgbt,torch_mlp \
  --pairwise-split-strategy own_ship \
  --run-calibration-eval \
  --run-own-ship-loo \
  --run-own-ship-case-eval \
  --own-ship-case-eval-repeat-count 5 \
  --run-validation-suite \
  --build-study-journal \
  --study-journal-output research_logs/$(date +%F)_<dataset_id>_study_journal.md \
  --torch-device auto \
  --random-seed 42
```

NOAA AccessAIS raw CSV를 쓰는 경우 `--source-preset noaa_accessais`를 지정한다.

raw 수집까지 한 번에 처리하려면 `study_run_cli`에서 source별 fetch 플래그를 사용한다.

```bash
# DMA
--fetch-dma

# NOAA
--fetch-noaa
```

연결/경로만 먼저 점검하려면 `--fetch-dry-run --fetch-summary-json <path>`를 붙여 fetch 계획만 검증한다.

### 4.3 반복 실험(모델셋 비교)

```bash
PYTHONPATH=src python -m ais_risk.study_sweep_cli \
  --manifest data/manifests/<dataset_id>.md \
  --raw-input data/raw/<source>/<dataset_id>/raw.csv \
  --output-prefix outputs/<dataset_id>_study_sweep \
  --output-root outputs/<dataset_id>_study_sweep_runs \
  --benchmark-modelsets "rule_score,logreg,hgbt;rule_score,logreg,hgbt,torch_mlp" \
  --pairwise-split-strategy own_ship \
  --run-calibration-eval \
  --run-own-ship-loo \
  --run-own-ship-case-eval \
  --own-ship-case-eval-repeat-count 5 \
  --build-study-journals \
  --study-journal-output-template "research_logs/{date}_{dataset_id}_{modelset_index}_study_journal.md" \
  --torch-device auto \
  --random-seed 42
```

### 4.4 리더보드 경보 모니터링

```bash
PYTHONPATH=src python -m ais_risk.validation_leaderboard_cli \
  --study-summary-glob "outputs/**/*_study_summary.json" \
  --output-csv outputs/validation_leaderboard.csv \
  --output-md outputs/validation_leaderboard.md \
  --sort-by own_ship_loo_f1_mean \
  --own-ship-case-f1-std-threshold 0.10 \
  --own-ship-case-f1-ci95-width-threshold 0.20 \
  --calibration-best-ece-threshold 0.15

PYTHONPATH=src python -m ais_risk.validation_leaderboard_cli \
  --study-summary-glob "outputs/**/*_study_summary.json" \
  --output-csv outputs/validation_leaderboard_case_repeat.csv \
  --output-md outputs/validation_leaderboard_case_repeat.md \
  --sort-by own_ship_case_f1_std_repeat_mean \
  --ascending
```

- [확정] validation suite를 생략한 run도 own-ship LOO/case/calibration 결과가 있으면 리더보드에 포함되며, 미생성 지표는 `n/a`로 표기한다.

### 4.5 합격/중단 기준(초안)

| 항목 | 기준 | 판정 |
|---|---|---|
| own_ship_loo_f1_mean | `>= 0.60` | [합리적 가정] |
| own_ship_case_f1_std | `<= 0.10` | [확정] |
| own_ship_case_f1_ci95_width | `<= 0.20` | [확정] |
| calibration_best_ece | `<= 0.15` | [확정] |
| 경보 개수(alert_count) | `0~1` 권장, `>=2` 개선 필요 | [확정] |

### 4.6 모델 강화 순서

1. [확정] baseline 고정: `rule_score`, `logreg`, `hgbt`.
2. [확정] 확장 비교: `torch_mlp` (MPS/GPU 사용).
3. [추가 검증 필요] threshold/feature tuning은 경보 지표 악화 없는 범위에서만 반영.

### 4.7 own-ship focus rank 반복 검증(보강)

```bash
PYTHONPATH=src python -m ais_risk.focus_rank_compare_cli \
  --manifest data/manifests/<dataset_id>.md \
  --raw-input data/raw/<source>/<dataset_id>/raw.csv \
  --output-prefix research_logs/$(date +%F)_<dataset_id>_focus_rank_compare \
  --output-root outputs/<dataset_id>_focus_rank_compare_runs \
  --auto-focus-ranks 1,2,3 \
  --benchmark-modelsets "rule_score,logreg,hgbt;rule_score,logreg,hgbt,torch_mlp" \
  --pairwise-split-strategy own_ship \
  --run-calibration-eval \
  --run-own-ship-loo \
  --run-own-ship-case-eval \
  --own-ship-case-eval-repeat-count 5 \
  --reuse-baseline-across-ranks \
  --torch-device mps \
  --random-seed 42
```

- [확정] `reuse_baseline_across_ranks=True`일 때 rank 1에서 baseline을 학습하고 rank 2/3은 baseline summary를 재사용한다.
- [확정] rank rows의 `baseline_reused`가 `False, True, True` 패턴이면 의도대로 동작한 것이다.
- [확정] 민감도 점검용으로 `--no-reuse-baseline-across-ranks`를 1회 추가 실행해 결론 일관성을 확인한다.

### 4.8 지정 own-ship MMSI 반복 검증(보강)

```bash
PYTHONPATH=src python -m ais_risk.focus_mmsi_compare_cli \
  --manifest data/manifests/<dataset_id>.md \
  --raw-input data/raw/<source>/<dataset_id>/raw.csv \
  --output-prefix research_logs/$(date +%F)_<dataset_id>_focus_mmsi_compare \
  --output-root outputs/<dataset_id>_focus_mmsi_compare_runs \
  --focus-own-ship-mmsis <mmsi_a>,<mmsi_b>,<mmsi_c> \
  --benchmark-modelsets "rule_score,logreg,hgbt;rule_score,logreg,hgbt,torch_mlp" \
  --pairwise-split-strategy own_ship \
  --run-calibration-eval \
  --run-own-ship-loo \
  --run-own-ship-case-eval \
  --own-ship-case-eval-repeat-count 5 \
  --reuse-baseline-across-mmsis \
  --torch-device mps \
  --random-seed 42
```

- [확정] 사용자가 지정한 MMSI 목록을 기준으로 focus-vs-baseline을 반복 실행하고 modelset aggregate를 생성한다.
- [확정] aggregate 기준은 `mean/std delta case F1`, `mean delta repeat std`, `mean delta calibration ECE`, judgement 분포다.
- [확정] baseline 공유 재사용 시 mmsi rows의 `baseline_reused`가 첫 MMSI만 `False`이고 이후 `True`여야 한다.
- [추가 검증 필요] 최종 결론 채택 전 `--no-reuse-baseline-across-mmsis` 1회 실행으로 민감도를 점검한다.

### 4.9 다중 seed 강건성 검증(보강)

```bash
PYTHONPATH=src python -m ais_risk.focus_seed_compare_cli \
  --manifest data/manifests/<dataset_id>.md \
  --raw-input data/raw/<source>/<dataset_id>/raw.csv \
  --output-prefix research_logs/$(date +%F)_<dataset_id>_focus_seed_compare \
  --output-root outputs/<dataset_id>_focus_seed_compare_runs \
  --focus-own-ship-mmsis <mmsi_a>,<mmsi_b>,<mmsi_c> \
  --seed-values 42,43,44 \
  --benchmark-modelsets "rule_score,logreg,hgbt;rule_score,logreg,hgbt,torch_mlp" \
  --pairwise-split-strategy own_ship \
  --run-calibration-eval \
  --run-own-ship-loo \
  --run-own-ship-case-eval \
  --own-ship-case-eval-repeat-count 5
```

- [확정] 출력에는 seed별 결과(`seed_rows`)와 modelset robustness 집계(`aggregate_by_modelset`)가 포함된다.
- [확정] `robustness_label`은 `focus_robust / baseline_robust / focus_tilt / baseline_tilt / mixed` 규칙으로 판정한다.
- [확정] 본문 결과표에는 단일 seed 점수 대신 seed 평균과 표준편차를 함께 제시한다.

### 4.10 자동 own-ship 후보 선택 + seed 강건성 일괄 실행

```bash
PYTHONPATH=src python -m ais_risk.focus_seed_pipeline_cli \
  --manifest data/manifests/<dataset_id>.md \
  --raw-input data/raw/<source>/<dataset_id>/raw.csv \
  --output-prefix research_logs/$(date +%F)_<dataset_id>_focus_seed_pipeline \
  --output-root outputs/<dataset_id>_focus_seed_pipeline_runs \
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

- [확정] `focus_seed_pipeline_cli`는 `workflow`의 own-ship ranking 상위 MMSI를 자동 추출한 뒤 seed 반복 검증을 연결한다.
- [확정] 수동 MMSI 검증으로 전환하려면 `--focus-own-ship-mmsis`를 지정하면 되고, 이 경우 자동 선택은 우회된다.
- [확정] 산출물로 `selected_focus_mmsis.csv`와 seed robustness 요약 JSON/MD를 같이 저장해 selection 근거와 결과를 함께 추적한다.
- [확정] validation gate 산출물(`validation_gate_overall_decision`, `validation_gate_recommended_modelset_key`, `validation_gate_rows.csv`)로 실험 종료 시점의 채택/보류 결정을 즉시 기록한다.

## 5. 성공 기준 또는 평가 기준

| 성공 조건 | 상태 |
|---|---|
| study_summary + validation_suite + study_journal 동시 생성 | [확정] |
| own-ship case에 CI95/repeat 안정성 지표 포함 | [확정] |
| 리더보드 경보 기준으로 run 간 악화 탐지 가능 | [확정] |

## 6. 리스크와 한계

| 항목 | 내용 | 상태 |
|---|---|---|
| 데이터 편향 | 특정 해역/기간에서만 성능 과대평가 가능 | [리스크] |
| 라벨 한계 | proxy 라벨은 실제 collision risk와 불일치 가능 | [리스크] |
| 계산량 | repeat_count/LOO 증가 시 실행시간 급증 | [리스크] |
| 데이터 수집 경로 | DMA endpoint DNS/접속 이슈로 raw 확보가 지연될 수 있음 | [리스크] |

## 7. 핵심 결정사항

1. [확정] baseline 우선, 딥러닝은 확장 비교안으로 유지.
2. [확정] 모델 선택은 단일 F1이 아니라 다중 경보 기준으로 결정.
3. [확정] 연구일지 자동 생성을 매 실행 루프의 종료 조건으로 고정.

## 8. 오픈 이슈

1. [추가 검증 필요] 해역별 경보 임계치 커스터마이징 전략.
2. [추가 검증 필요] own_ship_case repeat_count(3/5/7) 최적값.
3. [추가 검증 필요] torch_mlp의 MPS 재현성(런 간 편차) 정량화.

## 9. 다음 액션

1. 최근 3개 dataset_id에 동일 프로토콜 실행.
2. `validation_leaderboard`를 기준으로 alert_count 상위 run부터 원인분석.
3. 논문 본문에는 “성능 + 안정성 + calibration” 3축 표준표를 기본 결과표로 채택.
4. DMA 수집 실패 시 NOAA AccessAIS fallback runbook(`21`)으로 source 전환 후 동일 프로토콜 재실행.

## 교수/면접관 설명 팁

“이 프로젝트는 AI 모델 정확도 경쟁이 아니라, own-ship 중심 의사결정 지원에 필요한 일반화/안정성/보정(calibration) 검증 체계를 갖춘 점이 핵심입니다.”
