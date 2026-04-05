# 문서명
기준 선박 순환(Rotating Own-Ship) 학습 및 검증 프로토콜

# 문서 목적
특정 자선(own ship) 1척에만 의존하지 않고, 기준 선박(MMSI)을 바꿔가며 시나리오를 생성·학습·검증하는 연구 프로토콜을 고정한다.

# 대상 독자
연구자, 데이터사이언티스트, ML 엔지니어, 논문 작성자

# 작성 버전
v1.1 (2026-03-14)

# 핵심 요약
- [확정] 기준 선박을 바꿔가며 학습·검증하는 것은 가능하며, 현재 코드베이스도 이를 지원한다.
- [확정] 논문적으로는 `single ship only`보다 `rotating own-ship validation`이 훨씬 방어 가능하다.
- [확정] 가장 권장되는 구조는 `global model 학습 + rotating own-ship evaluation + ship-specific case repeat`다.
- [확정] auto-selected own-ship 후보에는 `quality gate`를 걸어 저품질 MMSI를 자동 제외할 수 있다.
- [리스크] 인접 timestamp leakage, 항로 암기, 저품질 own ship 선택을 통제하지 않으면 결과 해석이 약해진다.

## 1. 배경 및 문제 정의

- [확정] 단일 own ship만 기준으로 학습하면, 선박 자체를 학습한 것인지 특정 날짜/항로 패턴을 암기한 것인지 분리하기 어렵다.
- [확정] 반면 기준 선박을 바꿔가며 반복 검증하면 `own-ship-conditioned generalization`을 더 설득력 있게 제시할 수 있다.
- [확정] 현재 프로젝트의 목표는 `policy learning`이 아니라 `own-ship-centric spatial risk representation`이므로, rotating own-ship 설계는 모델 개인화(personalization)보다 검증 강화에 더 가깝다.

## 2. 목표와 비목표

| 구분 | 내용 | 상태 |
|---|---|---|
| 목표 | 기준 선박 순환 학습/검증 구조 고정 | [확정] |
| 목표 | leakage를 줄인 split 규칙 제시 | [확정] |
| 목표 | existing CLI 재사용 실행 경로 제공 | [확정] |
| 비목표 | 특정 선박 1척만으로 일반화 주장 | [확정] |
| 비목표 | RL 기반 항해 정책 학습 | [확정] |

## 3. 핵심 가정과 제약

| 항목 | 내용 | 상태 |
|---|---|---|
| 데이터 | AIS-only | [확정] |
| 기준 선박 식별 | MMSI | [확정] |
| 기본 모델 | `rule_score`, `logreg`, `hgbt`, `torch_mlp` | [확정] |
| 기본 split | `own_ship` + time/date blocking 보강 | [확정] |
| 계산 환경 | Apple Silicon `mps` 가능 | [확정] |

## 4. 상세 설계/요구사항/방법론

### 4.1 권장 설계 원칙

1. [확정] 학습은 가능한 한 여러 own ship를 포함한 `global model`로 수행한다.
2. [확정] 평가 시 기준 선박을 바꿔가며 반복한다.
3. [확정] 특정 선박 전용 분석은 `case study` 또는 `calibration candidate`로만 해석한다.
4. [확정] 인접 timestamp를 train/test에 동시에 넣지 않는다.

### 4.2 가능한 운영 모드

| 모드 | 설명 | 권장도 | 해석 |
|---|---|---|---|
| Mode A | `global train + rotating own-ship eval` | [확정] 높음 | 가장 논문 방어력이 높음 |
| Mode B | `focus MMSI vs baseline multi-own-ship compare` | [확정] 높음 | 특정 선박 민감도 확인에 적합 |
| Mode C | `single ship only train/test` | [리스크] 낮음 | 데모/사례연구용으로만 사용 |

### 4.3 기준 선박 선택 게이트

| 항목 | 기준 | 상태 |
|---|---|---|
| timestamp 수 | 충분한 시점 확보 | [추가 검증 필요] |
| 주변 선박 수 | target encounter가 일정 수준 이상 | [추가 검증 필요] |
| heading/cog coverage | sentinel/결측이 과도하지 않을 것 | [확정] |
| gap 수준 | interpolation 의존이 지나치지 않을 것 | [추가 검증 필요] |
| 날짜 다양성 | 가능한 한 여러 날짜에 등장 | [추가 검증 필요] |

