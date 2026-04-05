# 문서명
데이터 수집 및 모델 강화 계획서(Data Collection and Model Iteration Plan)

# 문서 목적
공개 AIS 실데이터를 수집하고, 규칙 기반 baseline 이후 여러 모델을 비교하면서도 범위를 과대화하지 않도록 데이터 확보 순서, 모델 강화 순서, Apple Silicon 학습 운영 원칙을 정의한다.

# 대상 독자
연구자, 데이터사이언티스트, ML 엔지니어, 지도교수

# 작성 버전
v1.0

# 핵심 요약
- [확정] 다음 단계의 우선순위는 `기능 추가`보다 `실제 공개 AIS 수집 -> 데이터 프로파일링 -> baseline 고정 -> 비교 모델 실험`이다.
- [확정] 규칙 기반 spatial baseline은 유지하고, ML은 `pairwise proxy risk comparator`로 제한해 단계적으로 붙인다.
- [확정] Apple Silicon에서는 우선 `전처리/feature/규칙 기반/대부분의 표 기반 모델은 CPU`, `선택적 PyTorch comparator만 MPS GPU`를 기본 운영 원칙으로 둔다.
- [확정] `own ship 하나를 정해서 반복 비교`는 디버깅과 사례 연구에는 유효하지만, 최종 검증의 전부로 쓰면 안 된다.
- [추가 검증 필요] 실제 대상 해역, 데이터 소스, 라이선스, 데이터량 상한은 수집 직전에 확정해야 한다.

## 1. 배경 및 문제 정의

현재 코드베이스는 샘플 AIS를 기준으로 end-to-end 실행이 가능하다. 그러나 연구와 검증을 실제 단계로 올리려면 다음 세 가지가 추가로 필요하다.

1. 어떤 공개 AIS를 어떤 순서로 모을지에 대한 운영 기준
2. baseline 이후 어떤 모델을 어떤 목적으로 비교할지에 대한 강화 로드맵
3. 실험 결과와 실패를 누락 없이 남길 연구일지 체계

핵심 원칙은 `데이터 우선`, `설명 가능한 baseline 우선`, `ML은 비교안으로 단계적 확대`다.

## 2. 목표와 비목표

### 2.1 목표

| 항목 | 설명 | 상태 |
|---|---|---|
| DGM-01 | 공개 AIS 실데이터를 재현 가능하게 수집/정제 | [확정] |
| DGM-02 | baseline 고정 후 ML comparator를 순차 비교 | [확정] |
| DGM-03 | Apple Silicon 1인 환경에서 반복 실험 가능한 운영 체계 확보 | [확정] |
| DGM-04 | 모든 실행을 연구일지와 산출물 경로로 남김 | [확정] |

### 2.2 비목표

| 항목 | 설명 | 상태 |
|---|---|---|
| 대규모 분산학습 | 멀티 GPU 또는 클러스터 학습을 전제하지 않음 | [확정] |
| 딥러닝 우선주의 | 초기 단계에서 sequence model을 핵심 방법으로 두지 않음 | [확정] |
| 무제한 데이터 적재 | 수집 가능한 모든 AIS를 먼저 쌓지 않음 | [확정] |
| 실선 제어 모델 학습 | 조타/제어 label 학습은 범위 밖 | [확정] |

## 3. 핵심 가정과 제약

| 항목 | 내용 | 상태 |
|---|---|---|
| 데이터 범위 | 공개 AIS only | [확정] |
| 운영 환경 | Apple Silicon 단일 장비 | [합리적 가정] |
| baseline | 규칙 기반 spatial risk map | [확정] |
| ML 학습 단위 | pairwise realized-future-separation label 분류 또는 점수 calibration | [확정] |
| GPU 사용 | PyTorch MPS backend를 optional comparator에만 사용 | [확정] |
| boosting 계열 GPU | Apple GPU 사용을 기본 가정으로 두지 않음 | [추가 검증 필요] |
| 최종 검증 | 단일 own ship 반복만으로 결론 내리지 않음 | [확정] |

## 4. 상세 설계/요구사항/방법론

### 4.1 데이터 수집 우선순위

| 단계 | 데이터 목표 | 이유 | 권장 규모 | 상태 |
|---|---|---|---|---|
| Stage D0 | 샘플 1개 해역, 3~7일 | ingestion pipeline 검증 | 수십 MB~수백 MB | [확정] |
| Stage D1 | 혼잡 해역 1곳, 연속 2~4주 | baseline 고정과 사례 확보 | 1차 핵심 dataset | [합리적 가정] |
| Stage D2 | traffic regime가 다른 해역 1~2곳 추가 | 일반화 검토 | 2~3개 해역 | [합리적 가정] |
| Stage D3 | 동일 해역의 다른 기간 추가 | 시간 일반화와 drift 확인 | 선택적 확장 | [추가 검증 필요] |

