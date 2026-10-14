# 图 4：区域极端降水统计

## 运行

在项目根目录运行：

```bash
conda activate MET
python "src/Pic/Fig4_RegionalStatistics/Fig4.py"
```

先运行图3以生成输入NPZ。

## 方法与统计口径

统计七个地理分区、三大流域和中国全域。区域强度为集合平均场的面积加权平均；误差棒为格点模式间标准差的区域加权平均，不是各模式区域均值的标准差。标准差继承图3的 ddof=0。分区采用代码中矩形范围，流域采用矢量掩膜。

## 数据地址与输出

以下路径均相对于项目根目录；例如 `Data/`、`Output/` 和 `src/` 为项目根目录下的文件夹。

| 数据地址 | 用途 | 内容 |
|---|---|---|
| `src/Pic/Fig3_ProjectionUncertainty/data/fig3_data.npz` | 跨图输入 | lon、lat、ssp126/245/585_mean及_std；400×700网格 |
| `Data/China/cnmap.shp` | 地理输入 | 中国边界；同名 .shx、.dbf 等配套文件需一起保留 |
| `Data/River/HuanghaiRiver_polygon.shp` | 地理输入 | 黄河（文件名沿用 HuanghaiRiver）流域多边形；同名配套文件需一起保留 |
| `Data/River/PearlRiver_polygon.shp` | 地理输入 | 珠江流域多边形；同名配套文件需一起保留 |
| `Data/River/YangtzeRiver_polygon.shp` | 地理输入 | 长江流域多边形；同名配套文件需一起保留 |
| `src/Pic/Fig4_RegionalStatistics/data/fig4_regional_stats.csv` | 本图生成后读取 | 33行区域统计；柱状图输入 |

依赖图3 NPZ，建议先运行图3。误差棒表示逐格点模式间标准差场的区域加权平均，不是各模式区域均值之间的标准差；std 延续图3 ddof=0。

本图生成的统计及分析文件：

- `src/Pic/Fig4_RegionalStatistics/data/fig4_regional_stats.csv`

最终图片：`src/Pic/Fig4_RegionalStatistics/Fig4.jpg`。
