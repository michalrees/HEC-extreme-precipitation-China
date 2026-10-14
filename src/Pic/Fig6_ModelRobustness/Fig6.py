# -*- coding: utf-8 -*-

from __future__ import annotations

import argparse
import sys
import time
import warnings
from pathlib import Path
from typing import Dict, List, Sequence, Tuple

import numpy as np
import pandas as pd
import xarray as xr
from scipy import stats as _st

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.colors import BoundaryNorm, ListedColormap, Normalize
from matplotlib.lines import Line2D
from matplotlib.patches import Patch
from matplotlib.ticker import MultipleLocator, FuncFormatter

import cartopy.crs as ccrs
import shapefile
from shapely.geometry import shape as shapely_shape

# 原 01_robustness_check.py 的模块级数值设置：让逐格点向量化运算中的
# 除零 / 无效值静默进行（只在"被剔除的格点"上产生 NaN，不影响有效格点结果）。
np.seterr(all="ignore")
warnings.filterwarnings("ignore", category=RuntimeWarning)

# 原 02_make_figures.py 的模块级绘图设置
plt.rcParams["font.family"] = "Times New Roman"
plt.rcParams["mathtext.fontset"] = "cm"
plt.rcParams["axes.unicode_minus"] = False


# ==================================================================
# 0. 常量
# ==================================================================
HIST_PERIOD_RANGE: Tuple[int, int] = (1981, 2010)
FUTURE_PERIOD_RANGE: Tuple[int, int] = (2021, 2050)
HIST_INDICATOR = "PrecipVar"
FUTURE_INDICATOR = "R95mm_intensity"

SCENARIOS: Tuple[str, ...] = ("ssp126", "ssp245", "ssp585")
SCENARIO_LABELS: Dict[str, str] = {
    "ssp126": "SSP1-2.6",
    "ssp245": "SSP2-4.5",
    "ssp585": "SSP5-8.5",
}


USE_OBS_STANDARD_ERROR = True    # 与脚本 6 保持一致：σ_o = 产品间标准差/√N（均值标准误）

MODE_ORDER: Tuple[str, ...] = (
    "ACCESS-CM2", "ACCESS-ESM1-5", "AWI-CM-1-1-MR", "CESM2", "CNRM-CM6-1",
    "CanESM5", "EC-Earth3-Veg", "FGOALS-g3", "IITM-ESM", "INM-CM4-8",
    "INM-CM5-0", "KACE-1-0-G", "KIOST-ESM", "MPI-ESM1-2-HR", "MRI-ESM2-0",
    "NESM3", "NorESM2-LM", "NorESM2-MM", "TaiESM1",
)

# 模式家族（保守分组，依据命名/机构/已知共用分量；见 Doc/Markdown/模式成员之间的联系.md §4）
FAMILIES: Dict[str, List[str]] = {
    "G1_ACCESS": ["ACCESS-CM2", "ACCESS-ESM1-5"],
    "G2_CESM": ["CESM2", "NorESM2-LM", "NorESM2-MM", "TaiESM1"],
    "G3_INM": ["INM-CM4-8", "INM-CM5-0"],
    "G4_ECHAM6": ["MPI-ESM1-2-HR", "AWI-CM-1-1-MR"],
}
# 分组敏感性：把 TaiESM1 从 CESM 谱系中摘出（TaiESM1 基于 CESM1 而非 CESM2，
# 属于"可争论"的成员，因此单列一个更保守的变体做敏感性检验）。
FAMILY_VARIANTS: Dict[str, List[str]] = {
    "G2b_CESM_core": ["CESM2", "NorESM2-LM", "NorESM2-MM"],
}


FAMILY_LABELS: Dict[str, str] = {
    "G1_ACCESS": "ACCESS",
    "G2_CESM": "CESM",
    "G3_INM": "INM",
    "G4_ECHAM6": "ECHAM6",
    "G2b_CESM_core": "CESM core",
}

# ---- 稳健性检查的判据（原 01_robustness_check.py）----
SIG_R_MIN = 0.5
SIG_P_MAX = 0.05
# Fig. 5b 的分级边界（用于"变类"统计）
REDUCTION_BOUNDS = np.array([0.0, 0.1, 0.2, 0.4, 0.6, 0.7])

# ---- 自检容差（原 03_selftest.py）----
TOL = 1e-4          # 相对 float32 存档量的量化精度

# ------------------------------------------------------------------
# 1. 路径
# ------------------------------------------------------------------
THIS_DIR = Path(__file__).resolve().parent
STUDY_ROOT = THIS_DIR          # 脚本与 data/ 同级，模块根即脚本所在目录
REPO_ROOT = next(
    p for p in THIS_DIR.parents if (p / "src").is_dir() and (p / "Doc").is_dir()
)


DATA_ROOT = REPO_ROOT / "Data"
DATA_DIR = STUDY_ROOT / "data"
FIG_DIR = STUDY_ROOT
CACHE_DIR = DATA_DIR / "cache"

MODE_FILE: Dict[str, Path] = {
    s: REPO_ROOT / "Output" / "Mode" / "indices" / "Scenariomerged"
    / f"MULTI_MODEL-{s}-ALL_INDICES.nc"
    for s in SCENARIOS
}
HEC_BASELINE_FILE: Dict[str, Path] = {
    s: REPO_ROOT / "Output" / "EC" / "China"
    / f"HEC_{s}_{HIST_INDICATOR}_to_{FUTURE_INDICATOR}.nc"
    for s in SCENARIOS
}
OBS_FILES: Dict[str, Path] = {
    "CN05": REPO_ROOT / "Output" / "Obs" / "indices" / "CN05-OBS-IntensityAndPrecipVar-1961-2023.nc",
    "CPC": REPO_ROOT / "Output" / "Obs" / "indices" / "CPC-OBS-IntensityAndPrecipVar-1979-2025.nc",
    "CHM_PRE_V2": REPO_ROOT / "Output" / "Obs" / "indices" / "CHM_PRE_V2-OBS-IntensityAndPrecipVar-1961-2024.nc",
    "HGCDC": REPO_ROOT / "Output" / "Obs" / "indices" / "HGCDC-OBS-IntensityAndPrecipVar-1961-2022.nc",
}


FOREIGN_CACHE_DIR = REPO_ROOT.parent / "废弃" / "code" / "完美模式检验" / "data" / "cache"
RIVER_DIR = DATA_ROOT / "River"

