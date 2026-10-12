# 图 2 —— HiCPC 多模式对历史极端降水与降水变率的评估

本图以 CN05.1 观测为参考，评估 HiCPC 中 19 个模式在历史时期（1981–2010 年）对中国区域极端降水强度（R95 Intensity）与降水变率（Precip Var）的刻画能力，回答“HiCPC 能否作为后续分层涌现约束（HEC）输入”这一前提性问题，对应论文第 2 节 Data and Methods 中的 HiCPC 适用性评估（TeX 中 `\label{fig:2}`，排在 Results 之前）。图中上行给出 19 个模式与观测的空间相关系数（CORR），下行给出偏差（Bias，mm/day）；蓝色为 Precip Var、红色为 R95 Intensity，水平虚线为各指标的 19 模式平均值，子图上方标注该平均值，CORR 面板另标 $p$ 值。⚠️ **模块根目录固定只有 4 项**：`Fig2.py`、`Fig2.jpg`、`data/`、`README.md`。其中 `Fig2.jpg` 是唯一的论文成品图（散点面板），由 `Fig2.py` 以 `dpi 400`、`bbox_inches="tight"` 直接 `savefig` 得到，运行一次不会多出任何文件。原「散点面板 + 地图面板」上下拼合中的地图面板 (b) 已按作者要求移除（其 CN05.1 与 MME 气候态空间分布与图 3 的 OBS − MME 偏差场内容重复）；地图面板的渲染流水线仍完整保留在 `Fig2.py` 内（`python Fig2.py --map-only` 可单独跑），但它只在**运行期**画到模块之外的临时目录、用完即删，不落盘——保留它是因为它算出的 MME 统计量仍是正文与摘要相应数字的来源。

## 目录结构
```
Fig2_ModelEvaluation/
├── Fig2.py           # 单文件流水线：散点面板 (a) + 地图面板 (b) + 统计数据落盘
├── Fig2.jpg          # 论文成品图（散点面板，dpi 400，293.5 KB）—— 模块内唯一的图片产出
├── data/             # 原始数据 + 代码计算的统计数据
│   ├── MULTI_MODEL-historical-1981-2010.nc   # HiCPC 19 模式原始输入（0.1°，1140.81 MB）
│   ├── CN05-OBS-1981-2010.nc                 # CN05.1 观测原始输入（0.25°，6.84 MB）
│   ├── fig2a_stats.csv                       # 散点面板落盘：指标 × 统计量汇总（mean/median/n_models）
│   ├── fig2b_stats.csv                       # 地图面板落盘：MME 评估汇总（corr/p/nrmse/bias/…）
│   ├── fig2_per_model.csv                    # 散点面板落盘：逐模式 CORR / Bias 明细（38 行）
│   ├── 图2a_统计数据.txt                     # 散点面板落盘：逐模式 CORR/Bias + MEAN(19 modes) 纯文本
│   └── 图2b_统计数据.txt                     # 地图面板落盘：MME vs CN05.1 纯文本统计
└── README.md
```
即模块根目录**恰好 4 项**，运行 `Fig2.py` 前后都不变。原先根目录下的 `Fig2a.jpg`（散点中间图）、`Fig2b.jpg`（地图面板）、`Fig2(2指标).jpg`（历史留档，无脚本产出）已删除：前两者现在是运行期临时产物（见「运行」一节），论文成品图只有 `Fig2.jpg`。

