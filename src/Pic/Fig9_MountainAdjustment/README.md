# 图 9 —— 山脉分区极端降水调整场组图

本图展示分层涌现约束（HEC）在 SSP2-4.5 情景下对中国极端降水强度（R95 Intensity，mm/day）预估的调整量，即后验均值与先验均值之差（Bias = Posterior − Prior），用于回答"约束调整量在空间上如何分布、是否受局地地形控制"这一问题。它是"全国图 + 若干山脉分区放大面板"的组图：(a) 为全国分布，用七色线框标出七个地理分区、右下角标注正向调整格点占比；(b)–(h) 依次为华北太行山、东北长白山、西北天山、西南横断山、华东武夷山、华南五指山、华中武陵山的分区放大图，并叠加区内主要山脉矢量，以评估地形对约束调整幅度的影响。本图对应论文结果章 §3.1 Hierarchical Emergent Constraints（`Doc/涌现约束_v2.md` 中的 `## 3.1`；`Doc/Tex/manuscript.tex` 中的 `\subsection{Hierarchical Emergent Constraints}`），论文成品图为模块根下的 `Fig9.jpg`。

## 目录结构
```
Fig9_MountainAdjustment/
├── Fig9.py                          # 单文件流水线：渲染 8 个面板（运行期临时）→ 拼合 Fig9.jpg → 输出统计 CSV
├── Fig9.jpg                         # 论文成品图（组图）
├── data/                            # 原始数据 + 代码计算的统计数据
│   ├── CN_MountainRanges_WGS84.shp  # WGS84 山脉矢量主文件（供 Fig9.py 读取）
│   ├── CN_MountainRanges_WGS84.shx  # 形状索引（shapefile 的一部分）
│   ├── CN_MountainRanges_WGS84.dbf  # 属性表：140 条要素，字段 Id / Name / Rank / TypeName / Type
│   ├── CN_MountainRanges_WGS84.prj  # 坐标参考：WGS 84（EPSG:4326），WKT2 文本
│   └── fig9_stats.csv               # Fig9.py 计算的 (b)–(h) 七分区偏差统计量
└── README.md
```
模块根目录下**恰好只有上列 4 项**：`Fig9.py`、`Fig9.jpg`、`data/`、`README.md`。8 张单面板 JPG（`Fig9a_China.jpg` 与 `Fig9b_Taihang.jpg` … `Fig9h_Wuling.jpg`）只是拼合组图的**运行期中间产物**：`main()` 用 `_panel_temp_dir()` 提供的临时目录存放，`compose_fig9()` 从该目录读取面板拼出 `Fig9.jpg`，运行结束（含异常退出）临时目录连同面板一并自动清理，**不再落盘到模块根**。

## 运行
```bash
cd "F:\Program\2Process\4HiCPC\Using hierarchical emergent constraints to reduce the uncertainty in future extreme precipitation projections over China"
python "src/Pic/Fig9_MountainAdjustment/Fig9.py"                        # 主流程：8 个面板（临时）→ Fig9.jpg + 统计 CSV
python "src/Pic/Fig9_MountainAdjustment/Fig9.py" --reproject-mountains  # 可选的一次性预处理（当前无法运行，见下）
```
依赖：`cartopy`、`matplotlib`、`numpy`、`xarray`、`pyproj`、`shapely`、`pyshp`（`import shapefile`）、`pandas`（写 CSV）、`Pillow`（`PIL`）、`scipy`。

脚本用 `Path(__file__).resolve().parents` 自下向上定位仓库根（同时含 `src/` 与 `Doc/`），无需修改路径。三个步骤现已合并进同一个 `Fig9.py`，共用一套路径常量与命名空间：不带参数的默认运行按固定顺序执行 `render_panels()`（渲染 8 个单面板 JPG + 写 `data/fig9_stats.csv`）→ `compose_fig9()`（读取这些面板 JPG 拼合 `Fig9.jpg`），一次运行即可复现论文组图与统计表，无需再分两步手动执行。

运行期落盘情况：8 张单面板 JPG 只写进 `_panel_temp_dir()` 提供的**临时目录**（首选 `tempfile.TemporaryDirectory()`；少数受限环境拒绝写入 tempfile 的 0o700 私有目录时，自动退回系统临时根下自建目录），`with` 块退出（含异常退出）即自动清理，**模块根目录始终只有 `Fig9.py`、`Fig9.jpg`、`data/`、`README.md` 四项**；最终落盘的只有 `Fig9.jpg` 与 `data/fig9_stats.csv`。

