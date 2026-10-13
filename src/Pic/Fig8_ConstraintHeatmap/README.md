# 图 8：区域约束热力图

## 运行

在项目根目录运行：

```bash
conda activate MET
python "src/Pic/Fig8_ConstraintHeatmap/Fig8.py"
```

## 方法与统计口径

统计中国全域、七个分区和三个流域的r、标准差缩减率与约束调整量。三个量共用 p<0.05 且 r≥0.5 的统计域，均采用余弦纬度加权。缩减率是逐格点缩减比例的区域平均；CSV中的std表示区域内空间离散度。

## 数据地址与输出

以下路径均相对于项目根目录；例如 `Data/`、`Output/` 和 `src/` 为项目根目录下的文件夹。

| 数据地址 | 用途 | 内容 |
|---|---|---|
| `Output/EC/China/HEC_ssp126_PrecipVar_to_R95mm_intensity.nc` | HEC输入 | ssp126；1981–2010历史约束2021–2050未来；163×283网格 |
| `Output/EC/China/HEC_ssp245_PrecipVar_to_R95mm_intensity.nc` | HEC输入 | ssp245；1981–2010历史约束2021–2050未来；163×283网格 |
| `Output/EC/China/HEC_ssp585_PrecipVar_to_R95mm_intensity.nc` | HEC输入 | ssp585；1981–2010历史约束2021–2050未来；163×283网格 |
| `Data/River/HuanghaiRiver_polygon.shp` | 地理输入 | 黄河（文件名沿用 HuanghaiRiver）流域多边形；同名配套文件需一起保留 |
| `Data/River/PearlRiver_polygon.shp` | 地理输入 | 珠江流域多边形；同名配套文件需一起保留 |
| `Data/River/YangtzeRiver_polygon.shp` | 地理输入 | 长江流域多边形；同名配套文件需一起保留 |
| `src/Pic/Fig8_ConstraintHeatmap/data/fig8_regional_stats.csv` | 本图生成后读取 | 33行=3情景×11区域；热力图输入 |

先读HEC计算区域统计CSV，再读CSV绘制热力图。r、缩减率、后验−先验调整量共用 p<0.05 且 r≥0.5 的统计域；CSV中的std是区域空间离散度。

本图生成的统计及分析文件：

- `src/Pic/Fig8_ConstraintHeatmap/data/fig8_regional_stats.csv`

最终图片：`src/Pic/Fig8_ConstraintHeatmap/Fig8.jpg`。