## 运行
```bash
cd "F:\Program\2Process\4HiCPC\Using hierarchical emergent constraints to reduce the uncertainty in future extreme precipitation projections over China"
python "src/Pic/Fig2_ModelEvaluation/Fig2.py"
python "src/Pic/Fig2_ModelEvaluation/Fig2.py" --scatter-only
python "src/Pic/Fig2_ModelEvaluation/Fig2.py" --map-only
```
三条命令依次为：默认全流程（散点面板 + 地图面板 + 全部统计数据，等价于合并前 `Fig2a.py` + `compose_fig2.py` + `Fig2b.py` 三条命令）、只跑散点面板（出论文成品图 `Fig2.jpg`）、只跑地图面板（只在临时目录里渲染，不落盘）。
依赖：单文件流水线的数据准备与散点面板 import `numpy / pandas / xarray / matplotlib / scipy`；地图面板另需 `cartopy / pyshp(shapefile) / shapely`；不再需要 `Pillow(PIL)`（原 `compose_fig2.py` 用它打印图片尺寸，现已取消）。
脚本用 `Path(__file__).resolve().parents` 自下向上定位仓库根（同时含 `src/` 与 `Doc/`），无需修改路径。图件请用仓库自带的解释器运行：`D:\Conda\envs\MET\python.exe`（Python 3.11 + matplotlib 3.10.8），它与归档的 `Fig2.jpg` 逐字节一致；PATH 上的 Python 3.14 + matplotlib 3.10.9 渲染出的 JPEG 会有 75 字节的字形抗锯齿差异。
补充（运行期临时产物）：地图面板仍会完整渲染，但 `main()` 先用 `os.makedirs()`（**默认权限**）在**模块之外**建一个临时目录 —— `REPO_ROOT` 的上一级，即 `F:\Program\2Process\4HiCPC\_tmp_fig2_map_<随机>`，把 `Fig2b.jpg` 写进去，然后在 `finally` 中 `shutil.rmtree(..., ignore_errors=True)` 删除；因此跑完模块根目录仍恰好 4 项。这里刻意**不用** `tempfile.mkdtemp()` / `TemporaryDirectory()`：它们以 `0o700` 建目录，在本机受限环境下会生成连删除都被拒绝的目录，绝不能落在模块目录里。地图面板额外依赖 `<仓库根>/Data/China/cnmap.shp`（已确认存在），`--scatter-only` 不需要该文件；它的 MME 统计量（`data/fig2b_stats.csv`、`data/图2b_统计数据.txt`）照常落盘，仍是正文与摘要数字的来源。**原 `FIG2_OUT` 环境变量已移除**：它以前用于给散点面板的成品改名（默认 `Fig2a.jpg`），现在论文成品图名固定为 `Fig2.jpg`，模块根目录不再产生其它图片文件。

## 数据来源
| 文件 | 来源 / 生成脚本 | 说明 |
|---|---|---|
| `data/MULTI_MODEL-historical-1981-2010.nc` | HiCPC 多模式输出合并（外部原始输入，非本模块脚本生成） | 19 个模式（`Mode`=19）、1981–2010 逐年（`year`=30）、0.1° 网格（`lat` 400 × `lon` 700，15.05–54.95°N、70.05–139.95°E）；含 `PrecipVar` 与 `R10mm / R20mm / R25mm / R50mm / R90mm / R95mm / R99mm_intensity`；文件属性 note 记为「Merged across models from batch outputs; added Mode dimension」；1140.81 MB |
| `data/CN05-OBS-1981-2010.nc` | CN05.1 格点观测（外部原始输入） | 1981–2010 逐年（`year`=30）、0.25° 网格（`lat` 163 × `lon` 283，14.75–55.25°N、69.75–140.25°E）；含 `R90mm / R95mm / R99mm_intensity` 与 `PrecipVar`；属性 `source`=CN05、`baseline_years`=1981-2010；有效阈值格点 15292 / 46129；6.84 MB |
| `data/图2a_统计数据.txt` | `Fig2.py` 的 `dump_scatter_stats_txt()`（原 `Fig2a.py` 的 `dump_statistics()`） | 纯文本：两个指标各一段，逐模式 `CORR` / `Bias(mm/day)` 明细 + `MEAN(19 modes)` 行 |
| `data/图2b_统计数据.txt` | `Fig2.py` 的 `dump_map_stats_txt()`（原 `Fig2b.py` 的 `dump_statistics()`） | 纯文本：MME vs CN05.1 一行一个指标，列为 `CORR / p_value / NRMSE(%) / OBS_mean / MME_mean / underest(%)` |
| `data/fig2a_stats.csv` | `Fig2.py` 的 `dump_scatter_stats_csv()`（原 `Fig2a.py` 的 `dump_statistics_csv()`） | 长表，一行一个「指标 × 统计量」：`metric, statistic, mean, median, n_models, unit, metric_key`（论文正文引用的“19 个模式的均值”即 `mean` 列） |
| `data/fig2b_stats.csv` | `Fig2.py` 的 `dump_map_stats_csv()`（原 `Fig2b.py` 的 `dump_statistics_csv()`） | 宽表，一行一个指标：`metric, corr, p_value, nrmse_pct, bias, unit, rmse, obs_mean, mme_mean, rel_bias_pct, n_valid, period` |
| `data/fig2_per_model.csv` | `Fig2.py` 的 `dump_scatter_stats_csv()`（`per_model_path` 参数，原 `Fig2a.py`） | 逐模式明细，一行一个「mode × metric」：`mode, metric, CORR, Bias_mm_per_day`，19 模式 × 2 指标 = 38 行 |