# ------------------------------------------------------------------
# 2. 区域定义（与 Fig.4 / Fig.6 的区域体系一致）
# ------------------------------------------------------------------
REGIONS_BOX: Tuple[Tuple[str, float, float, float, float], ...] = (
    ("China", -90.0, 90.0, -180.0, 360.0),
    ("NorthChina", 35.0, 42.0, 110.0, 118.0),
    ("Northeast", 38.0, 54.0, 118.0, 135.0),
    ("Northwest", 35.0, 50.0, 73.0, 105.0),
    ("Southwest", 21.0, 35.0, 95.0, 108.0),
    ("EastChina", 27.0, 35.0, 115.0, 123.0),
    ("SouthChina", 18.0, 26.0, 108.0, 120.0),
    ("CentralChina", 26.0, 34.0, 108.0, 115.0),
)
RIVER_BASINS: Tuple[Tuple[str, str], ...] = (
    ("YellowRiver", "HuanghaiRiver_polygon.shp"),
    ("PearlRiver", "PearlRiver_polygon.shp"),
    ("YangtzeRiver", "YangtzeRiver_polygon.shp"),
)
REGION_ORDER: Tuple[str, ...] = tuple(r[0] for r in REGIONS_BOX) + tuple(
    r[0] for r in RIVER_BASINS
)

SCENARIO_COLORS = {"ssp126": "#2b7bba", "ssp245": "#e08a1e", "ssp585": "#c0392b"}


# ==================================================================
# 3. 面积加权重网格（与 pipeline/6 逐行一致）
# ==================================================================
def _cell_bounds(vals: np.ndarray) -> np.ndarray:
    b = np.empty(vals.size + 1, dtype=np.float64)
    b[1:-1] = 0.5 * (vals[:-1] + vals[1:])
    b[0] = vals[0] - 0.5 * (vals[1] - vals[0])
    b[-1] = vals[-1] + 0.5 * (vals[-1] - vals[-2])
    return b


def build_overlap_weights(
    src_lat: np.ndarray,
    src_lon: np.ndarray,
    dst_lat: np.ndarray,
    dst_lon: np.ndarray,
) -> Tuple[np.ndarray, np.ndarray, slice, slice]:
    """源网格 -> 目标网格的面积重叠权重矩阵 (w_lat, w_lon, lat_slice, lon_slice)。"""
    src_lat = np.asarray(src_lat, dtype=np.float64)
    src_lon = np.asarray(src_lon, dtype=np.float64)
    dst_lat = np.asarray(dst_lat, dtype=np.float64)
    dst_lon = np.asarray(dst_lon, dtype=np.float64)

    src_lat_b = np.sin(np.deg2rad(_cell_bounds(src_lat)))
    src_lon_b = _cell_bounds(src_lon)
    dst_lat_b = np.sin(np.deg2rad(_cell_bounds(dst_lat)))
    dst_lon_b = _cell_bounds(dst_lon)

    lat_overlap = np.maximum(
        0.0,
        np.minimum(src_lat_b[1:][None, :], dst_lat_b[1:][:, None])
        - np.maximum(src_lat_b[:-1][None, :], dst_lat_b[:-1][:, None]),
    )
    lon_overlap = np.maximum(
        0.0,
        np.minimum(src_lon_b[1:][None, :], dst_lon_b[1:][:, None])
        - np.maximum(src_lon_b[:-1][None, :], dst_lon_b[:-1][:, None]),
    )
    with np.errstate(invalid="ignore", divide="ignore"):
        w_lat = lat_overlap / (dst_lat_b[1:] - dst_lat_b[:-1])[:, None]
        w_lon = lon_overlap / (dst_lon_b[1:] - dst_lon_b[:-1])[:, None]
    w_lat = np.where(np.isfinite(w_lat), w_lat, 0.0)
    w_lon = np.where(np.isfinite(w_lon), w_lon, 0.0)

    # 裁剪到权重非零的窗口，避免整幅 einsum
    # 权重列对应源网格，裁剪源数据必须使用列索引。
    lat_keep = np.where(w_lat.sum(axis=0) > 0)[0]
    lon_keep = np.where(w_lon.sum(axis=0) > 0)[0]
    lat_sl = slice(int(lat_keep.min()), int(lat_keep.max()) + 1) if lat_keep.size else slice(0, 0)
    lon_sl = slice(int(lon_keep.min()), int(lon_keep.max()) + 1) if lon_keep.size else slice(0, 0)
    return w_lat[:, lat_sl], w_lon[:, lon_sl], lat_sl, lon_sl


def regrid_conservative(
    field: np.ndarray,
    w_lat: np.ndarray,
    w_lon: np.ndarray,
    lat_sl: slice,
    lon_sl: slice,
) -> np.ndarray:
    """面积加权（一阶守恒式）重网格；NaN 按权重归一，全 NaN 格点返回 NaN。"""
    src = field[lat_sl, lon_sl].astype(np.float64)
    valid = np.isfinite(src)
    x0 = np.where(valid, src, 0.0)
    num = np.einsum("li,ik->lk", w_lat, np.einsum("ij,kj->ik", x0, w_lon, optimize=True), optimize=True)
    den = np.einsum(
        "li,ik->lk", w_lat,
        np.einsum("ij,kj->ik", valid.astype(np.float64), w_lon, optimize=True),
        optimize=True,
    )
    with np.errstate(invalid="ignore", divide="ignore"):
        out = num / den
    out[den <= 0.0] = np.nan
    return out


# ==================================================================
# 4. 数据装载
# ==================================================================
def _period_mean(da: xr.DataArray, year_range: Tuple[int, int]) -> np.ndarray:
    if "time" in da.dims and "year" not in da.dims:
        da = da.rename({"time": "year"})
    if "year" in da.coords and np.issubdtype(da["year"].dtype, np.datetime64):
        da = da.assign_coords(year=da["year"].dt.year.astype("int32"))
    return da.sel(year=slice(*year_range)).mean(dim="year", skipna=True)


def _sort_latlon(da: xr.DataArray) -> xr.DataArray:
    cmap = {str(n).lower(): str(n) for n in da.coords}
    la = cmap.get("lat") or cmap.get("latitude") or cmap.get("y")
    lo = cmap.get("lon") or cmap.get("longitude") or cmap.get("x")
    if la is None or lo is None:
        raise ValueError("场缺少经纬度坐标")
    if la != "lat":
        da = da.rename({la: "lat"})
    if lo != "lon":
        da = da.rename({lo: "lon"})
    if float(da["lon"].max()) > 180.0:
        da = da.assign_coords(lon=((da["lon"] + 180.0) % 360.0) - 180.0)
    if da["lat"].size > 1 and float(da["lat"][1] - da["lat"][0]) < 0:
        da = da.sortby("lat")
    if da["lon"].size > 1 and float(da["lon"][1] - da["lon"][0]) < 0:
        da = da.sortby("lon")
    return da


def target_grid() -> Tuple[np.ndarray, np.ndarray]:
    """CN05 的 0.25° 目标网格。"""
    with xr.open_dataset(OBS_FILES["CN05"]) as ds:
        lat = ds["lat"].values.astype(np.float64)
        lon = ds["lon"].values.astype(np.float64)
    if lat[1] < lat[0]:
        lat = lat[::-1]
    if lon[1] < lon[0]:
        lon = lon[::-1]
    return lat, lon


