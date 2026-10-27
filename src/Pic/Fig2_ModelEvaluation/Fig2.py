
from __future__ import annotations

import argparse
import json
import os
import shutil
import uuid
from pathlib import Path
from typing import Any, Dict, List, Tuple, cast

import numpy as np
import pandas as pd
import xarray as xr
import matplotlib.pyplot as plt
import cartopy.crs as ccrs
import shapefile
from shapely.geometry import shape as shapely_shape
from matplotlib.colors import BoundaryNorm, LinearSegmentedColormap
from matplotlib.figure import Figure
from matplotlib.ticker import FuncFormatter
from scipy.special import stdtr
from scipy.stats import ttest_1samp
import warnings

warnings.filterwarnings("ignore")

plt.rcParams["font.family"] = "Times New Roman"
plt.rcParams["mathtext.fontset"] = "cm"
plt.rcParams["axes.unicode_minus"] = False


DATA_DIR = Path(__file__).parent / "data"
MODEL_FILE = DATA_DIR / "MULTI_MODEL-historical-1981-2010.nc"
OBS_FILE = DATA_DIR / "CN05-OBS-1981-2010.nc"
FIG_DIR = Path(__file__).parent
# 图 2 固定保留相关系数与偏差两行。
PANEL_KEYS = ("corr", "bias")
# 论文成品图（散点面板）的文件名固定为 Fig2.jpg：模块根目录下不再产生
# Fig2a.jpg / Fig2b.jpg 等中间图片；原 Fig2a.py 的 FIG2_OUT 环境变量随之移除。
PAPER_FIG_NAME = "Fig2.jpg"
REPO_ROOT = next(p for p in Path(__file__).resolve().parents if (p / "src").is_dir())


DATA_ROOT = Path(__file__).resolve().parent / "data" / "geography"
SHP_PATH = DATA_ROOT / "China" / "cnmap.shp"

EVAL_START_YEAR = 1981
EVAL_END_YEAR = 2010

TARGET_METRICS = {
    "PrecipVar": {"label": "Precip Var", "unit": "mm/day"},
    "R95mm_intensity": {"label": "R95 Intensity", "unit": "mm/day"},
}

# ==================== 散点图参数（独立设置，均已标注含义） ====================
SCATTER_PARAMS = {
    # ---------- 字体字号 (pt) ----------
    "font_label": 13,           # 纵轴标签（CORR / Bias）
    "font_tick": 12,            # 刻度标签
    "font_annot": 12,           # 均值统计标注文字
    # ---------- 标记与线型 ----------
    "marker_size": 22,          # 散点标记面积 (pt²)
    "line_width": 0.6,          # 参考虚线线宽 (pt)
    "spine_width": 0.6,         # 坐标轴框线宽 (pt)
    # ---------- 子图布局 ----------
    "n_panels": 2,              # 散点子图行数（CORR / Bias）
    "hspace": 0.12,             # 子图纵向间距 (figure 相对)
    "left": 0.14,               #左侧边距
    "right": 0.96,              #右侧边距
}

# ==================== 空间图参数 ====================
MAP_PARAMS = {
    # ---------- 字体字号 (pt) ----------
    "font_title": 14,           # 地图子图标题（CN05.1 / HiCPC MME）
    "font_tick": 10,            # 经纬度刻度标签
    "font_stat": 12,            # 地图下方统计指标（CORR/NRMSE）
    "font_cbar": 11,            # 色带标签
    "font_row_label": 14,       # 行标签（Precip Var / R95 Intensity）
    # ---------- 线宽 (pt) ----------
    "line_grid": 0.3,           # 经纬网格线
    "line_boundary": 0.5,       # 中国国界线
    "line_contour": 0.4,        # 等值线
    # ---------- 统计/色带偏移 ----------
    "stat_offset": 0.050,       # 统计文字距 axes 底部偏移
    "cbar_offset": 0.095,       # 色带距 axes 底部偏移
    "cbar_w_ratio": 0.8,        # 色带宽度 / 两列地图总宽
    "cbar_h": 0.020,            # 色带高度 (figure 相对)
}


# ==================== 工具函数（两个面板共用） ====================
def get_common_years(model_ds: xr.Dataset, obs_ds: xr.Dataset) -> np.ndarray:
    model_years = np.asarray(model_ds["year"].values, dtype=np.int32)
    obs_years = np.asarray(obs_ds["year"].values, dtype=np.int32)
    common = np.intersect1d(model_years, obs_years)
    if common.size == 0:
        raise ValueError("两份数据没有共同年份")
    if EVAL_START_YEAR is not None:
        common = common[common >= int(EVAL_START_YEAR)]
    if EVAL_END_YEAR is not None:
        common = common[common <= int(EVAL_END_YEAR)]
    if common.size == 0:
        raise ValueError("按配置筛选后没有可评估年份")
    return common


def get_scenario_from_filename(fp: Path) -> str:
    parts = fp.stem.split("-")
    for p in parts:
        pl = p.lower()
        if pl.startswith("ssp") or pl == "historical":
            return pl
    return "unknown"


def load_model_dataset_from_file(fp: Path) -> xr.Dataset:
    ds = xr.open_dataset(fp)
    file_ssp = get_scenario_from_filename(fp)

    if "case" not in ds.dims:
        if "Mode" in ds.dims:
            if "Mode" in ds.coords:
                mode_vals = [str(v) for v in ds["Mode"].values]
            else:
                mode_vals = [f"Mode{i + 1}" for i in range(ds.sizes["Mode"])]
            case_vals = [f"{m}-{file_ssp}" for m in mode_vals]
            ds = ds.rename({"Mode": "case"})
            ds = ds.assign_coords(
                {"case": ("case", np.asarray(case_vals, dtype=object)),
                 "Mode": ("case", np.asarray(mode_vals, dtype=object))}
            )
        else:
            raise ValueError(f"文件缺少 case/Mode 维度，无法处理: {fp}")
    elif "Mode" not in ds.coords:
        mode_vals = [str(v).split("-ssp")[0] for v in ds["case"].values]
        ds = ds.assign_coords({"Mode": ("case", np.asarray(mode_vals, dtype=object))})

    if "SSP" not in ds.coords:
        ds = ds.assign_coords({"SSP": ("case", np.array([file_ssp] * ds.sizes["case"], dtype=object))})
    if "source_file" not in ds.coords:
        ds = ds.assign_coords({"source_file": ("case", np.array([fp.name] * ds.sizes["case"], dtype=object))})
    ds = ds.assign_attrs({**ds.attrs, "model_source_file": str(fp)})
    return ds


