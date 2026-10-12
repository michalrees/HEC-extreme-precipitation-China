# 图 1 —— 观测层：四套格点降水产品对约束因子与目标变量的气候态刻画

本图用 CN05.1、HGCDC、CHM PRE V2、CPC 四套格点降水产品，给出 1981–2010 气候态下 HEC（hierarchical emergent constraints）框架的**约束因子 PrecipVar** 与**目标变量 R95 Intensity** 的空间分布。它回答的问题是：四套观测产品对这两个量的气候态刻画分别长什么样、彼此差多少；产品间标准差 σ 同时被计算并留档，作为 HEC 观测层估计观测误差项 σ_o 的基础。对应论文的观测资料／观测层（observational layer）部分（本模块 `doc/` 为空，未留存具体章节编号）。布局为两个指标块上下排列，每块 2×2 排列四套产品，只画观测本身。

## 目录结构
```
Fig1_ObservedProducts/
├── Fig1.py         # 观测层主脚本：读取四套产品 nc → 掩膜/面积加权统计 → 2×2×2 面板绘制 → 落盘图与统计
├── Fig1.jpg        # 论文成品图
├── data/           # 代码计算的统计数据（原始输入不在本模块，见下表）
│   ├── fig1_stats.csv      # 统计表（12 条记录：4 套产品均值 + 产品间方差 + 产品间标准差）× 2 个指标
│   └── 图1_统计数据.txt    # 同一份统计的纯文本转储（含表头与 levels 分级）
└── README.md
```

## 运行
```bash
cd "F:\Program\2Process\4HiCPC\Using hierarchical emergent constraints to reduce the uncertainty in future extreme precipitation projections over China"
python "src/Pic/Fig1_ObservedProducts/Fig1.py"
```
依赖：`matplotlib / numpy / pandas / xarray / pyshp（import shapefile）/ shapely / cartopy`。
脚本用 `Path(__file__).resolve().parents` 自下向上定位仓库根（同时含 `src/` 与 `Doc/`），无需修改路径；`Path(__file__).resolve().parent` 即模块根，`Fig1.jpg` 与 `data/` 下的两个统计文件都写在该根目录下。

## 数据来源
| 文件 | 来源 / 生成脚本 | 说明 |
|---|---|---|
| `data/fig1_stats.csv` | **代码生成** —— `Fig1.py` 的 `main()`（`pandas.DataFrame.to_csv`，`encoding="utf-8-sig"`） | 12 条记录 = 2 个指标 ×（4 套产品均值 + 产品间方差 + 产品间标准差）；列为 `metric, unit, product, mean_area_weighted, note` |
| `data/图1_统计数据.txt` | **代码生成** —— 同一脚本 `main()`（`Path.write_text`，`encoding="utf-8"`） | 与 CSV 同一份统计的纯文本转储：表头（脚本、时段、权重、σ→σ_o 说明）+ 每个指标的四套产品面积加权均值、产品间方差、产品间标准差、`levels` 分级 |
| `Output/Obs/indices/CN05-OBS-IntensityAndPrecipVar-1961-2023.nc` | **原始输入**（仓库级目录，不在本模块内） | 变量 `PrecipVar`、`R95mm_intensity`（另有 `R90mm_intensity`、`R99mm_intensity`）；年份 1961–2023 |
| `Output/Obs/indices/HGCDC-OBS-IntensityAndPrecipVar-1961-2022.nc` | **原始输入** | 变量同上；年份 1961–2022 |
| `Output/Obs/indices/CHM_PRE_V2-OBS-IntensityAndPrecipVar-1961-2024.nc` | **原始输入** | 变量同上；年份 1961–2024 |
| `Output/Obs/indices/CPC-OBS-IntensityAndPrecipVar-1979-2025.nc` | **原始输入** | 变量同上；年份 1979–2025 |
| `Data/China/cnmap.shp`（含 `.shx`、`.prj`） | **原始输入** | 中国国界，用于陆域掩膜与国界线绘制；路径 `DATA_ROOT / "China" / "cnmap.shp"` |

说明：脚本按 `PERIOD = (1981, 2010)` 对每套产品取自身年份与该时段的交集再求气候态平均。`data/` 目录内没有任何原始输入文件，两个文件都是代码写出的统计数据。

注意：`data/图1_统计数据.txt` 表头 `script` 行已在扁平化后重新指向 `src/Pic/Fig1_ObservedProducts/Fig1.py`，与当前脚本写出的值一致；两个统计文件的数值内容也与当前脚本口径一致。

## 产出
| 文件 | 内容 |
|---|---|
| `Fig1.jpg` | 论文成品图：上块 **(a) Precip Var**、下块 **(b) R95 Intensity**，每块 2×2 排列 CN05.1、HGCDC、CHM PRE V2、CPC；每块内四面板共用一条水平色带；画幅 19.0 × 18.8 cm，`dpi=400`，`bbox_inches="tight"` |
| `data/图1_统计数据.txt` | 纯文本统计：四套产品的面积加权均值、产品间方差、产品间标准差、色带分级 `levels` |
| `data/fig1_stats.csv` | 同上统计的机器可读版本（12 行 + 表头），便于后续引用与核对 |

## 代码说明
| 脚本 | 作用 | 主要产出 |
|---|---|---|
| `Fig1.py` | 单文件主脚本：读取四套观测 nc → 构造中国陆域掩膜 → 面积加权统计 → 2×2×2 面板绘制 → 落盘图与两份统计 | `Fig1.jpg`、`data/图1_统计数据.txt`、`data/fig1_stats.csv` |

关键函数（均在 `Fig1.py` 内）：

