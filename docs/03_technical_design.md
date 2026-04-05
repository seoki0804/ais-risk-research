# 문서명
기술 설계서(Technical Design Document)

# 문서 목적
시스템 구조, 데이터 흐름, risk inference 흐름, heatmap/contour 생성 로직, speed scenario 처리 방식, 모듈/API 구조, MVP 기술 스택을 정의한다.

# 대상 독자
시스템 아키텍트, 데이터 엔지니어, ML 엔지니어, 백엔드 개발자, PM

# 작성 버전
v1.0

# 핵심 요약
- [확정] MVP 아키텍처는 `배치형 AIS 전처리 + 온디맨드 risk map 계산 + 경량 시각화 레이어`의 3층 구조다.
- [확정] heatmap은 `예측 상대위치 + pairwise severity + spatial kernel`을 이용해 셀 단위로 계산한다.
- [확정] safety contour는 `iso-risk threshold` 기반으로 생성하며, 안전 보장선이 아니라 `해석용 경계`로 정의한다.
- [합리적 가정] 초기 구현 스택은 `Python + DuckDB/Parquet + Polars/Pandas + PyProj/Shapely + Streamlit/Plotly`다.

## 1. 배경 및 문제 정의

본 시스템은 실시간 상용 항해 장비가 아니라, 공개 AIS 이력 데이터를 기반으로 위험도 공간 분포를 재구성하고 시각화하는 연구·MVP 시스템이다. 따라서 설계의 핵심은 `정확한 제어`가 아니라 `재현성`, `설명 가능성`, `개발 난이도 관리`, `시각 결과물 품질`이다.

기술 설계는 다음 질문에 답해야 한다.

1. AIS raw data를 어떻게 정제하고 저장할 것인가?
2. 특정 시점에 자선 중심 risk map을 어떻게 계산할 것인가?
3. 속력 시나리오별 결과를 어떻게 비교할 것인가?
4. UI가 이해 가능한 설명까지 제공하도록 어떤 중간 산출물을 유지할 것인가?

## 2. 목표와 비목표

### 2.1 목표

| 항목 | 설명 | 상태 |
|---|---|---|
| 아키텍처 단순성 | 1인 개발이 가능한 구성 유지 | [확정] |
| 계산 재현성 | 동일 입력에 동일 risk map 재현 | [확정] |
| 확장성 | baseline 후 ML/배치 분석 추가 가능 | [확정] |
| 시각화 적합성 | heatmap/contour 결과를 손쉽게 렌더링 가능 | [확정] |

### 2.2 비목표

| 항목 | 설명 | 상태 |
|---|---|---|
| 초저지연 스트리밍 | 실시간 분산 처리 설계는 초기 범위 밖 | [확정] |
| 대규모 분산 아키텍처 | Spark/Kafka 기반 설계는 과도함 | [확정] |
| 복합 조종 시뮬레이션 | heading/turn-rate 변화의 동적 제어 모델은 제외 | [확정] |

## 3. 핵심 가정과 제약

| 항목 | 값 | 상태 |
|---|---|---|
| 분석 좌표계 | 자선 중심 local ENU 좌표계 | [확정] |
| 예측 horizon | 15분 | [합리적 가정] |
| time step | 30초 | [합리적 가정] |
| 분석 반경 | 6 NM | [합리적 가정] |
| grid cell size | 250m | [합리적 가정] |
| kernel sigma | 200m | [합리적 가정] |
| speed scenarios | 0.8x, 1.0x, 1.2x of current SOG | [합리적 가정] |

## 4. 상세 설계/요구사항/방법론

### 4.1 시스템 개요

시스템은 5개 계층으로 구성한다.

1. `Ingestion Layer`: 공개 AIS 원본 수집 및 저장
2. `Preparation Layer`: 정제, 보간, trajectory reconstruction
3. `Risk Engine`: 상대운동 계산, pairwise severity, cell risk aggregation
4. `Serving Layer`: snapshot/query 기반 결과 생성 API 또는 함수
5. `Visualization Layer`: notebook/web dashboard 렌더링

### 4.2 전체 아키텍처

```text
[Public AIS Source]
        |
        v
[Raw Files: CSV/JSON]
        |
        v
[Preprocessing Pipeline]
- schema normalize
- timestamp sort
- invalid point filter
- interpolation / track reconstruction
        |
        v
[Curated Store: Parquet + DuckDB]
        |
        +-------------------------------+
        |                               |
        v                               v
[Scenario Engine]                 [Batch Evaluation]
- own ship selection              - event mining
- nearby vessel query             - metric computation
- relative motion                 - ablation jobs
- risk scoring
- heatmap/contour
        |
        v
[Result Objects]
- risk grid
- contour geometry
- top drivers
- metadata
        |
        v
[Notebook UI / Streamlit Dashboard]
```