def _cell_bounds_from_centers(coord_1d: np.ndarray) -> Tuple[np.ndarray, np.ndarray]:
    if coord_1d.ndim != 1:
        raise ValueError("坐标必须是一维")
    if coord_1d.size < 2:
        raise ValueError("坐标点数量不足")
    mid = 0.5 * (coord_1d[:-1] + coord_1d[1:])
    lower = np.empty_like(coord_1d, dtype=np.float64)
    upper = np.empty_like(coord_1d, dtype=np.float64)
    lower[1:] = mid
    upper[:-1] = mid
    lower[0] = coord_1d[0] - 0.5 * (coord_1d[1] - coord_1d[0])
    upper[-1] = coord_1d[-1] + 0.5 * (coord_1d[-1] - coord_1d[-2])
    return lower, upper


def _build_overlap_matrix(src_coord: np.ndarray, dst_coord: np.ndarray) -> np.ndarray:
    src_low, src_up = _cell_bounds_from_centers(src_coord)
    dst_low, dst_up = _cell_bounds_from_centers(dst_coord)
    left = np.maximum(dst_low[:, None], src_low[None, :])
    right = np.minimum(dst_up[:, None], src_up[None, :])
    return np.maximum(0.0, right - left).astype(np.float64)


def _area_weighted_remap_numpy(
    src_data: np.ndarray, lat_overlap: np.ndarray, lon_overlap: np.ndarray, src_lat_cos: np.ndarray,
) -> np.ndarray:
    src = np.asarray(src_data, dtype=np.float64)
    valid_mask = np.isfinite(src).astype(np.float64)
    lat_w = lat_overlap * src_lat_cos[None, :]
    tmp_num = np.einsum("aj,...ji->...ai", lat_w, np.where(np.isfinite(src), src, 0.0), optimize=True)
    tmp_den = np.einsum("aj,...ji->...ai", lat_w, valid_mask, optimize=True)
    num = np.einsum("bi,...ai->...ab", lon_overlap, tmp_num, optimize=True)
    den = np.einsum("bi,...ai->...ab", lon_overlap, tmp_den, optimize=True)
    return np.divide(num, den, out=np.full_like(num, np.nan), where=den > 0)


def area_weighted_remap_da_to_obs_grid(model_da: xr.DataArray, obs_da: xr.DataArray) -> xr.DataArray:
    src = model_da.sortby("lat").sortby("lon")
    dst_lat = np.asarray(obs_da["lat"].values, dtype=np.float64)
    dst_lon = np.asarray(obs_da["lon"].values, dtype=np.float64)
    src_lat = np.asarray(src["lat"].values, dtype=np.float64)
    src_lon = np.asarray(src["lon"].values, dtype=np.float64)
    lat_overlap = _build_overlap_matrix(src_lat, dst_lat)
    lon_overlap = _build_overlap_matrix(src_lon, dst_lon)
    src_lat_cos = np.clip(np.cos(np.deg2rad(src_lat)), 0.0, None)
    src_transposed = src.transpose(..., "lat", "lon")
    out_np = _area_weighted_remap_numpy(src_transposed.values, lat_overlap, lon_overlap, src_lat_cos)
    lead_dims = [d for d in src_transposed.dims if d not in {"lat", "lon"}]
    lead_coords = {d: src_transposed[d] for d in lead_dims}
    return xr.DataArray(
        out_np, dims=lead_dims + ["lat", "lon"],
        coords={**lead_coords, "lat": obs_da["lat"], "lon": obs_da["lon"]},
        name=src.name, attrs=src.attrs,
    )


def remap_model_to_obs_grid(model_ds: xr.Dataset, obs_ds: xr.Dataset, metric_names: List[str]) -> xr.Dataset:
    remapped = {}
    for name in metric_names:
        remapped[name] = area_weighted_remap_da_to_obs_grid(model_ds[name], obs_ds[name])
    out = xr.Dataset(remapped)
    for coord_name in ["case", "Mode", "SSP", "source_file"]:
        if coord_name in model_ds.coords and coord_name not in out.coords:
            out = out.assign_coords({coord_name: model_ds.coords[coord_name]})
    out.attrs.update(model_ds.attrs)
    return out


def _cos_lat_weights(field: xr.DataArray) -> np.ndarray:
    """构造格点面积权重（等经纬度网格上正比于 cos(lat)）。

    参数:
        field: 二维（lat, lon）场。

    返回:
        与 field 同形状的权重数组。
    """
    if "lat" not in field.coords:
        return np.ones(field.shape, dtype=np.float64)
    lat = np.asarray(field["lat"].values, dtype=np.float64)
    w_lat = np.clip(np.cos(np.deg2rad(lat)), 0.0, None)
    return np.broadcast_to(w_lat[:, None], field.shape).astype(np.float64)


