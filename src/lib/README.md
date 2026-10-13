# src/lib —— 公共功能模块

供分析和绘图脚本使用的公共计算模块。
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

说明：
- 两个模块之间没有互相引用，可以独立使用。
- `R95` 系列的 95% 分位阈值在基准期内**逐格点、仅用湿日（≥1 mm/day）样本**计算；基准期湿日少于 10 天的格点阈值置为缺测。
