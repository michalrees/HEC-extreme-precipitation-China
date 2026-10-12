# 图 6 —— 分层涌现约束（HEC）诊断：相关系数、不确定性缩减与后验−先验调整场

本图基于中国区域逐格点的分层涌现约束（Hierarchical Emergent Constraint, HEC）诊断结果，回答"历史期降水变率能否约束未来期极端降水强度预估、约束能把不确定性压到多低、以及约束把预估值推向何方"三个问题，对应论文第 3.1 节 Hierarchical Emergent Constraints（后验公式见论文第 2.3 节）。图由三个面板组成：**(a)** 约束因子（Precip Var）与目标变量（R95 Intensity）的相关系数 $r$ 空间分布；**(b)** 约束后的不确定性（$\sigma$）缩减率空间分布；**(c)** 后验均值减先验均值的调整场（Bias）空间分布。三个面板均按 SSP1-2.6 / SSP2-4.5 / SSP5-8.5 三个情景并排展示，空间格局在情景间高度一致。

## 目录结构
```
Fig6_EmergentConstraint/
├── Fig6.py          # 单文件流水线（本模块唯一的脚本），按固定顺序完成四个渲染阶段：
│                    #   ① 面板 (a) 相关系数 r 的三情景单行渲染        → 运行期临时目录
│                    #   ② 面板 (b) 不确定性缩减率（σ 口径）单行渲染  → 运行期临时目录
│                    #   ③ 面板 (c) 后验−先验差值（mm/day）单行渲染   → 运行期临时目录
│                    #   ④ 在一个 figure 内直接绘制 3 行(诊断量) × 3 列(情景) 组图，
│                    #      并落盘统计数据 CSV
├── Fig6.jpg         # 论文成品图（(a)(b)(c) 三行 × 三情景三列组图，dpi=400）
├── data/            # 代码计算的统计数据
│   └── fig6_stats.csv   # Fig6.py 写出的 3 面板 × 3 情景面积加权统计表
└── README.md
```
模块根目录**恰好只有上述 4 项**（`Fig6.py`、`Fig6.jpg`、`data/`、`README.md`）。①②③ 三张单面板图不再落盘到模块根目录，而是写进**模块目录之外**的运行期临时目录（`<仓库根目录的上一级>\_tmp_fig6_xxxxxxxx`，不可写时退回系统临时目录），当次运行结束即在 `finally` 中整体删除（渲染逻辑与原单面板脚本完全相同）。脚本**不会**在模块目录内创建任何临时目录或探测目录。

> **单面板图路径说明**：`fig6a.jpg` / `fig6b.jpg` / `fig6c.jpg` 原先放在 `fig/svg_components/` 子目录下，后短暂平铺于模块根目录；现在它们只是**运行期中间产物**，统一输出到模块目录之外的临时目录并在运行结束时自动清理。`fig/`、`code/` 子目录已取消，成品 `Fig6.jpg` 与 `data/fig6_stats.csv` 的输出路径仍为 `Path(__file__).resolve().parent`（即模块根目录）。
>
> **`doc/` 目录状态**：模块下仍存在一个空的 `doc/` 子目录（递归统计 0 个文件），其中没有任何 `.md` 或其他文档内容，故本 README 无需并入任何 `doc/*.md` 原文。

## 运行
```bash
cd "F:\Program\2Process\4HiCPC\Using hierarchical emergent constraints to reduce the uncertainty in future extreme precipitation projections over China"
python "src/Pic/Fig6_EmergentConstraint/Fig6.py"
```
默认一次跑完全部四个渲染阶段，顺序固定为 ① 单面板 (a) → ② 单面板 (b) → ③ 单面板 (c) → ④ `Fig6.jpg` + `data/fig6_stats.csv`（与原「依次运行 `Fig6a.py` → `Fig6b.py` → `Fig6c.py` → `Fig6.py`」完全一致）。**只有 ④ 落盘到模块根目录**：①②③ 的单面板 JPG 写进本次运行专用的临时目录（**模块目录之外**，形如 `4HiCPC\_tmp_fig6_xxxxxxxx\fig6a.jpg`；用 `os.makedirs()` 默认权限创建，**不使用** `tempfile.mkdtemp()` / `TemporaryDirectory()`——它们在 Windows 上以 `0o700` 建目录，受限令牌下连创建进程自己都无法写入或删除），运行结束时在 `finally` 中由 `shutil.rmtree(..., ignore_errors=True)` 整体删除；若仓库根目录的上一级不可写则退回系统临时目录。只需其中一部分时用 `--only` 指定；阶段顺序仍固定为上述顺序，与书写顺序无关：

