# 문서명
NOAA Houston Focus Quick Validation Runbook

# 문서 목적
NOAA 실데이터 수집 이후, Apple Silicon(`mps`) 환경에서 다중 모델을 빠르게 비교/검증하는 경량 실행 절차를 고정한다.

# 대상 독자
연구자, 데이터사이언티스트, ML 엔지니어

# 작성 버전
v1.5 (2026-03-13)

# 핵심 요약
- [확정] NOAA 일별 zip(`AIS_2023_08_01.zip`) 수집/병합/스키마 검증 완료.
- [확정] 밀도 기반 소구간(Houston 인근) subset(`35,019 rows`)으로 빠른 실험 루프를 구성.
- [확정] `rule_score/logreg/hgbt/torch_mlp(mps)` 4개 모델 benchmark + calibration + own-ship LOO + case repeat 수행.
- [확정] seed batch(42/43/44) 집계 결과, selection score 기준 추천 모델은 `logreg`.
- [확정] 61일 cross-month threshold stability와 61일 통합 모델 강화까지 확장 완료했으며, `hgbt` 우세와 threshold instability가 동시에 확인됐다.
- [리스크] pairwise dataset이 소규모(`353 rows`)이므로 과대평가 가능성이 있어 시간창/해역 확장 반복이 필요.

## 1. 배경 및 문제 정의

일별 NOAA raw는 900만 행 이상이라 전체 파이프라인의 반복 속도가 느려진다.  
연구 반복 속도와 검증 품질의 균형을 위해 `고밀도 소구간 subset -> 다중 모델 비교 -> own-ship 반복 검증` 구조로 경량 루프를 사용한다.

## 2. 목표와 비목표

| 구분 | 내용 | 상태 |
|---|---|---|
| 목표 | 실데이터 기반 다중 모델 학습/검증(MPS 포함) | [확정] |
| 목표 | own-ship 지정 반복 검증(LOO/case repeat) | [확정] |
| 비목표 | 전체 US coastal 1일 데이터 full-run의 즉시 완주 | [확정] |

## 3. 핵심 가정과 제약

| 항목 | 내용 | 상태 |
|---|---|---|
| 소구간 선택 | density scan 결과 상위 bin 기반 | [합리적 가정] |
| 실행 환경 | Apple Silicon + MPS | [확정] |
| 확장 필요 | 시간창/해역 확장 재검증 필요 | [추가 검증 필요] |

## 4. 상세 설계/요구사항/방법론

### 4.1 NOAA zip 수집/병합/스키마

```bash
PYTHONPATH=src python -m ais_risk.raw_merge_cli \
  --input-glob "data/raw/noaa/noaa_us_coastal_all_2023-08-01_2023-08-01_v1/downloads/2023-08-01/*.csv" \
  --output "data/raw/noaa/noaa_us_coastal_all_2023-08-01_2023-08-01_v1/raw.csv" \
  --summary-json "research_logs/2026-03-10_noaa_raw_merge_noaa_us_coastal_all_2023-08-01_summary.json"

PYTHONPATH=src python -m ais_risk.schema_probe_cli \
  --input "data/raw/noaa/noaa_us_coastal_all_2023-08-01_2023-08-01_v1/raw.csv" \
  --source-preset noaa_accessais \
  --sample-size 200 \
  --output "outputs/noaa_us_coastal_all_2023-08-01_2023-08-01_v1_schema_probe.json"
```

### 4.2 소구간 subset 생성

```bash
PYTHONPATH=src python -m ais_risk.preprocess_cli \
  --input "data/raw/noaa/noaa_us_coastal_all_2023-08-01_2023-08-01_v1/raw.csv" \
  --output "data/raw/noaa/noaa_us_coastal_all_2023-08-01_2023-08-01_v1/raw_focus_houston_0000_0659.csv" \
  --min-lat 29.0 --max-lat 30.5 \
  --min-lon -96.0 --max-lon -94.5 \
  --start-time 2023-08-01T00:00:00Z \
  --end-time 2023-08-01T06:59:59Z \
  --source-preset noaa_accessais \
  --vessel-types cargo,tanker,passenger,tug,service
```

### 4.3 경량 수동 검증 파이프라인

```bash
# 1) workflow tracks 준비(study_run을 쓰지 않고 이미 생성된 tracks 활용)
# tracks path:
# outputs/noaa_houston_focus_study_quick_2026-03-10/noaa_us_coastal_all_2023-08-01_2023-08-01_v1_workflow/tracks.csv

# 2) pairwise dataset 생성 (own ship 5개, timestamp cap 포함)
PYTHONPATH=src python -m ais_risk.pairwise_dataset_cli \
  --input "outputs/noaa_houston_focus_study_quick_2026-03-10/noaa_us_coastal_all_2023-08-01_2023-08-01_v1_workflow/tracks.csv" \
  --config configs/base.toml \
  --output "outputs/noaa_houston_manual_2026-03-10/noaa_houston_pairwise_dataset.csv" \
  --stats-output "outputs/noaa_houston_manual_2026-03-10/noaa_houston_pairwise_dataset_stats.json" \
  --own-mmsi 368184980 --own-mmsi 368198210 --own-mmsi 368216230 --own-mmsi 368110070 --own-mmsi 368221490 \
  --sample-every 5 \
  --label-distance-nm 1.6 \
  --max-timestamps-per-ship 120

# 3) 4모델 benchmark (MPS)
PYTHONPATH=src python -m ais_risk.benchmark_cli \
  --input "outputs/noaa_houston_manual_2026-03-10/noaa_houston_pairwise_dataset.csv" \
  --output-prefix "outputs/noaa_houston_manual_2026-03-10/noaa_houston_pairwise_benchmark" \
  --models rule_score,logreg,hgbt,torch_mlp \
  --split-strategy own_ship \
  --torch-device mps \
  --random-seed 42

# 4) calibration
PYTHONPATH=src python -m ais_risk.calibration_eval_cli \
  --predictions "outputs/noaa_houston_manual_2026-03-10/noaa_houston_pairwise_benchmark_test_predictions.csv" \
  --output-prefix "outputs/noaa_houston_manual_2026-03-10/noaa_houston_pairwise_calibration_eval" \
  --models rule_score,logreg,hgbt,torch_mlp \
  --num-bins 10

# 5) own-ship LOO (3 holdouts)
PYTHONPATH=src python -m ais_risk.own_ship_cv_cli \
  --input "outputs/noaa_houston_manual_2026-03-10/noaa_houston_pairwise_dataset.csv" \
  --output-prefix "outputs/noaa_houston_manual_2026-03-10/noaa_houston_pairwise_own_ship_loo" \
  --models rule_score,logreg,hgbt,torch_mlp \
  --holdout-own-mmsis 368184980,368198210,368216230 \
  --val-fraction 0.2 \
  --torch-device mps \
  --random-seed 42

# 6) own-ship case repeat (3 ships x repeat 3)
PYTHONPATH=src python -m ais_risk.own_ship_case_eval_cli \
  --input "outputs/noaa_houston_manual_2026-03-10/noaa_houston_pairwise_dataset.csv" \
  --output-prefix "outputs/noaa_houston_manual_2026-03-10/noaa_houston_pairwise_own_ship_case_eval" \
  --models rule_score,logreg,hgbt,torch_mlp \
  --own-mmsis 368184980,368198210,368216230 \
  --repeat-count 3 \
  --min-rows-per-ship 30 \
  --train-fraction 0.6 \
  --val-fraction 0.2 \
  --torch-device mps \
  --random-seed 42
```

### 4.4 focus-seed 확장(장시간 배치 권장)

```bash
PYTHONPATH=src python -m ais_risk.focus_seed_pipeline_cli \
  --manifest data/manifests/noaa_us_coastal_all_2023-08-01_2023-08-01_v1.md \
  --raw-input data/raw/noaa/noaa_us_coastal_all_2023-08-01_2023-08-01_v1/raw_focus_houston_0000_0659.csv \
  --output-prefix outputs/noaa_houston_manual_2026-03-10/noaa_houston_focus_seed_pipeline \
  --output-root outputs/noaa_houston_manual_focus_seed_runs_2026-03-10 \
  --source-preset auto \
  --focus-own-ship-mmsis 368184980,368198210,368216230 \
  --no-auto-select-focus-mmsis \
  --seed-values 42,43,44 \
  --benchmark-modelsets "rule_score,logreg,hgbt,torch_mlp" \
  --pairwise-split-strategy own_ship \
  --run-calibration-eval \
  --no-run-own-ship-loo \
  --run-own-ship-case-eval \
  --own-ship-case-eval-repeat-count 1 \
  --torch-device mps \
  --validation-gate-min-seed-count 3
```

주의: [리스크] 이 명령은 런타임이 길어 세션 내 즉시 완료가 어려울 수 있으므로 야간 배치(overnight) 실행을 권장한다.

## 5. 성공 기준 또는 평가 기준

| 항목 | 기준 | 상태 |
|---|---|---|
| MPS 학습 확인 | benchmark/LOO/case 결과에 `device=mps` 기록 | [확정] |
| 다중 모델 비교 | 4모델 공통 지표(F1/AUROC/AUPRC) 확보 | [확정] |
| 반복 검증 | LOO fold + case repeat aggregate 확보 | [확정] |
| calibration | Brier/ECE/bin 테이블 확보 | [확정] |
| seed 안정성 | seed 3개(42/43/44) 집계 점수 확보 | [확정] |

## 6. 리스크와 한계

| 항목 | 내용 | 상태 |
|---|---|---|
| 소표본 위험 | pairwise rows가 작아 분산/과대평가 가능 | [리스크] |
| 해역 편향 | Houston 근처 단일 구간으로 일반화 한계 | [리스크] |
| 시간창 편향 | 00:00~06:59 UTC 구간 중심 | [리스크] |

## 7. 핵심 결정사항