两个 CSV 与两个 txt 均以 `utf-8-sig` 编码写出（txt 为 `utf-8`），便于 Excel 直接打开且中文不乱码。

**为什么统计表要分成 `fig2a_stats.csv` 与 `fig2b_stats.csv`**：扁平化之前两个文件都叫 `data/fig2_stats.csv`，分别位于 `a/data/` 与 `b/data/`，互不干扰；合并到同一个 `data/` 后同名会互相覆盖，而二者 **schema 完全不同**——`fig2a_stats.csv` 是 `metric × statistic` 的长表（含 `mean / median / n_models`，对应 19 个模式逐个评估的集合统计），`fig2b_stats.csv` 是每指标一行的宽表（含 `corr / p_value / nrmse_pct / bias / rmse / obs_mean / mme_mean / rel_bias_pct / n_valid / period`，对应 MME 整体评估）。因此按产出脚本分别改名：`fig2a_stats.csv` 由原 `Fig2a.py` 写、`fig2b_stats.csv` 由原 `Fig2b.py` 写（两个脚本合并为 `Fig2.py` 后，分别由 `dump_scatter_stats_csv()` 与 `dump_map_stats_csv()` 写出），两者不可互相替代。同理，`MULTI_MODEL-*.nc` 与 `CN05-OBS-*.nc` 此前在 `a/data/` 与 `b/data/` 各存一份逐字节相同的副本，如今只在 `data/` 下保留一份。

## 产出
| 文件 | 内容 |
|---|---|
| `Fig2.jpg` | **论文成品图，也是模块内唯一的图片产出**：散点面板（CORR 行 + Bias 行），dpi 400 / `bbox_inches="tight"`，300553 B，sha256 `58E27504EA552A91F9D2776F8B9B75DD37E3148D9FE85C4ECE64397F14F9A538`（MD5 `BE704A085308FBF164FFCEADB073A9AE`）。用 `D:\Conda\envs\MET\python.exe` 重跑可逐字节复现 |
| `Fig2a.jpg`（已删除） | 原散点面板的中间图：现在散点面板直接把成品写成 `Fig2.jpg`，不再产生这个文件 |
| `Fig2b.jpg`（不落盘） | 2×2 地图面板（左右列 CN05.1 / HiCPC-MME，上下行两个指标，含 PDF 内嵌直方图与共用色带），运行期渲染到模块之外的临时目录，`finally` 里删除；当前不进入论文成品 |
| `Fig2(2指标).jpg`（已删除） | 并排双指标变体；模块内没有任何脚本会生成它，属历史/手工留档（正文未引用） |
| `data/fig2a_stats.csv` | 19 模式 CORR / Bias 的集合统计（long 格式） |
| `data/fig2b_stats.csv` | MME 对 CN05.1 的评估统计（wide 格式） |
| `data/fig2_per_model.csv` | 逐模式 CORR / Bias 明细 |
| `data/图2a_统计数据.txt` | 散点面板统计的纯文本存档 |
| `data/图2b_统计数据.txt` | MME 统计的纯文本存档 |

