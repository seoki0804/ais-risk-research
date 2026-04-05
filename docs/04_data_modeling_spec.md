# 문서명
데이터 및 모델 설계서(Data & Modeling Specification)

# 문서 목적
사용할 AIS 데이터 정의, raw field 사전, 전처리 규칙, trajectory reconstruction, 상대운동 계산, feature engineering, 라벨 생성 방식, baseline/ML 모델 후보, 데이터 분할 전략, 평가 지표, 누수와 편향 리스크를 정의한다.

# 대상 독자
데이터사이언티스트, ML 엔지니어, 데이터 엔지니어, 연구자

# 작성 버전
v1.0

# 핵심 요약
- [확정] 초기 시스템은 `AIS raw data -> 정제 -> trajectory reconstruction -> pairwise feature 생성 -> spatial projection` 흐름으로 동작한다.
- [확정] ML을 도입하더라도 학습 대상은 우선 `pairwise near-future conflict proxy`이며, `cell risk` 자체를 직접 학습하지 않는다.
- [확정] 현재 구현 기준 pseudo-label은 `reconstructed track 상 향후 15분 내 realized minimum separation`으로 정의한다.
- [확정] 규칙 기반 baseline이 1차 산출물이며, ML은 baseline 대비 비교안 또는 calibration 용도로 제한한다.

## 1. 배경 및 문제 정의

공개 AIS 데이터는 위치, 속력, 침로 중심의 관측 데이터이므로 곧바로 spatial risk map에 사용할 수 없다. 시간 정렬, 결측 처리, trajectory segmentation, 상대운동 계산, feature engineering이 선행되어야 한다. 또한 실제 충돌의 정답 레이블이 거의 없기 때문에, ML을 적용하더라도 라벨 정의를 보수적으로 해야 한다.

본 문서는 `무엇을 raw로 받고`, `어떻게 정제하며`, `어떤 feature를 만들고`, `무엇을 예측 대상으로 둘 것인지`를 명확히 정의한다.

## 2. 목표와 비목표

### 2.1 목표

| 항목 | 설명 | 상태 |
|---|---|---|
| 데이터 재현성 | 동일 raw data에서 동일 curated dataset 재생산 | [확정] |
| feature 신뢰성 | CPA/TCPA, bearing 등 핵심 feature가 일관되게 계산 | [확정] |
| ML 확장 가능성 | 규칙 기반 후 interpretable ML 적용 가능 | [확정] |
| leakage 방지 | 시간/trajectory 기준 분리로 평가 신뢰성 확보 | [확정] |

### 2.2 비목표

| 항목 | 설명 | 상태 |
|---|---|---|
| deep learning 우선 적용 | 라벨 부족 상황에서 딥러닝을 기본 선택하지 않음 | [확정] |
| cell-level direct supervision | 초기 단계에서 셀별 정답 라벨 학습을 시도하지 않음 | [확정] |
| 복합 센서 feature 추가 | AIS-only 범위를 유지 | [확정] |

## 3. 핵심 가정과 제약

| 항목 | 값 | 상태 |
|---|---|---|
| 데이터 단위 | timestamped AIS snapshot + reconstructed track | [확정] |
| 예측 horizon | 15분 | [합리적 가정] |
| pseudo-label 기준 | 향후 15분 내 realized minimum separation < threshold | [확정] |
| track gap 기준 | 10분 초과 시 새 segment | [합리적 가정] |
| interpolation step | 30초 | [합리적 가정] |
| 대상 범위 | 자선 기준 반경 6 NM 내 타선 | [합리적 가정] |

## 4. 상세 설계/요구사항/방법론

### 4.1 사용할 데이터 정의

| 항목 | 설명 | 상태 |
|---|---|---|
| 공개 AIS raw records | timestamp별 선박 상태 관측치 | [확정] |
| own ship selected track | 자선으로 선정한 특정 MMSI의 연속 trajectory segment | [확정] |
| surrounding vessel tracks | 자선 시점 근방에 존재하는 타선 trajectory | [확정] |
| vessel metadata | vessel type, length, width 등 사용 가능 시 보조 feature | [추가 검증 필요] |

### 4.2 AIS raw field 사전

