[English](README.md) | [简体中文](README_zh.md)

# Precipitation indices and hierarchical emergent constraints

Use 1981–2010 `PrecipVar` to constrain 2021–2050 `R95mm_intensity`, producing HEC results for three SSP scenarios.

## Environment and inputs

Use Python 3.10 or later with numpy, pandas, xarray, netCDF4, scipy, dask, tqdm, matplotlib and rioxarray.

Inputs are daily precipitation in mm/day with one-dimensional latitude and longitude coordinates. Paths are relative to the project root.

| Input | Path |
|---|---|
| Original observations | `Data/Obs/`: CN05.1, CPC, CHM PRE V2 and HGCDC |
| Model precipitation | `Data/Mode/<mode>/HiCPC_pr_<mode>_<scenario>.nc` |
| Observational annual indices | `Output/Obs/indices/` |
| Scenario-merged model indices | `Output/Mode/indices/Scenariomerged/MULTI_MODEL-<scenario>-ALL_INDICES.nc` |

CN05.1 defines the target grid. Prepare `Output/Obs/Regridded/CN05.1_1961-2023_0.25-0.25.nc` before calculating observational indices.

## Scripts and outputs

| Script | Purpose | Output directory |
|---|---|---|
| `1统一观测数据分辨率.py` | Bilinear interpolation for CPC; area-weighted regridding for CHM PRE V2 and HGCDC | `Output/Obs/Regridded/` |
| `2计算观测数据指标.py` | Annual indices for four observational products | `Output/Obs/indices/` |
| `3计算模式数据强度和降水变率.py` | Single-model indices | `Output/Mode/indices/<mode>/<scenario>/` |
| `4批量计算多个模式_强度和降水变率.py` | Batch processing of 19 models | Same as script 3 |
| `5模式数据合并.py` | Merge model indices by scenario | `Output/Mode/indices/Scenariomerged/` |
| `6中国区域分层涌现约束.py` | Grid-cell HEC calculations | `Output/EC/China/` |

Choose script 3 or 4 as needed. Check ensemble completeness before merging. With observational and merged model indices already available, run script 6 directly.

## Run

From the project root:

```bash
conda activate MET
python "src/pipeline/1统一观测数据分辨率.py"
python "src/pipeline/2计算观测数据指标.py"
python "src/pipeline/4批量计算多个模式_强度和降水变率.py"
python "src/pipeline/5模式数据合并.py"
# Without SCENARIO, script 6 processes all three scenarios in sequence.
unset SCENARIO
python "src/pipeline/6中国区域分层涌现约束.py"
```

Single-model calculation:

```bash
python "src/pipeline/3计算模式数据强度和降水变率.py" --mode ACCESS-CM2 --scenarios ssp245
```

HEC for one scenario:

```bash
SCENARIO=ssp245 python "src/pipeline/6中国区域分层涌现约束.py"
```

## Indices and settings

- The baseline is 1981–2010. Default index periods intersect available years with 1961–2025 for observations and 1979–2100 for models.
- Scenarios are `ssp126`, `ssp245` and `ssp585`. The default model domain is 14–56°N, 69–141°E; the PrecipVar split year is 2015.
- `R90/95/99mm_intensity` is annual mean intensity above the corresponding baseline wet-day percentile. Wet days have ≥1 mm/day; thresholds are invalid with fewer than 10 baseline wet days.
- `PrecipVar` is the annual standard deviation of daily residuals after removing the annual cycle and linear trend (ddof=0).
- Observational outputs contain three percentile-intensity indices and PrecipVar. Model outputs also include fixed-threshold `R10/20/25/50mm_intensity` indices.
- HEC uses the across-product sample standard deviation and standard error and requires at least three valid model pairs. Outputs retain the full CN05 grid; plotting scripts handle regional statistics and significance masks.

## HEC outputs

Each scenario produces `HEC_<scenario>_PrecipVar_to_R95mm_intensity.nc`, with `(lat, lon)` dimensions and float32 variables.

| Variable | Meaning |
|---|---|
| `r` | Across-model correlation between the historical predictor and future target |
| `p_value` | Two-sided p value for the corresponding regression slope |
| `obs_sigma_raw` | Sample standard deviation across historical product means; nonpositive values are set to NaN |
| `obs_sigma_effective` | Observational error term: obs_sigma_raw / √N (standard error) |
| `prior_mean` / `prior_std` | Mean / sample standard deviation of the valid future model ensemble |
| `posterior_mean` / `posterior_std` | HEC posterior mean / standard deviation |
| `reduction` | Relative standard-deviation reduction; 0.2 means 20%; stored without multiplication by 100 |
| `n` | Valid model-pair count at each grid cell, not observational-product count `N` |