1. [확정] full-run보다 빠른 연구 반복을 위해 수동 경량 파이프라인을 우선 채택.
2. [확정] 모델 비교는 `rule/logreg/hgbt/torch_mlp(mps)` 4개를 고정.
3. [확정] 검증은 split 성능 + LOO + case repeat + calibration을 묶어서 해석.

## 8. 오픈 이슈

1. [추가 검증 필요] 동일 절차를 시간창 확장(12h/24h)으로 반복할 때 metric 안정성.
2. [추가 검증 필요] 다른 해역(예: Seattle/NOLA)에서 동일 경향 재현 여부.
3. [추가 검증 필요] focus-seed pipeline 장시간 연산을 위한 배치 전략(overnight run).

## 9. 61일 Cross-month 운영 메모

### 9.1 최신 확장 상태
- [확정] `2023-08-01~2023-09-15 + 2023-10-01~2023-10-15` 기준 61일 cross-month threshold stability 집계 완료:
  - `/Users/seoki/Desktop/research/outputs/scenario_threshold_stability_cross_date_61day_2026-03-13/scenario_threshold_stability_cross_date_61day_summary.md`
- [확정] 61일 통합 모델 강화 완료:
  - `/Users/seoki/Desktop/research/research_logs/2026-03-13_noaa_multidate_0801_0915_1001_1015_model_reinforcement.md`
- [확정] 61일 governed selection 완료:
  - `/Users/seoki/Desktop/research/research_logs/2026-03-13_governed_model_threshold_selection_61day.md`

### 9.2 최신 핵심 수치
- [확정] 61일 threshold stability: `unstable`, `majority_profile=s0p30_w0p55`, `majority_ratio=0.1803`, `mean_topk_jaccard=0.1388`
- [확정] 61일 모델 성능: `hgbt` benchmark F1 `0.9453`, ECE `0.0187`, LOO F1 mean `0.9241`, case F1 mean `0.9086`
- [확정] 61일 comparator: `logreg` benchmark F1 `0.8750`, LOO F1 mean `0.8953`, case F1 mean `0.9030`
- [리스크] threshold는 여전히 단일 default보다 shortlist 운영이 더 타당하다.

### 9.3 디스크 운영 규칙
- [확정] NOAA 장기 확장 중에는 zip 원본과 `raw.csv`를 남기고, 재생성 가능한 추출 CSV(`data/raw/noaa/**/downloads/*/AIS_*.csv`)는 주기적으로 정리해도 된다.
- [리스크] 추출 CSV를 누적 보관하면 unzip 단계에서 디스크 부족이 재발할 수 있다.

## 10. Time-window Stratified Pilot 메모

### 10.1 배경
- [확정] 기존 61일 `scenario_shift_multi`는 run당 sample이 3개로 고정돼 있어, `top-3` sensitivity가 사실상 전체 sample 집계였다.
- [확정] 따라서 selected-rank 편향을 직접 점검하려면 dense snapshot 파일럿이 별도로 필요했다.

### 10.2 파일럿 구성
- [확정] dense scenario-shift(2023-10-01~2023-10-15, 45 runs, sample_count=8, min_time_gap=90m):
  - `/Users/seoki/Desktop/research/outputs/scenario_shift_multi_2023-10-01_2023-10-15_dense_2026-03-13/scenario_shift_multi_2023-10-01_2023-10-15_dense_summary.md`
- [확정] sensitivity CLI 확장:
  - `/Users/seoki/Desktop/research/src/ais_risk/threshold_shortlist_sensitivity_cli.py`
  - 옵션: `--selection-mode selected_rank|time_window`, `--time-window-hours`

### 10.3 핵심 결과
- [확정] balanced baseline(`s0p30_w0p65`) 기준 overall에서 `s0p30_w0p55` warning delta는 `selected_rank +0.0514`, `time_window +0.0481`이었다.
- [확정] `s0p35_w0p65` caution delta는 `selected_rank -0.4319`, `time_window -0.4046`이었다.
- [확정] 두 방식 모두 `sector change ratio=0.0`으로, shortlist는 방향을 바꾸기보다 contour 면적을 조정하는 역할을 유지했다.
- [확정] 즉 `selected_rank`와 `time_window`를 바꿔도 shortlist role 해석은 유지됐다.

## 11. 61일 Holdout Figure Set 메모

### 11.1 최신 figure 세트
- [확정] 61일 shortlist 기준 holdout compare:
  - `/Users/seoki/Desktop/research/outputs/threshold_shortlist_holdout_compare_61day_2026-03-13/threshold_shortlist_holdout_compare_summary.md`
- [확정] Houston figure:
  - `/Users/seoki/Desktop/research/outputs/threshold_shortlist_holdout_compare_61day_2026-03-13/houston_24h_20231015/houston_24h_20231015_current_threshold_shortlist_compare.svg`
- [확정] NOLA figure:
  - `/Users/seoki/Desktop/research/outputs/threshold_shortlist_holdout_compare_61day_2026-03-13/nola_24h_20231015/nola_24h_20231015_current_threshold_shortlist_compare.svg`
- [확정] Seattle figure:
  - `/Users/seoki/Desktop/research/outputs/threshold_shortlist_holdout_compare_61day_2026-03-13/seattle_24h_20231015/seattle_24h_20231015_current_threshold_shortlist_compare.svg`

### 11.2 설명 규칙
- [확정] `default(s0p30_w0p55)`는 warning-inclusive profile로 설명한다.
- [확정] `balanced(s0p30_w0p65)`는 warning만 줄이고 caution은 유지하는 profile로 설명한다.
- [확정] `tight(s0p35_w0p65)`는 warning은 유지하고 caution까지 줄이는 profile로 설명한다.
- [확정] Seattle처럼 warning area가 애초에 0인 case에서는 `default`와 `balanced` 차이가 거의 없고, `tight`가 caution만 줄이는 예외가 아니라 low-warning case의 정상 패턴으로 본다.

## 12. 발표용 1페이지 요약 메모

### 12.1 산출물
- [확정] 61일 결과 기준 발표/피치용 1페이지 요약:
  - `/Users/seoki/Desktop/research/outputs/presentation_one_page_61day_2026-03-13/presentation_one_page_61day.md`

### 12.2 발표 문구 고정
- [확정] 모델 문구: `hgbt primary + logreg comparator`
- [확정] threshold 문구: `default/balanced/tight`
- [확정] 비주장 문구: `완전자율운항`, `법적 안전 경계`, `실제 충돌확률 정밀 추정`은 주장하지 않는다.

## 부록 A. Seed Batch 결과(42/43/44)

- 결과 경로:
  - `/Users/seoki/Desktop/research/outputs/noaa_houston_seed_batch_2026-03-10/noaa_houston_seed_batch_summary.json`
  - `/Users/seoki/Desktop/research/outputs/noaa_houston_seed_batch_2026-03-10/noaa_houston_seed_batch_summary.md`
- [확정] 추천 모델: `logreg`.

| model | device | benchmark_f1_mean | loo_f1_mean_mean | single_case_f1_mean_mean | ece_mean | selection_score |
|---|---|---:|---:|---:|---:|---:|
| rule_score | cpu | 0.3261 | 0.3969 | 0.6524 | 0.1407 | 0.3801 |
| logreg | cpu | 0.8485 | 0.9297 | 0.7214 | 0.0836 | 0.6729 |
| hgbt | cpu | 0.7778 | 0.9495 | 0.4042 | 0.0552 | 0.5905 |
| torch_mlp | mps | 0.5794 | 0.8965 | 0.7387 | 0.2583 | 0.6441 |

해석:
- [확정] `logreg`를 기본 모델로 두고, `hgbt`를 calibration/LOO 강점 비교군으로 유지.
- [리스크] 현재 결론은 Houston 소구간·소표본 조건에 한정된다.

## 부록 B. 12h 확장 검증(00:00-11:59) 결과

경로:
- `/Users/seoki/Desktop/research/research_logs/2026-03-10_noaa_houston_12h_validation.md`
- `/Users/seoki/Desktop/research/outputs/noaa_houston_manual_12h_2026-03-10`

핵심 수치:
- [확정] pairwise rows: `624` (6h 대비 증가).
- [확정] benchmark F1: `logreg=0.8485`, `hgbt=0.7778`, `torch_mlp=0.5091`.
- [확정] own-ship LOO F1 mean: `hgbt=0.9434`(최고), `logreg=0.8894`.
- [확정] own-ship case F1 mean: `hgbt=0.8970`(최고), `logreg=0.8193`.
- [확정] calibration ECE: `hgbt=0.0176`(최고), `logreg=0.1096`, `torch_mlp=0.1760`.

판단:
- [합리적 가정] 소표본 6h에서는 `logreg` 균형이 우세했으나, 12h 확장에서는 `hgbt`의 안정성/캘리브레이션 우위가 더 명확해졌다.
- [추가 검증 필요] 24h 및 타 해역에서 동일 경향이 재현되는지 확인 후 기본 모델을 최종 고정.

추가 seed 집계:
- [확정] 12h seed batch(42/43/44) 결과:
  - `/Users/seoki/Desktop/research/outputs/noaa_houston_12h_seed_batch_2026-03-10/noaa_houston_12h_seed_batch_summary.md`
- [확정] selection score 추천 모델: `hgbt` (`0.8802`), 2순위 `logreg` (`0.8669`).

## 부록 C. 24h 확장 검증(00:00-23:59, seed=42)

경로:
- `/Users/seoki/Desktop/research/research_logs/2026-03-10_noaa_houston_24h_validation.md`
- `/Users/seoki/Desktop/research/outputs/noaa_houston_manual_24h_2026-03-10`

핵심 수치:
- [확정] pairwise rows: `916`.
- [확정] benchmark F1: `hgbt=0.8718`, `logreg=0.7805`, `torch_mlp=0.6818`.
- [확정] own-ship LOO F1 mean: `logreg=0.9544`, `hgbt=0.9527` (거의 동급).
- [확정] own-ship case F1 mean: `hgbt=0.9211`(최고), `logreg=0.8530`.
- [확정] calibration ECE: `hgbt=0.0266`(최고), `logreg=0.0432`.

