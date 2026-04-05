# 문서명
검증 전략 보완서(Validation Strategy Upgrade)

# 문서 목적
`own ship 하나를 지정하고 타선과 반복 비교`하는 방식이 어디까지 유효한지 한계를 분명히 하고, 데이터셋/해역/선종/시간 축을 포함한 보완된 검증 프레임워크를 정의한다.

# 대상 독자
연구자, 데이터사이언티스트, ML 엔지니어, 지도교수, 리뷰어

# 작성 버전
v1.0

# 핵심 요약
- [확정] `single own-ship repeated comparison`은 디버깅과 사례 분석에는 적합하지만, 최종 검증의 전부로는 부족하다.
- [확정] 검증은 `timestamp`, `own-ship segment`, `dataset/area`의 3개 단위로 나눠야 한다.
- [확정] 정량 지표만으로 끝내지 않고 `case review`, `ablation`, `failure analysis`, `cross-case summary`를 함께 남겨야 한다.
- [합리적 가정] 최소 검증 단계는 `1개 해역, 3개 이상 own ship, 각 own ship당 3개 이상 timestamp bundle`이다.
- [추가 검증 필요] 다중 해역 검증은 실제 데이터 확보 후 최종 범위를 확정한다.

## 1. 배경 및 문제 정의

자선(own ship) 하나를 고정한 뒤 주변 타선을 반복 비교하는 방식은 구현 검증과 시각적 사례 설명에는 매우 유용하다. 다만 이 방식만으로는 다음 질문에 답하기 어렵다.

1. 다른 own ship을 잡아도 같은 경향이 유지되는가
2. 다른 시간대와 다른 교통 밀도에서도 통하는가
3. 다른 해역과 선종에서도 baseline이 과대평가되지 않는가

따라서 검증 구조를 `단일 사례 검증`에서 `다층 검증`으로 확장해야 한다.

## 2. 목표와 비목표

### 2.1 목표

| 항목 | 설명 | 상태 |
|---|---|---|
| VAL-01 | single-case validation의 역할과 한계를 명확히 정의 | [확정] |
| VAL-02 | 최소한의 다중 own-ship / 다중 timestamp 검증 구조를 정의 | [확정] |
| VAL-03 | 모델 비교에 공정한 split, metric, review 절차를 정의 | [확정] |
| VAL-04 | 논문/면접에서 방어 가능한 validation narrative를 제공 | [확정] |

### 2.2 비목표

| 항목 | 설명 | 상태 |
|---|---|---|
| 상용 인증 수준 안전성 증명 | 본 프로젝트의 범위 아님 | [확정] |
| 실제 조타 성능 검증 | AIS-only로 직접 검증 불가 | [확정] |
| 충돌 예측 benchmark 1위 달성 | 목적이 아님 | [확정] |

## 3. 핵심 가정과 제약

| 항목 | 내용 | 상태 |
|---|---|---|
| 레이블 | pseudo-label 기반 정량 검증 | [확정] |
| 관측 단위 | own ship-centric snapshot | [확정] |
| 사례 검증 | 리포트/heatmap/contour의 정성 검토 필요 | [확정] |
| cross-area | 데이터 확보 전까지 optional | [합리적 가정] |
| 전문가 검토 | 있으면 보조 근거, 없으면 필수 조건은 아님 | [합리적 가정] |

## 4. 상세 설계/요구사항/방법론

### 4.1 `own ship 하나 기준 반복 비교`의 적합 범위

| 사용 목적 | 적합 여부 | 설명 |
|---|---|---|
| 수식/코드 디버깅 | 적합 | relative motion, DCPA/TCPA, contour 변화 검증에 좋음 |
| 발표용 대표 사례 생성 | 적합 | 설명 가능한 exemplar case를 만들기 좋음 |
| threshold 튜닝 초기 탐색 | 적합 | 과민/과소반응 여부를 빨리 확인 가능 |
| 모델 일반화 검증 | 부적합 | 한 MMSI/한 segment에 과적합될 수 있음 |
| 논문 최종 결론 근거 | 부적합 | 표본 편향이 너무 큼 |

결론:

- [확정] `single own-ship repeated comparison`은 `V0~V1 단계`까지만 핵심 수단이다.
- [확정] 최종 보고에서는 반드시 `multi own-ship`, 가능하면 `multi area`까지 확장해야 한다.

