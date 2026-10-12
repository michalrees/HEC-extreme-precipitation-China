# 图 7 —— 模式稳健性检查（Leave-one-model-out / Leave-one-family-out）

把 19 个 CMIP6 模式（HiCPC 降尺度产品）中的任意一个、或任意一簇同源模式家族从集合里剔掉之后，正文 Fig.6 那条涌现约束诊断链（相关系数 $r$ → 不确定性缩减率 $\Delta=1-\sigma_{\mathrm{post}}/\sigma_{\mathrm{prior}}$ → 后验 $-$ 先验调整场）还成不成立？本目录就是在**逐格点**上把整条链重算 24 遍（19 组逐个剔除单模式 + 4 组逐个剔除模式家族 + 1 组家族边界敏感性试验），再出一张龙卷风图。它对应二修意见一之(2)「查看排除单个模式或模式家族后的结果稳健性」，同时回应意见四「CMIP6 模式之间的机构与代码亲缘关系」。结果服务于正文 §3.1（`Doc/涌现约束_v2.md`），在正文中编号为 **Fig.7**（`doc/` 下归档的三份说明按更早的编号称其为"图 6"/"图 9"）。

## 一句话结论

稳健。 24 个剔除试验中，全国面积加权平均 $r$ 只在 0.820–0.851 之间变动
（相对变幅 ≤ 2.4%），不确定性缩减率只在 16.8%–20.4% 之间变动
（相对变幅 ≤ 11.1%）；相关系数空间型与参照场的型相关系数始终 ≥ 0.907，
缩减率空间型始终 ≥ 0.957；达到显著判据的面积比例从未低于 97.1%
（参照 98.5%–98.7%）。唯一值得写进正文的保留意见是：`CanESM5` 是唯一的强杠杆模式，
单剔它会把全国平均缩减率从 19.0% 拉到 16.9%（−2.1 个百分点），
但即使如此，空间格局与区域排序都不变。

> **口径提示（2026-10 重跑）**：上面这段是归档 README 与 2026-09-22 版《方法说明》的数值。
> 此后观测层口径固定为 SEM（`USE_OBS_STANDARD_ERROR = True`）并重跑了稳健性检查（现 `Fig7.py`），
> 当前 `data/` 中的数字为：全国平均 $r$ 参照 0.847–0.849、24 个剔除算例区间 0.833–0.857
> （最大相对变幅 1.7%）；不确定性缩减率参照 19.1%–19.8%、区间 17.2%–20.6%
> （最大绝对变幅 2.0 个百分点）；显著面积比例参照 98.5%–98.7%、最低 97.1%；
> 型相关系数 $r$ 场 ≥ 0.907、缩减率场 ≥ 0.957（未变）。
> 结论不变，但 `CanESM5` 已不是唯一的强杠杆模式：当前数据下 `FGOALS-g3` 的影响与它同量级
> （SSP2-4.5：`CanESM5` 使 $r$ 由 0.849 降至 0.835、缩减率由 19.2% 降至 17.3%；
> `FGOALS-g3` 的 $\Delta r=-0.014$）。逐项当前值见「方法说明 4.7」。

## 目录结构

```
Fig7_ModelRobustness/
├── Fig7.py                 # 唯一脚本：路径/区域/重网格/HEC 子集解算 + 主计算 + 出图 + 自检
├── Fig7.jpg                # 论文成品图
├── data/                   # 原始数据 + 代码计算的统计数据
│   ├── robustness_ssp126.nc     # 25 算例 × 逐格点诊断场（SSP1-2.6）
│   ├── robustness_ssp245.nc     # 同上（SSP2-4.5）
│   ├── robustness_ssp585.nc     # 同上（SSP5-8.5）
│   ├── case_region_stats.csv    # 逐（情景, 算例, 区域）统计量（825 行）
│   ├── map_similarity.csv       # 逐（情景, 算例）空间型相似度（75 行）
│   ├── spread_vs_baseline.csv   # 逐（情景, 区域, 指标）剔除敏感性（132 行）
│   ├── run_meta.csv             # 运行元信息与自检偏差（10 行）
│   └── cache/                   # 可选：逐模式重网格缓存（自动生成，当前不存在）
└── README.md
```

原 `code/`、`fig/`、`doc/` 三个子目录已扁平化：脚本上移到模块根，`FIG_DIR = STUDY_ROOT`
即模块根（图片直接输出到根目录）；`doc/` 下三份说明（`模式稳健性检查_方法说明.md`、
`图件说明.md`、`正文插入段落_3.1模式稳健性.md`）的内容已全部并入本 README 的「方法说明」一节。

原 `00_hec_common.py`（公共库）、`01_robustness_check.py`（主计算）、`02_make_figures.py`（出图）、
`03_selftest.py`（自检）四个脚本已合并为**单一文件 `Fig7.py`**，不再有跨脚本 `import`：
路径常量、模式清单与家族分组、区域掩膜、重网格、`hec_subset()` 解算器、25 算例 × 3 情景的
主计算、龙卷风图与自检都在同一个命名空间里。`main()` 的默认流程是"先算稳健性、再出图"；
自检改由 `--selftest` 单独触发，不参与默认流程。

## 运行

```bash
cd "F:\Program\2Process\4HiCPC\Using hierarchical emergent constraints to reduce the uncertainty in future extreme precipitation projections over China"
python "src/Pic/Fig7_ModelRobustness/Fig7.py" --selftest   # 自检 T1–T6，约 15 秒（只自检，不算不出图）
python "src/Pic/Fig7_ModelRobustness/Fig7.py"              # 全量：稳健性检查约 45 秒 + 出图约 90 秒
```

依赖：`numpy / scipy / pandas / xarray / matplotlib / cartopy / pyshp / shapely`
（`shapefile` 与 `shapely` 只用于 3 个流域多边形掩膜，缺失时 `build_region_masks()`
会跳过流域、只保留 8 个经纬框区域，不报错）。脚本用 `Path(__file__).resolve().parents`
自下向上定位仓库根（同时含 `src/` 与 `Doc/`），无需修改路径。

