# 문서명
UI/UX 요구사항 문서(UI/UX Requirement Doc)

# 문서 목적
사용자 목표, 메인 화면 구성, 지도 시각화 요소, heatmap legend, contour 표현 방식, speed scenario control, interaction flow, 알림/설명 메시지, 사용성 요구사항, 발표/포트폴리오용 화면 구성을 정의한다.

# 대상 독자
UX 기획자, 프론트엔드 개발자, PM, 데이터 시각화 담당자

# 작성 버전
v1.0

# 핵심 요약
- [확정] 핵심 UI 목표는 `자선 주변 위험 공간을 빠르게 이해`하고 `속력 시나리오 차이를 직관적으로 비교`하게 만드는 것이다.
- [확정] 메인 화면은 `지도`, `시나리오 패널`, `설명 패널`, `타임라인` 4개 블록을 중심으로 설계한다.
- [확정] `safety contour`는 안전 보장선이 아니라 `상대적 위험 경계`임을 UI에서 명시해야 한다.
- [합리적 가정] MVP는 데스크톱 우선 UI로 만들고, 발표와 포트폴리오용 레이아웃을 별도로 최적화한다.

## 1. 배경 및 문제 정의

위험도 계산 자체가 좋아도 사용자가 공간적 의미를 빠르게 읽지 못하면 제품 가치가 낮다. 특히 본 프로젝트는 숫자보다 `위험 공간의 형상`, `방향성`, `시나리오 차이`, `설명 문장`이 중요하다. 따라서 UI/UX는 단순 지도 표시가 아니라, `해석 지원`을 중심에 둔 분석형 인터페이스여야 한다.

## 2. 목표와 비목표

### 2.1 목표

| 항목 | 설명 | 상태 |
|---|---|---|
| UX-G1 | 고위험 방향과 영역을 한눈에 파악 가능 | [확정] |
| UX-G2 | 3개 speed scenario를 빠르게 비교 가능 | [확정] |
| UX-G3 | 결과의 근거를 설명 패널에서 확인 가능 | [확정] |
| UX-G4 | 발표/포트폴리오용 시각 결과물 생성 가능 | [확정] |

### 2.2 비목표

| 항목 | 설명 | 상태 |
|---|---|---|
| 실시간 항해 장비 UI | 상용 브리지 UI 수준 최적화는 범위 밖 | [확정] |
| 복잡한 route editor | 항로 생성/수정 도구는 초기 제외 | [확정] |
| 모바일 우선 설계 | 초기 MVP는 데스크톱 우선 | [합리적 가정] |

## 3. 핵심 가정과 제약

| 항목 | 내용 | 상태 |
|---|---|---|
| 사용자 문맥 | 연구/분석/발표 환경 사용 | [합리적 가정] |
| 지도 기준 | 자선 중심 고정 view 기본 | [확정] |
| 정보 밀도 | 한 화면에 핵심 비교와 설명을 함께 제공 | [확정] |
| 표시 대상 | 위험 heatmap, contour, 자선/타선 위치, 주요 수치 | [확정] |
| 해석 보호장치 | AIS-only 한계와 disclaimer 표시 필요 | [확정] |

## 4. 상세 설계/요구사항/방법론

### 4.1 사용자 목표

| 사용자 | 목표 | UI에서 필요한 것 |
|---|---|---|
| 항해 의사결정 지원 사용자 | 어느 방향이 더 위험한지 빠르게 이해 | 지도 중심 heatmap + contour |
| 연구자 | scenario별 차이와 factor 영향 분석 | 비교 패널 + 세부 설명 |
| 심사자/면접관 | 프로젝트 차별점 빠르게 파악 | 대표 사례 화면 + 요약 카드 |

### 4.2 메인 화면 구성

권장 레이아웃:

```text
+--------------------------------------------------------------+
| Header: case info / own ship / timestamp / export            |
+----------------------+----------------------+----------------+
| Left Control Panel   | Main Map             | Right Insight  |
| - ship/time select   | - base map           | Panel          |
| - scenario selector  | - heatmap            | - top drivers  |
| - threshold slider   | - contours           | - key metrics  |
| - legend toggle      | - vessel tracks      | - explanations |
+--------------------------------------------------------------+
| Bottom Timeline / Replay / Scenario Comparison Summary       |
+--------------------------------------------------------------+
```

### 4.3 지도 위 시각화 요소

| 요소 | 설명 | 필수 여부 |
|---|---|---|
| own ship marker | 자선 위치와 heading 표시 | Must |
| target ship markers | 주변 타선 위치/방향 | Must |
| risk heatmap | 셀 기반 위험도 색상 표현 | Must |
| safety contour | 주의/안전 경계 | Must |
| warning contour | 고위험 경계 | Should |
| predicted relative path | 선택 선박의 예측 경로 | Should |
| sector overlay | 8방위 섹터 표시 | Could |

### 4.4 heatmap legend

권장 색상 체계:

| 등급 | 값 범위 | 색상 제안 | 이유 |
|---|---|---|---|
| Safe | `< 0.35` | Teal / Blue-green | 상대적으로 낮은 위험 |
| Caution | `0.35~0.65` | Amber / Orange | 주의 강조 |
| Danger | `>= 0.65` | Crimson / Red | 고위험 강조 |

UI 원칙:

- [확정] legend에 수치 구간을 명시한다.
- [확정] 색상만으로 구분하지 않고 contour와 텍스트를 함께 제공한다.
- [리스크] red-green 대비만 쓰면 접근성이 떨어질 수 있다.

