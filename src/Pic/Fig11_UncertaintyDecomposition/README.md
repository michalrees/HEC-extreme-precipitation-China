# 图 11 —— 先验/后验不确定性缩减的尺度分解

本模块生成论文图 11：把 SSP2-4.5 情景下的先验 σ 场与后验 σ 场（模式间标准差）各做一次 2D DCT，
按 Fig10 检出的断点（1409 / 4898 km）分成小、中、大三个尺度档，再逐区域统计各档的不确定性缩减率 $R_b$。
它只回答一个问题——HEC 对模式间不确定性的压缩，在三个尺度上是否相同。答案是**几乎相同**：
全国三档为 20.9% / 19.5% / 21.2%，极差仅 1.7 个百分点，说明压缩在全谱段同步发生、没有尺度偏好。
成品为单面板分组柱状图，对应论文 **3.3 节**（`\label{sec:3.3}`，Uncertainty decomposition of prior and
posterior estimates），与 3.2 节的图 10（分解调整场 Bias）互补：图 10 问"校正发生在哪个尺度"，
图 11 问"压缩在各尺度上是否一致"。

## 目录结构
```
Fig11_UncertaintyDecomposition/
├── Fig11.py               # 单文件模块（2026-10-12 合并）：主流水线 + 谱对照 + 三个诊断函数
├── Fig11.jpg              # 论文成品图（单面板：各区域三档缩减率）
├── data/                  # 原始数据 + 代码计算的统计数据
│   ├── uncertainty_reduction.csv  # 全国 + 七分区 + 三流域的分档幅值/缩减量/缩减率（run_fig11() 产出）
│   └── uncertainty_spectrum.csv   # 先验/后验 σ 与方差缩减量的 DCT 波长-方差谱（run_spectrum() 产出）
└── README.md
```

**本目录恰好 4 项**（`Fig11.py`、`Fig11.jpg`、`data/`、`README.md`）：谱对照步骤的备用谱图
`fig11a.jpg` 只在运行期写到一个**模块之外**的临时目录（工作区根下的 `_tmp_fig11_<随机 8 位>`），
`main()` 退出 `with` 块时连同目录一起删除，运行前后都不会在本目录留下文件。

> 原 `尺度谱.py`、`_calc_cancellation.py`、`_calc_cross_check.py`、`_trace_13_38_49.py` 四个脚本已于
> 2026-10-12 合并进 `Fig11.py`（与图 10 模块把 `region_stats.py` 合并进来的做法一致）：全模块只有一个
> 命名空间，不再有 `from Fig11 import ...` 这类跨脚本导入，掩膜/加权/DCT 工具被谱对照与诊断函数直接复用。

## 运行
```bash
cd "F:\Program\2Process\4HiCPC\Using hierarchical emergent constraints to reduce the uncertainty in future extreme precipitation projections over China"
python "src/Pic/Fig11_UncertaintyDecomposition/Fig11.py"
```
不带参数即跑完整流水线，顺序与原两脚本一致：
① `run_fig11()` → `data/uncertainty_reduction.csv` + `Fig11.jpg`；
② `run_spectrum()` → `data/uncertainty_spectrum.csv`（备用谱图 `fig11a.jpg` 只写模块外的运行期
临时目录，退出即整目录删除，**不在本目录落盘**）。

> 解释器提示：本模块的三份产物是用 `D:\Conda\envs\MET\python.exe`（Python 3.11 / matplotlib 3.10.8 /
> pandas 2.3.3）之外的环境（PATH 上的 Python 3.14 / matplotlib 3.10.9 / pandas 3.0.3）生成的——
> 只有后者能与仓库现有产物**逐字节一致**（前者会因浮点末位与字体栅格化差异产出不同字节）。
> 复现既有产物时请沿用产出该产物的解释器。

依赖：`numpy / scipy`（`scipy.fft.dctn, idctn`）`/ pandas / xarray / matplotlib`（含
`matplotlib.ticker`）`/ pyshp`（`import shapefile`）`/ shapely`。
脚本用 `Path(__file__).resolve().parents` 自下向上定位仓库根（同时含 `src/` 与 `Doc/`），无需修改路径，
也**不再要求把模块目录当作工作目录**。

三个诊断函数由命令行开关触发，**默认一律不运行**（只打印，不写任何产物）：

```bash
python "src/Pic/Fig11_UncertaintyDecomposition/Fig11.py" --cancellation  # 诊断① 有符号 vs 绝对值区域平均的相消率
python "src/Pic/Fig11_UncertaintyDecomposition/Fig11.py" --cross-check   # 诊断② 三种总缩减率口径交叉校验
python "src/Pic/Fig11_UncertaintyDecomposition/Fig11.py" --trace         # 诊断③ 已废弃的 13/38/49 溯源
```