판단:
- [합리적 가정] 시간창을 24h로 늘릴수록 `hgbt` 우세가 강화되는 경향이 보인다.
- [확정] 24h seed batch(42/43/44)에서도 `hgbt`가 추천 모델로 유지된다.

추가 seed 집계:
- [확정] 24h seed batch 결과:
  - `/Users/seoki/Desktop/research/outputs/noaa_houston_24h_seed_batch_2026-03-10/noaa_houston_24h_seed_batch_summary.md`
- [확정] selection score: `hgbt=0.9338`, `logreg=0.8940`, `torch_mlp=0.8107`.

## 부록 D. 타 해역 일반화 스모크(NOLA 12h)

경로:
- `/Users/seoki/Desktop/research/research_logs/2026-03-10_noaa_nola_12h_validation.md`
- `/Users/seoki/Desktop/research/outputs/noaa_nola_12h_seed_batch_2026-03-10/noaa_nola_12h_seed_batch_summary.md`

핵심:
- [확정] NOLA 12h seed batch(42/43/44) 추천 모델은 `logreg`(`0.6615`).
- [확정] Houston(12h/24h)과 달리 NOLA 12h에서는 `hgbt`의 single-case 축 점수가 낮아 종합 점수에서 밀렸다.
- [리스크] NOLA pairwise rows(`446`)는 소표본이라 24h 확장 전 모델 고정 결론으로 사용하면 과적합 해석 위험이 있다.

추가 확장:
- [확정] NOLA 24h seed batch(42/43/44) 결과:
  - `/Users/seoki/Desktop/research/outputs/noaa_nola_24h_seed_batch_2026-03-10/noaa_nola_24h_seed_batch_summary.md`
- [확정] 24h에서는 `hgbt`가 추천 모델(`0.7619`)로 복귀, `logreg=0.6465`.
- [해석] [합리적 가정] NOLA도 시간창 확대(표본 증가) 시 `hgbt` 강점이 재확인된다.

Seattle 추가:
- [확정] Seattle 12h seed batch(42/43/44) 결과:
  - `/Users/seoki/Desktop/research/outputs/noaa_seattle_12h_seed_batch_2026-03-10/noaa_seattle_12h_seed_batch_summary.md`
- [확정] 추천 모델은 `hgbt`(`0.7752`), `logreg`(`0.7673`)와 근소 차이.
- [리스크] Seattle 12h pairwise rows(`174`)는 소표본이라 24h 확장 전 결론 고정은 보류.

Seattle 24h 확장:
- [확정] Seattle 24h seed batch(42/43/44) 결과:
  - `/Users/seoki/Desktop/research/outputs/noaa_seattle_24h_seed_batch_2026-03-10/noaa_seattle_24h_seed_batch_summary.md`
- [확정] 24h에서는 `logreg`가 추천 모델(`0.6187`), `hgbt=0.5952`.
- [해석] [리스크] Seattle은 12h/24h 사이 추천 모델이 바뀌므로, 해역별 모델 고정 대신 seed-batch 재평가 절차를 운영 규칙으로 채택해야 한다.

Multi-own 편향 완화:
- [확정] Houston/NOLA/Seattle 24h에서 multi-own case 재평가 추가.
  - Houston: `/Users/seoki/Desktop/research/outputs/noaa_houston_24h_seed_batch_multiown_2026-03-10/houston_24h_multiown_summary.md`
  - NOLA: `/Users/seoki/Desktop/research/outputs/noaa_nola_24h_seed_batch_multiown_2026-03-10/nola_24h_multiown_summary.md`
  - Seattle: `/Users/seoki/Desktop/research/outputs/noaa_seattle_24h_seed_batch_multiown_2026-03-10/seattle_24h_multiown_summary.md`
- [확정] calibration gate(ECE<=0.25, LOO>=0.60)를 함께 적용하면 24h 기준 권고 모델이 일관되게 `hgbt`로 수렴.
- [확정] 요약: `/Users/seoki/Desktop/research/research_logs/2026-03-10_multiown_bias_mitigation_summary.md`
- [확정] 24h governed matrix: `/Users/seoki/Desktop/research/research_logs/2026-03-10_model_selection_matrix_24h_governed.md`

Holdout spatial 검증:
- [확정] holdout(test split) 예측 기반 heatmap/contour 비교 완료.
  - `/Users/seoki/Desktop/research/research_logs/2026-03-10_spatial_holdout_compare.md`
- [확정] Houston/NOLA 24h에서 holdout 기준으로도 `hgbt`가 공간 표현 품질(F1+고위험 면적) 우세.
- [리스크] Seattle 24h는 holdout test rows가 작아 단정 결론을 보류.
- [확정] governed recommendation 산출을 CLI로 고정:
  - `/Users/seoki/Desktop/research/outputs/governed_selection_24h_2026-03-10/governed_selection_24h_summary.md`
  - `PYTHONPATH=src python -m ais_risk.governed_selection_cli ...`

## 부록 E. Spatial Heatmap/Contour 비교 산출물

경로:
- `/Users/seoki/Desktop/research/research_logs/2026-03-10_spatial_heatmap_contour_compare.md`
- `/Users/seoki/Desktop/research/outputs/spatial_risk_model_compare_2026-03-10/houston_24h_rule_logreg_hgbt_heatmap_contour.png`
- `/Users/seoki/Desktop/research/outputs/spatial_risk_model_compare_2026-03-10/nola_12h_rule_logreg_hgbt_heatmap_contour.png`

핵심:
- [확정] rule baseline은 고위험(0.65+) 영역 형성이 거의 없고, `logreg/hgbt`에서 고위험 영역이 생성된다.
- [추가 검증 필요] 현재는 학습 전체 기준 시각화라, holdout 기반 재생성 후 최종 발표판으로 고정한다.

## 부록 F. Scenario Shift 다중 스냅샷(해역당 3개)

경로:
- `/Users/seoki/Desktop/research/outputs/scenario_shift_multi_2026-03-10/scenario_shift_multi_summary.md`

핵심:
- [확정] Houston/NOLA 24h는 다중 샘플에서도 `warning area delta`가 거의 0에 수렴.
- [확정] Seattle 24h는 `speedup_mean_risk_delta` 평균 `+0.0034`, `speedup_caution_area_nm2_delta` 평균 `+0.2855`로 scenario 민감도가 상대적으로 큼.
- [확정] 발표 지표는 `warning area` 단독보다 `caution area + mean risk` 조합이 더 일관적이다.

## 부록 G. Scenario Threshold Sweep

경로:
- `/Users/seoki/Desktop/research/outputs/scenario_threshold_sweep_2026-03-10/scenario_threshold_sweep_summary.md`
- `/Users/seoki/Desktop/research/research_logs/2026-03-10_scenario_threshold_sweep.md`

핵심:
- [확정] `mean risk` 기반 speedup delta는 threshold(base/conservative/sensitive) 변경에도 안정적이다.
- [확정] `caution/warning area`는 threshold 민감도가 커서 profile을 함께 명시해야 해석 왜곡이 줄어든다.
- [확정] Seattle 24h는 threshold에 따라 speedup area delta가 크게 변해(보수 profile: 축소, 민감 profile: 확대) 시각 경계선 설명에 주의가 필요하다.

## 부록 H. Scenario Threshold Tuning(Grid)

경로:
- `/Users/seoki/Desktop/research/outputs/scenario_threshold_tuning_2026-03-10/scenario_threshold_tuning_summary.md`
- `/Users/seoki/Desktop/research/research_logs/2026-03-10_scenario_threshold_tuning.md`

핵심:
- [확정] grid(`safe 0.25~0.45`, `warning 0.55~0.80`) 탐색에서 추천 profile은 `safe=0.35`, `warning=0.60`.
- [확정] 상위권 profile 간 objective 점수 차이가 작아(동점 다수) 현재 데이터에서는 날짜 확장 후 재튜닝이 필요.
- [합리적 가정] 시연 기본은 `0.35/0.60`, 비교선은 `0.35/0.65`를 병행하면 운영/연구 설명 균형이 좋다.
- [확정] bootstrap(400회) 기준 추천 profile top-1 빈도는 `0.1475`로 낮아, threshold는 단일값 확정 대신 상위 후보군(예: `0.35/0.60`, `0.35/0.65`) 병행 관리가 타당하다.
- [확정] bootstrap seed 민감도(42/7/99)에서도 추천 profile은 `s0p35_w0p60`로 일치했지만, 평균 top-1 빈도는 `0.125`로 낮아 안정성 상태는 `unstable`.
- [확정] 다중 tuning summary 안정성 집계는 `scenario_threshold_stability_cli`로 자동화 가능:
  - `/Users/seoki/Desktop/research/outputs/scenario_threshold_stability_seed_sensitivity_2026-03-10/scenario_threshold_stability_seed_sensitivity_summary.md`
- [확정] 해역별 focus->tracks->pairwise 재생성은 `noaa_focus_pairwise_bundle_cli`로 일괄 실행 가능:
  - `/Users/seoki/Desktop/research/outputs/noaa_focus_pairwise_bundle_2026-03-10/noaa_focus_pairwise_bundle_2023-08-01_summary.md`
- [확정] cross-date 7일(2023-08-01~08-07) 비교에서도 추천 profile이 날짜마다 달라 단일 threshold 고정은 위험하다.
- [확정] 7일 안정성 집계:
  - `/Users/seoki/Desktop/research/outputs/scenario_threshold_stability_cross_date_7day_2026-03-10/scenario_threshold_stability_cross_date_7day_summary.md`

## 부록 I. Tuned Config 반영

경로:
- `/Users/seoki/Desktop/research/configs/base_tuned_s035_w060.toml`
- `/Users/seoki/Desktop/research/outputs/scenario_threshold_profile_compare_2026-03-10/scenario_threshold_profile_compare_summary.md`

