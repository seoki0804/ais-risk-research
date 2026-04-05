# 문서명
위험도 정의서(Risk Definition Specification)

# 문서 목적
위험도의 의미, baseline risk score 수식, 각 구성 요소의 반영 방식, cell-level aggregation, safety contour 생성 논리, 위험 등급 기준, 설명 가능한 규칙과 ML의 역할 분담을 정의한다.

# 대상 독자
도메인 분석가, 데이터사이언티스트, ML 엔지니어, PM, 연구자

# 작성 버전
v1.0

# 핵심 요약
- [확정] 본 문서의 risk score는 `실제 충돌확률`이 아니라 `AIS-only 조건에서의 설명 가능한 근접위험 proxy score`다.
- [확정] baseline은 `distance`, `DCPA`, `TCPA`, `bearing`, `relative speed`, `encounter type`, `traffic density`를 결합한 규칙 기반 점수다.
- [확정] cell risk는 pairwise severity를 예측 상대위치 경로에 공간 커널로 투영해 계산한다.
- [합리적 가정] 초기 분류 기준은 `Safe < 0.35`, `Caution 0.35~0.65`, `Danger >= 0.65`다.

## 1. 배경 및 문제 정의

위험도를 어떻게 정의하느냐에 따라 이 프로젝트의 품질과 설명 가능성이 결정된다. AIS만으로는 실제 조타 의도, 기상, 시정, 센서 오차, 기관 응답을 충분히 알 수 없기 때문에, risk score를 `절대적 안전 판단`으로 정의하는 것은 부적절하다.

따라서 본 프로젝트의 위험도는 다음과 같이 정의한다.

> 자선 중심 시점에서, 공개 AIS로 관측 가능한 상대운동과 국소 교통 맥락을 바탕으로 향후 단기 horizon 내 공간적 근접위험이 얼마나 높은지를 나타내는 설명 가능한 proxy score

## 2. 목표와 비목표

### 2.1 목표

| 항목 | 설명 | 상태 |
|---|---|---|
| 정의 명료성 | risk score가 무엇을 의미하고 의미하지 않는지 명확화 | [확정] |
| 설명 가능성 | 각 factor의 기여를 추적 가능 | [확정] |
| 시각화 연결성 | cell risk와 contour 생성까지 연결되는 구조 | [확정] |
| 확장성 | ML comparator가 들어와도 baseline 해석 유지 | [확정] |

### 2.2 비목표

| 항목 | 설명 | 상태 |
|---|---|---|
| 실제 충돌확률 추정 | 정답 확률 모델을 주장하지 않음 | [확정] |
| 법적 위험 판정 | COLREG legal compliance engine으로 해석하지 않음 | [확정] |
| 자동 회피 추천 | 조종 권고 시스템으로 확장하지 않음 | [확정] |

## 3. 핵심 가정과 제약

| 항목 | 값 | 상태 |
|---|---|---|
| horizon | 15분 | [합리적 가정] |
| grid radius | 6 NM | [합리적 가정] |
| grid cell size | 250m | [합리적 가정] |
| time step | 30초 | [합리적 가정] |
| speed scenarios | 0.8x, 1.0x, 1.2x | [합리적 가정] |
| density radius | 2 NM | [합리적 가정] |
| contour threshold | 0.35 / 0.65 | [합리적 가정] |

## 4. 상세 설계/요구사항/방법론

### 4.1 위험도의 정의

#### 4.1.1 pairwise risk severity

타선 `i`에 대한 시나리오 `s`의 pairwise severity `C_i(s)`는 다음으로 정의한다.

```text
C_i(s) = w_dist * f_dist(d_i)
       + w_dcpa * f_dcpa(dcpa_i(s))
       + w_tcpa * f_tcpa(tcpa_i(s))
       + w_bearing * f_bearing(beta_i)
       + w_relspeed * f_relspeed(vrel_i(s))
       + w_enc * f_encounter(e_i(s))
       + w_density * f_density(rho)
```

제약:

- 모든 `f_*`는 `[0, 1]`로 정규화한다.
- 모든 `w_*`의 합은 `1`이다.
- `C_i(s)`는 `0~1` 범위의 proxy severity다.

#### 4.1.2 권장 baseline weight

| 요소 | 기호 | 기본 가중치 | 상태 |
|---|---|---|---|
| 거리 | `w_dist` | 0.15 | [합리적 가정] |
| DCPA | `w_dcpa` | 0.20 | [합리적 가정] |
| TCPA | `w_tcpa` | 0.20 | [합리적 가정] |
| 상대방위 | `w_bearing` | 0.10 | [합리적 가정] |
| 상대속도 | `w_relspeed` | 0.10 | [합리적 가정] |
| encounter type | `w_enc` | 0.15 | [합리적 가정] |
| 교통밀도 | `w_density` | 0.10 | [합리적 가정] |

이 가중치는 초기값이며, calibration 또는 전문가 검토로 조정 가능하다.