```bash
python "src/Pic/Fig6_EmergentConstraint/Fig6.py" --only a           # 只渲染单面板 (a)（临时图，运行结束自动清理）
python "src/Pic/Fig6_EmergentConstraint/Fig6.py" --only b,c         # 只渲染单面板 (b) 与 (c)
python "src/Pic/Fig6_EmergentConstraint/Fig6.py" --only composite   # 只渲染 Fig6.jpg 与 data/fig6_stats.csv
python "src/Pic/Fig6_EmergentConstraint/Fig6.py" --only all         # 等价于不带参数（默认全部）
```
依赖：`numpy`、`pandas`（写统计数据 CSV）、`xarray`、`matplotlib`、`cartopy`、`pyshp`（`import shapefile`）、`shapely`；`xarray` 读取 `.nc` 还需 `netcdf4` 或 `h5netcdf` 后端。脚本导入 `cartopy.crs`、`shapefile`、`shapely.geometry.shape`，并用到 `mpl_toolkits.axes_grid1.inset_locator.inset_axes`（随 `matplotlib` 提供）。

脚本用 `Path(__file__).resolve().parents` 自下向上定位仓库根（同时含 `src/` 与 `Doc/`），无需修改路径。具体为：`ROOT = Path(__file__).resolve().parent`（模块根，用于输出图片与 CSV），`REPO_ROOT = next(p for p in Path(__file__).resolve().parents if (p / "src").is_dir() and (p / "Doc").is_dir())`，即 `4HiCPC/Using hierarchical emergent constraints to reduce the uncertainty in future extreme precipitation projections over China/`；数据根目录取 `DATA_ROOT = REPO_ROOT / "Data"`。

## 数据来源
| 文件 | 来源 / 生成脚本 | 说明 |
|---|---|---|
| `Output/EC/China/HEC_ssp126_PrecipVar_to_R95mm_intensity.nc` | `src/pipeline/6中国区域分层涌现约束.py`（文件名模板 `HEC_{SCENARIO}_{HIST_INDICATOR}_to_{FUTURE_INDICATOR}.nc`，三情景 nc 平铺在 `China` 根目录） | SSP1-2.6 逐格点 HEC 结果 |
| `Output/EC/China/HEC_ssp245_PrecipVar_to_R95mm_intensity.nc` | 同上 | SSP2-4.5 逐格点 HEC 结果 |
| `Output/EC/China/HEC_ssp585_PrecipVar_to_R95mm_intensity.nc` | 同上 | SSP5-8.5 逐格点 HEC 结果 |
| `Data/China/cnmap.shp`（含同名 `.shx`、`.prj`） | 中国国界矢量数据 | 地图底图边界；用 `shapefile.Reader` 读取，按 `bbox` 外扩 1° 作为 `set_extent` 范围 |
| `data/fig6_stats.csv` | `Fig6.py` 运行时写出到 `ROOT/"data"/fig6_stats.csv`（`encoding="utf-8-sig"`） | 代码计算的统计数据，9 行（3 面板 × 3 情景） |

`.nc` 文件由该 pipeline 脚本写出的变量包括 `r`、`p_value`、`obs_sigma_raw`、`obs_sigma_effective`、`prior_mean`、`prior_std`、`posterior_std`、`posterior_mean`、`reduction`、`n`（坐标 `lat`、`lon`）。本模块实际只读取其中 5 个变量：`r`、`p_value`、`reduction`、`prior_mean`、`posterior_mean`；`fig6_stats.csv` 的 `field` 列也据此命名。文件属性含 `scenario`、`history_indicator`、`future_indicator`、`history_period`、`future_period`、`observational_error_term`；`Fig6.py` 会打印 `future_period`（pipeline 中 `FUTURE_PERIOD_RANGE = (2021, 2050)`）。`Fig6.py` 在缺文件时显式抛出 `FileNotFoundError` 并提示先运行 `src/pipeline/6中国区域分层涌现约束.py`；合并为单文件后四个渲染阶段共用同一加载函数，因此该检查对单面板渲染同样生效。