可选参数（都在 `Fig7.py` 上）：

| 参数 | 作用 |
| --- | --- |
| `--selftest` | 只跑自检 T1–T6，不做稳健性计算、不出图（失败时退出码 1） |
| `--force-regrid` | 忽略重网格缓存，现场重算并落盘到 `data/cache/` |
| `--scenarios ssp245 …` | 只跑指定情景，默认三个都跑 |

路径常量都写在 `Fig7.py` 顶部：`THIS_DIR = Path(__file__).resolve().parent`、
`STUDY_ROOT = THIS_DIR`（脚本与 `data/` 同级）、`FIG_DIR = STUDY_ROOT`、
`CACHE_DIR = data/cache`；`REPO_ROOT` 取 `THIS_DIR.parents` 中同时含 `src/` 与 `Doc/`
的那一级（即论文文件夹），`Output/`、`Data/` 由它派生。

## 数据来源

本模块 `data/` 下的文件全部由 `Fig7.py` 写出：

| 文件 | 来源 / 生成脚本 | 说明 |
| --- | --- | --- |
| `data/robustness_ssp126.nc` | `Fig7.py` | SSP1-2.6：25 个算例 × 逐格点诊断场，维度 `(case, lat, lon)`，变量 `r`、`p_value`、`reduction`、`bias`、`prior_mean`、`prior_std`、`posterior_mean`、`posterior_std`、`n_models`（float32，zlib 压缩，约 11 MB） |
| `data/robustness_ssp245.nc` | 同上 | SSP2-4.5，结构与变量相同 |
| `data/robustness_ssp585.nc` | 同上 | SSP5-8.5，结构与变量相同 |
| `data/case_region_stats.csv` | 同上 | 825 行；逐（情景, 算例, 区域）统计量，列为 `Scenario, scenario, Case, Group, Label, n_models, Excluded, Region, r_mean, reduction_mean, bias_mean, sig_frac, sig_frac_unw, n_valid`；统计域为"区域掩膜 ∩ 有效格点（$p<0.05$ 且 $r\ge0.5$）"，与 Fig.6 面板 Mean 同口径 |
| `data/map_similarity.csv` | 同上 | 75 行；逐（情景, 算例）空间型相似度：`pattern_corr_r`、`pattern_corr_reduction`、`rmsd_r`、`max_abs_dev_r`、`rmsd_reduction`、`max_abs_dev_reduction`、`sig_change_frac` / `sig_lost_frac` / `sig_gained_frac`、`reduction_class_change_frac`、`bias_sign_change_frac`、`r_dev_gt005_frac` / `r_dev_gt01_frac` / `r_dev_gt02_frac`、`reduction_dev_gt2pp_frac` / `reduction_dev_gt5pp_frac` / `reduction_dev_gt10pp_frac`、`china_r_mean`、`china_reduction_mean`、`delta_china_r_mean`、`delta_china_reduction_mean` |
| `data/spread_vs_baseline.csv` | 同上 | 132 行；逐（情景, 区域, 指标）参照值与 24 个剔除算例的极值区间，列为 `Scenario, Region, Metric, baseline, excl_min, excl_max, excl_mean, excl_std, max_abs_dev, range, rel_change_pct, case_at_min, case_at_max`；指标为 `r_mean` / `reduction_mean` / `bias_mean` / `sig_frac` |
| `data/run_meta.csv` | 同上 | 10 行；运行元信息（`n_models_full=19`、`n_cases=25`、`sig_rule=p < 0.05 and r >= 0.5`、`reduction_bounds=0,0.1,0.2,0.4,0.6,0.7`、`obs_uncertainty=standard_error`、历史期 1981–2010、未来期 2021–2050）与三个情景的基线自检最大偏差 |
| `data/cache/`（**可选**，自动生成，当前不存在） | `Fig7.load_model_fields()` | 逐模式重网格缓存 `regrid_<scenario>_<mode>.nc`（变量 `X_regrid`、`Y_regrid`）；仅当本目录缓存与下述归档缓存都缺失时才走现场重网格 |

上游输入全部是只读的仓库既有文件，不由本模块生成：

| 文件 | 来源 / 生成脚本 | 说明 |
| --- | --- | --- |
| `Output/Mode/indices/Scenariomerged/MULTI_MODEL-<scenario>-ALL_INDICES.nc` | 仓库既有（`src/pipeline/5模式数据合并.py` 产出） | 19 个模式的逐情景指标场；取 `PrecipVar`（1981–2010）与 `R95mm_intensity`（2021–2050）两个指标 |
| `Output/Obs/indices/CN05-OBS-IntensityAndPrecipVar-1961-2023.nc` | 仓库既有（`src/pipeline/2计算观测数据指标.py` 产出） | 观测层产品之一，同时提供 0.25°（$163\times283$）目标网格 |
| `Output/Obs/indices/CPC-OBS-IntensityAndPrecipVar-1979-2025.nc` | 同上 | 观测层产品之一（只用于均值与产品间离散度） |
| `Output/Obs/indices/CHM_PRE_V2-OBS-IntensityAndPrecipVar-1961-2024.nc` | 同上 | 观测层产品之一 |
| `Output/Obs/indices/HGCDC-OBS-IntensityAndPrecipVar-1961-2022.nc` | 同上 | 观测层产品之一 |
| `Output/EC/China/HEC_<scenario>_PrecipVar_to_R95mm_intensity.nc` | 仓库既有（`src/pipeline/6中国区域分层涌现约束.py` 产出） | 全集合 19 模式的 HEC 存档基线，作为 `ALL` 算例的逐位比对基准（自检 T1/T2/T5） |
| `Data/River/{HuanghaiRiver,PearlRiver,YangtzeRiver}_polygon.shp` | 仓库既有 | 3 个流域多边形掩膜（`build_region_masks()` 用 `pyshp + shapely` 合并、`contains_xy` 点在多边形内判定） |
| `废弃/code/完美模式检验/data/cache/lomo_regrid_<scenario>_<mode>.nc` | 已归档的 `完美模式检验` 目录（仓库根 `废弃/code/` 下，共 57 个文件） | 优先复用的逐模式重网格缓存；与本脚本的重网格结果已核对一致 |