### 4.3.1 자동 quality gate 적용 규칙

| 항목 | 기본값 | 해석 | 상태 |
|---|---:|---|---|
| `min_row_count` | `80` | 전체 행 수가 너무 적은 MMSI 제외 | [확정] |
| `min_observed_row_count` | `40` | 보간 이전 관측치가 너무 적은 MMSI 제외 | [확정] |
| `max_interpolation_ratio` | `0.70` | 재구성 의존이 지나친 MMSI 제외 | [확정] |
| `min_heading_coverage_ratio` | `0.50` | heading 결측이 심한 MMSI 제외 | [확정] |
| `min_movement_ratio` | `0.30` | 정박/무이동 위주 MMSI 제외 | [확정] |
| `min_active_window_ratio` | `0.10` | 유효 시간창이 너무 짧은 MMSI 제외 | [확정] |
| `min_average_nearby_targets` | `0.50` | 주변 선박 상호작용이 거의 없는 MMSI 제외 | [확정] |
| `max_segment_break_count` | `50` | gap segmentation이 과도한 MMSI 제외 | [확정] |
| `min_candidate_score` | `0.20` | workflow 후보 점수가 낮은 MMSI 제외 | [확정] |
| `min_recommended_target_count` | `1` | 대표 interaction target이 없는 MMSI 제외 | [확정] |

권장 해석:
- [확정] quality gate는 후보를 “재정렬”하기보다 “제외”하는 용도로 쓰는 편이 안전하다.
- [확정] formal experiment에서는 `--auto-candidate-quality-gate-apply`를 켜고, 품질이 너무 낮으면 `--auto-candidate-quality-gate-strict`로 실패시키는 편이 논문 방어에 유리하다.
- [확정] auto-selection workflow output dir는 run마다 unique하게 저장해야 하며, 최신 `focus_seed_pipeline_cli`는 기본적으로 `output-prefix` 기준 unique dir를 사용한다.

자동 gate만 먼저 보고 싶다면 아래 CLI를 사용한다.

```bash
PYTHONPATH=src python -m ais_risk.own_ship_quality_gate_cli \
  --input outputs/<dataset_id>_workflow/own_ship_candidates.csv \
  --output-prefix research_logs/$(date +%F)_<dataset_id>_own_ship_quality_gate
```

own-ship split에서 linear baseline이 왜 무너졌는지 빠르게 확인하려면 아래 ablation CLI를 사용한다.

```bash
PYTHONPATH=src python -m ais_risk.logreg_feature_ablation_cli \
  --input outputs/<dataset_id>_pairwise.csv \
  --output-prefix outputs/<dataset_id>_logreg_feature_ablation \
  --split-strategy own_ship
```

gate를 통과한 MMSI만 바로 lightweight compare로 넘기려면 아래 예시 스크립트를 사용한다.

```bash
MANIFEST=data/manifests/<dataset_id>.md \
RAW_INPUT=data/raw/<source>/<dataset_id>/raw.csv \
GATE_ROWS_CSV=research_logs/<date>_<dataset_id>_own_ship_quality_gate_rows.csv \
./examples/noaa_focus_compare_from_quality_gate.sh
```

중간 중단 후 같은 tag로 다시 실행해야 하면 아래처럼 output root를 비우는 옵션을 함께 쓰는 편이 안전하다.

```bash
MANIFEST=data/manifests/<dataset_id>.md \
RAW_INPUT=data/raw/<source>/<dataset_id>/raw.csv \
GATE_ROWS_CSV=research_logs/<date>_<dataset_id>_own_ship_quality_gate_rows.csv \
CLEAN_OUTPUT_ROOT=1 \
./examples/noaa_focus_compare_from_quality_gate.sh
```

해역별 `movement_ratio` sensitivity를 빠르게 보려면 아래 예시 스크립트를 사용한다.

```bash
INPUT=outputs/<date>_<region>_focus_candidates_pilot/own_ship_candidates_top20.csv \
OUTPUT_TAG=$(date +%F)_<dataset_id>_movement_sensitivity \
./examples/noaa_quality_gate_movement_sensitivity.sh
```

### 4.3.2 해역별 relaxed exploratory 설정