给任一开关时只跑诊断、不重跑流水线（不会覆盖产物）；多个开关可同时给出。
`--trace` 读的是 git HEAD 里的旧产物
（`git show HEAD:src/Pic/Fig11_UncertaintyDecomposition/data/uncertainty_decomposition.csv`），
该路径在当前 git HEAD 中已不存在，故该开关会打印提示并以退出码 1 结束（不再抛异常栈）；
它只依赖 `pandas` 与 `git` 命令，与当前磁盘上的 `data/` 内容无关。

## 数据来源
| 文件 | 来源 / 生成脚本 | 说明 |
|---|---|---|
| `Output/EC/China/HEC_ssp245_PrecipVar_to_R95mm_intensity.nc` | 上游脚本 6 的规范输出（仓库 `Output/EC/China/` 存档） | 提供 `lat`/`lon` 与 `prior_std`、`posterior_std` 两个 σ 场；`prior_std` 由脚本 6 用 `np.nanstd(..., ddof=1)` 写入，**是模式间标准差 σ 而不是方差** |
| `src/Pic/Fig10_BiasScaleDecomposition/data/breakpoint.json` | **Fig10 模块（`Fig10_BiasScaleDecomposition/`）产出** | 本模块只取其中的 `selected_breakpoints`（1408.97 与 4897.51 km），`sorted()` 后过滤 `≥200`、取前两个作为分档断点；**断点由 Fig10 从调整场 Bias 的谱分析检出，本模块沿用、不重新检测**（谱对照步骤另取 `multi_breakpoints` 备用） |
| `Data/China/cnmap.shp` | 仓库原始底图（附 `cnmap.shx`、`cnmap.prj`） | 全国陆地掩膜：各要素 `unary_union` → `polygonize` → `buffer(0)`，逐格点 `prep(...).intersects(Point)` |
| `Data/River/HuanghaiRiver_polygon.shp`、`PearlRiver_polygon.shp`、`YangtzeRiver_polygon.shp` | 仓库原始矢量 | 黄河、珠江、长江流域掩膜；**仅入 CSV、不出图**。文件不存在时该流域自动跳过（`if rfp.exists()`） |
| `data/uncertainty_reduction.csv` | `Fig11.py` 的 `run_fig11()` 生成 | 区域统计结果（列见《产出》） |
| `data/uncertainty_spectrum.csv` | `Fig11.py` 的 `run_spectrum()` 生成 | 谱数据（列见《产出》） |

> 图 11 对 Fig10 的依赖是**单点、只读**的：只要 `breakpoint.json` 存在并含 `selected_breakpoints`，
> 本模块即可独立重跑；若删除 `doc/` 或改动本模块内的文件名，均不影响该依赖。

## 产出
| 文件 | 内容 |
|---|---|
| `Fig11.jpg` | 论文成品图（单面板，`figsize=(7.874, 4.3)`，dpi 400）：8 组（全国 + 七个分区）× 3 档缩减率（%）分组柱，纵轴 `Reduction rate of σ per scale (%)`，每根柱顶标注数值，柱上按 `rate_s*` 直接绘制；三个流域被 `df[~df["region"].isin(流域)]` 过滤掉，不在图内。全国总缩减率的水平参考线及其面板内注记已于 2026-10-12 按作者要求删除——`ref` 仍计算并打印（全场口径 20.7%），但只在论文图注中说明 |
| `data/uncertainty_reduction.csv` | 11 行（全国 + 七分区 + 三流域），列：`region`、`n_grid`、`sigma_prior`、`sigma_post`、`total_reduction`、`r_total`、`mag_prior_s1..s3`、`mag_post_s1..s3`、`reduction_s1..s3`、`rate_s1..s3`（`s1/s2/s3` = 小/中/大三档） |
| `data/uncertainty_spectrum.csv` | 41 个波长分箱（对数分箱、45 个边界），列：`wavelength_km`（几何中心）、`prior_var`、`post_var`、`reduction_var`。**注意 `reduction_var` 是 `prior_std² − posterior_std²` 的谱，而 `prior_var`/`post_var` 是 σ 场本身的谱**，两者不同量纲口径 |
| `fig11a.jpg`（运行期临时产物，**不落盘**） | `run_spectrum()` 生成的双面板备用谱图（(a) 先验/后验 σ 谱、(b) 方差缩减谱，均标注断点）——**非论文成品图**。合并为单文件后它只写到模块之外的运行期临时目录（工作区根下 `_tmp_fig11_<随机 8 位>`），由 `main()` 退出 `with` 块时连同目录一起删除，故模块根与 `data/` 都不会留下它 |

