# HEC extreme precipitation China

Using hierarchical emergent constraints to reduce the uncertainty in future extreme precipitation projections over China.

## 目录

| 路径 | 内容 |
|---|---|
| `src/Pic/Fig1_ObservedProducts/` … `Fig11_UncertaintyDecomposition/` | 11 张图的绘图脚本，每个目录一份 `FigN.py` + `FigN.jpg` + `data/` + `README.md` |
| `src/pipeline/` | 观测重网格、指标计算、模式合并与分层涌现约束（HEC）主流程 |
| `src/lib/` | 公共函数库（ETCCDI 指标、降水变率等） |

## 复现

先跑 `src/pipeline/` 生成约束场，再按各图目录的 README 出图。
每个 `src/Pic/*/README.md` 都写明了该图的输入、产出、依赖与运行命令。

## 数据

超过 GitHub 单文件上限的数据见 [`DATA.md`](DATA.md)。