## 代码说明
| 脚本 | 作用 | 主要产出 |
|---|---|---|
| `Fig2.py` | 单文件流水线：① 数据准备（两个面板共用，先于绘图）——读两个 `.nc`，把 0.1° 模式场按面积权重粗化到 0.25° 观测网格；② 散点面板 (a)——对 19 个 `case` 逐个取 30 年平均场并与观测平均场算 CORR / Bias，先落盘统计表再绘制 `PANEL_KEYS = ("corr", "bias")` 两行散点图，并把 figure 以 dpi 400 / `bbox_inches="tight"` 直接存成论文成品图 `Fig2.jpg`；③ 地图面板 (b)——对 19 个模式取等权集合平均（MME）后算 MME 与观测的 CORR / Bias / RMSE / NRMSE，绘制 2×2 气候态地图（`r95_cmap` / `precipvar_cmap` 等值线填色 + 中国国界 + 逐面板 PDF 直方图 + 逐行共用色带 + `CORR=(p)` 标注），图片写到模块之外的运行期临时目录（`_make_map_tmpdir()` → `os.makedirs()` 默认权限，`main()` 的 `finally` 里删除） | `Fig2.jpg`、`data/fig2a_stats.csv`、`data/fig2_per_model.csv`、`data/图2a_统计数据.txt`、`data/fig2b_stats.csv`、`data/图2b_统计数据.txt` |

原三个脚本已合并进 `Fig2.py` 并删除：`Fig2a.py` → 散点面板部分，`Fig2b.py` → 地图面板部分，`compose_fig2.py`（`shutil.copyfile(Fig2a.jpg → Fig2.jpg)`）→ 直接由散点面板的 `savefig` 输出成品图 `Fig2.jpg`。合并时按面板重命名了撞名函数：`dump_statistics` → `dump_scatter_stats_txt` / `dump_map_stats_txt`，`dump_statistics_csv` → `dump_scatter_stats_csv` / `dump_map_stats_csv`；`calc_spatial_metrics` 统一采用「含 RMSE / NRMSE」的超集版本（散点面板仍只取 `corr` / `bias`，数值口径不变）。

`Fig2.py` 散点图的版面固定为：画布宽 14.0 cm，面板宽 10.5 cm、高 2.8 cm、行间距 0.75 cm，底行基线 2.0 cm，总高 9.05 cm；CORR 面板纵轴固定 0.92–0.98（刻度 0.94 / 0.96 / 0.98），Bias 面板纵轴由数据自适应。

历史遗留说明（以代码与正文图号为准）：
* `Fig2.py` 地图面板的 docstring 与 `draw_map_panels()` 里仍写作 “Fig. 1(b)”，并仍画 `(b)` 块标号——这是早期图号的遗留，该地图块后来才被编入图 2。
* 地图面板 docstring 中“NRMSE 仅在散点面板 (a) 中给出”同样是修订前的说法：自 2026-10-09 起图 2 只保留 CORR 与 Bias，散点面板也不再画 NRMSE，NRMSE 只在 `图2b_统计数据.txt` 与 `fig2b_stats.csv` 中留档。
* `data/图2a_统计数据.txt` 与 `data/图2b_统计数据.txt` 里 `script:` 一行在扁平化后指向 `src/Pic/Fig2_ModelEvaluation/Fig2a.py` / `Fig2b.py`（原先写作 `a/code/`、`b/code/`）；**合并为单文件后这两行仍保留原脚本名**（代码中已加注释说明），以便这两个归档文件的字节保持不变；数值本身始终未改动。

## 方法说明

本模块扁平化后 **没有 `doc/` 目录，也没有任何 `.md` 说明文件**（改路径前的备份中同样只有 `code/`），故本节依据脚本代码本身，并对照论文正文与格式说明（`Doc/涌现约束_v2.md` §2、`Doc/Tex/formatting-notes.md`）整理。

