# 图 2：历史模式评估

## 运行

在项目根目录运行：

```bash
conda activate MET
python "src/Pic/Fig2_ModelEvaluation/Fig2.py"
```

## 方法与统计口径

评估1981–2010年19个模式的 PrecipVar 和 R95mm_intensity。模式场面积加权重网格到观测网格后，计算空间相关及观测−模式偏差。相关系数为纬度余弦加权的空间相关，不能等同于模式集合上的涌现关系相关系数。

## 数据地址与输出

以下路径均相对于项目根目录；例如 `Data/`、`Output/` 和 `src/` 为项目根目录下的文件夹。

| 数据地址 | 用途 | 内容 |
|---|---|---|
| `src/Pic/Fig2_ModelEvaluation/data/MULTI_MODEL-historical-1981-2010.nc` | 历史输入 | 1981–2010；PrecipVar、R95mm_intensity |
| `src/Pic/Fig2_ModelEvaluation/data/CN05-OBS-1981-2010.nc` | 历史输入 | 1981–2010；PrecipVar、R95mm_intensity |
| `Data/China/cnmap.shp` | 地理输入 | 中国边界；同名 .shx、.dbf 等配套文件需一起保留 |

两个历史文件直接从图2 data 读取。Bias 定义为观测−模式；本地 CN05 为历史期观测指标。

本图生成的统计及分析文件：

- `src/Pic/Fig2_ModelEvaluation/data/fig2a_stats.csv`
- `src/Pic/Fig2_ModelEvaluation/data/fig2_per_model.csv`
- `src/Pic/Fig2_ModelEvaluation/data/fig2b_stats.csv`

最终图片：`src/Pic/Fig2_ModelEvaluation/Fig2.jpg`。
