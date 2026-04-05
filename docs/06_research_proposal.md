# 문서명
연구계획서(Research Proposal)

# 문서 목적
연구 배경, 연구 문제, 차별점, 연구 질문(RQ), 가설(Hypothesis), 방법론, 데이터셋 구성, 실험 설계, 기대 기여점, 한계, 논문 목차 초안을 정의한다.

# 대상 독자
지도교수, 대학원 심사자, 연구자, PM, 기술 리드

# 작성 버전
v1.0

# 핵심 요약
- [확정] 연구의 중심 질문은 `pairwise AIS risk 판단을 own-ship-centric spatial risk representation으로 확장할 수 있는가`다.
- [확정] 핵심 기여 후보는 `spatial risk mapping`, `speed scenario 비교`, `설명 가능한 risk contour`다.
- [합리적 가정] 연구 범위는 석사 프로젝트 수준이며, 단일 해역 MVP 후 cross-case validation을 수행한다.
- [확정] ML은 연구의 필수 조건이 아니라 비교군 또는 확장안이다.

## 1. 배경 및 문제 정의

AIS 기반 해양 위험 분석은 전통적으로 CPA/TCPA, encounter type, pairwise conflict detection에 집중되어 왔다. 그러나 실제 항해 의사결정은 "어떤 타선이 위험한가" 뿐 아니라 "지금 자선 주변 어떤 공간과 방향이 상대적으로 위험한가"라는 공간적 인지가 중요하다.

따라서 본 연구는 위험 표현 단위를 `선박 쌍(pair)`에서 `자선 중심 공간 cell`로 확장한다. 이는 단순 시각화 추가가 아니라, 위험 정보를 사람이 해석 가능한 공간 구조로 재구성하는 문제다.

## 2. 목표와 비목표

### 2.1 연구 목표

| 목표 | 설명 | 상태 |
|---|---|---|
| R-G1 | own-ship-centric spatial risk map 정의 | [확정] |
| R-G2 | speed scenario별 위험 분포 차이 분석 | [확정] |
| R-G3 | 설명 가능한 rule-based baseline 제안 | [확정] |
| R-G4 | ML comparator를 통한 확장 가능성 검토 | [확정] |

### 2.2 비목표

| 항목 | 설명 | 상태 |
|---|---|---|
| 법적 회피 의사결정 연구 | COLREG 준수 자동화 연구가 아님 | [확정] |
| 제어 성능 연구 | 자율항해 control loop 연구가 아님 | [확정] |
| 실선 안전성 증명 | 운영 안전성 보장 연구가 아님 | [확정] |

## 3. 핵심 가정과 제약

| 항목 | 내용 | 상태 |
|---|---|---|
| 데이터 | 공개 AIS만 사용 | [확정] |
| 정답 라벨 | collision ground truth 부족 | [확정] |
| 연구 단위 | snapshot별 pairwise feature -> spatial risk map | [확정] |
| 실험 범위 | 단일 해역 중심, 일반화는 보조 분석 | [합리적 가정] |
| 검증 수단 | pseudo-label + case study + controlled scenario | [확정] |

## 4. 상세 설계/요구사항/방법론

### 4.1 기존 접근과 차별점

| 구분 | 기존 접근 | 본 연구 제안 |
|---|---|---|
| 위험 단위 | pairwise ship-to-ship | own-ship-centric spatial cell |
| 출력 | CPA/TCPA 수치, 위험 선박 목록 | heatmap + contour + 설명 텍스트 |
| 시나리오 | 현재 상태 판정 중심 | speed scenario별 비교 |
| 설명 방식 | 숫자/룰 중심 | 공간 표현 + 룰 기반 설명 |
| AI 역할 | 일부는 black-box classifier | baseline은 explainable rule, ML은 comparator |

### 4.2 연구 질문(RQ)

| RQ ID | 연구 질문 |
|---|---|
| RQ1 | AIS 기반 pairwise risk를 자선 중심 spatial risk map으로 확장하면 항해 위험 인지가 더 직관적으로 표현되는가? |
| RQ2 | speed scenario(감속/현속/증속)에 따라 위험 contour와 고위험 영역이 의미 있게 달라지는가? |
| RQ3 | 설명 가능한 rule-based baseline만으로도 유의미한 spatial risk representation이 가능한가? |
| RQ4 | 간단한 ML comparator가 rule-based baseline 대비 pairwise conflict proxy 예측에서 개선을 보이더라도, 공간적 해석력 측면에서 추가 가치가 있는가? |

### 4.3 가설(Hypothesis)

| 가설 ID | 가설 | 상태 |
|---|---|---|
| H1 | rule-based baseline만으로도 case study에서 직관적인 위험 공간 분포를 재현할 수 있다 | [합리적 가정] |
| H2 | speed scenario를 바꾸면 contour 면적과 고위험 방향이 유의미하게 변한다 | [합리적 가정] |
| H3 | pairwise classifier 성능이 조금 높아져도, spatial projection 구조 자체가 전체 시스템 가치의 핵심이다 | [합리적 가정] |
| H4 | 설명 가능한 baseline은 연구 설득력과 실무 수용성을 동시에 높인다 | [합리적 가정] |

### 4.4 방법론

#### 연구 절차

