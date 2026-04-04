# All Models Multi-Area Leaderboard

| Dataset | Model | Family | Status | Positives | F1 | AUROC | ECE | Notes |
|---|---|---|---|---:|---:|---:|---:|---|
| houston_pooled_pairwise | cnn_focal_temp | regional_raster_cnn | completed | 40 | 0.8315 | 0.9910 | 0.1458 | loss=focal; temperature_scaled |
| houston_pooled_pairwise | hgbt | tabular | completed | 40 | 0.8286 | 0.9833 | 0.0229 |  |
| houston_pooled_pairwise | cnn_focal | regional_raster_cnn | completed | 40 | 0.8148 | 0.9910 | 0.2620 | loss=focal |
| houston_pooled_pairwise | cnn_weighted | regional_raster_cnn | completed | 40 | 0.7952 | 0.9909 | 0.1896 | loss=weighted_bce |
| houston_pooled_pairwise | cnn_weighted_temp | regional_raster_cnn | completed | 40 | 0.7952 | 0.9909 | 0.1896 | loss=weighted_bce; temperature_scaled |
| houston_pooled_pairwise | torch_mlp | tabular | completed | 40 | 0.7595 | 0.9768 | 0.2342 |  |
| houston_pooled_pairwise | logreg | tabular | completed | 40 | 0.7317 | 0.9564 | 0.0716 |  |
| houston_pooled_pairwise | rule_score | tabular | completed | 40 | 0.4138 | 0.9052 | 0.1718 |  |
| nola_pooled_pairwise | hgbt | tabular | completed | 50 | 0.6015 | 0.9707 | 0.0237 |  |
| nola_pooled_pairwise | torch_mlp | tabular | completed | 50 | 0.4533 | 0.9064 | 0.1958 |  |
| nola_pooled_pairwise | rule_score | tabular | completed | 50 | 0.4455 | 0.9735 | 0.1412 |  |
| nola_pooled_pairwise | cnn_weighted | regional_raster_cnn | completed | 50 | 0.4432 | 0.9624 | 0.1019 | loss=weighted_bce |
| nola_pooled_pairwise | cnn_focal | regional_raster_cnn | completed | 50 | 0.4368 | 0.9628 | 0.1792 | loss=focal |
| nola_pooled_pairwise | cnn_weighted_temp | regional_raster_cnn | completed | 50 | 0.4368 | 0.9624 | 0.0917 | loss=weighted_bce; temperature_scaled |
| nola_pooled_pairwise | cnn_focal_temp | regional_raster_cnn | completed | 50 | 0.4260 | 0.9628 | 0.0883 | loss=focal; temperature_scaled |
| nola_pooled_pairwise | logreg | tabular | completed | 50 | 0.4248 | 0.9204 | 0.0531 |  |
| seattle_pooled_pairwise | cnn_focal | regional_raster_cnn | completed | 59 | 0.8364 | 0.9609 | 0.2791 | loss=focal |
| seattle_pooled_pairwise | cnn_focal_temp | regional_raster_cnn | completed | 59 | 0.8269 | 0.9609 | 0.2074 | loss=focal; temperature_scaled |
| seattle_pooled_pairwise | cnn_weighted | regional_raster_cnn | completed | 59 | 0.8246 | 0.9602 | 0.3093 | loss=weighted_bce |
| seattle_pooled_pairwise | logreg | tabular | completed | 59 | 0.8214 | 0.9679 | 0.0482 |  |
| seattle_pooled_pairwise | cnn_weighted_temp | regional_raster_cnn | completed | 59 | 0.8099 | 0.9602 | 0.3140 | loss=weighted_bce; temperature_scaled |
| seattle_pooled_pairwise | torch_mlp | tabular | completed | 59 | 0.7818 | 0.9437 | 0.1895 |  |
| seattle_pooled_pairwise | hgbt | tabular | completed | 59 | 0.7647 | 0.9622 | 0.0419 |  |
| seattle_pooled_pairwise | rule_score | tabular | completed | 59 | 0.5714 | 0.9006 | 0.1521 |  |