## 产出

| 文件 | 内容 |
| --- | --- |
| `Fig7.jpg` | 论文成品图（龙卷风图，`dpi=400`）：23 行 × 3 面板——(a) $\Delta$ 全国平均相关系数、(b) $\Delta$ 全国平均不确定性缩减率（%）、(c) $r$ 场 RMSD（%）；圆点颜色区分三个 SSP 情景，黄色底纹标出 LOFO 行。与投稿用图 `Doc/Tex/figures/Fig7.jpg` 逐字节相同 |
| `data/robustness_<scenario>.nc`（3 个） | 25 算例 × 逐格点诊断场（变量与维度见上表） |
| `data/case_region_stats.csv` | 逐（情景, 算例, 区域）统计量（825 行） |
| `data/map_similarity.csv` | 逐（情景, 算例）空间型相似度（75 行） |
| `data/spread_vs_baseline.csv` | 逐（情景, 区域, 指标）剔除敏感性（132 行） |
| `data/run_meta.csv` | 运行元信息与三个情景的自检最大偏差（10 行） |
| `data/cache/regrid_<scenario>_<mode>.nc` | 可选的重网格缓存（自动生成） |

## 代码说明

全模块只有一个脚本 `Fig7.py`，按下面的顺序组织（也是 `main()` 的执行顺序）：

| 段 | 内容 | 主要产出 |
| --- | --- | --- |
| 常量与路径 | 情景/模式清单、模式家族分组、指标名与时段、判据（`SIG_P_MAX` / `SIG_R_MIN`）、`THIS_DIR` / `STUDY_ROOT` / `DATA_DIR` / `FIG_DIR` / `CACHE_DIR` | 无 |
| 重网格与装载 | `build_overlap_weights()`、`regrid_conservative()`、`target_grid()`、`load_observation_layer()`、`load_model_fields()`（面积加权一阶守恒，与 `pipeline/6` 逐行一致） | `data/cache/regrid_<scenario>_<mode>.nc`（可选） |
| HEC 子集解算 | `hec_subset()` 向量化复现 pipeline/6 的 (1)–(5) 式；`build_region_masks()` / `area_weights()` / `weighted_mean()`；`build_cases()` 算例表 | 无 |
| 主计算 `run_robustness_check()` | 25 算例 × 3 情景逐格点重算，与 `ALL` 参照场比较，汇总区域统计与空间型相似度 | `robustness_ssp*.nc`、`case_region_stats.csv`、`map_similarity.csv`、`spread_vs_baseline.csv`、`run_meta.csv` |
| 出图 `make_figures()` → `figure_r3()` | 三面板龙卷风图（纵轴先单模式、后家族，两组内部各按 $\Delta r$ 升序） | `Fig7.jpg` |
| 自检 `run_selftest()` | T1–T6；由 `--selftest` 触发，**默认不跑**；全部 PASS 才可解释结果（失败时退出码 1） | 无文件产出 |

两点实现说明：

* `Fig7.py` 中的 `USE_OBS_STANDARD_ERROR` **必须保持 `True`**，才与 `pipeline/6`
  的存档结果一致（观测不确定性取四套产品间标准差 $/\sqrt{N}$，即均值标准误）。
* 该文件里另有当前未被使用的 `SHP_PATH`（`Data/China/cnmap.shp`）与历史遗留常量 `DOC_DIR`
  （现指向 `data/`）；顶部 `import` 的 `cartopy / shapefile / shapely`
  在当前出图路径中也没有被调用，真正用到的是 CSV + matplotlib。

## 算例设计

| 组别 | 算例数 | 集合大小 | 说明 |
| --- | --- | --- | --- |
| Baseline | 1 | 19 | 全集合参照，与 `Output/EC/China` 存档逐位一致 |
| LOMO | 19 | 18 | 逐个剔除 1 个模式 |
| LOFO | 4 | 15–17 | 逐个剔除 1 个模式家族：`G1_ACCESS`(2)、`G2_CESM`(4)、`G3_INM`(2)、`G4_ECHAM6`(2) |
| 分组敏感性 | 1 | 16 | `G2b_CESM_core`＝CESM2 + NorESM2-LM + NorESM2-MM（把有争议的 `TaiESM1` 摘出） |

## 方法说明

以下内容由 `doc/` 下三份说明（`模式稳健性检查_方法说明.md`、`图件说明.md`、
`正文插入段落_3.1模式稳健性.md`）合并而成；`doc/` 目录删除后，本 README 是唯一副本。
4.1–4.6 的数字与表格为 2026-09-22 版口径，脚本重跑后的当前数值见 4.7。

### 1. 为什么必须做这一项

图 6 的涌现关系是用 19 个 CMIP6 模式（HiCPC 降尺度产品）拟合出来的。多模式集合是
「机会集合」（ensemble of opportunity），模式之间既非独立、也非按不确定性系统抽样：
同一机构会有两代模式（本研究中的 `INM-CM4-8` 与 `INM-CM5-0`），不同机构的模式会共用
公共分量或代码谱系（`NorESM2-*`、`TaiESM1` 与 `CESM2` 同出 CESM 谱系；
`MPI-ESM1-2-HR` 与 `AWI-CM-1-1-MR` 共用 ECHAM6 大气分量）。Sansom 等（2018）指出，
这种聚类会在回归中产生杠杆效应：

> "Similar models are likely to give similar outputs, leading to clustering that could
> result in biased inferences if not properly accounted for. This is especially important
> when analyzing emergent constraints since a large cluster of outlying models could
> strongly influence any regression relationship."

