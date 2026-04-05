# Three-Region Heatmap/Scenario Evidence Panels

Each panel links one representative heatmap+contour figure with region-level error taxonomy and calibration evidence.

## Panel: houston

- model / F1 / ECE: `hgbt` / `0.8286` / `0.0229`
- FP / FN (seed-42 taxonomy snapshot): `1` / `11`
- calibration note: Well-calibrated probability profile (ECE <= 0.03).
- error interpretation: FN pressure dominates; discuss missed-risk implications.
- reliability figure: `/Users/seoki/Desktop/research/outputs/2026-04-04_reliability_report_10seed/houston_recommended_reliability.png`
- heatmap+contour figure: `/Users/seoki/Desktop/research/outputs/2026-04-05_uncertainty_contour_panel_10seed/houston_report_figure.svg`
- representative case: `2023-10-09T20-26-11Z__368216230__hgbt` (own_mmsi `368216230`, timestamp `2023-10-09T20:26:11Z`, target_count `2`, max_risk_mean `0.9538`)

## Panel: nola

- model / F1 / ECE: `hgbt` / `0.6015` / `0.0237`
- FP / FN (seed-42 taxonomy snapshot): `43` / `10`
- calibration note: Well-calibrated probability profile (ECE <= 0.03).
- error interpretation: FP pressure dominates; discuss alert fatigue tradeoff.
- reliability figure: `/Users/seoki/Desktop/research/outputs/2026-04-04_reliability_report_10seed/nola_recommended_reliability.png`
- heatmap+contour figure: `/Users/seoki/Desktop/research/outputs/2026-04-05_uncertainty_contour_panel_10seed/nola_report_figure.svg`
- representative case: `2023-08-09T04-02-05Z__368102290__hgbt` (own_mmsi `368102290`, timestamp `2023-08-09T04:02:05Z`, target_count `1`, max_risk_mean `0.6402`)

## Panel: seattle

- model / F1 / ECE: `extra_trees` / `0.8174` / `0.0282`
- FP / FN (seed-42 taxonomy snapshot): `5` / `15`
- calibration note: Well-calibrated probability profile (ECE <= 0.03).
- error interpretation: FN pressure dominates; discuss missed-risk implications.
- reliability figure: `/Users/seoki/Desktop/research/outputs/2026-04-04_reliability_report_10seed/seattle_recommended_reliability.png`
- heatmap+contour figure: `/Users/seoki/Desktop/research/outputs/2026-04-05_uncertainty_contour_panel_10seed/seattle_report_figure.svg`
- representative case: `2023-08-08T19-49-32Z__366929710__extra_trees` (own_mmsi `366929710`, timestamp `2023-08-08T19:49:32Z`, target_count `1`, max_risk_mean `0.9462`)