| 항목 | 권장 규칙 | 상태 |
|---|---|---|
| formal default | `min_movement_ratio=0.30` 유지 | [확정] |
| exploratory relaxation | 해역별 pass rate가 지나치게 낮을 때만 별도 표기 후 제한적으로 적용 | [확정] |
| NOLA pilot | top-20 후보 기준 `0.30 -> 1/20`, `0.25 -> 2/20`, `0.20 -> 4/20` | [확정] |
| reviewer-safe exploratory setting | NOLA에서는 `0.25` | [확정] |
| 비권장 | exploratory threshold를 곧바로 formal default로 승격 | [리스크] |

실증 근거:
- [확정] NOLA `0.25` 통과 MMSI 2척(`367010480`, `368301040`)으로 direct pairwise exploratory subset을 만들었고, `6,676 rows`, `hgbt benchmark F1 0.9459`, `hgbt case F1 mean 0.9125`를 확인했다.
- [확정] 따라서 relaxed threshold는 “학습 가능 subset 탐색”에는 유효하지만, formal gate 기본값을 바꾸는 근거로 해석하면 과장이다.
- [확정] 관련 로그:
  - `/Users/seoki/Desktop/research/research_logs/2026-03-14_noaa_nola_movement_ratio_sensitivity.md`
  - `/Users/seoki/Desktop/research/research_logs/2026-03-14_noaa_nola_mr025_exploratory_pairwise.md`

### 4.4 권장 split 구조

| split | 목적 | 상태 |
|---|---|---|
| own-ship split | 특정 own ship leakage 방지 | [확정] |
| date block split | 인접 시점 leakage 방지 | [확정] |
| case repeat | ship-specific 반복 안정성 확인 | [확정] |
| seed repeat | 학습 난수 민감도 확인 | [확정] |

실증 메모:
- [확정] direct exploratory pilot에서 Houston/Seattle은 `timestamp split`보다 `own_ship split` 성능이 낮았고, 특히 Houston은 cross-own-ship generalization gap이 크게 나타났다.
- [확정] 따라서 rotating own-ship 실험에서는 timestamp 기준 성능만 보고하지 말고, own-ship split 또는 case-repeat 결과를 함께 보고해야 한다.
- [확정] Houston에서는 train split에 `tug positive`가 0건이었지만 test positive 대부분이 `tug`여서, linear baseline(`logreg`)이 특히 크게 무너졌다.
- [확정] Seattle에서는 train split에 `passenger`와 `tug` positive가 모두 있었고, vessel-type 제거 ablation 효과도 거의 없어서 Houston과 다른 failure mode를 보였다.
- [확정] Houston 다른 날짜(`2023-08-09`) supplementary check에서도 같은 방향의 support mismatch가 재현됐지만, default gate pass가 낮아 formal 재현과 supplementary 재현을 구분해야 했다.
- [확정] Houston recurrence는 날짜별 강도가 달랐고, `always strong`보다는 `date-varying but recurrent`로 설명하는 편이 더 안전하다.
- [확정] Seattle은 날짜별 ablation 효과가 mixed-sign으로 나타나 Houston형 recurrent mismatch와는 다른 양상을 보였다.
- [확정] NOLA는 날짜별 ablation 효과가 대부분 negative/neutral이었고, `2023-08-12`에만 tug recall 회복과 passenger recall 하락이 함께 나타나는 trade-off 기반 positive가 관찰됐다.
- [확정] 따라서 3해역 failure mode는 `Houston = date-varying but recurrent`, `Seattle = mixed-sign and non-recurrent`, `NOLA = mostly negative/neutral with isolated positive trade-off`로 구분해 설명하는 편이 reviewer-safe하다.

### 4.5 권장 실험 프로토콜

#### 단계 1. 후보 own ship 선정

- [확정] `own_ship_candidates` 또는 기존 workflow ranking으로 후보 MMSI를 추린다.
- [확정] 후보는 1척이 아니라 최소 3척 이상 둔다.

#### 단계 2. focus MMSI 비교

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
  --torch-device mps \
  --random-seed 42
