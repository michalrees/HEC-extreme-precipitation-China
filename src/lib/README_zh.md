# 公共计算模块

[English](README.md) | [中文](README_zh.md)

将本目录加入 `sys.path` 后导入所需模块。

```python
import sys
from pathlib import Path

REPO_ROOT = next(p for p in Path(__file__).resolve().parents if (p / "src").is_dir() and (p / "Doc").is_dir())
sys.path.append(str(REPO_ROOT / "src" / "lib"))

import ETCCDI
from precip_variability_netcdf import compute_precip_variability_split
```

| 模块 | 用途 |
|---|---|
| `ETCCDI.py` | 极端降水指标，包括固定阈值、百分位强度及连续干湿日等指标。 |
| `precip_variability_netcdf.py` | 去除年循环和线性趋势后计算逐年降水变率。 |

主要供观测和模式指标计算脚本使用。R95 阈值按基准期逐格点湿日（≥1 mm/day）样本计算，湿日不足 10 天时设为缺测。