def calc_spatial_metrics(
    model_field: xr.DataArray,
    obs_field: xr.DataArray,
    weights: np.ndarray | None = None,
) -> Dict[str, float]:
    """计算模式场与观测场的空间统计指标（面积加权）。

    权重默认取格点纬度的 cos 值（等经纬度网格上的面积权重），亦可通过 weights 显式传入。
    CORR / Bias / RMSE / NRMSE 使用同一套权重，保证同一幅图内口径一致。

    说明：原 Fig2a.py 与 Fig2b.py 各有一份同名函数，二者只在返回字典是否含
    `rmse` / `nrmse` 上不同（Fig2a 不需要这两项）；合并后统一采用含 RMSE / NRMSE
    的超集版本，散点面板仍然只取 `corr` / `bias`，数值口径完全不变。
    """
    model_flat = model_field.values.reshape(-1)
    obs_flat = obs_field.values.reshape(-1)
    valid = ~(np.isnan(model_flat) | np.isnan(obs_flat))
    model_valid = model_flat[valid].astype(np.float64)
    obs_valid = obs_flat[valid].astype(np.float64)

    nan_result = {"corr": np.nan, "bias": np.nan, "rel_bias": np.nan, "rmse": np.nan, "nrmse": np.nan, "p_value": np.nan, "n_valid": 0}
    if model_valid.size < 5:
        return nan_result

    w_all = _cos_lat_weights(model_field).reshape(-1) if weights is None else np.asarray(weights, dtype=np.float64).reshape(-1)
    w = np.clip(w_all[valid], 0.0, None)
    w_sum = float(w.sum())
    if w_sum <= 0.0:
        return nan_result

    model_mean = float((w * model_valid).sum() / w_sum)
    obs_mean = float((w * obs_valid).sum() / w_sum)
    model_anom = model_valid - model_mean
    obs_anom = obs_valid - obs_mean
    cov = float((w * model_anom * obs_anom).sum() / w_sum)
    var_model = float((w * model_anom ** 2).sum() / w_sum)
    var_obs = float((w * obs_anom ** 2).sum() / w_sum)

    corr_value = np.nan if (var_model <= 0.0 or var_obs <= 0.0) else cov / np.sqrt(var_model * var_obs)
    if not np.isnan(corr_value) and model_valid.size > 2:
        t_stat = corr_value * np.sqrt((model_valid.size - 2) / max(1.0 - corr_value**2, 1e-15))
        p_value = float(2.0 * stdtr(model_valid.size - 2, -abs(t_stat)))
    else:
        p_value = np.nan
    bias = obs_mean - model_mean
    rel_bias = float((bias / obs_mean) * 100) if obs_mean != 0 else np.nan
    rmse = float(np.sqrt((w * (model_valid - obs_valid) ** 2).sum() / w_sum))
    nrmse = float(rmse / abs(obs_mean)) if obs_mean != 0 else np.nan
    return {"corr": corr_value, "bias": bias, "rel_bias": rel_bias, "rmse": rmse, "nrmse": nrmse, "p_value": p_value, "n_valid": int(model_valid.size)}


def ensure_required_vars(ds: xr.Dataset, required_vars: List[str], name: str) -> None:
    """检查数据集中是否包含所需变量，缺失则报错。"""
    missing = [v for v in required_vars if v not in ds]
    if missing:
        raise ValueError(f"{name} 缺少必要变量: {missing}")


def _format_pval(p: float) -> str:
    """格式化为学术风格 p 值字符串。p < 0.001 时不提供精确值，加括号。"""
    if p < 0.001:
        return "(p < 0.001)"
    if p < 0.01:
        return f"p = {p:.3f}"
    if p < 0.05:
        return f"p = {p:.3f}"
    return f"p = {p:.3f}"


# ==================== 散点面板 (a)：绘图函数 ====================
def draw_scatter_panels(axes, mode_names, r95_stats, var_stats, params):
    """在 axes 上绘制散点子图（CORR / Bias）。

    参数由 SCATTER_PARAMS 传入，不与空间图共享。
    """
    x = np.arange(len(mode_names))
    _ALL_SPECS = {"corr": ("CORR", "corr"),
                  "bias": ("Bias (mm/day)", "bias")}
    panel_specs = [_ALL_SPECS[k] for k in PANEL_KEYS]

    for idx, (ax, (ylabel, key)) in enumerate(zip(axes, panel_specs)):
        # 编号放在纵轴左上方，与轴外的均值标注保持同一高度。
        ax.text(-0.14, 1.04, {"corr": "(a)", "bias": "(b)"}[key],
                transform=ax.transAxes, fontsize=params["font_label"],
                ha="left", va="bottom", color="black", clip_on=False)
        y_r95 = np.asarray(r95_stats[key], dtype=np.float64)
        y_var = np.asarray(var_stats[key], dtype=np.float64)

        ax.scatter(x, y_var, c="#99bbef", edgecolors="#2596be",
                   s=params["marker_size"], alpha=0.9, linewidths=0.8,
                   label="Precip Var index", zorder=3, marker="o")
        ax.scatter(x, y_r95, c="#e9542c", edgecolors="#d52813",
                   s=params["marker_size"], alpha=0.9, linewidths=0.8,
                   label="R95 Intensity", zorder=3, marker="o")

        mean_r95 = float(np.nanmean(y_r95))
        mean_var = float(np.nanmean(y_var))
        ax.axhline(mean_r95, color="#d52813", linestyle="--",
                   linewidth=params["line_width"], alpha=0.9)
        ax.axhline(mean_var, color="#2596be", linestyle="--",
                   linewidth=params["line_width"], alpha=0.9)

        # 均值标注（axes 相对坐标，位于轴外上方）
        # 第一行：均值；CORR 面板第二行：p 值
        _annot_size = params["font_annot"]
        _is_corr = (key == "corr")

        ax.text(0.66, 1.04, "●", transform=ax.transAxes,
                fontsize=_annot_size,
                ha="left", va="bottom", color="#2596be", fontweight="normal")
        ax.text(0.685, 1.04, f"Mean Precip Var $= {mean_var:.3f}$",
                transform=ax.transAxes, fontsize=_annot_size,
                ha="left", va="bottom", color="black", fontweight="normal")

        ax.text(0.02, 1.04, "●", transform=ax.transAxes,
                fontsize=_annot_size,
                ha="left", va="bottom", color="#d52813", fontweight="normal")
        ax.text(0.045, 1.04, f"Mean R95 Intensity $= {mean_r95:.3f}$",
                transform=ax.transAxes, fontsize=_annot_size,
                ha="left", va="bottom", color="black", fontweight="normal")

        if _is_corr:
            p_var = float(ttest_1samp(y_var[~np.isnan(y_var)], 0).pvalue) if np.any(~np.isnan(y_var)) else 1.0
            p_r95 = float(ttest_1samp(y_r95[~np.isnan(y_r95)], 0).pvalue) if np.any(~np.isnan(y_r95)) else 1.0
            ax.text(0.84, 1.00, _format_pval(p_var),
                    transform=ax.transAxes, fontsize=_annot_size - 2,
                    ha="center", va="top", color="black", fontweight="normal")
            ax.text(0.21, 1.00, _format_pval(p_r95),
                    transform=ax.transAxes, fontsize=_annot_size - 2,
                    ha="center", va="top", color="black", fontweight="normal")

        ax.set_ylabel(ylabel, fontsize=params["font_label"], fontweight="normal")
        ax.grid(True, axis="y", linestyle="-", color="#d0d0d0", linewidth=0.3, alpha=0.25)
        # 固定宽度格式化 y 轴刻度，确保两行数据区域左对齐
        if key == "corr":
            ax.set_yticks([0.94, 0.96, 0.98])
            ax.set_ylim(0.92, 0.98)
            ax.yaxis.set_major_formatter(FuncFormatter(lambda v, _: f"{v:.2f}"))
        elif key == "bias":
            ax.yaxis.set_major_formatter(FuncFormatter(lambda v, _: f"{v:>5.1f}"))
        ax.tick_params(axis="y", labelsize=params["font_tick"], width=params["spine_width"])
        ax.tick_params(axis="x", width=params["spine_width"], labelsize=params["font_tick"])
        for sp in ax.spines.values():
            sp.set_linewidth(params["spine_width"])
        ax.spines["top"].set_visible(False)
        ax.spines["right"].set_visible(False)
        if idx < len(axes) - 1:      # 只在最后一个面板保留模式名（原写法写死 idx<2，不适用于其它面板数）
            ax.tick_params(axis="x", labelbottom=False)

    for ax in axes:
        ax.set_xlim(-0.5, len(mode_names) - 0.5)
        ax.set_xticks(x)
    axes[-1].set_xticklabels(mode_names, rotation=45, ha="right", va="top",
                             fontsize=params["font_tick"], fontweight="normal")
    axes[-1].set_xlabel("", fontweight="normal")


