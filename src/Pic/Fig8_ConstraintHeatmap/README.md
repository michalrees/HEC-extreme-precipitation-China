# 图 8 —— 分区域约束效果热力图（Regional Constraint Heatmap）

本模块绘制论文图 8：分层涌现约束（HEC）在中国各区域/流域上的**约束效果热力图**。行方向为
11 个区域（中国全域、七大分区，以及黄河流域、珠江流域、长江流域），列方向为三个 SSP 情景
（SSP1-2.6、SSP2-4.5、SSP5-8.5），三个面板分别展示区域平均的
(a) 相关系数 $r$、(b) 不确定性（$\sigma$）缩减率、(c) 后验−先验调整量（Bias $=$ Posterior $-$ Prior）。
它回答的问题是：约束效果在区域之间是否存在系统性的空间格局（南高北低），以及这种格局在各排放情景间是否稳定。
该图位于正文 **3.1 节 Hierarchical Emergent Constraints**（Results 第一小节），紧接图 7、先于图 9，
作用是把图 6 的逐格点结论落到区域尺度上。

> 说明：论文图注写作"10 个子区域/流域"，指的是 7 个分区 + 3 个流域；热力图实际为 **11 行**，
> 因为另有"中国全域（China）"一行。

## 目录结构
```
Fig8_ConstraintHeatmap/
├── Fig8.py                 # 单文件流水线：先按区域做 cos φ 面积加权统计写出 CSV，
│                           # 再读取该 CSV 绘制 11×3 三面板热力图并保存 Fig8.jpg
├── Fig8.jpg                # 论文成品图
├── data/                   # 代码计算的统计数据
│   └── fig8_regional_stats.csv  # 3 情景 × 11 区域的面积加权均值/标准差（33 行）
└── README.md
```

> 说明：原先拆分的 `calc_regional_stats.py`（统计）与 `Fig8.py`（绘图）已合并为**单个** `Fig8.py`，
> 由 `main()` 按「先统计、后绘图」的固定顺序依次调用 `calc_regional_stats()` 与 `plot_heatmap()`；
> 导入本模块不会触发任何计算或绘图。

## 运行
```bash
cd "F:\Program\2Process\4HiCPC\Using hierarchical emergent constraints to reduce the uncertainty in future extreme precipitation projections over China"
python "src/Pic/Fig8_ConstraintHeatmap/Fig8.py"
```
**单文件内两步顺序固定、不可颠倒**：`main()` 先执行统计 `calc_regional_stats()`（写 `data/fig8_regional_stats.csv`），
再执行绘图 `plot_heatmap()`（读该 CSV 出 `Fig8.jpg`）。绘图依赖统计产物，故由 `main()` 串联一次跑完；
模块级只定义常量与函数，`import Fig8`（或 `from Fig8 import plot_heatmap`）不会触发计算或绘图。

依赖：`numpy`、`pandas`、`xarray`、`pyshp`（`import shapefile`）、`shapely`、`matplotlib`。

脚本用 `Path(__file__).resolve().parent` 定位模块目录，读写本模块内的 `data/fig8_regional_stats.csv` 与 `Fig8.jpg`；
同时用 `Path(__file__).resolve().parents` 自下向上定位仓库根（同时含 `src/` 与 `Doc/`），以定位 `Output/` 与 `Data/`，无需修改路径。

## 数据来源
| 文件 | 来源 / 生成脚本 | 说明 |
|---|---|---|
| `Output/EC/China/HEC_{ssp126,ssp245,ssp585}_PrecipVar_to_R95mm_intensity.nc` | `src/pipeline/6中国区域分层涌现约束.py`（脚本 6 的 2021–2050 规范输出） | 逐格点 HEC 诊断场，含 `r`、`p_value`、`prior_mean`、`posterior_std`、`posterior_mean`、`reduction` 等变量；网格 `lon`/`lat` 坐标取自第一个情景文件 |
| `Data/River/HuanghaiRiver_polygon.shp` | 外部矢量数据 | 黄河流域多边形。文件名沿用 `HuanghaiRiver`，但范围为黄河流域，显示名统一为 `YellowRiver`（"Yellow River Basin"） |
| `Data/River/PearlRiver_polygon.shp` | 外部矢量数据 | 珠江流域多边形（显示名 `PearlRiver`，"Pearl Basin"） |
| `Data/River/YangtzeRiver_polygon.shp` | 外部矢量数据 | 长江流域多边形（显示名 `YangtzeRiver`，"Yangtze Basin"） |
| `data/fig8_regional_stats.csv` | 由本模块 `Fig8.py` 的 `calc_regional_stats()` 生成 | 本模块中间产物，也是同一文件中 `plot_heatmap()` 的唯一输入 |

