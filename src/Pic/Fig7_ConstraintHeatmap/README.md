# Figure 7: Regional constraint heatmap

[English](README.md) | [中文](README_zh.md)

## Run

Run from the project root:

```bash
conda activate MET
python "src/Pic/Fig7_ConstraintHeatmap/Fig7.py"
```

## Description

Summarize correlation, uncertainty reduction and constraint adjustments for China, seven regions and three basins. Statistics use valid cells with p < 0.05 and r ≥ 0.5 and cosine-of-latitude weights; CSV std values describe regional spatial dispersion.

## Inputs

Paths are relative to the project root.

| Data path  |  Role |
|---|---|
| `Output/EC/China/HEC_ssp126_PrecipVar_to_R95mm_intensity.nc`  |  HEC input |
| `Output/EC/China/HEC_ssp245_PrecipVar_to_R95mm_intensity.nc`  |  HEC input |
| `Output/EC/China/HEC_ssp585_PrecipVar_to_R95mm_intensity.nc`  |  HEC input |
| `Data/River/HuanghaiRiver_polygon.shp`  |  Geographic input |
| `Data/River/PearlRiver_polygon.shp`  |  Geographic input |
| `Data/River/YangtzeRiver_polygon.shp`  |  Geographic input |
| `src/Pic/Fig7_ConstraintHeatmap/data/fig7_regional_stats.csv`  |  Generated here, then read |

## Outputs

- `src/Pic/Fig7_ConstraintHeatmap/data/fig7_regional_stats.csv`

Image: `src/Pic/Fig7_ConstraintHeatmap/Fig7.jpg`.