| 필드명 | 타입 | 설명 | 필수 여부 | 처리 규칙 |
|---|---|---|---|---|
| `mmsi` | string/int | 선박 식별자 | 필수 | 문자열 정규화 |
| `timestamp` | datetime | 관측 시각 | 필수 | UTC 또는 기준 타임존 통일 |
| `lat` | float | 위도 | 필수 | 범위 벗어나면 제거 |
| `lon` | float | 경도 | 필수 | 범위 벗어나면 제거 |
| `sog` | float | Speed Over Ground (knots) | 필수 | 음수 제거, 비정상 고속 값 검토 |
| `cog` | float | Course Over Ground (deg) | 필수 권장 | 0~360 정규화 |
| `heading` | float | Heading (deg) | 선택 | 결측 시 `cog` fallback |
| `nav_status` | categorical | 항해 상태 | 선택 | low-confidence feature로 사용 |
| `vessel_type` | categorical | 선종 | 선택 | coarse grouping |
| `rot` | float | Rate of Turn | 선택 | 결측 빈도 높으면 baseline 제외 |
| `length` | float | 선박 길이 | 선택 | 있으면 보조 feature |
| `width` | float | 선박 폭 | 선택 | 있으면 보조 feature |

### 4.3 전처리 규칙

| 규칙 ID | 규칙 | 이유 |
|---|---|---|
| PP-01 | `mmsi + timestamp` 중복 제거 | 동일 시점 복수 레코드 정리 |
| PP-02 | 위경도 범위 오류 제거 | 물리적으로 불가능한 좌표 제거 |
| PP-03 | `sog < 0` 제거, 비현실적 상한 초과 값 점검 | 속력 이상치 제거 |
| PP-04 | `heading` 결측 시 `cog` 사용 | 방향 feature 안정화 |
| PP-05 | 각 MMSI별 timestamp 오름차순 정렬 | trajectory 계산 기초 |
| PP-06 | 10분 초과 gap이면 track segment 분리 | 장시간 단절 track 분리 |
| PP-07 | 2분 이하 작은 gap만 선형 보간 허용 | 과도한 보간 방지 |
| PP-08 | 해역 bounding box 밖 레코드 제거 | 대상 해역 집중 |
| PP-09 | 너무 짧은 segment 제거 | 분석 품질 확보 |

### 4.4 이상치/결측치 처리

| 항목 | 처리 방법 | 상태 |
|---|---|---|
| heading 결측 | `heading := cog` fallback | [확정] |
| vessel_type 결측 | `unknown`으로 유지, baseline 핵심 feature에서는 제외 | [확정] |
| nav_status 결측 | optional feature로만 사용 | [확정] |
| irregular interval | 재샘플링 전 원본 간격 유지, reconstruction 단계에서 표준화 | [확정] |
| 순간 점프(outlier jump) | 속도/거리 기반 jump detector로 제거 후보 표시 | [합리적 가정] |

### 4.5 trajectory reconstruction

재구성 목적은 `불규칙한 AIS 점열`을 `일정 시간 간격의 track segment`로 바꾸는 것이다.

기본 절차:

1. MMSI별 정렬
2. 시간 gap 기반 segment 분리
3. 소구간 보간
4. ENU 또는 projected coordinate 변환
5. 속력/방향 파생치 재계산

의사코드:

```python
for mmsi in vessels:
    track = sort_by_timestamp(records[mmsi])
    segments = split_when_gap_exceeds(track, minutes=10)
    for seg in segments:
        if len(seg) < min_points:
            continue
        seg = interpolate_small_gaps(seg, max_gap_minutes=2, step_seconds=30)
        seg = project_to_local_coordinates(seg)
        save(seg)
```

### 4.6 상대운동 계산 항목

| 항목 | 정의 | 계산 방식 |
|---|---|---|
| relative distance | 자선-타선 간 거리 | geodesic 또는 projected Euclidean |
| relative bearing | 자선 선수 방향 기준 타선 방향각 | bearing difference |
| relative velocity | 속도 벡터 차이 | `v_rel = v_target - v_own` |
| relative speed | 상대속도 크기 | `||v_rel||` |
| TCPA | 최근접 접근 예상 시간 | `- (r·v_rel) / ||v_rel||^2` |
| DCPA/CPA | 최근접 접근 거리 | `||r + TCPA * v_rel||` |
| encounter type | head-on/crossing/overtaking 등 | heuristic rule |
| local traffic density | 국소 혼잡도 | 반경 내 선박 수 또는 kernel density |

수식 초안:

```text
r = p_target - p_own
v_rel = v_target - v_own
TCPA = - (r · v_rel) / ||v_rel||^2
DCPA = || r + TCPA * v_rel ||
```