### 4.3 데이터 수집/저장/전처리 흐름

| 단계 | 입력 | 처리 | 출력 |
|---|---|---|---|
| Ingest | raw AIS files | 컬럼 매핑, 포맷 정규화 | raw staging data |
| Clean | raw staging | 위경도, SOG/COG 범위 체크, 중복 제거 | cleaned AIS |
| Reconstruct | cleaned AIS | 시간 정렬, gap 기준 세그먼트화, 보간 | curated trajectories |
| Index | curated trajectories | 해역/시간/MMSI 인덱스 | queryable store |

권장 저장 방식:

- Raw: 압축 CSV/JSON 원본 보존
- Curated: Parquet partitioning by `date` and optionally `region`
- Query: DuckDB view 또는 local SQLite metadata

### 4.4 모델 추론 흐름

```text
Input(snapshot):
  own_ship_id, timestamp, scenario_speed_multiplier

1. own ship state 조회
2. 반경 내 target ships 조회
3. own ship / target ship 상태 벡터 구성
4. scenario speed 적용
5. relative motion prediction over horizon
6. pairwise severity 계산
7. grid cell별 spatial kernel 누적
8. contour extraction
9. top contributing vessels/factors 산출
10. UI render payload 반환
```

### 4.5 heatmap 생성 로직 개요

기본 로직은 `예측된 상대위치의 위험 강도`를 그리드에 투영하는 방식이다.

1. 자선과 타선의 현재 상태를 벡터화한다.
2. 시나리오 속력을 자선에 적용한다.
3. `0~15분` horizon 동안 상대위치를 예측한다.
4. 각 시간 스텝에서 pairwise severity를 계산한다.
5. severity를 해당 상대위치 인근 셀로 `Gaussian-like kernel`로 확산시킨다.
6. 셀별 최대값 또는 제한된 누적값을 취해 risk map을 만든다.

MVP baseline:

- 집계 방식: `cell risk = max contribution`
- 이유: 해석이 쉽고 threshold tuning이 단순함

확장안:

- 집계 방식: `probabilistic union` 또는 `top-k weighted sum`
- 이유: 여러 중간위험 선박의 누적 효과 반영 가능

### 4.6 safety contour 생성 방식 개요

| 항목 | 설계 |
|---|---|
| 입력 | 정규화된 risk grid |
| 방식 | 지정 임계값 이상의 셀을 연결하여 iso-risk boundary 생성 |
| 기본 threshold | 0.35(안전 경계), 0.65(고위험 경계) [합리적 가정] |
| 구현 후보 | marching squares 또는 contour extraction from raster |
| 출력 | polygon 또는 polyline geometry |

주의:

- contour는 법적 "안전 보장선"이 아니다.
- contour는 현재 가정과 시나리오 하에서 `상대적으로 위험도가 상승하는 경계`를 나타내는 시각화 도구다.

### 4.7 속력 시나리오 처리 방식

| 시나리오 | 정의 | 목적 |
|---|---|---|
| Baseline | 현재 SOG | 현재 상태 기준 위험도 |
| Slowdown | 0.8 x 현재 SOG | 감속 시 위험 공간 변화 확인 |
| Speed-up | 1.2 x 현재 SOG | 증속 시 위험 공간 변화 확인 |

처리 규칙:

- [확정] 초기 MVP에서는 `자선 속력만 변경`한다.
- [확정] 자선의 heading/COG는 고정한다.
- [확정] 타선은 현재 속력/침로를 유지하는 `constant velocity` 가정을 사용한다.
- [리스크] 실제 운항에서는 감속에 따른 의도 변화와 타선 반응이 반영되지 않는다.

### 4.8 모듈 구조 또는 API 구조

#### 모듈 구조

| 모듈 | 책임 |
|---|---|
| `data_ingest` | raw AIS 적재, 포맷 변환 |
| `data_cleaning` | 이상치 제거, 결측 처리 |
| `trajectory_builder` | track segmentation, interpolation |
| `scenario_engine` | own ship scenario state 생성 |
| `relative_motion` | distance/bearing/CPA/TCPA 계산 |
| `risk_scoring` | pairwise severity, cell aggregation |
| `contour_builder` | contour extraction |
| `explanation` | top contributors, factor summary |
| `ui_adapter` | dashboard payload 생성 |