# ==================== 散点面板 (a)：统计数据落盘 ====================


# ==================== 散点面板 (a)：统计数据 CSV 落盘 ====================
# 指标在 CSV 中的显示名（与论文正文/图例一致）
CSV_METRIC_LABELS = {
    "PrecipVar": "PrecipVar",
    "R95mm_intensity": "R95 Intensity",
}

# (CSV 中的统计量名, metric_results 中的键, 换算系数, 单位)
CSV_STAT_SPECS = [
    ("CORR", "corr", 1.0, "1"),
    ("Bias", "bias", 1.0, "mm/day"),
]


def dump_scatter_stats_csv(
    metric_results: Dict[str, Dict[str, Any]],
    mode_names: List[str],
    out_path: Path,
    per_model_path: Path | None = None,
) -> None:
    """把图 2 的统计数据落盘为 CSV（data/ 目录），便于核对论文数字。

    （合并前为 Fig2a.py 的 `dump_statistics_csv()`，因与 Fig2b.py 的同名函数
    重名而改名。）

    输出两张表：
        1. out_path：长表，一行一个 metric × statistic，给出 19 个模式的
           集合均值（mean）、中位数（median）与参与统计的模式数（n_models）。
           论文正文引用的“19 个模式的均值”即 mean 列。
        2. per_model_path（可选）：宽表，一行一个 mode × metric，
           给出逐模式的 CORR / Bias(mm/day) 明细。

    参数:
        metric_results: metric_results[metric_name] =
                        {"corr": [...], "bias": [...], "unit": str}。
        mode_names: 模式名列表（与 metric_results 中各列表顺序一致）。
        out_path: 汇总 CSV 路径（metric × statistic）。
        per_model_path: 逐模式明细 CSV 路径；为 None 时不输出。

    两处落盘均使用 utf-8-sig 编码，便于 Excel 直接打开且中文/符号不乱码。
    """
    summary_rows: List[Dict[str, Any]] = []
    per_model_rows: List[Dict[str, Any]] = []

    for metric_name, meta in TARGET_METRICS.items():
        r = metric_results[metric_name]
        csv_metric = CSV_METRIC_LABELS.get(metric_name, meta["label"])
        scaled: Dict[str, np.ndarray] = {}

        for stat_label, key, scale, unit in CSV_STAT_SPECS:
            values = np.asarray(r[key], dtype=np.float64) * scale
            scaled[stat_label] = values
            valid = values[~np.isnan(values)]
            summary_rows.append({
                "metric": csv_metric,
                "statistic": stat_label,
                "mean": round(float(np.mean(valid)), 4) if valid.size else np.nan,
                "median": round(float(np.median(valid)), 4) if valid.size else np.nan,
                "n_models": int(valid.size),
                "unit": unit,
                "metric_key": metric_name,
            })

        if per_model_path is not None:
            for i, name in enumerate(mode_names):
                per_model_rows.append({
                    "mode": name,
                    "metric": csv_metric,
                    "CORR": round(float(scaled["CORR"][i]), 4),
                    "Bias_mm_per_day": round(float(scaled["Bias"][i]), 4),
                })

    out_path.parent.mkdir(parents=True, exist_ok=True)
    pd.DataFrame(
        summary_rows,
        columns=["metric", "statistic", "mean", "median", "n_models", "unit", "metric_key"],
    ).to_csv(out_path, index=False, encoding="utf-8-sig")

    if per_model_path is not None:
        per_model_path.parent.mkdir(parents=True, exist_ok=True)
        pd.DataFrame(
            per_model_rows,
            columns=["mode", "metric", "CORR", "Bias_mm_per_day"],
        ).to_csv(per_model_path, index=False, encoding="utf-8-sig")