`--reproject-mountains` 对应原独立脚本 `reproject_mountains_to_wgs84.py` 的一次性预处理功能（`reproject_mountains_to_wgs84()` 函数），**默认不执行**，也不会进入绘图流程；其源 shapefile 在当前仓库中已不存在，当前无法重跑，详见下方"数据来源"的**注意**。

## 数据来源
| 文件 | 来源 / 生成脚本 | 说明 |
|---|---|---|
| `data/CN_MountainRanges_WGS84.shp` / `.shx` / `.dbf` | `Fig9.py --reproject-mountains`（`reproject_mountains_to_wgs84()`） | 由 Albers 等面积投影（中央经线 105°、标准纬线 30°/40°、原点纬度 27.5°）重投影到 WGS84（EPSG:4326）；`.shp` 为几何、`.shx` 为索引、`.dbf` 为属性表（140 条要素，字段 `Id`、`Name`、`Rank`、`TypeName`、`Type`） |
| `data/CN_MountainRanges_WGS84.prj` | `Fig9.py --reproject-mountains`（`reproject_mountains_to_wgs84()`） | 以 `dst_crs.to_wkt()` 写入的 WGS 84 坐标定义（WKT2） |
| `data/fig9_stats.csv` | `Fig9.py`（默认运行 `render_panels()`） | 代码计算的 (b)–(h) 七个分区的偏差统计（格点数、面积加权平均、最小/最大值、正向格点占比），编码 `utf-8-sig` |
| `Output/EC/China/HEC_ssp126_PrecipVar_to_R95mm_intensity.nc`（模块外） | 上游"脚本 6"的分层涌现约束输出（2021–2050） | 仅用于确定全局共享色标的取值范围 |
| `Output/EC/China/HEC_ssp245_PrecipVar_to_R95mm_intensity.nc`（模块外） | 同上 | 实际绘制的场：`posterior_mean`、`prior_mean`、`p_value`、`lon`、`lat` |
| `Output/EC/China/HEC_ssp585_PrecipVar_to_R95mm_intensity.nc`（模块外） | 同上 | 仅用于确定全局共享色标的取值范围 |
| `Data/China/cnmap.shp`（模块外） | 仓库 `Data/` 下的中国国界矢量 | 提供国界轮廓几何与全国 bbox（外扩 1° 作为 (a) 面板范围） |

> **注意**：山脉矢量重投影（`reproject_mountains_to_wgs84()`，由 `--reproject-mountains` 触发）的源数据 `Data/山脉走势数据/中国主要山脉【山脉数据】/CN_MountainRanges/CN_MountainRanges.shp` **在仓库中已不存在**，该步骤无法重跑，因此被放在标志之后**默认不执行**——不带参数的 `python Fig9.py` 不会进入该分支；绘图实际消费的是 `data/` 下已重投影好的 `CN_MountainRanges_WGS84.*` 派生文件，因此主流程不依赖源 shapefile。

## 产出
本模块**落盘**的产物只有两项（与"目录结构"一致）：

| 文件 | 内容 |
|---|---|
| `Fig9.jpg` | 论文成品组图，2660 × 1916 px、400 dpi，由 `Fig9.py` 主流程的 `compose_fig9()` 在渲染完 8 个面板后自动拼合：(a) 全国 Bias 场（七分区线框 + 分区标号 `(b)`–`(h)`、左下角图例（地区 + 山名）、右下角 `Bias>0` 正向格点占比、底部水平色标 `Bias (mm/day)`）；(b)–(h) 依次为华北太行山、东北长白山、西北天山、西南横断山、华东武夷山、华南五指山、华中武陵山的分区放大图，均叠加区内主要山脉矢量 |
| `data/fig9_stats.csv` | (b)–(h) 七分区偏差统计表（`panel`、`region_key`、`region_en`、`mtn`、`n_grid`、`mean_area_weighted`、`vmin`、`vmax`、`pct_bias_positive`） |

