# 图 3 —— HiCPC 多模式集合平均相对 CN05.1 观测的偏差空间分布（Bias）

本模块绘制论文图 3：历史时期（1981–2010）HiCPC 多模式集合平均（Multi-Model Ensemble, MME）相对 CN05.1 观测的偏差空间分布（$\mathrm{Bias} = \mathrm{OBS} - \mathrm{MME}$），左、右两个面板分别为极端降水强度（R95 Intensity）与降水变率（PrecipVar）。
它回答的问题是：HiCPC 在中国区域对这两个指标的模拟偏差有多大、空间上如何分布、以低估还是高估为主，从而判断 HiCPC 能否作为后续分层涌现约束研究的数据基础。
该图对应论文第 2 节 Data and Methods 中「HiCPC 数据在中国区域的适用性评估」部分（图注与正文数值见 `Doc/涌现约束_v2.md`），在评估链条上承接图 2（19 个模式的逐模式散点评估），并为后续以降水变率约束极端降水强度提供依据。

## 目录结构
```
Fig3_BiasSpatialMaps/
├── Fig3.py                       # 唯一脚本（单文件流水线）：先提取 CN05 − MME 偏差场并存 NetCDF，再读 Bias_*.nc 绘制 1×2 偏差空间分布图并落盘统计量
├── Fig3.jpg                      # 论文成品图
├── data/                         # 原始数据 + 代码计算的统计数据
│   ├── Bias_historical.nc        # 偏差场（Fig3.py 提取步骤产出），同脚本绘图步骤的唯一绘图输入
│   ├── CN05_clim_historical.nc   # CN05.1 观测气候态（Fig3.py 提取步骤产出）
│   ├── MME_clim_historical.nc    # HiCPC MME 气候态（Fig3.py 提取步骤产出）
│   ├── fig3_stats.csv            # 图 3 统计量（Fig3.py 绘图步骤产出，utf-8-sig，可由 Excel 直接打开）
│   ├── 图3_统计数据.txt          # 图 3 统计量纯文本版（Fig3.py 绘图步骤产出，与 CSV 同源同值）
│   └── 图3_统计数据_历史.txt     # 归档：早期版本统计转储，现行代码不再写出
└── README.md
```
> 说明：本模块已改为扁平结构，原 `code/`、`fig/`、`doc/` 子目录不再存在。
> 原 `doc/画图格式说明.md` 的全文已合并进本 README 的「方法说明」一节，该目录删除后信息不会丢失。
> 本模块已由原来的 `extract_bias.py` + `Fig3.py` 双脚本合并为**单个 `Fig3.py`**：`main()` 先调用 `extract_bias()` 提取偏差场，再调用 `plot_bias_maps()` 绘图，两个步骤共享同一命名空间与路径配置。下文历史叙述中出现的 `extract_bias.py` 一律指该单文件内的偏差提取步骤（`extract_bias()`）。

## 运行
```bash
cd "F:\Program\2Process\4HiCPC\Using hierarchical emergent constraints to reduce the uncertainty in future extreme precipitation projections over China"
python "src/Pic/Fig3_BiasSpatialMaps/Fig3.py"
```
单文件流水线一次运行即可复现全部产物：`main()` 先执行偏差场提取（写 `data/Bias_historical.nc`、`data/CN05_clim_historical.nc`、`data/MME_clim_historical.nc`），再执行绘图与统计落盘（写 `Fig3.jpg`、`data/图3_统计数据.txt`、`data/fig3_stats.csv`）。读取 1.2 GB 的 MME 文件并做面积加权重映射需要数分钟，请预留足够时间。
依赖：`numpy`、`pandas`、`xarray`、`matplotlib`、`cartopy`、`pyshp`（`import shapefile`）、`shapely`。
脚本用 `Path(__file__).resolve().parent` 定位模块目录、用 `Path(__file__).resolve().parents` 自下向上定位仓库根（同时含 `src/` 与 `Doc/`），无需修改路径。

