# 降水指标与分层涌现约束

[English](README.md) | [中文](README_zh.md)

以 1981–2010 年的 `PrecipVar` 约束 2021–2050 年的 `R95mm_intensity`，输出三个 SSP 情景的 HEC 结果。

## 环境与输入

使用 Python 3.10 或更新版本。依赖：numpy、pandas、xarray、netCDF4、scipy、dask、tqdm、matplotlib 和 rioxarray。

输入为采用一维经纬度坐标、单位为 mm/day 的逐日降水。所有路径相对于项目根目录。

| 输入 | 路径 |
|---|---|
| 原始观测 | `Data/Obs/`：CN05.1、CPC、CHM PRE V2、HGCDC |
| 模式降水 | `Data/Mode/<mode>/HiCPC_pr_<mode>_<scenario>.nc` |
| 观测年指标 | `Output/Obs/indices/` |
| 情景合并模式指标 | `Output/Mode/indices/Scenariomerged/MULTI_MODEL-<scenario>-ALL_INDICES.nc` |

CN05.1 为目标网格。运行观测指标计算前，需准备 `Output/Obs/Regridded/CN05.1_1961-2023_0.25-0.25.nc`。

## 脚本与输出

| 脚本 | 功能 | 输出目录 |
|---|---|---|
| `1统一观测数据分辨率.py` | CPC 双线性插值；CHM PRE V2 和 HGCDC 面积加权重网格 | `Output/Obs/Regridded/` |
| `2计算观测数据指标.py` | 四套观测产品的年指标 | `Output/Obs/indices/` |
| `3计算模式数据强度和降水变率.py` | 单模式指标计算 | `Output/Mode/indices/<mode>/<scenario>/` |
| `4批量计算多个模式_强度和降水变率.py` | 批量处理 19 个模式 | 同脚本 3 |
| `5模式数据合并.py` | 按情景合并模式指标 | `Output/Mode/indices/Scenariomerged/` |
| `6中国区域分层涌现约束.py` | 逐格点 HEC 计算 | `Output/EC/China/` |

脚本 3 和 4 按需选择一个。合并前确认模式集合完整；已有观测和合并模式指标时，可直接运行脚本 6。

## 运行

在项目根目录运行：

```bash
conda activate MET
python "src/pipeline/1统一观测数据分辨率.py"
python "src/pipeline/2计算观测数据指标.py"
python "src/pipeline/4批量计算多个模式_强度和降水变率.py"
python "src/pipeline/5模式数据合并.py"
# 不设置SCENARIO时，脚本6依次处理三个情景
unset SCENARIO
python "src/pipeline/6中国区域分层涌现约束.py"
```

单模式计算：

```bash
python "src/pipeline/3计算模式数据强度和降水变率.py" --mode ACCESS-CM2 --scenarios ssp245
```

仅计算一个 HEC 情景：

```bash
SCENARIO=ssp245 python "src/pipeline/6中国区域分层涌现约束.py"
```

## 指标与参数

- 基准期为 1981–2010 年；默认观测指标覆盖可用的 1961–2025 年，模式指标覆盖可用的 1979–2100 年。
- 三个情景为 `ssp126`、`ssp245`、`ssp585`；默认模式区域为 14–56°N、69–141°E，PrecipVar 分段点为 2015 年。
- `R90/95/99mm_intensity` 为超过基准期湿日相应百分位阈值的年平均强度，湿日定义为 ≥1 mm/day；基准期湿日少于 10 天时阈值无效。
- `PrecipVar` 为去除年循环和线性趋势后逐日残差的年标准差（ddof=0）。
- 观测侧输出三个百分位强度指标及 PrecipVar；模式侧还输出 `R10/20/25/50mm_intensity` 固定阈值强度指标。
- HEC 采用观测产品间样本标准差及标准误，至少需要 3 对有效模式样本。输出场保留完整 CN05 网格，区域统计和显著性筛选由绘图脚本完成。

## HEC 输出

每个情景生成 `HEC_<scenario>_PrecipVar_to_R95mm_intensity.nc`，变量维度为 `(lat, lon)`，类型为 float32。

| 变量 | 含义 |
|---|---|
| `r` | 模式集合历史预测因子与未来目标的相关系数 |
| `p_value` | 对应线性回归斜率的双侧检验 p 值 |
| `obs_sigma_raw` | 观测产品历史期均值之间的样本标准差；非正值置为 NaN |
| `obs_sigma_effective` | 观测误差项：obs_sigma_raw / √N |
| `prior_mean` / `prior_std` | 有效模式集合未来目标的均值 / 样本标准差 |
| `posterior_mean` / `posterior_std` | HEC 约束后的均值 / 标准差 |
| `reduction` | 标准差相对缩减比例；0.2 表示缩减 20%，文件内未乘 100 |
| `n` | 每个格点用于统计的有效模式对数量，不是观测产品数 `N` |
