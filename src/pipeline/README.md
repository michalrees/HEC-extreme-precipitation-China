# 降水指标与中国区域分层涌现约束计算流程

本目录包含观测重网格、观测与模式指标计算、模式合并和逐格点分层涌现约束（HEC）六个脚本。默认使用历史期 `PrecipVar` 约束未来期 `R95mm_intensity`，输出 NetCDF。图件和区域统计由 `src/Pic/` 下的脚本另行处理。

## 1. 流程与路径约定

以下路径均相对于项目根目录（同时包含 `src/` 和 `Doc/`）。脚本根据自身位置定位根目录；运行命令示例假定终端位于项目根目录。

```text
Data/Obs/ 下的 CPC、CHM_PRE_V2、HGCDC 日降水
    └─ 1统一观测数据分辨率.py
         └─ Output/Obs/*_0.25-0.25.nc（三套产品）
另行准备的 Output/Obs/CN05.1_1961-2023_0.25-0.25.nc
    └─ 与上述三套产品一起进入 2计算观测数据指标.py
         └─ Output/Obs/indices/<source>-OBS-IntensityAndPrecipVar-<start>-<end>.nc

Data/Mode/<mode>/HiCPC_pr_<mode>_<scenario>.nc
    └─ 3计算模式数据强度和降水变率.py
       （4批量计算多个模式_强度和降水变率.py 串行调用脚本 3）
         └─ Output/Mode/indices/<mode>/<scenario>/
              <mode>-<scenario>-IntensityAndPrecipVar-<start>-<end>.nc
              └─ 5模式数据合并.py
                   └─ Output/Mode/indices/Scenariomerged/
                        MULTI_MODEL-<scenario>-ALL_INDICES.nc

观测指标 + 情景合并模式指标
    └─ 6中国区域分层涌现约束.py
         └─ Output/EC/China/HEC_<scenario>_PrecipVar_to_R95mm_intensity.nc
```

脚本 3 和脚本 4 是单模式运行与批量运行两种入口，无需重复执行。已有合格的观测指标和模式合并文件时，可以直接运行脚本 6。

## 2. 环境与输入要求

使用 Python 3.10 或更新版本，并准备以下依赖（代码未锁定版本）：

| 使用位置 | 第三方依赖 |
|---|---|
| 脚本 1 | `numpy`、`xarray`、`dask`、`scipy`，以及支持压缩写出的 NetCDF 后端 |
| 脚本 2、3 及其公共模块 | `numpy`、`xarray`、`pandas`、`scipy`、`tqdm`，以及 NetCDF 后端 |
| 脚本 4 | 自身仅使用标准库，子进程仍需要脚本 3 的依赖 |
| 脚本 5 | `xarray`，以及支持压缩写出的 NetCDF 后端 |
| 脚本 6 | `numpy`、`xarray`、`scipy`、`matplotlib`、`rioxarray`，以及 NetCDF 后端 |

NetCDF 后端可使用 `netCDF4`。脚本 6 虽然不绘图，仍在顶层导入 `matplotlib` 和 `rioxarray`，运行环境必须能够导入它们；环境名称本身没有硬性要求。脚本 4 和脚本 6 的批处理均沿用当前 Python 解释器。

输入应为已整理的逐日降水，使用一维经纬度坐标。脚本 2、3 不负责把降水通量换算成日降水量；脚本 1 仅将输出单位属性设为 `mm/day`，不做数值单位转换，须事先确认输入数值的单位。`PrecipVar` 模块按 `(time, lat, lon)` 数组处理，并通过 `pandas.to_datetime` 解析时间；非标准日历数据需要预先确认兼容性。

脚本 2、3 使用 `src/lib/ETCCDI.py` 和 `src/lib/precip_variability_netcdf.py`。脚本 6 在自身代码中完成重映射和 HEC 计算，没有调用 `hec_integrate.py` 或 `hec_grid_interpolate.py`。

## 3. 各阶段的实际行为

### 3.1 统一观测网格：脚本 1

目标网格取自 `Data/Obs/CN05.1_1961-2023.nc` 的经纬度坐标，保留其网格位置与间隔，并按升序输出。

| 原始文件（位于 `Data/Obs/`） | 方法 | 输出文件（位于 `Output/Obs/`） |
|---|---|---|
| `CPC_1979-2025.nc` | 双线性插值 | `CPC_1979-2025_0.25-0.25.nc` |
| `CHM_PRE_V2_daily_1960-2024.nc` | 球面网格重叠面积加权 | `CHM_PRE_V2_daily_1960-2024_0.25-0.25.nc` |
| `HGCDC_1961-2022.nc` | 球面网格重叠面积加权 | `HGCDC_1961-2022_0.25-0.25.nc` |

脚本选取源文件的第一个数据变量，规范经纬度、裁剪至目标坐标范围，按年重网格，输出变量名 `pr`，采用 float32 和压缩级别 4。