> **必须在 Fig2 之后运行**：偏差提取步骤的输入全部来自兄弟模块 `src/Pic/Fig2_ModelEvaluation/data/`（由 `MODULE_DIR.parent / "Fig2_ModelEvaluation" / "data"` 一级向上解析），若该目录下的两个 `.nc` 文件不存在，脚本会在提取阶段直接抛 `FileNotFoundError`。由于 `main()` 内置「先提取、后绘图」的顺序，不再需要像旧版那样先手动运行 `extract_bias.py`。
> 路径解析说明：`src/` 与 `Doc/` 位于论文文件夹 `Using hierarchical emergent constraints to reduce the uncertainty in future extreme precipitation projections over China/` 内；命令行中的 `src/Pic/...` 相对路径需相对包含 `src/` 的那一级目录解析。脚本内部的输入/输出路径一律基于 `Path(__file__)` 推导，与当前工作目录无关。

## 数据来源
| 文件 | 来源 / 生成脚本 | 说明 |
|---|---|---|
| `../Fig2_ModelEvaluation/data/MULTI_MODEL-historical-1981-2010.nc` | **Fig2 模块产出**，`extract_bias.py` 的只读输入 | 19 个 HiCPC 模式 1981–2010 年逐年 `R95mm_intensity`、`PrecipVar` 场（含 `case`/`year` 维）；文件名中的 `historical` 决定本模块输出文件的情景后缀 |
| `../Fig2_ModelEvaluation/data/CN05-OBS-1981-2010.nc` | **Fig2 模块产出**，两个脚本都读 | CN05.1 观测逐年场。`extract_bias.py` 用它算观测气候态与偏差；`Fig3.py` 用它算相对偏差（缺失时相对偏差记为 NaN，并打印提示） |
| `../../../Data/China/cnmap.shp` | 仓库 `Data/China/` 矢量边界（同目录还有 `cnmap.shx`、`cnmap.prj`） | `Fig3.py` 用 pyshp 读取中国边界几何与 bbox，用于绘制国界并确定图幅范围 |
| `data/Bias_historical.nc` | `extract_bias.py` 生成 | 偏差场数据集，变量名 `R95mm_intensity`、`PrecipVar`（每图变量另附 `long_name` / `units` / `scenario` / `period` 属性）；`Fig3.py` 的唯一绘图输入 |
| `data/CN05_clim_historical.nc` | `extract_bias.py` 生成 | CN05.1 观测的 1981–2010 气候态（两指标），供对比使用 |
| `data/MME_clim_historical.nc` | `extract_bias.py` 生成 | HiCPC MME 的 1981–2010 气候态（两指标），供对比使用 |
| `data/图3_统计数据.txt` | `Fig3.py` 生成 | 图 3 统计量纯文本（含色带分级与刻度完整列表） |
| `data/fig3_stats.csv` | `Fig3.py` 生成 | 与上面同源同值的机器可读版本（13 个字段，2 行数据） |
| `data/图3_统计数据_历史.txt` | **归档文件，现行代码不写出** | 早期版本的统计转储：标题为 `Fig. 2 statistics`，色带分级取整数（R95 为 −60…60 步长 12，PrecipVar 为 −12…12 步长 3），缺少观测/MME 均值、相对偏差、低估面积占比、中位绝对偏差等派生指标 |

## 产出
| 文件 | 内容 |
|---|---|
| `data/Bias_historical.nc` | 偏差场（`extract_bias.py`）：`Bias = CN05 气候态 − HiCPC MME 气候态`，情景 `historical`，时段 1981–2010 |
| `data/CN05_clim_historical.nc` | CN05.1 观测气候态（`extract_bias.py`） |
| `data/MME_clim_historical.nc` | HiCPC MME 气候态（`extract_bias.py`） |
| `Fig3.jpg` | 论文成品图（`Fig3.py`）：1 行 × 2 列的偏差空间分布，(a) R95 Intensity、(b) PrecipVar；等值线填色 + 中国矢量边界 + 左下角内嵌 PDF 直方图 + 色带上方面积加权平均偏差标注；JPEG，400 dpi，`bbox_inches="tight"` |
| `data/图3_统计数据.txt` | 面板统计量纯文本：极值、未加权/面积加权均值、观测与 MME 面积加权均值、相对偏差、低估面积占比、中位绝对偏差、色带分级与刻度 |
| `data/fig3_stats.csv` | 同上统计量的 CSV（`utf-8-sig`）；`levels` / `ticks` 两列用 `;` 分隔 |