因此"图 6 的结论是否只是被某一个模式或某一簇近亲模式撑起来的"是一个必须先回答的问题。
本检查的做法是把整条诊断链重算 24 遍，每次剔掉一个模式或一个模式家族，
看 $r$ 与不确定性缩减率怎么变。

### 2. 复现口径与自检

#### 2.1 与 pipeline/6 的逐位一致性

子集解算器 `Fig7.hec_subset()` 是
`src/pipeline/6中国区域分层涌现约束.py` 中式 (1)–(5) 的向量化重写，
逐项对应关系如下：

| 本目录 | pipeline/6 | 论文式 |
| --- | --- | --- |
| `xb`, `yb` | `x_mean`, `y_mean` | $\bar x$, $\bar y$ |
| `sx`, `sy`（ddof = 1） | `sigma_x`, `std_y` | $\sigma_x$, $\sigma_y$ |
| `r`, `p_value`（$t$ 检验，df $=n-2$） | `linregress` 的 `rvalue`/`pvalue` | $\rho$ |
| `prior_mean`, `prior_std` | `prior_mean`, `prior_std` | $\bar y$, $\sigma_y$ |
| `posterior_mean` | `posterior_mean` | 式 (3) $y_c$ |
| `posterior_std` | `posterior_std` | 式 (4) $\sigma_{y_c}$ |
| `reduction` $=1-\sigma_{y_c}/\sigma_y$ | `reduction` | 不确定性缩减率 |
| `bias` $=y_c-\bar y$ | `posterior_mean − prior_mean` | 偏差场 |
| 观测层 $\sigma_o$ | `obs_sigma_effective` | 式 (5) 的 $\sigma_o$ |
| `valid_core` $=(n\ge3)\wedge(r\text{ 有限})\wedge(\sigma_x^2>0)\wedge(\sigma_y^2>0)$ | 同 | — |

集合大小 $n$ 在剔除之后重新统计，均值/标准差/相关系数全部按子集重算，
面积加权重网格沿用 pipeline/6 的一阶守恒格式（源场 → CN05 $0.25^\circ$ 网格，
$163\times283$）。

#### 2.2 自检（`Fig7.py --selftest`，全部 PASS）

| 编号 | 检查内容 | 结果 |
| --- | --- | --- |
| T1 | 全集合解算 vs `Output/EC/China/{ssp126,ssp245,ssp585}` 存档的 `r`/`p_value`/`reduction`/`prior_mean`/`prior_std`/`posterior_mean`/`posterior_std` | 最大偏差 $1.8\times10^{-5}$（float32 量化精度） |
| T2 | 有效格点掩膜逐格点一致 | 三个情景全部一致 |
| T3 | 随机合成场上向量化 $r$、$p$ vs `scipy.stats.linregress` | 最大偏差 $4.4\times10^{-16}$ |
| T4 | 25 个算例的集合大小（19 / 18 / 15–17 / 16） | 全部符合预期 |
| T5 | 面积加权平均 $r$、缩减率 vs 存档 | 完全一致（如 SSP2-4.5：0.843191 vs 0.843191） |
| T6 | 解析关系 $\text{reduction}=1-\sqrt{1-r^2/(1+\mathrm{SNR}^{-1})}$ | 最大偏差 $2.2\times10^{-16}$ |

结论：本目录使用的子集解算器可以逐位复现图 6b、图 7b 的缩减率，
因此"剔除之后的场"与"未剔除的场"是同一套算法下的可比结果。

> 注：断言项数随算例数与情景数而定。归档文档记为 66 项；按当前代码路径逐项统计为
> 59 项（T1/T2 24 + T3 2 + T4 26 + T5 6 + T6 1）。当前 `data/run_meta.csv` 记录的
> 基线自检最大偏差为 `r` = 7.33e-07 / 5.91e-07 / 5.62e-07（ssp126 / ssp245 / ssp585），
> 与归档时的 $1.8\times10^{-5}$ 同量级（float32 量化精度）。

### 3. 算例设计

| 组别 | 算例 | 集合大小 | 含义 |
| --- | --- | --- | --- |
| Baseline | `ALL` | 19 | 全模式集合，即正文图 6 的参照 |
| LOMO（leave-one-model-out） | `LOMO_<mode>` × 19 | 18 | 逐个剔除 1 个模式 |
| LOFO（leave-one-family-out） | `LOFO_G1_ACCESS` | 17 | 剔除 `ACCESS-CM2`、`ACCESS-ESM1-5`（澳大利亚 ACCESS 社区模式） |
| | `LOFO_G2_CESM` | 15 | 剔除 `CESM2`、`NorESM2-LM`、`NorESM2-MM`、`TaiESM1`（CESM 谱系） |
| | `LOFO_G3_INM` | 17 | 剔除 `INM-CM4-8`、`INM-CM5-0`（俄罗斯 INM 两代） |
| | `LOFO_G4_ECHAM6` | 17 | 剔除 `MPI-ESM1-2-HR`、`AWI-CM-1-1-MR`（共用 ECHAM6 大气分量） |
| 分组敏感性 | `LOFO_G2b_CESM_core` | 16 | CESM2 + NorESM2-LM + NorESM2-MM；把谱系归属有争议的 `TaiESM1` 摘出 |

分组依据为模式命名、机构与已知共用分量，属保守分组（宁可少合并）。
其余 10 个模式（`CNRM-CM6-1`、`CanESM5`、`EC-Earth3-Veg`、`FGOALS-g3`、`IITM-ESM`、
`KACE-1-0-G`、`KIOST-ESM`、`MRI-ESM2-0`、`NESM3`）在本集合中无同源伙伴，各自成组，
其 LOFO 等价于 LOMO，不重复计算。

区域体系为 11 个：`China`（CN05 全域矩形）+ 7 个经纬框分区（`NorthChina`、`Northeast`、
`Northwest`、`Southwest`、`EastChina`、`SouthChina`、`CentralChina`）+ 3 个流域
（`YellowRiver`、`PearlRiver`、`YangtzeRiver`）。

### 4. 结果

#### 4.1 全国尺度的核心数字