주의:

- `TCPA < 0`이면 이미 최근접점이 지난 상태로 보고 별도 처리한다.
- `||v_rel|| ≈ 0`인 경우 수치 불안정 방어 로직이 필요하다.

### 4.7 feature engineering

| feature 그룹 | feature | 설명 | baseline 사용 | ML 사용 |
|---|---|---|---|---|
| 기하 | relative distance | 현재 자선-타선 거리 | Yes | Yes |
| 기하 | relative bearing | 선수 기준 방향 섹터 | Yes | Yes |
| 운동 | relative speed | 속도 벡터 차이 크기 | Yes | Yes |
| 운동 | TCPA | 근접 예상 시간 | Yes | Yes |
| 운동 | DCPA | 근접 예상 거리 | Yes | Yes |
| 규칙 | encounter type | head-on/crossing/overtaking heuristic | Yes | Yes |
| 맥락 | local traffic density | 국소 해역 혼잡도 | Yes | Yes |
| 맥락 | vessel type group | 선종 그룹 | Optional | Optional |
| 시나리오 | speed multiplier | 자선 속력 시나리오 계수 | Yes | Yes |
| 시간 | hour-of-day, day-of-week | 운영 패턴 보조 feature | No | Optional |

권장 파생 feature:

- `bearing_sector`: ahead / port bow / starboard bow / abeam / astern
- `closing_speed`: 방사방향 접근 속도
- `conflict_intensity_window`: 최근 N분 내 위험 점수 평균
- `scenario_adjusted_tcpa`: 속력 시나리오를 적용한 TCPA

### 4.8 label 생성 방식 또는 risk score 학습 target 정의

초기 ML 단계에서는 `cell risk`가 아니라 `pairwise near-future conflict`를 예측 대상으로 둔다. 현재 구현 스켈레톤은 reconstructed track에서 `실제 미래 근접도(realized future separation)`를 라벨로 생성한다.

#### pairwise pseudo-label

| 라벨 | 정의 | 상태 |
|---|---|---|
| `y_pair = 1` | 향후 15분 내 reconstructed track 기준 `future minimum separation < threshold` | [확정] |
| `y_pair = 0` | 위 조건 미충족 | [확정] |

확장 가능한 대안:

- multi-class: safe / caution / danger
- fallback proxy: `DCPA/TCPA` 기반 근접위험 정의
- continuous target: `future minimum separation` 또는 `rule-based severity`

중요 원칙:

- [확정] pseudo-label은 `실제 충돌 레이블`이 아니다.
- [확정] ML 결과는 `proxy risk estimator`로 해석해야 한다.
- [확정] realized future separation 기반 label이 baseline의 현재 시점 DCPA/TCPA보다 순환 논리 리스크를 줄인다.
- [리스크] reconstructed track quality가 낮으면 realized label 자체가 흔들릴 수 있다.

### 4.9 baseline 모델

| 모델 | 목적 | 장점 | 한계 |
|---|---|---|---|
| Rule-based risk engine | 1차 MVP, 설명 가능한 기준선 | 해석 용이, 구현 빠름 | threshold tuning 필요 |
| CPA threshold baseline | 가장 단순한 비교군 | 구현 매우 단순 | 공간 표현력 낮음 |
| Pairwise rule + spatial projection | 본 프로젝트 핵심 baseline | spatial map과 직접 연결 | 파라미터 설계 필요 |

### 4.10 ML 모델 후보 비교

| 후보 | 역할 | 장점 | 한계 | 권장 여부 |
|---|---|---|---|---|
| Logistic Regression | interpretable comparator | 계수 해석 가능 | 비선형 표현 약함 | 높음 |
| Gradient Boosting / XGBoost 계열 | 비선형 pairwise risk 분류 | 적은 feature로도 성능 우수 가능 | 설명성 보완 필요 | 높음 |
| Random Forest | 빠른 baseline ML | 튜닝 단순 | calibration 약할 수 있음 | 중간 |
| Sequence model (LSTM/Transformer) | trajectory sequence 학습 | 시간 의존성 반영 가능 | 데이터/라벨 요구 큼, 과함 | 낮음 |

권고:

- [확정] ML 1차 비교안은 `Logistic Regression`과 `Gradient Boosting`이면 충분하다.
- [확정] 딥러닝은 MVP나 석사 프로젝트 초기 범위에서 우선순위가 낮다.