### 评估设计（论文 §2）
本研究使用 CN05.1 作为参考观测（因其对中国地区极端降水的评估比较准确），对历史时期（1981–2010 年）HiCPC 的日降水输出开展独立评估，采用 Pearson 相关系数（CORR）和偏差（Bias）两项指标进行定量评估。流程为：先分别计算每个 HiCPC 模式与 CN05.1 的降水变率（Precip Var）和极端降水强度（R95 Intensity）；再在对 HiCPC 粗化处理以统一分辨率为 $0.25^\circ \times 0.25^\circ$ 的基础上，将每个模式的指标场与 CN05.1 观测场逐格点对比，并以格点纬度的余弦为面积权重计算空间相关系数（CORR）和偏差（Bias），得到 19 个模式的两个空间统计指标，进而通过散点图展示 19 个模式各指标的分布及均值（图 2）；最后对 19 个模式取等权集合平均（Multi-Model Ensemble, MME），同样以面积加权评估 MME 的整体表现——这一步的产物即 `Fig2.py` 的地图面板流水线与 `fig2b_stats.csv`。

19 个模式（`Fig2.py` 散点图横轴顺序）：ACCESS-CM2、ACCESS-ESM1-5、AWI-CM-1-1-MR、CESM2、CNRM-CM6-1、CanESM5、EC-Earth3-Veg、FGOALS-g3、IITM-ESM、INM-CM4-8、INM-CM5-0、KACE-1-0-G、KIOST-ESM、MPI-ESM1-2-HR、MRI-ESM2-0、NESM3、NorESM2-LM、NorESM2-MM、TaiESM1。

### 两个评估指标
* **R95 Intensity**（代码变量名 `R95mm_intensity`，图例 “R95 Intensity”）：95% 分位阈值在基准期（1981–2010）逐格点计算，且仅使用湿日样本（日降水量 $\geq 1$ mm/day），以避免干旱区因大量无降水日而系统性低估阈值；基准期湿日少于 10 天的格点其阈值设为缺测。R95p 为一年内日降水量超过该阈值的累计降水量，R95d 为相应的降水日数，二者之比即 R95 Intensity（论文式 (6)）。上述阈值口径可从 `.nc` 属性中核对：`wet_day_threshold` = `1.0 mm/day`、`min_wet_days_for_statistics` = `10`。
* **Precip Var**（代码变量名 `PrecipVar`）：降水变率，定义为经预处理后日降水扰动序列的逐年时间标准差 $\sigma(t)$。预处理先去除年循环、再去除长期线性趋势，得到无季节循环、无长期线性趋势的纯净扰动序列，然后计算该序列的标准差（总体标准差，即以 $D_t$ 为分母）（论文式 (7)）。

### 预处理：面积加权粗化到观测网格
两个面板共用同一条重网格链路（合并前两个脚本各写了一份完全相同的实现，现已并为一份 `remap_model_to_obs_grid()`）：`_cell_bounds_from_centers()` 由格点中心构造经纬向单元边界，`_build_overlap_matrix()` 构造源网格与目标网格的重叠长度矩阵，`_area_weighted_remap_numpy()` 先按纬向重叠长度 × $\cos(\mathrm{lat})$ 做纬向加权（权重与数据一起累加，`np.where(np.isfinite(...))` 使 NaN 格点既不进入分子也不进入分母），再按经向重叠长度做经向加权，最终得到面积加权的守恒式平均。源数据先 `sortby("lat").sortby("lon")` 并转置为 `(..., lat, lon)`，输出坐标替换为观测网格的 `lat` / `lon`。本例中即把 0.1°（400 × 700）的 HiCPC 场粗化到 0.25°（163 × 283）的 CN05.1 网格；`case` / `Mode` / `SSP` / `source_file` 等坐标原样继承。年份取模式与观测的共同年份并按 `EVAL_START_YEAR = 1981`、`EVAL_END_YEAR = 2010` 截取。