# ==================== 地图面板 (b)：绘图函数 ====================
def _draw_map_panel(ax, field, levels, cmap, cn_geoms, region, params):
    """单个地图面板（等值线 + 中国边界 + PDF 直方图）。"""
    ax.set_extent([region["lon_min"], region["lon_max"],
                   region["lat_min"], region["lat_max"]])
    # 保持经纬度纵横比（在中心纬度处不变形）
    center_lat = (region["lat_min"] + region["lat_max"]) / 2
    ax.set_aspect(1.0 / np.cos(np.deg2rad(center_lat)), adjustable="box")
    ax.contourf(field.lon, field.lat, field, levels=levels, cmap=cmap, extend="both")
    ax.contour(field.lon, field.lat, field, levels=levels, colors="black", linewidths=params["line_contour"])
    ax.add_geometries(cn_geoms, crs=ccrs.PlateCarree(), facecolor="none", edgecolor="#888888", linewidth=params["line_boundary"])
    gl = ax.gridlines(draw_labels=True, linewidth=params["line_grid"], alpha=0.4, linestyle="--")
    gl.top_labels = False; gl.right_labels = False
    gl.xlabel_style = {"size": params["font_tick"]}; gl.ylabel_style = {"size": params["font_tick"]}
    try:
        ax.spines["geo"].set_visible(False)
    except Exception:
        pass

    fvals = field.values.ravel()
    fvals = fvals[np.isfinite(fvals)]
    if len(fvals) > 0:
        fvals = np.clip(fvals, levels[0], levels[-1])
        counts, _ = np.histogram(fvals, bins=levels)
        n_int = len(levels) - 1
        bc = (levels[:-1] + levels[1:]) / 2
        bin_w = np.diff(levels)
        pdf = counts / (counts.sum() * bin_w)
        from mpl_toolkits.axes_grid1.inset_locator import inset_axes
        # 直方图内嵌轴：宽度 0.56、高度 0.44（均为 axes 相对坐标）
        hist_ax = inset_axes(ax, width=0.56, height=0.44,
                             bbox_to_anchor=(0.18, 0.07),
                             bbox_transform=ax.transAxes, loc="lower left", borderpad=0)
        cmap_obj = plt.get_cmap(cmap)
        for j in range(n_int):
            hist_ax.bar(bc[j], pdf[j], width=bin_w[j] * 0.9,
                        color=cmap_obj(j / (n_int - 1)),
                        edgecolor="black", linewidth=0.3)
        hist_ax.set_xlim(levels[0], levels[-1])
        hist_ax.tick_params(axis="both", length=1.5, labelsize=8, width=0.3)
        hist_ax.set_ylabel("PDF", fontsize=9, labelpad=0)
        hist_ax.set_facecolor("none"); hist_ax.patch.set_alpha(0)
        for sp in hist_ax.spines.values(): sp.set_linewidth(0.3)
        hist_ax.spines["top"].set_visible(False); hist_ax.spines["right"].set_visible(False)


def draw_map_panels(fig: Figure, axes: np.ndarray, spatial_rows: List[Dict[str, Any]],
                    cn_geoms: list, region: Dict[str, float], params: Dict[str, Any]) -> List:
    """在给定 2×2 axes 网格中绘制空间分布图，并添加统计标注和色带。返回色带 axes 列表。"""
    col_titles = ["CN05.1", "HiCPC-MME"]
    cbar_axes = []

    for r, row in enumerate(spatial_rows):
        obs_map = row["obs_map"]
        mme_map = row["mme_map"]
        cmap_main = str(row["cmap_main"])
        label = str(row["label"])

        vmin = float(np.nanmin([obs_map.min().values, mme_map.min().values]))
        vmax = float(np.nanmax([obs_map.max().values, mme_map.max().values]))
        n_intervals = 10 if cmap_main == "r95_cmap" else 8

        # levels 以 0 为中心对称（对跨越 0 的变量），避免色带一侧过大
        if vmin < 0 < vmax:
            bound = max(abs(np.floor(vmin)), abs(np.ceil(vmax)))
            levels = np.round(np.linspace(-bound, bound, n_intervals + 1)).astype(int)
        else:
            # 全正值数据：从数据真实最小值取整开始，避免 0 带来的"蓝色=负值"视觉误导
            vmin_level = max(0.5, np.floor(vmin * 10) / 10)
            vmax_level = np.ceil(vmax * 10) / 10
            levels = np.linspace(vmin_level, vmax_level, n_intervals + 1)
            levels = np.round(levels, 1)
        levels = np.unique(levels)

        for c in range(2):
            field = obs_map if c == 0 else mme_map
            _draw_map_panel(axes[r, c], field, levels, cmap_main, cn_geoms, region, params)
            axes[r, c].axis("off")

        # 行标号不再逐行绘制：图 1(b) 指整幅空间图块，块标号在循环外统一绘制

        axes[r, 0].text(-0.28, 0.5, label, transform=axes[r, 0].transAxes,
                        rotation=90, ha="center", va="center",
                        fontsize=params["font_row_label"], fontweight="normal")

        corr = float(row.get("corr", np.nan))
        p_val = float(row.get("p_value", np.nan))
        nrmse = float(row.get("nrmse", np.nan))   # 仅用于统计数据落盘，图上不再标注
        p_str = f"p<0.0001" if (not np.isnan(p_val) and p_val < 0.0001) else (f"p={p_val:.4f}" if not np.isnan(p_val) else "p=N/A")
        r_y0 = axes[r, 0].get_position().y0
        cx = (axes[r, 0].get_position().x0 + axes[r, 1].get_position().x1) / 2
        fig.text(cx, r_y0 - params["stat_offset"],
                 f"CORR={corr:.3f} ({p_str})",
                 ha="center", va="center", fontsize=params["font_stat"],
                 fontweight="normal", color="black")

        x0 = axes[r, 0].get_position().x0
        x1 = axes[r, 1].get_position().x1
        w = (x1 - x0) * params["cbar_w_ratio"]
        cx = (x0 + x1) / 2
        cax = fig.add_axes((cx - w / 2, r_y0 - params["cbar_offset"], w, params["cbar_h"]))
        norm = BoundaryNorm(levels, ncolors=256, extend="both")
        cbar = fig.colorbar(plt.cm.ScalarMappable(norm=norm, cmap=cmap_main),
                            cax=cax, orientation="horizontal", extend="both",
                            extendfrac=0.04, ticks=levels)
        cbar.ax.xaxis.set_major_formatter(
            FuncFormatter(lambda v, _: f"{v:.0f}" if abs(v - round(v)) < 1e-10 else f"{v:.1f}"))
        cax.set_xlabel(row["unit"], fontsize=params["font_cbar"], labelpad=0)
        cbar_axes.append(cax)

    # 列标题统一放在两行子图的上方（选择顶行 = 最后创建的行）
    top_row = axes.shape[0] - 1
    for c in range(2):
        ax_b = axes[top_row, c].get_position()
        fig.text((ax_b.x0 + ax_b.x1) / 2, ax_b.y1 + 0.03,
                 col_titles[c], ha="center", va="bottom",
                 fontsize=params["font_title"], fontweight="normal")

    # 块标号：图 1(b) 指整幅空间图块，故只在块左上角加一次 (b)
    pos_top = axes[top_row, 0].get_position()
    fig.text(pos_top.x0 - 0.02, pos_top.y1 + 0.02, "(b)",
             fontsize=13, ha="right", va="bottom", fontweight="normal")

    return cbar_axes


# ==================== 地图面板 (b)：统计数据落盘 ====================