핵심:
- [확정] tuned config(`safe=0.35`, `warning=0.60`)는 base 대비 Seattle 24h speedup warning delta를 소폭 확대(`+0.0121`)한다.
- [확정] Houston/NOLA 24h에서는 tuned/base 차이가 거의 없었다.

## 부록 J. Multi-date 모델 강화(08-01~08-07 통합)

경로:
- `/Users/seoki/Desktop/research/research_logs/2026-03-10_noaa_multidate_0801_0807_model_reinforcement.md`
- `/Users/seoki/Desktop/research/outputs/noaa_multidate_0801_0807_2026-03-10/noaa_multidate_benchmark_summary.md`
- `/Users/seoki/Desktop/research/outputs/noaa_multidate_0801_0807_2026-03-10/noaa_multidate_calibration_eval_summary.md`
- `/Users/seoki/Desktop/research/outputs/noaa_multidate_0801_0807_2026-03-10/noaa_multidate_own_ship_loo_own_ship_loo_summary.md`
- `/Users/seoki/Desktop/research/outputs/noaa_multidate_0801_0807_2026-03-10/noaa_multidate_own_ship_case_eval_summary.md`

핵심:
- [확정] 통합 dataset(`7,791 rows`, own_mmsi `15`)에서 `hgbt`가 benchmark/calibration/LOO/case repeat 전반 우세.
- [확정] `logreg`는 성능이 높고 해석 가능성이 좋아 비교/설명 baseline으로 유지 가치가 높다.
- [합리적 가정] 현재 스케일에서는 `torch_mlp(mps)`를 주력 모델보다 GPU comparator로 유지하는 편이 효율적이다.

자동화:
- [확정] 일자 반복 파이프라인은 `/Users/seoki/Desktop/research/examples/noaa_daily_bundle_shift_tuning.sh`로 고정 가능.
- [확정] NOAA zip 안정 다운로드는 `/Users/seoki/Desktop/research/examples/noaa_parallel_download.py`로 고정 가능.
- [확정] 다일자 배치 래퍼는 `/Users/seoki/Desktop/research/examples/noaa_batch_days.sh`로 고정 가능.
- [추가 검증 필요] 31일 이후는 동일 스크립트 조합으로 cross-month(예: 9월 초) 안정성 지표를 누적해 threshold 변동성을 재평가.

## 부록 K. 10일 확장(08-01~08-10)

경로:
- `/Users/seoki/Desktop/research/research_logs/2026-03-12_noaa_2023-08-08_2023-08-10_cross_date_10day_stability.md`
- `/Users/seoki/Desktop/research/outputs/scenario_threshold_stability_cross_date_10day_2026-03-12/scenario_threshold_stability_cross_date_10day_summary.md`
- `/Users/seoki/Desktop/research/research_logs/2026-03-12_noaa_multidate_0801_0810_model_reinforcement.md`
- `/Users/seoki/Desktop/research/outputs/noaa_multidate_0801_0810_2026-03-12/noaa_multidate_benchmark_summary.md`
- `/Users/seoki/Desktop/research/outputs/noaa_multidate_0801_0810_2026-03-12/noaa_multidate_calibration_eval_summary.md`
- `/Users/seoki/Desktop/research/outputs/noaa_multidate_0801_0810_2026-03-12/noaa_multidate_own_ship_loo_own_ship_loo_summary.md`
- `/Users/seoki/Desktop/research/outputs/noaa_multidate_0801_0810_2026-03-12/noaa_multidate_own_ship_case_eval_summary.md`

핵심:
- [확정] 10일 안정성 집계에서도 `stability_status=unstable`, `recommendation_majority_ratio=0.2000`, `mean_topk_jaccard=0.1206`으로 threshold 수렴 신호가 약하다.
- [확정] 추천 profile은 `s0p35_w0p70`와 `s0p30_w0p55`가 각각 2회 추천되어, 단일 threshold 고정 전략은 방어가 어렵다.
- [확정] 10일 통합 dataset(`11,191 rows`, own_mmsi `15`) 기준으로도 `hgbt`가 benchmark(F1 `0.9537`)·calibration(ECE `0.0278`)·LOO(F1 mean `0.9167`)·case repeat(F1 mean `0.8773`)에서 가장 안정적이다.
- [확정] `logreg`는 성능이 높고 설명 가능성이 좋아 비교 baseline으로 유지 가치가 높다.
- [합리적 가정] 현재 운영/발표 조합은 `hgbt primary + logreg comparator + threshold shortlist`가 가장 현실적이다.

## 부록 L. 14일 확장(08-01~08-14)

경로:
- `/Users/seoki/Desktop/research/research_logs/2026-03-12_noaa_2023-08-11_2023-08-14_cross_date_14day_stability.md`
- `/Users/seoki/Desktop/research/outputs/scenario_threshold_stability_cross_date_14day_2026-03-12/scenario_threshold_stability_cross_date_14day_summary.md`
- `/Users/seoki/Desktop/research/research_logs/2026-03-12_noaa_multidate_0801_0814_model_reinforcement.md`
- `/Users/seoki/Desktop/research/outputs/noaa_multidate_0801_0814_2026-03-12/noaa_multidate_benchmark_summary.md`
- `/Users/seoki/Desktop/research/outputs/noaa_multidate_0801_0814_2026-03-12/noaa_multidate_calibration_eval_summary.md`
- `/Users/seoki/Desktop/research/outputs/noaa_multidate_0801_0814_2026-03-12/noaa_multidate_own_ship_loo_own_ship_loo_summary.md`
- `/Users/seoki/Desktop/research/outputs/noaa_multidate_0801_0814_2026-03-12/noaa_multidate_own_ship_case_eval_summary.md`

핵심:
- [확정] 14일 안정성 집계에서도 `stability_status=unstable`, `recommendation_majority_ratio=0.1429`, `mean_topk_jaccard=0.1298`으로 threshold 수렴 신호가 약하다.
- [확정] 추천 profile은 `s0p30_w0p55`, `s0p35_w0p65`, `s0p35_w0p70`, `s0p30_w0p70`이 각각 2회 추천되어 사실상 4-way tie에 가깝다.
- [확정] 14일 통합 dataset(`16,035 rows`, own_mmsi `15`) 기준으로도 `hgbt`가 benchmark(F1 `0.9546`)·calibration(ECE `0.0212`)·LOO(F1 mean `0.9140`)·case repeat(F1 mean `0.8787`)에서 가장 안정적이다.
- [확정] `logreg`는 여전히 설명 가능한 비교 baseline으로 유지 가치가 높다.
- [합리적 가정] 현재 운영/발표 조합은 계속 `hgbt primary + logreg comparator + threshold shortlist`가 가장 현실적이다.

## 부록 M. 21일 확장(08-01~08-21)

경로:
- `/Users/seoki/Desktop/research/research_logs/2026-03-12_noaa_2023-08-15_2023-08-21_cross_date_21day_stability.md`
- `/Users/seoki/Desktop/research/outputs/scenario_threshold_stability_cross_date_21day_2026-03-12/scenario_threshold_stability_cross_date_21day_summary.md`
- `/Users/seoki/Desktop/research/research_logs/2026-03-12_noaa_multidate_0801_0821_model_reinforcement.md`
- `/Users/seoki/Desktop/research/outputs/noaa_multidate_0801_0821_2026-03-12/noaa_multidate_benchmark_summary.md`
- `/Users/seoki/Desktop/research/outputs/noaa_multidate_0801_0821_2026-03-12/noaa_multidate_calibration_eval_summary.md`
- `/Users/seoki/Desktop/research/outputs/noaa_multidate_0801_0821_2026-03-12/noaa_multidate_own_ship_loo_own_ship_loo_summary.md`
- `/Users/seoki/Desktop/research/outputs/noaa_multidate_0801_0821_2026-03-12/noaa_multidate_own_ship_case_eval_summary.md`

핵심:
- [확정] 21일 안정성 집계에서도 `stability_status=unstable`, `recommendation_majority_ratio=0.1429`, `mean_topk_jaccard=0.1256`, `mean_recommended_bootstrap_top1_frequency=0.0976`으로 threshold 수렴 신호가 없다.
- [확정] 추천 count 상위 profile은 `s0p30_w0p65=3`, `s0p35_w0p65=3`, `s0p30_w0p55=2`로 분산돼 있으며, single threshold보다 shortlist 운영이 더 타당하다.
- [확정] 21일 통합 dataset(`23,842 rows`, own_mmsi `15`) 기준으로도 `hgbt`가 benchmark(F1 `0.9543`)·calibration(ECE `0.0222`)·LOO(F1 mean `0.9090`)·case repeat(F1 mean `0.8958`)에서 가장 안정적이다.
- [확정] `logreg`는 성능이 높고 설명 가능성이 좋아 comparator로 유지 가치가 높다.
- [합리적 가정] 현재 운영/발표 조합은 계속 `hgbt primary + logreg comparator + threshold shortlist`가 가장 현실적이다.

## 부록 N. 31일 확장(08-01~08-31)

경로:
- `/Users/seoki/Desktop/research/research_logs/2026-03-12_noaa_2023-08-22_2023-08-31_cross_date_31day_stability.md`
- `/Users/seoki/Desktop/research/outputs/scenario_threshold_stability_cross_date_31day_2026-03-12/scenario_threshold_stability_cross_date_31day_summary.md`
- `/Users/seoki/Desktop/research/research_logs/2026-03-12_noaa_multidate_0801_0831_model_reinforcement.md`
- `/Users/seoki/Desktop/research/outputs/noaa_multidate_0801_0831_2026-03-12/noaa_multidate_benchmark_summary.md`
- `/Users/seoki/Desktop/research/outputs/noaa_multidate_0801_0831_2026-03-12/noaa_multidate_calibration_eval_summary.md`
- `/Users/seoki/Desktop/research/outputs/noaa_multidate_0801_0831_2026-03-12/noaa_multidate_own_ship_loo_own_ship_loo_summary.md`
- `/Users/seoki/Desktop/research/outputs/noaa_multidate_0801_0831_2026-03-12/noaa_multidate_own_ship_case_eval_summary.md`

