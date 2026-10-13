# 图 3：历史偏差空间分布

## 运行

在项目根目录运行：

```bash
conda activate MET
python "src/Pic/Fig3_BiasSpatialMaps/Fig3.py"
```

## 方法与统计口径

Bias = 观测气候态 − 多模式集合平均气候态；正值表示模式低估。对 PrecipVar 与 R95mm_intensity 分别计算，使用1981–2010年数据。先生成中间NetCDF，再绘制偏差场。

## 数据地址与输出

以下路径均相对于项目根目录；例如 `Data/`、`Output/` 和 `src/` 为项目根目录下的文件夹。

| 数据地址 | 用途 | 内容 |
|---|---|---|
| `src/Pic/Fig2_ModelEvaluation/data/MULTI_MODEL-historical-1981-2010.nc` | 历史输入 | 1981–2010；PrecipVar、R95mm_intensity |
| `src/Pic/Fig2_ModelEvaluation/data/CN05-OBS-1981-2010.nc` | 历史输入 | 1981–2010；PrecipVar、R95mm_intensity |
| `Data/China/cnmap.shp` | 地理输入 | 中国边界；同名 .shx、.dbf 等配套文件需一起保留 |
| `src/Pic/Fig3_BiasSpatialMaps/data/Bias_historical.nc` | 本图生成后读取 | 两个指标的163×283历史气候态场 |
| `src/Pic/Fig3_BiasSpatialMaps/data/CN05_clim_historical.nc` | 本图生成后读取 | 两个指标的163×283历史气候态场 |
| `src/Pic/Fig3_BiasSpatialMaps/data/MME_clim_historical.nc` | 本图生成后读取 | 两个指标的163×283历史气候态场 |

先由图2历史数据生成本图中间 NetCDF，再读取 data/Bias_*.nc 绘图；当前匹配的是 Bias_historical.nc。Bias=观测−多模式均值。

本图生成的统计及分析文件：

- `src/Pic/Fig3_BiasSpatialMaps/data/fig3_stats.csv`

最终图片：`src/Pic/Fig3_BiasSpatialMaps/Fig3.jpg`。
