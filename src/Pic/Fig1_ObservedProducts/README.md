# 图 1：观测产品气候态

## 运行

在项目根目录运行：

```bash
conda activate MET
python "src/Pic/Fig1_ObservedProducts/Fig1.py"
```

## 方法与统计口径

四套观测的 PrecipVar 与 R95mm_intensity 取1981–2010年气候态。区域均值采用中国陆域掩膜与余弦纬度权重。产品间样本标准差用于描述观测分歧，HEC观测误差项采用该标准差除以有效产品数的平方根。

## 数据地址与输出

以下路径均相对于项目根目录；例如 `Data/`、`Output/` 和 `src/` 为项目根目录下的文件夹。

| 数据地址 | 用途 | 内容 |
|---|---|---|
| `Output/Obs/indices/CN05-OBS-IntensityAndPrecipVar-1961-2023.nc` | 观测输入 | 1981–2010逐年指标取时间平均；图1使用 PrecipVar、R95mm_intensity，图6使用 PrecipVar |
| `Output/Obs/indices/HGCDC-OBS-IntensityAndPrecipVar-1961-2022.nc` | 观测输入 | 1981–2010逐年指标取时间平均；图1使用 PrecipVar、R95mm_intensity，图6使用 PrecipVar |
| `Output/Obs/indices/CHM_PRE_V2-OBS-IntensityAndPrecipVar-1961-2024.nc` | 观测输入 | 1981–2010逐年指标取时间平均；图1使用 PrecipVar、R95mm_intensity，图6使用 PrecipVar |
| `Output/Obs/indices/CPC-OBS-IntensityAndPrecipVar-1979-2025.nc` | 观测输入 | 1981–2010逐年指标取时间平均；图1使用 PrecipVar、R95mm_intensity，图6使用 PrecipVar |
| `Data/China/cnmap.shp` | 地理输入 | 中国边界；同名 .shx、.dbf 等配套文件需一起保留 |

逐年观测先取历史期平均，再使用中国陆域掩膜。统计使用 cos(纬度) 面积权重。

本图生成的统计及分析文件：

- `src/Pic/Fig1_ObservedProducts/data/fig1_stats.csv`

最终图片：`src/Pic/Fig1_ObservedProducts/Fig1.jpg`。
