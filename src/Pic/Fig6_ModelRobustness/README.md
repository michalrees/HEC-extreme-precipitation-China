[English](README.md) | [简体中文](README_zh.md)

# Figure 6: Model-ensemble robustness

## Run

Run from the project root:

```bash
conda activate MET
python "src/Pic/Fig6_ModelRobustness/Fig6.py"
# Rebuild caches after changing upstream model inputs
python "src/Pic/Fig6_ModelRobustness/Fig6.py" --force-regrid
# Check computational consistency
python "src/Pic/Fig6_ModelRobustness/Fig6.py" --selftest
```

## Description

Compare 19 leave-one-model-out and four leave-one-family-out cases using changes in national mean correlation, uncertainty reduction and correlation-field RMSD. Historical and future periods are 1981–2010 and 2021–2050; observational errors use standard errors.

## Inputs

Paths are relative to the project root.

| Data path  |  Role |
|---|---|
| `Output/Obs/indices/CN05-OBS-IntensityAndPrecipVar-1961-2023.nc`  |  Observational input |
| `Output/Obs/indices/HGCDC-OBS-IntensityAndPrecipVar-1961-2022.nc`  |  Observational input |
| `Output/Obs/indices/CHM_PRE_V2-OBS-IntensityAndPrecipVar-1961-2024.nc`  |  Observational input |
| `Output/Obs/indices/CPC-OBS-IntensityAndPrecipVar-1979-2025.nc`  |  Observational input |
| `Output/Mode/indices/Scenariomerged/MULTI_MODEL-ssp126-ALL_INDICES.nc`  |  Model input |
| `Output/Mode/indices/Scenariomerged/MULTI_MODEL-ssp245-ALL_INDICES.nc`  |  Model input |
| `Output/Mode/indices/Scenariomerged/MULTI_MODEL-ssp585-ALL_INDICES.nc`  |  Model input |
| `Output/EC/China/HEC_ssp126_PrecipVar_to_R95mm_intensity.nc`  |  Baseline validation |
| `Output/EC/China/HEC_ssp245_PrecipVar_to_R95mm_intensity.nc`  |  Baseline validation |
| `Output/EC/China/HEC_ssp585_PrecipVar_to_R95mm_intensity.nc`  |  Baseline validation |
| `Data/River/HuanghaiRiver_polygon.shp`  |  Geographic input |
| `Data/River/PearlRiver_polygon.shp`  |  Geographic input |
| `Data/River/YangtzeRiver_polygon.shp`  |  Geographic input |
| `src/Pic/Fig6_ModelRobustness/data/map_similarity.csv`  |  Generated here, then read |
| `src/Pic/Fig6_ModelRobustness/data/cache/regrid_ssp126_ACCESS-CM2.nc`  |  Figure-local regridding cache |
| `src/Pic/Fig6_ModelRobustness/data/cache/regrid_ssp245_ACCESS-CM2.nc`  |  Figure-local regridding cache |
| `src/Pic/Fig6_ModelRobustness/data/cache/regrid_ssp585_ACCESS-CM2.nc`  |  Figure-local regridding cache |

## Outputs

- `src/Pic/Fig6_ModelRobustness/data/case_region_stats.csv`
- `src/Pic/Fig6_ModelRobustness/data/map_similarity.csv`
- `src/Pic/Fig6_ModelRobustness/data/spread_vs_baseline.csv`
- `src/Pic/Fig6_ModelRobustness/data/run_meta.csv`
- `src/Pic/Fig6_ModelRobustness/data/robustness_ssp126.nc`
- `src/Pic/Fig6_ModelRobustness/data/robustness_ssp245.nc`
- `src/Pic/Fig6_ModelRobustness/data/robustness_ssp585.nc`

Image: `src/Pic/Fig6_ModelRobustness/Fig6.jpg`.
