[English](README.md) | [简体中文](README_zh.md)

# Figure 4: Regional extreme-precipitation statistics

## Run

Run from the project root:

```bash
conda activate MET
python "src/Pic/Fig4_RegionalStatistics/Fig4.py"
```

Run Figure 3 first to generate the required input.

## Description

Summarize extreme-precipitation intensity for China, seven geographical regions and three river basins. Error bars are regional weighted means of grid-cell intermodel standard deviations, calculated with ddof=0.

## Inputs

Paths are relative to the project root.

| Data path  |  Role |
|---|---|
| `src/Pic/Fig3_ProjectionUncertainty/data/fig3_data.npz`  |  Input from another figure |
| `Data/China/cnmap.shp`  |  Geographic input |
| `Data/River/HuanghaiRiver_polygon.shp`  |  Geographic input |
| `Data/River/PearlRiver_polygon.shp`  |  Geographic input |
| `Data/River/YangtzeRiver_polygon.shp`  |  Geographic input |
| `src/Pic/Fig4_RegionalStatistics/data/fig4_regional_stats.csv`  |  Generated here, then read |

## Outputs

- `src/Pic/Fig4_RegionalStatistics/data/fig4_regional_stats.csv`

Image: `src/Pic/Fig4_RegionalStatistics/Fig4.jpg`.