### 4.2 권장 검증 레벨

| 레벨 | 이름 | 최소 단위 | 목적 | 통과 기준 |
|---|---|---|---|---|
| V0 | Smoke Validation | 1 own ship, 1 timestamp | 파이프라인 정상 동작 | output 생성, 값 범위 정상 |
| V1 | Case Validation | 1 own ship, 3~5 timestamps | 시각화/설명 가능성 확인 | contour와 top vessel 설명 가능 |
| V2 | Ship-Level Validation | 3개 이상 own ship | own ship 선택 편향 완화 | aggregate metric 산출 |
| V3 | Area-Level Validation | 1개 해역 전체 case bundle | 동일 해역 내 일반화 | split-based metric 확보 |
| V4 | Cross-Area Validation | 2개 이상 해역 | traffic regime 일반화 검토 | area holdout 비교 가능 |

### 4.3 최소 권장 검증 세트

| 축 | 최소 권장 수 | 이유 | 상태 |
|---|---|---|---|
| own ship 수 | 3개 이상 | 특정 MMSI 편향 완화 | [합리적 가정] |
| own ship당 timestamp | 3개 이상 | 고위험/중위험/저위험 비교 | [합리적 가정] |
| scenario 수 | slowdown/current/speedup | 기본 구조 유지 | [확정] |
| failure case 수 | 3종 이상 | 한계 명시 | [확정] |
| dataset 수 | 1개 이상, 가능하면 2개 이상 | baseline 재현성과 일반화 | [합리적 가정] |

### 4.4 데이터 split 전략

| split | 설명 | 주의점 | 상태 |
|---|---|---|---|
| Time split | 기간 기준 train/val/test | 미래 정보 누수 방지 | [확정] |
| Segment split | 같은 trajectory segment를 다른 split에 섞지 않음 | repeated near-duplicate 방지 | [확정] |
| Own-ship holdout | 일부 MMSI/segment를 통째로 holdout | own ship 편향 완화 | [합리적 가정] |
| Area holdout | 해역 단위 분리 | 데이터가 2개 이상일 때만 가능 | [추가 검증 필요] |

권장 split 예시:

```text
Train:   dataset week 1-2
Val:     dataset week 3
Test:    dataset week 4
Ship-HO: top own ship candidate 일부는 train에 넣지 않음
```

### 4.5 모델 비교 방식

| 비교 ID | 모델 | 비교 목적 | 주의점 |
|---|---|---|---|
| C0 | CPA threshold only | 가장 단순한 기준 | spatial output 없음 |
| C1 | Rule-based spatial baseline | 주 기준선 | threshold tuning 기록 필요 |
| C2 | Logistic Regression + spatial projection | 설명 가능한 ML 비교 | pseudo-label circularity 주의 |
| C3 | Boosting + spatial projection | 비선형 비교군 | calibration 확인 필요 |
| C4 | Small MLP + spatial projection | Apple Silicon MPS 실험군 | 과적합과 재현성 점검 |

### 4.6 평가 지표 체계

| 층위 | 지표 | 목적 |
|---|---|---|
| Pairwise | AUROC, AUPRC, F1, Precision@k | 위험 pair 탐지력 |
| Spatial | CPA-point containment, top-q cell capture | heatmap/contour 타당성 |
| Scenario | warning area delta, dominant sector shift | 속력 변화 민감도 |
| Stability | split 간 variance, rerun consistency | 재현성 |
| Runtime | latency, memory | MVP 가능성 |
| Qualitative | reviewer note, failure tag | 해석 가능성 |

### 4.7 보완된 검증 루프

의사코드:

```python
for dataset in datasets:
    for own_ship in select_own_ship_candidates(dataset, top_n=5):
        timestamps = pick_diverse_timestamps(
            own_ship,
            buckets=["high", "mid", "low"],
            per_bucket=1,
        )
        for ts in timestamps:
            snapshot = build_snapshot(dataset, own_ship, ts)
            for model in ["rule", "logreg", "hgbt", "small_mlp"]:
                result = run_case(snapshot, model=model)
                evaluate_pairwise(result)
                evaluate_spatial(result)
                save_case_report(result)
        summarize_ship_level(dataset, own_ship)
    summarize_dataset_level(dataset)
summarize_cross_dataset()
```