> 注：`data/图3_统计数据.txt` 与 `data/图3_统计数据_历史.txt` 的第 2 行（`script`）已在扁平化后重新指向 `src/Pic/Fig3_BiasSpatialMaps/Fig3.py`，与现行代码写出的值一致。

## 代码说明
| 脚本 | 作用 | 主要产出 |
|---|---|---|
| `Fig3.py`（唯一脚本，单文件流水线） | 原 `extract_bias.py` + `Fig3.py` 已合并为本文件，`main()` 顺序调用两个步骤：<br>**第 1 步 `extract_bias()`（数据提取）**：复用 Fig2b 的数据加载与网格重映射逻辑，读取 Fig2 目录下的 MME 与 CN05.1 观测，取共同年份（限定 1981–2010），把各模式指标场以「面积重叠权重 × $\cos(\mathrm{lat})$」重映射到观测网格；再按 `obs_mean = 观测逐年平均`、`mme_mean = 模式等权平均后逐年平均` 计算 `bias = obs_mean − mme_mean`，并顺带保存两套气候态。指标由 `TARGET_METRICS` 指定：`R95mm_intensity`（R95 Intensity, mm/day）与 `PrecipVar`（Precip Var index）。<br>**第 2 步 `plot_bias_maps()`（绘图）**：遍历 `data/Bias_*.nc`，按变量名自动选色带（变量名含 `r95` → `r95_cmap`，否则 `precipvar_cmap`），绘制 1×2 偏差场面板（`contourf` + `contour` + 国界 + 经纬网 + 内嵌 PDF 直方图 + 水平色带 + 面板编号 + 面积加权平均偏差标注）；同时把每个面板的统计量写入文本与 CSV。 | `Fig3.jpg`、`data/Bias_historical.nc`、`data/CN05_clim_historical.nc`、`data/MME_clim_historical.nc`、`data/图3_统计数据.txt`、`data/fig3_stats.csv` |

其他实现要点：

- 两幅图色标单位在代码中统一写为 `mm/day`（R95 Intensity 是强度之差，PrecipVar 是日降水扰动标准差之差，量纲同为 mm/day）；论文图注（`Doc/涌现约束_v2.md`）写作「mm/day 与 σ (mm/day)」。
- 面板顺序由 `Bias_historical.nc` 中变量的存储顺序决定，现状为 (a) R95 Intensity、(b) PrecipVar（与 `data/图3_统计数据.txt` 中的记录顺序一致）。`plot_bias_panels` 的函数 docstring 仍写着旧顺序「Precip Var Bias | R95 Intensity Bias」，与实际输出不符。
- 合并为单文件后，两个脚本各自的模块级主函数已改名，避免同名冲突：数据提取为 `extract_bias()`、绘图为 `plot_bias_maps()`，`main()` 只负责按「先提取、后绘图」的顺序调用两者；文件内不存在跨脚本 import，两者共享同一命名空间。
- 路径常量同样已去重统一：`MODULE_DIR = Path(__file__).resolve().parent`；`DATA_DIR = MODULE_DIR / "data"`（吸收原 `extract_bias.py` 的 `OUTPUT_DIR` 与原 `Fig3.py` 的 `BIAS_DIR`）；`FIG2_DATA_DIR = MODULE_DIR.parent / "Fig2_ModelEvaluation" / "data"`（保留对兄弟模块的一级向上引用，`MODEL_FILE`、`OBS_FILE` 由它派生）；`OUTPUT_DIR = MODULE_DIR`（图片输出到模块根）。原先两处 `OBS_FILE` 定义本就指向同一个文件，已合并为一处。
- `data/图3_统计数据.txt` 表头的 `input` 行仍写作 `data/Bias_historical.nc (produced by extract_bias.py)`：这是历史文本，为保持该统计文件与旧版逐字节一致而刻意保留；该 NetCDF 实际由本文件的 `extract_bias()` 步骤生成。
- `dump_bias_statistics` / `dump_bias_statistics_csv` 的 docstring 已写明输出到 `data/` 目录，与代码实际路径一致。