핵심:
- [확정] 31일 안정성 집계에서도 `stability_status=unstable`, `recommendation_majority_ratio=0.1290`, `mean_topk_jaccard=0.1427`, `mean_recommended_bootstrap_top1_frequency=0.1067`으로 threshold 수렴 신호는 여전히 약하다.
- [확정] 추천 count 상위 profile은 `s0p35_w0p65=4`, `s0p30_w0p65=4`, `s0p30_w0p55=4`로 분산돼 있으며, single threshold보다 shortlist 운영이 더 타당하다.
- [확정] 31일 통합 dataset(`34,889 rows`, own_mmsi `15`) 기준으로도 `hgbt`가 benchmark(F1 `0.9539`)·calibration(ECE `0.0202`)·LOO(F1 mean `0.9208`)·case repeat(F1 mean `0.9030`)에서 가장 안정적이다.
- [확정] 21일 대비 majority ratio는 낮아졌지만, top-k overlap과 `hgbt`의 반복 검증 안정성은 오히려 좋아졌다.
- [합리적 가정] 현재 운영/발표 조합은 계속 `hgbt primary + logreg comparator + threshold shortlist`가 가장 현실적이다.

## 9. 다음 액션

1. `focus_seed_pipeline`은 `1 seed/1 modelset` micro부터 완료 후 gate 확인.
2. `2023-09-01~09-15` 또는 다른 NOAA 기간을 추가해 cross-month stability를 확인.
3. shortlisted threshold별 holdout heatmap/contour 비교 세트를 고정.
4. run별 연구일지를 `validation_leaderboard/batch_trend`로 누적 추적.

설명 팁: “실데이터 수집-정제-다중모델-MPS-반복검증을 먼저 빠르게 닫고, 이후 범위를 확장하는 단계형 검증 전략”으로 설명하면 실무성과 연구성을 함께 방어하기 좋다.

## 부록 O. 46일 cross-month 확장(08-01~09-15)

경로:
- `/Users/seoki/Desktop/research/research_logs/2026-03-12_noaa_2023-09-01_2023-09-15_cross_month_46day_stability.md`
- `/Users/seoki/Desktop/research/outputs/scenario_threshold_stability_cross_date_46day_2026-03-12/scenario_threshold_stability_cross_date_46day_summary.md`
- `/Users/seoki/Desktop/research/research_logs/2026-03-12_noaa_multidate_0801_0915_model_reinforcement.md`
- `/Users/seoki/Desktop/research/outputs/noaa_multidate_0801_0915_2026-03-12/noaa_multidate_benchmark_summary.md`
- `/Users/seoki/Desktop/research/outputs/noaa_multidate_0801_0915_2026-03-12/noaa_multidate_calibration_eval_summary.md`
- `/Users/seoki/Desktop/research/outputs/noaa_multidate_0801_0915_2026-03-12/noaa_multidate_own_ship_loo_own_ship_loo_summary.md`
- `/Users/seoki/Desktop/research/outputs/noaa_multidate_0801_0915_2026-03-12/noaa_multidate_own_ship_case_eval_summary.md`

핵심:
- [확정] 46일 안정성 집계에서도 `stability_status=unstable`, `recommendation_majority_ratio=0.1522`, `mean_topk_jaccard=0.1407`, `mean_recommended_bootstrap_top1_frequency=0.1141`으로 threshold 수렴 신호는 여전히 약하다.
- [확정] 추천 count 상위 profile은 `s0p30_w0p65=7`, `s0p30_w0p55=7`, `s0p35_w0p65=5`로 분산돼 있으며, single threshold보다 shortlist 운영이 더 타당하다.
- [확정] 46일 통합 dataset(`50,932 rows`, own_mmsi `15`) 기준으로도 `hgbt`가 benchmark(F1 `0.9487`)·calibration(ECE `0.0191`)·LOO(F1 mean `0.9196`)·case repeat(F1 mean `0.8984`)에서 가장 안정적이다.
- [확정] `logreg`는 benchmark F1 `0.8803`, calibration ECE `0.0706`, LOO F1 mean `0.8861`, case repeat F1 mean `0.8647`로 설명 가능한 comparator로 계속 유효하다.
- [합리적 가정] 현재 운영/발표 조합은 계속 `hgbt primary + logreg comparator + threshold shortlist`가 가장 현실적이다.

## 10. 다음 액션

1. `focus_seed_pipeline`은 `1 seed/1 modelset` micro부터 완료 후 gate 확인.
2. `2023-10-06~2023-10-15`를 추가해 56일 또는 61일 cross-month 파일럿으로 확장.
3. selected rank 외 sampling 방식으로 threshold shortlist sensitivity 검증 범위를 확대.
4. run별 연구일지를 `validation_leaderboard/batch_trend`로 누적 추적.

설명 팁: “월 단위로 범위를 넓혀도 threshold는 단일값으로 수렴하지 않았지만, 모델 우위(`hgbt`)와 shortlist 구조는 유지됐다”라고 설명하면 연구적으로 더 정직하고 설득력 있다.

## 부록 P. Threshold Shortlist Holdout Compare

경로:
- `/Users/seoki/Desktop/research/research_logs/2026-03-12_threshold_shortlist_holdout_compare.md`
- `/Users/seoki/Desktop/research/outputs/threshold_shortlist_holdout_compare_2026-03-12/threshold_shortlist_holdout_compare_summary.md`
- `/Users/seoki/Desktop/research/outputs/threshold_shortlist_holdout_compare_2026-03-12/houston_24h_20230915/houston_24h_20230915_current_threshold_shortlist_compare.svg`
- `/Users/seoki/Desktop/research/outputs/threshold_shortlist_holdout_compare_2026-03-12/nola_24h_20230915/nola_24h_20230915_current_threshold_shortlist_compare.svg`
- `/Users/seoki/Desktop/research/outputs/threshold_shortlist_holdout_compare_2026-03-12/seattle_24h_20230915/seattle_24h_20230915_current_threshold_shortlist_compare.svg`

실행 명령:
- `PYTHONPATH=src python -m ais_risk.threshold_shortlist_holdout_compare_cli --scenario-shift-summary outputs/scenario_shift_multi_2023-09-15_2026-03-12/scenario_shift_multi_2023-09-15_summary.json --output-dir outputs/threshold_shortlist_holdout_compare_2026-03-12 --profile s0p30_w0p65:0.30:0.65 --profile s0p30_w0p55:0.30:0.55 --profile s0p35_w0p65:0.35:0.65 --scenario-name current --prefer-warning-nonzero`

핵심:
- [확정] `warning threshold 0.65 -> 0.55`는 representative holdout 3건 모두에서 warning area를 확대했다.
- [확정] `safe threshold 0.30 -> 0.35`는 같은 warning threshold에서 caution area를 축소했다.
- [확정] shortlist 내부 차이는 dominant sector를 크게 바꾸지 않았고, contour 면적 조정 효과가 더 컸다.
- [리스크] 현재는 해역별 대표 case 1개씩이라 통계화는 추가로 필요하다.

## 부록 Q. Governed Model/Threshold Selection (46-day)

경로:
- `/Users/seoki/Desktop/research/research_logs/2026-03-13_governed_model_threshold_selection_46day.md`
- `/Users/seoki/Desktop/research/outputs/governed_model_threshold_selection_46day_2026-03-13/governed_model_threshold_selection_46day_summary.md`

실행 명령:
- `PYTHONPATH=src python -m ais_risk.governed_model_threshold_selection_cli --benchmark-summary outputs/noaa_multidate_0801_0915_2026-03-12/noaa_multidate_benchmark_summary.json --calibration-summary outputs/noaa_multidate_0801_0915_2026-03-12/noaa_multidate_calibration_eval_summary.json --loo-summary outputs/noaa_multidate_0801_0915_2026-03-12/noaa_multidate_own_ship_loo_own_ship_loo_summary.json --case-summary outputs/noaa_multidate_0801_0915_2026-03-12/noaa_multidate_own_ship_case_eval_summary.json --threshold-stability-summary outputs/scenario_threshold_stability_cross_date_46day_2026-03-12/scenario_threshold_stability_cross_date_46day_summary.json --threshold-compare-summary outputs/threshold_shortlist_holdout_compare_2026-03-12/threshold_shortlist_holdout_compare_summary.json --output-prefix outputs/governed_model_threshold_selection_46day_2026-03-13/governed_model_threshold_selection_46day`

핵심:
- [확정] model gate를 통과한 모델은 `hgbt`, `logreg` 두 개뿐이다.
- [확정] primary model은 `hgbt`, comparator는 `logreg`로 고정 가능하다.
- [확정] default threshold profile은 `s0p30_w0p65`, warning-sensitive profile은 `s0p30_w0p55`, caution-tight profile은 `s0p35_w0p65`다.
- [확정] threshold role은 contour 면적 조정 관점에서 설명하는 편이 가장 자연스럽다.

## 부록 R. Threshold Shortlist Sensitivity Aggregate (46-source, top-1)

경로:
- `/Users/seoki/Desktop/research/research_logs/2026-03-13_threshold_shortlist_sensitivity_46day_top1.md`
- `/Users/seoki/Desktop/research/outputs/threshold_shortlist_sensitivity_46day_top1_full_2026-03-13/threshold_shortlist_sensitivity_46day_top1_full_summary.md`

핵심:
- [확정] 전체 `138 case`에서 `s0p30_w0p55`는 default 대비 warning area를 평균 `+0.0572 nm2` 확대했고, warning increase ratio는 `0.6014`였다.
- [확정] 전체 `138 case`에서 `s0p35_w0p65`는 default 대비 caution area를 평균 `-0.4423 nm2` 축소했고, caution decrease ratio는 `0.9855`였다.
- [확정] Houston/NOLA/Seattle 모든 지역에서 `sector change ratio=0.0`으로, shortlist 차이는 방향 변경보다 contour 면적 조정에 가깝다.
- [확정] 따라서 `default/sensitive/tight` 역할 분담은 representative 3-case를 넘어 aggregate 수준에서도 유지된다.