### 4.8 정성 검토 절차

| 단계 | 질문 | 기록 위치 |
|---|---|---|
| Review-1 | heatmap의 고위험 방향이 top vessel과 일치하는가 | 연구일지 |
| Review-2 | contour가 지나치게 넓거나 좁지 않은가 | 연구일지 |
| Review-3 | speedup/slowdown의 변화가 도메인 상식과 충돌하는가 | 연구일지 |
| Review-4 | AIS gap/noisy heading이 결과를 왜곡했는가 | failure note |

### 4.9 failure case 보강 항목

| 유형 | 왜 중요한가 | 기록 방식 |
|---|---|---|
| parallel traffic false alarm | density와 bearing 과대평가 가능 | case report + screenshot |
| post-CPA lingering risk | 이미 지나간 위험이 남을 수 있음 | timestamp sequence 검토 |
| sparse AIS gap | interpolation이 contour를 왜곡 가능 | profile + raw gap note |
| anchorage/static vessel | 정박선이 불필요하게 올라올 수 있음 | vessel type/nav status 점검 |

### 4.10 검증 결과 해석 원칙

| 원칙 | 설명 | 상태 |
|---|---|---|
| 과장 금지 | 좋은 metric이 나와도 `의사결정 지원` 범위만 주장 | [확정] |
| baseline anchor | ML이 좋아 보여도 baseline 대비 추가 가치만 평가 | [확정] |
| case + aggregate 병행 | 사례 그림만 또는 평균 숫자만 단독 사용 금지 | [확정] |
| one-ship bias disclosure | 단일 own ship 중심 결과는 반드시 한계 명시 | [확정] |

## 5. 성공 기준 또는 평가 기준

| 항목 | 기준 | 상태 |
|---|---|---|
| V2 달성 | 3개 이상 own ship 기준 aggregate summary 생성 | [확정] |
| case diversity | 각 own ship에 대해 고/중/저위험 timestamp 확보 | [합리적 가정] |
| failure coverage | 최소 3종 failure case 문서화 | [확정] |
| model fairness | 동일 split에서 baseline과 comparator 비교 | [확정] |
| claim safety | 논문/발표에 one-ship 결과만으로 일반화 주장하지 않음 | [확정] |

## 6. 리스크와 한계

| 항목 | 내용 | 상태 |
|---|---|---|
| pseudo-label circularity | current-state feature와 label 정의가 지나치게 가까워질 위험 | [리스크] |
| area bias | 한 해역 결과의 일반화 한계 | [리스크] |
| own-ship recommendation bias | 추천 후보가 특정 패턴만 선택할 수 있음 | [리스크] |
| qualitative subjectivity | 사람이 보는 해석이 달라질 수 있음 | [리스크] |
| compute budget | 모든 조합을 다 돌리기 어렵다 | [리스크] |

## 7. 핵심 결정사항

- [확정] `one own ship 반복 비교`는 유지하되, 검증 레벨을 V0/V1로 명시한다.
- [확정] 최종 검증 최소 단위는 `multi own-ship same-area`다.
- [확정] 정량 지표와 정성 사례를 모두 제출한다.
- [확정] Apple Silicon 실험에서도 baseline과 comparator는 동일 split 위에서만 비교한다.

## 8. 오픈 이슈

1. [추가 검증 필요] own-ship holdout을 MMSI 기준으로 할지 segment 기준으로 할지
2. [추가 검증 필요] cross-area validation에 쓸 두 번째 해역을 어떤 유형으로 고를지
3. [추가 검증 필요] 전문가 정성 검토를 붙일 수 있는지

## 9. 다음 액션

1. 첫 실데이터 세트에서 own ship 후보 5개를 추린다.
2. 각 후보에서 고/중/저위험 timestamp를 1개씩 뽑는다.
3. baseline experiment/ablation을 먼저 돌린다.
4. 같은 case bundle로 Logistic Regression comparator를 붙인다.
5. 연구일지에 `case-level note`와 `dataset-level summary`를 분리해 남긴다.

설명 팁: 심사자에게는 "단일 own ship 분석은 case study용이고, 최종 평가는 own ship과 timestamp를 묶은 bundle 단위 aggregate로 본다"라고 설명하면 검증 구조가 훨씬 탄탄하게 들린다.
