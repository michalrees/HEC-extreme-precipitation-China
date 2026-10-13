# 图 11：先验与后验不确定性的尺度分解

## 运行

在项目根目录运行：

```bash
conda activate MET
python "src/Pic/Fig11_UncertaintyDecomposition/Fig11.py"
```

先运行图10以生成尺度断点。

## 方法与统计口径

读取SSP2-4.5的 prior_std、posterior_std，沿用图10断点做二维DCT分解，不去除σ场均值。每档缩减率为 1 − 后验重构分量绝对值的区域加权平均 / 先验对应平均。

CSV的r_total为三档平均绝对幅值之和的缩减率，全国约20.6%；原始σ场区域平均值之比对应约20.7%，代码仅计算并打印，未绘制参考线。二者均不同于图8的逐格点缩减率区域平均，且掩膜不同。小尺度重构可能含负值，采用绝对幅值不代表原始标准差为负，也不能解释为各类降水过程的集合方差缩减。

## 数据地址与输出

以下路径均相对于项目根目录；例如 `Data/`、`Output/` 和 `src/` 为项目根目录下的文件夹。

| 数据地址 | 用途 | 内容 |
|---|---|---|
| `Output/EC/China/HEC_ssp245_PrecipVar_to_R95mm_intensity.nc` | HEC输入 | ssp245；1981–2010历史约束2021–2050未来；163×283网格 |
| `src/Pic/Fig10_BiasScaleDecomposition/data/breakpoint.json` | 跨图输入 | selected_breakpoints，约1409和4898 km |
| `Data/China/cnmap.shp` | 地理输入 | 中国边界；同名 .shx、.dbf 等配套文件需一起保留 |
| `Data/River/HuanghaiRiver_polygon.shp` | 地理输入 | 黄河（文件名沿用 HuanghaiRiver）流域多边形；同名配套文件需一起保留 |
| `Data/River/PearlRiver_polygon.shp` | 地理输入 | 珠江流域多边形；同名配套文件需一起保留 |
| `Data/River/YangtzeRiver_polygon.shp` | 地理输入 | 长江流域多边形；同名配套文件需一起保留 |


本图生成的统计及分析文件：

- `src/Pic/Fig11_UncertaintyDecomposition/data/uncertainty_reduction.csv`
- `src/Pic/Fig11_UncertaintyDecomposition/data/uncertainty_spectrum.csv`

最终图片：`src/Pic/Fig11_UncertaintyDecomposition/Fig11.jpg`。