def load_observation_layer(
    target_lat: np.ndarray, target_lon: np.ndarray
) -> Tuple[np.ndarray, np.ndarray, np.ndarray]:
    """HEC 观测层：四套产品在 1981–2010 的 PrecipVar 均值、离散度与有效产品数。"""
    fields = []
    for _, fp in OBS_FILES.items():
        if not fp.exists():
            raise FileNotFoundError(f"未找到观测文件: {fp}")
        with xr.open_dataset(fp) as ds:
            da = _sort_latlon(_period_mean(ds[HIST_INDICATOR], HIST_PERIOD_RANGE))
            if da.sizes.get("lat", 0) != target_lat.size or da.sizes.get("lon", 0) != target_lon.size:
                raise ValueError(f"{fp.name} 网格与 CN05 不一致，需先运行 pipeline/1 统一分辨率")
            fields.append(da.transpose("lat", "lon").values.astype(np.float32))
    stack = np.stack(fields, axis=0)
    obs_mean = np.nanmean(stack, axis=0)
    obs_sigma_raw = np.nanstd(stack, axis=0, ddof=1)
    obs_count = np.sum(np.isfinite(stack), axis=0).astype(np.float64)
    obs_sigma_eff = obs_sigma_raw / np.sqrt(obs_count) if USE_OBS_STANDARD_ERROR else obs_sigma_raw

    obs_mean = np.where(np.isfinite(obs_mean), obs_mean, np.nan)
    obs_sigma_eff = np.where(np.isfinite(obs_sigma_eff) & (obs_sigma_eff > 0), obs_sigma_eff, np.nan)
    return obs_mean, obs_sigma_raw, obs_sigma_eff


def load_model_fields(
    scenario: str,
    target_lat: np.ndarray,
    target_lon: np.ndarray,
    *,
    force: bool = False,
) -> Tuple[List[str], np.ndarray, np.ndarray]:
    """返回 (模式名, X(历史 PrecipVar), Y(未来 R95 强度))，形状 (n_mode, lat, lon)。

    优先读重网格缓存（本目录 data/cache，其次完美模式检验目录的同名缓存）；
    缓存缺失时按 pipeline/6 的面积加权算法现场重网格并落盘。
    """
    cache_paths = {m: CACHE_DIR / f"regrid_{scenario}_{m}.nc" for m in MODE_ORDER}
    foreign = {m: FOREIGN_CACHE_DIR / f"lomo_regrid_{scenario}_{m}.nc" for m in MODE_ORDER}

    if not force and all(p.exists() for p in cache_paths.values()):
        X, Y = [], []
        for m in MODE_ORDER:
            with xr.open_dataset(cache_paths[m]) as ds:
                X.append(ds["X_regrid"].values.astype(np.float64))
                Y.append(ds["Y_regrid"].values.astype(np.float64))
        return list(MODE_ORDER), np.stack(X), np.stack(Y)

    if not force and all(p.exists() for p in foreign.values()):
        X, Y = [], []
        for m in MODE_ORDER:
            with xr.open_dataset(foreign[m]) as ds:
                X.append(ds["X_regrid"].values.astype(np.float64))
                Y.append(ds["Y_regrid"].values.astype(np.float64))
        return list(MODE_ORDER), np.stack(X), np.stack(Y)

    # ---- 现场重网格 ----
    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    with xr.open_dataset(MODE_FILE[scenario]) as ds_all:
        mode_names = [str(v) for v in ds_all["Mode"].values]
        missing = [m for m in MODE_ORDER if m not in mode_names]
        if missing:
            raise ValueError(f"模式文件中缺少: {missing}")
        X, Y = [], []
        for m in MODE_ORDER:
            print(f"    [regrid] {scenario} / {m}", flush=True)
            ds_m = ds_all.sel(Mode=m)
            xm = _sort_latlon(_period_mean(ds_m[HIST_INDICATOR], HIST_PERIOD_RANGE))
            ym = _sort_latlon(_period_mean(ds_m[FUTURE_INDICATOR], FUTURE_PERIOD_RANGE))
            w_lat, w_lon, lat_sl, lon_sl = build_overlap_weights(
                xm["lat"].values, xm["lon"].values, target_lat, target_lon
            )
            xr_out = regrid_conservative(xm.transpose("lat", "lon").values, w_lat, w_lon, lat_sl, lon_sl)
            yr_out = regrid_conservative(ym.transpose("lat", "lon").values, w_lat, w_lon, lat_sl, lon_sl)
            xr.Dataset(
                {
                    "X_regrid": (("lat", "lon"), xr_out.astype(np.float32)),
                    "Y_regrid": (("lat", "lon"), yr_out.astype(np.float32)),
                },
                coords={"lat": target_lat, "lon": target_lon},
                attrs={"scenario": scenario, "mode": m,
                       "history_period": f"{HIST_PERIOD_RANGE[0]}-{HIST_PERIOD_RANGE[1]}",
                       "future_period": f"{FUTURE_PERIOD_RANGE[0]}-{FUTURE_PERIOD_RANGE[1]}"},
            ).to_netcdf(cache_paths[m])
            X.append(xr_out.astype(np.float32))
            Y.append(yr_out.astype(np.float32))
    return list(MODE_ORDER), np.stack(X), np.stack(Y)


# ==================================================================
# 5. HEC 子集解算（逐格点向量化，公式与 pipeline/6 逐项一致）
# ==================================================================
def hec_subset(
    X: np.ndarray,
    Y: np.ndarray,
    obs_mean: np.ndarray,
    obs_sigma_eff: np.ndarray,
    keep: Sequence[int],
) -> Dict[str, np.ndarray]:
    """对模式子集 ``keep`` 复现 pipeline/6 的 HEC 诊断场。

    公式对应论文 (1)–(5) 式：``y_c = ȳ + a/(1+SNR⁻¹)(x₀−x̄)``、
    ``σ²_yc = (1 − ρ²/(1+SNR⁻¹)) σ_y²``、``SNR = σ_x²/σ_o²``。
    """
    Xs = X[list(keep)]
    Ys = Y[list(keep)]
    valid = (
        np.isfinite(Xs) & np.isfinite(Ys)
        & np.isfinite(obs_mean)[None, :, :] & np.isfinite(obs_sigma_eff)[None, :, :]
    )
    n = valid.sum(axis=0).astype(np.float64)
    xs = np.where(valid, Xs, 0.0)
    ys = np.where(valid, Ys, 0.0)
    with np.errstate(invalid="ignore", divide="ignore"):
        xb = np.where(n > 0, xs.sum(axis=0) / n, np.nan)
        yb = np.where(n > 0, ys.sum(axis=0) / n, np.nan)
        xd = np.where(valid, Xs - xb[None, :, :], 0.0)
        yd = np.where(valid, Ys - yb[None, :, :], 0.0)
        sxx = (xd ** 2).sum(axis=0)
        syy = (yd ** 2).sum(axis=0)
        sxy = (xd * yd).sum(axis=0)
        sx = np.sqrt(np.where(n > 1, sxx / (n - 1), np.nan))
        sy = np.sqrt(np.where(n > 1, syy / (n - 1), np.nan))
        r = sxy / np.sqrt(np.where(sxx * syy > 0, sxx * syy, np.nan))

    var_x, var_y = sx ** 2, sy ** 2
    df = n - 2
    with np.errstate(invalid="ignore", divide="ignore"):
        tstat = r * np.sqrt(df / (1.0 - r ** 2))
    p_value = 2.0 * _st.t.sf(np.abs(tstat), df)

    core = (n >= 3) & np.isfinite(r) & (var_x > 0) & (var_y > 0)
    for arr in (r, p_value, sx, sy, xb, yb):
        arr[~core] = np.nan

    with np.errstate(invalid="ignore", divide="ignore"):
        snr = var_x / obs_sigma_eff ** 2
        posterior_mean = yb + (r * sy / sx) * (obs_mean - xb) / (var_x + obs_sigma_eff ** 2) * var_x
        posterior_std = np.sqrt(np.clip(1.0 - r ** 2 / (1.0 + 1.0 / snr), 0.0, None) * var_y)
        reduction = 1.0 - posterior_std / sy

    out = {
        "r": r,
        "p_value": p_value,
        "prior_mean": yb,
        "prior_std": sy,
        "posterior_mean": posterior_mean,
        "posterior_std": posterior_std,
        "reduction": reduction,
        "bias": posterior_mean - yb,
        "n": n,
    }
    for k in ("posterior_mean", "posterior_std", "reduction", "bias"):
        out[k] = np.where(core, out[k], np.nan)
    out["n_models"] = np.where(core, n, np.nan)
    return out


