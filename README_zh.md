# 分层涌现约束下中国近期未来极端降水强度的尺度依赖调整

英文题目：Scale-dependent adjustments to near-future extreme precipitation intensity over China under hierarchical emergent constraints

本仓库提供研究所用的 Python 分析与绘图代码。数据及图件通过 Zenodo 单独提供。

## 数据获取

- [Zenodo 数据记录：过程数据与分析结果](https://zenodo.org/records/23682272)
- 预留 DOI：[10.5281/zenodo.23682272](https://doi.org/10.5281/zenodo.23682272)

**当前状态：**数据仍在上传，记录尚未正式发布；预留 DOI 将在发布后生效。

数据记录包含数据获取与使用说明、文件清单及校验文件。原始降水资料请通过数据说明中列出的链接向提供方获取。

## 代码结构与使用

- `src/pipeline/`：重网格、降水指标计算、模式合并和分层涌现约束。
- `src/lib/`：降水指标计算的公共函数。
- `src/Pic/Fig*/FigN.py`：图 1–10 的绘图与诊断脚本。

将所需的 Zenodo 压缩包解压到项目根目录，保留包内相对路径。`geographic_inputs.zip` 包含绘图所用的边界、流域和山脉矢量资料。运行分析与绘图脚本需要相应数据，仅下载代码不足以完成计算和绘图。

Python 依赖包括 numpy、pandas、xarray、netCDF4、scipy、matplotlib、cartopy、pyshp、shapely、pyproj、dask、tqdm 和 rioxarray。文件路径及分析参数在各脚本中设置。
