# 图 6：模式集合稳健性

[English](README.md) | [中文](README_zh.md)

## 运行

在项目根目录运行：

```bash
conda activate MET
python "src/Pic/Fig6_ModelRobustness/Fig6.py"
# 上游模式输入变化时重建缓存
python "src/Pic/Fig6_ModelRobustness/Fig6.py" --force-regrid
# 计算一致性检查
python "src/Pic/Fig6_ModelRobustness/Fig6.py" --selftest
```

## 说明

对比 19 组单模式剔除和 4 组家族剔除结果，报告全国平均相关系数变化、缩减率变化和相关场 RMSD。历史期为 1981–2010 年，未来期为 2021–2050 年；观测误差采用标准误。

## 输入

路径均相对于项目根目录。

| 数据地址  |  用途 |
|---|---|
| `Output/Obs/indices/CN05-OBS-IntensityAndPrecipVar-1961-2023.nc`  |  观测输入 |
| `Output/Obs/indices/HGCDC-OBS-IntensityAndPrecipVar-1961-2022.nc`  |  观测输入 |
| `Output/Obs/indices/CHM_PRE_V2-OBS-IntensityAndPrecipVar-1961-2024.nc`  |  观测输入 |
| `Output/Obs/indices/CPC-OBS-IntensityAndPrecipVar-1979-2025.nc`  |  观测输入 |
| `Output/Mode/indices/Scenariomerged/MULTI_MODEL-ssp126-ALL_INDICES.nc`  |  模式输入 |
| `Output/Mode/indices/Scenariomerged/MULTI_MODEL-ssp245-ALL_INDICES.nc`  |  模式输入 |
| `Output/Mode/indices/Scenariomerged/MULTI_MODEL-ssp585-ALL_INDICES.nc`  |  模式输入 |
| `Output/EC/China/HEC_ssp126_PrecipVar_to_R95mm_intensity.nc`  |  基线核验 |
| `Output/EC/China/HEC_ssp245_PrecipVar_to_R95mm_intensity.nc`  |  基线核验 |
| `Output/EC/China/HEC_ssp585_PrecipVar_to_R95mm_intensity.nc`  |  基线核验 |
| `Data/River/HuanghaiRiver_polygon.shp`  |  地理输入 |
| `Data/River/PearlRiver_polygon.shp`  |  地理输入 |
| `Data/River/YangtzeRiver_polygon.shp`  |  地理输入 |
| `src/Pic/Fig6_ModelRobustness/data/map_similarity.csv`  |  本图生成后读取 |
| `src/Pic/Fig6_ModelRobustness/data/cache/regrid_ssp126_ACCESS-CM2.nc`  |  本图重网格缓存 |
| `src/Pic/Fig6_ModelRobustness/data/cache/regrid_ssp245_ACCESS-CM2.nc`  |  本图重网格缓存 |
| `src/Pic/Fig6_ModelRobustness/data/cache/regrid_ssp585_ACCESS-CM2.nc`  |  本图重网格缓存 |

## 输出

- `src/Pic/Fig6_ModelRobustness/data/case_region_stats.csv`
- `src/Pic/Fig6_ModelRobustness/data/map_similarity.csv`
- `src/Pic/Fig6_ModelRobustness/data/spread_vs_baseline.csv`
- `src/Pic/Fig6_ModelRobustness/data/run_meta.csv`
- `src/Pic/Fig6_ModelRobustness/data/robustness_ssp126.nc`
- `src/Pic/Fig6_ModelRobustness/data/robustness_ssp245.nc`
- `src/Pic/Fig6_ModelRobustness/data/robustness_ssp585.nc`

图片：`src/Pic/Fig6_ModelRobustness/Fig6.jpg`。
