# 图 1：观测产品气候态

[English](README.md) | [中文](README_zh.md)

## 运行

在项目根目录运行：

```bash
conda activate MET
python "src/Pic/Fig1_ObservedProducts/Fig1.py"
```

## 说明

比较四套观测产品在 1981–2010 年的 PrecipVar 和 R95mm_intensity 气候态。区域均值采用中国陆域掩膜和余弦纬度权重；HEC 观测误差采用标准误。

## 输入

路径均相对于项目根目录。

| 数据地址  |  用途 |
|---|---|
| `Output/Obs/indices/CN05-OBS-IntensityAndPrecipVar-1961-2023.nc`  |  观测输入 |
| `Output/Obs/indices/HGCDC-OBS-IntensityAndPrecipVar-1961-2022.nc`  |  观测输入 |
| `Output/Obs/indices/CHM_PRE_V2-OBS-IntensityAndPrecipVar-1961-2024.nc`  |  观测输入 |
| `Output/Obs/indices/CPC-OBS-IntensityAndPrecipVar-1979-2025.nc`  |  观测输入 |
| `Data/China/cnmap.shp`  |  地理输入 |

## 输出

- `src/Pic/Fig1_ObservedProducts/data/fig1_stats.csv`

图片：`src/Pic/Fig1_ObservedProducts/Fig1.jpg`。