面积加权（$\cos\varphi$）全国平均，参照值为 `ALL`，区间为 24 个剔除算例的极值。

| 情景 | 指标 | 参照（19 模式） | 剔除区间 | 最大绝对变幅 | 最大相对变幅 |
| --- | --- | --- | --- | --- | --- |
| SSP1-2.6 | 相关系数 $r$ | 0.8405 | 0.8203 – 0.8493 | 0.0201 | 2.39% |
| | 不确定性缩减率 | 18.90% | 16.80% – 19.95% | 2.10 pp | 11.10% |
| | 后验 $-$ 先验（mm/day） | 2.458 | 2.230 – 2.580 | 0.228 | 9.28% |
| | 显著格点比例 | 98.46% | 97.10% – 98.67% | 1.36 pp | 1.38% |
| SSP2-4.5 | 相关系数 $r$ | 0.8432 | 0.8243 – 0.8506 | 0.0189 | 2.25% |
| | 不确定性缩减率 | 19.02% | 16.92% – 20.06% | 2.09 pp | 11.01% |
| | 后验 $-$ 先验（mm/day） | 2.500 | 2.272 – 2.662 | 0.228 | 9.11% |
| | 显著格点比例 | 98.69% | 97.64% – 98.79% | 1.04 pp | 1.06% |
| SSP5-8.5 | 相关系数 $r$ | 0.8425 | 0.8241 – 0.8499 | 0.0184 | 2.19% |
| | 不确定性缩减率 | 19.55% | 17.61% – 20.36% | 1.94 pp | 9.93% |
| | 后验 $-$ 先验（mm/day） | 2.537 | 2.323 – 2.658 | 0.214 | 8.44% |
| | 显著格点比例 | 98.59% | 97.61% – 98.77% | 0.98 pp | 1.00% |

读法：全国平均 $r$ 的变幅不超过 0.021（2.4%），缩减率的变幅不超过 2.1 个百分点；
显著格点比例始终不低于 97.1%，与参照的 98.5%–98.7% 只差 1–2 个百分点。
三个情景的表现几乎相同。

#### 4.2 空间型是否被改变

以 24 个剔除算例各自与 `ALL` 参照场做逐格点比较（有效格点全域，共 35 551 点）：

| 指标 | SSP1-2.6 | SSP2-4.5 | SSP5-8.5 |
| --- | --- | --- | --- |
| $r$ 场型相关系数（最小 / 中位 / 最大） | 0.913 / 0.984 / 0.994 | 0.918 / 0.983 / 0.992 | 0.907 / 0.985 / 0.992 |
| 缩减率场型相关系数 | 0.957 / 0.995 / 0.998 | 0.958 / 0.995 / 0.998 | 0.961 / 0.996 / 0.998 |
| $r$ 场 RMSD（中位 / 最大） | 0.020 / 0.056 | 0.020 / 0.053 | 0.019 / 0.050 |
| 显著性"变类"格点比例（中位 / 最大） | 0.50% / 1.91% | 0.48% / 1.45% | 0.39% / 1.40% |
| $\lvert\Delta r\rvert>0.10$ 的面积比例（中位 / 最大） | 0.54% / 7.06% | 0.47% / 6.06% | 0.45% / 5.85% |
| $\lvert\Delta\text{缩减率}\rvert>5$ pp 的面积比例（中位 / 最大） | 0.79% / 18.42% | 0.82% / 18.43% | 0.85% / 17.27% |
| 偏差场符号翻转的面积比例（中位 / 最大） | 0.24% / 0.68% | 0.27% / 0.67% | 0.24% / 0.55% |

读法：$r$ 场与缩减率场的空间型在 24 个剔除试验中几乎完全保持
（型相关系数最低 0.907 / 0.957）。逐格点的不稳定是局部的：
即使在最极端的算例中，$\lvert\Delta r\rvert>0.10$ 的格点也只占 6%–7%，
$\lvert\Delta\text{缩减率}\rvert>5$ pp 的格点占 17%–18%（中位仅 0.8%）。

#### 4.3 谁最有影响：单个模式

按全国平均 $r$ 的偏移排序（SSP2-4.5，负号表示剔掉该模式后 $r$ 下降）：

| 剔除的模式 | $\Delta$ 全国平均 $r$ | $\Delta$ 全国平均缩减率 | $r$ 场 RMSD | 型相关系数 |
| --- | --- | --- | --- | --- |
| CanESM5 | −0.0189 | −0.0209 | 0.0527 | 0.9183 |
| FGOALS-g3 | −0.0165 | −0.0166 | 0.0377 | 0.9550 |
| KIOST-ESM | −0.0016 | −0.0011 | 0.0255 | 0.9746 |
| ACCESS-CM2 | −0.0015 | −0.0001 | 0.0171 | 0.9880 |
| …（中间 15 个模式） | $\lvert\Delta r\rvert\le0.005$ | $\lvert\Delta\text{缩减率}\rvert\le0.006$ | ≤ 0.022 | ≥ 0.980 |
| AWI-CM-1-1-MR | +0.0049 | +0.0052 | 0.0155 | 0.9904 |

`CanESM5` 是唯一的强杠杆模式：单剔它会把全国平均 $r$ 从 0.843 拉到 0.824、
把全国平均缩减率从 19.0% 拉到 16.9%。除它之外，其余 18 个模式的 $\lvert\Delta r\rvert$
均不超过 0.017，其中 17 个不超过 0.005。`FGOALS-g3` 是第二敏感的（$\Delta r=-0.017$），
但仍显著小于 `CanESM5`。

三个情景下的排序一致（`CanESM5` 在 SSP1-2.6 与 SSP2-4.5 都是极值，
SSP5-8.5 下与家族 `G2_CESM` 相当）。

> 当前数据（`data/map_similarity.csv`，SSP2-4.5）已把 `FGOALS-g3` 抬到与 `CanESM5`
> 同量级：`CanESM5` −0.0141、`FGOALS-g3` −0.0139、`AWI-CM-1-1-MR` +0.0045，
> 其余 16 个模式 $\lvert\Delta r\rvert\le0.0034$，详见 4.7。

