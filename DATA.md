# 数据说明

本仓库包含论文的全部**代码、文档与可复现所需的小型数据**。
以下文件因超过 GitHub 的单文件上限（100 MB）未纳入版本控制，需另行下载。

| 文件 | 大小 | 说明 |
|---|---:|---|
| `Data/Obs/CHM_PRE_V2_daily_1960-2024.nc` | 41,734.2 MB | 观测原始日降水（第三方数据集，请从原始提供方获取） |
| `Data/Obs/HGCDC_1961-2022.nc` | 5,700.5 MB | 观测原始日降水（第三方数据集，请从原始提供方获取） |
| `Output/Mode/indices/Scenariomerged/MULTI_MODEL-ssp585-ALL_INDICES.nc` | 4,793.8 MB | CMIP6 多模式指标场，由 `src/pipeline/` 生成 |
| `Output/Mode/indices/Scenariomerged/MULTI_MODEL-ssp245-ALL_INDICES.nc` | 4,757.8 MB | CMIP6 多模式指标场，由 `src/pipeline/` 生成 |
| `Output/Mode/indices/Scenariomerged/MULTI_MODEL-ssp126-ALL_INDICES.nc` | 4,743.0 MB | CMIP6 多模式指标场，由 `src/pipeline/` 生成 |
| `Data/Obs/CPC_1979-2025.nc` | 2,751.8 MB | 观测原始日降水（第三方数据集，请从原始提供方获取） |
| `Output/Obs/HGCDC_1961-2022_0.25-0.25.nc` | 1,732.3 MB | 观测指标/重网格产品，由 `src/pipeline/` 生成 |
| `src/Pic/Fig2_ModelEvaluation/data/MULTI_MODEL-historical-1981-2010.nc` | 1,140.8 MB | 模式历史期指标场，由 `src/pipeline/` 生成 |
| `Output/Obs/CPC_1979-2025_0.25-0.25.nc` | 1,003.4 MB | 观测指标/重网格产品，由 `src/pipeline/` 生成 |
| `Data/Obs/CN05.1_1961-2023.nc` | 917.0 MB | 观测原始日降水（第三方数据集，请从原始提供方获取） |
| `Output/Obs/CN05.1_1961-2023_0.25-0.25.nc` | 917.0 MB | 观测指标/重网格产品，由 `src/pipeline/` 生成 |
| `Output/Obs/CHM_PRE_V2_daily_1960-2024_0.25-0.25.nc` | 720.3 MB | 观测指标/重网格产品，由 `src/pipeline/` 生成 |

## 如何取得

1. **观测数据**：`Data/Obs/` 下的原始日降水请从各自提供方申请 ——
   CN05.1、HGCDC、CHM_PRE V2、CPC。（本仓库不转售第三方数据。）
2. **模式指标场**：`Output/Mode/indices/Scenariomerged/` 可由 `src/pipeline/` 下的脚本
   从 CMIP6 原始数据重新生成，见 `src/pipeline/README.md`。
3. 或从数据仓库下载（Zenodo / Figshare 等），DOI 待补：`10.5281/zenodo.XXXXXXX`。