## 代码说明
单文件 `Fig11.py` 内的函数分工（原五个脚本合并为一个命名空间）：

| 函数 | 作用 | 主要产出 |
|---|---|---|
| `run_fig11()` | **主入口**。读 nc 的 σ 场 → `compute_wavelength_map()` 造二维波长场、`dct_filter_bands()` 做一次全国 2D DCT 并按断点分档逆变换 → `make_china_mask()` / `region_masks()` / `build_river_mask()` 造掩膜 → `_wmean_abs()` 做 cos φ 面积加权的区域平均绝对值 → `_plot_rate()` 出单面板柱图 | `data/uncertainty_reduction.csv`、`Fig11.jpg` |
| `compute_spectrum()` + `run_spectrum()` | 谱对照步骤（原 `尺度谱.py`，不产生论文成品图）。对 `prior_std`、`posterior_std` 及方差缩减量三个场各算一条 2D DCT 波长-方差谱（对数分箱内 power 求和），并画出选中断点竖线。绘图包在 `plt.rc_context(plt.rcParamsDefault)` 内，以保持与原独立脚本相同的默认字体/字号。谱图落点由 `_spectrum_scratch()` 提供（模块外的运行期临时目录，退出即整目录删除；**不采用 `tempfile.TemporaryDirectory()`**：其固定的 `0o700` 权限位在某些 Windows 受限环境下会生成既写不进、也删不掉的目录） | `data/uncertainty_spectrum.csv`（谱图 `fig11a.jpg` 仅存在于运行期临时目录） |
| `run_cancellation()`（`--cancellation`） | **辅助核算，非图件流水线**（原 `_calc_cancellation.py`）。对全国（cnmap 陆地掩膜）与华中（经纬框 ∩ 陆地）的先验 σ 三档分量，比较有符号区域平均 ⟨σ_b⟩ 与区域平均绝对值 ⟨|σ_b|⟩，给出相消率 1 − |⟨σ_b⟩| / ⟨|σ_b|⟩；并在无掩膜整矩形域上验证带通分量本身零均值。只读运行，无产物，**默认不跑** | 仅终端打印 |
| `run_cross_check()`（`--cross-check`） | **辅助核算，非图件流水线**（原 `_calc_cross_check.py`）。用 cnmap 陆地掩膜交叉校验三种总缩减率口径：① 全场直接算 `1−⟨σ_post⟩/⟨σ_prior⟩`（20.7%）、② 三档幅值之和（20.6%）、③ 逐格点缩减率的区域平均 `⟨1−σ_post/σ_prior⟩`（图 6b 面板口径，19.2%）。断点在函数内重算、直接做 DCT，不再依赖 `data/` 下已清理的 `*.npy` 中间场。**默认不跑** | 仅终端打印 |
| `run_trace()`（`--trace`） | **溯源脚本，非图件流水线**（原 `_trace_13_38_49.py`）。用 `git show HEAD:src/Pic/Fig11_UncertaintyDecomposition/data/uncertainty_decomposition.csv` 取旧版产物，按"三档幅值之和"与"全场总量之比"两种定义各算一遍三档份额，核对草稿摘要里已废弃的 13/38/49 究竟出自哪一版口径。**默认不跑**；该路径在当前 git HEAD 中已不存在，故 `git show` 失败时打印提示并返回退出码 1（不抛异常栈） | 仅终端打印 |
| `main()` | 解析开关：无开关时依次调用 `run_fig11()` → `run_spectrum()`（保持原两脚本的顺序）；给出诊断开关时只跑对应诊断 | — |
| 共享工具 | `compute_wavelength_map()`、`dct_filter_bands()`、`make_china_mask()`、`region_masks()`、`build_river_mask()`、`_lat_weights()`、`_wmean_abs()`（另有仅诊断用的 `_wmean_signed()`）——原跨脚本 `from Fig11 import ...` 已消失，谱对照与两个核算函数直接复用同一份实现 | — |

## 方法说明

> 2026-10-12 重写；同日按作者指示**只保留"三档缩减率"，删去各尺度贡献份额**（份额差异只是
> 各档先验量级不同所致，"贡献大"≠"压缩得多"，单列易被误读）。旧版（先验/后验 σ 的**有符号**
> 区域平均热图 + 有符号缩减率热图）已废弃：σ 场恒为正，但有符号的带通区域平均在小尺度上接近
> 零甚至为负（华北 −0.15、华中 −0.40 mm/day），读起来像"不确定性为负"。