def dump_map_stats_csv(rows, out_path, y0, y1) -> None:
    """把图 1(b) 的统计数据写成 CSV（data/ 目录，utf-8-sig 编码）。

    （合并前为 Fig2b.py 的 `dump_statistics_csv()`，因与 Fig2a.py 的同名函数重名而改名。）

    字段:
        metric      : 指标名（Precip Var / R95 Intensity）。
        corr        : MME 与 CN05.1 的空间相关系数（面积加权，w=cos(lat)）。
        p_value     : 该相关系数的显著性 p 值（双侧 t 检验）。
        nrmse_pct   : 归一化均方根误差（%，以观测面积加权均值为分母）。
        bias        : 平均偏差（面积加权，OBS_mean - MME_mean，正值为模式低估）。
        unit        : 物理量单位。
        rmse        : 均方根误差（原单位）。
        obs_mean    : CN05.1 观测的面积加权区域均值。
        mme_mean    : HiCPC-MME 的面积加权区域均值。
        rel_bias_pct: 相对偏差（%，(OBS-MME)/OBS*100）。
        n_valid     : 参与统计的有效格点数。
        period      : 评估时段。

    参数:
        rows: 每个指标一行，含 label / corr / p_value / nrmse / obs_mean_w / mme_mean_w。
        out_path: 输出 CSV 路径。
        y0, y1: 评估时段起止年。
    """
    records = []
    for row in rows:
        obs_mean_w = float(row["obs_mean_w"])
        mme_mean_w = float(row["mme_mean_w"])
        bias = obs_mean_w - mme_mean_w
        rel_bias_pct = (bias / obs_mean_w * 100.0) if obs_mean_w != 0 else np.nan
        records.append({
            "metric": str(row["label"]),
            "corr": round(float(row["corr"]), 6),
            "p_value": float(row["p_value"]),
            "nrmse_pct": round(float(row["nrmse"]) * 100.0, 6),
            "bias": round(bias, 6),
            "unit": str(row["unit"]),
            "rmse": round(float(row["rmse"]), 6) if "rmse" in row else np.nan,
            "obs_mean": round(obs_mean_w, 6),
            "mme_mean": round(mme_mean_w, 6),
            "rel_bias_pct": round(rel_bias_pct, 6),
            "n_valid": int(row["n_valid"]) if "n_valid" in row else np.nan,
            "period": f"{y0}-{y1}",
        })
    df = pd.DataFrame(records)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(out_path, index=False, encoding="utf-8-sig")


# ==================== 数据准备（两个面板共用，先于绘图） ====================
def load_evaluation_data() -> Tuple[xr.Dataset, xr.Dataset, np.ndarray, List[str]]:
    """读取并预处理两个面板共用的评估数据。

    原 Fig2a.py 与 Fig2b.py 的主流程各做了一遍完全相同的读取 + 重网格，
    合并后只做一次（口径不变，省一半 IO/重映射开销）。

    返回:
        (model_sel, obs_sel, common_years, mode_names)
    """
    if not MODEL_FILE.exists():
        raise FileNotFoundError(f"模型文件不存在: {MODEL_FILE}")
    if not OBS_FILE.exists():
        raise FileNotFoundError(f"观测文件不存在: {OBS_FILE}")

    # ---- 加载数据 ----
    scenario = get_scenario_from_filename(MODEL_FILE)
    obs_ds = xr.open_dataset(OBS_FILE)
    model_ds = load_model_dataset_from_file(MODEL_FILE)
    ensure_required_vars(obs_ds, list(TARGET_METRICS.keys()), "观测")
    ensure_required_vars(model_ds, list(TARGET_METRICS.keys()), "模型")

    common_years = get_common_years(model_ds, obs_ds)
    model_sel = model_ds.sel(year=common_years)
    obs_sel = obs_ds.sel(year=common_years)
    model_sel = remap_model_to_obs_grid(model_sel, obs_sel, list(TARGET_METRICS.keys()))

    mode_names = [str(v) for v in model_sel["Mode"].values] if "Mode" in model_sel.coords else \
                 [str(v).split("-ssp")[0] for v in model_sel["case"].values]

    print(f"  情景: {scenario}  年份: {int(common_years.min())}-{int(common_years.max())}  case: {model_sel.sizes['case']}")
    return model_sel, obs_sel, common_years, mode_names


def compute_scatter_metrics(model_sel: xr.Dataset, obs_sel: xr.Dataset) -> Dict[str, Dict[str, Any]]:
    """逐模式（case）计算散点面板所需的 CORR / Bias（原 Fig2a.py 主流程的计算段）。"""
    metric_results: Dict[str, Dict[str, Any]] = {}

    for metric_name, meta in TARGET_METRICS.items():
        label = meta["label"]
        unit = meta["unit"]
        model_var = model_sel[metric_name]
        obs_var = obs_sel[metric_name]

        # 散点数据（逐 case）
        corrs: List[float] = []
        bias_vals: List[float] = []
        for i in range(model_var.sizes["case"]):
            case_field = model_var.isel(case=i).mean(dim="year")
            obs_field = obs_var.mean(dim="year")
            s = calc_spatial_metrics(case_field, obs_field)
            corrs.append(s["corr"])
            bias_vals.append(s["bias"])
        metric_results[metric_name] = {"corr": corrs, "bias": bias_vals, "unit": unit}

        print(f"  {label}: CORR / Bias 已计算")

    return metric_results


def compute_spatial_rows(model_sel: xr.Dataset, obs_sel: xr.Dataset) -> List[Dict[str, Any]]:
    """计算 MME 与观测的空间统计量并组装地图面板所需的行数据（原 Fig2b.py 主流程的计算段）。"""
    spatial_rows: List[Dict[str, Any]] = []

    for metric_name, meta in TARGET_METRICS.items():
        label = meta["label"]
        unit = meta["unit"]
        model_var = model_sel[metric_name]
        obs_var = obs_sel[metric_name]

        # MME 空间统计
        mme_field = model_var.mean(dim="case").mean(dim="year")
        obs_field = obs_var.mean(dim="year")
        stats = calc_spatial_metrics(mme_field, obs_field)

        obs_map = obs_sel[metric_name].mean(dim="year")
        mme_map = model_sel[metric_name].mean(dim="case").mean(dim="year")
        cmap_main = "r95_cmap" if metric_name == "R95mm_intensity" else "precipvar_cmap"
        # 面积加权区域均值（供 data/ 统计落盘）
        w_map = _cos_lat_weights(obs_map)
        ok_map = np.isfinite(obs_map.values) & np.isfinite(mme_map.values)
        obs_mean_w = float((obs_map.values[ok_map] * w_map[ok_map]).sum() / w_map[ok_map].sum())
        mme_mean_w = float((mme_map.values[ok_map] * w_map[ok_map]).sum() / w_map[ok_map].sum())
        spatial_rows.append({
            "label": label, "unit": unit,
            "obs_map": obs_map, "mme_map": mme_map,
            "cmap_main": cmap_main,
            "corr": stats["corr"], "p_value": stats.get("p_value", np.nan),
            "nrmse": stats["nrmse"], "rmse": stats.get("rmse", np.nan),
            "n_valid": stats.get("n_valid", 0),
            "obs_mean_w": obs_mean_w, "mme_mean_w": mme_mean_w,
        })
        print(f"  {label}: CORR={stats['corr']:.3f}  NRMSE={stats['nrmse']:.3f}")

    return spatial_rows


