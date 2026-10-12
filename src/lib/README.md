# src/lib —— 公共功能模块

从 `src/` 根目录整理到此，供 `src/` 下的分析脚本与 `src/Pic/` 下的绘图脚本复用。
调用方式：把本目录加入 `sys.path` 后直接按模块名导入。

```python
import sys
from pathlib import Path

REPO_ROOT = next(p for p in Path(__file__).resolve().parents if (p / "src").is_dir() and (p / "Doc").is_dir())
sys.path.append(str(REPO_ROOT / "src" / "lib"))

import ETCCDI
from precip_variability_netcdf import compute_precip_variability_split
```

| 模块 | 作用 | 主要调用方 |
|---|---|---|
| `ETCCDI.py` | 极端气候指标函数库：R1mm/R10mm/R20mm/R25mm/R50mm 系列、百分位阈值指标（R95mm intensity 等）、SDII、RX1DAY、RX5DAY、CDD/CWD、PRCPTOT | `src/pipeline/2计算观测数据指标.py`、`src/pipeline/3计算模式数据强度和降水变率.py`（脚本 4 只是 subprocess 批量驱动，不直接导入本模块） |
| `precip_variability_netcdf.py` | 日降水变率（Precip Var）计算：去日序气候态、去线性趋势后求逐年标准差 | `src/pipeline/2计算观测数据指标.py`、`src/pipeline/3计算模式数据强度和降水变率.py` |
| `hec_grid_interpolate.py` | 逐格点 HEC 的简化解析实现（方法原型，非主流程） | 暂无脚本导入；对比说明见 `废弃/Others/说明/hec_grid_interpolate_与正式HEC流程对比.md` |
| `hec_integrate.py` | 数值「两级积分」实现，用于核对 `src/pipeline/6中国区域分层涌现约束.py` 的闭式后验解与论文 §2.3 两级模型是否等价 | 无脚本导入（独立自检脚本）；`python src/lib/hec_integrate.py` 会跑等价性自检，2026-10-09 复核：90 组样本最大偏差 5.0e-15（均值）/ 3.7e-14（标准差），阈值 1e-6，判定一致 |

说明：
- 四个模块之间没有互相引用，可以独立使用。
- `R95` 系列的 95% 分位阈值在基准期内**逐格点、仅用湿日（≥1 mm/day）样本**计算；基准期湿日少于 10 天的格点阈值置为缺测。