#### 4.4 谁最有影响：模式家族

| 家族 | 成员数 | $\Delta$ 全国平均 $r$（三个情景） | $\Delta$ 全国平均缩减率（三个情景） | $r$ 场型相关（最低） |
| --- | --- | --- | --- | --- |
| `G1_ACCESS` | 2 | −0.0033 / −0.0026 / −0.0016 | −0.0006 / −0.0004 / +0.0012 | 0.971 |
| `G2_CESM` | 4 | +0.0060 / +0.0059 / +0.0060 | +0.0105 / +0.0105 / +0.0048 | 0.907 |
| `G3_INM` | 2 | +0.0042 / +0.0060 / +0.0046 | +0.0056 / +0.0064 / +0.0065 | 0.965 |
| `G4_ECHAM6` | 2 | +0.0088 / +0.0074 / +0.0074 | +0.0087 / +0.0083 / +0.0081 | 0.971 |
| `G2b_CESM_core`（敏感性） | 3 | +0.0054 / +0.0043 / +0.0053 | +0.0084 / +0.0078 / +0.0028 | 0.926 |

读法：最大的同源家族（CESM 谱系 4 个模式，剔除后集合只剩 15 个）是影响最大的家族，
但即使整族剔除，全国平均 $r$ 只变化 $+0.006$、缩减率只变化 $+0.011$。
把归属有争议的 `TaiESM1` 从该家族摘出（`G2b`）后结论不变
（$\Delta r=+0.004$ 至 $+0.005$），说明分组方式不影响结论。

#### 4.5 区域尺度的稳健性

11 个区域（全国 + 7 个地理分区 + 3 个流域）的参照值与 24 个剔除算例的极值区间见
`data/spread_vs_baseline.csv`（归档文档中的绘图脚本"图 R4"未实现，当前只出龙卷风图）。要点：

* 南高北低的区域格局完全不变。把 11 个区域按"南方组"（华南、珠江、西南、长江）
  与"北方组"（东北、华北、西北、黄河）划分，在 3 个情景 × 25 个算例 = 75 次比较中，
  南方组的最小值始终高于北方组的最大值，余量最小 0.0025（缩减率，SSP2-4.5）、
  最大 0.047（$r$，SSP1-2.6），无一例外。
* 逐区域排名高度保持但非完全不变。以基线区域排序为参照，24 个剔除算例的
  Spearman 秩相关最低 0.936（缩减率，SSP2-4.5）、最高 1.000；
  排名完全一致的算例占 4/24–13/24。也就是说，个别相邻区域（如华南与珠江、
  华东与西北）会互换位置，但量级相近，不影响任何结论。
* 变幅最大的区域是东北，最小的是华南 / 珠江。以 $r$ 的极差为例：
  东北 0.048–0.061、华北 ~0.033、长江 0.024–0.031、珠江 0.031–0.038、
  华南 ~0.033、西北 ~0.030；缩减率的极差以东北最大（5.1–5.4 个百分点）。
  这与"约束效率越高的区域越稳定"一致。
* 最低值仍显著。所有区域在全部 24 个剔除试验中的面积加权平均 $r$ 都 $\ge 0.740$
  （最低为 SSP5-8.5 的华北 0.7396），缩减率都 $\ge 11.6\%$
  （最低为 SSP1-2.6 的东北 0.1158）。

#### 4.6 分组敏感性小结

`G2b_CESM_core` 与 `G2_CESM` 的差别只在 `TaiESM1` 一个成员，两者的结论同向同量级，
说明家族边界怎么划不会改变"结论不由任何单一模式家族主导"这一判断。

#### 4.7 当前 `data/` 的重算值（对照 4.1 / 4.3 / 4.4）

4.1–4.6 是 2026-09-22 版《方法说明》记录的数字；观测层口径固定为 SEM 并重跑之后，
`data/` 中的当前数值如下（本次核对 `data/spread_vs_baseline.csv`、`data/map_similarity.csv`、
`data/case_region_stats.csv`）：

| 情景 | 指标 | 参照（19 模式） | 剔除区间（24 算例） | 最大绝对变幅 | 最大相对变幅 |
| --- | --- | --- | --- | --- | --- |
| SSP1-2.6 | 相关系数 $r$ | 0.8472 | 0.8332 – 0.8557 | 0.0140 | 1.66% |
| | 不确定性缩减率 | 19.15% | 17.23% – 20.31% | 1.92 pp | 10.01% |
| | 后验 $-$ 先验（mm/day） | 2.486 | 2.279 – 2.620 | 0.207 | 8.33% |
| | 显著格点比例 | 98.46% | 97.10% – 98.67% | 1.36 pp | 1.38% |
| SSP2-4.5 | 相关系数 $r$ | 0.8492 | 0.8351 – 0.8569 | 0.0141 | 1.66% |
| | 不确定性缩减率 | 19.24% | 17.28% – 20.36% | 1.95 pp | 10.15% |
| | 后验 $-$ 先验（mm/day） | 2.523 | 2.310 – 2.693 | 0.213 | 8.44% |
| | 显著格点比例 | 98.69% | 97.64% – 98.79% | 1.04 pp | 1.06% |
| SSP5-8.5 | 相关系数 $r$ | 0.8488 | 0.8344 – 0.8563 | 0.0144 | 1.69% |
| | 不确定性缩减率 | 19.79% | 17.98% – 20.60% | 1.81 pp | 9.14% |
| | 后验 $-$ 先验（mm/day） | 2.560 | 2.359 – 2.681 | 0.201 | 7.85% |
| | 显著格点比例 | 98.59% | 97.61% – 98.77% | 0.98 pp | 1.00% |

单模式（SSP2-4.5，`data/map_similarity.csv`）：

