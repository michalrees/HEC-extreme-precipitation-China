# 图 6：模式集合稳健性

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

## 方法与统计口径

以19个模式的全集合为参照，进行19组单模式剔除和4组模式家族剔除；绘图对比23组剔除结果。诊断全国平均相关系数变化、缩减率变化及相关场RMSD。观测误差项为产品间样本标准差除以有效产品数的平方根。模式历史与未来时段分别为1981–2010和2021–2050。重网格缓存需与上游模式文件一致；上游变化后使用 --force-regrid。--selftest 检验计算与基线的一致性，不证明未来预估准确性。

## 数据地址与输出

以下路径均相对于项目根目录；例如 `Data/`、`Output/` 和 `src/` 为项目根目录下的文件夹。

| 数据地址 | 用途 | 内容 |
|---|---|---|
| `Output/Obs/indices/CN05-OBS-IntensityAndPrecipVar-1961-2023.nc` | 观测输入 | 1981–2010逐年指标取时间平均；图1使用 PrecipVar、R95mm_intensity，图6使用 PrecipVar |
| `Output/Obs/indices/HGCDC-OBS-IntensityAndPrecipVar-1961-2022.nc` | 观测输入 | 1981–2010逐年指标取时间平均；图1使用 PrecipVar、R95mm_intensity，图6使用 PrecipVar |
| `Output/Obs/indices/CHM_PRE_V2-OBS-IntensityAndPrecipVar-1961-2024.nc` | 观测输入 | 1981–2010逐年指标取时间平均；图1使用 PrecipVar、R95mm_intensity，图6使用 PrecipVar |
| `Output/Obs/indices/CPC-OBS-IntensityAndPrecipVar-1979-2025.nc` | 观测输入 | 1981–2010逐年指标取时间平均；图1使用 PrecipVar、R95mm_intensity，图6使用 PrecipVar |
| `Output/Mode/indices/Scenariomerged/MULTI_MODEL-ssp126-ALL_INDICES.nc` | 模式输入 | ssp126；19个模式；历史 PrecipVar：1981–2010，未来 R95mm_intensity：2021–2050 |
| `Output/Mode/indices/Scenariomerged/MULTI_MODEL-ssp245-ALL_INDICES.nc` | 模式输入 | ssp245；19个模式；历史 PrecipVar：1981–2010，未来 R95mm_intensity：2021–2050 |
| `Output/Mode/indices/Scenariomerged/MULTI_MODEL-ssp585-ALL_INDICES.nc` | 模式输入 | ssp585；19个模式；历史 PrecipVar：1981–2010，未来 R95mm_intensity：2021–2050 |
| `Output/EC/China/HEC_ssp126_PrecipVar_to_R95mm_intensity.nc` | 基线核验 | ssp126；1981–2010历史约束2021–2050未来；163×283网格 |
| `Output/EC/China/HEC_ssp245_PrecipVar_to_R95mm_intensity.nc` | 基线核验 | ssp245；1981–2010历史约束2021–2050未来；163×283网格 |
| `Output/EC/China/HEC_ssp585_PrecipVar_to_R95mm_intensity.nc` | 基线核验 | ssp585；1981–2010历史约束2021–2050未来；163×283网格 |
| `Data/River/HuanghaiRiver_polygon.shp` | 地理输入 | 黄河（文件名沿用 HuanghaiRiver）流域多边形；同名配套文件需一起保留 |
| `Data/River/PearlRiver_polygon.shp` | 地理输入 | 珠江流域多边形；同名配套文件需一起保留 |
| `Data/River/YangtzeRiver_polygon.shp` | 地理输入 | 长江流域多边形；同名配套文件需一起保留 |
| `src/Pic/Fig6_ModelRobustness/data/map_similarity.csv` | 本图生成后读取 | 最终图6使用的模式剔除空间相似性与区域变化统计 |
| `src/Pic/Fig6_ModelRobustness/data/cache/regrid_ssp126_ACCESS-CM2.nc` | 本图重网格缓存 | X_regrid：历史PrecipVar；Y_regrid：未来R95mm_intensity |
| `src/Pic/Fig6_ModelRobustness/data/cache/regrid_ssp245_ACCESS-CM2.nc` | 本图重网格缓存 | X_regrid：历史PrecipVar；Y_regrid：未来R95mm_intensity |
| `src/Pic/Fig6_ModelRobustness/data/cache/regrid_ssp585_ACCESS-CM2.nc` | 本图重网格缓存 | X_regrid：历史PrecipVar；Y_regrid：未来R95mm_intensity |

缓存命名规则：`src/Pic/Fig6_ModelRobustness/data/cache/regrid_{scenario}_{model}.nc`，3情景×19模式共57份。上表列出每个情景的一份代表文件。旧外部缓存候选目录：`/home/yuhaoran/Research/Program/2Process/废弃/code/完美模式检验/data/cache`；命名为 `lomo_regrid_{scenario}_{model}.nc`，仅在本图缓存不可用时尝试读取。

最终图片读取 `map_similarity.csv`。

本图生成的统计及分析文件：

- `src/Pic/Fig6_ModelRobustness/data/case_region_stats.csv`
- `src/Pic/Fig6_ModelRobustness/data/map_similarity.csv`
- `src/Pic/Fig6_ModelRobustness/data/spread_vs_baseline.csv`
- `src/Pic/Fig6_ModelRobustness/data/run_meta.csv`
- `src/Pic/Fig6_ModelRobustness/data/robustness_ssp126.nc`
- `src/Pic/Fig6_ModelRobustness/data/robustness_ssp245.nc`
- `src/Pic/Fig6_ModelRobustness/data/robustness_ssp585.nc`

最终图片：`src/Pic/Fig6_ModelRobustness/Fig6.jpg`。
