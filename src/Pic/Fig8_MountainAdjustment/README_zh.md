[English](README.md) | [简体中文](README_zh.md)

# 图 8：山脉分区约束调整

## 运行

在项目根目录运行：

```bash
conda activate MET
python "src/Pic/Fig8_MountainAdjustment/Fig8.py"
```

## 说明

绘制 SSP2-4.5 情景下的后验减先验调整量，三个情景共用色标。默认绘图使用已有 WGS84 山脉数据；Adjustment > 0 为有效格点中正向调整的数量占比，p ≥ 0.05 的格点以灰色显示。

## 输入

路径均相对于项目根目录。

| 数据地址  |  用途 |
|---|---|
| `Output/EC/China/HEC_ssp126_PrecipVar_to_R95mm_intensity.nc`  |  HEC输入 |
| `Output/EC/China/HEC_ssp245_PrecipVar_to_R95mm_intensity.nc`  |  HEC输入 |
| `Output/EC/China/HEC_ssp585_PrecipVar_to_R95mm_intensity.nc`  |  HEC输入 |
| `Data/China/cnmap.shp`  |  地理输入 |
| `src/Pic/Fig8_MountainAdjustment/data/CN_MountainRanges_WGS84.shp`  |  地理输入 |

## 输出

- `src/Pic/Fig8_MountainAdjustment/data/fig8_stats.csv`

图片：`src/Pic/Fig8_MountainAdjustment/Fig8.jpg`。
