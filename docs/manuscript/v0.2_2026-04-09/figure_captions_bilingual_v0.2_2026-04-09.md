# Figure Captions v0.2 (KOR/ENG)

## Figure 1
- Path: `./figure_1_model_family_comparison.svg`
- KOR: 해역별 최고 성능 모델 패밀리(F1) 비교. 각 해역에서 tabular과 regional_raster_cnn의 최고 성능 모델을 비교해 기준 모델 채택 근거를 제시한다.
- ENG: Region-wise comparison of best-performing model families (F1). For each region, the best tabular and best regional_raster_cnn candidates are contrasted to justify final model-family selection.

## Figure 2
- Path: `./figure_2_transfer_delta_f1_heatmap.svg`
- KOR: 교차 해역 전이 ΔF1 히트맵. 행은 source, 열은 target이며 음수 구간은 도메인 시프트 취약 구간을 의미한다.
- ENG: Cross-region transfer ΔF1 heatmap. Rows indicate source regions and columns indicate target regions; negative cells indicate domain-shift-sensitive transfer routes.

## Figure 3
- Path: `./figure_3_pipeline_overview.svg`
- KOR: 데이터 수집부터 모델 학습, 전이 검증, 원고 산출물 생성까지의 엔드투엔드 연구 파이프라인.
- ENG: End-to-end research pipeline from data curation to model training, transfer evaluation, and manuscript-ready asset generation.

## Figure 4
- Path: `./figure_4_threshold_utility_curve.svg`
- KOR: FN 가중치(5) 중심 운영 비용 프로파일에서 임계값 변화에 따른 정규화 비용 곡선과 governed/utility-opt 운영점을 비교한다.
- ENG: Normalized cost-vs-threshold curves under FN-heavy profile (FN=5, FP=1) with governed and utility-opt operating points.

## Scenario Visuals (Existing)
- Houston KOR: Houston 시나리오 위험도 히트맵/등고선 결과로 고위험 구역의 공간 집중을 보여준다.
- Houston ENG: Houston scenario heatmap/contour output showing spatial concentration of high-risk zones.
- NOLA KOR: NOLA 시나리오에서 전이 적용 후 위험도 분포 변화를 비교한다.
- NOLA ENG: NOLA scenario visualization comparing risk distribution shifts under transferred models.
- Seattle KOR: Seattle 시나리오의 경계 조건에서 모델 보정 품질과 위험도 표현 일관성을 점검한다.
- Seattle ENG: Seattle scenario used to inspect calibration quality and consistency of risk representation under boundary conditions.
