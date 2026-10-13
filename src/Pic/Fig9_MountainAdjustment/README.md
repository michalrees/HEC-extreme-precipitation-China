# 图 9：山脉分区约束调整

## 运行

在项目根目录运行：

```bash
conda activate MET
python "src/Pic/Fig9_MountainAdjustment/Fig9.py"
```

## 方法与统计口径

实际绘制SSP2-4.5的 posterior_mean − prior_mean，另两个情景用于确定共享色标。七个分区叠加WGS84山脉矢量；统计调整量区域均值、范围和正向格点占比。p≥0.05格点叠加灰色掩膜。图上Adjustment>0为有效格点计数比例，非面积加权比例。空间对应关系不能直接证明地形机制。

## 数据地址与输出

以下路径均相对于项目根目录；例如 `Data/`、`Output/` 和 `src/` 为项目根目录下的文件夹。

| 数据地址 | 用途 | 内容 |
|---|---|---|
| `Output/EC/China/HEC_ssp126_PrecipVar_to_R95mm_intensity.nc` | HEC输入 | ssp126；1981–2010历史约束2021–2050未来；163×283网格 |
| `Output/EC/China/HEC_ssp245_PrecipVar_to_R95mm_intensity.nc` | HEC输入 | ssp245；1981–2010历史约束2021–2050未来；163×283网格 |
| `Output/EC/China/HEC_ssp585_PrecipVar_to_R95mm_intensity.nc` | HEC输入 | ssp585；1981–2010历史约束2021–2050未来；163×283网格 |
| `Data/China/cnmap.shp` | 地理输入 | 中国边界；同名 .shx、.dbf 等配套文件需一起保留 |
| `src/Pic/Fig9_MountainAdjustment/data/CN_MountainRanges_WGS84.shp` | 地理输入 | WGS84山脉矢量，配套 .shx/.dbf/.prj |

实际调整场取ssp245；ssp126、ssp585仅用于确定共享色标范围。默认绘图使用已有WGS84山脉数据，不需要重新投影。--reproject-mountains使用的原始山脉路径已缺失，不属于默认绘图输入。

本图生成的统计及分析文件：

- `src/Pic/Fig9_MountainAdjustment/data/fig9_stats.csv`

最终图片：`src/Pic/Fig9_MountainAdjustment/Fig9.jpg`。