#### API 예시

| 메서드 | 경로 | 설명 |
|---|---|---|
| `GET` | `/ships` | available own ship candidates 조회 |
| `GET` | `/snapshots` | 특정 시점 후보 조회 |
| `POST` | `/risk-map` | scenario 기반 risk map 계산 |
| `POST` | `/compare-scenarios` | 3개 scenario 일괄 계산 |
| `POST` | `/export` | PNG/JSON export |

초기 MVP는 API 없이 Python 함수 호출 기반으로도 충분하다. API는 웹 데모 단계에서만 추가해도 된다.

### 4.9 유지보수/확장성 고려사항

| 항목 | 고려사항 |
|---|---|
| 파라미터 관리 | threshold, weights, horizon을 config 파일로 분리 |
| 재현성 | 데이터 버전과 파라미터 버전 기록 |
| 계산량 | 반경 기반 타선 조회, 격자 해상도 제한 |
| 확장성 | ML scoring module을 plug-in처럼 교체 가능하게 설계 |
| 테스트 | 수학 함수와 geometry 함수에 단위 테스트 추가 |

### 4.10 MVP 기술 스택 제안

| 영역 | 제안 스택 | 이유 |
|---|---|---|
| 언어 | Python | 데이터/지리 연산 생태계 풍부 |
| 데이터 처리 | Polars 또는 Pandas | 시계열/테이블 조작 용이 |
| 저장 | Parquet + DuckDB | 로컬 분석 친화적, 빠른 query |
| 좌표/지오메트리 | PyProj, Shapely, GeoPandas | 좌표 변환과 contour 처리 용이 |
| 수치 계산 | NumPy, SciPy | 벡터 연산과 kernel 처리 |
| 시각화 | Plotly, PyDeck, Matplotlib | 지도/heatmap/contour 렌더링 |
| 웹 데모 | Streamlit | 1인 MVP에 적합 |
| 실험 관리 | Jupyter + YAML config | 초기 연구/시각화 반복이 쉬움 |

## 5. 성공 기준 또는 평가 기준

| 범주 | 기준 | 상태 |
|---|---|---|
| 아키텍처 실현성 | 로컬 환경에서 전체 pipeline 실행 가능 | [확정] |
| 재현성 | 동일 파라미터와 데이터에 결과 일관 | [확정] |
| 확장성 | baseline 후 ML module 추가 가능 | [확정] |
| 시각화 적합성 | heatmap과 contour가 노트북/웹에서 모두 렌더링 가능 | [확정] |

## 6. 리스크와 한계

| 항목 | 내용 | 상태 |
|---|---|---|
| data volume | 4주 AIS도 해역에 따라 커질 수 있음 | [리스크] |
| geometry complexity | contour extraction이 noisy할 수 있음 | [리스크] |
| constant velocity assumption | 실제 기동 변화를 반영하지 못함 | [리스크] |
| notebook-web 이중 구현 | 일정이 부족하면 둘 다 어설플 수 있음 | [리스크] |

## 7. 핵심 결정사항

- [확정] MVP는 `배치 전처리 + 온디맨드 inference` 구조를 사용한다.
- [확정] risk map 생성은 `relative motion prediction + spatial kernel` 기반으로 구현한다.
- [확정] contour는 `iso-risk visualization layer`로 정의한다.
- [합리적 가정] 초기 스택은 Python 중심 경량 스택으로 제한한다.

## 8. 오픈 이슈

1. [추가 검증 필요] 해역 규모에 따라 DuckDB 단독으로 충분한가?
2. [추가 검증 필요] contour extraction의 시각 품질을 위해 smoothing 단계가 필요한가?
3. [추가 검증 필요] 웹 데모를 Streamlit로 끝낼지, 추후 API/프론트 분리를 할지?

## 9. 다음 액션

1. 데이터 및 모델 설계서에서 raw fields와 전처리 규칙을 잠근다.
2. 위험도 정의서에서 pairwise severity 수식과 contour threshold를 수치화한다.
3. 첫 구현에서는 notebook 기반 pipeline을 우선 완성한 뒤 웹으로 이행한다.

설명 팁: 실무자에게는 "분산 시스템보다, 재현 가능한 로컬 분석 엔진과 설명 가능한 시각화 파이프라인을 우선 설계했다"라고 설명하면 현실성이 높게 전달된다.
