# HEC extreme precipitation China

Using hierarchical emergent constraints to reduce the uncertainty in future extreme precipitation projections over China.

本研究结合四套观测降水产品和 19 个 HiCPC 模式，以历史期（1981–2010 年）降水变率约束中国近未来（2021–2050 年）极端降水强度，分析 SSP1-2.6、SSP2-4.5 和 SSP5-8.5 三种情景。

## 仓库内容

| 路径 | 内容 |
| --- | --- |
| `src/Pic/Fig*/FigN.py` | Fig1–Fig10 的绘图脚本 |
| `src/Pic/Fig*/FigN.jpg` | 论文图片 |
| `src/Pic/Fig*/data/` | 各图所需的精简绘图输入：二维场、统计表、NPZ 及地理矢量 |
| `src/pipeline/` | 本地完整分析流程 |
| `src/lib/` | 降水指标等公共函数 |
| `data.md` | 原始数据下载地址 |

## 重绘图片

绘图输入已随各图目录提供，默认出图无需下载原始数据或先运行完整分析流程。安装依赖后，运行对应脚本，例如：

```bash
pip install numpy pandas xarray netCDF4 scipy matplotlib cartopy pyshp shapely pyproj pillow
python src/Pic/Fig1_ObservedProducts/Fig1.py
python src/Pic/Fig2_ModelEvaluation/Fig2.py
python src/Pic/Fig3_ProjectionUncertainty/Fig3.py
```

其他图片同样运行各目录的 `FigN.py`。Fig2 使用从历史指标中提取的全精度相关系数和偏差；Fig3 使用已保存的集合均值与标准差；Fig6 使用稳健性试验的绘图统计。其余图片读取本目录中的观测气候态、约束场所需变量及地理文件。

## 本地完整分析

原始数据 `Data/`、完整过程数据 `Output/` 以及大型评价输入和稳健性计算缓存保留在本地，不随仓库上传。原始数据来源见 [data.md](data.md)。需要重新计算分析结果时，按 `src/pipeline/` 的编号运行本地流程，再更新各图的精简输入。绘图复现与完整分析使用相同的统计定义；精简输入保留相应绘图数值，不包含整套逐年指标或原始逐日降水。

Times New Roman 不可用时，Matplotlib 会使用可用字体替代，文字外观可能略有差异。
