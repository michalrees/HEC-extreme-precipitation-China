# Shared computational modules

[English](README.md) | [中文](README_zh.md)

Add this directory to `sys.path`, then import the required module.

```python
import sys
from pathlib import Path

REPO_ROOT = next(p for p in Path(__file__).resolve().parents if (p / "src").is_dir() and (p / "Doc").is_dir())
sys.path.append(str(REPO_ROOT / "src" / "lib"))

import ETCCDI
from precip_variability_netcdf import compute_precip_variability_split
```

| Module | Purpose |
|---|---|
| `ETCCDI.py` | Extreme-precipitation indices, including fixed thresholds, percentile intensities and consecutive dry/wet days. |
| `precip_variability_netcdf.py` | Annual precipitation variability after removing the annual cycle and linear trend. |

Used mainly by the observational and model index scripts. R95 thresholds use baseline wet days (≥1 mm/day) separately at each grid cell; thresholds are missing with fewer than 10 wet days.