### 一、要回答的问题

| 图 11 | 问题 | 统计量 |
|---|---|---|
| 单面板 | 先验到后验的缩减，在三个尺度上是否相同？ | 各尺度缩减率 $R_b$（%） |

**报告的核心结果**：全国三档缩减率 20.9% / 19.5% / 21.2%，极差 1.7 个百分点，远小于同一尺度
内部的区域差异 → 压缩在全谱段同步发生、没有尺度偏好。

### 二、数据

基于 SSP2-4.5 情景下以 PrecipVar 为历史指标、R95mm_intensity 为未来指标的涌现约束结果：

- 输入：`Output/EC/China/HEC_ssp245_PrecipVar_to_R95mm_intensity.nc`（脚本 6 的规范输出）
  - `prior_std`：先验不确定性场，实为**模式间标准差 σ**（脚本 6 用 `np.nanstd(..., ddof=1)` 写入），
    不是方差；本图直接对其做尺度分解。
  - `posterior_std`：后验不确定性场，同为 σ 口径。
- 断点：`src/Pic/Fig10_BiasScaleDecomposition/data/breakpoint.json` 的 `selected_breakpoints`
  （1409 与 4898 km，取自调整场 Bias 的谱分析，本图沿用、不重新检测）。

### 三、尺度分解

与 3.2 节（图 10）同一实现：全场做一次 2D DCT（`scipy.fft.dctn`, type=2, norm="ortho"），
按与 DCT 系数一一对应的二维波长场分段掩膜，再逆变换回空间场：

$$\tilde f_b(x,y) = \text{IDCT-II}\{F(k_x,k_y)\cdot\mathbb{1}\{\lambda_b^{\min} \le \lambda(k_x,k_y) < \lambda_b^{\max}\}\}$$

| 档 | 波长范围 | 说明 |
|---|---|---|
| 小尺度 | $\lambda \le 1409$ km | 含 200 km 以下的网格尺度分量 |
| 中尺度 | $1409\text{–}4898$ km | |
| 大尺度 | $\ge 4898$ km | 承接零频项（σ 是幅值场，**有意不去均值**，与 3.2 节一致） |

恒等式：$\sum_b \tilde f_b = f$（实测重建误差 9.8e-15）。因不去均值，**三档幅值之和恰等于
该区域的全场平均 σ**（全国 2.377 mm/day），这也使"各档幅值/缩减量可加"成立。

### 四、区域统计

- 区域：全国（`cnmap.shp` polygonize 后的陆地掩膜，15387 个有效格点）+ 七个分区
  （经纬框 ∩ 陆地掩膜）；三个流域（黄河、珠江、长江）**一并计算并写入 CSV**，但不出图
  （流域面积小、受区域掩膜影响大）。
- 所有区域统计按 $\cos\varphi$ 面积加权，报告的是**区域平均**（每格点的量，单位 mm/day），
  不是区域内格点求和的总量。
- 各档统计量取带通重构分量的**区域平均绝对值**：

$$\langle|\sigma_b|\rangle = \frac{\sum_{(i,j)\in\mathcal M_r} w_{ij}\,|\tilde f_b(i,j)|}{\sum_{(i,j)\in\mathcal M_r} w_{ij}},\qquad w_{ij}=\cos\varphi_j$$

  为什么必须取绝对值：带通分量是有符号残差，其**全域**平均在前两档恒等于 0（不含零频），
  在有掩膜的区域上也会大量相消——全国小尺度档 ⟨σ₁⟩ = 0.254 而 ⟨|σ₁|⟩ = 0.612（相消 58.5%），
  华中 ⟨σ₁⟩ = −0.395 而 ⟨|σ₁|⟩ = 0.717（相消 44.8%）；相消率随尺度减小而升高（小尺度 45%–59%、
  中尺度 2%、大尺度 0%），故有符号平均会**系统性地压低小尺度、抬高相对大尺度**，把结论弄反。
  取幅值后恒为非负、可加（三档之和 = 全场平均 σ），并与 σ 本身"先平方再平均再开方"的绝对值型
  构造保持一致。复核：`python Fig11.py --cancellation`。

### 五、统计量定义

$$R_b = \frac{\langle|\sigma_{\mathrm{prior},b}|\rangle - \langle|\sigma_{\mathrm{post},b}|\rangle}{\langle|\sigma_{\mathrm{prior},b}|\rangle},\qquad
r_{\text{tot}} = \frac{\sum_b\bigl(\langle|\sigma_{\mathrm{prior},b}|\rangle - \langle|\sigma_{\mathrm{post},b}|\rangle\bigr)}{\sum_b\langle|\sigma_{\mathrm{prior},b}|\rangle}$$