8 张单面板 JPG（`Fig9a_China.jpg`、`Fig9b_Taihang.jpg` … `Fig9h_Wuling.jpg`）**不再作为本模块的落盘产物**：它们只是拼合 `Fig9.jpg` 的**运行期中间产物**，仅存在于 `_panel_temp_dir()` 提供的临时目录中（文件名与上表历史一致），运行结束即随临时目录一并删除，因此模块根目录里不会出现它们。

## 代码说明
本模块只有 `Fig9.py` 一个脚本（原 `Fig9.py`、`compose_fig9.py`、`reproject_mountains_to_wgs84.py` 已合并为一个文件，共用同一命名空间与路径常量），入口为 `main()`，其行为由 `--reproject-mountains` 标志切换：

| 函数（均在 `Fig9.py` 内） | 作用 | 主要产出 |
|---|---|---|
| `main()` | 单文件入口：默认在 `_panel_temp_dir()` 临时目录里依次调用 `render_panels()` → `compose_fig9()`（顺序不可颠倒）；带 `--reproject-mountains` 时只调用 `reproject_mountains_to_wgs84()` 后返回 | `Fig9.jpg` + `data/fig9_stats.csv`（8 张面板为临时产物，不落盘） |
| `render_panels(panel_dir)` | 读取 SSP2-4.5 的 `posterior_mean`/`prior_mean` 求差得到 Bias 场，绘制全国图与七个分区放大图（写入 `panel_dir` 临时目录），并计算各分区统计量 | 临时目录中的 `Fig9a_China.jpg`、`Fig9b_Taihang.jpg` … `Fig9h_Wuling.jpg`；`data/fig9_stats.csv` |
| `compose_fig9(panel_dir)` | 以作者原组图中各面板"地图框"位置为锚点，缩放并精确对位粘贴 8 个面板（从 `panel_dir` 读取） | `Fig9.jpg` |
| `_panel_temp_dir()` | 提供存放单面板的临时目录并在退出时自动清理：首选 `tempfile.TemporaryDirectory()`，受限环境（拒绝写 0o700 私有目录）自动退回系统临时根下自建目录 | — |
| `reproject_mountains_to_wgs84()` | 一次性预处理（`--reproject-mountains` 触发，**默认不执行**）：把 Albers 等面积投影的山脉矢量重投影为 WGS84，保留原属性字段 | `data/CN_MountainRanges_WGS84.shp/.shx/.dbf/.prj` |

提示：合并时已把模块 docstring 与分节注释里的旧称 "Fig8" 统一为 "Fig9"；`_draw_map()` 中按长度映射线宽的 `min_len`/`max_len`/`min_w`/`max_w` 属历史遗留变量，实际绘制线宽固定为 1.0 磅（见"方法说明"）。

## 方法说明

### 调整量场与共享色标

绘图量为后验均值与先验均值之差 $\mathrm{Bias} = \overline{P}_{\text{post}} - \overline{P}_{\text{prior}}$，取自 SSP2-4.5 的 `HEC_ssp245_PrecipVar_to_R95mm_intensity.nc`。色标不是按单情景自适应，而是先用三个情景（`ssp126`、`ssp245`、`ssp585`）的 Bias 全体格点求全局极值：当极值满足 `global_min < -1` 且 `global_max > 1` 时，取 $half = \max(|\text{global\_min}|, |\text{global\_max}|)$，用 `_diverging_bounds(half, inner=(1.0, 6.0))` 构造以 0 为中心、近 0 密两端疏的对称分级 $[-half, -6, -1, 1, 6, half]$（当前渲染为 $[-40.5, -6, -1, 1, 6, 40.5]$，即 5 个色块 + 两端 extend 箭头）；颜色由 5 个锚点 `#315484 → #84B0D3 → #E7F2F6 → #F58A58 → #992323` 线性插值采样，与图 6(c) 的分级配色口径统一。若极值条件不满足，则退化为在 $[\text{global\_min}, \text{global\_max}]$ 上等分 12 个边界、直接使用 `DELTA_COLORS` 的 11 色列表。色标刻度只标注首尾实际极值、$\pm 1$，以及分级边界中出现的 $\pm 6$（或 $\pm 16$），并统一按 `_fmt_tick` 格式化（整数不带小数、非整数保留 1 位）。8 个面板共用同一套 `bounds` 与 `colors`，因此面板之间颜色可直接比较。