| 函数 | 作用 |
|---|---|
| `china_mask(lon, lat)` | 用 `cnmap.shp` 经 `polygonize` + `unary_union` 得到中国陆域多边形，再转成 `matplotlib.path.Path` 做向量化点内判断（毫秒级），打印落在陆域的格点数；与图 8/图 9 同源 |
| `lat_weights(lat)` | 面积权重 `w = clip(cos(lat), 0, None)` |
| `wmean(field, lat)` | 掩膜内面积加权均值（自动跳过 NaN） |
| `levels_of(vmin, vmax, step_hint)` | 按步长提示生成等距分级，档数不超过 `MAX_LEVELS = 10` |
| `load_field(fname, var)` | 打开 nc，`sel(year=slice(1981, 2010)).mean("year")` 求气候态；若纬度为降序则翻转为升序，便于 `contourf` |
| `main()` | 定义画幅/面板位置、循环两个指标块完成绘图与统计落盘 |

产品的读取顺序固定为 `CN05.1 → HGCDC → CHM PRE V2 → CPC`，对应每块内 2×2 的阅读顺序（左上、右上、左下、右下）。每个面板右上角标注该产品的面积加权均值 `Mean: x.xx`；每块只在左上角面板标一次指标编号 `(a)` / `(b)`——原第三列 “Inter-observation Uncertainty (σ)” 面板已于 2026-10-09 移除。

## 方法说明

### 数据与时段
四套产品的原始文件均为 `year × lat × lon` 的格点数据集（`lat=163`、`lon=283`）。脚本对每套产品取 `1981–2010` 与自身可得年份的交集求平均：CN05.1（1961–2023）、HGCDC（1961–2022）、CHM PRE V2（1961–2024）在该时段内完整；CPC 起始年 1979，故实际用 1981–2010。两个指标取自 nc 中的 `PrecipVar`（约束因子，单位 mm/day）与 `R95mm_intensity`（目标变量，单位 mm/day）。

### 掩膜与面积加权
绘图与统计都只在中国陆域内进行：`cnmap.shp` 的多边形先做并集与 `buffer(0)` 修复自相交，再由 `matplotlib.path.Path.contains_points` 逐格点判定，掩膜外的值置为 `NaN`。所有区域均值都用纬度余弦权重 `w = cos(lat)` 作面积加权，全国口径即 `Σ(field·w)/Σw`（仅计有效格点）。

### 分级与色带
色带上下限取四套产品实际极值（2026-09-22 统一口径）；档数沿用 `levels_of` 在 1–99 百分位参考范围下给出的档数，再用 `np.linspace` 把首尾拉到实际极值，避免向外取整造成空档。`extend="both"` 使两端延伸箭头各占一色，因此颜色数 = 档数 + 2。`PrecipVar` 用 `YlGnBu`（步长提示 0.25），`R95 Intensity` 用 `YlOrRd`（步长提示 2.5）。刻度标签由 `_fmt_tick` 统一：整数不带小数，非整数保留 1 位。每面板叠加 `levels[1:-1]` 的黑色细等值线（0.25 pt）与国界线（`#666666`，0.4 pt），并绘制 `PlateCarree` 经纬网（仅左、下标标签）。

### 产品间离散度 σ 与 σ_o（已移除的面板）
对每个格点计算四套产品间的标准差 `spread = nanstd(stack, axis=0, ddof=0)` 与方差 `variance = spread**2`。原图第三列的 σ 面板已于 2026-10-09 移除，但两者仍在脚本内计算并写入两份统计文件留档：HEC 观测层在此基础上除以 `sqrt(n)` 得到观测误差项 σ_o（observational error term）。

### 统计结果（代码实际落盘数值）
面积加权均值（`w = cos(lat)`，中国陆域，1981–2010；取自 `data/图1_统计数据.txt` 与 `data/fig1_stats.csv`）：

| 指标 | 单位 | CN05.1 | HGCDC | CHM PRE V2 | CPC |
|---|---|---|---|---|---|
| Precip Var | mm/day | 3.741 | 4.414 | 4.117 | 3.630 |
| R95 Intensity | mm/day | 26.328 | 32.193 | 30.858 | 27.084 |

产品间离散度（同上，`ddof=0`，仅留档、不再出图）：

| 指标 | 产品间方差 面积加权均值 | 产品间方差 空间最大 | 产品间标准差 σ 面积加权均值 | σ 空间最大 |
|---|---|---|---|---|
| Precip Var | 0.439 (mm/day)² | 116.041 (mm/day)² | 0.421 mm/day | 10.772 mm/day |
| R95 Intensity | 23.867 (mm/day)² | 4187.998 (mm/day)² | 3.784 mm/day | 64.715 mm/day |

（CSV 中保留 6 位小数，例如 PrecipVar/CN05.1 = 3.740918、R95 Intensity/HGCDC = 32.193395。）

色带分级 `levels`：

* `Precip Var`：`[0.2644, 5.2942, 10.324, 15.3538, 20.3837, 25.4135, 30.4433]`（6 档）
* `R95 Intensity`：`[3.5745, 25.6254, 47.6764, 69.7274, 91.7783, 113.8293, 135.8803, 157.9312, 179.9822]`（8 档）

### 文档沿革
本模块 `doc/` 目录为空（无任何 `.md` 文件），因此本文档全部内容来自 `Fig1.py` 的模块 docstring、分节注释，以及 `data/` 下两份由该脚本实际写出的统计文件；原 `code/`、`fig/`、`doc/` 三个子目录已随模块扁平化重构取消，脚本中的输出路径现统一指向模块根（`FIG_DIR = ROOT`）与 `ROOT / "data"`。