注：8 个区域（含中国全域）的边界**不来自矢量文件**，而是 `Fig8.py` 中 `REGIONS` 硬编码的经纬度框
（区域定义与图 5 的同名脚本完全一致）；只有 3 个河流流域用 `Data/River` 下的 shapefile 做点在多边形内判定。

## 产出
| 文件 | 内容 |
|---|---|
| `data/fig8_regional_stats.csv` | 33 行 = 3 情景 × 11 区域；列为 `Scenario, Region, r_mean, r_std, reduction_mean, reduction_std, delta_mean, delta_std`（数值四舍五入到 4 位小数，`utf-8-sig` 编码） |
| `Fig8.jpg` | 论文图 8 成品：1×3 热力图，400 dpi，`bbox_inches='tight'` |

## 代码说明
单文件 `Fig8.py` 内部分为「统计」与「绘图」两个函数，由 `main()` 按规定顺序调用：

| 函数 / 入口 | 作用 | 主要产出 |
|---|---|---|
| `calc_regional_stats()` | 依次读取三个情景的 HEC NetCDF，构造 8 个经纬度框掩膜与 3 个流域掩膜，与有效格点（$p<0.05$ 且 $r\geq0.5$）求交，对 $r$、缩减率、后验−先验三个场做 $\cos\varphi$ 面积加权统计（均值与标准差），逐行累积结果表并写出 CSV | `data/fig8_regional_stats.csv` |
| `plot_heatmap()` | 读取该 CSV，按脚本内固定的区域序与情景序组装矩阵，绘制 (a) $r$、(b) 缩减率（百分比）、(c) Bias 三个热力图面板，标注格内数值并配带箭头色带 | `Fig8.jpg` |
| `main()` | 先调用 `calc_regional_stats()`，再调用 `plot_heatmap()`；仅由 `if __name__ == "__main__"` 在直接运行时触发 | 上述两者 |
| 模块级常量与工具 | `MODULE_DIR` / `REPO_ROOT` / `DATA_ROOT` / `HEC_DIR`、`REGIONS`、`RIVER_BASINS`、`scenarios` / `scenario_labels`、`region_order` / `region_labels` / `var_configs`、`build_river_mask()`、`weighted_stats()`、`_fmt_tick()`；导入模块只做定义，无副作用 | — |

## 方法说明

### 三个统计量
| 面板 | 变量（CSV 列） | 定义 |
|---|---|---|
| (a) Correlation r | `r_mean` / `r_std` | 历史期（1981–2010）降水变率与未来期（2021–2050）R95 强度在 19 个模式上的涌现相关系数 $r$，区域值为有效格点上的面积加权平均 |
| (b) Uncertainty Reduction (σ) | `reduction_mean` / `reduction_std` | 逐格点缩减率 $\Delta = 1 - \sigma_{\mathrm{post}}/\sigma_{\mathrm{prior}}$；$\sigma_{\mathrm{prior}}$ 为 19 个模式未来极端降水强度的模式间标准差，$\sigma_{\mathrm{post}}$ 为约束后的后验标准差（图 6 图注给出 $\sigma_{\mathrm{post}} = \sigma_{\mathrm{prior}}\sqrt{1 - r^{2}/(1 + 1/\mathrm{SNR})}$，$\mathrm{SNR} = \sigma_x^{2}/\sigma_{o,\mathrm{eff}}^{2}$）。数据中为 0–1 的小数（如 0.1915），热力图显示时 ×100 转为百分比 |
| (c) Bias | `delta_mean` / `delta_std` | 逐格点 `posterior_mean` $-$ `prior_mean`，即约束对 R95 强度估值的调整量与方向（论文图注单位 mm/day） |

### 有效格点与面积加权
* **有效格点判据**：$p<0.05$ 且 $r\geq0.5$（`p_value` 与 `r` 均为有限值），与图 6 面板的着色区域口径一致，也与论文正文一致。
* **面积加权**：权重 $w = \cos\varphi$（$\varphi$ 为格点纬度），加权均值 $\bar{x} = \sum w x / \sum w$，
  加权标准差 $s = \sqrt{\sum w\,(x-\bar{x})^{2} / \sum w}$。注意这里的 $s$ 是区域内格点值的空间离散度，**不是**模式间不确定性。
