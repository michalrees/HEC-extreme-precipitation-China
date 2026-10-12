# 图 4 —— 极端降水强度（R95 Intensity）预估及其模式间不确定性空间分布

图 4 展示 HiCPC 19 个 CMIP6 模式对中国区域 2021--2050 年极端降水强度（R95 Intensity）的预估及模式间分歧：上排 (a) 为多模式集合平均（MME），下排 (b) 为模式间不确定性（模式间标准差 $\sigma$），三列依次对应 SSP1-2.6、SSP2-4.5、SSP5-8.5 三个情景。它回答两个问题：未来极端降水强度的空间量级如何分布，以及这一预估在模式之间有多大分歧。该图对应论文 `Doc/Tex/manuscript.tex` 中 Data and Methods 一节里"刻画 2021--2050 年极端降水强度预估本身的量级与模式间分歧"的段落（即目标变量的先验分布），并为 Results 中的区域统计（`fig:5`）与分层涌现约束的缩减评估（`fig:6`）提供基准。

## 目录结构
```
Fig4_ProjectionUncertainty/
├── Fig4.py          # 单文件流水线：预处理（读三情景 R95mm_intensity → 集合平均/模式间方差与标准差 → data/fig4_data.npz）+ 绘图（2×3 空间分布图，行=均值/σ，列=情景，并落盘统计表与色带分级）
├── Fig4.jpg         # 论文成品图
├── data/            # 代码计算的中间数据 + 统计数据
│   ├── fig4_data.npz      # 预处理段产出：lon/lat 坐标 + 三情景的 mean/var/std 场（原子写入）
│   ├── fig4_stats.csv     # 绘图段产出：逐面板面积加权均值与极值（主表，utf-8-sig）
│   ├── fig4_levels.csv    # 绘图段产出：mean/std 两行的色带分级边界（长表）
│   └── 图4_统计数据.txt    # 绘图段产出：与 fig4_stats.csv 同源的纯文本统计（含色带分级）
└── README.md
```

## 运行
```bash
cd "F:\Program\2Process\4HiCPC\Using hierarchical emergent constraints to reduce the uncertainty in future extreme precipitation projections over China"
python "src/Pic/Fig4_ProjectionUncertainty/Fig4.py"              # 完整流水线：预处理 + 绘图
python "src/Pic/Fig4_ProjectionUncertainty/Fig4.py" --reuse-npz  # 只绘图：跳过预处理，复用已有 data/fig4_data.npz
```

**顺序要求**：单文件内部已按"先预处理、后绘图"排列（`main()` 中先 `prepare_data()`，再 `plot_figure()`），不再需要手工分两步运行。`plot_figure()` 直接 `np.load(data/fig4_data.npz)`，该文件不存在时会直接报错；`--reuse-npz` 仅跳过预处理，依旧要求 `data/fig4_data.npz` 已存在（否则抛 `FileNotFoundError`）。`prepare_data()` 会把 npz 先写到同目录的临时文件再 `os.replace()` 到最终名（原子替换），以便兄弟模块在并发读取该文件时不会读到半成品。产物目录为模块根下的 `data/`（`Path(__file__).parent / 'data'`，不存在时自动创建）。

`--reuse-npz` 的适用场景：预处理要读入三个约 4.6 GB 的 `MULTI_MODEL-*-ALL_INDICES.nc`（合计约 15 GB），在只需重绘或复核图形、且 `data/fig4_data.npz` 已经是最新时可用该开关省去这段耗时。

依赖：`numpy`、`pandas`、`xarray`（仅预处理段）、`matplotlib`（含 `matplotlib.colors`、`matplotlib.ticker`、`mpl_toolkits.axes_grid1.inset_locator`）、`cartopy`、`pyshp`（`import shapefile`）、`shapely`。

脚本用 `Path(__file__).resolve().parents` 自下向上定位仓库根（同时含 `src/` 与 `Doc/`），无需修改路径；文件仍在模块根下，`Path(__file__).parent` 的定位逻辑不变。

