# 图 7：区域约束热力图

[English](README.md) | [中文](README_zh.md)

## 运行

在项目根目录运行：

```bash
conda activate MET
python "src/Pic/Fig7_ConstraintHeatmap/Fig7.py"
```

## 说明

统计全国、七个分区和三个流域的相关系数、不确定性缩减率及约束调整量。统计范围为 p < 0.05 且 r ≥ 0.5 的有效格点，采用余弦纬度权重；CSV 中的 std 为区域空间标准差。

## 输入

路径均相对于项目根目录。

| 数据地址  |  用途 |
|---|---|
| `Output/EC/China/HEC_ssp126_PrecipVar_to_R95mm_intensity.nc`  |  HEC输入 |
| `Output/EC/China/HEC_ssp245_PrecipVar_to_R95mm_intensity.nc`  |  HEC输入 |
| `Output/EC/China/HEC_ssp585_PrecipVar_to_R95mm_intensity.nc`  |  HEC输入 |
| `Data/River/HuanghaiRiver_polygon.shp`  |  地理输入 |
| `Data/River/PearlRiver_polygon.shp`  |  地理输入 |
| `Data/River/YangtzeRiver_polygon.shp`  |  地理输入 |
| `src/Pic/Fig7_ConstraintHeatmap/data/fig7_regional_stats.csv`  |  本图生成后读取 |

## 输出

- `src/Pic/Fig7_ConstraintHeatmap/data/fig7_regional_stats.csv`

图片：`src/Pic/Fig7_ConstraintHeatmap/Fig7.jpg`。
