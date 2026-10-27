# 图 9：约束调整场的谱分析与尺度分解

[English](README.md) | [中文](README_zh.md)

## 运行

在项目根目录运行：

```bash
conda activate MET
python "src/Pic/Fig9_BiasScaleDecomposition/Fig9.py"
```

## 说明

对 SSP2-4.5 调整场进行二维 DCT，按约 1409 和 4898 km 分为三档尺度。全国及七个分区采用中国陆域掩膜；净调整量为有符号面积加权平均，方差份额为各档区域空间方差占三档方差之和的比例。200 km 以下的分量保留在小尺度中；存在协方差时，方差份额不等于原场总方差的严格分解。

## 输入

路径均相对于项目根目录。

| 数据地址  |  用途 |
|---|---|
| `Output/EC/China/HEC_ssp245_PrecipVar_to_R95mm_intensity.nc`  |  HEC输入 |
| `Data/China/cnmap.shp`  |  地理输入 |
| `Data/River/HuanghaiRiver_polygon.shp`  |  地理输入 |
| `Data/River/PearlRiver_polygon.shp`  |  地理输入 |
| `Data/River/YangtzeRiver_polygon.shp`  |  地理输入 |

## 输出

- `src/Pic/Fig9_BiasScaleDecomposition/data/bias_spectrum.csv`
- `src/Pic/Fig9_BiasScaleDecomposition/data/bias_slope.csv`
- `src/Pic/Fig9_BiasScaleDecomposition/data/breakpoint.json`
- `src/Pic/Fig9_BiasScaleDecomposition/data/band_1_le1409_km.npy`
- `src/Pic/Fig9_BiasScaleDecomposition/data/band_2_1409-4898_km.npy`
- `src/Pic/Fig9_BiasScaleDecomposition/data/band_3_ge_4898_km.npy`
- `src/Pic/Fig9_BiasScaleDecomposition/data/scale_variance.csv`
- `src/Pic/Fig9_BiasScaleDecomposition/data/region_band_sign_stats.csv`

图片：`src/Pic/Fig9_BiasScaleDecomposition/Fig9.jpg`。