## 数据来源
| 文件 | 来源 / 生成脚本 | 说明 |
|---|---|---|
| `Output/Mode/indices/Scenariomerged/MULTI_MODEL-ssp126-ALL_INDICES.nc`、`MULTI_MODEL-ssp245-ALL_INDICES.nc`、`MULTI_MODEL-ssp585-ALL_INDICES.nc` | 外部输入（HiCPC 多模式指数文件），由 `Fig4.py` 的预处理段 `prepare_data()` 读取 | 三情景的逐年多模式指标文件；代码取变量 `R95mm_intensity`，模式清单取自 `Mode` 坐标（19 个模式），时间维为 `year`，未来时段 `slice(2021, 2050)`；文件缺失时脚本 `raise FileNotFoundError` |
| `Data/China/cnmap.shp`（配套 `cnmap.shx`、`cnmap.prj`） | 外部输入，由 `Fig4.py` 的绘图段 `plot_figure()` 读取 | 中国国界矢量；经 `shapefile.Reader` + `shapely.geometry.shape` 转为几何后以灰色边线叠加，并由其 `bbox` 外扩 1° 设定地图范围 |
| `data/fig4_data.npz` | `Fig4.py` 的 `prepare_data()` 生成 | 本模块的核心中间数据，见"产出"表 |
| `data/fig4_stats.csv`、`data/图4_统计数据.txt`、`data/fig4_levels.csv` | `Fig4.py` 的 `plot_figure()` 生成 | 由同一次运行中的 `stats_rows` 与 `LEVELS` 落盘 |

其中 `data/fig4_data.npz` 含 11 个数组：`lon`（700，经度）、`lat`（400，纬度），以及 `ssp126`/`ssp245`/`ssp585` 各自的 `_mean`、`_var`、`_std`，每个场形状均为 `(400, 700)`（即 $0.25^\circ$ 网格、400 lat × 700 lon）。

## 产出
| 文件 | 内容 |
|---|---|
| `Fig4.jpg` | 论文成品图：2 行 × 3 列，画布 20 cm × 15 cm，`dpi=400`、`bbox_inches="tight"`；(a) 行 R95 Intensity 多模式集合平均，(b) 行模式间标准差 $\sigma$，列为 SSP1-2.6 / SSP2-4.5 / SSP5-8.5 |
| `data/fig4_data.npz` | `lon`、`lat` 及三情景 $\times$ `mean`/`var`/`std` 共 11 个数组；`var` 为模式间方差（单位 $(\mathrm{mm/day})^2$，仅留档），`std` 为模式间标准差（绘图主口径）。由 `prepare_data()` 原子写入：先写同目录临时文件再 `os.replace()` 到最终名，以便 Fig5 并发读取时不会读到半成品 |
| `data/fig4_stats.csv` | 逐面板统计主表，6 行；列固定为 `row,scenario,label,mean_area_weighted,vmin,vmax`；编码 `utf-8-sig`（带 BOM，Excel 双击不乱码） |
| `data/图4_统计数据.txt` | 与 `fig4_stats.csv` 同源的纯文本（同一次运行写入同一批数字），额外记录脚本/输入/时段/网格/权重说明、情景间极差，以及 `[colorbar levels, data-driven]` 色带分级 |
| `data/fig4_levels.csv` | 色带分级长表，列 `row,level_index,level_value`；`mean` 与 `std` 各 7 个边界值（即 6 档），便于按 `row` 过滤读取 |

## 代码说明
本模块只含一个 Python 文件 `Fig4.py`（原 `fig4data.py` 的预处理与 `Fig4.py` 的绘图已合并，不再互相 import）。文件仍是可执行脚本，入口为 `main()`：

