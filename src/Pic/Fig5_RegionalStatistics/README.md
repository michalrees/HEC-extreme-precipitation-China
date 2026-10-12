# 图 5 —— 中国七大地理分区与三大河流流域的极端降水区域统计

本模块产出论文图 5：中国七大地理分区与三大河流流域的区划图（a），以及 2021–2050 年极端降水强度（R95 Intensity）的区域统计柱状图（b）。它回答的问题是：在 SSP1-2.6 / SSP2-4.5 / SSP5-8.5 三个情景下，各分区与流域的面积加权平均极端降水强度有多大、区域间差异如何、模式间不确定性（σ）如何分布——这正是后续层次涌现约束所依据的**先验分布**。结论上，强度呈东南高、西北低的阶梯状：华南最高（约 49.1–49.4 mm/day），华东次之（约 45.0–45.3 mm/day），西北最低（约 10.4–10.5 mm/day），三个排放情景的区域差异均不超过 0.3 mm/day。对应论文第 2 章 Data and Methods 中刻画未来预估先验分布的部分（正文在图 4 之后引用图 5，见 `Doc/Tex/manuscript.tex` 的 `\label{fig:5}`）。

## 目录结构

```
Fig5_RegionalStatistics/
├── Fig5.py                 # 单文件流水线：先做区域面积加权统计（写 CSV），再绘制区划图 (a) 与柱状图 (b)
├── Fig5.jpg                # 论文成品图（正文图 5）
├── data/                   # 代码计算的统计数据（本模块唯一数据文件）
│   └── fig5_regional_stats.csv  # 3 情景 × 11 区域 = 33 行面积加权统计
└── README.md
```

## 运行

```bash
cd "F:\Program\2Process\4HiCPC\Using hierarchical emergent constraints to reduce the uncertainty in future extreme precipitation projections over China"
python "src/Pic/Fig5_RegionalStatistics/Fig5.py"
```
> ⚠️ **前置依赖：必须先运行兄弟模块 Fig4。** `Fig5.py` 统计步骤的输入不是本模块的 `data/`，而是 `src/Pic/Fig4_ProjectionUncertainty/data/fig4_data.npz`（由 Fig4 的 `fig4data.py` 生成），因此完整顺序是：
> ```bash
> python "src/Pic/Fig4_ProjectionUncertainty/fig4data.py"   # 生成 fig4_data.npz
> python "src/Pic/Fig5_RegionalStatistics/Fig5.py"          # 统计 + 绘图，一次运行完成
> ```
> 该 npz 由本模块**只读**使用（代码只 `np.load`，从不写它）：打开/解压失败时（例如 Fig4 正在并发重新生成）会间隔 2 s 重试至多 3 次，仍失败才抛 `RuntimeError`（`raise ... from` 原始异常，npz 缺失即 `FileNotFoundError`）；文件名常量 `FIG4_NPZ` 指向上一级兄弟模块。本模块 CSV 由同一次运行的统计步骤先写出，绘图步骤读它；若单独调用绘图步骤且 CSV 不存在，只打印提示并画出空白 (b) 面板。

依赖：`numpy`、`pandas`、`pyshp`（`import shapefile`）、`shapely`、`matplotlib`（含 `mpl_toolkits.axes_grid1` 内嵌子图工具）、`cartopy`。
脚本用 `Path(__file__).resolve().parents` 自下向上定位仓库根（同时含 `src/` 与 `Doc/`），无需修改路径；上游输入仍取 `ROOT.parent / "Fig4_ProjectionUncertainty" / "data"`，与合并前一致。

## 数据来源

| 文件 | 来源 / 生成脚本 | 说明 |
|---|---|---|
| `data/fig5_regional_stats.csv` | 本模块 `Fig5.py` 的统计步骤生成 | 本模块**唯一**数据文件，且是**计算得到的统计量**（非原始输入）。33 行 = 3 情景 × 11 区域；列为 `Scenario, Region, Weighted_Mean_Intensity, Weighted_Std, Weighted_Variance`；以 `utf-8-sig` 编码写出 |
| `../Fig4_ProjectionUncertainty/data/fig4_data.npz` | 兄弟模块 `src/Pic/Fig4_ProjectionUncertainty/fig4data.py` | **上游输入**（`FIG4_NPZ = ROOT.parent / "Fig4_ProjectionUncertainty" / "data" / "fig4_data.npz"`，即上一级兄弟模块）。读取变量：`lon`、`lat`、`ssp126_mean`、`ssp245_mean`、`ssp585_mean`、`ssp126_std`、`ssp245_std`、`ssp585_std`（同文件中的 `*_var` 本模块未使用）。本模块只读该文件 |
| `Data/China/cnmap.shp` | 仓库根 `Data/` 目录（原始矢量） | 仅绘图步骤使用，绘制中国国界并据此确定地图范围（bbox ±1°） |
| `Data/River/HuanghaiRiver_polygon.shp`<br>`Data/River/PearlRiver_polygon.shp`<br>`Data/River/YangtzeRiver_polygon.shp` | 仓库根 `Data/River/` 目录（原始矢量） | 单文件内两处共用同一常量 `RIVER_FILES`：统计步骤用其构建流域格点掩膜，绘图步骤用其绘制流域边界。对应键名 `YellowRiver` / `PearlRiver` / `YangtzeRiver` |