| 剔除的模式 | $\Delta$ 全国平均 $r$ | $\Delta$ 全国平均缩减率 | $r$ 场 RMSD | 型相关系数 |
| --- | --- | --- | --- | --- |
| CanESM5 | −0.0141 | −0.0195 | 0.0527 | 0.9183 |
| FGOALS-g3 | −0.0139 | −0.0158 | 0.0377 | 0.9550 |
| AWI-CM-1-1-MR | +0.0045 | +0.0051 | 0.0155 | 0.9904 |
| 其余 16 个模式 | $\lvert\Delta r\rvert\le0.0034$ | $\lvert\Delta\text{缩减率}\rvert\le0.0044$ | ≤ 0.0255 | ≥ 0.9746 |

模式家族（SSP2-4.5）：

| 家族 | $\Delta$ 全国平均 $r$ | $\Delta$ 全国平均缩减率 | $r$ 场型相关 |
| --- | --- | --- | --- |
| `G1_ACCESS` | −0.0004 | +0.0004 | 0.9717 |
| `G2_CESM` | +0.0077 | +0.0112 | 0.9390 |
| `G3_INM` | +0.0059 | +0.0063 | 0.9649 |
| `G4_ECHAM6` | +0.0073 | +0.0083 | 0.9764 |
| `G2b_CESM_core`（敏感性） | +0.0049 | +0.0080 | 0.9616 |

空间型（24 个剔除算例，`data/map_similarity.csv`）：$r$ 场型相关系数最低 0.9133 /
0.9183 / 0.9074，缩减率场最低 0.9572 / 0.9584 / 0.9614（SSP1-2.6 / SSP2-4.5 / SSP5-8.5）；
$r$ 场 RMSD 中位 0.020、最大 0.056；显著性"变类"比例中位 ≤ 0.5%、最大 1.91%；
$\lvert\Delta r\rvert>0.10$ 的面积比例中位 ≤ 0.6%、最大 7.06%；
$\lvert\Delta\text{缩减率}\rvert>5$ pp 的面积比例中位 ≤ 0.9%、最大 18.43%；
偏差场符号翻转比例始终 < 0.7%。这些数字与 4.2 的归档值一致。

区域尺度（24 个剔除算例，`data/case_region_stats.csv`）：南方组最小值仍始终高于北方组
最大值（3 情景 × 25 算例 = 75 次比较无一例外），余量最小为缩减率 0.00025（≈0.03 个
百分点，SSP2-4.5，剔除 `FGOALS-g3`）、$r$ 为 0.0167（SSP2-4.5，剔除 `G2_CESM`）；
各区域最低值：$r$ 0.7679、缩减率 12.23%（都出现在东北）；变幅最大的区域是东北
（$r$ 极差 0.0669），缩减率极差最大的是西南（5.95 个百分点，东北 5.86 个百分点次之）。

### 5. 结论与正文建议写法

1. 可以写"稳健"：剔除任意单个模式或任意一个模式家族后，图 6 的相关系数空间型
   （型相关 ≥ 0.907）、不确定性缩减率空间型（型相关 ≥ 0.957）、区域排序与显著性范围
   （≥ 97.1%）都不改变；全国面积加权平均 $r$ 的变幅 ≤ 2.4%，缩减率的变幅 ≤ 2.1 个百分点。
2. 必须写出的保留意见：`CanESM5` 是唯一的强杠杆模式。建议在正文中显式给出
   "含 / 不含 `CanESM5`" 的两组数字，而不是笼统地说"不受任何单个模式影响"。
   这也正面印证了 Sansom 等（2018）关于杠杆效应的提醒。
   （当前数据下 `FGOALS-g3` 与 `CanESM5` 同量级，正文 §3.1 已按此改写为两者并列，
   并给出含 / 不含 `CanESM5` 的缩减率 19.2% 与 17.3%。）
3. 与完美模式检验的分工：本检查回答"结论是否被某个模式主导"；
   `完美模式检验` 回答"约束后的预估是否更准"。两者不可互相替代，
   正文中宜分别成段。

### 6. 数据与代码索引

| 文件 | 内容 |
| --- | --- |
| `Fig7.py` | 唯一脚本：路径、模式清单、家族分组、区域掩膜、重网格、`hec_subset()`；25 算例 × 3 情景逐格点重算（输出 nc 与 4 个 CSV）；龙卷风图（正文 Fig.7）；自检 T1–T6（`--selftest`） |
| `data/robustness_ssp*.nc` | 变量：`r`、`p_value`、`reduction`、`bias`、`prior_mean`、`prior_std`、`posterior_mean`、`posterior_std`、`n_models`；维度 `(case, lat, lon)` |
| `data/case_region_stats.csv` | `Scenario, scenario, Case, Group, Label, n_models, Excluded, Region, r_mean, reduction_mean, bias_mean, sig_frac, sig_frac_unw, n_valid` |
| `data/map_similarity.csv` | 型相关、RMSD、最大偏离、变类比例、阈值偏离比例 |
| `data/spread_vs_baseline.csv` | 逐区域、逐指标的参照值与剔除区间 |
| `data/run_meta.csv` | 算例数、判据、三个情景的自检最大偏差 |

### 7. 图件说明（怎么读 `Fig7.jpg`）

一张图，由 `Fig7.py` 的 `figure_r3()`（经 `make_figures()` 调用）生成，依赖 `data/map_similarity.csv`
（由 `run_robustness_check()` 产出）。该图已被正文采用，投稿用图为
`Doc/Tex/figures/Fig7.jpg`（与本目录 `Fig7.jpg` 逐字节相同）。

三个面板共用一个纵轴，列出 **23 行**剔除试验：先 19 组单模式（LOMO）、后 4 组模式家族
（LOFO），两组内部各自按全国面积加权平均 $\Delta r$ 升序；括号内为剔除后的集合大小。
家族边界敏感性试验 `LOFO_G2b_CESM_core` 仍保留在分析输出（CSV）中，但自 2026-09-23 起
不再绘入本图，故图上为 23 行而非 24 行。黄色底纹为 leave-one-family-out 行，
圆点颜色区分三个 SSP 情景（图例为单行、无边框，位于三个子标题下方）。

