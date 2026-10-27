# Figure 8: Constraint adjustments around mountain ranges

[English](README.md) | [中文](README_zh.md)

## Run

Run from the project root:

```bash
conda activate MET
python "src/Pic/Fig8_MountainAdjustment/Fig8.py"
```

## Description

Plot posterior-minus-prior adjustments under SSP2-4.5 using a color range shared across three scenarios. Default plotting uses the existing WGS84 mountain data. Adjustment > 0 is the fraction of valid grid cells with positive adjustments; cells with p ≥ 0.05 are shown in gray.

## Inputs

Paths are relative to the project root.

| Data path  |  Role |
|---|---|
| `Output/EC/China/HEC_ssp126_PrecipVar_to_R95mm_intensity.nc`  |  HEC input |
| `Output/EC/China/HEC_ssp245_PrecipVar_to_R95mm_intensity.nc`  |  HEC input |
| `Output/EC/China/HEC_ssp585_PrecipVar_to_R95mm_intensity.nc`  |  HEC input |
| `Data/China/cnmap.shp`  |  Geographic input |
| `src/Pic/Fig8_MountainAdjustment/data/CN_MountainRanges_WGS84.shp`  |  Geographic input |

## Outputs

- `src/Pic/Fig8_MountainAdjustment/data/fig8_stats.csv`

Image: `src/Pic/Fig8_MountainAdjustment/Fig8.jpg`.