| 函数 / 段落 | 作用 | 主要产出 |
|---|---|---|
| `prepare_data()`（第 1 步：预处理，原 `fig4data.py`） | 逐情景打开 `MULTI_MODEL-<scen>-ALL_INDICES.nc`，对每个模式在 2021--2050 年上做 `skipna=True` 的时间平均，堆叠为 `(n_models, lat, lon)`；再沿模式维用 `np.nanmean` / `np.nanstd` 求集合平均与模式间标准差，并留档方差 $\sigma^2$；最后原子写入 npz | `data/fig4_data.npz` |
| `plot_figure()`（第 2 步：绘图，原 `Fig4.py`） | 载入 npz，以 $\cos\varphi$ 为面积权重，由数据全域推出色带分级；用 cartopy `contourf` + `contour` 绘制 2×3 面板，叠加中国国界、经纬网格与内嵌 PDF 直方图，配每行共用横向色带及 (a)/(b) 行标；同时计算并落盘逐面板统计与色带分级 | `Fig4.jpg`、`data/fig4_stats.csv`、`data/图4_统计数据.txt`、`data/fig4_levels.csv` |
| `main()` | 解析 `--reuse-npz` 开关；默认先 `prepare_data()` 再 `plot_figure()`；带 `--reuse-npz` 时跳过预处理，直接复用已有 npz 绘图 | — |

下游复用：`src/Pic/Fig5_RegionalStatistics/calc_regional_stats.py` 直接以 `Path(__file__).parent.parent / "Fig4_ProjectionUncertainty" / "data" / "fig4_data.npz"` 读取本模块的 `mean`/`std` 场，因此**图 5 的区域统计依赖本模块 `Fig4.py` 的预处理段已运行**（无需绘图段）；由于该 npz 改为原子替换写入，Fig5 与本模块并发运行时不会读到写了一半的文件。

注：`Fig4.py` 中的 `data_driven_levels()`（"整齐步长"分级）仍保留在脚本内，但当前分级已改为直接取数据极值等分，该函数不再被调用。脚本内的历史字样（控制台打印、"图 3"、"doc/ 目录"）已在扁平化时一并订正为 "Fig. 4" 与 `data/`；磁盘上 `data/图4_统计数据.txt` 的 `script` 行也已重新指向 `src/Pic/Fig4_ProjectionUncertainty/Fig4.py`。该 txt 中的 `input` 行仍写作 `data/fig4_data.npz (produced by fig4data.py)`——这是合并前的原文，为保持产物逐字节不变而刻意保留（预处理现已并入同一文件的 `prepare_data()`）。

## 方法说明

### 未来时段与情景
未来预估时段为 2021--2050（`future_period = slice(2021, 2050)`），情景与标签一一对应：`ssp126` $\rightarrow$ SSP1-2.6、`ssp245` $\rightarrow$ SSP2-4.5、`ssp585` $\rightarrow$ SSP5-8.5。

### 集合统计量（模式间不确定性的定义）
设模式 $m$ 在格点 $(i,j)$、年份 $y$ 的 R95 Intensity 为 $X_m(i,j,y)$。先对每个模式做未来时段的时间平均：

$$\overline{X}_m(i,j) = \operatorname{mean}_{y \in [2021,2050]} X_m(i,j,y)$$

再沿模式维（19 个模式）求集合统计量：

$$\mu(i,j) = \operatorname{nanmean}_m \overline{X}_m(i,j), \qquad \sigma(i,j) = \operatorname{nanstd}_m \overline{X}_m(i,j)$$

$\mu$ 即 (a) 行的多模式集合平均，$\sigma$ 即 (b) 行的模式间不确定性。代码同时留档模式间方差 $\sigma^2$（注释明确"留档；全文统一按 $\sigma$ 报告"），故绘图与统计均以标准差 $\sigma$ 为主口径，单位为 mm/day。

### 面积加权统计
所有区域平均值均以格点纬度的余弦为面积权重（`weight: area-weighted, w = cos(lat)`）：

$$\overline{X}_w = \frac{\sum_{i,j} X(i,j)\,\cos\varphi_j}{\sum_{i,j} \cos\varphi_j}\quad(\text{仅对 } X \text{ 有限的格点求和})$$

代码实现为 `np.nansum(field_data * weights_2d) / np.nansum(weights_2d * valid)`，其中 `valid = np.isfinite(field_data)`。该值以白底圆角文本框 `Mean: xx.xx` 标注在每个面板左下角，并写入统计表。