### CORR / Bias 统计量的实现
`calc_spatial_metrics()` 计算模式场与观测场的空间统计指标，两个面板共用：
* 有效样本为模式与观测同时非 NaN 的格点；有效格点少于 5 个时返回全 NaN。
* 权重 $w = \max(\cos(\mathrm{lat}), 0)$（等经纬度网格上的面积权重），**CORR 与 Bias 使用同一套权重**，以保证同一幅图内口径一致。
* 面积加权均值、协方差与方差 → $\mathrm{CORR} = \mathrm{cov} / \sqrt{\mathrm{var}_{model} \cdot \mathrm{var}_{obs}}$；$\mathrm{Bias} = \overline{OBS} - \overline{MODEL}$，**正值为模式低估**。
* 相关系数显著性用 $t = r\sqrt{(n-2)/(1-r^2)}$、$p = 2 \cdot \mathrm{stdtr}(n-2, -|t|)$，$n$ 为有效格点数（本模块为 15292）。
* 地图面板另外需要 $\mathrm{RMSE} = \sqrt{\sum w (m-o)^2 / \sum w}$ 与 $\mathrm{NRMSE} = \mathrm{RMSE} / |\overline{OBS}|$。合并前只有 `Fig2b.py` 的指标函数返回这两项，`Fig2a.py` 的**不含**；合并后 `calc_spatial_metrics()` 统一返回含 RMSE / NRMSE 的超集，散点面板仍然只取 `corr` / `bias`（2026-10-09 修订后图 2 只保留 CORR 与 Bias 两行），因此口径与数值均未改变。
* **图上两个 $p$ 值口径不同**：散点图 CORR 面板上方标注的 $p$ 值来自 `scipy.stats.ttest_1samp`，检验的是“19 个模式的 CORR 均值是否显著异于 0”（$p<0.001$ 时格式化为 `(p < 0.001)`）；`fig2b_stats.csv` 中的 `p_value` 检验的是“MME 与观测这一对空间场的相关系数是否显著”（双侧 $t$ 检验）。两种口径在本模块均远小于 0.001。

### 统计结果（磁盘现有归档）
散点面板、19 个模式逐个评估的集合统计（`data/fig2a_stats.csv`，`fig2_per_model.csv` 为其逐模式明细，`图2a_统计数据.txt` 为同一批数字的纯文本）：

| 指标 | 统计量 | 19 模式均值 | 中位数 | 逐模式区间 | n_models | 单位 |
|---|---|---|---|---|---|---|
| PrecipVar | CORR | 0.9508 | 0.9507 | 0.9425（CanESM5）– 0.9568（FGOALS-g3） | 19 | 1 |
| PrecipVar | Bias | 0.3702 | 0.3588 | 0.2192（EC-Earth3-Veg）– 0.6277（CanESM5） | 19 | mm/day |
| R95 Intensity | CORR | 0.9363 | 0.9374 | 0.9231（CanESM5）– 0.9437（EC-Earth3-Veg） | 19 | 1 |
| R95 Intensity | Bias | 3.3463 | 3.2571 | 2.0484（EC-Earth3-Veg）– 5.5761（CanESM5） | 19 | mm/day |

MME 整体评估（`data/fig2b_stats.csv`，`图2b_统计数据.txt` 为同一批数字的纯文本，其中 `underest(%)` 即 `rel_bias_pct`）：

| 指标 | CORR | p_value | NRMSE (%) | Bias (mm/day) | RMSE | OBS_mean | MME_mean | 相对偏差 (%) | n_valid | 时段 |
|---|---|---|---|---|---|---|---|---|---|---|
| Precip Var | 0.9535 | ≈0 | 26.5022 | 0.3701 | 0.9933 | 3.7482 | 3.3781 | 9.87 | 15292 | 1981-2010 |
| R95 Intensity | 0.9428 | ≈0 | 27.8038 | 3.3540 | 7.3310 | 26.3669 | 23.0128 | 12.72 | 15292 | 1981-2010 |

论文正文与图注引用的正是上表数字：19 个模式分别与观测对比的均值中，降水变率与极端降水强度的空间相关系数分别为 0.951 与 0.936，偏差分别为 0.37 与 3.35 mm/day（$p<0.001$），表明极端降水强度的偏差明显大于降水变率；MME 在极端降水强度上与 CN05.1 有较高的空间一致性，但强度整体偏低（观测均值 26.37 mm/day 对应 MME 23.01 mm/day，约 13%）。

