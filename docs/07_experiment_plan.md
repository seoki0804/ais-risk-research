# 문서명
실험 계획서(Experiment Plan)

# 문서 목적
baseline과 proposed method의 비교 방식, 실험 변수, 평가 지표, ablation 항목, speed scenario 실험, 일반화 검토, failure case 분석, 결과 해석 방법을 정의한다.

# 대상 독자
연구자, 데이터사이언티스트, ML 엔지니어, 지도교수

# 작성 버전
v1.0

# 핵심 요약
- [확정] 실험의 중심은 `baseline rule-based spatial risk map`이 실제로 유의미한지 검증하는 것이다.
- [확정] 비교군은 `단순 CPA threshold`, `rule-based spatial map`, `ML pairwise comparator + spatial projection` 순으로 구성한다.
- [합리적 가정] 정량 평가는 `pairwise proxy classification`, `spatial containment`, `scenario sensitivity`, `runtime`을 함께 본다.
- [확정] failure case 분석과 ablation study를 반드시 포함해 과장된 주장 가능성을 낮춘다.

## 1. 배경 및 문제 정의

본 프로젝트는 실제 충돌 레이블이 부족한 AIS-only 조건에서 수행되므로, 실험 계획이 부실하면 결과가 그럴듯한 시각화에 그칠 위험이 있다. 따라서 본 실험 계획은 `정량 비교`, `정성 사례`, `controlled scenario`, `ablation`, `failure analysis`를 함께 설계해 결과의 신뢰도를 보완한다.

## 2. 목표와 비목표

### 2.1 목표

| 항목 | 설명 | 상태 |
|---|---|---|
| Exp-G1 | rule-based spatial map의 유효성 검증 | [확정] |
| Exp-G2 | speed scenario 효과의 가시성 검증 | [확정] |
| Exp-G3 | ML comparator의 실질적 추가가치 확인 | [확정] |
| Exp-G4 | failure case를 통한 한계 명시 | [확정] |

### 2.2 비목표

| 항목 | 설명 | 상태 |
|---|---|---|
| collision prediction benchmark 경쟁 | 공개 benchmark leaderboard 목적 아님 | [확정] |
| 상용 현장시험 | 실선·시뮬레이터 실험은 제외 | [확정] |

## 3. 핵심 가정과 제약

| 항목 | 내용 | 상태 |
|---|---|---|
| 데이터 | 단일 해역 중심 | [합리적 가정] |
| 레이블 | reconstructed track 기반 pseudo-label 사용 | [확정] |
| 시나리오 | 속력만 조절 | [확정] |
| 지도 평가 | 공간 containment 중심 | [합리적 가정] |
| 전문가 평가 | 가능하면 보조적으로만 포함 | [추가 검증 필요] |

## 4. 상세 설계/요구사항/방법론

### 4.1 실험 목적

| 실험 ID | 목적 |
|---|---|
| E1 | pairwise conflict proxy 예측에서 baseline rule의 타당성 확인 |
| E2 | spatial heatmap이 CPA 기반 단순 표시보다 정보량이 높은지 확인 |
| E3 | speed scenario에 따라 risk contour가 의미 있게 변하는지 확인 |
| E4 | ML comparator가 baseline 대비 어떤 이점을 가지는지 확인 |
| E5 | 어떤 상황에서 제안 방식이 실패하는지 분석 |

### 4.2 baseline vs proposed 비교

| 방법 | 설명 | 역할 |
|---|---|---|
| B0: CPA threshold only | `DCPA`, `TCPA` 임계값만 사용한 위험 판정 | 가장 단순한 기준선 |
| B1: Rule pairwise list | 위험 선박 목록만 산출, spatial map 없음 | pairwise-only 비교군 |
| P1: Rule-based spatial map | 본 프로젝트 핵심 baseline | 주 방법 |
| P2: Logistic Regression + spatial projection | interpretable ML 비교군 | 확장안 |
| P3: Gradient Boosting + spatial projection | 비선형 ML 비교군 | 확장안 |

### 4.3 실험 변수

| 변수 | 값 후보 | 목적 |
|---|---|---|
| horizon | 10 / 15 / 20분 | time sensitivity |
| grid size | 100m / 250m / 500m | 해상도와 계산량 trade-off |
| threshold | 0.35 / 0.65 기준 조정 | contour 민감도 |
| scenario multiplier | 0.8 / 1.0 / 1.2 | speed effect |
| aggregation | max / top-k sum / union | spatial risk aggregation 비교 |
| density feature | on / off | 혼잡도 기여 확인 |

### 4.4 평가 지표

| 범주 | 지표 | 설명 |
|---|---|---|
| pairwise 분류 | AUROC, AUPRC | realized future separation label 예측 성능 |
| pairwise threshold | Precision, Recall, F1 | 특정 임계값 비교 |
| spatial | CPA-point containment | 미래 CPA 근방이 고위험 영역에 포함되는 비율 |
| spatial | Top-q risk cell capture | 미래 근접 경로가 상위 위험 셀에 포함되는 비율 |
| scenario | contour area delta | 시나리오 간 contour 면적 변화 |
| scenario | sector risk shift | 방향별 위험 중심 이동량 |
| system | latency, memory | 실제 MVP 가능성 |

### 4.5 ablation study 항목

