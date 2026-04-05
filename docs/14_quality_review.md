# 문서명
문서 패키지 품질 검토(Quality Review)

# 문서 목적
작성된 문서 패키지의 충돌 여부, 과장 가능성, AIS-only 범위 적합성, baseline/AI 균형, 논문 약점, MVP 과대 범위, 핵심 차별점을 점검한다.

# 대상 독자
PM, 연구책임자, 지도교수, 프로젝트 수행자

# 작성 버전
v1.0

# 핵심 요약
- [확정] 문서 간 핵심 가정은 대체로 일관되며, 공통 기준선은 `1인·12주·단일 해역·규칙 기반 우선·AIS-only`로 유지된다.
- [확정] 과장되거나 검증 불가능한 주장은 대부분 제거되었고, `decision support` framing이 유지된다.
- [리스크] novelty 설명, threshold calibration 근거, pseudo-label 한계, 다중 해역 일반화, 전문가 검증 부재는 논문 관점의 약점이다.
- [확정] MVP 관점에서는 `ML`, `정교한 web UI`, `다중 해역 실험`을 후순위로 밀어 범위를 관리하는 것이 적절하다.

## 1. 문서 간 충돌 여부 점검

### 1.1 일관성 점검 결과

| 항목 | 공통 값/방향 | 충돌 여부 |
|---|---|---|
| 데이터 범위 | 공개 AIS only | 없음 |
| 프로젝트 목적 | 위험도 인지 및 의사결정 지원 | 없음 |
| 비목표 | 자동 조타/상용 인증/센서융합 제외 | 없음 |
| baseline 우선순위 | 규칙 기반 우선, ML은 확장 | 없음 |
| 기본 시나리오 | 현재/20% 감속/20% 증속 | 없음 |
| 기본 horizon | 15분 | 없음 |
| 기본 grid | 반경 6 NM, cell 250m | 없음 |
| contour 해석 | 안전 보장선이 아닌 상대적 위험 경계 | 없음 |

### 1.2 주의가 필요한 부분

| 항목 | 상태 |
|---|---|
| 대상 해역과 데이터 소스는 여전히 미확정이며 여러 문서에서 `[추가 검증 필요]`로 유지됨 | [정상] |
| threshold와 weight는 초기값으로 일관되게 제시되었으나 calibration 전까지 임시값임 | [정상] |

결론:

- [확정] 문서 간 구조적 충돌은 크지 않다.
- [합리적 가정] 실제 해역과 데이터가 정해지면 수치 파라미터 일부는 조정될 수 있다.

## 2. 과장되거나 검증 불가능한 주장 점검

| 점검 항목 | 결과 |
|---|---|
| 완전자율운항 프레이밍 | 제거됨 |
| 실제 안전 보장/법적 회피 판단 주장 | 제거됨 |
| collision probability 직접 추정 주장 | 제거됨 |
| 실시간 상용 시스템 수준 성능 주장 | 제거됨 |
| AIS-only로 intent/weather/control까지 해결 가능하다는 암시 | 제거됨 |

잔여 주의점:

- [리스크] `safety contour`라는 명칭 자체가 과장으로 오해될 수 있으므로 UI와 발표 자료에서 반드시 설명이 필요하다.
- [리스크] ML comparator가 조금 개선되더라도 이를 핵심 기여로 과장하면 논리 일관성이 깨질 수 있다.

## 3. AIS만으로 불가능한 부분이 섞였는지 점검

### 3.1 AIS만으로 가능한 부분

- 자선/타선 trajectory reconstruction
- relative distance, bearing, relative speed 계산
- DCPA/TCPA 기반 pairwise conflict proxy
- traffic density, spatial heatmap, contour visualization
- 속력 시나리오 기반 상대운동 비교

### 3.2 AIS만으로 불가능하거나 제한적인 부분

- 실제 조타 의도와 회피 전략의 정확 추정
- 기상, 시정, 조류, 해상 상태 반영
- 법적/운항상 안전 보장
- 실선 제어 성능 검증
- hidden target 또는 비협조 표적 인지

결론:

- [확정] 문서 패키지에는 AIS-only 범위를 넘어서는 구현 요구는 포함되지 않았다.
- [리스크] 발표 시 표현을 잘못하면 contour나 scenario 비교가 제어 추천처럼 들릴 수 있다.

## 4. 규칙 기반 baseline 없이 AI를 과도하게 전제한 부분 점검

| 점검 항목 | 결과 |
|---|---|
| baseline 존재 여부 | 명확히 존재 |
| ML 필수화 여부 | 필수 아님, 비교/확장안 |
| 딥러닝 과전제 여부 | 없음 |
| 설명 가능한 룰 우선 여부 | 유지됨 |

결론:

- [확정] 문서 전반에서 AI는 과도하게 전제되지 않았다.
- [확정] baseline만으로도 충분히 가치 있는 MVP로 정의되어 있다.

## 5. 논문 관점에서 약한 부분 5개와 보완책

| 약점 | 이유 | 보완책 |
|---|---|---|
| 1. novelty 오해 가능성 | "그냥 heatmap 아닌가?"라는 반응 가능 | pairwise 대비 spatial representation의 정보 구조 차이를 그림과 ablation으로 보여주기 |
| 2. threshold/weight 근거 부족 | 가중치가 임의적으로 보일 수 있음 | calibration 절차, sensitivity analysis, 전문가 리뷰 추가 |
| 3. pseudo-label 한계 | 실제 위험 정답과 다를 수 있음 | controlled scenarios, 정성 사례, 다중 metric 병행 |
| 4. 단일 해역 편향 | 일반화 주장이 약함 | 최소한 시간대/조건 분리 검증 또는 추가 사례 해역 검토 |
| 5. ML 기여 약화 가능성 | baseline이 이미 충분하면 ML 파트가 약해짐 | ML을 핵심 기여가 아니라 비교군/보조 분석으로 위치 조정 |

## 6. MVP 관점에서 범위가 과도한 부분 5개와 축소안

| 과도한 부분 | 왜 과도한가 | 축소안 |
|---|---|---|
| 1. web dashboard 완성도 욕심 | 데이터/실험보다 UI 시간이 커질 수 있음 | notebook 데모 우선, web은 read-only 수준으로 축소 |
| 2. ML 두세 종류 이상 실험 | 1인 일정에서 과도 | Logistic Regression 하나만 남기거나 ML 전체 후순위 |
| 3. 다중 해역 일반화 | 데이터 확보와 전처리 비용 증가 | 단일 해역 + 다양한 사례로 대체 |
| 4. replay/export/full interaction 모두 구현 | MVP보다 제품화 과제에 가까움 | export는 PNG/JSON만, replay는 후순위 |
| 5. contour 정교화 과도 | geometry tuning에 시간 소모 큼 | simple threshold contour + min-area filtering까지만 |

## 7. 이 프로젝트의 가장 강한 차별점 3가지 정리

1. [확정] `pairwise risk`를 `own-ship-centric spatial risk map`으로 바꾼 점
2. [확정] `speed scenario별 위험 분포와 contour 변화`를 비교 가능한 구조로 만든 점
3. [확정] `규칙 기반 baseline`을 중심으로 두어 연구성과와 실무 설명 가능성을 동시에 확보한 점

## 8. 오픈 이슈

1. [추가 검증 필요] 실제 데이터 소스와 해역이 정해진 뒤에도 현재 기본 가정이 유지되는가?
2. [추가 검증 필요] 도메인 전문가 코멘트를 품질 검토 루프에 포함할 수 있는가?

## 9. 다음 액션

1. 대상 해역과 데이터 소스를 확정한 뒤 threshold와 density normalization을 1차 calibration한다.
2. 발표 자료와 UI에서 `safety contour`의 의미를 명확히 설명하는 문구를 고정한다.
3. 논문용으로는 novelty 설명 슬라이드/그림을 별도 준비한다.

설명 팁: 교수나 면접관에게는 "이 프로젝트는 AI 성능 경쟁이 아니라, 설명 가능한 공간 위험 표현을 얼마나 설득력 있게 구현했는지가 핵심"이라고 정리하면 좋다.
