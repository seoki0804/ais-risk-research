# 문서명
공개 AIS 데이터 소스 후보 정리(Public AIS Source Shortlist)

# 문서 목적
실데이터 수집을 시작하기 전에 실제 프로젝트에 적합한 공개 AIS 소스를 후보군으로 정리하고, own-ship-centric 검증에 적합한지 여부를 판단하는 기준을 제공한다.

# 대상 독자
연구자, 데이터사이언티스트, 데이터 엔지니어, 지도교수

# 작성 버전
v1.0

# 핵심 요약
- [확정] 첫 실데이터는 `stable vessel identifier`, `raw point/track level`, `area/time filtering 가능`, `license 명확`의 네 조건을 먼저 본다.
- [확정] 본 프로젝트의 1순위는 `historical AIS CSV 또는 point data`이며, density plot이나 aggregated 통계는 보조 자료에 가깝다.
- [합리적 가정] 첫 operational dataset 후보로는 `Danish Maritime Authority historical AIS` 또는 `NOAA AccessAIS`가 가장 실용적이다.
- [추가 검증 필요] 한국 공공데이터의 AIS 동적정보는 매우 유용할 수 있으나, MMSI masking이 own ship 추적에 치명적이지 않은지 먼저 확인해야 한다.

## 1. 배경 및 문제 정의

공개 AIS라고 해서 모두 이 프로젝트에 적합한 것은 아니다. own-ship-centric spatial risk 검증에는 다음이 필수다.

1. 동일 선박을 시간축으로 이어서 볼 수 있는 식별자
2. 위치, 속력, 침로 수준의 raw point 또는 track 데이터
3. 특정 해역/기간을 선택할 수 있는 유연성
4. 재사용 가능한 이용 조건

## 2. 목표와 비목표

### 2.1 목표

| 항목 | 설명 | 상태 |
|---|---|---|
| SRC-01 | 첫 dataset 후보를 2~3개로 압축 | [확정] |
| SRC-02 | own ship 추적 적합성 기준을 명시 | [확정] |
| SRC-03 | source 선택 리스크를 사전에 드러냄 | [확정] |

### 2.2 비목표

| 항목 | 설명 | 상태 |
|---|---|---|
| 모든 공개 AIS source 열거 | 전체 목록화가 목적은 아님 | [확정] |
| 상용 API 추천 | 비공개/유료 enterprise feed는 제외 | [확정] |

## 3. 핵심 가정과 제약

| 항목 | 내용 | 상태 |
|---|---|---|
| 프로젝트 범위 | 공개 AIS only | [확정] |
| 분석 방식 | own-ship-centric repeated validation | [확정] |
| 필요 필드 | timestamp, lat/lon, sog, cog, vessel id | [확정] |
| 한국 데이터 선호 | 있으면 좋지만 필수는 아님 | [합리적 가정] |

## 4. 상세 설계/요구사항/방법론

### 4.1 소스 평가 기준

| 기준 | 설명 | 중요도 |
|---|---|---|
| ID stability | MMSI 또는 stable anonymized ID 존재 여부 | Must |
| Raw trajectory suitability | point/track level 데이터인지 | Must |
| Area/time selectivity | 원하는 해역과 기간을 잘라 받을 수 있는지 | Must |
| License clarity | 재사용 조건이 명확한지 | Must |
| Metadata richness | vessel type 등 보조 메타데이터 존재 여부 | Should |
| Retrieval friction | 다운로드/신청 절차가 과도하지 않은지 | Should |

### 4.2 후보 소스 비교

| 소스 | 장점 | 한계 | own ship 적합성 | 상태 |
|---|---|---|---|---|
| NOAA AccessAIS | 사용자 정의 geography/time 기간으로 U.S. vessel traffic point data를 다운로드할 수 있음 | 미국/미국 영해 중심 | 높음 | [합리적 가정] |
| Danish Maritime Authority historical AIS | historical AIS CSV를 무료로 제공한다고 명시 | 덴마크 수역 중심, 파일 구조 사전 확인 필요 | 높음 | [합리적 가정] |
| 해양수산부 선박 AIS 동적정보 | 한국 공공데이터, 무료, 동적 정보 제공 | MMSI가 특수문자로 대체된다고 명시, 좌표 스케일 변환 필요 | 중간 이하 | [추가 검증 필요] |
| AISHub API | XML/JSON/CSV API 제공 | aggregated feed 접근은 contributor 조건과 이용 조건 확인 필요 | 낮음 | [추가 검증 필요] |

### 4.3 1순위 추천

| 순위 | 소스 | 이유 |
|---|---|---|
| 1 | Danish Maritime Authority historical AIS | free historical CSV, raw AIS 중심, own ship repeated validation에 적합할 가능성이 높음 |
| 2 | NOAA AccessAIS | geography/time filtering이 쉬워 MVP dataset을 빠르게 만들기 좋음 |
| 3 | 해양수산부 선박 AIS 동적정보 | 한국 해역 장점은 있으나 MMSI masking 적합성 검증이 선행돼야 함 |

