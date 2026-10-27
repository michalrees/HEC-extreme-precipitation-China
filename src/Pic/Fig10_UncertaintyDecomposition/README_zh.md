# 图 10：先验与后验不确定性的尺度分解

[English](README.md) | [中文](README_zh.md)

## 运行

在项目根目录运行：

```bash
conda activate MET
python "src/Pic/Fig10_UncertaintyDecomposition/Fig10.py"
```

先运行图 9 生成所需输入。

## 说明

沿用图 9 的尺度断点，对 SSP2-4.5 的先验和后验标准差场进行二维 DCT，保留场均值。各档缩减率为 1 减去后验与先验重构分量区域平均绝对幅值之比；r_total 对应三档平均绝对幅值之和的缩减率。

## 输入

路径均相对于项目根目录。

| 数据地址  |  用途 |
|---|---|
| `Output/EC/China/HEC_ssp245_PrecipVar_to_R95mm_intensity.nc`  |  HEC输入 |
| `src/Pic/Fig9_BiasScaleDecomposition/data/breakpoint.json`  |  跨图输入 |
| `Data/China/cnmap.shp`  |  地理输入 |
| `Data/River/HuanghaiRiver_polygon.shp`  |  地理输入 |
| `Data/River/PearlRiver_polygon.shp`  |  地理输入 |
| `Data/River/YangtzeRiver_polygon.shp`  |  地理输入 |

## 输出

- `src/Pic/Fig10_UncertaintyDecomposition/data/uncertainty_reduction.csv`
- `src/Pic/Fig10_UncertaintyDecomposition/data/uncertainty_spectrum.csv`

图片：`src/Pic/Fig10_UncertaintyDecomposition/Fig10.jpg`。