# ==================================================================
# 6. 区域掩膜与面积加权
# ==================================================================
def build_region_masks(lat: np.ndarray, lon: np.ndarray) -> Dict[str, np.ndarray]:
    """11 个区域的布尔掩膜（8 个经纬框 + 3 个流域多边形）。"""
    lon2d, lat2d = np.meshgrid(lon, lat)
    masks: Dict[str, np.ndarray] = {}
    for name, lat_min, lat_max, lon_min, lon_max in REGIONS_BOX:
        masks[name] = (lat2d >= lat_min) & (lat2d <= lat_max) & (lon2d >= lon_min) & (lon2d <= lon_max)

    try:
        import shapefile  # pyshp
        from shapely.geometry import shape as _shape
        from shapely.ops import unary_union
        from shapely import contains_xy
    except ImportError:  # pragma: no cover
        return masks

    for name, fname in RIVER_BASINS:
        fp = RIVER_DIR / fname
        if not fp.exists():
            continue
        sf = shapefile.Reader(str(fp))
        merged = unary_union([_shape(s.__geo_interface__) for s in sf.shapes()])
        masks[name] = np.asarray(contains_xy(merged, lon2d.ravel(), lat2d.ravel())).reshape(lon2d.shape)
    return masks


def area_weights(lat: np.ndarray) -> np.ndarray:
    return np.cos(np.deg2rad(lat))[:, np.newaxis]


def weighted_mean(field: np.ndarray, mask: np.ndarray, w2d: np.ndarray) -> float:
    ok = mask & np.isfinite(field)
    denom = np.nansum(w2d * ok)
    if denom <= 0:
        return float("nan")
    return float(np.nansum(np.where(ok, field, 0.0) * w2d) / denom)


# ==================================================================
# 7. 情景 / 算例清单
# ==================================================================
def build_cases() -> List[Dict[str, object]]:
    """构造全部算例：baseline + LOMO(19) + LOFO(4) + 分组敏感性(1) = 25。"""
    all_idx = list(range(len(MODE_ORDER)))
    cases: List[Dict[str, object]] = [
        {"case": "ALL", "group": "Baseline", "label": "All 19 models (reference)",
         "excluded": [], "keep": all_idx},
    ]
    for i, m in enumerate(MODE_ORDER):
        cases.append({
            "case": f"LOMO_{m}", "group": "LOMO",
            "label": f"Exclude {m}", "excluded": [m],
            "keep": [j for j in all_idx if j != i],
        })
    for fam, members in FAMILIES.items():
        cases.append({
            "case": f"LOFO_{fam}", "group": "LOFO",
            "label": f"Exclude {FAMILY_LABELS.get(fam, fam)} ({len(members)})",
            "excluded": list(members),
            "keep": [j for j, m in enumerate(MODE_ORDER) if m not in members],
        })
    for fam, members in FAMILY_VARIANTS.items():
        cases.append({
            "case": f"LOFO_{fam}", "group": "Sensitivity",
            "label": f"Exclude {FAMILY_LABELS.get(fam, fam)} ({len(members)})",
            "excluded": list(members),
            "keep": [j for j, m in enumerate(MODE_ORDER) if m not in members],
        })
    return cases


# ==================================================================
# 8. 主计算：排除单个模式 / 模式家族后的逐格点稳健性检查
#    （原 01_robustness_check.py）
# ==================================================================
def log(msg: str) -> None:
    print(f"[{time.strftime('%H:%M:%S')}] {msg}", flush=True)


def significance_mask(r: np.ndarray, p: np.ndarray) -> np.ndarray:
    """Fig. 5 的掩膜判据：p < 0.05 且 r >= 0.5。"""
    return np.isfinite(r) & np.isfinite(p) & (p < SIG_P_MAX) & (r >= SIG_R_MIN)


def class_index(field: np.ndarray, bounds: np.ndarray) -> np.ndarray:
    """把 reduction 场映射到 Fig. 5b 的分级序号；非有限值记为 -1。"""
    idx = np.clip(np.digitize(field, bounds) - 1, 0, len(bounds) - 2)
    return np.where(np.isfinite(field), idx, -1)


