# Supplementary Transfer-Uncertainty Table

This table is intended for the external-validity supplement and reports all transfer directions.

| Source | Target | Model | Fixed-th ΔF1 | CI95(low,high) | Retune Gain | Best Target-th | Retuned ΔF1 |
|---|---|---|---:|---:|---:|---:|---:|
| houston | nola | hgbt | -0.1383 | (-0.1631, 0.8807) | 0.0032 | 0.4500 | -0.1351 |
| houston | seattle | hgbt | -0.2103 | (-0.2479, 0.8162) | 0.0793 | 0.9400 | -0.1310 |
| nola | houston | hgbt | 0.3213 | (0.1842, 0.4764) | 0.1055 | 0.6200 | 0.4269 |
| nola | seattle | hgbt | 0.4439 | (0.3089, 0.5963) | 0.0178 | 0.4200 | 0.4617 |
| seattle | houston | extra_trees | 0.0021 | (-0.1068, 0.1153) | 0.0028 | 0.4700 | 0.0050 |
| seattle | nola | extra_trees | 0.0488 | (-0.0488, 0.1422) | 0.0066 | 0.4400 | 0.0554 |

Main-text citation sentence:
See Supplementary Table S-Transfer-1 for fixed-threshold transfer ΔF1, bootstrap CI95, and target-threshold retune gains across all directions.
