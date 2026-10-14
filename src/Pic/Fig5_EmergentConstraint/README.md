# 图 5：分层涌现约束诊断

## 运行

在项目根目录运行：

```bash
conda activate MET
python "src/Pic/Fig5_EmergentConstraint/Fig5.py"
```

## 方法与统计口径

绘制相关系数r、标准差缩减比例及约束调整量（posterior_mean − prior_mean）。有效统计域为 p_value<0.05 且 r≥0.5，区域均值按余弦纬度加权。reduction = 1 − posterior_std/prior_std，先逐格点计算再平均；HEC模式间标准差采用 ddof=1。

## 数据地址与输出

以下路径均相对于项目根目录；例如 `Data/`、`Output/` 和 `src/` 为项目根目录下的文件夹。

| 数据地址 | 用途 | 内容 |
|---|---|---|
| `Output/EC/China/HEC_ssp126_PrecipVar_to_R95mm_intensity.nc` | HEC输入 | ssp126；1981–2010历史约束2021–2050未来；163×283网格 |
| `Output/EC/China/HEC_ssp245_PrecipVar_to_R95mm_intensity.nc` | HEC输入 | ssp245；1981–2010历史约束2021–2050未来；163×283网格 |
| `Output/EC/China/HEC_ssp585_PrecipVar_to_R95mm_intensity.nc` | HEC输入 | ssp585；1981–2010历史约束2021–2050未来；163×283网格 |
| `Data/China/cnmap.shp` | 地理输入 | 中国边界；同名 .shx、.dbf 等配套文件需一起保留 |

读取 r、p_value、reduction、prior_mean、posterior_mean 等。显著约束统计采用 p<0.05 且 r≥0.5。调整量=后验−先验；HEC模式间标准差使用 ddof=1。

本图生成的统计及分析文件：

- `src/Pic/Fig5_EmergentConstraint/data/fig5_stats.csv`

最终图片：`src/Pic/Fig5_EmergentConstraint/Fig5.jpg`。