### 4.2 구성 요소별 반영 방식

#### 4.2.1 거리(distance)

```text
f_dist(d) = exp(-d / d0)
```

- `d0 = 1.0 NM` [합리적 가정]
- 현재 거리가 가까울수록 높은 점수

#### 4.2.2 DCPA

```text
f_dcpa(x) = max(0, 1 - x / D0)
```

- `D0 = 1.0 NM` [합리적 가정]
- 최근접 접근 거리가 작을수록 위험

#### 4.2.3 TCPA

```text
f_tcpa(t) =
  0,                  if t <= 0 or t > T0
  1 - t / T0,         if 0 < t <= T0
```

- `T0 = 15분` [합리적 가정]
- 최근접 접근이 곧 일어날수록 높은 점수

#### 4.2.4 상대방위(relative bearing)

자선 선수 기준 섹터를 사용한다.

| bearing sector | 예시 범위 | 점수 |
|---|---|---|
| Ahead / bow | `|beta| <= 22.5°` | 1.0 |
| Forward beam | `22.5° < |beta| <= 90°` | 0.8 |
| Abeam / aft beam | `90° < |beta| <= 135°` | 0.5 |
| Astern | `|beta| > 135°` | 0.3 |

상태: [합리적 가정]

#### 4.2.5 상대속도(relative speed)

```text
f_relspeed(v) = min(1, v / V0)
```

- `V0 = 20 knots` [합리적 가정]
- 상대속도가 높을수록 상황 악화 가능성이 큼

#### 4.2.6 encounter type

| encounter type | 점수 | 설명 |
|---|---|---|
| head-on | 1.0 | 정면 접근 |
| crossing | 0.85 | 횡단 접근 |
| overtaking | 0.70 | 추월 상황 |
| diverging / low relevance | 0.20 | 이탈 중 또는 상호영향 낮음 |

상태: [합리적 가정]

주의:

- 이 분류는 `COLREG legal judgment`가 아니라 `heuristic encounter category`다.

#### 4.2.7 traffic density

```text
rho = number_of_targets_within_2NM / local_area
f_density(rho) = min(1, rho / rho_ref)
```

- `rho_ref`는 calibration set의 90 percentile 사용 권장 [합리적 가정]
- 절대 밀도보다 지역 분포 기준 정규화가 안정적이다

### 4.3 speed scenario 반영 방식

시나리오 `s`는 자선 속도벡터만 수정한다.

```text
v_own(s) = m_s * v_own(current)
where m_s in {0.8, 1.0, 1.2}
```

이후 각 타선에 대해 `dcpa_i(s)`, `tcpa_i(s)`, `vrel_i(s)`, `e_i(s)`를 다시 계산한다.

원칙:

- [확정] 타선 상태는 현재 속력/침로 유지
- [확정] 자선 heading 고정
- [확정] 속력 변화만 비교하여 scenario effect를 분리
- [리스크] 실제 운항의 연속 기동과 타선 반응은 반영되지 않음

### 4.4 cell 단위 risk 집계 방식

#### 4.4.1 상대위치 예측

각 타선 `i`에 대해 상대위치 경로를 예측한다.

```text
p_i_rel(t_k, s) = p_i_rel(0) + v_i_rel(s) * t_k
for t_k in {0, 30s, ..., 15min}
```

#### 4.4.2 시간감쇠(time decay)

```text
h(t_k) = max(0, 1 - t_k / H)
```

- 가까운 미래를 더 크게 반영
- `H = 15분` [합리적 가정]

#### 4.4.3 공간 커널(spatial kernel)

셀 중심 `c`와 예측 상대위치 간 거리에 따라 contribution을 부여한다.

```text
K(c, p) = exp( - ||c - p||^2 / (2 * sigma^2) )
```

- `sigma = 200m` [합리적 가정]

#### 4.4.4 baseline cell risk

```text
r_i(c, t_k, s) = C_i(s) * h(t_k) * K(c, p_i_rel(t_k, s))
R(c, s) = max over i, t_k of r_i(c, t_k, s)
```

선택 이유:

- `max aggregation`은 어떤 타선이 특정 셀을 지배적으로 위험하게 만드는지 설명하기 쉽다.
- contour threshold tuning이 비교적 단순하다.

확장안:

```text
R_union(c, s) = 1 - product over i,t_k (1 - clip(r_i(c, t_k, s), 0, 0.95))
```

이는 여러 중간위험 선박의 누적 효과를 표현할 때 사용 가능하다.

### 4.5 safety contour 생성 논리

| 단계 | 설명 |
|---|---|
| 1 | risk grid를 optional smoothing한다 |
| 2 | threshold `theta_safe` 이상 영역의 경계를 추출한다 |
| 3 | 너무 작은 조각 polygon은 제거한다 |
| 4 | `theta_safe`, `theta_warn` 두 개 contour를 생성할 수 있다 |

기본 threshold:

| contour | threshold | 의미 | 상태 |
|---|---|---|---|
| safety contour | 0.35 | 상대적 주의 경계 | [합리적 가정] |
| warning contour | 0.65 | 고위험 경계 | [합리적 가정] |

주의:

- 이름은 `safety contour`지만, 실제 의미는 `현재 가정 하에서 상대적으로 안전 영역의 바깥 경계`다.
- UI에서 반드시 disclaimer를 붙여야 한다.

### 4.6 위험/주의/안전 등급 기준

| 등급 | 기준 | 의미 |
|---|---|---|
| Safe | `R < 0.35` | 현재 가정 하에서 즉시 높은 충돌 근접위험은 낮음 |
| Caution | `0.35 <= R < 0.65` | 주의가 필요한 공간 |
| Danger | `R >= 0.65` | 상대적으로 높은 단기 근접위험 |

상태: [합리적 가정]

### 4.7 설명 가능한 규칙과 ML의 역할 분담

| 구성 | 역할 | 원칙 |
|---|---|---|
| 규칙 기반 engine | 1차 결과 생성 | 항상 해석 가능해야 함 |
| Logistic Regression | baseline 대비 계수 기반 비교 | explainability 보조 |
| Gradient Boosting | 비선형 개선 가능성 검토 | 설명 도구(SHAP 등)는 보조 수단 |
| UI explanation | 최종 사용자 설명 레이어 | 규칙 기반 factor를 우선 노출 |

결론:

- [확정] 최종 사용자에게 보여주는 주 출력은 규칙 기반 결과를 우선한다.
- [확정] ML 결과가 더 좋아도 baseline을 대체하기보다 비교/보완 수단으로 유지한다.

### 4.8 정성적/정량적 해석 방식

#### 정량 지표

| 지표 | 설명 |
|---|---|
| high-risk area ratio | `R >= theta_warn` 셀 면적 비율 |
| contour area | contour 내부 면적 |
| contour shift | 시나리오 간 contour 중심점/방향 변화 |
| sector risk | 8방위 섹터별 평균 위험도 |
| top contributor share | 최고 기여 타선의 위험 점유율 |

#### 정성 설명 템플릿

```text
현재 시나리오에서 자선 전방 우현 섹터의 위험도가 가장 높다.
주요 원인은 (1) 12분 내 근접 예상(TCPA), (2) 낮은 DCPA, (3) 혼잡도 증가다.
감속 시 해당 고위험 영역이 자선 전방에서 우현 측면으로 축소 이동했다.
```

## 5. 성공 기준 또는 평가 기준

| 항목 | 기준 | 상태 |
|---|---|---|
| 점수 해석성 | 각 risk score에 기여 factor 추적 가능 | [확정] |
| 공간 연결성 | pairwise severity가 heatmap/contour로 자연스럽게 이어짐 | [확정] |
| 시나리오 반응성 | 속력 변경 시 risk map 차이가 관측됨 | [확정] |
| 안전한 표현 | 실제 안전 보장 또는 제어로 오해되지 않음 | [확정] |

## 6. 리스크와 한계

| 항목 | 내용 | 상태 |
|---|---|---|
| threshold 임의성 | 0.35/0.65 기준은 초기값일 뿐 | [리스크] |
| weight calibration 부족 | 도메인 검증 없으면 임계값 설득력이 약함 | [리스크] |
| max aggregation 단순성 | 다중 중간위험 누적 효과를 충분히 반영 못할 수 있음 | [리스크] |
| name ambiguity | `safety contour`가 과도한 안전 보장으로 오해될 수 있음 | [리스크] |

## 7. 핵심 결정사항

- [확정] risk score는 `collision probability`가 아니라 `explainable proxy risk`다.
- [확정] baseline은 규칙 기반 가중합 + spatial kernel + max aggregation 구조다.
- [확정] speed scenario는 자선 속력만 바꾸는 최소 시나리오로 제한한다.
- [합리적 가정] 초기 등급 기준은 `0.35 / 0.65`를 사용한다.

## 8. 오픈 이슈

1. [추가 검증 필요] `0.5 NM`, `15분`, `6 NM 반경`이 대상 해역에 적절한가?
2. [추가 검증 필요] 교통밀도 항을 단순 카운트로 둘지 kernel density로 둘지?
3. [추가 검증 필요] 시나리오별 contour가 지나치게 noisy할 경우 어떤 smoothing이 적절한가?

## 9. 다음 액션

1. 샘플 해역으로 calibration set을 만들고 가중치와 threshold를 1차 조정한다.
2. controlled encounter case를 만들어 risk map이 직관적으로 나오는지 검토한다.
3. explanation 템플릿을 UI/UX 문서와 연결한다.

설명 팁: 교수에게는 "이 점수는 실제 충돌확률이 아니라, AIS로 계산 가능한 근접위험 proxy를 공간적으로 풀어낸 것"이라고 먼저 선을 그으면 과장 리스크를 크게 줄일 수 있다.