1. 공개 AIS 데이터 수집 및 정제
2. 자선/타선 trajectory reconstruction
3. pairwise kinematic feature 계산
4. rule-based pairwise severity 정의
5. spatial projection으로 risk heatmap 생성
6. contour 추출 및 시나리오 비교
7. pseudo-label 기반 ML comparator 학습
8. 정량/정성 평가 및 failure case 분석

#### 핵심 방법론 포인트

| 항목 | 방법 |
|---|---|
| baseline | rule-based weighted severity |
| spatialization | predicted relative path + kernel projection |
| scenario analysis | own ship speed multiplier 적용 |
| evaluation | pairwise metric + spatial metric + case study |

### 4.5 데이터셋 구성

| 구성 요소 | 설명 | 상태 |
|---|---|---|
| 해역 | 단일 혼잡 해역 1곳 우선 | [합리적 가정] |
| 기간 | 연속 4주 | [합리적 가정] |
| 자선 샘플 | 연속성이 좋은 track segment 여러 개 | [합리적 가정] |
| 타선 샘플 | 자선 반경 6 NM 이내 target set | [합리적 가정] |
| evaluation cases | head-on, crossing, overtaking, congested traffic 사례 | [확정] |

### 4.6 실험 설계 개요

| 실험 | 목적 |
|---|---|
| Exp-1 | CPA threshold baseline vs proposed rule-based spatial map 비교 |
| Exp-2 | speed scenario별 contour/area/sector risk 변화 분석 |
| Exp-3 | Logistic Regression / Gradient Boosting comparator 비교 |
| Exp-4 | factor ablation으로 설명 가능한 요소의 기여 확인 |
| Exp-5 | canonical encounter case study 분석 |

### 4.7 기대 기여점

| 기여 영역 | 내용 | 상태 |
|---|---|---|
| 표현 기여 | pairwise risk를 spatial risk mapping으로 확장 | [확정] |
| 방법론 기여 | 설명 가능한 rule-based severity를 contour와 결합 | [확정] |
| 분석 기여 | speed scenario별 위험 분포 비교 프레임 제안 | [확정] |
| 실용 기여 | 공개 AIS만으로 재현 가능한 MVP 연구 구조 제시 | [확정] |

### 4.8 한계

| 항목 | 설명 | 상태 |
|---|---|---|
| ground truth 부족 | 실제 충돌/회피 의도 정답 없음 | [확정] |
| 센서 제한 | AIS-only로 hidden target, weather 영향 미반영 | [확정] |
| 해역 일반화 제한 | 단일 해역에서 출발하면 일반화 주장 약함 | [리스크] |
| 법적 해석 제한 | encounter type은 heuristic일 뿐 | [확정] |

### 4.9 논문 목차 초안

1. 서론
2. 문제 정의 및 연구 범위
3. 관련 접근 정리: AIS risk, pairwise methods, spatial representation
4. 데이터셋 및 전처리
5. 제안 방법: rule-based severity + spatial projection + contour
6. 실험 설계
7. 결과 및 분석
8. failure case와 한계
9. 결론 및 향후 과제

## 5. 성공 기준 또는 평가 기준

| 항목 | 기준 | 상태 |
|---|---|---|
| 연구 질문 명확성 | RQ와 가설이 구현 구조와 연결됨 | [확정] |
| 차별점 명확성 | pairwise 대비 spatial extension이 설득력 있게 제시됨 | [확정] |
| 실험 가능성 | 12주 내 최소 3개 실험 수행 가능 | [합리적 가정] |
| 논문성 | 방법, 평가, 한계가 균형 있게 제시됨 | [확정] |

## 6. 리스크와 한계

| 항목 | 내용 | 상태 |
|---|---|---|
| novelty 과장 위험 | 단순 시각화를 기여로 과장할 수 있음 | [리스크] |
| literature grounding 부족 | 선행연구 정리가 약하면 논문성 약화 | [리스크] |
| evaluation 약함 | 정량평가가 proxy metric 위주가 될 수 있음 | [리스크] |
| ML 필요성 불명확 | comparator의 연구 가치가 약할 수 있음 | [리스크] |

## 7. 핵심 결정사항

- [확정] 연구의 주 기여는 `spatial risk representation`이다.
- [확정] `speed scenario comparison`을 독립 기여 축으로 둔다.
- [확정] ML은 연구의 필수 기여가 아니라 `비교/확장` 기여다.
- [합리적 가정] 석사 프로젝트 수준에서는 단일 해역 + 다수 사례 분석만으로도 충분히 설득 가능하다.

## 8. 오픈 이슈

1. [추가 검증 필요] 관련 연구 대비 novelty statement를 어떻게 더 정교화할 것인가?
2. [추가 검증 필요] 도메인 전문가 정성 평가를 연구에 포함할 수 있는가?
3. [추가 검증 필요] 단일 해역이 아닌 다중 해역 실험이 가능한가?

## 9. 다음 액션

1. 선행연구 리뷰 틀을 만들어 pairwise 접근과 spatial 접근을 비교 정리한다.
2. canonical encounter 시나리오 3종을 실험셋에 포함한다.
3. 연구 질문별로 대응 metric과 그림 유형을 사전에 연결한다.

설명 팁: 교수에게는 "핵심 novelty는 AI 모델이 아니라 위험 표현 단위를 pairwise에서 spatial로 바꾼 것"이라고 선명하게 말하는 편이 훨씬 강하다.