def run_robustness_check(
    force_regrid: bool = False,
    scenarios: Sequence[str] = SCENARIOS,
) -> int:
    """25 算例 × 3 情景逐格点重算，并写出 3 个 nc + 4 个 CSV。"""
    DATA_DIR.mkdir(parents=True, exist_ok=True)

    log("仓库根: " + str(REPO_ROOT))
    lat, lon = target_grid()
    w2d = area_weights(lat)
    log(f"目标网格: lat={lat.size}, lon={lon.size}")

    obs_mean, obs_sigma_raw, obs_sigma_eff = load_observation_layer(lat, lon)
    log(f"观测层: 有效格点 {int(np.isfinite(obs_mean).sum())}, "
        f"σ_o(标准误) 全域均值 {np.nanmean(obs_sigma_eff):.4f}")

    region_masks = build_region_masks(lat, lon)
    log(f"区域掩膜 {len(region_masks)} 个: {', '.join(region_masks)}")

    cases = build_cases()
    case_names = [c["case"] for c in cases]
    log(f"算例 {len(cases)} 个: 1 baseline + "
        f"{sum(c['group'] == 'LOMO' for c in cases)} LOMO + "
        f"{sum(c['group'] == 'LOFO' for c in cases)} LOFO + "
        f"{sum(c['group'] == 'Sensitivity' for c in cases)} 敏感性")

    region_rows: list[dict] = []
    sim_rows: list[dict] = []
    meta: dict[str, object] = {
        "n_models_full": len(MODE_ORDER),
        "n_cases": len(cases),
        "sig_rule": f"p < {SIG_P_MAX} and r >= {SIG_R_MIN}",
        "reduction_bounds": ",".join(f"{b:g}" for b in REDUCTION_BOUNDS),
        "obs_uncertainty": "standard_error" if USE_OBS_STANDARD_ERROR else "spread",
        "history_period": "1981-2010",
        "future_period": "2021-2050",
    }

    for scenario in scenarios:
        log(f"===== {SCENARIO_LABELS[scenario]} =====")
        t0 = time.time()
        modes, X, Y = load_model_fields(scenario, lat, lon, force=force_regrid)
        log(f"  模式场 {X.shape}, 装载 {time.time() - t0:.1f}s")

        # ---- 自检：ALL 必须复现存档的 Fig.5 基线 ----
        base = hec_subset(X, Y, obs_mean, obs_sigma_eff, list(range(len(modes))))
        ref_fp = HEC_BASELINE_FILE[scenario]
        if ref_fp.exists():
            with xr.open_dataset(ref_fp) as ref:
                for name in ("r", "p_value", "reduction", "posterior_mean", "posterior_std", "prior_mean"):
                    np.testing.assert_allclose(
                        base[name], ref[name].values, rtol=1e-5, atol=1e-6,
                        equal_nan=True, err_msg=f"{scenario}: {name} 与 HEC 基线不一致",
                    )
                dev = {
                    v: float(np.nanmax(np.abs(base[k] - ref[v].values.astype(np.float64))))
                    for k, v in (("r", "r"), ("p_value", "p_value"), ("reduction", "reduction"),
                                 ("posterior_mean", "posterior_mean"),
                                 ("posterior_std", "posterior_std"), ("prior_mean", "prior_mean"))
                }
            meta[f"selftest_maxdiff_{scenario}"] = "; ".join(f"{k}={v:.2e}" for k, v in dev.items())
            log("  基线自检 max|Δ|: " + ", ".join(f"{k}={v:.1e}" for k, v in dev.items()))

        # ---- 逐算例 ----
        def pack(res: dict) -> np.ndarray:
            return np.stack([res["r"], res["p_value"], res["reduction"], res["bias"],
                             res["prior_mean"], res["prior_std"], res["posterior_mean"],
                             res["posterior_std"], res["n_models"]]).astype(np.float32)

        fields: dict[str, np.ndarray] = {"ALL": pack(base)}
        for c in cases:
            if c["case"] == "ALL":
                continue
            fields[c["case"]] = pack(
                hec_subset(X, Y, obs_mean, obs_sigma_eff, c["keep"])
            )

        var_names = ["r", "p_value", "reduction", "bias", "prior_mean", "prior_std",
                     "posterior_mean", "posterior_std", "n_models"]
        arr = np.stack([fields[c["case"]] for c in cases])
        ds_out = xr.Dataset(
            {v: (("case", "lat", "lon"), arr[:, i]) for i, v in enumerate(var_names)},
            coords={"case": case_names, "lat": lat, "lon": lon},
            attrs={
                "scenario": scenario,
                "history_period": "1981-2010",
                "future_period": "2021-2050",
                "history_indicator": HIST_INDICATOR,
                "future_indicator": FUTURE_INDICATOR,
                "note": "HEC diagnostics recomputed for each leave-one-model/family-out subset",
            },
        )
        enc = {v: {"zlib": True, "complevel": 4, "dtype": "float32"} for v in var_names}
        out_nc = DATA_DIR / f"robustness_{scenario}.nc"
        ds_out.to_netcdf(out_nc, encoding=enc)
        ds_out.close()
        log(f"  已保存 {out_nc.name} ({out_nc.stat().st_size / 1e6:.1f} MB)")

        b = fields["ALL"]
        base_sig = significance_mask(b[0], b[1])
        base_cls = class_index(b[2], REDUCTION_BOUNDS)
        base_sign = np.sign(b[3])

        # ---- 区域统计 ----
        for c in cases:
            f = fields[c["case"]]
            for rname in REGION_ORDER:
                m = region_masks.get(rname)
                if m is None:
                    continue
                n_ok = int((m & np.isfinite(f[0])).sum())
                sig = significance_mask(f[0], f[1]) & m
                denom = m & np.isfinite(f[0]) & np.isfinite(f[1])
                denom_w = float(np.nansum(w2d * denom))
                region_rows.append({
                    "Scenario": SCENARIO_LABELS[scenario],
                    "scenario": scenario,
                    "Case": c["case"],
                    "Group": c["group"],
                    "Label": c["label"],
                    "n_models": len(c["keep"]),
                    "Excluded": ",".join(c["excluded"]),
                    "Region": rname,


                    "r_mean": weighted_mean(f[0], m & sig, w2d),
                    "reduction_mean": weighted_mean(f[2], m & sig, w2d),
                    "bias_mean": weighted_mean(f[3], m & sig, w2d),
                    "sig_frac": float(np.nansum(w2d * sig) / denom_w) if denom_w > 0 else np.nan,
                    "sig_frac_unw": float(sig.sum() / n_ok) if n_ok else np.nan,
                    "n_valid": n_ok,
                })

        # ---- 空间型相似度 ----
        for c in cases:
            f = fields[c["case"]]
            ok = np.isfinite(b[0]) & np.isfinite(f[0])
            okr = np.isfinite(b[2]) & np.isfinite(f[2])
            dr = f[0][ok] - b[0][ok]
            drd = f[2][okr] - b[2][okr]
            f_sig = significance_mask(f[0], f[1])
            f_cls = class_index(f[2], REDUCTION_BOUNDS)
            sim_rows.append({
                "Scenario": SCENARIO_LABELS[scenario],
                "scenario": scenario,
                "Case": c["case"],
                "Group": c["group"],
                "Label": c["label"],
                "n_models": len(c["keep"]),
                "Excluded": ",".join(c["excluded"]),
                "pattern_corr_r": float(np.corrcoef(f[0][ok], b[0][ok])[0, 1]) if ok.sum() > 2 else np.nan,
                "pattern_corr_reduction": float(np.corrcoef(f[2][okr], b[2][okr])[0, 1]) if okr.sum() > 2 else np.nan,
                "rmsd_r": float(np.sqrt(np.mean(dr ** 2))) if dr.size else np.nan,
                "max_abs_dev_r": float(np.max(np.abs(dr))) if dr.size else np.nan,
                "rmsd_reduction": float(np.sqrt(np.mean(drd ** 2))) if drd.size else np.nan,
                "max_abs_dev_reduction": float(np.max(np.abs(drd))) if drd.size else np.nan,
                "sig_change_frac": float(np.mean(f_sig[ok] != base_sig[ok])) if ok.sum() else np.nan,
                "sig_lost_frac": float(np.mean(base_sig[ok] & ~f_sig[ok])) if ok.sum() else np.nan,
                "sig_gained_frac": float(np.mean(~base_sig[ok] & f_sig[ok])) if ok.sum() else np.nan,
                "reduction_class_change_frac": float(np.mean(f_cls[okr] != base_cls[okr])) if okr.sum() else np.nan,
                "bias_sign_change_frac": float(np.mean(np.sign(f[3])[ok] != base_sign[ok])) if ok.sum() else np.nan,
                # 阈值口径的偏离比例（比"分级变类"更直观，不受分级边界疏密影响）
                "r_dev_gt005_frac": float(np.mean(np.abs(dr) > 0.05)) if dr.size else np.nan,
                "r_dev_gt01_frac": float(np.mean(np.abs(dr) > 0.10)) if dr.size else np.nan,
                "r_dev_gt02_frac": float(np.mean(np.abs(dr) > 0.20)) if dr.size else np.nan,
                "reduction_dev_gt2pp_frac": float(np.mean(np.abs(drd) > 0.02)) if drd.size else np.nan,
                "reduction_dev_gt5pp_frac": float(np.mean(np.abs(drd) > 0.05)) if drd.size else np.nan,
                "reduction_dev_gt10pp_frac": float(np.mean(np.abs(drd) > 0.10)) if drd.size else np.nan,
                # China 全域同样限定在有效格点（各自集合自己的判据），与 (a) 面板一致
                "china_r_mean": weighted_mean(f[0], region_masks["China"] & f_sig, w2d),
                "china_reduction_mean": weighted_mean(f[2], region_masks["China"] & f_sig, w2d),
                "delta_china_r_mean": float(weighted_mean(f[0], region_masks["China"] & f_sig, w2d)
                                            - weighted_mean(b[0], region_masks["China"] & base_sig, w2d)),
                "delta_china_reduction_mean": float(weighted_mean(f[2], region_masks["China"] & f_sig, w2d)
                                                    - weighted_mean(b[2], region_masks["China"] & base_sig, w2d)),
            })

    # ---------------- 汇总：剔除敏感性 ----------------
    df_region = pd.DataFrame(region_rows)
    df_sim = pd.DataFrame(sim_rows)
    excl = df_region[df_region["Group"] != "Baseline"]

    spread_rows = []
    for scen_lab in df_region["Scenario"].drop_duplicates():
        g_scen = df_region[df_region["Scenario"] == scen_lab]
        g_ex = excl[excl["Scenario"] == scen_lab]
        for rname in REGION_ORDER:
            gb = g_scen[g_scen["Region"] == rname]
            ge = g_ex[g_ex["Region"] == rname]
            if gb.empty or ge.empty:
                continue
            for metric in ("r_mean", "reduction_mean", "bias_mean", "sig_frac"):
                bval = float(gb[metric].iloc[0])
                vals = ge[metric].to_numpy(dtype=float)
                i_min, i_max = int(np.nanargmin(vals)), int(np.nanargmax(vals))
                spread_rows.append({
                    "Scenario": scen_lab, "Region": rname, "Metric": metric,
                    "baseline": bval,
                    "excl_min": float(vals[i_min]), "excl_max": float(vals[i_max]),
                    "excl_mean": float(np.nanmean(vals)), "excl_std": float(np.nanstd(vals, ddof=1)),
                    "max_abs_dev": float(np.nanmax(np.abs(vals - bval))),
                    "range": float(vals[i_max] - vals[i_min]),
                    "rel_change_pct": float(np.nanmax(np.abs(vals - bval)) / abs(bval) * 100) if bval else np.nan,
                    "case_at_min": str(ge["Case"].to_numpy()[i_min]),
                    "case_at_max": str(ge["Case"].to_numpy()[i_max]),
                })
    df_spread = pd.DataFrame(spread_rows)

    for df, name in ((df_region, "case_region_stats.csv"),
                     (df_sim, "map_similarity.csv"),
                     (df_spread, "spread_vs_baseline.csv")):
        fp = DATA_DIR / name
        df.to_csv(fp, index=False, encoding="utf-8-sig")
        log(f"已保存 {name}: {len(df)} 行")

    pd.DataFrame([{"key": k, "value": v} for k, v in meta.items()]).to_csv(
        DATA_DIR / "run_meta.csv", index=False, encoding="utf-8-sig")

    # ---------------- 控制台摘要 ----------------
    log("=" * 78)
    log("全国（China）尺度：剔除单个模式/家族后 r 与不确定性缩减的变化幅度")
    log("=" * 78)
    cn = df_spread[df_spread["Region"] == "China"]
    for _, row in cn.iterrows():
        log(f"  {row['Scenario']:9s} {row['Metric']:16s} baseline={row['baseline']:.4f} "
            f"[{row['excl_min']:.4f}, {row['excl_max']:.4f}] "
            f"max|Δ|={row['max_abs_dev']:.4f} ({row['rel_change_pct']:.2f}%)")
    log("-" * 78)
    worst = df_sim[df_sim["Group"] != "Baseline"].nlargest(6, "max_abs_dev_r")
    log("对 r 空间场影响最大的 6 个剔除算例：")
    for _, row in worst.iterrows():
        log(f"  {row['Scenario']:9s} {row['Case']:24s} max|Δr|={row['max_abs_dev_r']:.4f} "
            f"rmsd={row['rmsd_r']:.4f} 变类={row['sig_change_frac'] * 100:.3f}%")
    return 0