### 4.5 contour 표현 방식

| contour | 시각 표현 | 설명 문구 |
|---|---|---|
| safety contour | 얇은 실선 또는 점선, blue/teal 계열 | `주의 경계` |
| warning contour | 굵은 점선 또는 solid, orange/red 계열 | `고위험 경계` |

표현 규칙:

- contour label을 지도에 직접 붙이거나 우측 패널에서 수치와 함께 설명
- island polygon이 너무 작으면 숨기고 explanation에서 제외
- contour hover 시 면적, 주요 기여 선박 수 표시 가능

### 4.6 speed scenario control

| 방식 | 장점 | 권장도 |
|---|---|---|
| Segmented control | 현재/감속/증속 전환이 빠름 | 높음 |
| Small multiples 3-panel | 차이를 한 번에 비교 가능 | 높음 |
| Slider | 미세 조정 가능 | 중간 |

권장 MVP:

1. 기본은 `segmented control`
2. 발표/분석 모드에서는 `3-panel comparison`

### 4.7 interaction flow

```text
1. 사용자: own ship와 timestamp 선택
2. 시스템: 주변 타선 조회 및 baseline scenario risk map 계산
3. 사용자: slowdown / speed-up 시나리오 선택
4. 시스템: contour, area delta, top drivers 갱신
5. 사용자: 고위험 셀 또는 타선 클릭
6. 시스템: factor explanation, pairwise metrics, predicted path 표시
7. 사용자: 결과 export 또는 replay 실행
```

### 4.8 알림/설명 메시지

권장 메시지 유형:

| 상황 | 메시지 예시 |
|---|---|
| disclaimer | `본 결과는 공개 AIS와 단순 운동 가정 기반의 의사결정 지원용 지표이며, 실제 조타 지시를 의미하지 않습니다.` |
| high risk insight | `우현 전방 영역의 위험도가 높습니다. 낮은 DCPA와 10분 이내 TCPA가 주요 원인입니다.` |
| scenario delta | `감속 시 고위험 contour 면적이 18% 감소했습니다.` |
| low confidence | `Heading 결측이 많아 encounter type 신뢰도가 낮습니다.` |

### 4.9 사용성 고려사항

| 항목 | 요구사항 |
|---|---|
| 정보 과밀 방지 | 지도 위 레이어를 토글 가능하게 한다 |
| 해석 지원 | 숫자보다 문장형 요약을 함께 보여준다 |
| 비교 용이성 | scenario 간 동일 color scale 유지 |
| 접근성 | 색상 외 contour/label/text 병행 |
| 재현성 | 현재 파라미터를 화면에 명시 |

### 4.10 발표/포트폴리오용 화면 구성

권장 발표 모드 카드:

| 카드 | 내용 |
|---|---|
| Problem Card | pairwise만으로는 공간 위험 인지가 어렵다 |
| Main View | 3개 scenario heatmap + contour |
| Insight Card | top driver, contour area delta, key metrics |
| Method Card | rule-based spatial risk logic 요약 |

발표용 필수 화면:

1. 정면 교행 사례 1개
2. 혼잡 해역 사례 1개
3. 감속으로 contour가 줄어드는 비교 사례 1개

## 5. 성공 기준 또는 평가 기준

| 항목 | 기준 | 상태 |
|---|---|---|
| 직관성 | 처음 보는 사람도 위험 방향을 10초 내 설명 가능 | [합리적 가정] |
| 비교 가능성 | 3개 scenario 차이가 시각적으로 분명함 | [확정] |
| 설명 가능성 | 주요 위험 요인이 패널에서 확인 가능 | [확정] |
| 발표 적합성 | 대표 사례 화면만으로 프로젝트 가치 설명 가능 | [확정] |

## 6. 리스크와 한계

| 항목 | 내용 | 상태 |
|---|---|---|
| 과밀한 지도 | 타선이 많으면 heatmap과 marker가 겹칠 수 있음 | [리스크] |
| contour 오해 | 안전 보장선으로 오해될 수 있음 | [리스크] |
| scenario 비교 피로 | 화면 전환이 많으면 차이 인지가 어려움 | [리스크] |
| 데이터 품질 숨김 | low-confidence 상황을 UI가 숨기면 오해를 만든다 | [리스크] |

## 7. 핵심 결정사항

- [확정] UI는 `지도 + 시나리오 비교 + 설명 패널` 3요소를 축으로 설계한다.
- [확정] scenario 간 동일한 색상 범위와 contour 규칙을 사용한다.
- [확정] disclaimer를 항상 노출해 의사결정 지원 도구임을 명확히 한다.
- [합리적 가정] 데스크톱 우선 설계 후 필요 시 반응형 보완을 검토한다.

## 8. 오픈 이슈

1. [추가 검증 필요] 발표용 모드와 분석용 모드를 분리할지?
2. [추가 검증 필요] replay 기능을 MVP에 포함할지 후순위로 둘지?
3. [추가 검증 필요] base map을 해도형 중심으로 둘지 단순 지리배경으로 둘지?

## 9. 다음 액션

1. low-fidelity wireframe을 먼저 만든다.
2. 대표 사례 3개를 선정해 발표용 화면 구성에 맞춰 캡처한다.
3. `warning contour`, `safety contour`, `top drivers` 설명 텍스트를 UI 컴포넌트에 고정한다.

설명 팁: 면접관에게는 "이 UI의 목적은 예쁘게 그리는 것이 아니라, 위험 공간과 그 이유를 한 화면에서 이해시키는 것"이라고 설명하면 된다.