> 上表中的 `Data/` 指仓库根（含 `src/`、`Doc/` 的目录）下的 `Data/`，**不是**本模块的 `data/`。

## 产出

| 文件 | 内容 |
|---|---|
| `data/fig5_regional_stats.csv` | 逐（情景 × 区域）的面积加权统计：加权平均强度 `Weighted_Mean_Intensity`、加权模式间标准差 `Weighted_Std`、加权模式间方差 `Weighted_Variance`（均保留 3 位小数） |
| `Fig5.jpg` | 论文成品图，12 cm × 16 cm，`dpi=400`。(a) 七大分区彩色范围框 + 三大流域矢量边界 + 左下角图例（2 列）；(b) 11 组 × 3 情景分组柱状图（误差棒 = 模式间 σ，y 轴 0–70 mm/day），左上角嵌入华南放大子图并用水平箭头指向华南柱组 |

## 代码说明

本模块为**单文件流水线**，全部代码都在 `Fig5.py` 内，`main()` 严格按「先统计、后绘图」两步执行：

| 脚本 | 作用 | 主要产出 |
|---|---|---|
| `Fig5.py` | `main()` → `compute_regional_stats()`（统计）+ `plot_figure()`（绘图）：统计步骤读取 Fig4 的 `fig4_data.npz`，对 8 个经纬度框（含中国全域参考行）与 3 个流域多边形掩膜用 $\cos\varphi$ 做面积加权平均，逐情景输出加权均值、模式间 σ 与方差；绘图步骤读取上一步写出的 CSV 与仓库矢量，绘制 (a) 区划图、(b) 区域统计柱状图及华南放大子图 | `data/fig5_regional_stats.csv`（33 行）+ `Fig5.jpg` |

主要函数（均在 `Fig5.py` 内，共用同一命名空间）：

| 函数 | 作用 |
|---|---|
| `load_fig4_data()` | 只读加载 `../Fig4_ProjectionUncertainty/data/fig4_data.npz`，把 `lon`、`lat` 与各情景 `_mean`/`_std` 一次性读入内存；失败重试至多 3 次 |
| `build_river_mask()` | 用 `shapefile` + `shapely` 为单个流域多边形构建格点布尔掩膜 |
| `area_weighted_stats()` | 对掩膜内有限值格点做 $\cos\varphi$ 面积加权平均，返回（均值, σ, 方差）三元组 |
| `compute_regional_stats()` | 统计步骤：8 个经纬度框 + 3 个流域 × 3 情景，写出 `data/fig5_regional_stats.csv` |
| `plot_figure()` | 绘图步骤：加载矢量与 CSV，绘制并保存 `Fig5.jpg` |
| `main()` | 依次调用统计、绘图两步 |

补充说明：