## 부록 S. Threshold Shortlist Sensitivity Aggregate (46-source, top-2)

경로:
- `/Users/seoki/Desktop/research/research_logs/2026-03-13_threshold_shortlist_sensitivity_46day_top2.md`
- `/Users/seoki/Desktop/research/outputs/threshold_shortlist_sensitivity_46day_top2_full_2026-03-13/threshold_shortlist_sensitivity_46day_top2_full_summary.md`

실행 명령:
- `PYTHONPATH=src python -m ais_risk.threshold_shortlist_sensitivity_cli --summary-json outputs/scenario_shift_multi_2026-03-10/scenario_shift_multi_summary.json --summary-json-glob 'outputs/scenario_shift_multi_2023-*_2026-03-*/scenario_shift_multi_2023-*_summary.json' --output-prefix outputs/threshold_shortlist_sensitivity_46day_top2_full_2026-03-13/threshold_shortlist_sensitivity_46day_top2_full --profile s0p30_w0p65:0.30:0.65 --profile s0p30_w0p55:0.30:0.55 --profile s0p35_w0p65:0.35:0.65 --default-profile s0p30_w0p65 --scenario-name current --max-cases-per-run 2`

핵심:
- [확정] 전체 `276 case`에서 `s0p30_w0p55`는 default 대비 warning area를 평균 `+0.0575 nm2` 확대했고, warning increase ratio는 `0.6014`였다.
- [확정] 전체 `276 case`에서 `s0p35_w0p65`는 default 대비 caution area를 평균 `-0.4064 nm2` 축소했고, caution decrease ratio는 `0.9565`였다.
- [확정] Houston/NOLA/Seattle 모든 지역에서 `sector change ratio=0.0`으로, shortlist 차이는 top-2에서도 여전히 contour 면적 조정에 가깝다.
- [확정] 따라서 `default/sensitive/tight` 역할 분담은 representative case와 top-1 aggregate를 넘어 top-2 aggregate에서도 유지된다.

## 부록 T. Threshold Shortlist Sensitivity Aggregate (46-source, top-3)

경로:
- `/Users/seoki/Desktop/research/research_logs/2026-03-13_threshold_shortlist_sensitivity_46day_top3.md`
- `/Users/seoki/Desktop/research/outputs/threshold_shortlist_sensitivity_46day_top3_full_2026-03-13/threshold_shortlist_sensitivity_46day_top3_full_summary.md`

실행 명령:
- `PYTHONPATH=src python -m ais_risk.threshold_shortlist_sensitivity_cli --summary-json outputs/scenario_shift_multi_2026-03-10/scenario_shift_multi_summary.json --summary-json-glob 'outputs/scenario_shift_multi_2023-*_2026-03-*/scenario_shift_multi_2023-*_summary.json' --output-prefix outputs/threshold_shortlist_sensitivity_46day_top3_full_2026-03-13/threshold_shortlist_sensitivity_46day_top3_full --profile s0p30_w0p65:0.30:0.65 --profile s0p30_w0p55:0.30:0.55 --profile s0p35_w0p65:0.35:0.65 --default-profile s0p30_w0p65 --scenario-name current --max-cases-per-run 3`

핵심:
- [확정] 전체 `414 case`에서 `s0p30_w0p55`는 default 대비 warning area를 평균 `+0.0535 nm2` 확대했고, warning increase ratio는 `0.5773`이었다.
- [확정] 전체 `414 case`에서 `s0p35_w0p65`는 default 대비 caution area를 평균 `-0.3840 nm2` 축소했고, caution decrease ratio는 `0.9589`였다.
- [확정] Houston/NOLA/Seattle 모든 지역에서 `sector change ratio=0.0`으로, shortlist 차이는 top-3에서도 여전히 contour 면적 조정에 가깝다.
- [확정] 따라서 `default/sensitive/tight` 역할 분담은 representative case, top-1 aggregate, top-2 aggregate를 넘어 top-3 aggregate에서도 유지된다.

## 부록 U. 51일 Cross-month Pilot(08-01~09-15 + 10-01~10-05)

경로:
- `/Users/seoki/Desktop/research/research_logs/2026-03-13_noaa_2023-10-01_2023-10-05_cross_month_51day_pilot.md`
- `/Users/seoki/Desktop/research/outputs/scenario_threshold_stability_cross_date_51day_2026-03-13_fix/scenario_threshold_stability_cross_date_51day_summary.md`

핵심:
- [확정] 51일 파일럿에서도 `stability_status=unstable`, `recommendation_majority_ratio=0.1569`, `mean_topk_jaccard=0.1385`, `mean_recommended_bootstrap_top1_frequency=0.1106`으로 threshold 수렴 신호는 없다.
- [확정] 상위 profile은 `s0p30_w0p55(8)`, `s0p30_w0p65(7)`, `s0p35_w0p65(6)`으로, shortlist 축 자체는 유지된다.
- [확정] 10월 초 5일을 붙이자 recommendation count에서는 `s0p30_w0p55`가 약간 앞서기 시작했지만, 여전히 shortlist 운영이 더 타당하다.

## 부록 V. 51일 Model Reinforcement Pilot

경로:
- `/Users/seoki/Desktop/research/research_logs/2026-03-13_noaa_multidate_0801_0915_1001_1005_model_reinforcement.md`
- `/Users/seoki/Desktop/research/outputs/noaa_multidate_0801_0915_1001_1005_2026-03-13/noaa_multidate_benchmark_summary.md`
- `/Users/seoki/Desktop/research/outputs/noaa_multidate_0801_0915_1001_1005_2026-03-13/noaa_multidate_calibration_eval_summary.md`
- `/Users/seoki/Desktop/research/outputs/noaa_multidate_0801_0915_1001_1005_2026-03-13/noaa_multidate_own_ship_loo_summary.md`
- `/Users/seoki/Desktop/research/outputs/noaa_multidate_0801_0915_1001_1005_2026-03-13/noaa_multidate_summary.md`

핵심:
- [확정] 통합 데이터는 `56,213 rows`, own_mmsi `15`, positive_rate `0.2917`이다.
- [확정] `hgbt`는 benchmark F1 `0.9489`, ECE `0.0235`, LOO F1 mean `0.9213`, case F1 mean `0.8973`으로 계속 가장 균형이 좋다.
- [확정] `logreg`는 benchmark F1 `0.8776`, LOO F1 mean `0.8870`, case F1 mean `0.8897`로 explainable comparator로 계속 강하다.

## 부록 W. Governed Model/Threshold Selection (51-day pilot)

경로:
- `/Users/seoki/Desktop/research/research_logs/2026-03-13_governed_model_threshold_selection_51day.md`
- `/Users/seoki/Desktop/research/outputs/governed_model_threshold_selection_51day_2026-03-13/governed_model_threshold_selection_51day_summary.md`

핵심:
- [확정] primary model은 계속 `hgbt`, comparator는 `logreg`다.
- [확정] 51일 파일럿에서는 threshold 상위권이 `s0p30_w0p55`, `s0p30_w0p65`, `s0p35_w0p65`이고, `default_profile`은 `s0p30_w0p55` 쪽으로 이동했다.
- [리스크] `default`와 `sensitive`가 같은 profile로 수렴해, threshold default는 아직 고정 규칙으로 말하기 어렵다.

## 부록 X. 발표 슬라이드 구성안 메모

경로:
- `/Users/seoki/Desktop/research/outputs/presentation_deck_outline_61day_2026-03-13/presentation_deck_outline_61day.md`

핵심:
- [확정] 61일 결과 기준으로 8장 발표 슬라이드 구조와 스피커 노트를 작성했다.
- [확정] Slide 5는 `hgbt primary + logreg comparator`, Slide 6은 `default / balanced / tight` shortlist role, Slide 7은 Houston/NOLA/Seattle holdout compare figure를 사용하는 구조다.
- [확정] 예상 질문과 권장 답변까지 포함해 심사/면접 대응용으로 바로 재사용할 수 있다.
- [확정] 발표 초반에 non-goal을 명시해 `완전자율운항`, `법적 안전 경계`, `single best threshold` 오해를 먼저 차단하도록 설계했다.

## 부록 Y. 발표 Q&A 카드 메모

경로:
- `/Users/seoki/Desktop/research/outputs/presentation_deck_outline_61day_2026-03-13/presentation_qa_cards_61day.md`

핵심:
- [확정] 발표 질의응답에서 반복 사용할 핵심 답변 축을 `AIS-only`, `decision support`, `hgbt primary`, `threshold shortlist`, `non-goal 명시`로 정리했다.
- [확정] threshold instability, 딥러닝 비채택, contour 의미, generalization 범위 등 주요 질문 20개에 대한 권장 답변을 수록했다.
- [확정] 답변 순서는 `범위 제한 -> 검증 구조 -> 기여` 순서로 말하는 것이 가장 안정적이다.

## 부록 Z. 슬라이드 본문 문안 및 분리 Q&A 메모

경로:
- `/Users/seoki/Desktop/research/outputs/presentation_deck_outline_61day_2026-03-13/presentation_slide_copy_61day.md`
- `/Users/seoki/Desktop/research/outputs/presentation_deck_outline_61day_2026-03-13/presentation_qa_cards_61day_split.md`

핵심:
- [확정] `presentation_slide_copy_61day.md`는 8장 발표 슬라이드에 바로 붙일 수 있는 압축 본문 문안이다.
- [확정] `presentation_qa_cards_61day_split.md`는 교수 심사용과 실무자용 질의응답을 분리해 리허설에 바로 사용할 수 있게 정리했다.
- [확정] 발표 자료와 Q&A 모두 `AIS-only decision support`, `hgbt primary`, `default/balanced/tight shortlist`, `non-goal 명시` 축을 유지한다.

## 부록 AA. PPT 텍스트 완성본 및 발표 대본 메모