## 方法说明

本节完整合并自原 `doc/画图格式说明.md`（该目录即将删除），"版式说明 1–8" 各节为其原文内容（保留全部数值与结论）；前面两节补充本模块的实现细节。

### 1. 偏差场定义与统计口径

- 偏差定义：$\mathrm{Bias} = \mathrm{OBS} - \mathrm{MME}$，即 CN05.1 观测气候态减去 HiCPC 19 模式等权集合平均气候态。偏差为**正**表示 MME 低估，为**负**表示 MME 高估。
- 时间口径：历史期 1981–2010 年，观测与模式均先取该时段的逐年平均。
- 空间口径：模式场先以面积重叠权重（纬向乘以 $\cos(\mathrm{lat})$）重映射到 CN05.1 网格，再逐格点相减。
- 面积加权：$w = \cos(\mathrm{lat})$，用于区域平均偏差、相对偏差与低估面积占比；未加权均值同时留档。
- 相对偏差 $=$ 面积加权平均偏差 $/$ 观测面积加权气候态 $\times 100\%$（保留符号）。
- 低估面积占比 $=$ 满足 $\mathrm{Bias} > 0$ 的格点面积权重之和占总权重比例。
- 统计表头记录：`period: 1981-2010`、`modes: 19`、`weight: area-weighted, w = cos(lat)`。

本次运行数值（来自 `data/图3_统计数据.txt`，与 `data/fig3_stats.csv` 完全一致）：

| 指标 | 单位 | min | max | 未加权均值 | 面积加权均值 | 观测（面积加权） | MME（面积加权） | 相对偏差 | MME 低估面积占比 | 中位 $\lvert \mathrm{bias}\rvert$ |
|---|---|---|---|---|---|---|---|---|---|---|
| R95 Intensity | mm/day | −56.1482 | 29.2394 | 3.2305 | **+3.3540** | 26.3669 | 23.0128 | +12.72 % | 67.9 % | 3.3962 |
| PrecipVar | mm/day | −11.5604 | 4.1435 | 0.3522 | **+0.3701** | 3.7482 | 3.3781 | +9.87 % | 71.2 % | 0.3423 |

（「面积加权均值」即正文引用的偏差；「MME（面积加权）」由 `观测 − 偏差` 得到。）

色带分级与刻度（现行实现：以 0 为中心、$\pm\max(|\min|,|\max|)$ 对称等分，区间数 R95 为 10、PrecipVar 为 8）：

| 指标 | 分级数 | 色带上下限 | 色带刻度 |
|---|---|---|---|
| R95 Intensity | 11 级（10 区间） | ±56.1482 | −56.1482, −33.6889, 0, 33.6889, 56.1482 |
| PrecipVar | 9 级（8 区间） | ±11.5604 | −11.5604, −5.78021, 0, 5.78021, 11.5604 |

### 2. 绘图实现（Fig3.py 现状）

- 面板布局：1 行 × 2 列；画布 20 cm × 14 cm；单幅地图宽 7.0 cm、高 $7.0 \times$ `map_aspect` cm（`map_aspect` 由区域经纬跨度与中心纬度余弦算得）；列间距 1.6 cm；左边距 1.0 cm；底边 $y = \max(1.0,\ (\text{画布高} - \text{地图高})/2)$。（脚本注释写明这是「对齐 Fig2 格式：20 cm 基准宽度，单幅地图宽 7 cm，列间距 1.6 cm」。）
- 投影与范围：`PlateCarree` 投影，范围取中国边界 bbox 外扩 1°。
- 图层：`contourf` 填色 + 同分级 `contour` 黑线（线宽 0.4）+ 国界（`#888888`，线宽 0.5）+ 经纬网（`draw_labels=True`，线宽 0.3，`alpha=0.4`，虚线，仅左/下标签），并隐藏 `geo` spine。
- 内嵌 PDF 直方图：取有限值并裁剪到色带范围后按同一色带分级统计；`inset_axes` 宽高 0.56 × 0.44，锚点 (0.18, 0.07)，柱宽为分箱宽度的 0.9 倍，柱面用主色带对应颜色、黑边；坐标轴刻度 8 pt，y 轴标签 `PDF` 9 pt；背景透明，去掉上/右边框。
- 面板编号：在坐标轴外左上角写 `(a)`、`(b)`，13 pt；标题为指标名（`R95 Intensity`、`PrecipVar`），14 pt，`pad=8`。
- 色带：置于面板正下方（偏移 0.095），宽度为单幅地图宽 × 0.8，高度 0.02；`BoundaryNorm` + `extend="both"`、`extendfrac=0.04`；取 5 个刻度（四舍五入到最近的 levels 下标，保证以 0 为中心对称），刻度标签由 `_fmt_tick` 统一格式（整数不带小数、非整数保留 1 位小数），色带下方标注单位。
- 统计标注：每幅地图下方居中写 `Mean bias = ±x.xx mm/day`（面积加权区域平均偏差，12 pt）。
- 字体：全局 `Times New Roman`，数学字体 `cm`，`axes.unicode_minus = False`。