# ==================================================================
# 9. 出图：龙卷风图（原 02_make_figures.py）
# ==================================================================

# ---- 图 R3 所需：cm 换算（配色取自模块常量 SCENARIO_COLORS）----
CM = 1.0 / 2.54


def figure_r3():
    FIG_DIR.mkdir(parents=True, exist_ok=True)
    sim = pd.read_csv(DATA_DIR / "map_similarity.csv")


    sim = sim[(sim["Group"] != "Baseline") & (sim["Group"] != "Sensitivity")].copy()


    _ord = sim[sim["scenario"] == "ssp245"].copy()
    _ord["_fam"] = _ord["Group"].eq("LOFO").astype(int)
    order = _ord.sort_values(["_fam", "delta_china_r_mean"])["Case"].tolist()
    ypos = {c: i for i, c in enumerate(order)}
    meta = sim.drop_duplicates("Case").set_index("Case")
    groups = meta["Group"].to_dict()
    nmodel = meta["n_models"].to_dict()

    # 画布加高：顶部要放"三个子标题 + 图例"两行（原 10.6 cm 高度只够一行图例在底部）
    fig, axes = plt.subplots(1, 3, figsize=(17.0 * CM * 1.62, 11.8 * CM * 1.62), sharey=True)


    PANEL_FS = 16.5
    LEGEND_FS = 12.5     # 图例字号
    # 图例顶边与子标题底边的间距（点）：沿用原「整图标题 ↔ 图例」实测的 5.2 pt
    TITLE_GAP_PT = 5.2


    panels = [("delta_china_r_mean", "(a) \u0394 mean correlation r", 0.025, 1.0, 0.02),
              ("delta_china_reduction_mean", "(b) \u0394 uncertainty reduction (%)", 2.5, 100.0, 1.0),
              ("rmsd_r", "(c) RMSD of the r field (%)", 6.0, 100.0, 2.0)]
    for ax, (col, xlabel, xlim, scale, tick_step) in zip(axes, panels):
        for c, yv in ypos.items():
            if groups[c] in ("LOFO", "Sensitivity"):
                ax.axhspan(yv - 0.5, yv + 0.5, color="#f2c14e", alpha=0.22, zorder=0)
        for s in SCENARIOS:
            sub = sim[sim["scenario"] == s]
            y = [ypos[c] for c in sub["Case"]]
            ax.plot(sub[col].values * scale, y, "o", ms=4.4, mfc=SCENARIO_COLORS[s],
                    mec="white", mew=0.5, alpha=0.95)
        ax.axvline(0, color="k", lw=0.9)
        ax.set_xlim(-xlim, xlim)
        # 坐标字号放大到 12.5 后 matplotlib 会自动减少刻度，这里显式指定步长以保持刻度密度
        ax.xaxis.set_major_locator(MultipleLocator(tick_step))
        ax.grid(axis="x", ls=":", lw=0.5, alpha=0.6)
        # 子标题改画在图例之上（figure 级文字，见下方 _sub_texts），因此不再用 ax.set_title
        ax.tick_params(labelsize=12.5)   # 横纵坐标字号：10.5 → 放大 2 号
        ax.set_ylim(len(order) - 0.5, -0.5)

    axes[0].set_yticks(range(len(order)))


    _labels = []
    for c in order:
        _name = FAMILY_LABELS.get(c.replace("LOFO_", ""), c.replace("LOMO_", ""))
        _labels.append(f"{_name}  (n={int(nmodel[c])})")
    axes[0].set_yticklabels(_labels, fontsize=12.5)   # 23 行标签：10.5 → 放大 2 号


    fig.tight_layout(rect=(0, 0, 1, 0.895))

    # 三个子标题（(a)(b)(c)）各自居中于自己的面板跨度，置于最上一行
    _span_l = axes[0].get_position().x0
    _span_r = axes[-1].get_position().x1
    _sub_texts = []
    for _ax, (_col, _lab, *_rest) in zip(axes, panels):
        _cx = (_ax.get_position().x0 + _ax.get_position().x1) / 2.0
        _sub_texts.append(fig.text(_cx, 0.985, _lab, ha="center", va="top", fontsize=PANEL_FS))
    print(f"  子标题居中于面板跨度 [ {_span_l:.3f}, {_span_r:.3f} ]，字号 {PANEL_FS:.1f} pt"
          f"（已去掉整图标题）")
    # 图例顶边：由子标题版面盒底边下移 TITLE_GAP_PT 点实时算出（不写死数值，
    # 这样字号再变时"子标题 ↔ 图例"的间距保持不变）
    fig.canvas.draw()
    _sub_bottom = min(t.get_window_extent().y0 for t in _sub_texts)
    LEGEND_TOP = (_sub_bottom - TITLE_GAP_PT / 72.0 * fig.dpi) / fig.bbox.height


    _s = list(SCENARIOS)                       # ("ssp126", "ssp245", "ssp585")
    _order = [_s[0], _s[1], _s[2]]
    _labels = [SCENARIO_LABELS[s] for s in _order] + ["leave-one-family-out"]
    _fam_label = _labels[3]

    def _mk_line(_scen, _lab):
        return Line2D([], [], marker="o", ls="none", mfc=SCENARIO_COLORS[_scen],
                      mec="white", mew=0.5, ms=6, label=_lab)

    def _mk_fam(_lab):
        return Patch(facecolor="#f2c14e", alpha=0.35, edgecolor="none", label=_lab)

    _cx = (_span_l + _span_r) / 2.0
    _leg = fig.legend(handles=[_mk_line(_order[0], _labels[0]),
                               _mk_line(_order[1], _labels[1]),
                               _mk_line(_order[2], _labels[2]),
                               _mk_fam(_fam_label)],
                      loc="upper center", ncol=4, fontsize=LEGEND_FS,
                      frameon=False, bbox_to_anchor=(_cx, LEGEND_TOP),
                      borderaxespad=0, handletextpad=0.5, columnspacing=1.6)
    fig.canvas.draw()
    _bb = _leg.get_window_extent()
    _span_w = (_span_r - _span_l) * fig.bbox.width
    print(f"  图例：单行 4 项、无边框，水平居中于面板跨度 x = {_cx:.3f}，"
          f"宽 {_bb.width / fig.bbox.width:.3f} 画布宽（跨度 {_span_r - _span_l:.3f}）"
          + ("，超出跨度！" if _bb.width > _span_w else "")
          + f"；框顶边 y = {LEGEND_TOP:.4f}（在子标题盒底边下 {TITLE_GAP_PT:.1f} pt）")
    _ax_top = max(ax.get_position().y1 for ax in axes)
    print(f"  图例底边 y = {_bb.y0 / fig.bbox.height:.4f}，面板顶边 y = {_ax_top:.4f}，"
          f"净距 {(_bb.y0 / fig.bbox.height - _ax_top) * fig.bbox.height / fig.dpi:.3f} in")

    out = FIG_DIR / "Fig6.jpg"
    fig.savefig(out, dpi=400, bbox_inches="tight")
    plt.close(fig)
    print(f"  saved {out.name}")