* 合并后只保留一份区域定义：`REGIONS` 为七大地理分区，中国全域参考行单独定义为 `CHINA_REGION = ("China", -90, 90, -180, 360)`；统计时按 `[CHINA_REGION] + REGIONS` 的顺序处理（与合并前 `calc_regional_stats.py` 的 8 框顺序一致），绘图时把 `China` 单独提出、置于柱状图最左侧。
* 河流流域只保留一份定义 `RIVER_FILES`（合并前的 `RIVER_BASINS` 与 `RIVER_FILES` 文件名、键名、顺序完全相同）：统计步骤用它建格点掩膜，绘图步骤用它画流域边界。
* 情景表也只保留一份：`SCENARIO_KEYS`（npz 变量前缀 `ssp126/ssp245/ssp585`）与 `SCENARIOS`（显示名 `SSP1-2.6/SSP2-4.5/SSP5-8.5`）按下标一一对应；`REPO_ROOT`、`DATA_ROOT`、`river_dir` 等合并前重复且等价的定义已统一。
* 面积加权公式集中在 `area_weighted_stats()`，经纬度框与流域掩膜共用同一实现（均值场与 σ 场各自使用自己的有限值掩膜），数值口径与合并前逐字一致。
* (b) 面板的柱状图区域顺序为 `China` + 七大分区 + 三大流域，代码注释标明该行序**与正文图 6 热力图一致**，便于两图对照。
* 配色固定：七大分区用 `plt.cm.Set2` 取样，流域用 `#1f77b4`（黄河）/`#d62728`（珠江）/`#2ca02c`（长江），情景用 `#4C9AC9`（SSP1-2.6）/`#F3A161`（SSP2-4.5）/`#D64736`（SSP5-8.5）。
* 华南放大子图的纵轴范围由华南三情景数值驱动（留 35% 边距），锚点高度按「子图与华南柱之间最高柱（含误差棒）+ 0.6」自动计算并在运行时打印，避免压住柱子。
* 注意：合并前 `Fig5.py` 的模块 docstring 首行沿用旧文字写作 “Fig. 4 (a) 中国七大地理分区区划图……”；单文件化后 docstring 已重写为「图 5 单文件流水线」说明（统计 → 绘图 → 产出 `Fig5.jpg`）。
* 关于区划的横向一致性：`Fig5.py` 内的行内注释写作「与 Fig8/Fig9/Fig10 完全一致」，而 `doc/区划说明.md` 写作 `Fig9.py` / `Fig10.py` / `Fig11.py`；两处表述不同，但四至数值相同（见下节）。

## 方法说明

> 本节完整保留原 `doc/区划说明.md` 的内容（该 `doc/` 目录已废弃，内容并入此处），并补充了依据 `Fig5.py` 统计步骤整理的统计口径。

### 区域体系（2026-09-17 更新）

由原「8 个气候子区域 + 三大流域」改为 **标准七大地理分区 + 三大流域**：

* **删除**：东部季风区（EastMonsoon）、江淮（MiddleLowerYangtze）、青藏高原（TibetanPlateau）；
* **新增**：华东（EastChina）、华中（CentralChina）。

四至范围与 `Fig9.py` / `Fig10.py` / `Fig11.py` 完全一致，且各分区互不重叠（相邻分区仅共边）。

### 标准区域划分

| 区域 | 英文名 | 纬度范围 | 经度范围 | 说明 |
|------|--------|----------|----------|------|
| 华北 | NorthChina | 35°N – 42°N | 110°E – 118°E | 东界由 120°E 收到 118°E，以消除与东北的交叠 |
| 东北 | Northeast | 38°N – 54°N | 118°E – 135°E | |
| 西北 | Northwest | 35°N – 50°N | 73°E – 105°E | |
| 西南 | Southwest | 21°N – 35°N | 95°E – 108°E | |
| 华东 | EastChina | 27°N – 35°N | 115°E – 123°E | 原「江淮」由华东 + 华中两块取代 |
| 华南 | SouthChina | 18°N – 26°N | 108°E – 120°E | |
| 华中 | CentralChina | 26°N – 34°N | 108°E – 115°E | 新增；东界取 115°E，以消除与华东的交叠 |
| 中国全境 | China | 全格点 | 全格点 | 仅作柱状图/热力图的参考行，不掩膜 |

### 重叠核对

七区两两全部无面积交叠（21 组逐对自检通过）。为此在沿用 Fig8–9 四至的基础上做了两处最小裁剪：**华北东界 120°E → 118°E、华中东界 116°E → 115°E**；其余 5 个分区（东北、西北、西南、华东、华南）与 `Fig9.py`/`Fig10.py`/`Fig11.py` 完全一致。

### 河流流域（多边形精确掩膜）

| 流域 | 键名 | shapefile | 范围 |
|------|------|-----------|------|
| 黄河流域 | YellowRiver | `Data/River/HuanghaiRiver_polygon.shp` | 95.88–119.88°E, 32.38–42.62°N |
| 长江流域 | YangtzeRiver | `Data/River/YangtzeRiver_polygon.shp` | 90.62–121.88°E, 24.38–35.88°N |
| 珠江流域 | PearlRiver | `Data/River/PearlRiver_polygon.shp` | 102.38–117.12°E, 20.38–26.88°N |

> 黄河的 shapefile 文件名沿用旧名 `HuanghaiRiver_polygon.shp`（图上曾误标为 “Huanghai Basin / 黄海”），但其经纬度范围即为黄河流域，故图例与横轴已统一显示为 **Yellow River Basin**。