所有面板还把 p 值图层的非显著格点（`np.isfinite(p_value) & (p_value >= 0.05)`）以半透明灰色（alpha 0.55）叠加标示，并叠加 `Data/China/cnmap.shp` 的黑色国界轮廓；经纬网格用虚线网格线并关闭上/右边标签。

### 山脉矢量的加载、长度计算与筛选

`_load_mountain_geoms()` 用 `shapefile.Reader` 读取 `data/CN_MountainRanges_WGS84.shp` 的全部要素，转成 shapely 几何后，用 `pyproj.Geod(ellps="WGS84")` 的 `inv()` 逐段累加测地线长度（单位：米），按几何类型分别处理 `LineString`、`MultiLineString`、`Polygon`、`MultiPolygon`，返回 `(geom, length_m)` 列表。`_filter_mountains_in_extent()` 再按几何**质心**是否落在该分区 `extent` 内筛选，得到每个分区要叠加的山脉子集。绘制时山脉线为 `#7e5b42` 色、alpha 0.9；代码中保留了按长度映射线宽的 `min_w/max_w` 与 min/max 长度计算，但实际绘制线宽被统一固定为 1.0 磅。

### 分区统计量（`data/fig9_stats.csv`）

统计对象是**调整量格点值 $\Delta$**（不是 R95 强度本身），只对 (b)–(h) 七个分区计算，不做全国汇总。对每个分区，用一维 `lon`/`lat` 生成的 `Lon`/`Lat_grid` 网格取矩形掩膜（`extent` 为 `(lon_min, lon_max, lat_min, lat_max)`），并剔除 `NaN` 格点：

- `n_grid`：掩膜内有效格点数；
- `mean_area_weighted`：面积（余弦纬度）加权平均 $\bar{\Delta} = \dfrac{\sum_i \Delta_i \cos\varphi_i}{\sum_i \cos\varphi_i}$，其中权重由一维 `lat` 的 $\cos\varphi$ 广播到经向；
- `vmin` / `vmax`：掩膜内 $\Delta$ 的最小/最大值；
- `pct_bias_positive`：$\Delta > 0$ 的格点占有效格点的百分比。

(a) 面板右下角的 `Bias>0:` 数值则是全国口径、按格点计数（非面积加权）的正偏差格点占比，在 `Fig9.py` 中单独计算。

### 组图版式的锚定与拼合

`Fig9.py` 的 `compose_fig9()`（原 `compose_fig9.py`）复现作者的手工版式，核心是"以地图框为锚点、按宽度等比缩放后精确对位粘贴"：

1. `map_box()` 在单个面板 JPG 上检测地图框——灰度阈值 120 取暗色像素做连通域标记，挑选"面积最大且填充率低（< 0.30，即只有框线）"、且宽 ≥ 150 px、高 ≥ 100 px 的连通域，返回其 `(x0, y0, x1, y1)`。
2. `TARGETS` 保存各面板在作者原组图中的地图框目标矩形（像素），缩放比 $s = \dfrac{\text{目标框宽}}{\text{检测框宽}}$，即按框宽对齐。
3. 粘贴位置为 $(\text{tx0} - \text{mx0}\cdot s,\ \text{ty0} - \text{my0}\cdot s)$，即让缩放后的检测框左上角落在目标框左上角。
4. `content_mask()` 在粘贴时把近白像素（灰度 ≥ 250）设为透明，只贴实际内容——面板标题加长后各面板 JPG 变宽，整块矩形贴图的白边会压住相邻面板的框线与标号，改用内容掩膜后重叠区的被盖内容全部恢复。
5. 若某面板框线检测失败，则退回按其余面板的**中位缩放**居中放置到目标框中心。
6. 画布固定为 `CANVAS = (2660, 1916)`（2026-10-11 由 2525 加宽——面板标题由"山名"改为"地区 + 山名"后单行标题右缘达 2642 px，原画布会裁掉末几字；面板锚点一律不动，左移会压住 (a) 面板右下角的 `Bias>0` 标框）。PIL 保存不会自带 DPI 元数据，脚本显式写入 `dpi=(400, 400)`。

各面板锚点（原组图像素坐标，`(x0, y0, x1, y1)`）：