# ==================================================================
# 图 R4：区域尺度参照值与剔除区间（未实现，保留分区标题）
# ==================================================================


def make_figures() -> int:
    """出图入口：目前只有图 R3（正文 Fig.6 的龙卷风图）。"""
    print("生成图件 ...")
    figure_r3()
    print("完成。")
    return 0


# ==================================================================
# 10. 自检（原 03_selftest.py）
#     在做「排除若干模式后重算 Fig. 5」之前，必须先确认本次使用的子集解算器
#     **与论文 pipeline/6 的存档结果逐位一致**，否则稳健性结论无从谈起。
#
#     T1  向量化 HEC 子集解算器 vs 存档的 Output/EC/China 基线（r / p / reduction /
#         prior_mean / prior_std / posterior_mean / posterior_std）
#     T2  显著性掩膜与有效格点掩膜逐格点一致
#     T3  随机合成场上，向量化相关系数与 p 值 vs scipy.stats.linregress
#     T4  留一算例的集合大小 n 恒为 18（LOFO_G2_CESM 为 15）
#     T5  面积加权平均统计量 vs pipeline/6 存档值
#     T6  reduction 与 (r, SNR) 的解析关系  reduction = 1 − sqrt(1 − r²/(1+SNR⁻¹))
# ==================================================================
SELFTEST_FAIL = 0


def check(name: str, ok: bool, detail: str = "") -> None:
    global SELFTEST_FAIL
    tag = "PASS" if ok else "FAIL"
    if not ok:
        SELFTEST_FAIL += 1
    print(f"  [{tag}] {name}" + (f"  {detail}" if detail else ""))