권장 해역 유형:

| 유형 | 목적 | 예시 성격 | 상태 |
|---|---|---|---|
| 항만/정박지 접근 | 고밀도, 저속 혼잡 검증 | harbor approach | [합리적 가정] |
| 연안 통항 | crossing/overtaking 다양성 확보 | coastal traffic lane | [합리적 가정] |
| 비교적 개방 수역 | 저위험 대조군 확보 | offshore/coastal outer lane | [합리적 가정] |

### 4.2 데이터 적재 및 동결(Freeze) 정책

| 규칙 | 설명 | 상태 |
|---|---|---|
| raw 보존 | 원본 파일은 수정하지 않고 `data/raw/`에만 저장 | [확정] |
| curated 분리 | 정제 후 결과는 `data/curated/` 또는 workflow output으로 분리 | [확정] |
| dataset manifest | source, 기간, bbox, 필터, row count를 Markdown 또는 JSON으로 기록 | [확정] |
| freeze 단위 | 논문/발표에 쓰는 dataset은 `dataset_id` 기준으로 고정 | [확정] |
| 재실행 기록 | 같은 dataset에 대해 config가 바뀌면 연구일지에 반드시 기록 | [확정] |

권장 dataset ID 규칙:

```text
{source}_{area}_{start}_{end}_{version}
예: publicais_harborA_2026-01-01_2026-01-28_v1
```

### 4.3 데이터 수집 체크리스트

| 체크 항목 | 기준 | 상태 |
|---|---|---|
| 라이선스 확인 | 비상업/연구 사용 가능 여부 확인 | [추가 검증 필요] |
| 시간 범위 확인 | 연속 기간인지, 결손 구간이 큰지 확인 | [확정] |
| spatial extent 확인 | bbox가 실제 목적 해역과 맞는지 확인 | [확정] |
| 선종 분포 확인 | cargo/tanker/tug/passenger 비율 확인 | [합리적 가정] |
| MMSI coverage 확인 | 지속적으로 관측되는 선박이 충분한지 확인 | [확정] |
| gap 분포 확인 | 재구성 가능한 수준의 간격인지 확인 | [확정] |

### 4.4 모델 강화 순서

| 단계 | 모델 | 역할 | 학습/실행 위치 | 유지 여부 |
|---|---|---|---|---|
| M0 | Rule-based spatial map | 주 baseline | CPU | 반드시 유지 |
| M1 | Logistic Regression | interpretable ML comparator | CPU | 우선 도입 |
| M2 | HistGradientBoosting 또는 XGBoost CPU | 비선형 표 기반 comparator | CPU | 2차 도입 |
| M3 | Calibrated classifier | score calibration 보정 | CPU | 선택 |
| M4 | Small MLP (PyTorch) | Apple Silicon MPS 실험용 comparator | MPS GPU | 선택 |

모델 강화 원칙:

| 원칙 | 설명 | 상태 |
|---|---|---|
| baseline first | M0 성능과 failure가 정리되기 전 M1 이상으로 넘어가지 않음 | [확정] |
| simple before complex | Logistic Regression이 먼저다 | [확정] |
| pairwise only | 초기 ML은 pairwise proxy risk를 예측하고 spatial projection은 후단에서 동일하게 적용 | [확정] |
| same input policy | baseline과 ML은 최대한 동일 feature set에서 비교 | [확정] |
| explainability guardrail | 블랙박스 성능 상승보다 해석 가능성을 우선 | [확정] |

### 4.5 권장 feature / model 조합

| 모델 | 입력 feature | 장점 | 리스크 | 권장도 |
|---|---|---|---|---|
| Logistic Regression | distance, DCPA, TCPA, bearing, relative speed, density, encounter | 계수 해석 용이 | 비선형 약함 | 높음 |
| HistGradientBoosting | 위 feature + vessel type + context | 비선형 포착 | calibration 추가 필요 | 높음 |
| XGBoost CPU | 위 feature + engineered interaction | tabular 강함 | dependency 및 reproducibility 관리 필요 | 중간 |
| Small MLP | 정규화된 pairwise feature vector | MPS 활용 가능 | 과적합과 설명성 저하 | 낮음 |

### 4.6 Apple Silicon 학습 운영 원칙

| 항목 | 권장안 | 상태 |
|---|---|---|
| 규칙 기반, 전처리, 평가 | CPU 우선 | [확정] |
| scikit-learn 계열 | CPU 우선 | [확정] |
| PyTorch comparator | `mps` 사용 가능 시 선택 적용 | [확정] |
| 배치 크기 | 작은 tabular 모델은 과도하게 키우지 않음 | [합리적 가정] |
| mixed precision | 초기에는 비활성 권장 | [합리적 가정] |
| 재현성 | random seed, config, dataset_id를 연구일지에 남김 | [확정] |