流域掩膜的构造方式：用 `shapefile` + `shapely` 读入全部多边形并 `unary_union` 合并，先用合并后的外包框（bounds）对格点做粗筛，再对粗筛内的格点逐点做 `contains(Point(lon, lat))` 精确点包含判断，得到布尔掩膜（`build_river_mask()`）；`Fig5.py` 的统计步骤运行时打印每个流域命中的格点数。

### 面积加权统计口径（依据 `Fig5.py` 的 `area_weighted_stats()`）

对每个区域 $r$，以格点纬度余弦为权重 $w_i=\cos\varphi_i$，并对该区域掩膜 $m_i$ 内**有限值**的格点求加权平均（均值场与 σ 场各自使用自己的有限值掩膜）：

$$\bar{X}_r=\frac{\sum_{i\in r} X_i\,w_i\,m_i}{\sum_{i\in r} w_i\,m_i}$$

三个输出列分别对应：

| 列 | 计算对象 | 含义 |
|---|---|---|
| `Weighted_Mean_Intensity` | 集合平均强度场 `{ssp}_mean` | 区域面积加权平均极端降水强度（mm/day） |
| `Weighted_Std` | 模式间标准差场 `{ssp}_std` | 逐格点 σ 的面积加权平均（mm/day），柱状图误差棒即用此列 |
| `Weighted_Variance` | 模式间方差场 $\sigma^2$ | 逐格点模式间方差的面积加权平均（(mm/day)²），**留档用，不参与绘图** |

> 注意 `Weighted_Variance` 不是 `Weighted_Std` 的平方：两列分别对 $\sigma^2$ 场与 $\sigma$ 场取加权平均，由 Jensen 不等式 $\overline{\sigma^2}\ge\bar{\sigma}^2$。例如中国全域 SSP1-2.6 的 `Weighted_Std` = 2.003、`Weighted_Variance` = 5.254（而 $2.003^2\approx4.012$）。**全文统一按 σ 报告**，方差列仅作留档。

另按 `Doc/Tex/formatting-notes.md` 的口径记录：图 4 / 图 5 报告的区域平均 σ 为**自算的全尺度合计值（恒为正）**，与图 11 尺度分解中「不含流域」的 σ 口径不同，两者不可逐位比较。

### 参考来源

验证状态说明：

1. Shi, X., Lu, C., & Xu, X. (2011). Variability and Trends of High Temperature, High Humidity, and Sultry Weather in the Warm Season in China during the Period 1961–2004. *Journal of Applied Meteorology and Climatology*, 50(1), 127–143. doi: [10.1175/2010JAMC2345.1](https://doi.org/10.1175/2010JAMC2345.1)
   - ✅ 已验证 — 华南（27.5°N 以南、107.5°E 以东）、江淮、西南的分区边界
2. Wang, T., Zhou, D., & Shen, X. (2021). Spatial-temporal variations of Köppen climate types in China. *Terrestrial, Atmospheric and Oceanic Sciences (TAO)*, 32(4), 483–496. doi: [10.3319/TAO.2021.10.18.01](https://doi.org/10.3319/TAO.2021.10.18.01)
   - ✅ 已验证 — 中国 Köppen 气候分类背景
3. Liu, C. & Shi, R. X. (2016). 中国综合自然地理区划四大生态地理区界线数据集. *Global Change Research Data Publishing & Repository*. doi: [10.3974/geodb.2016.04.21.V1](https://doi.org/10.3974/geodb.2016.04.21.V1)
   - ✅ 已验证 — 原「东部季风区」以 400mm 等降水线（~100°E）为界（该区已删除）
4. Feng, Y. & Du, S. (2020). Climate Changes and Landscape Responses of China During the Past 40 Years (1979–2018) Under Köppen-Geiger Climate Classification. *ISPRS Annals*, V-3-2020, 731–737. doi: [10.5194/isprs-annals-v-3-2020-731-2020](https://doi.org/10.5194/isprs-annals-v-3-2020-731-2020)
   - ✅ 已验证 — 0.1° 分辨率 Köppen 分类
5. 青藏高原范围 — 中国科学院青藏高原研究所（该区已从图 4/图 6 的区域体系中删除）: [https://itpcas.cas.cn/new_kxcb/new_kpwz/202012/t20201211_5814695.html](https://itpcas.cas.cn/new_kxcb/new_kpwz/202012/t20201211_5814695.html)
