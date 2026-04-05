# First Public AIS Dataset Manifest Template

## 0. 기본 정보

- dataset_id:
- 작성일:
- 작성자:
- source name:
- source URL:
- license / terms URL:
- source type: `historical CSV` / `clip-and-ship point data` / `API`
- status: `[확정]` / `[합리적 가정]` / `[추가 검증 필요]`

## 1. 왜 이 소스를 고르는가

- 프로젝트 적합성:
- own ship 추적 적합성:
- 포기한 대안:

## 2. 커버리지

| 항목 | 값 |
|---|---|
| 해역 |  |
| bbox |  |
| 시작 시각 |  |
| 종료 시각 |  |
| raw 파일 개수 |  |
| raw 총 용량 |  |

## 3. 스키마 점검

| 항목 | 결과 |
|---|---|
| vessel id column |  |
| timestamp column |  |
| lat/lon column |  |
| sog/cog column |  |
| heading availability |  |
| vessel_type availability |  |
| stable identifier 여부 |  |

## 4. 전처리 계획

| 항목 | 값 |
|---|---|
| source preset |  |
| column override |  |
| vessel type filter |  |
| bbox filter |  |
| time filter |  |
| split gap min |  |
| max interp gap min |  |
| step sec |  |

## 5. 리스크 메모

- [리스크]
- [추가 검증 필요]

## 6. 실행 기록

```bash
# schema probe

# preprocess

# trajectory

# workflow
```

## 7. 산출물 경로

- raw path:
- curated path:
- tracks path:
- schema probe path:
- workflow summary path:

## 8. 다음 액션

1. 
2. 
3. 