# ==================== 散点面板 (a)：流水线 ====================
def render_scatter_figure(metric_results: Dict[str, Dict[str, Any]], mode_names: List[str]) -> None:
    """绘制散点面板 (a)，并落盘为论文成品图 Fig2.jpg。

    取代原 compose_fig2.py 的 `shutil.copyfile` 步骤，也不再产生中间的
    Fig2a.jpg：模块根目录下只有这一张成品图。
    """
    # ========================================================
    # Fig. 2 — 散点图 (CORR / Bias)
    # ========================================================
    # 底部行固定在 2.0 cm（留出旋转的模式名），保留原面板高度与间距。
    # 两行画布高 9.05 cm，行位 5.55 / 2.0 cm。
    sw, sh, sg, sx = 10.5, 2.8, 0.75, 0.7
    _row_step = sh + sg
    _n_panel = len(PANEL_KEYS)
    _y_bottom = 2.0
    fig2_w = 14.0
    fig2_h_cm = _y_bottom + (_n_panel - 1) * _row_step + sh + 0.7
    fig2 = plt.figure(figsize=(fig2_w / 2.54, fig2_h_cm / 2.54))

    def R_a(l, b, w, h):
        return (l / fig2_w, b / fig2_h_cm, w / fig2_w, h / fig2_h_cm)

    fig2_axes = [fig2.add_axes(R_a(sx, _y_bottom + (_n_panel - 1 - i) * _row_step, sw, sh))
                 for i in range(_n_panel)]

    r95_stats = metric_results.get("R95mm_intensity", {})
    var_stats = metric_results.get("PrecipVar", {})
    draw_scatter_panels(fig2_axes, mode_names, r95_stats, var_stats, SCATTER_PARAMS)

    print(f"  面板: {list(PANEL_KEYS)}  输出: {PAPER_FIG_NAME}")
    fig2.savefig(FIG_DIR / PAPER_FIG_NAME, dpi=400, bbox_inches="tight")
    print(f"  导出: {PAPER_FIG_NAME}")
    plt.close(fig2)


def run_scatter_panel(model_sel: xr.Dataset, obs_sel: xr.Dataset, common_years: np.ndarray,
                      mode_names: List[str]) -> None:
    """散点面板 (a) 全流程：统计计算 → 统计落盘 → 绘图并输出论文成品图 Fig2.jpg。"""
    print("-" * 70)
    print("Fig. 2 — 散点面板 (CORR / Bias)：按论文正文口径逐模式评估")

    metric_results = compute_scatter_metrics(model_sel, obs_sel)

    # ---- 统计数据落盘（data/，CSV，供核对论文数字）----
    csv_path = DATA_DIR / "fig2a_stats.csv"
    per_model_csv_path = DATA_DIR / "fig2_per_model.csv"
    dump_scatter_stats_csv(metric_results, mode_names, csv_path, per_model_csv_path)
    print(f"  统计数据(csv): {csv_path}")
    print(f"  逐模式明细(csv): {per_model_csv_path}")

    render_scatter_figure(metric_results, mode_names)


# ==================== 地图面板 (b)：流水线 ====================
def _register_map_colormaps() -> None:
    """注册地图面板专用色带（r95_cmap / precipvar_cmap）。"""
    r95_colors = ["#315484", "#568588", "#84B0D3", "#82D1DF", "#CCD7BC",
                  "#FEF2B6", "#FDC780", "#F58A58", "#D64736", "#992323"]
    if "r95_cmap" not in plt.colormaps():
        plt.colormaps.register(LinearSegmentedColormap.from_list("r95_cmap", r95_colors))
    var_colors = ["#7195DB", "#D0E8F8", "#90C0D8", "#708A98",
                  "#F5F7F7", "#E2CCB2", "#E9AF99", "#D96E57"]
    if "precipvar_cmap" not in plt.colormaps():
        plt.colormaps.register(LinearSegmentedColormap.from_list("precipvar_cmap", var_colors))


def _load_china_boundary() -> Tuple[list, Dict[str, float]]:
    """读取中国国界 shapefile，返回 (geoms, region)。"""
    sf = shapefile.Reader(str(SHP_PATH))
    cn_geoms = []
    for s in sf.shapes():
        geo_interface = getattr(s, "__geo_interface__", None)
        if geo_interface is None:
            raise ValueError("shapefile 记录缺少 __geo_interface__ 属性")
        cn_geoms.append(shapely_shape(cast(Any, geo_interface)))
    shp_bbox = sf.bbox
    region = {"lon_min": float(shp_bbox[0]) - 1, "lon_max": float(shp_bbox[2]) + 1,
              "lat_min": float(shp_bbox[1]) - 1, "lat_max": float(shp_bbox[3]) + 1}
    return cn_geoms, region