* **同域统计**：三个变量共用同一统计域（区域掩膜 ∩ 有效格点），以保证同一区域的三项可跨列比较。
* **空区域处理**：区域内无有效格点则返回 `NaN`；流域若算出 `NaN` 则整行跳过、不写入 CSV。
* **口径变更**：脚本 docstring 记录，原始版本采用"区域内全部有限格点"口径，2026-09-22 起按作者要求统一为有效格点口径。

### 区域与流域定义
| Region（CSV 值） | 纬度范围 | 经度范围 | 类型 |
|---|---|---|---|
| `China` | −90 – 90 | −180 – 360 | 经纬度框（全域，等价于不加区域掩膜，但仍与有效格点求交） |
| `NorthChina` | 35 – 42 | 110 – 118 | 经纬度框 |
| `Northeast` | 38 – 54 | 118 – 135 | 经纬度框 |
| `Northwest` | 35 – 50 | 73 – 105 | 经纬度框 |
| `Southwest` | 21 – 35 | 95 – 108 | 经纬度框 |
| `EastChina` | 27 – 35 | 115 – 123 | 经纬度框 |
| `SouthChina` | 18 – 26 | 108 – 120 | 经纬度框 |
| `CentralChina` | 26 – 34 | 108 – 115 | 经纬度框 |
| `YellowRiver` | — | — | 多边形：`Data/River/HuanghaiRiver_polygon.shp` |
| `PearlRiver` | — | — | 多边形：`Data/River/PearlRiver_polygon.shp` |
| `YangtzeRiver` | — | — | 多边形：`Data/River/YangtzeRiver_polygon.shp` |

### 流域掩膜构造
用 `shapefile.Reader` 读入流域全部多边形，`shapely.ops.unary_union` 合并为一个几何体；
先用合并后的外包矩形（`bounds`）对格点做粗筛，再对候选格点逐点调用 `contains(Point(lon, lat))` 判定，
避免在全国网格上做全量点在多边形内测试。

### 热力图绘制
* **矩阵结构**：11 行（区域）× 3 列（情景）。行序 `region_order`、列序 `scenario_order` 在 `Fig8.py` 内固定，
  行标签使用带词间隔的显示名（`North China`、`Yellow River Basin`、`Pearl Basin`、`Yangtze Basin` 等），与图 4 的 `REGION_LABELS` 保持一致。
* **配色与格式**：(a) `YlOrRd`、(b) `OrRd`、(c) `RdBu_r`；格内数值格式分别为 `.3f`、`.1f` + `%`、`.1f`。
* **色标口径**：热力图与色带统一使用"显示量"（缩减率面板为百分数），`vmin/vmax` 取该面板数据的 min/max，
  避免出现格内写 18.9% 而色带刻度写 0.16 的口径不一致；色带两端带箭头（`extend='both'`，长度约为图的 3/4）。
* **刻度标签**：三个面板的色带刻度步长分别为 0.1 / 2.5 / 2.0，标签统一为"整数不带小数、非整数保留 1 位小数"。
* **文字**：格内数值字号 8，`norm > 0.6` 用白色、否则用黑色；字体 Times New Roman、数学字体 `cm`；
  三个面板各带 `(a)`/`(b)`/`(c)` 子标题（字号 9.5）；图内不设总标题，标题信息由论文图注给出。

### 论文中的读图结论（正文 3.1 节）
正文依据本图给出的区域尺度结论如下：

* 三个情景下各区域历史降水变率与未来 R95 强度均为显著正相关，面积加权区域平均 $r$ 普遍在 0.78–0.90，情景间差异极小；
* 高相关区（$r>0.88$）集中于西南、华南、珠江流域与青藏高原，以西南最突出（0.887–0.901）；东北、华北相对较低（约 0.78–0.82），整体呈南高北低；
* 不确定性（$\sigma$）缩减率在 16%–27%，同为南高北低：华南与珠江流域最高（约 26%–27%），东北最低（约 16%–17%）；
* 调整量全为正值（后验 > 先验）：华南与珠江流域最大（约 5.4–7.1 mm/day），西北最小（约 1.0–1.1 mm/day），表明气候越湿润的地区约束效果越强。

上述区间与 `data/fig8_regional_stats.csv` 中的实际极值一致（$r$ 0.7784–0.9008，缩减率 0.1582–0.2741，Bias 1.0637–7.1074）。