**CN05 衔接要求：**脚本 1 只读取 CN05 作为目标网格，不生成 `Output/Obs/CN05.1_1961-2023_0.25-0.25.nc`。脚本 2 默认要求该文件存在；从原始数据重建流程时，须另行准备符合要求的 CN05 文件，或核实原始 CN05 的变量、单位和网格后修改脚本 2 的 `INPUT_FILES["CN05"]`。代码中虽然定义了 `resolve_input_files()`，主入口没有调用它，不会自动回退到原始数据目录。

### 3.2 计算观测指标：脚本 2

`INPUT_FILES` 固定指向上述三套重网格文件及 CN05 文件，逐产品输出一个指标文件。

| 配置 | 默认值 |
|---|---|
| `BASELINE_YEARS` | 1981–2010，百分位阈值基准期 |
| `TARGET_YEARS` | 1961–2025，与每套数据实际可用年份取交集 |
| `SPLIT_YEAR` | 2015，PrecipVar 分段点 |
| `LAT_RANGE` / `LON_RANGE` | `None`，主入口从 CN05 输入文件推断范围 |
| 输出变量 | `R90mm_intensity`、`R95mm_intensity`、`R99mm_intensity`、`PrecipVar` |

指标通常为 `(year, lat, lon)`，输出文件名使用实际输出起止年份。缺失的观测产品会被批处理跳过，但默认配置下 CN05 在范围推断阶段就必须存在。单个强度指标失败时会打印警告并继续，因此生成文件不代表四个指标全部成功。

### 3.3 计算模式指标：脚本 3、4

脚本 3 处理一个模式的一个或多个情景，要求输入文件已经包含所需历史期与未来期数据；不自动下载或拼接 historical 与 SSP 原始文件。

| 配置 | 默认值 |
|---|---|
| `--mode` | `ACCESS-CM2` |
| `--scenarios` | `ssp126 ssp245 ssp585`，接受一个或多个值 |
| `BASELINE_YEARS` | 1981–2010 |
| `TARGET_YEARS` | 1979–2100，与可用年份取交集 |
| `SPLIT_YEAR` | 2015 |
| `LAT_RANGE` / `LON_RANGE` | 14–56°N / 69–141°E |
| 输出变量 | `R10mm_intensity`、`R20mm_intensity`、`R25mm_intensity`、`R50mm_intensity`、`R90mm_intensity`、`R95mm_intensity`、`R99mm_intensity`、`PrecipVar` |

脚本 4 按 `MODES` 列表串行调用脚本 3，每个模式计算三个情景。当前列出 19 个模式：

```text
ACCESS-CM2       ACCESS-ESM1-5    AWI-CM-1-1-MR
CanESM5          CESM2            CNRM-CM6-1
EC-Earth3-Veg    FGOALS-g3        IITM-ESM
INM-CM4-8        INM-CM5-0        KACE-1-0-G
KIOST-ESM        MPI-ESM1-2-HR    MRI-ESM2-0
NESM3           NorESM2-LM       NorESM2-MM
TaiESM1
```

脚本 3 在情景失败后继续处理其他情景，最后以退出码 1 报告失败；脚本 4 对失败模式采用相同策略。强度指标内部失败仍可能被跳过，需同时检查警告与输出变量。

### 3.4 指标定义

- `R10/20/25/50mm_intensity`：一年内达到固定日降水阈值的日降水平均强度，仅模式侧默认计算。
- `R90/95/99mm_intensity`：基准期湿日（降水 ≥ 1 mm/day）的第 90/95/99 百分位阈值以上日子的年平均降水强度。按代码使用严格大于阈值，并同时满足湿日条件；基准期湿日不足 10 天的格点阈值无效。名称中的 `R95mm` 在这里表示百分位指标，不是固定 95 mm 阈值。
- `PrecipVar`：使用自身的逐日序气候态去除年循环，再逐格点去除线性趋势，计算每年残差的日标准差（`numpy.nanstd`，默认 `ddof=0`）。输出是变率，不是方差或变率趋势。

### 3.5 按情景合并：脚本 5

递归扫描 `Output/Mode/indices/**/*.nc`，只接受以下命名格式，且情景必须属于 `ssp126`、`ssp245`、`ssp585`：

```text
<model>-<scenario>-IntensityAndPrecipVar-<start>-<end>.nc
```

为每个文件新增 `Mode` 维度，按情景拼接并按模式名排序，输出变量通常为 `(Mode, year, lat, lon)`。使用 `join="outer"` 对齐坐标，不做重网格；坐标缺口可能产生 NaN。已有 `MULTI_MODEL-…-ALL_INDICES.nc` 不匹配输入命名规则，会被跳过。

脚本不检查是否集齐 19 个模式，也不对同一模式的多个匹配文件去重。合并前须确认文件集合正确，避免重复模式或不完整集合覆盖已有结果。无输入或某个情景合并失败时仅打印信息/警告，不能仅凭退出码判断是否成功。

### 3.6 中国区域 HEC：脚本 6

默认参数：

| 参数 | 默认值 |
|---|---|
| 历史预测因子 `HIST_INDICATOR` | `PrecipVar` |
| 历史期 `HIST_PERIOD_RANGE` | 1981–2010 |
| 未来目标 `FUTURE_INDICATOR` | `R95mm_intensity` |
| 未来期 `FUTURE_PERIOD_RANGE` | 2021–2050 |
| 情景 | `ssp126`、`ssp245`、`ssp585` |

