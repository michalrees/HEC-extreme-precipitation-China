# 图 3：未来预估与模式间不确定性

[English](README.md) | [中文](README_zh.md)

## 运行

在项目根目录运行：

```bash
conda activate MET
python "src/Pic/Fig3_ProjectionUncertainty/Fig3.py"
```

## 说明

绘制 2021–2050 年 R95mm_intensity 的集合均值、标准差和方差。标准差使用 ddof=0，区域统计采用余弦纬度权重。

## 输入

路径均相对于项目根目录。

| 数据地址  |  用途 |
|---|---|
| `Output/Mode/indices/Scenariomerged/MULTI_MODEL-ssp126-ALL_INDICES.nc`  |  模式输入 |
| `Output/Mode/indices/Scenariomerged/MULTI_MODEL-ssp245-ALL_INDICES.nc`  |  模式输入 |
| `Output/Mode/indices/Scenariomerged/MULTI_MODEL-ssp585-ALL_INDICES.nc`  |  模式输入 |
| `Data/China/cnmap.shp`  |  地理输入 |
| `src/Pic/Fig3_ProjectionUncertainty/data/fig3_data.npz`  |  本图生成后读取 |

## 输出

- `src/Pic/Fig3_ProjectionUncertainty/data/fig3_stats.csv`
- `src/Pic/Fig3_ProjectionUncertainty/data/fig3_levels.csv`

图片：`src/Pic/Fig3_ProjectionUncertainty/Fig3.jpg`。
