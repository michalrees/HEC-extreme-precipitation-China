# 图 4：区域极端降水统计

[English](README.md) | [中文](README_zh.md)

## 运行

在项目根目录运行：

```bash
conda activate MET
python "src/Pic/Fig4_RegionalStatistics/Fig4.py"
```

先运行图 3 生成所需输入。

## 说明

统计全国、七个地理分区和三大流域的极端降水强度。误差棒为格点模式间标准差的区域加权平均，标准差使用 ddof=0。

## 输入

路径均相对于项目根目录。

| 数据地址  |  用途 |
|---|---|
| `src/Pic/Fig3_ProjectionUncertainty/data/fig3_data.npz`  |  跨图输入 |
| `Data/China/cnmap.shp`  |  地理输入 |
| `Data/River/HuanghaiRiver_polygon.shp`  |  地理输入 |
| `Data/River/PearlRiver_polygon.shp`  |  地理输入 |
| `Data/River/YangtzeRiver_polygon.shp`  |  地理输入 |
| `src/Pic/Fig4_RegionalStatistics/data/fig4_regional_stats.csv`  |  本图生成后读取 |

## 输出

- `src/Pic/Fig4_RegionalStatistics/data/fig4_regional_stats.csv`

图片：`src/Pic/Fig4_RegionalStatistics/Fig4.jpg`。
