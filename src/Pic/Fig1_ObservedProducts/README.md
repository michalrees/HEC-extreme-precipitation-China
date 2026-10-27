[English](README.md) | [简体中文](README_zh.md)

# Figure 1: Observed-product climatologies

## Run

Run from the project root:

```bash
conda activate MET
python "src/Pic/Fig1_ObservedProducts/Fig1.py"
```

## Description

Compare 1981–2010 PrecipVar and R95mm_intensity climatologies from four observational products. Regional means use the Chinese land mask and cosine-of-latitude weights; HEC uses observational standard errors.

## Inputs

Paths are relative to the project root.

| Data path  |  Role |
|---|---|
| `Output/Obs/indices/CN05-OBS-IntensityAndPrecipVar-1961-2023.nc`  |  Observational input |
| `Output/Obs/indices/HGCDC-OBS-IntensityAndPrecipVar-1961-2022.nc`  |  Observational input |
| `Output/Obs/indices/CHM_PRE_V2-OBS-IntensityAndPrecipVar-1961-2024.nc`  |  Observational input |
| `Output/Obs/indices/CPC-OBS-IntensityAndPrecipVar-1979-2025.nc`  |  Observational input |
| `Data/China/cnmap.shp`  |  Geographic input |

## Outputs

- `src/Pic/Fig1_ObservedProducts/data/fig1_stats.csv`

Image: `src/Pic/Fig1_ObservedProducts/Fig1.jpg`.