def run_selftest() -> int:
    global SELFTEST_FAIL
    SELFTEST_FAIL = 0
    print("=" * 74)
    print("模式稳健性检查 —— 自检")
    print("=" * 74)

    lat, lon = target_grid()
    w2d = area_weights(lat)
    obs_mean, obs_sigma_raw, obs_sigma_eff = load_observation_layer(lat, lon)
    print(f"目标网格 {lat.size} x {lon.size}；观测层有效格点 "
          f"{int(np.isfinite(obs_mean).sum())}")

    # ---------------- T1 / T2：与存档基线逐位一致 ----------------
    print("\nT1/T2  与 Output/EC/China 存档基线比对")
    for scenario in SCENARIOS:
        ref_fp = HEC_BASELINE_FILE[scenario]
        if not ref_fp.exists():
            check(f"{scenario}: 存档基线存在", False, str(ref_fp))
            continue
        _, X, Y = load_model_fields(scenario, lat, lon)
        res = hec_subset(X, Y, obs_mean, obs_sigma_eff, list(range(X.shape[0])))
        with xr.open_dataset(ref_fp) as ref:
            for key, vname in (("r", "r"), ("p_value", "p_value"),
                               ("reduction", "reduction"),
                               ("prior_mean", "prior_mean"), ("prior_std", "prior_std"),
                               ("posterior_mean", "posterior_mean"),
                               ("posterior_std", "posterior_std")):
                d = float(np.nanmax(np.abs(res[key] - ref[vname].values.astype(np.float64))))
                check(f"{scenario} {vname} max|Δ|", d < TOL, f"{d:.2e}")
            mask_ok = np.array_equal(np.isfinite(res["r"]), np.isfinite(ref["r"].values))
            check(f"{scenario} 有效格点掩膜一致", mask_ok)

    # ---------------- T3：合成场上与 linregress 对比 ----------------
    print("\nT3  合成场：向量化解算 vs scipy.stats.linregress")
    rng = np.random.default_rng(20260917)
    n_mode, n_lat, n_lon = 19, 12, 15
    Xs = rng.normal(size=(n_mode, n_lat, n_lon))
    Ys = 0.8 * Xs + rng.normal(size=(n_mode, n_lat, n_lon))
    om = np.full((n_lat, n_lon), 0.0) + 0.3
    osig = np.full((n_lat, n_lon), 0.4)
    res = hec_subset(Xs, Ys, om, osig, list(range(n_mode)))
    r_ref = np.full((n_lat, n_lon), np.nan)
    p_ref = np.full((n_lat, n_lon), np.nan)
    for i in range(n_lat):
        for j in range(n_lon):
            lr = _st.linregress(Xs[:, i, j], Ys[:, i, j])
            r_ref[i, j] = lr.rvalue
            p_ref[i, j] = lr.pvalue
    check("r 与 linregress 一致", float(np.nanmax(np.abs(res["r"] - r_ref))) < 1e-12,
          f"max|Δ|={float(np.nanmax(np.abs(res['r'] - r_ref))):.2e}")
    check("p 与 linregress 一致", float(np.nanmax(np.abs(res["p_value"] - p_ref))) < 1e-12,
          f"max|Δ|={float(np.nanmax(np.abs(res['p_value'] - p_ref))):.2e}")

    # ---------------- T4：集合大小 ----------------
    print("\nT4  剔除算例的集合大小")
    cases = build_cases()
    for c in cases:
        n_keep = len(c["keep"])
        expect = 19 - len(c["excluded"])
        check(f"{c['case']:22s} n={n_keep}", n_keep == expect, f"expect {expect}")
    n_cases = len(cases)
    check("算例总数 = 25 (1 + 19 + 4 + 1)", n_cases == 25, f"实际 {n_cases}")

    # ---------------- T5：面积加权统计量 ----------------
    print("\nT5  面积加权平均统计量 vs 存档")
    for scenario in SCENARIOS:
        ref_fp = HEC_BASELINE_FILE[scenario]
        if not ref_fp.exists():
            continue
        _, X, Y = load_model_fields(scenario, lat, lon)
        res = hec_subset(X, Y, obs_mean, obs_sigma_eff, list(range(X.shape[0])))
        with xr.open_dataset(ref_fp) as ref:
            for key, vname in (("r", "r"), ("reduction", "reduction")):
                mine = weighted_mean(res[key], np.ones_like(res[key], dtype=bool), w2d)
                theirs = weighted_mean(ref[vname].values.astype(np.float64),
                                       np.ones_like(res[key], dtype=bool), w2d)
                check(f"{scenario} 面积加权 {vname}", abs(mine - theirs) < TOL,
                      f"{mine:.6f} vs {theirs:.6f}")

    # ---------------- T6：reduction 的解析关系 ----------------
    print("\nT6  reduction = 1 − sqrt(1 − r²/(1+SNR⁻¹))")
    _, X, Y = load_model_fields("ssp245", lat, lon)
    res = hec_subset(X, Y, obs_mean, obs_sigma_eff, list(range(X.shape[0])))
    sx = res["prior_std"]
    with np.errstate(invalid="ignore", divide="ignore"):
        snr = (np.nanstd(X, axis=0, ddof=1) ** 2) / obs_sigma_eff ** 2
        red_analytic = 1.0 - np.sqrt(1.0 - res["r"] ** 2 / (1.0 + 1.0 / snr))
    d = float(np.nanmax(np.abs(res["reduction"] - red_analytic)))
    check("解析关系成立", d < 1e-10, f"max|Δ|={d:.2e}")

    print("\n" + "=" * 74)
    if SELFTEST_FAIL == 0:
        print("全部自检通过。子集解算器与论文 pipeline/6 逐位一致，可用于剔除试验。")
    else:
        print(f"存在 {SELFTEST_FAIL} 项失败，请先修复再解释稳健性结果。")
    print("=" * 74)
    return 1 if SELFTEST_FAIL else 0


# ==================================================================
# 11. 命令行入口
# ==================================================================
def build_parser() -> argparse.ArgumentParser:
    ap = argparse.ArgumentParser(
        description="排除单模式/模式家族后的逐格点稳健性检查与出图（单文件管线）",
    )
    ap.add_argument("--selftest", action="store_true",
                    help="只运行自检 T1–T6（约 15 秒），不做稳健性计算、不出图")
    ap.add_argument("--force-regrid", action="store_true",
                    help="忽略重网格缓存，重新计算")
    ap.add_argument("--scenarios", nargs="*", default=list(SCENARIOS),
                    help=f"要跑的情景，默认全部：{' '.join(SCENARIOS)}")
    return ap


def main(argv: Sequence[str] | None = None) -> int:
    """默认流程：先做稳健性检查（25 算例 × 3 情景），再出 Fig6.jpg。"""
    args = build_parser().parse_args(argv)

    if args.selftest:
        return run_selftest()

    rc = run_robustness_check(force_regrid=args.force_regrid, scenarios=args.scenarios)
    if rc != 0:
        return rc
    return make_figures()


if __name__ == "__main__":
    sys.exit(main())
