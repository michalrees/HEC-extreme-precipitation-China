[English](README.md) | [简体中文](README_zh.md)

# Figure 3: Future projections and intermodel uncertainty

## Run

Run from the project root:

```bash
conda activate MET
python "src/Pic/Fig3_ProjectionUncertainty/Fig3.py"
```

## Description

Plot ensemble means, standard deviations and variances of 2021–2050 R95mm_intensity. Standard deviations use ddof=0; regional statistics use cosine-of-latitude weights.

## Inputs

Paths are relative to the project root.

| Data path  |  Role |
|---|---|
| `Output/Mode/indices/Scenariomerged/MULTI_MODEL-ssp126-ALL_INDICES.nc`  |  Model input |
| `Output/Mode/indices/Scenariomerged/MULTI_MODEL-ssp245-ALL_INDICES.nc`  |  Model input |
| `Output/Mode/indices/Scenariomerged/MULTI_MODEL-ssp585-ALL_INDICES.nc`  |  Model input |
| `Data/China/cnmap.shp`  |  Geographic input |
| `src/Pic/Fig3_ProjectionUncertainty/data/fig3_data.npz`  |  Generated here, then read |

## Outputs

- `src/Pic/Fig3_ProjectionUncertainty/data/fig3_stats.csv`
- `src/Pic/Fig3_ProjectionUncertainty/data/fig3_levels.csv`

Image: `src/Pic/Fig3_ProjectionUncertainty/Fig3.jpg`.