| 面板 | 检测/粘贴目标框 | 分区 | 山名 |
|---|---|---|---|
| `Fig9a_China` | (823, 189, 1873, 801) | 全国 | — |
| `Fig9b_Taihang` | (2060, 726, 2492, 1029) | North China | Taihang Mountains |
| `Fig9c_Changbai` | (2102, 147, 2483, 505) | Northeast | Changbai Mountain |
| `Fig9d_Tianshan` | (130, 179, 562, 384) | Northwest | Tianshan Mountains |
| `Fig9e_Hengduan` | (193, 635, 526, 993) | Southwest | Hengduan Mountains |
| `Fig9f_Wuyi` | (1913, 1469, 2272, 1827) | East China | Wuyi Mountains |
| `Fig9g_Wuzhi` | (425, 1473, 857, 1763) | South China | Wuzhi Mountain |
| `Fig9h_Wuling` | (1212, 1451, 1570, 1809) | Central China | Wuling Mountains |

### 分区范围、标号与图幅

七个分区按"地区 + 山名"绑定，标号 `(b)`–`(h)` 由 `PANEL_LETTERS = "bcdefgh"` 决定，与 (a) 面板上写在每个线框中心的标号、以及 (a) 面板左下角图例一一对应；图例条目格式为 `(b) North China Taihang Mountains`，为不遮挡 (e) 西南分区框，图例字号为 5 磅。(a) 面板宽 10 cm、高宽比 6.2/7；各分区小图宽 4 cm、高宽比 5/6；输出 DPI 均为 400，保存时用 `bbox_inches="tight"`。

| 分区 key | 图上标签 | 分区范围 extent (lon_min, lon_max, lat_min, lat_max) | 线框颜色 | 网格线刻度 (经度 / 纬度) |
|---|---|---|---|---|
| `NorthChina` | North China | (110, 118, 35, 42) | `#E76254` | 112/114/116/118/120 ; 36/38/40/42 |
| `Northeast` | Northeast | (118, 135, 38, 54) | `#EF8A47` | 120/125/130/135 ; 40/45/50 |
| `Northwest` | Northwest | (73, 105, 35, 50) | `#FFD06F` | 75/85/95/105 ; 35/40/45/50 |
| `Southwest` | Southwest | (95, 108, 21, 35) | `#AADCE0` | 98/102/106 ; 22/26/30/34 |
| `EastChina` | East China | (115, 123, 27, 35) | `#72BCD5` | 116/118/120/122 ; 28/30/32/34 |
| `SouthChina` | South China | (108, 120, 18, 26) | `#528FAD` | 108/112/116/120 ; 18/20/22/24/26 |
| `CentralChina` | Central China | (108, 115, 26, 34) | `#376795` | 108/112/116 ; 26/28/30/32/34 |

### 图注与结论要点（与论文一致）

论文图注：分层涌现约束（HEC）在 SSP2-4.5 情景下对极端降水强度（R95 Intensity）的调整量（Bias = Posterior − Prior）。(a) 全国分布，线框为七个分区，编号 (b)–(h) 与左侧图例对应，自 (b) 至 (h) 依次为华北太行山、东北长白山、西北天山、西南横断山、华东武夷山、华南五指山、华中武陵山；右下角为正向调整格点占比。(b–h) 各分区放大图，叠加区内主要山脉矢量。

论文对结果的表述（§3.1 中图 9 所在段落）：后验调整量整体呈"从东南沿海向西北内陆递减"的总体格局；地形依赖在不同区域差异显著——华北太行山、东北长白山及西北天山沿线表现出清晰的迎风坡正向调整增强特征；而华东武夷山、华南五指山及华中武陵山区域，调整量的空间分布与地形之间的对应关系并不明显，其调整幅度主要由大尺度环流背景而非局地地形主导。这一格局与已有研究中"复杂地形区降水模拟偏差与次网格地形拖曳过程相关"的机制一致。

`data/fig9_stats.csv` 中七分区的面积加权平均调整量与该叙述相符：西北天山最小（约 1.08 mm/day），华南五指山最大（约 7.11 mm/day），华东武夷山与华中武陵山居中（约 4.64、4.70 mm/day）；七个分区的正向格点占比均在 82% 以上（西北天山 82.15% 最低，华中武陵山 99.16% 最高）。相邻的图 8 段落给出的区域口径区间为"华南和珠江流域最大（约 5.4–7.1 mm/day）、西北最小（约 1.0–1.1 mm/day）"。