### 版式说明 1：全局绘图风格

- 字体族: Times New Roman
- 数学字体: cm
- 负号显示: axes.unicode_minus = False

### 版式说明 2：图件结构

- 图(a): 三行散点图，指标为 CORR、NRMSE、Bias
- 图(b): 2×2 空间分布图
  - 左列: CN05.1
  - 右列: HiCPC-MME
  - 行变量: PrecipVar、R95mm intensity

### 版式说明 3：散点图格式参数（SCATTER_PARAMS）

> 以下为 Fig2 的散点图面板（图 2a）参数，本模块 `Fig3.py` 不含散点图，仅作为沿线沿用的版式依据保留。

#### 3.1 字体

- 纵轴标签字号: 13 pt
- 刻度字号: 12 pt
- 均值标注字号: 12 pt

#### 3.2 线型与标记

- 散点大小: 22 pt²
- 参考均值虚线线宽: 0.6 pt
- 坐标轴 spine 线宽: 0.6 pt
- 网格线: y 方向，颜色 #d0d0d0，线宽 0.3，透明度 0.25

#### 3.3 颜色

- PrecipVar 散点填充/边线: #99bbef / #2596be
- R95mm intensity 散点填充/边线: #e9542c / #d52813
- 均值虚线颜色: PrecipVar 用 #2596be，R95mm intensity 用 #d52813

#### 3.4 子图几何（图a）

- 画布尺寸: 20 cm × 18 cm
- 3 个散点子图，每个尺寸: 15.0 cm × 4.0 cm
- 子图间距（纵向）: 1.0 cm
- 左起始位置: x = 1.0 cm
- 三行底边位置:
  - CORR: y = 13.0 cm
  - NRMSE: y = 8.0 cm
  - Bias: y = 3.0 cm

### 版式说明 4：空间图格式参数（MAP_PARAMS）

#### 4.1 字体

- 列标题字号: 14 pt
- 经纬网刻度字号: 10 pt
- 行统计文字字号: 12 pt
- 色带标签字号: 11 pt
- 行标签字号: 14 pt

#### 4.2 线型

- 经纬网线宽: 0.3 pt
- 国界线宽: 0.5 pt
- 等值线线宽: 0.4 pt

#### 4.3 配色与分级

- R95mm intensity 色带: r95_cmap（10 色）
- PrecipVar 色带: precipvar_cmap（8 色）
- 分级规则:
  - 若跨 0: 以 0 对称分级
  - 若全正: 从真实最小值取整后起步，避免 0 造成负值视觉误导

> 现行 `Fig3.py` 只保留了「以 0 对称分级」这一支：上下限直接取 $\pm\max(|\min|,|\max|)$，不再做整数步长取整、也没有硬编码下限，因此色带两端恰好等于数据极值（R95 取到 −56.1482 一侧）。上面「全正」分支在本模块中不会被触发。
>
> 两条色带的 10 色 / 8 色定义为：`r95_cmap` = #315484 → #568588 → #84B0D3 → #82D1DF → #CCD7BC → #FEF2B6 → #FDC780 → #F58A58 → #D64736 → #992323；`precipvar_cmap` = #7195DB → #D0E8F8 → #90C0D8 → #708A98 → #F5F7F7 → #E2CCB2 → #E9AF99 → #D96E57。

