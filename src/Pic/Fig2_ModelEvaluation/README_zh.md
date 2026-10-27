# 图 2：历史模式评估

[English](README.md) | [中文](README_zh.md)

## 运行

在项目根目录运行：

```bash
conda activate MET
python "src/Pic/Fig2_ModelEvaluation/Fig2.py"
```

## 说明

评估 19 个模式在 1981–2010 年的空间相关和偏差。模式场面积加权重网格到观测网格；相关采用余弦纬度权重，偏差为观测减模式。

## 输入

路径均相对于项目根目录。

| 数据地址  |  用途 |
|---|---|
| `src/Pic/Fig2_ModelEvaluation/data/MULTI_MODEL-historical-1981-2010.nc`  |  历史输入 |
| `src/Pic/Fig2_ModelEvaluation/data/CN05-OBS-1981-2010.nc`  |  历史输入 |
| `Data/China/cnmap.shp`  |  地理输入 |

## 输出

- `src/Pic/Fig2_ModelEvaluation/data/fig2a_stats.csv`
- `src/Pic/Fig2_ModelEvaluation/data/fig2_per_model.csv`
- `src/Pic/Fig2_ModelEvaluation/data/fig2b_stats.csv`

图片：`src/Pic/Fig2_ModelEvaluation/Fig2.jpg`。