운영 메모:

- [확정] Apple Silicon GPU는 `PyTorch MPS` 경로가 가장 현실적이다.
- [확정] 현재 프로젝트의 핵심 비교 모델은 tabular 중심이므로 CPU로도 충분히 시작 가능하다.
- [추가 검증 필요] XGBoost/LightGBM의 Apple GPU 경로는 이 프로젝트의 기본 전제로 두지 않는다.

### 4.7 실험 주기(Cadence)

| 주기 | 해야 할 일 | 산출물 |
|---|---|---|
| 매일 | 데이터/모델 실행, failure 기록 | 연구일지 1건 |
| 주 2회 | 대표 사례 점검, threshold 재검토 | screenshot 또는 report 링크 |
| 주 1회 | model comparison 표 갱신 | metric summary |
| milestone 종료 시 | dataset freeze, best config 고정 | manifest + summary |

### 4.8 추천 운영 순서

1. Stage D0 데이터 1세트를 확보한다.
2. `schema probe -> preprocess -> trajectory -> profile -> own-ship candidates`를 돌린다.
3. candidate 중 3~5개 own ship bundle을 선정한다.
4. baseline experiment/ablation을 먼저 고정한다.
5. 그 다음에 Logistic Regression을 같은 split에만 붙인다.
6. 필요할 때만 boosting 또는 MLP를 추가한다.

의사코드:

```python
for dataset in collected_datasets:
    freeze(dataset)
    baseline = run_rule_baseline(dataset)
    log_result(dataset, model="rule_baseline", result=baseline)

    if baseline_is_stable(dataset):
        for model_name in ["logreg", "hgbt", "small_mlp"]:
            result = run_model_comparison(dataset, model_name=model_name)
            log_result(dataset, model=model_name, result=result)
```

## 5. 성공 기준 또는 평가 기준

| 항목 | 기준 | 상태 |
|---|---|---|
| 데이터 준비도 | 최소 1개 혼잡 해역의 2~4주 데이터셋 freeze 완료 | [확정] |
| baseline 안정성 | 동일 dataset에서 반복 실행 결과가 재현됨 | [확정] |
| 모델 비교 가능성 | M0 vs M1 최소 비교표 생성 | [확정] |
| 연구 추적성 | 모든 실험이 연구일지와 output path로 연결됨 | [확정] |
| 운영 현실성 | Apple Silicon 단일 장비에서 overnight 실험 가능 | [합리적 가정] |

## 6. 리스크와 한계

| 항목 | 내용 | 상태 |
|---|---|---|
| 데이터 과다 수집 | 너무 많은 raw 파일을 먼저 모아 정리가 늦어질 수 있음 | [리스크] |
| 모델 과도화 | baseline 정리 전에 complex model로 흐를 수 있음 | [리스크] |
| GPU 집착 | Apple GPU를 쓰려다 본질적 검증이 늦어질 수 있음 | [리스크] |
| label proxy 한계 | pseudo-label 개선이 실제 안전성을 직접 뜻하지 않음 | [리스크] |
| 단일 해역 편향 | 첫 데이터셋에서 얻은 결론이 일반화되지 않을 수 있음 | [리스크] |

## 7. 핵심 결정사항

- [확정] 다음 단계의 1순위는 `실데이터 확보와 baseline 고정`이다.
- [확정] `single own-ship 반복 분석`은 탐색과 사례 연구용으로만 사용한다.
- [확정] ML 1차 비교안은 `Logistic Regression`, 2차 비교안은 `HistGradientBoosting 또는 XGBoost CPU`다.
- [확정] Apple Silicon GPU는 optional PyTorch comparator에서만 활용한다.

## 8. 오픈 이슈

1. [추가 검증 필요] 첫 실데이터 해역을 어느 지역으로 고를지
2. [추가 검증 필요] vessel type 메타데이터 품질이 충분한지
3. [추가 검증 필요] dataset freeze를 몇 주 단위로 끊을지
4. [추가 검증 필요] MLP comparator까지 실제로 필요한지

## 9. 다음 액션

1. `data/raw/`에 첫 실데이터 해역 1세트를 적재한다.
2. `workflow_cli`로 full workflow를 돌려 profile과 own-ship candidates를 만든다.
3. candidate 3~5개를 뽑아 baseline experiment와 ablation을 먼저 고정한다.
4. 연구일지 템플릿을 기준으로 첫 dataset freeze 로그를 남긴다.
5. 그 뒤에만 Logistic Regression comparator를 붙인다.

설명 팁: 교수나 면접관에게는 "우선 실데이터를 freeze하고 baseline을 잠근 뒤, 같은 split 위에서만 모델을 늘린다"라고 설명하면 범위 통제가 잘 된 프로젝트로 보인다.