```

#### 단계 3. seed robustness

```bash
PYTHONPATH=src python -m ais_risk.focus_seed_pipeline_cli \
  --manifest data/manifests/<dataset_id>.md \
  --raw-input data/raw/<source>/<dataset_id>/raw.csv \
  --output-prefix research_logs/$(date +%F)_<dataset_id>_focus_seed_pipeline \
  --output-root outputs/<dataset_id>_focus_seed_pipeline_runs \
  --auto-select-focus-mmsis \
  --auto-candidate-quality-gate-apply \
  --auto-candidate-quality-gate-strict \
  --seed-values 42,43,44 \
  --benchmark-modelsets "rule_score,logreg,hgbt;rule_score,logreg,hgbt,torch_mlp" \
  --pairwise-split-strategy own_ship \
  --run-calibration-eval \
  --run-own-ship-loo \
  --run-own-ship-case-eval \
  --own-ship-case-eval-repeat-count 5 \
  --validation-gate-min-seed-count 3 \
  --validation-gate-max-delta-case-f1-std 0.05 \
  --torch-device mps
```

### 4.6 연구 해석 규칙

| 상황 | 해석 | 상태 |
|---|---|---|
| 여러 MMSI에서 동일 모델 우세 | model robustness 근거 | [확정] |
| 특정 MMSI에서만 개선 | ship-specific calibration candidate | [확정] |
| seed마다 결론이 바뀜 | 불안정, 채택 보류 | [확정] |
| single ship only 결과만 좋음 | 사례연구로 제한 | [확정] |

### 4.7 논문용 권장 문장

국문:
- `본 연구는 단일 자선에 국한된 성능 평가를 피하기 위해 기준 선박(MMSI)을 바꿔가며 focus-vs-baseline 비교와 seed robustness 검증을 수행하였다.`
- `따라서 결과는 특정 선박의 항로 패턴에만 맞춘 모델이 아니라, own-ship-conditioned setting에서의 상대적 안정성으로 해석한다.`
- `또한 auto-selected own-ship 후보에는 quality gate를 적용하여 과도한 보간 의존, 낮은 상호작용성, 높은 결측률을 보이는 MMSI를 자동 제외하였다.`

영문:
- `To avoid overinterpreting single-ship performance, the study rotates the own-ship MMSI across focus-vs-baseline comparisons and seed-robustness checks.`
- `The result is therefore interpreted as relative stability under own-ship-conditioned evaluation rather than as a ship-specific policy model.`
- `In addition, an own-ship quality gate filters out auto-selected MMSIs with excessive interpolation dependence, weak interaction density, or insufficient motion coverage.`

## 5. 성공 기준 또는 평가 기준

| 항목 | 기준 | 상태 |
|---|---|---|
| MMSI 다양성 | 최소 3개 이상 focus MMSI 비교 | [확정] |
| 안정성 | seed 3개 이상에서 판단 가능 | [확정] |
| leakage 방지 | own_ship/date 기준 split 유지 | [확정] |
| 해석 가능성 | ship-specific overfit와 global robustness를 구분 가능 | [확정] |

## 6. 리스크와 한계

| 항목 | 설명 | 대응 |
|---|---|---|
| 저품질 MMSI | gap/결측이 많은 own ship 선택 가능 | quality gate 적용 |
| 항로 암기 | 같은 항로/같은 날짜만 반복 학습될 수 있음 | date block split 추가 |
| 해역 편향 | rotating ship가 같은 해역 내부에만 존재 | cross-region 확장 병행 |

## 7. 핵심 결정사항

1. [확정] `single ship only train/test`는 기본 연구 프로토콜로 채택하지 않는다.
2. [확정] rotating own-ship validation을 기본선으로 둔다.
3. [확정] ship-specific 성능은 일반화 주장보다 보조 해석으로 둔다.

## 8. 오픈 이슈

1. [확정] own-ship quality gate CLI와 pipeline integration은 구현 완료.
2. [추가 검증 필요] vessel class 단위 calibration까지 확장할 것인지 여부.

## 9. 다음 액션

1. [확정] 관심 해역에서 focus own-ship MMSI 3개를 먼저 고른다.
2. [확정] `focus_mmsi_compare_cli`와 `focus_seed_pipeline_cli`를 순서대로 실행한다.
3. [확정] auto-selection을 쓸 때는 `--auto-candidate-quality-gate-apply`를 기본으로 두고, formal run은 `--auto-candidate-quality-gate-strict`까지 함께 사용한다.

설명 팁: “기준 선박을 바꿔가며 본다”는 말은 단순 반복이 아니라, `single ship case study`를 `own-ship-conditioned validation protocol`로 승격시키는 설계라고 설명하면 좋다.