#### 4.4 地图面板细节

- 投影: PlateCarree
- 范围: 中国边界 bbox 外扩 1°
- 纵横比: 按中心纬度余弦修正
- 每个地图内嵌 PDF 直方图:
  - inset 宽高: 0.56 × 0.44（相对坐标）
  - 锚点: (0.18, 0.07)
  - 柱宽: 分箱宽度的 90%
  - 直方图坐标轴字号: 8 pt
  - y 轴标签 PDF: 9 pt

#### 4.5 子图几何（图b）

- 画布尺寸: 20 cm × 14 cm
- 每个地图宽度: 7.0 cm
- 每个地图高度: 7.0 × map_aspect cm（随区域比例计算）
- 两列间距: 1.6 cm
- 两行间距: 2.4 cm
- 左列起点 x: 1.0 cm
- 右列起点 x: 1.0 + 7.0 + 1.6 cm
- 每行底边 y: 1.0 + r × (mh + 2.4)

> 本模块只有 1 行面板，故「两行间距 2.4 cm」与「每行底边 y」的公式未被使用；实际底边取 $\max(1.0,\ (\text{画布高} - \text{地图高})/2)$，使单行在 20 cm × 14 cm 画布中垂直居中。

### 版式说明 5：标签与标题定位

#### 5.1 图(a) 标签

- 文本: (a)
- 位置: figure 坐标 (0.01, 0.995)
- 字号: 16 pt
- 对齐: 左上

#### 5.2 图(b) 标签

- 文本: (b)
- 位置: 以 2×2 地图整体外接框左上角为锚点
  - x = map_left - 0.03
  - y = map_top + 0.07
- 坐标系: fig_b.transFigure
- 字号: 16 pt
- 对齐: 左上

#### 5.3 图(b) 列标题

- 文本: CN05.1、HiCPC-MME
- 位置: 基于顶行地图上边界，y = 顶行 y1 + 0.03
- 字号: 14 pt
- 对齐: 居中下对齐

> 现行 `Fig3.py` 的面板标签改为：`(a)`/`(b)` 以各面板自身位置为锚点（`x = x0 − 0.02`、`y = y1 + 0.02`，figure 坐标），字号 13 pt；面板标题即指标名，字号 14 pt、`pad = 8`，无「CN05.1 / HiCPC-MME」列标题。

### 版式说明 6：统计文字与色带位置

- 每一行地图下方统计文字:
  - 内容: CORR、p 值、NRMSE
  - 位置: 该行地图底边 y0 下方 0.050
- 每一行地图下方水平色带:
  - 宽度: 两列地图总宽的 0.8
  - 位置: 该行地图底边 y0 下方 0.095
  - 高度: 0.02（figure 相对）

> 现行 `Fig3.py`：统计文字位置仍为底边下方 0.050，内容改为 `Mean bias = ±x.xx mm/day`（每个面板各自一条，置于色带上方）；色带位置 0.095、高度 0.02 不变，宽度改为**单幅地图宽 × 0.8**（`cbar_w_ratio = 0.8`，并按面板水平居中）。

### 版式说明 7：导出设置

- 导出目录: fig/svg_components
- 图(a): fig_a.svg
- 图(b): fig_b.svg
- 导出方式: format = svg，bbox_inches = tight

> 该节描述的是 Fig2 的 SVG 拆分导出流程，`fig/` 目录已随扁平化改造删除，本模块不执行该流程。`Fig3.py` 的导出为 `Fig3.jpg`：`format="jpg"`、`dpi=400`、`bbox_inches="tight"`。

### 版式说明 8：维护建议

- 若后续频繁调版式，建议将以下量提升为显式参数:
  - (a)/(b) 标签字号与偏移
  - 图(b) 标题与标签的 y 偏移
  - 图(b) 的列间距与行间距
- 目前 MAP_PARAMS 中的 stat_offset、cbar_offset、cbar_w_ratio、cbar_h 尚未完全替代硬编码位置；如需统一控制，建议改为全部由参数驱动。