### 4.11 학습/검증/테스트 분리 전략

| 전략 | 설명 | 상태 |
|---|---|---|
| Time-based split | 날짜 구간 기준 train/val/test 분리 | [확정] |
| Segment isolation | 동일 trajectory segment가 서로 다른 split에 섞이지 않게 함 | [확정] |
| MMSI overlap 최소화 | 가능하면 동일 MMSI의 장거리 segment 누수 방지 | [합리적 가정] |
| Cross-area split | 다중 해역 확보 시 별도 검토 | [추가 검증 필요] |

권장 예시:

- Train: 1~3주차
- Validation: 4주차 초반
- Test: 4주차 후반

### 4.12 평가 지표

| 범주 | 지표 | 목적 |
|---|---|---|
| 분류 | AUROC, AUPRC | pairwise pseudo-label 분류력 |
| 분류 | F1, Precision, Recall | threshold 기준 비교 |
| calibration | Brier score, reliability plot | 확률/점수 해석성 |
| ranking | Precision@k risky pairs | 상위 위험 쌍 탐지력 |
| 공간 | CPA-point containment in high-risk cells | spatial map 타당성 |
| 시스템 | latency, memory | MVP 실행 가능성 |

### 4.13 편향/한계/누수(leakage) 위험

| 위험 | 설명 | 완화책 |
|---|---|---|
| 해역 편향 | 특정 항만 패턴에 과적합 | 단일 해역 결과로만 주장 범위 제한 |
| 시간 누수 | 미래 window 정보가 feature에 섞일 수 있음 | feature 생성 시 snapshot 기준 고정 |
| label circularity | baseline 규칙과 동일 기준으로 ML을 평가 | 별도 spatial/qualitative metric 병행 |
| class imbalance | 위험 이벤트가 희소함 | downsampling, class weighting, AUPRC 사용 |
| metadata sparsity | vessel type 등 결측 많음 | optional feature로만 사용 |

## 5. 성공 기준 또는 평가 기준

| 항목 | 기준 | 상태 |
|---|---|---|
| 데이터 품질 | 분석 가능한 연속 track segment 확보 | [확정] |
| feature 안정성 | CPA/TCPA 계산 오류 없이 배치 생성 | [확정] |
| 라벨 정의 명료성 | pseudo-label 기준이 문서화되고 재현 가능 | [확정] |
| ML 비교 타당성 | 최소 2개 모델과 baseline 비교 가능 | [확정] |

## 6. 리스크와 한계

| 항목 | 내용 | 상태 |
|---|---|---|
| pseudo-label 한계 | 실제 위험을 완전히 대표하지 못함 | [리스크] |
| AIS 품질 저하 | 누락/지연으로 trajectory reconstruction 실패 가능 | [리스크] |
| 장면 편향 | 혼잡 해역 중심 데이터는 일반화가 약함 | [리스크] |
| optional metadata 부족 | vessel type 기반 정교화가 제한될 수 있음 | [리스크] |

## 7. 핵심 결정사항

- [확정] ML target은 `pairwise future conflict proxy`로 제한한다.
- [확정] cell risk는 학습이 아니라 `spatial projection`으로 생성한다.
- [확정] baseline은 rule-based engine이며 ML은 비교안이다.
- [확정] 현재 코드 기준 pseudo-label은 향후 15분 내 realized minimum separation threshold로 설정한다.

## 8. 오픈 이슈

1. [추가 검증 필요] 실제 공개 AIS 소스의 샘플링 간격과 결측률은 어느 정도인가?
2. [추가 검증 필요] 선종, 선박 길이 등 metadata를 안정적으로 확보할 수 있는가?
3. [추가 검증 필요] 대상 해역 특성상 0.5 NM 기준이 너무 보수적이거나 느슨하지 않은가?

## 9. 다음 액션

1. 샘플 데이터 확보 후 raw field coverage와 결측률을 프로파일링한다.
2. 1차 전처리 파이프라인을 구현해 trajectory reconstruction 품질을 확인한다.
3. pairwise feature 테이블과 realized future separation label 생성 스크립트를 분리 구현한다.
4. baseline rule engine과 logistic regression 비교 실험을 준비한다.

설명 팁: 교수에게는 "ML을 하더라도 셀을 직접 학습하지 않고, pairwise risk를 예측한 뒤 공간 투영하는 구조라서 해석성과 구현 가능성을 모두 잡았다"라고 설명하면 설계 의도가 분명해진다.