### 色带分级
每行（`mean` / `std`）先取三情景合集的有效值范围 $[lo, hi]$（`row_data_range()`），再用 `np.linspace(lo, hi, 7)` 生成 7 个边界、6 个区间，首尾恰为数据全局最小/最大值，不再向外取整到"整齐步长"（脚本注释标注为 2026-09-22 统一口径）。分带颜色由 `make_band_colors()` 从各行基色带线性采样得到（离散色带先转线性再采样，避免相邻分带取到同一颜色）；地图分带、直方图柱色与色带分段共用这一组颜色，保证颜色边界严格落在分级刻度上。

### 绘图设置
- **布局**：2 行 × 3 列；行 = 集合平均 / 模式间 $\sigma$，列 = 三个情景；行标题居中于中间列上方，(a)/(b) 标号置于每行首列轴外左上角。
- **填色与等值线**：`contourf` 使用 6 档离散色并设 `extend='both'`；同一组分级再以黑色 `contour`（`linewidths=0.3`）勾出分级界线。
- **底图**：中国国界以 `#999999`、线宽 0.5 叠加（不填充），隐藏地图轴边框 `ax.spines['geo']`；地图范围取自 `cnmap.shp` 的 `bbox` 外扩 1°。
- **经纬网格**：`xlocs=[80, 90, 110, 130]`、`ylocs=[10, 20, 30, 40, 50]`，虚线、`alpha=0.4`，仅保留左侧与下侧标签。
- **内嵌直方图**：分箱与色带分级完全一致（`bins = levels`），纵轴为概率密度 $\mathrm{PDF} = \mathrm{counts}/(N \cdot \Delta)$（$N$ 为该面板有效格点数、$\Delta$ 为组距），柱色与分带色一致；位置在面板左下角 `(0.18, 0.07)`，宽度第一行 0.40、第二行 0.315。
- **色带**：每行一个横向色带，以中间子图为中心、宽度为其 1.80 倍，`BoundaryNorm` + `ListedColormap` 渲染，刻度落在分级边界上，`extend='both'`、`extendfrac=0.04`，标签 `mm/day`；刻度标签经 `FuncFormatter` 统一为整数不带小数、非整数保留 1 位小数。
- **字体**：`Times New Roman`，数学字体 `cm`，`axes.unicode_minus = False`。

### 主要结果（脚本落盘数值）
| row | 情景 | 面积加权均值 | min | max |
|---|---|---|---|---|
| mean | SSP1-2.6 | 23.9353 | 3.846 | 87.350 |
| mean | SSP2-4.5 | 23.9658 | 4.010 | 88.631 |
| mean | SSP5-8.5 | 23.8935 | 4.040 | 87.176 |
| std | SSP1-2.6 | 2.0034 | 0.219 | 10.644 |
| std | SSP2-4.5 | 2.0299 | 0.218 | 10.828 |
| std | SSP5-8.5 | 2.0612 | 0.317 | 12.328 |

$$ \text{mean}: \text{情景间极差} = 0.0723\ \mathrm{mm/day}, \qquad \text{std}: \text{情景间极差} = 0.0578\ \mathrm{mm/day} $$

色带分级边界（数据驱动，各 7 个边界 / 6 档）：

| row | 分级边界（mm/day） |
|---|---|
| mean | 3.846, 17.977, 32.108, 46.239, 60.369, 74.500, 88.631 |
| std | 0.218, 2.236, 4.254, 6.273, 8.291, 10.309, 12.328 |

上述数值表明：三个排放情景的全国面积加权平均 R95 Intensity 几乎相同（均约 23.9 mm/day，情景间极差仅 0.0723 mm/day），说明该时段极端降水强度的不确定性主要来自模式结构差异而非排放路径；模式间 $\sigma$ 的区域平均约 2.0--2.1 mm/day，其空间最大值在三个情景下分别为 10.644、10.828 与 12.328 mm/day，即极端降水越强的区域模式间绝对分歧越大（与论文该节结论一致）。