| 面板 | 横轴 | 含义 |
| --- | --- | --- |
| 左 (a) | $\Delta$ 全国平均相关系数 | 剔除后 $r$ 相对全集合的偏移 |
| 中 (b) | $\Delta$ 全国平均不确定性缩减率（%） | 同上，改用缩减率；原始数据是小数，绘图时乘 100，横轴为 −2.5 ~ 2.5 |
| 右 (c) | $r$ 场的 RMSD（%） | 整幅空间场的均方根偏差；绘图时乘 100，横轴为 −6 ~ 6 |

怎么读：

* 只有前两行（`LOMO_CanESM5`、`LOMO_FGOALS-g3`）明显偏离零线；第三行开始
  三种情景的点几乎重叠在 0 附近。
* 黄色底纹行（家族试验）中 `G2_CESM` 的偏移最大，但仍只有 ±0.008 量级，远小于 `CanESM5`。

对应数据：`data/map_similarity.csv`。图件以 `savefig(..., dpi=400, bbox_inches="tight")`
保存（归档的《图件说明》记为 350 dpi，当前代码为 400 dpi）；若期刊要求 600 dpi，
改 `Fig7.py` 中 `figure_r3()` 里的 `dpi` 即可，版式不受影响。

### 8. 正文插入段落与图题

归档状态说明（历史记录）：本目录的正文段落已并入正文 §3.1，图件已在正文中被引用，
在当时的编号下称为"图 6"（原图 6–10 顺位为 7–11）。当前状态（本次核对）：
正文 `Doc/涌现约束_v2.md` §3.1 的第 165–177 行即该段落，图片以
`../src/Pic/Fig7_ModelRobustness/Fig7.jpg` 直接引用、编号为 **Fig.7**，
投稿用副本为 `Doc/Tex/figures/Fig7.jpg`；归档目录正文插入段落文件里的"图 9 / 图 6"
编号是当时排版阶段的残留，以正文为准。

归档文件中保留的图题原文（编号照录）：

> 图 9 24 组剔除试验对全国面积加权平均诊断量的影响。
> 左：全国平均相关系数相对全集合参照的变化 $\Delta r$；
> 中：全国平均不确定性缩减率的变化；
> 右：相关系数场相对参照场的均方根偏差（RMSD）。
> 纵轴为 24 组试验，按 $\Delta r$ 排序，黄色底纹标示 leave-one-family-out 与家族边界
> 敏感性试验；圆点颜色区分三个 SSP 情景。可见除 CanESM5 与 CESM 谱系外，
> 其余剔除试验对全国平均量的影响均小于 0.005。

正文当前使用的图题（`Doc/涌现约束_v2.md` §3.1）：

> Fig.7 排除单个模式或模式家族后分层涌现约束诊断的稳健性。纵轴为 23 组剔除试验
> （19 组逐个剔除单个模式、4 组逐个剔除模式家族；括号内为剔除后的集合大小），
> 先列单模式、后列模式家族，两组内部均按全国面积加权平均相关系数的变化 $\Delta r$ 排序
> （家族边界敏感性试验未绘入本图）；圆点颜色区分三个 SSP 情景（SSP1-2.6、SSP2-4.5、
> SSP5-8.5），黄色底纹标示 leave-one-family-out 试验。横轴分别为 (a) 全国平均相关系数的
> 变化 $\Delta r$、(b) 全国平均不确定性（$\sigma$）缩减率的变化（单位：%，即百分点），
> 以及 (c) 相关系数场相对全集合参照场的均方根偏差（RMSD，以 $r$ 单位的百分数表示，
> 即 3% 表示 RMSD = 0.03）。除 CanESM5（LOMO）与 CESM 谱系（LOFO）外，其余剔除试验对
> 全国平均量的影响均小于 0.005。

## 与其它工作的关系

* 与 `src/Pic/Fig6_EmergentConstraint/`（正文 Fig.6）：那是 HEC 约束结果本身；本目录把
  它背后的整条诊断链在逐格点上重算 25 遍，检验其是否被某个模式或家族主导。
* 与 `废弃/code/完美模式检验/`（原 `src/Pic/完美模式检验/`，2026-10-09 归档到仓库根的
  `废弃/code/` 下）：那是回答"约束后的预估是否更准"（后验 vs 先验的 RMSE 与覆盖率）。
  本目录回答的是另一个问题——"结论是否被某个模式主导"。两者互补，不要互相替代。
  该目录的 `data/cache/lomo_regrid_<scenario>_<mode>.nc`（57 个文件）被
  `Fig7.load_model_fields()` 直接复用为重网格缓存；缓存全部缺失时会自动回退为
  现场重网格并写入本目录 `data/cache/`，结果不受影响。
* 与 `废弃/code/完美模式检验/模式成员之间的联系.md`（原 `Doc/Markdown/模式成员之间的联系.md`）：
  该文档 §3.1 提出三种留出方案（含 LOFO）、§4 给出 19 个模式的亲缘分组、§8.1 已给出
  区域平均口径的家族检验；本目录把同一检验推到逐格点尺度并出图，
  补上了该文档 §5「实施计划」中"出图待做 / 逐格点待做"的部分。
* 与 `src/pipeline/6中国区域分层涌现约束.py`：本目录的子集解算器是该脚本
  公式 (1)–(5) 的向量化重写；`Fig7.py --selftest` 逐项核对，最大偏差为 float32 量化精度
  （归档方法说明记为 $10^{-5}$ 量级，当前 `data/run_meta.csv` 记录 $r$ 的 max$\lvert\Delta\rvert$
  为 5.6e-07–7.3e-07）。
* 与正文 `Doc/涌现约束_v2.md` §3.1：该节的 Fig.7 段落与图题即由本目录结果写成；
  投稿用图 `Doc/Tex/figures/Fig7.jpg` 与本目录 `Fig7.jpg` 逐字节相同。