### 论文图注（`Doc/涌现约束_v2.md` §2 / `Doc/Tex/manuscript.tex`）
> 依据历史时期（1981–2010）观测 CN05.1 数据对 HiCPC 多模式的对比评估。散点图给出 19 个 CMIP6 模式在中国区域的降水变率（PrecipVar index，蓝色）与极端降水强度（R95 Intensity，红色）相对于 CN05.1 观测的相关系数（CORR，上行）和偏差（Bias，mm/day，下行）两项评估指标；横轴为 19 个模式，水平虚线为各指标的 19 模式平均值，每个子图上方标注该平均值。

### 修订记录
* **2026-09-22**（见 `compose_fig2.py` docstring）：按作者要求去掉图 2 的地图面板 (b)。理由是该面板展示的 CN05.1 与 MME 气候态空间分布与图 3（OBS − MME 偏差场）内容重复。`compose_fig2.py` 因此由“上下拼合”改为“直接复制”，`Fig2b.py` 保留以备查与供正文数字。
* **2026-10-09**（见 `Doc/Tex/formatting-notes.md` “图 2 修订”）：按作者要求图 2 仅保留 CORR 和 Bias 两行。Markdown 与 TeX 同步删除 RMSE、NRMSE 原式 (8)、(9)，移除相关方法、数值和图注描述，现保留公式 (1) 至 (7)；图 2 图片由修改后的绘图代码重新生成，TeX 工程中的图片副本同步更新。
* **模块扁平化**：原 `a/`、`b/` 两个子模块（各含 `code/ data/ doc/ fig/`）合并为本目录，脚本内路径改为 `Path(__file__).parent`；`fig2_stats.csv` 因两份 schema 不同而拆分为 `fig2a_stats.csv` 与 `fig2b_stats.csv`；重复的 `.nc` 文件只保留一份。
* **三脚本合并为单文件**：`Fig2a.py` + `Fig2b.py` + `compose_fig2.py` 合并为本目录下的 `Fig2.py` 并删除原三个脚本。数据准备（读取 + 重网格）由两个面板共用、只做一次；`main()` 先跑散点面板再跑地图面板，可用 `--scatter-only` / `--map-only` 只跑其中一半；散点面板的 `savefig` 直接产出成品图，因此不再有 `compose_fig2.py` 这一步。合并后核对：`data/` 下 5 个归档文件与地图面板 JPG 重新生成后与合并前逐字节一致。
* **图片产出收敛到「模块根恰好 4 项」**：模块根目录固定为 `Fig2.py`、`Fig2.jpg`、`data/`、`README.md`。散点面板只写论文成品图 `Fig2.jpg`（不再产生中间文件 `Fig2a.jpg`）；地图面板仍完整渲染，但图片只在运行期写进模块之外的临时目录并在 `finally` 里删除；根目录下原有的 `Fig2a.jpg`、`Fig2b.jpg`、`Fig2(2指标).jpg` 已删除。`FIG2_OUT` 环境变量随之移除（它原用于给 `Fig2a.jpg` 改名）。
* **验证环境**：图件必须用仓库自带的 `D:\Conda\envs\MET\python.exe`（Python 3.11 + matplotlib 3.10.8）运行——它能把 `Fig2.jpg` 与 `data/` 下 5 个统计文件逐字节复现（`Fig2.jpg` sha256 `58E27504…F9A538`，300553 B）；PATH 上的 Python 3.14 + matplotlib 3.10.9 会把散点图 JPEG 渲染差出 75 字节（亚像素字形抗锯齿），统计文件则不受影响。
* **已知残留（非本模块产出，删除被系统拒绝）**：受限沙箱下 `tempfile.mkdtemp()` 以 `0o700` 创建的目录会被永久锁死，早期探测在模块根目录留下了两个**空目录**：`_tmp_fig2_map_y4pmywfi` 与 `tmp1b62ax04`。`Remove-Item`、`rmdir`、`takeown`、`icacls`、重命名均返回 Access denied；请在非受限的普通命令行（或重启资源管理器后）手工删除，删除后模块根目录即恢复为恰好 4 项。`Fig2.py` 现已改用 `_make_map_tmpdir()`（`os.makedirs()` 默认权限 + 模块之外），不会再产生此类目录。