四套观测指标的文件名在 `OBS_PRODUCT_FILES` 中固定配置：

```text
CN05-OBS-IntensityAndPrecipVar-1961-2023.nc
CPC-OBS-IntensityAndPrecipVar-1979-2025.nc
CHM_PRE_V2-OBS-IntensityAndPrecipVar-1961-2024.nc
HGCDC-OBS-IntensityAndPrecipVar-1961-2022.nc
```

它们均位于 `Output/Obs/indices/`，缺少任意一套会报错。若上游输出年份改变，需要同步修改这里的路径。

计算步骤：

1. 从 CN05 指标文件读取目标网格。四套观测先计算历史期年平均，再计算产品均值、产品间样本标准差（`ddof=1`）和有效产品数 `N`。
2. 观测侧不再重网格；代码检查经纬度尺寸后重新赋予 CN05 坐标，因此输入坐标位置必须事先一致，不能只保证数组大小相同。
3. 各模式分别计算历史预测因子与未来目标的时段均值，再按网格重叠面积重映射到 CN05 网格。目标是未来强度本身，不是相对历史期的变化量。
4. 逐格点对模式集合计算相关系数 `r` 和回归斜率的双侧检验 `p_value`。有效核心要求至少 3 对模式样本、有限相关系数以及非零的模式方差。

记模式历史均值、标准差为 `mu_x`、`sigma_x`，未来均值、标准差为 `mu_y`、`sigma_y`，观测均值为 `mu_o`，则：

```text
SNR = sigma_x² / sigma_o²
posterior_mean = mu_y + r × (sigma_y / sigma_x)
                         × (mu_o - mu_x) × sigma_x² / (sigma_x² + sigma_o²)
posterior_std  = sigma_y × sqrt(1 - r² / (1 + 1/SNR))
reduction      = 1 - posterior_std / sigma_y
```

脚本在 CN05 网格覆盖范围内计算，不执行中国边界或流域矢量裁剪，不汇总区域统计，也不按 `p_value` 阈值筛选后验场。显著性掩膜和地图呈现由下游分析决定。

## 4. 运行方法

先激活包含上述依赖的 Python 环境。在项目根目录使用 PowerShell：

```powershell
# 观测处理：先完成 CN05 衔接要求
python "src/pipeline/1统一观测数据分辨率.py"
python "src/pipeline/2计算观测数据指标.py"

# 单模式示例（与下一条批处理命令按需选择）
python "src/pipeline/3计算模式数据强度和降水变率.py" --mode ACCESS-CM2 --scenarios ssp245

# 全部 19 个模式 × 3 个情景
python "src/pipeline/4批量计算多个模式_强度和降水变率.py"

# 确认逐模式文件齐备后合并
python "src/pipeline/5模式数据合并.py"

# 清除情景环境变量，依次计算三个情景的 HEC
Remove-Item Env:SCENARIO -ErrorAction SilentlyContinue
python "src/pipeline/6中国区域分层涌现约束.py"
```

仅运行一个 HEC 情景：

```powershell
$env:SCENARIO = "ssp245"
try {
    python "src/pipeline/6中国区域分层涌现约束.py"
} finally {
    Remove-Item Env:SCENARIO -ErrorAction SilentlyContinue
}
```

脚本 6 通过环境变量而非命令行参数选择情景。未设置时串行启动三个子进程，任意情景失败即中止；空字符串不等同于未设置，会触发不支持情景错误。脚本 6 的计算位于模块顶层，不应把它当作无副作用的库导入。

除脚本 3 的 `--mode`、`--scenarios` 和脚本 6 的 `SCENARIO` 外，路径、年份、指标和模式列表均在源码中配置。各脚本没有跳过已有输出的机制，重跑可能覆盖同名文件。脚本 2、3 会加载裁剪后的日数据，脚本 5 会加载待合并数据，运行前应预留相应内存。

## 5. HEC 输出字段

每个情景输出一个文件，直接平铺在 `Output/EC/China/`，所有数据变量为 `(lat, lon)`、float32。

| 变量 | 含义 |
|---|---|
| `r` | 模式集合历史预测因子与未来目标的相关系数 |
| `p_value` | 对应线性回归斜率的双侧检验 p 值 |
| `obs_sigma_raw` | 观测产品历史期均值之间的样本标准差；非正值置为 NaN |
| `obs_sigma_effective` | 观测误差项 |
| `prior_mean` / `prior_std` | 有效模式集合未来目标的均值 / 样本标准差 |
| `posterior_mean` / `posterior_std` | HEC 约束后的均值 / 标准差 |
| `reduction` | 标准差相对缩减比例；0.2 表示缩减 20%，文件内未乘 100 |
| `n` | 每个格点用于统计的有效模式对数量，不是观测产品数 `N` |

全局属性记录 `scenario`、`history_indicator`、`future_indicator`、`history_period`、`future_period` 和 `observational_error_term = "sigma_raw / sqrt(N)"`。文件不输出逐模式重网格场、观测均值或观测产品数。
