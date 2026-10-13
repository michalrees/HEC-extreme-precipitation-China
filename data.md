# 原始数据来源与存放位置

本文档列出研究使用的原始数据来源、获取地址和项目内路径。所有本地路径均相对于仓库根目录；`Data/` 和 `Output/Obs/Regridded/` 不随仓库上传，需要自行准备。表中的文件名是本项目整理后的输入名称，不一定与数据平台下载文件名相同。

## 观测降水

四套观测产品用于计算历史期降水波动与极端降水强度，并以产品间差异估计观测误差。历史分析时段为 1981–2010 年。

| 产品 | 原始数据获取地址 | 数据说明 | 项目内输入路径 |
| --- | --- | --- | --- |
| CN05.1 | [中国科学院大气物理研究所资源页面](https://ccrc.iap.ac.cn/resource/detail?id=228) | 中国格点日尺度观测产品，使用日降水、0.25° 网格；本地文件覆盖 1961–2023 年。该网格作为观测重采样的目标网格。获取版本及权限以提供方说明为准。 | `Data/Obs/CN05.1_1961-2023.nc` |
| CPC Global Unified Gauge-Based Analysis of Daily Precipitation | [NOAA 产品说明](https://psl.noaa.gov/data/gridded/data.cpc.globalprecip.html)、[NetCDF 下载目录](https://downloads.psl.noaa.gov/Datasets/cpc_global_precip/) | 全球雨量站分析日降水产品，0.5° 网格；项目整理为 1979–2025 年文件。文件名中的年份不保证末年每日均有有效值。 | `Data/Obs/CPC_1979-2025.nc` |
| CHM_PRE V2 | [数据 DOI](https://doi.org/10.11888/Atmos.tpdc.300523)、[数据产品页面](https://data.tpdc.ac.cn/en/data/e5c335d9-cbb9-48a6-ba35-d67dd614bb8c) | 中国大陆格点日降水产品；本项目使用 V2、0.1° 网格及本地 1960–2024 年文件。数据页面持续更新，下载时应确认 V2 和所需年份。 | `Data/Obs/CHM_PRE_V2_daily_1960-2024.nc` |
| HGCDC | [数据 DOI](https://doi.org/10.11888/Atmos.tpdc.302712)、[CSTR 永久地址](https://cstr.cn/18406.11.Atmos.tpdc.302712) | 中国均一化格点气候数据集，使用日降水、0.1° 网格。Wang et al. (2025) 发布记录覆盖 1961–2024 年；项目现有输入文件覆盖 1961–2022 年，两者应区分。 | `Data/Obs/HGCDC_1961-2022.nc` |

CHM_PRE V2 的方法介绍见 [Hu et al. (2025)](https://doi.org/10.5194/essd-17-3987-2025)。HGCDC 的数据引用为 Wang, K., Cai, H., He, Y., Li, Y., Xia, H., Ying, C., Yu, H., Zhao, R., Zhang, Z., and Zhou, C. (2025), *Homogenized gridded climate dataset for China (1961–2024)*, National Tibetan Plateau / Third Pole Environment Data Center。

## 模式降水

使用 HiCPC（High-resolution CMIP6 downscaled daily Climate Projections over China）的日降水变量 `pr`：

- [数据 DOI](https://doi.org/10.11888/Atmos.tpdc.301122)
- [国家青藏高原科学数据中心产品页面](https://data.tpdc.ac.cn/zh-hans/data/842a025c-9683-4509-8ab4-599b3a00ba56)
- [Yuan et al. (2024) 数据论文](https://doi.org/10.1038/s41597-024-03982-x)

HiCPC 为 0.1° × 0.1° 的 CMIP6 统计降尺度产品，提供历史期 1979–2014 年及未来 2015–2100 年数据。发布产品包含 22 个模式与四种 SSP 情景；本研究选用其中 19 个模式以及 `ssp126`、`ssp245`、`ssp585` 三种情景，分析历史期 1981–2010 年和未来期 2021–2050 年。

项目要求的输入路径为：

```text
Data/Mode/<mode>/HiCPC_pr_<mode>_<scenario>.nc
```

每个输入文件需事先包含相应模式的历史期与对应情景未来期数据。当前流水线不负责下载或拼接原始文件。模式清单与处理参数见 [流水线说明](src/pipeline/README.md)。

## 地理辅助数据

| 用途 | 项目内路径 | 说明 |
| --- | --- | --- |
| 中国边界及区域绘图 | `Data/China/cnmap.shp` | 用于中国区域掩膜与地图边界。 |
| 黄河流域 | `Data/River/HuanghaiRiver_polygon.shp` | 项目中保留的文件名，实际用途为黄河流域掩膜。 |
| 长江流域 | `Data/River/YangtzeRiver_polygon.shp` | 用于长江流域掩膜。 |
| 珠江流域 | `Data/River/PearlRiver_polygon.shp` | 用于珠江流域掩膜。 |
| 山脉位置 | `Data/CN_MountainRanges/CN_MountainRanges.shp` | 用于山脉位置标注；绘图时需核实坐标参考系。 |

这些本地矢量文件的原始发布地址尚未在项目资料中明确记录，不能据文件名确定下载来源；复现时需要补充同一版本的数据及来源。Shapefile 应同时保留 `.shx`、`.dbf`、`.prj` 等配套文件。

## 从原始输入到分析数据

1. 将下载数据整理为上述输入路径。降水数值应已转换为 `mm/day`，并具有日尺度 `time` 与一维 `lat`、`lon` 坐标；仅修改单位属性不会转换实际数值。
2. 观测重网格结果放在 `Output/Obs/Regridded/`：CPC 使用双线性插值，CHM_PRE V2 与 HGCDC 使用球面网格重叠面积加权。CN05.1 作为目标网格，流水线脚本 1 不生成其预处理文件；需另行准备 `CN05.1_1961-2023_0.25-0.25.nc`。
3. 观测指标保存在 `Output/Obs/indices/`，模式指标保存在 `Output/Mode/indices/`，分层涌现约束结果保存在 `Output/EC/China/`。

完整输入要求、处理步骤及输出命名见 [src/pipeline/README.md](src/pipeline/README.md)；各图的数据输入见相应绘图目录的 README。
