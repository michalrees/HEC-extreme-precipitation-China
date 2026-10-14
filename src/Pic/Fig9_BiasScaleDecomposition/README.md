# 图 9：约束调整场的谱分析与尺度分解

## 运行

在项目根目录运行：

```bash
conda activate MET
python "src/Pic/Fig9_BiasScaleDecomposition/Fig9.py"
```

## 方法与统计口径

对SSP2-4.5的 posterior_mean − prior_mean 做一次全国域二维DCT。由波长—方差谱的局部斜率曲率筛选断点，过滤200 km以下候选和过近的候选，选取约1409、4898 km断点；200 km以下的场仍包含在小尺度分量中。三档带通重构场之和恢复调整场。

净调整量是各分量的有符号面积加权平均；正、负贡献分别计算 max(分量,0) 和 min(分量,0) 的面积加权平均，两者之和等于净调整量。方差份额定义为各档区域空间方差除以三档方差之和，存在协方差时不等同于原场总方差的严格分解。全国与七个分区采用中国陆域掩膜；结果描述空间尺度结构，不直接对应唯一物理过程。breakpoint.json供图10使用。

## 数据地址与输出

以下路径均相对于项目根目录；例如 `Data/`、`Output/` 和 `src/` 为项目根目录下的文件夹。

| 数据地址 | 用途 | 内容 |
|---|---|---|
| `Output/EC/China/HEC_ssp245_PrecipVar_to_R95mm_intensity.nc` | HEC输入 | ssp245；1981–2010历史约束2021–2050未来；163×283网格 |
| `Data/China/cnmap.shp` | 地理输入 | 中国边界；同名 .shx、.dbf 等配套文件需一起保留 |
| `Data/River/HuanghaiRiver_polygon.shp` | 地理输入 | 黄河（文件名沿用 HuanghaiRiver）流域多边形；同名配套文件需一起保留 |
| `Data/River/PearlRiver_polygon.shp` | 地理输入 | 珠江流域多边形；同名配套文件需一起保留 |
| `Data/River/YangtzeRiver_polygon.shp` | 地理输入 | 长江流域多边形；同名配套文件需一起保留 |

对ssp245的 posterior_mean−prior_mean 做DCT，生成谱、断点和三档重构场；breakpoint.json是图10的输入。现行区域统计以scale_variance.csv为准。

本图生成的统计及分析文件：

- `src/Pic/Fig9_BiasScaleDecomposition/data/bias_spectrum.csv`
- `src/Pic/Fig9_BiasScaleDecomposition/data/bias_slope.csv`
- `src/Pic/Fig9_BiasScaleDecomposition/data/breakpoint.json`
- `src/Pic/Fig9_BiasScaleDecomposition/data/band_1_le1409_km.npy`
- `src/Pic/Fig9_BiasScaleDecomposition/data/band_2_1409-4898_km.npy`
- `src/Pic/Fig9_BiasScaleDecomposition/data/band_3_ge_4898_km.npy`
- `src/Pic/Fig9_BiasScaleDecomposition/data/scale_variance.csv`
- `src/Pic/Fig9_BiasScaleDecomposition/data/region_band_sign_stats.csv`

最终图片：`src/Pic/Fig9_BiasScaleDecomposition/Fig9.jpg`。