### 4.4 소스별 운영 메모

#### A. Danish Maritime Authority historical AIS

- [확정] 공식 페이지는 historical AIS data를 free CSV zip으로 접근 가능하다고 명시한다.
- [확정] 무료 historical AIS와 별도로 online raw proxy access는 유료다.
- [합리적 가정] 첫 실험용 dataset으로 가장 실용적이다.
- [추가 검증 필요] CSV 스키마와 선종/heading coverage는 실제 다운로드 후 확인해야 한다.

공식 근거:

- [AIS data | dma.dk](https://www.dma.dk/safety-at-sea/navigational-information/ais-data)
- [AIS data management policy | dma.dk](https://www.dma.dk/safety-at-sea/navigational-information/ais-data/ais-data-management-policy-)

#### B. NOAA AccessAIS

- [확정] NOAA Digital Coast의 AccessAIS는 user-defined geography and time period 기반 다운로드를 지원한다고 안내한다.
- [합리적 가정] 특정 harbor 또는 coastal lane을 잘라 MVP용 dataset을 빠르게 만들기 좋다.
- [추가 검증 필요] 현재 제공 연도 범위와 세부 컬럼은 실제 tool export 후 manifest에 기록해야 한다.

공식 근거:

- [AccessAIS | NOAA Digital Coast](https://coast.noaa.gov/digitalcoast/tools/ais.html)

#### C. 해양수산부 선박 AIS 동적정보

- [확정] 공공데이터포털 설명상 동적정보를 무료 다운로드할 수 있다.
- [확정] 페이지 설명에 따르면 개별 선박 식별정보(MMSI)는 특수문자로 대체된다.
- [확정] 위경도 값은 `/60,000` 변환이 필요하다고 명시되어 있다.
- [리스크] MMSI masking이 stable identifier를 보장하지 않으면 own-ship-centric 반복 검증에 부적합하다.

공식 근거:

- [해양수산부_선박 AIS 동적정보_20220101 | 공공데이터포털](https://www.data.go.kr/data/15129186/fileData.do)

#### D. AISHub

- [확정] API 자체는 XML/JSON/CSV 형식을 제공한다고 안내한다.
- [확정] aggregated feed 접근은 contributor 품질 요건을 충족해야 한다고 안내한다.
- [리스크] contributor requirement 때문에 reproducible public dataset source로는 부적합할 수 있다.

공식 근거:

- [AIS data API | AISHub](https://www.aishub.net/api)
- [Join us and get access to worldwide AIS data stream | AISHub](https://www.aishub.net/join-us)

## 5. 성공 기준 또는 평가 기준

| 항목 | 기준 | 상태 |
|---|---|---|
| source shortlist | 2~3개 source로 압축 | [확정] |
| first pick | 첫 수집 source 1개 결정 | [확정] |
| manifest readiness | source, license, field note를 기록할 수 있음 | [확정] |

## 6. 리스크와 한계

| 항목 | 내용 | 상태 |
|---|---|---|
| MMSI masking | 한국 공공데이터 동적정보의 가장 큰 리스크 | [리스크] |
| schema drift | source마다 컬럼 구조가 다를 수 있음 | [리스크] |
| region mismatch | 관심 해역과 source coverage가 다를 수 있음 | [리스크] |
| retrieval friction | 웹 기반 download tool은 자동화가 제한될 수 있음 | [리스크] |

## 7. 핵심 결정사항

- [확정] density plot이나 aggregated count 데이터만으로는 학습/검증을 하지 않는다.
- [확정] 첫 dataset은 raw point/track 중심 source에서 선택한다.
- [확정] source 선정 시 `stable identifier`를 최우선 조건으로 둔다.

## 8. 오픈 이슈

1. [추가 검증 필요] DMA historical CSV의 컬럼 구조와 용량
2. [추가 검증 필요] AccessAIS export의 최신 연도 범위
3. [추가 검증 필요] 한국 공공데이터의 masked MMSI가 세션 내 stable한지

## 9. 다음 액션

1. DMA 또는 AccessAIS 중 1개를 첫 dataset source로 고른다.
2. `source_probe_cli`로 소스 가용성(HTTP status/restricted/network_error)을 먼저 점검한다.
3. 다운로드 직후 `data/manifests/`에 dataset manifest를 남긴다.
4. `schema_probe_cli`로 실제 스키마를 먼저 점검한다.
5. stable identifier 여부를 확인한 뒤에만 own ship candidate 추천으로 넘어간다.

설명 팁: 심사자에게는 "공개 AIS를 아무거나 쓰지 않고, own ship repeated validation에 필요한 stable identifier부터 본다"라고 설명하는 편이 설득력이 높다.