경로:
- `/Users/seoki/Desktop/research/outputs/presentation_deck_outline_61day_2026-03-13/presentation_ppt_text_61day.md`
- `/Users/seoki/Desktop/research/outputs/presentation_deck_outline_61day_2026-03-13/presentation_scripts_61day.md`

핵심:
- [확정] `presentation_ppt_text_61day.md`는 실제 PPT 제작용으로 슬라이드별 제목, 부제, 본문, takeaway, 발표자 노트를 한 번에 정리한 문서다.
- [확정] `presentation_scripts_61day.md`는 1분, 3분, 10분 버전 발표 대본을 제공해 상황에 맞는 리허설을 가능하게 한다.
- [확정] 두 문서 모두 `AIS-only decision support`, `hgbt primary + logreg comparator`, `default/balanced/tight shortlist`, `non-goal 명시` 축을 유지한다.

## 부록 AB. 레이아웃 가이드 및 초단축 피치 메모

경로:
- `/Users/seoki/Desktop/research/outputs/presentation_deck_outline_61day_2026-03-13/presentation_layout_guide_61day.md`
- `/Users/seoki/Desktop/research/outputs/presentation_deck_outline_61day_2026-03-13/presentation_micro_pitch_61day.md`

핵심:
- [확정] `presentation_layout_guide_61day.md`는 Slide 5/6/7 중심 시각 우선순위, 색상 규칙, figure 배치 원칙을 제공하는 실제 제작 가이드다.
- [확정] `presentation_micro_pitch_61day.md`는 20초, 30초, 45초, 60초 버전 초단축 피치와 면접형 1문장 답변 세트를 제공한다.
- [확정] 두 문서 모두 `AIS-only decision support`, `hgbt primary`, `threshold shortlist`, `non-goal 명시` 축을 유지한다.

## 부록 AC. 썸네일 스케치 및 영문 quick pack 메모

경로:
- `/Users/seoki/Desktop/research/outputs/presentation_deck_outline_61day_2026-03-13/presentation_thumbnail_sketch_61day.md`
- `/Users/seoki/Desktop/research/outputs/presentation_deck_outline_61day_2026-03-13/presentation_english_quick_pack_61day.md`

핵심:
- [확정] `presentation_thumbnail_sketch_61day.md`는 8장 발표 자료의 텍스트 기반 와이어프레임으로, 실제 슬라이드 제작 전 배치 결정을 빠르게 끝내기 위한 문서다.
- [확정] `presentation_english_quick_pack_61day.md`는 영문 one-line summary, short pitch, claims, non-claims, Q&A를 묶은 빠른 대응 문서다.
- [확정] 두 문서 모두 기존 발표 메시지 축인 `AIS-only decision support`, `hgbt primary`, `threshold shortlist`, `non-goal 명시`를 유지한다.

## 부록 AD. Mock Storyboard 및 영문 full pack 메모

경로:
- `/Users/seoki/Desktop/research/outputs/presentation_deck_outline_61day_2026-03-13/presentation_mock_storyboard_61day.md`
- `/Users/seoki/Desktop/research/outputs/presentation_deck_outline_61day_2026-03-13/presentation_english_slide_copy_61day.md`
- `/Users/seoki/Desktop/research/outputs/presentation_deck_outline_61day_2026-03-13/presentation_english_10min_script_61day.md`

핵심:
- [확정] `presentation_mock_storyboard_61day.md`는 거의 완성 슬라이드 수준에 가까운 장면 설명과 포인터 동선까지 포함한 storyboard 문서다.
- [확정] `presentation_english_slide_copy_61day.md`는 영어 슬라이드 제작용 문안이고, `presentation_english_10min_script_61day.md`는 영어 연구 발표용 대본이다.
- [확정] 세 문서 모두 기존 발표 메시지 축인 `AIS-only decision support`, `hgbt primary`, `threshold shortlist`, `non-goal 명시`를 유지한다.

## 부록 AE. 영문 5분 대본, 초록, 포스터 텍스트 메모

경로:
- `/Users/seoki/Desktop/research/outputs/presentation_deck_outline_61day_2026-03-13/presentation_english_5min_script_61day.md`
- `/Users/seoki/Desktop/research/outputs/presentation_deck_outline_61day_2026-03-13/research_abstract_61day_ko_en.md`
- `/Users/seoki/Desktop/research/outputs/presentation_deck_outline_61day_2026-03-13/poster_text_61day_ko_en.md`

핵심:
- [확정] `presentation_english_5min_script_61day.md`는 짧은 영어 발표용 대본이다.
- [확정] `research_abstract_61day_ko_en.md`는 국문/영문 논문 초록 초안이다.
- [확정] `poster_text_61day_ko_en.md`는 포스터 레이아웃에 바로 넣을 수 있는 국문/영문 포스터 문안이다.
- [확정] 세 문서 모두 기존 메시지 축인 `AIS-only decision support`, `hgbt primary`, `threshold shortlist`, `non-goal 명시`를 유지한다.

## 부록 AF. 축약 초록, 포스터 헤드라인, 영문 Q&A, 포스터 레이아웃 메모

경로:
- `/Users/seoki/Desktop/research/outputs/presentation_deck_outline_61day_2026-03-13/research_abstract_short_versions_61day_ko_en.md`
- `/Users/seoki/Desktop/research/outputs/presentation_deck_outline_61day_2026-03-13/poster_headline_qr_pack_61day_ko_en.md`
- `/Users/seoki/Desktop/research/outputs/presentation_deck_outline_61day_2026-03-13/presentation_english_qa_cards_61day.md`
- `/Users/seoki/Desktop/research/outputs/presentation_deck_outline_61day_2026-03-13/poster_layout_guide_61day.md`

핵심:
- [확정] `research_abstract_short_versions_61day_ko_en.md`는 영문 150/250-word와 국문 축약 소개문을 포함한 분량 제한형 초록 문서다.
- [확정] `poster_headline_qr_pack_61day_ko_en.md`는 포스터 headline, subheadline, QR summary 후보안을 제공한다.
- [확정] `presentation_english_qa_cards_61day.md`는 영어 면접/발표용 Q&A 카드다.
- [확정] `poster_layout_guide_61day.md`는 A0/A1 기준 포스터 섹션 배치와 figure 우선순위 가이드다.

## 부록 AG. 100-word 초록, 포스터 Header Mock, QR Landing Summary 메모

경로:
- `/Users/seoki/Desktop/research/outputs/presentation_deck_outline_61day_2026-03-13/research_abstract_100word_61day_ko_en.md`
- `/Users/seoki/Desktop/research/outputs/presentation_deck_outline_61day_2026-03-13/poster_header_mock_61day.md`
- `/Users/seoki/Desktop/research/outputs/presentation_deck_outline_61day_2026-03-13/qr_landing_summary_61day_ko_en.md`

핵심:
- [확정] `research_abstract_100word_61day_ko_en.md`는 매우 짧은 제출/소개문용 초록이다.
- [확정] `poster_header_mock_61day.md`는 포스터 상단 title/subtitle/tag/author 구조를 mock 형태로 제안한다.
- [확정] `qr_landing_summary_61day_ko_en.md`는 QR landing page hero text, short summary, CTA를 국문/영문으로 정리한 문서다.

## 부록 AH. 최종 발표 Run Sheet 및 포트폴리오 Copy 메모

경로:
- `/Users/seoki/Desktop/research/outputs/presentation_deck_outline_61day_2026-03-13/final_presentation_run_sheet_61day.md`
- `/Users/seoki/Desktop/research/outputs/presentation_deck_outline_61day_2026-03-13/portfolio_readme_copy_61day_ko_en.md`

핵심:
- [확정] `final_presentation_run_sheet_61day.md`는 발표 직전 파일 오픈 순서, 시간 배분, figure 보조 경로, Q&A 전환 문장을 포함한 운영 문서다.
- [확정] `portfolio_readme_copy_61day_ko_en.md`는 GitHub README나 portfolio landing page에 바로 사용할 수 있는 국문/영문 소개문과 CTA를 제공한다.

## 부록 AI. Root README 반영 메모

경로:
- `/Users/seoki/Desktop/research/README.md`

핵심:
- [확정] 루트 README 상단에 프로젝트 개요, 61일 검증 스냅샷, 문서 패키지 진입점, non-goal 섹션을 추가했다.
- [확정] 저장소 진입 시 코드 스켈레톤뿐 아니라 연구/발표 패키지로도 바로 이동할 수 있다.

## 부록 AJ. 패키지 인덱스 및 최종 편집 체크리스트 메모

경로:
- `/Users/seoki/Desktop/research/outputs/presentation_deck_outline_61day_2026-03-13/package_index_61day.md`
- `/Users/seoki/Desktop/research/outputs/presentation_deck_outline_61day_2026-03-13/final_asset_edit_checklist_61day.md`

핵심:
- [확정] `package_index_61day.md`는 발표/면접/영문 발표/포스터/초록/README 용도별 문서 진입점이다.
- [확정] `final_asset_edit_checklist_61day.md`는 PPT, 포스터, README, landing page 반영 직전 최종 점검 문서다.

## 부록 AK. README Full Draft 및 Final Text Bundle 메모

경로:
- `/Users/seoki/Desktop/research/outputs/presentation_deck_outline_61day_2026-03-13/readme_full_draft_61day.md`
- `/Users/seoki/Desktop/research/outputs/presentation_deck_outline_61day_2026-03-13/final_edit_text_bundle_61day.md`

핵심:
- [확정] `readme_full_draft_61day.md`는 루트 README를 더 크게 재구성할 때 참고할 수 있는 전체 draft다.
- [확정] `final_edit_text_bundle_61day.md`는 PPT, 포스터, README, landing page에 반복 삽입할 핵심 문장을 모아둔 문서다.

## 부록 AL. Poster Final Assembly Bundle 메모

경로:
- `/Users/seoki/Desktop/research/outputs/presentation_deck_outline_61day_2026-03-13/poster_final_assembly_bundle_61day.md`

