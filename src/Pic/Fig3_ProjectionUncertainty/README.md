# 图 3：未来预估与模式间不确定性

## 运行

在项目根目录运行：

```bash
conda activate MET
python "src/Pic/Fig3_ProjectionUncertainty/Fig3.py"
```

## 方法与统计口径

各模式先取2021–2050年 R95mm_intensity 平均，再计算集合均值、标准差和方差。标准差采用 ddof=0，区域统计使用余弦纬度权重。图4依赖本图输出的NPZ。

## 数据地址与输出

以下路径均相对于项目根目录；例如 `Data/`、`Output/` 和 `src/` 为项目根目录下的文件夹。

| 数据地址 | 用途 | 内容 |
|---|---|---|
| `Output/Mode/indices/Scenariomerged/MULTI_MODEL-ssp126-ALL_INDICES.nc` | 模式输入 | 2021–2050 R95mm_intensity；逐模式年段均值→集合统计 |
| `Output/Mode/indices/Scenariomerged/MULTI_MODEL-ssp245-ALL_INDICES.nc` | 模式输入 | 2021–2050 R95mm_intensity；逐模式年段均值→集合统计 |
| `Output/Mode/indices/Scenariomerged/MULTI_MODEL-ssp585-ALL_INDICES.nc` | 模式输入 | 2021–2050 R95mm_intensity；逐模式年段均值→集合统计 |
| `Data/China/cnmap.shp` | 地理输入 | 中国边界；同名 .shx、.dbf 等配套文件需一起保留 |
| `src/Pic/Fig3_ProjectionUncertainty/data/fig3_data.npz` | 本图生成后读取 | 经纬度及三情景mean/var/std；同时供图4读取 |

先对各模式取2021–2050平均，再求集合均值、标准差和方差；std 使用 ddof=0。NPZ 是图4的上游依赖。

本图生成的统计及分析文件：

- `src/Pic/Fig3_ProjectionUncertainty/data/fig3_stats.csv`
- `src/Pic/Fig3_ProjectionUncertainty/data/fig3_levels.csv`

最终图片：`src/Pic/Fig3_ProjectionUncertainty/Fig3.jpg`。