区域总缩减率另有独立算法可校验：不经分档、直接由全场先验与后验 σ 相除，全国得 20.7%
（分档求和口径 20.6%，差 0.1 个百分点，来自分解基线 2.377 对 2.002 的绝对幅值比）。
详见 `python Fig11.py --cross-check`。

> **不再报告"各尺度对总缩减量的贡献份额"**：该量定义为 $\Delta_b/\sum_b\Delta_b$，其大小几乎
> 完全由各档先验不确定性量级决定（0.61 / 0.80 / 0.96 mm/day），而非各档被压缩的难易：
> 三档缩减率既然相同，"份额"只会给出"大尺度贡献最大（41.8%）"这种容易被读成
> "约束偏向大尺度"的结论。份额数据如需查证，可由 CSV 的 `reduction_s*` 列现算。

### 六、关键数值（SSP2-4.5，`data/uncertainty_reduction.csv`）

| 区域 | 先验 σ | 后验 σ | 总缩减率 | $R$ 小 / 中 / 大 |
|---|---|---|---|---|
| 全国 | 2.377 | 1.888 | 20.6% | 20.9 / 19.5 / 21.2 |
| 华北 | 2.952 | 2.374 | 19.6% | 19.8 / 18.5 / 20.7 |
| 东北 | 2.451 | 1.982 | 19.1% | 21.0 / 18.6 / 18.4 |
| 西北 | 1.557 | 1.292 | 17.1% | 16.3 / 14.3 / 19.5 |
| 西南 | 2.443 | 1.863 | 23.7% | 22.8 / 27.5 / 22.9 |
| 华东 | 3.571 | 2.815 | 21.2% | 26.8 / 17.6 / 22.1 |
| 华南 | 4.265 | 3.178 | 25.5% | 25.2 / 27.9 / 23.5 |
| 华中 | 3.860 | 2.987 | 22.6% | 28.5 / 20.2 / 22.7 |

要点：三档缩减率处处相近（档间极差 ≤4 个百分点），区域差异远大于尺度差异；
区域总缩减率随湿润度升高（西北 17.1% → 华南 25.5%）。

### 七、与图 10（3.2 节）的分工

- 图 10 分解的是**调整场** Bias = Posterior − Prior，回答"校正发生在哪个尺度、以何种形式"；
  其空间变率高度集中于小尺度（全国 72.1%），但小尺度正负相消、对净调整量贡献极小。
- 图 11 分解的是**不确定性场 σ 自身**，回答"压缩在各尺度上是否一致"。
- 两图互补给出的判据：约束对小尺度空间结构的调整量最大（变率份额），但**对不确定性的压缩
  在全谱段等比例发生**；两处"小尺度"的含义不同，引用时不可混用。

### 八、产物与复现

| 文件 / 入口 | 说明 |
|---|---|
| `Fig11.py` | 单文件全流程：读 nc → DCT 分解 → 区域统计 → 单面板出图，随后接着跑谱对照；同时是两份 CSV 的生产者 |
| `data/uncertainty_reduction.csv` | 全国 + 七分区 + 三流域：`mag_prior_s*`、`mag_post_s*`、`reduction_s*`、`rate_s*`、`sigma_prior/post`、`total_reduction`、`r_total`（另有 `n_grid`） |
| `Fig11.jpg` | 单面板图（各区域三档缩减率，按 `rate_s*` 直接绘制）。全国总缩减率的参考线及其面板内注记已于 2026-10-12 按作者要求删除，`ref`（全场口径 20.7%）仍计算打印、只在图注中说明 |
| `data/uncertainty_spectrum.csv`（+ 运行期临时谱图 `fig11a.jpg`） | 谱对照步骤 `run_spectrum()` 的产物：波长-方差谱数据落盘；双面板备用谱图只写模块外的运行期临时目录、退出即删 |
| `--cross-check` | 三种缩减率口径交叉校验（直接全场 20.7%、三档求和 20.6%、逐格点平均 19.2%） |
| `--cancellation` | 有符号平均的相消率实测（第四节论证的依据） |
| `--trace` | 从 git HEAD 旧产物复算，用于核对已废弃的 13/38/49 的出处 |

运行：在仓库根执行 `python "src/Pic/Fig11_UncertaintyDecomposition/Fig11.py"`
（仅需 numpy/scipy/pandas/xarray/pyshp/shapely/matplotlib）；诊断加 `--cancellation` / `--cross-check` / `--trace`。