## 产出
| 文件 | 内容 |
|---|---|
| `Fig6.jpg` | 论文成品组图（模块根目录中**唯一落盘的图件**）：3 行（(a) 相关系数 / (b) 不确定性缩减 / (c) 后验−先验） × 3 列（三情景），每行共享一条横向色带，`dpi=400`、`bbox_inches="tight"` |
| `data/fig6_stats.csv` | 列：`panel, scenario, field, mean_area_weighted, pct_p_lt_005_and_r_ge_05` |
| `fig6a.jpg` / `fig6b.jpg` / `fig6c.jpg` | **不再落盘**：单面板 (a)(b)(c) 的渲染结果写在**模块目录之外**的运行期临时目录里（`4HiCPC\_tmp_fig6_xxxxxxxx\`，`os.makedirs()` 默认权限），运行结束即整体删除。渲染本身与原单面板脚本完全相同——同样 `dpi=400`、`bbox_inches="tight"`，同样带 suptitle、`(a)/(b)/(c)` 角标、共享色带、灰色图例与内嵌 PDF 直方图 |

`data/fig6_stats.csv` 现有内容（三情景面积加权统计，百分数列仅 (a) 面板有值）：

| panel | scenario | field | mean_area_weighted | pct_p_lt_005_and_r_ge_05 |
|---|---|---|---|---|
| a_correlation | SSP1-2.6 | r | 0.8472 | 98.35 |
| a_correlation | SSP2-4.5 | r | 0.8492 | 98.61 |
| a_correlation | SSP5-8.5 | r | 0.8488 | 98.54 |
| b_reduction | SSP1-2.6 | reduction_sigma_caliber_significant_only | 0.1915 | |
| b_reduction | SSP2-4.5 | reduction_sigma_caliber_significant_only | 0.1924 | |
| b_reduction | SSP5-8.5 | reduction_sigma_caliber_significant_only | 0.1979 | |
| c_posterior_minus_prior | SSP1-2.6 | posterior_mean - prior_mean | 2.4862 | |
| c_posterior_minus_prior | SSP2-4.5 | posterior_mean - prior_mean | 2.5232 | |
| c_posterior_minus_prior | SSP5-8.5 | posterior_mean - prior_mean | 2.5604 | |

## 代码说明
本模块只有 `Fig6.py` 一个脚本，内部按流水线顺序组织为「共用加载逻辑 + 四个渲染函数 + 命令行入口」：

| 位置 | 作用 | 主要产出 |
|---|---|---|
| `load_china_geoms()`、`load_datasets()` | 共用加载：`shapefile.Reader` 读 `Data/China/cnmap.shp` 并算 `set_extent` 范围；读三情景 nc 并打印 `future_period`（缺文件时显式抛出 `FileNotFoundError` 并提示先运行 `src/pipeline/6中国区域分层涌现约束.py`） | — |
| `render_panel_a()` | 阶段①：读取三情景 nc 的 `r`、`p_value`，绘制 $1 \times 3$ 相关系数地图（固定 0.5–1.0 分级、灰色掩膜、等值线、内嵌 PDF 直方图小图），下方共享色带与灰色图例 | `fig6a.jpg`（运行期临时文件，自动清理） |
| `render_panel_b()` | 阶段②：读取 `reduction`、`p_value`，绘制 $1 \times 3$ 不确定性缩减率地图（分级 $[0,0.1,0.2,0.4,0.6,0.8,1.0]$ 按实际最大值裁剪、内嵌 PDF 直方图），色带刻度显示实际最小/最大百分比 | `fig6b.jpg`（运行期临时文件，自动清理） |
| `render_panel_c()` | 阶段③：读取 `posterior_mean`、`prior_mean`、`p_value`，绘制 $1 \times 3$ 后验−先验差值地图（极值超出 $\pm 1$ 时用固定边界 $[-14,-7,-1,1,7,14]$，否则线性分级；内嵌 PDF 直方图） | `fig6c.jpg`（运行期临时文件，自动清理） |
| `render_composite()` | 阶段④：算全局色带边界后在一个 `plt.figure` 内用 `fig.add_axes` 直接绘制 3 行 × 3 列地图面板（行=相关系数 / 缩减率 / 后验−先验，列=三情景），逐面板加中国边界、经纬网格、情景标题、"$p<0.05$ and $r \ge 0.5$" 面积占比与 Mean 标注，每行加横向色带与行标题，并写统计数据 | `Fig6.jpg`、`data/fig6_stats.csv` |
| `parse_args()`、`main()` | 命令行入口：默认按 ① → ② → ③ → ④ 顺序全部渲染；`--only` 可只跑其中一部分（见「运行」） | — |

四个渲染函数各自使用独立的局部变量与分级规则，互不影响；模块顶部只保留四者共用的常量（`SCENARIOS`、`SCENARIO_LABELS`、`PROJ`、`CORR_CMAP`、`CLASS_COLORS`、`DELTA_ANCHOR_COLORS` 等）。

## 方法说明

### 涌现约束关系
以历史期（1981–2010）降水变率（Precip Var）为约束因子 $x$、以未来期（2021–2050）极端降水强度（R95 Intensity）为因变量 $y$，在 19 个 HiCPC 模式上逐格点回归，得到 $\bar{x}$、$\sigma_x$、$\bar{y}$、$\sigma_y$、$r$ 与显著性 $p$。论文 §3.1 报告的逐格点缩减率为 $\Delta = 1 - \sigma_{\mathrm{post}}/\sigma_{\mathrm{prior}}$，其中 $\sigma_{\mathrm{prior}}$ 为 19 个模式的模式间标准差（先验不确定性）、$\sigma_{\mathrm{post}}$ 为贝叶斯更新后的后验标准差，由两层涌现约束的闭式解给出：$\sigma_{\mathrm{post}} = \sigma_{\mathrm{prior}} \times \sqrt{1 - r^2/(1 + 1/\mathrm{SNR})}$，式中 $\mathrm{SNR} = \sigma_x^2/\sigma_{o,\mathrm{eff}}^2$ 为约束因子模式间方差与观测层有效方差之比，$\sigma_{o,\mathrm{eff}}$ 取四套观测产品（CN05.1、CPC、CHM PRE V2、HGCDC）间的标准差除以 $\sqrt{N}$（$N$ 为该格点可用产品数，即观测误差项）。当观测视为无误差（$\sigma_{o,\mathrm{eff}} \to 0$，$\mathrm{SNR} \to \infty$）时该式退化为经典涌现约束的 $1 - \sqrt{1-r^2}$；本文显式保留 $\sigma_{o,\mathrm{eff}}$，故所得缩减率更为保守。pipeline 脚本中对应的后验均值与后验标准差为：`posterior_mean = y_mean + (r * std_y / sigma_x) * (obs_mean - x_mean) / (sigma_x**2 + obs_sigma_eff**2) * sigma_x**2`、`posterior_std = sqrt((1 - r**2 / (1 + 1/snr)) * std_y**2)`，`reduction = 1 - posterior_std / std_y`。

### 三个诊断量
- **(a) 相关系数 $r$**：灰色掩膜覆盖未通过显著性检验（$p \ge 0.05$）或弱相关（$r < 0.5$）的格点，等值线勾勒分级界线，面板上方标注面积加权区域平均相关系数，下方标注满足 $p<0.05$ 且 $r \ge 0.5$ 的面积占比（`Fig6.py` 将该占比画在面板下方、Mean 画在面板上方）。
- **(b) 不确定性缩减率**：$\Delta = 1 - \sigma_{\mathrm{post}}/\sigma_{\mathrm{prior}}$，色带为 6 档分类填色，刻度以百分比显示。
- **(c) 后验−先验调整量**：`posterior_mean - prior_mean`（mm/day，即 nc 中 `posterior_mean` 减 `prior_mean`），反映涌现约束对各格点极端降水强度估值的调整幅度与方向；`Fig6.py` 用近 0 密、两端疏的以 0 为中心对称分级，并叠加黑色等值线。

### 组图如何拼合
`Fig6.py` **不读取** `fig6a.jpg` / `fig6b.jpg` / `fig6c.jpg`，而是用同一批 nc 数据在一个 `matplotlib` figure 内**直接重绘** 3 行 × 3 列地图面板（`fig.add_axes` + `set_extent`），每行统一按中间面板位置确定色带宽度与位置，另加行标题、`(a)/(b)/(c)` 行标签与灰色掩膜图例，最后 `fig.savefig(ROOT / "Fig6.jpg", dpi=400, bbox_inches="tight")` 输出成品图。因此三张单面板 JPG 与成品组图是**同一套数据的两套独立渲染**，而非"渲染面板 → 拼接 JPG"的流水线；单面板脚本额外带总标题（suptitle）、各自的色带刻度和内嵌 PDF 直方图小图，成品组图则没有直方图小图。

### 统计口径（成品组图与单面板脚本的差异）
| 项目 | `render_composite()`（成品组图） | `render_panel_a/b/c()`（单面板） |
|---|---|---|
| 灰色掩膜判据 | 三行统一为 $p<0.05$ **且** $r \ge 0.5$（与论文正文口径一致） | `render_panel_a()` 同为 $p<0.05$ 且 $r \ge 0.5$；`render_panel_b()`、`render_panel_c()` 仅用 $p \ge 0.05$ |
| Mean 标注 | 仅在有效格点（$p<0.05$ 且 $r\ge0.5$，即图上着色区域）上按 $\cos\varphi$ 面积加权 | 在全部有限格点上按 $\cos\varphi$ 面积加权 |
| Mean 格式 | 相关系数 3 位小数、缩减率 3 位小数、调整量 2 位小数 | 三者统一用 `%.3g` |
| (a) 色带分级 | 按三情景显著区（$p<0.05$ 且 $r\ge0.5$）实际极值重算 `np.linspace(corr_min, corr_max, 6)` | 固定 0.5–1.0：`np.linspace(0.5, 1.0, 7)` |
| (b) 色带分级 | 三情景并集实际极值 `np.linspace(r_min, r_max, 6)` | 固定 `[0, 0.1, 0.2, 0.4, 0.6, 0.8, 1.0]`，按实际最大值裁剪后可能追加真实最大值 |
| (c) 色带分级 | 以 0 为中心的对称非等距分级（内层 $\pm1$、$\pm6$ + 首尾实际极值） | 极值超出 $\pm1$ 时用固定 `[-14, -7, -1, 1, 7, 14]`，否则 `np.linspace(global_min, global_max, 6)` |
| 内嵌 PDF 直方图 | 无 | 三个单面板渲染均有（按各自分级统计、颜色与填色一致） |
| 面积占比标注 | 仅 (a) 行有 | 仅 `render_panel_a()` 有 |

### 与论文正文的对应
论文 §3.1 的结论为：相关系数在超过 98% 的中国陆地区域达到统计显著（$p<0.05$），空间上呈南高北低的分布格局，西南地区和华南部分地区相关系数超过 0.88，东北和西北地区相对较低；不确定性缩减率空间分布与相关系数高度一致，高缩减区集中于西南、华南和珠江流域，局部格点超过 70%，东北和西北整体偏低；调整场（后验−先验）显示约束调整均为正值，华南和华东沿海调整幅度最大（超过 5 mm/day），向西北内陆递减至 1 mm/day 以下，且上述空间分布特征在各排放情景间高度一致。`data/fig6_stats.csv` 中 (b) 面板 19.15%–19.79% 的全国面积加权缩减率与论文报告的 19.2%–19.8% 一致，(a) 面板 0.8472–0.8492 的平均相关系数与论文的 0.847–0.849 一致。

### 备注
- 合并为单文件时已重写文件头 docstring：原 `Fig6.py` 的 "Fig. 5 — 先验约束诊断…" 时代遗留改为 "Fig. 6 — 分层涌现约束（HEC）诊断…"，并说明四个渲染阶段的先后顺序。
- `Fig6.py` 中 `OUTPUT_DIR = ROOT`，而统计数据固定写到 `ROOT / "data" / "fig6_stats.csv"`（`data/` 不存在时自动创建）。
- 地图绘制时经向/纬向数组做了 `[::2, ::2]` 降采样（`contourf` / `contour` / 掩膜层一致），以减小渲染量；数据本身分辨率不变。
- **绘图环境敏感性（实测）**：本模块现有 `Fig6.jpg` 由 `matplotlib 3.10.9` 渲染，用同一 matplotlib 版本重跑可**逐字节复现**；改用 `D:\Conda\envs\MET\python.exe`（Python 3.11 + `matplotlib 3.10.8`）重跑时数据与 `data/fig6_stats.csv` 完全一致，但 `bbox_inches="tight"` 结果差 1 px（2275×3171 vs 2276×3169），JPG 字节随之不同。即本模块图件对应的是 `matplotlib 3.10.9` 环境，重新出图前请确认所用解释器版本。
