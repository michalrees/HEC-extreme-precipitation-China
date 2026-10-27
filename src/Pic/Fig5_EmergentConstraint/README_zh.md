[English](README.md) | [简体中文](README_zh.md)

# 图 5：分层涌现约束诊断

## 运行

在项目根目录运行：

```bash
conda activate MET
python "src/Pic/Fig5_EmergentConstraint/Fig5.py"
```

## 说明

绘制相关系数、不确定性缩减率和后验减先验调整量。统计范围为输入数据域内满足 p < 0.05 且 r ≥ 0.5 的有效格点，采用余弦纬度权重。缩减率为 1 − posterior_std/prior_std；HEC 标准差使用 ddof=1。

## 输入

路径均相对于项目根目录。

| 数据地址  |  用途 |
|---|---|
| `Output/EC/China/HEC_ssp126_PrecipVar_to_R95mm_intensity.nc`  |  HEC输入 |
| `Output/EC/China/HEC_ssp245_PrecipVar_to_R95mm_intensity.nc`  |  HEC输入 |
| `Output/EC/China/HEC_ssp585_PrecipVar_to_R95mm_intensity.nc`  |  HEC输入 |
| `Data/China/cnmap.shp`  |  地理输入 |

## 输出

- `src/Pic/Fig5_EmergentConstraint/data/fig5_stats.csv`

图片：`src/Pic/Fig5_EmergentConstraint/Fig5.jpg`。