def render_map_figure(spatial_rows: List[Dict[str, Any]], cn_geoms: list,
                      region: Dict[str, float], out_dir: Path) -> None:
    """绘制 2×2 气候态地图面板 (b)，图片写入 out_dir（运行期临时目录，不落盘）。"""
    # ========================================================
    # Fig. 1(b) — 空间分布图 (2×2 地图)
    # ========================================================
    dlon = region["lon_max"] - region["lon_min"]
    dlat = region["lat_max"] - region["lat_min"]
    clat = np.deg2rad((region["lat_min"] + region["lat_max"]) / 2)
    map_aspect = (dlat / dlon) / np.cos(clat)

    mw = 7.0
    mh = mw * map_aspect

    fig3_w, fig3_h = 20 / 2.54, 14 / 2.54
    fig3 = plt.figure(figsize=(fig3_w, fig3_h))

    def R_b(l, b, w, h):
        return (l/20, b/14, w/20, h/14)

    mgx = 1.6
    mgy = 2.4
    mx_cn = 1.0
    mx_mme = mx_cn + mw + mgx

    map_axes = np.empty((len(spatial_rows), 2), dtype=object)
    for r in range(len(spatial_rows)):
        my = 1.0 + r * (mh + mgy)
        for c in range(2):
            mx = mx_cn if c == 0 else mx_mme
            map_axes[r, c] = fig3.add_axes(R_b(mx, my, mw, mh), projection=ccrs.PlateCarree())

    draw_map_panels(fig3, map_axes, spatial_rows, cn_geoms, region, MAP_PARAMS)

    # 地图面板只是运行期的核对产物：写到临时目录，模块根目录不落盘。
    map_path = out_dir / "Fig2b.jpg"
    fig3.savefig(map_path, dpi=400, bbox_inches="tight")
    print(f"  导出(临时目录，运行结束即随临时目录删除): {map_path}")
    plt.close(fig3)


def run_map_panel(model_sel: xr.Dataset, obs_sel: xr.Dataset, common_years: np.ndarray,
                  out_dir: Path) -> None:
    """地图面板 (b) 全流程：注册色带 → 算 MME 统计量并落盘 → 读国界 → 绘图到 out_dir。

    渲染与统计逻辑与原 Fig2b.py 完全一致，唯一区别是图片写进 `out_dir`
    （由 main() 提供的运行期临时目录，退出即删除），模块根目录不留图。

    这里算出的 MME 统计量（CORR≈0.94/0.95、偏差 0.37/3.35 mm/day、
    观测 26.37 对 MME 23.01 mm/day）仍是正文与摘要的引用来源，必须保留。
    """
    print("-" * 70)
    print("Fig. 2 — 地图面板 (b)：CN05.1 vs HiCPC-MME 气候态空间分布 + MME 评估统计")

    # ---- 注册色带 ----
    _register_map_colormaps()

    # ---- 计算空间指标 + 构建 spatial_rows ----
    spatial_rows = compute_spatial_rows(model_sel, obs_sel)

    # ---- 统计数据落盘（CSV）----
    stats_csv_path = Path(__file__).parent / "data" / "fig2b_stats.csv"
    dump_map_stats_csv(spatial_rows, stats_csv_path, int(common_years.min()), int(common_years.max()))
    print(f"  统计数据(CSV): {stats_csv_path}")

    # ---- 中国地图边界 ----
    cn_geoms, region = _load_china_boundary()

    render_map_figure(spatial_rows, cn_geoms, region, out_dir)


def _make_map_tmpdir() -> Path:
    """为地图面板 (b) 创建运行期临时目录，返回其路径。

    刻意**不用** `tempfile.mkdtemp()` / `TemporaryDirectory()`，也刻意不放在模块目录内：
      * 它们以 0o700 建目录，在受限环境（本仓库所在的 Windows 沙箱）下会生成
        连删除都被拒绝的目录，一旦落在模块目录里就会永久破坏
        「模块根只有 Fig2.py / Fig2.jpg / data/ / README.md 四项」的结构；
      * 平台默认临时目录（%TEMP%）在同样的受限环境下还可能「允许建目录、
        却禁止往目录里写文件」。
    因此这里用 `os.makedirs()`（默认权限）把临时目录建在模块**之外**的工作区根目录
    （即论文仓库 `REPO_ROOT` 的上一级），并在 main() 的 finally 中删除。
    """
    tmp_dir = REPO_ROOT.parent / f"_tmp_fig2_map_{uuid.uuid4().hex[:8]}"
    os.makedirs(tmp_dir, exist_ok=False)
    return tmp_dir


# ==================== 命令行入口 ====================
def parse_args(argv: List[str] | None = None) -> argparse.Namespace:
    """解析命令行参数。

    不带参数时按原「Fig2a.py + compose_fig2.py + Fig2b.py」三条命令的顺序
    依次完成散点面板与地图面板；原来的两个独立脚本改为可选开关。
    """
    parser = argparse.ArgumentParser(
        description="图 2 单文件流水线：散点面板 (a) + 地图面板 (b) + 统计数据落盘",
    )
    group = parser.add_mutually_exclusive_group()
    group.add_argument("--scatter-only", action="store_true",
                       help="只跑散点面板：论文成品图 Fig2.jpg 及 data/fig2a_stats.csv 等")
    group.add_argument("--map-only", action="store_true",
                       help="只跑地图面板：地图渲染到临时目录（不落盘），统计写入 data/fig2b_stats.csv 等")
    return parser.parse_args(argv)


def main(argv: List[str] | None = None) -> None:
    args = parse_args(argv)

    print("=" * 70)
    print("Fig. 2 — HiCPC 与 CN05.1 评估图（单文件版：散点面板 + 地图面板）")
    print(f"模型: {MODEL_FILE}")
    print(f"观测: {OBS_FILE}")
    print("=" * 70)

    FIG_DIR.mkdir(parents=True, exist_ok=True)

    # ---- 数据准备（两个面板共用，先于绘图）----
    if not args.map_only:
        payload = json.loads((DATA_DIR / "fig2_plot_metrics.json").read_text())
        render_scatter_figure(payload["metric_results"], payload["mode_names"])
        return

    model_sel, obs_sel, common_years, mode_names = load_evaluation_data()

    # ---- 先散点面板，后地图面板（保持原「先算后画、先 a 后 b」的顺序）----
    if not args.map_only:
        run_scatter_panel(model_sel, obs_sel, common_years, mode_names)
    if not args.scatter_only:
        # 地图面板 (b) 是运行期临时产物：图片写进模块之外的临时目录，用完即删，
        # 模块根目录因此只留论文成品图 Fig2.jpg（MME 统计仍照常落盘 data/）。
        tmp_dir = _make_map_tmpdir()
        try:
            run_map_panel(model_sel, obs_sel, common_years, tmp_dir)
        finally:
            shutil.rmtree(tmp_dir, ignore_errors=True)

    print("完成。")


if __name__ == "__main__":
    main()