| Ablation ID | 제거 요소 | 검증 목적 |
|---|---|---|
| A1 | traffic density 제거 | 혼잡도 항의 실질 기여 확인 |
| A2 | encounter type 제거 | 도메인 규칙 항의 기여 확인 |
| A3 | bearing 항 제거 | 자선 중심 방향성 표현 기여 확인 |
| A4 | time decay 제거 | 단기 미래 강조의 필요성 확인 |
| A5 | spatial kernel 제거 | pairwise -> spatial projection의 핵심성 검증 |
| A6 | speed scenario 재계산 제거 | scenario-aware 계산 필요성 확인 |

### 4.6 speed scenario 비교 실험

#### controlled scenarios

| 케이스 | 기대 확인 포인트 |
|---|---|
| Head-on | 감속/증속에 따른 전방 고위험 영역 이동 |
| Starboard crossing | 우현 전방 contour 확장 또는 축소 |
| Overtaking | 후방/측후방 위험 분포 변화 |
| Congested harbor approach | density 항의 영향과 다중 타선 상호작용 |

#### real AIS case studies

| 케이스 유형 | 선정 기준 |
|---|---|
| 근접교행 사례 | DCPA 낮고 TCPA가 짧은 시점 |
| 혼잡 항로 사례 | 동일 시점 다수 타선 존재 |
| 저위험 대비 사례 | 넓은 수역의 분산 traffic |

### 4.7 해역/조건별 일반화 검토

| 수준 | 계획 | 상태 |
|---|---|---|
| 기본 | 동일 해역 내 시간대 분리 검증 | [확정] |
| 확장 | 날씨/시정 정보 없이 주간/야간 간접 비교 | [합리적 가정] |
| 추가 | 다중 해역 전이 실험 | [추가 검증 필요] |

### 4.8 failure case 분석 계획

| failure 유형 | 분석 질문 |
|---|---|
| AIS gap case | 데이터 누락이 contour를 왜곡했는가? |
| parallel traffic | 실제 위험이 낮은데 고밀도 때문에 과대평가되는가? |
| diverging after close pass | TCPA/DCPA 기반 규칙이 이미 지나간 상황을 과대평가하는가? |
| noisy heading | heading fallback이 encounter type 분류를 왜곡하는가? |

### 4.9 결과 해석 방법

정량 결과만으로 결론을 내리지 않는다. 아래 3층 해석 구조를 사용한다.

1. `Metric layer`: AUROC, containment, latency
2. `Spatial layer`: 대표 heatmap/contour 이미지
3. `Narrative layer`: 왜 해당 결과가 나왔는지 factor와 failure를 설명

권장 결과 정리 표:

| 질문 | 핵심 그림 | 핵심 표 | 해석 포인트 |
|---|---|---|---|
| RQ1 | baseline heatmap 사례 | containment 표 | 공간 표현력이 실제로 늘었는가 |
| RQ2 | scenario comparison 3분할 화면 | contour area delta | 속력 변화에 반응하는가 |
| RQ3 | rule vs ML 사례 비교 | metric table | ML이 꼭 필요한가 |
| RQ4 | failure cases | ablation 표 | 어떤 항이 중요한가 |

## 5. 성공 기준 또는 평가 기준

| 항목 | 기준 | 상태 |
|---|---|---|
| baseline 타당성 | B0/B1 대비 P1의 spatial 해석력이 개선됨 | [확정] |
| scenario 가시성 | 대표 사례에서 contour 변화가 의미 있게 보임 | [확정] |
| ML 가치 판단 | P2/P3의 개선 여부를 명확히 해석 가능 | [확정] |
| 실패 분석 | 최소 3종 failure case 문서화 | [확정] |

## 6. 리스크와 한계

| 항목 | 내용 | 상태 |
|---|---|---|
| 평가의 proxy성 | 지표가 실제 항해 안전성과 직접 일치하지 않음 | [리스크] |
| controlled scenario 단순화 | 실제 해상 복잡성을 충분히 반영 못함 | [리스크] |
| 단일 해역 실험 | 일반화 결론이 제한적 | [리스크] |
| metric interpretation | spatial metric 설계가 낯설 수 있음 | [리스크] |

## 7. 핵심 결정사항

- [확정] `rule-based spatial map`을 main method로 둔다.
- [확정] 실험은 `정량 + 정성 + failure case`를 함께 본다.
- [확정] ablation에서 `spatial kernel`과 `speed scenario recomputation`을 핵심 검증 대상으로 둔다.
- [합리적 가정] containment 계열 spatial metric을 주요 지표로 사용한다.

## 8. 오픈 이슈

1. [추가 검증 필요] spatial metric을 교수/심사자가 직관적으로 이해할 수 있도록 어떻게 설명할 것인가?
2. [추가 검증 필요] real AIS case와 synthetic case의 비중을 어떻게 조절할 것인가?
3. [추가 검증 필요] cross-area generalization이 불가능할 경우 논문 기여를 어떻게 정리할 것인가?

## 9. 다음 액션

1. 실험 config 템플릿을 작성해 horizon, grid, threshold를 바꿔 돌릴 수 있게 한다.
2. representative case mining 스크립트를 만들어 사례 후보를 추출한다.
3. 결과 표와 그림 포맷을 미리 정해 나중에 논문/발표 자료 전환 비용을 줄인다.

설명 팁: 심사자에게는 "이 실험은 모델 성능 숫자만 보는 게 아니라, heatmap과 contour가 실제로 더 설명력 있는 표현인지 검증한다"라고 강조하는 편이 좋다.