핵심:
- [확정] `poster_final_assembly_bundle_61day.md`는 포스터 최종 편집용 assembled copy로, header, section text, figure caption, limitation box, QR box를 한 번에 제공한다.

## 부록 AM. Tagline / Poster Short Pack 메모

경로:
- `/Users/seoki/Desktop/research/outputs/presentation_deck_outline_61day_2026-03-13/github_tagline_badge_pack_61day.md`
- `/Users/seoki/Desktop/research/outputs/presentation_deck_outline_61day_2026-03-13/poster_a0_a1_short_pack_61day.md`
- `/Users/seoki/Desktop/research/README.md`

핵심:
- [확정] `github_tagline_badge_pack_61day.md`는 GitHub/포트폴리오용 짧은 tagline과 badge 문구 후보안이다.
- [확정] `poster_a0_a1_short_pack_61day.md`는 A0/A1 포스터용으로 더 짧게 줄인 문구 팩이다.
- [확정] 루트 README 제목 아래에 영문 tagline 한 줄을 추가했다.

## 부록 AN. README 실사용 재구성 / Project Handoff Summary 메모

경로:
- `/Users/seoki/Desktop/research/README.md`
- `/Users/seoki/Desktop/research/outputs/presentation_deck_outline_61day_2026-03-13/project_handoff_summary_61day.md`
- `/Users/seoki/Desktop/research/outputs/presentation_deck_outline_61day_2026-03-13/package_index_61day.md`

핵심:
- [확정] 루트 README 상단에 `지금 바로 볼 것`, `현재 핵심 결론`, `인수인계/현황 파악 추천 순서`를 추가해 저장소 첫 진입 경험을 정리했다.
- [확정] `project_handoff_summary_61day.md`는 현재 완료 범위, 고정 메시지, 남은 실제 제작 작업을 한 문서에서 보여주는 인수인계 요약이다.
- [확정] 추천 사용 순서는 `project_handoff_summary -> package_index -> final_asset_edit_checklist`다.

## 부록 AO. Representative Outputs Manifest 메모

경로:
- `/Users/seoki/Desktop/research/outputs/presentation_deck_outline_61day_2026-03-13/representative_outputs_manifest_61day.md`
- `/Users/seoki/Desktop/research/README.md`

핵심:
- [확정] `representative_outputs_manifest_61day.md`는 대표 figure 3개와 핵심 문서를 한 번에 보여주는 shortlist 문서다.
- [확정] 루트 README에는 `핵심 산출물` 섹션을 추가해 대표 결과물 경로를 직접 연결했다.
- [확정] 외부 검토자에게는 `representative_outputs_manifest -> validation summary` 순서로 보여주는 편이 가장 빠르다.

## 부록 AP. Message Lock Sheet / README 사용 가이드 메모

경로:
- `/Users/seoki/Desktop/research/outputs/presentation_deck_outline_61day_2026-03-13/message_lock_sheet_61day.md`
- `/Users/seoki/Desktop/research/README.md`

핵심:
- [확정] `message_lock_sheet_61day.md`는 발표/README/포스터/면접에서 반드시 유지할 표현과 피해야 할 표현을 고정한 문서다.
- [확정] 루트 README에는 `이 저장소를 보는 방법` 섹션을 추가해 독자별 진입 경로를 더 명확히 했다.
- [확정] 최종 편집 전에는 `message_lock_sheet -> final_asset_edit_checklist` 순서로 보는 것이 가장 안전하다.

## 부록 AQ. Reviewer Rebuttal Short Pack 메모

경로:
- `/Users/seoki/Desktop/research/outputs/presentation_deck_outline_61day_2026-03-13/reviewer_rebuttal_short_pack_61day_ko_en.md`
- `/Users/seoki/Desktop/research/README.md`

핵심:
- [확정] `reviewer_rebuttal_short_pack_61day_ko_en.md`는 novelty, threshold instability, AIS-only limitation, baseline 약세에 대한 짧은 방어 문장을 제공한다.
- [확정] 루트 README에는 reviewer 대응 경로를 추가해 교수 심사/논문 초안 response 진입점을 보강했다.
- [확정] 최종 reviewer 대응 전에는 `message_lock_sheet -> reviewer_rebuttal_short_pack -> validation_summary` 순서가 가장 안전하다.

## 부록 AR. Reviewer Rebuttal Section Pack 메모

경로:
- `/Users/seoki/Desktop/research/outputs/presentation_deck_outline_61day_2026-03-13/reviewer_rebuttal_section_pack_61day_ko_en.md`
- `/Users/seoki/Desktop/research/README.md`

핵심:
- [확정] `reviewer_rebuttal_section_pack_61day_ko_en.md`는 methods/results/limitations 기준으로 reviewer response를 구조화한 문서다.
- [확정] 루트 README에는 reviewer 대응 경로에 section pack까지 추가해 더 긴 response 작성 동선을 보강했다.
- [확정] 최종 reviewer 대응 전에는 `message_lock_sheet -> reviewer_rebuttal_short_pack -> reviewer_rebuttal_section_pack -> validation_summary` 순서가 가장 안전하다.

## 부록 AS. Reviewer Tone Split Pack 메모

경로:
- `/Users/seoki/Desktop/research/outputs/presentation_deck_outline_61day_2026-03-13/reviewer_rebuttal_conference_tone_61day_ko_en.md`
- `/Users/seoki/Desktop/research/outputs/presentation_deck_outline_61day_2026-03-13/reviewer_rebuttal_journal_tone_61day_ko_en.md`
- `/Users/seoki/Desktop/research/README.md`

핵심:
- [확정] `reviewer_rebuttal_conference_tone_61day_ko_en.md`는 더 짧고 직접적인 conference-style response 문서다.
- [확정] `reviewer_rebuttal_journal_tone_61day_ko_en.md`는 더 정중하고 설명적인 journal-style response 문서다.
- [확정] 최종 reviewer 대응 전에는 `message_lock_sheet -> short_pack -> section_pack -> conference/journal tone pack -> validation_summary` 순서가 가장 안전하다.

## 부록 AT. Reviewer Comment Template / Cover Letter Tone Pack 메모

경로:
- `/Users/seoki/Desktop/research/outputs/presentation_deck_outline_61day_2026-03-13/reviewer_comment_template_pack_61day_ko_en.md`
- `/Users/seoki/Desktop/research/outputs/presentation_deck_outline_61day_2026-03-13/cover_letter_tone_pack_61day_ko_en.md`
- `/Users/seoki/Desktop/research/README.md`

핵심:
- [확정] `reviewer_comment_template_pack_61day_ko_en.md`는 실제 reviewer comment 유형별 response 초안 템플릿이다.
- [확정] `cover_letter_tone_pack_61day_ko_en.md`는 제출 메일과 cover letter 첫 문단에 바로 쓸 수 있는 문안 모음이다.
- [확정] 최종 제출 전에는 `message_lock_sheet -> cover_letter_tone_pack` 순서로 보는 것이 가장 안전하다.

## 부록 AU. Figure/Table/Stats Template / Target Venue Cover Letter 메모

경로:
- `/Users/seoki/Desktop/research/outputs/presentation_deck_outline_61day_2026-03-13/reviewer_figure_table_stats_template_pack_61day_ko_en.md`
- `/Users/seoki/Desktop/research/outputs/presentation_deck_outline_61day_2026-03-13/cover_letter_target_venue_variants_61day_ko_en.md`
- `/Users/seoki/Desktop/research/README.md`

핵심:
- [확정] `reviewer_figure_table_stats_template_pack_61day_ko_en.md`는 figure/table/statistical significance 코멘트에 특화된 response 템플릿 문서다.
- [확정] `cover_letter_target_venue_variants_61day_ko_en.md`는 workshop/demo, conference, journal, internal review 유형별 cover letter 변형안을 제공한다.
- [확정] 최종 제출 전에는 `message_lock_sheet -> cover_letter_target_venue_variants -> cover_letter_tone_pack` 순서가 가장 안전하다.

## 부록 AV. Reinforcement Learning Positioning 메모

경로:
- `/Users/seoki/Desktop/research/outputs/presentation_deck_outline_61day_2026-03-13/reinforcement_learning_positioning_note_61day_ko_en.md`
- `/Users/seoki/Desktop/research/outputs/presentation_deck_outline_61day_2026-03-13/reviewer_rebuttal_short_pack_61day_ko_en.md`
- `/Users/seoki/Desktop/research/outputs/presentation_deck_outline_61day_2026-03-13/reviewer_rebuttal_section_pack_61day_ko_en.md`
- `/Users/seoki/Desktop/research/README.md`

핵심:
- [확정] 현재 프로젝트에는 강화학습(RL)을 적용하지 않았다.
- [확정] 그 이유는 `AIS-only`, `simulator 부재`, `reward 정당화 부족`, `안전한 policy evaluation 부재`, `decision support 범위` 때문이다.
- [확정] reviewer 대응 시에는 `message_lock_sheet -> RL positioning note -> short pack -> section pack` 순서로 보는 것이 가장 안전하다.

## 부록 AW. Paper Section Hardening 메모

경로:
- `/Users/seoki/Desktop/research/outputs/presentation_deck_outline_61day_2026-03-13/paper_section_hardening_note_61day_ko_en.md`
- `/Users/seoki/Desktop/research/outputs/presentation_one_page_61day_2026-03-13/presentation_one_page_61day.md`
- `/Users/seoki/Desktop/research/outputs/presentation_deck_outline_61day_2026-03-13/research_abstract_61day_ko_en.md`

핵심:
- [확정] `paper_section_hardening_note_61day_ko_en.md`는 Methods / Limitations / Future Work용 reviewer-safe 문장 은행이다.
- [확정] one-page summary와 abstract에도 RL 미적용 이유와 reviewer-safe scope를 반영했다.
- [확정] 논문 본문 작성 전에는 `message_lock_sheet -> RL positioning note -> paper section hardening note -> abstract` 순서로 보는 것이 가장 안전하다.
