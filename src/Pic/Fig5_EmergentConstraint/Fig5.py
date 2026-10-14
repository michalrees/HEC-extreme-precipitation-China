import argparse
import os
import shutil
import tempfile
import uuid
from pathlib import Path

import pandas as pd
import matplotlib.pyplot as plt
import numpy as np
import xarray as xr
from matplotlib.colors import ListedColormap, BoundaryNorm, Normalize, LinearSegmentedColormap
from matplotlib.patches import Patch
from matplotlib.ticker import FuncFormatter
from mpl_toolkits.axes_grid1.inset_locator import inset_axes

import cartopy.crs as ccrs
import shapefile
from shapely.geometry import shape as shapely_shape

plt.rcParams["font.family"] = "Times New Roman"
plt.rcParams["mathtext.fontset"] = "cm"
plt.rcParams["axes.unicode_minus"] = False

ROOT = Path(__file__).resolve().parent
REPO_ROOT = next(p for p in Path(__file__).resolve().parents if (p / "src").is_dir() and (p / "Doc").is_dir())


DATA_ROOT = REPO_ROOT / "Data"
SHP_PATH = DATA_ROOT / "China" / "cnmap.shp"
OUTPUT_DIR = ROOT
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)


HEC_DIR = REPO_ROOT / "Output" / "EC" / "China"

SCENARIOS = ("ssp126", "ssp245", "ssp585")
SCENARIO_LABELS = {"ssp126": "SSP1-2.6", "ssp245": "SSP2-4.5", "ssp585": "SSP5-8.5"}
PROJ = ccrs.PlateCarree()

# ---- 配色（组图与单面板共用同一份锚点色，但分级规则各自独立）----
CORR_COLORS = ["#254653", "#267271", "#259D8C", "#E9C46B", "#F3A161", "#E76F50"]
CORR_CMAP = ListedColormap(CORR_COLORS, "corr_custom")

CLASS_COLORS = ["#E7F2F6", "#FE9833", "#E95538", "#D3113D", "#770838", "#1A0033"]


DELTA_ANCHOR_COLORS = ["#315484", "#84B0D3", "#E7F2F6", "#F58A58", "#992323"]


def _fmt_tick(v, _pos=None):
    """刻度标签：整数不带小数，非整数保留 1 位小数（组图统一口径）。"""
    return f"{v:.0f}" if abs(v - round(v)) < 1e-9 else f"{v:.1f}"


def _diverging_bounds(half, inner=(1.0, 6.0)):
    """以 0 为中心、近 0 密两端疏的分级边界，首尾恰为 ±half（实际极值）。"""
    pos = [v for v in inner if v < half] + [half]
    return np.array([-p for p in reversed(pos)] + pos)


# ============================================================
# 加载中国国界 / 加载数据（四个渲染阶段共用）
# ============================================================
def load_china_geoms():
    """读取中国国界矢量，返回 (几何列表, set_extent 用的经纬范围)。"""
    sf = shapefile.Reader(str(SHP_PATH))
    cn_geoms = [shapely_shape(s.__geo_interface__) for s in sf.shapes()]
    shp_bbox = sf.bbox
    extent = [float(shp_bbox[0]) - 1, float(shp_bbox[2]) + 1,
              float(shp_bbox[1]) - 1, float(shp_bbox[3]) + 1]
    return cn_geoms, extent


def load_datasets():
    """加载三情景 HEC 结果；缺文件时显式报错并提示先跑 pipeline。"""
    datasets = {}
    for s in SCENARIOS:
        _fp = HEC_DIR / f"HEC_{s}_PrecipVar_to_R95mm_intensity.nc"
        if not _fp.exists():
            raise FileNotFoundError(f"未找到 HEC 输出: {_fp}（请先运行 src/pipeline/6中国区域分层涌现约束.py）")
        with xr.open_dataset(_fp) as ds:
            datasets[s] = ds.load()
        print(f'  {SCENARIO_LABELS[s]} 加载完成  future_period={datasets[s].attrs.get("future_period")}')
    return datasets


# ============================================================
# ① 面板 (a) 单面板：相关系数 r（固定 0.5–1.0 分级）
# ============================================================
def render_panel_a(datasets, cn_geoms, extent, out_path) -> None:
    """单面板 (a)：相关系数三情景单行渲染（灰色掩膜 + 等值线 + 内嵌 PDF 直方图），写到 out_path。"""
    # 单面板固定分级（与组图按显著区极值重算不同，勿统一）
    contour_levels = np.linspace(0.5, 1.0, 7)

    fig = plt.figure(figsize=(20 / 2.54, 6.5 / 2.54))
    sub_axes = []

    for c, scenario in enumerate(SCENARIOS):
        ds = datasets[scenario]
        r_vals = ds["r"].values
        lon = ds["lon"].values.astype(np.float64)
        lat = ds["lat"].values.astype(np.float64)
        p_map = ds["p_value"].values

        Lon, Lat_grid = np.meshgrid(lon, lat)

        valid = np.isfinite(p_map) & np.isfinite(r_vals)
        mask = (np.isfinite(p_map) & (p_map >= 0.05)) | (np.isfinite(r_vals) & (r_vals < 0.5))

        colored_pct = ((~mask) & valid).sum() / valid.sum() * 100 if valid.sum() > 0 else 0

        ax = fig.add_subplot(1, 3, c + 1, projection=PROJ)
        sub_axes.append(ax)
        ax.set_extent(extent, crs=PROJ)

        ax.contourf(Lon[::2, ::2], Lat_grid[::2, ::2], r_vals[::2, ::2],
                     levels=contour_levels,
                     cmap=CORR_CMAP, extend='both', transform=PROJ)
        if np.any(mask):
            ax.contourf(Lon[::2, ::2], Lat_grid[::2, ::2],
                        mask.astype(float)[::2, ::2],
                        levels=[0.5, 1.5],
                        colors=["grey"], alpha=0.55, transform=PROJ)
        ax.contour(Lon[::2, ::2], Lat_grid[::2, ::2], r_vals[::2, ::2],
                   levels=contour_levels,
                   transform=PROJ, colors="black", linewidths=0.4)
        ax.add_geometries(cn_geoms, crs=ccrs.PlateCarree(), facecolor='none',
                          edgecolor='#999999', linewidth=0.5)
        ax.set_title(SCENARIO_LABELS[scenario], fontsize=14, fontweight='normal', pad=20)

        gl = ax.gridlines(draw_labels=True, linewidth=0.3, alpha=0.4, linestyle='--',
                          xlocs=[80, 90, 110, 130], ylocs=[10, 20, 30, 40, 50])
        gl.top_labels = False
        gl.right_labels = False
        gl.xlabel_style = {"size": 10}
        gl.ylabel_style = {"size": 10}

        ax.text(0.5, 1.09, f"p < 0.05 and r >= 0.5: {colored_pct:.1f}%",
                transform=ax.transAxes, fontsize=9,
                ha="center", va="top",
                bbox={"boxstyle": "round,pad=0.3", "facecolor": "white",
                      "edgecolor": "gray", "alpha": 0.8})

        # Mean 在全部有限格点上按 cos(φ) 面积加权（与组图的"仅显著格点"口径不同）
        w2d = np.cos(np.deg2rad(lat))[:, np.newaxis]
        wm = np.nansum(r_vals * w2d) / np.nansum(w2d * np.isfinite(r_vals))
        ax.text(0.97, 0.03, f"Mean: {wm:.3g}",
                transform=ax.transAxes, fontsize=7,
                ha="right", va="bottom",
                bbox=dict(boxstyle="round,pad=0.3", facecolor="white",
                          edgecolor="gray", alpha=0.8))

        fvals = r_vals[np.isfinite(r_vals)]
        if len(fvals) > 0:
            fvals = np.clip(fvals, 0.5, 1.0)
            counts, _ = np.histogram(fvals, bins=contour_levels)
            n_int = len(contour_levels) - 1
            bc = (contour_levels[:-1] + contour_levels[1:]) / 2
            bw = np.diff(contour_levels)
            pdf = counts / (counts.sum() * bw) if counts.sum() > 0 else np.zeros_like(counts)

            hist_ax = inset_axes(ax, width=0.315, height=0.248,
                                 bbox_to_anchor=(0.18, 0.07),
                                 bbox_transform=ax.transAxes,
                                 loc="lower left", borderpad=0)
            for j in range(n_int):
                hist_ax.bar(bc[j], pdf[j], width=bw[j] * 0.9,
                            color=CORR_CMAP((bc[j] - 0.5) / 0.5),
                            edgecolor="black", linewidth=0.3)
            hist_ax.set_xlim(0.5, 1.0)
            hist_ax.tick_params(axis="both", length=1.5, labelsize=6, width=0.3)
            hist_ax.set_ylabel("PDF", fontsize=7, fontweight="normal", labelpad=0)
            hist_ax.set_facecolor("none")
            hist_ax.patch.set_alpha(0)
            for sp in hist_ax.spines.values():
                sp.set_linewidth(0.3)
            hist_ax.spines["top"].set_visible(False)
            hist_ax.spines["right"].set_visible(False)

    for ax in sub_axes:
        ax.spines['geo'].set_visible(False)

    fig.subplots_adjust(left=0.05, right=0.92, top=0.873, bottom=0.14, wspace=0.16)

    ax_mid = sub_axes[1]
    x0, x1, y0 = ax_mid.get_position().x0, ax_mid.get_position().x1, ax_mid.get_position().y0
    cax = fig.add_axes(((x0 + x1) / 2 - (x1 - x0) * 0.9, y0 - 0.14, (x1 - x0) * 1.80, 0.030))

    sm = plt.cm.ScalarMappable(norm=Normalize(0.5, 1.0), cmap=CORR_CMAP)
    sm.set_array([])
    cbar = fig.colorbar(sm, cax=cax, orientation="horizontal",
                        extend="both", extendfrac=0.04, ticks=contour_levels)
    cbar.ax.xaxis.set_major_formatter(FuncFormatter(lambda v, _: f"{v:.2f}"))
    cbar.ax.tick_params(labelsize=11)
    cbar.set_label("Correlation r", fontsize=11)

    ax3 = sub_axes[2]
    ax3_pos = ax3.get_position()
    fig.legend(handles=[Patch(facecolor="grey", alpha=0.55, label="p ≥ 0.05 or r < 0.5")],
               bbox_to_anchor=(ax3_pos.x0 + 0.97 * ax3_pos.width, -0.03),
               loc="lower right", fontsize=8, framealpha=0.8)

    fig.suptitle("Correlation between Precipitation Variability and R95 Intensity Index",
                 fontsize=15, fontweight='normal', y=1.10)

    fig.text(0.01, 1.10, '(a)', fontsize=18, fontweight='normal',
             transform=fig.transFigure, ha='left', va='top')

    fig.savefig(out_path, dpi=400, bbox_inches="tight")
    print(f"  单面板 (a) 已渲染: {out_path}")
    plt.close(fig)


# ============================================================
# ② 面板 (b) 单面板：不确定性缩减率（固定分级，按实际最大值裁剪）
# ============================================================
def render_panel_b(datasets, cn_geoms, extent, out_path) -> None:
    """单面板 (b)：不确定性缩减率三情景单行渲染（灰色掩膜仅按 p≥0.05 + 内嵌 PDF 直方图），写到 out_path。"""
    all_vals = np.concatenate([datasets[s]["reduction"].values.ravel() for s in SCENARIOS])
    all_valid = all_vals[np.isfinite(all_vals)]
    global_min = float(all_valid.min()) if len(all_valid) > 0 else 0.0
    global_max = float(all_valid.max()) if len(all_valid) > 0 else 1.0

    raw_bounds = [0.0, 0.1, 0.2, 0.4, 0.6, 0.8, 1.0]
    bounds = [b for b in raw_bounds if b <= global_max * 1.01]
    if bounds[-1] < global_max:
        bounds.append(global_max)
    colors = CLASS_COLORS[:len(bounds) - 1]
    cmap = ListedColormap(colors)
    class_norm = BoundaryNorm(bounds, cmap.N, clip=True)

    fig = plt.figure(figsize=(20 / 2.54, 6.5 / 2.54))
    sub_axes = []

    for c, scenario in enumerate(SCENARIOS):
        ds = datasets[scenario]
        reduction = ds["reduction"].values
        p_map = ds["p_value"].values
        lon = ds["lon"].values.astype(np.float64)
        lat = ds["lat"].values.astype(np.float64)
        Lon, Lat_grid = np.meshgrid(lon, lat)

        # 单面板口径：灰色掩膜只判 p >= 0.05（不含 r < 0.5，与组图不同）
        mask = np.isfinite(p_map) & (p_map >= 0.05)

        ax = fig.add_subplot(1, 3, c + 1, projection=PROJ)
        sub_axes.append(ax)
        ax.set_extent(extent, crs=PROJ)

        ax.contourf(Lon[::2, ::2], Lat_grid[::2, ::2], reduction[::2, ::2],
                     levels=bounds, colors=colors, extend='both', transform=PROJ)
        if np.any(mask):
            ax.contourf(Lon[::2, ::2], Lat_grid[::2, ::2],
                        mask.astype(float)[::2, ::2],
                        levels=[0.5, 1.5],
                        colors=["grey"], alpha=0.55, transform=PROJ)
        ax.contour(Lon[::2, ::2], Lat_grid[::2, ::2], reduction[::2, ::2],
                   levels=bounds, transform=PROJ, colors="black", linewidths=0.4)
        ax.add_geometries(cn_geoms, crs=ccrs.PlateCarree(), facecolor='none',
                          edgecolor='#999999', linewidth=0.5)
        ax.set_title(SCENARIO_LABELS[scenario], fontsize=14, fontweight='normal')

        gl = ax.gridlines(draw_labels=True, linewidth=0.3, alpha=0.4, linestyle='--',
                          xlocs=[80, 90, 110, 130], ylocs=[10, 20, 30, 40, 50])
        gl.top_labels = False
        gl.right_labels = False
        gl.xlabel_style = {"size": 10}
        gl.ylabel_style = {"size": 10}

        # Mean 在全部有限格点上按 cos(φ) 面积加权（与组图的"仅显著格点"口径不同）
        w2d = np.cos(np.deg2rad(lat))[:, np.newaxis]
        wm = np.nansum(reduction * w2d) / np.nansum(w2d * np.isfinite(reduction))
        ax.text(0.97, 0.03, f"Mean: {wm:.3g}",
                transform=ax.transAxes, fontsize=7,
                ha="right", va="bottom",
                bbox=dict(boxstyle="round,pad=0.3", facecolor="white",
                          edgecolor="gray", alpha=0.8))

        fvals = reduction[np.isfinite(reduction)]
        if len(fvals) > 0:
            fvals = np.clip(fvals, bounds[0], bounds[-1])
            counts, _ = np.histogram(fvals, bins=bounds)
            n_int = len(bounds) - 1
            bc = (np.array(bounds[:-1]) + np.array(bounds[1:])) / 2
            bw = np.diff(bounds)
            pdf = counts / (counts.sum() * bw) if counts.sum() > 0 else np.zeros_like(counts)

            hist_ax = inset_axes(ax, width=0.315, height=0.248,
                                 bbox_to_anchor=(0.18, 0.07),
                                 bbox_transform=ax.transAxes,
                                 loc="lower left", borderpad=0)
            uniform_bw = (bounds[-1] - bounds[0]) / n_int
            for j in range(n_int):
                cidx = j
                hist_ax.bar(bc[j], pdf[j], width=uniform_bw * 0.9,
                            color=colors[cidx],
                            edgecolor="black", linewidth=0.3)
            hist_ax.set_xlim(0, 1)
            hist_ax.tick_params(axis="both", length=1.5, labelsize=6, width=0.3)
            hist_ax.set_ylabel("PDF", fontsize=7, fontweight="normal", labelpad=0)
            hist_ax.set_facecolor("none")
            hist_ax.patch.set_alpha(0)
            for sp in hist_ax.spines.values():
                sp.set_linewidth(0.3)
            hist_ax.spines["top"].set_visible(False)
            hist_ax.spines["right"].set_visible(False)

    for ax in sub_axes:
        ax.spines['geo'].set_visible(False)

    fig.subplots_adjust(left=0.05, right=0.92, top=0.767, bottom=0.14, wspace=0.16)

    ax_mid = sub_axes[1]
    x0, x1, y0 = ax_mid.get_position().x0, ax_mid.get_position().x1, ax_mid.get_position().y0
    cx = (x0 + x1) / 2
    cax = fig.add_axes((cx - (x1 - x0) * 0.9, y0 - 0.14, (x1 - x0) * 1.80, 0.030))

    sm = plt.cm.ScalarMappable(norm=class_norm, cmap=cmap)
    sm.set_array([])
    cbar = fig.colorbar(sm, cax=cax, orientation="horizontal",
                        extend="both", extendfrac=0.04, ticks=bounds)
    cbar.ax.xaxis.set_major_formatter(FuncFormatter(lambda v, _: f"{v * 100:.0f}%"))
    cbar.ax.tick_params(labelsize=11)
    cbar.ax.set_xticklabels(
        [f"{global_min * 100:.1f}%"] + [f"{b * 100:.0f}%" for b in bounds[1:-1]] + [f"{global_max * 100:.1f}%"])
    cbar.set_label("Uncertainty Reduction ($\\sigma$)", fontsize=11)

    fig.suptitle("Uncertainty Reduction ($\\sigma$ caliber) of Precipitation Variability to R95 Intensity Index",
                 fontsize=15, fontweight='normal', y=0.98)

    fig.text(0.01, 0.99, '(b)', fontsize=18, fontweight='normal',
             transform=fig.transFigure, ha='left', va='top')

    fig.savefig(out_path, dpi=400, bbox_inches="tight")
    print(f"  单面板 (b) 已渲染: {out_path}")
    plt.close(fig)


# ============================================================
# ③ 面板 (c) 单面板：后验−先验差值（固定 ±1 外置边界）
# ============================================================
def render_panel_c(datasets, cn_geoms, extent, out_path) -> None:
    """单面板 (c)：后验−先验差值三情景单行渲染（灰色掩膜仅按 p≥0.05 + 内嵌 PDF 直方图），写到 out_path。"""
    all_delta = np.concatenate([
        (datasets[s]["posterior_mean"] - datasets[s]["prior_mean"]).values.ravel()
        for s in SCENARIOS])
    all_valid = all_delta[np.isfinite(all_delta)]
    global_min = float(all_valid.min()) if len(all_valid) > 0 else -1.0
    global_max = float(all_valid.max()) if len(all_valid) > 0 else 1.0


    DELTA_COLORS = ["#315484", "#84B0D3", "#E7F2F6", "#F58A58", "#992323"]

    if global_min < -1 and global_max > 1:
        bounds = [-14, -7, -1, 1, 7, 14]          # 6 boundaries -> 5 intervals
    else:
        bounds = list(np.linspace(global_min, global_max, 6))
    colors = DELTA_COLORS
    cmap = ListedColormap(colors)
    class_norm = BoundaryNorm(bounds, cmap.N, clip=True)

    fig = plt.figure(figsize=(20 / 2.54, 6.5 / 2.54))
    sub_axes = []

    for c, scenario in enumerate(SCENARIOS):
        ds = datasets[scenario]
        posterior = ds["posterior_mean"].values
        prior = ds["prior_mean"].values
        p_map = ds["p_value"].values
        lon = ds["lon"].values.astype(np.float64)
        lat = ds["lat"].values.astype(np.float64)
        delta = posterior - prior

        Lon, Lat_grid = np.meshgrid(lon, lat)

        # 单面板口径：灰色掩膜只判 p >= 0.05（不含 r < 0.5，与组图不同）
        mask = np.isfinite(p_map) & (p_map >= 0.05)

        ax = fig.add_subplot(1, 3, c + 1, projection=PROJ)
        sub_axes.append(ax)
        ax.set_extent(extent, crs=PROJ)

        ax.contourf(Lon[::2, ::2], Lat_grid[::2, ::2], delta[::2, ::2],
                     levels=bounds, colors=colors, extend='both', transform=PROJ)
        if np.any(mask):
            ax.contourf(Lon[::2, ::2], Lat_grid[::2, ::2],
                        mask.astype(float)[::2, ::2],
                        levels=[0.5, 1.5],
                        colors=["grey"], alpha=0.55, transform=PROJ)
        ax.contour(Lon[::2, ::2], Lat_grid[::2, ::2], delta[::2, ::2],
                   levels=bounds, transform=PROJ, colors="black", linewidths=0.4)
        ax.add_geometries(cn_geoms, crs=ccrs.PlateCarree(), facecolor='none',
                          edgecolor='#999999', linewidth=0.5)
        ax.set_title(SCENARIO_LABELS[scenario], fontsize=14, fontweight='normal')

        gl = ax.gridlines(draw_labels=True, linewidth=0.3, alpha=0.4, linestyle='--',
                          xlocs=[80, 90, 110, 130], ylocs=[10, 20, 30, 40, 50])
        gl.top_labels = False
        gl.right_labels = False
        gl.xlabel_style = {"size": 10}
        gl.ylabel_style = {"size": 10}

        # Mean 在全部有限格点上按 cos(φ) 面积加权（与组图的"仅显著格点"口径不同）
        w2d = np.cos(np.deg2rad(lat))[:, np.newaxis]
        wm = np.nansum(delta * w2d) / np.nansum(w2d * np.isfinite(delta))
        ax.text(0.97, 0.03, f"Mean: {wm:.3g}",
                transform=ax.transAxes, fontsize=7,
                ha="right", va="bottom",
                bbox=dict(boxstyle="round,pad=0.3", facecolor="white",
                          edgecolor="gray", alpha=0.8))

        fvals = delta[np.isfinite(delta)]
        if len(fvals) > 0:
            fvals = np.clip(fvals, bounds[0], bounds[-1])
            counts, _ = np.histogram(fvals, bins=bounds)
            n_int = len(bounds) - 1
            bc = (np.array(bounds[:-1]) + np.array(bounds[1:])) / 2
            bw = np.diff(bounds)
            pdf = counts / (counts.sum() * bw) if counts.sum() > 0 else np.zeros_like(counts)

            hist_ax = inset_axes(ax, width=0.315, height=0.248,
                                 bbox_to_anchor=(0.18, 0.07),
                                 bbox_transform=ax.transAxes,
                                 loc="lower left", borderpad=0)
            uniform_bw = (bounds[-1] - bounds[0]) / n_int
            for j in range(n_int):
                cidx = j
                hist_ax.bar(bc[j], pdf[j], width=uniform_bw * 0.9,
                            color=colors[cidx],
                            edgecolor="black", linewidth=0.3)
            hist_ax.set_xlim(bounds[0], bounds[-1])
            hist_ax.tick_params(axis="both", length=1.5, labelsize=6, width=0.3)
            hist_ax.set_ylabel("PDF", fontsize=7, fontweight="normal", labelpad=0)
            hist_ax.set_facecolor("none")
            hist_ax.patch.set_alpha(0)
            for sp in hist_ax.spines.values():
                sp.set_linewidth(0.3)
            hist_ax.spines["top"].set_visible(False)
            hist_ax.spines["right"].set_visible(False)

    for ax in sub_axes:
        ax.spines['geo'].set_visible(False)

    fig.subplots_adjust(left=0.05, right=0.92, top=0.767, bottom=0.14, wspace=0.16)

    ax_mid = sub_axes[1]
    x0, x1, y0 = ax_mid.get_position().x0, ax_mid.get_position().x1, ax_mid.get_position().y0
    cax = fig.add_axes(((x0 + x1) / 2 - (x1 - x0) * 0.9, y0 - 0.14, (x1 - x0) * 1.80, 0.030))

    sm = plt.cm.ScalarMappable(norm=class_norm, cmap=cmap)
    sm.set_array([])
    # 显示关键标注：负端、-1、1、正端，2位小数
    show_ticks = sorted(set([bounds[0], -1.0, 1.0, bounds[-1]]))
    cbar = fig.colorbar(sm, cax=cax, orientation="horizontal",
                        extend="both", extendfrac=0.04, ticks=show_ticks)
    cbar.ax.xaxis.set_major_formatter(FuncFormatter(lambda v, _: f"{v:.0f}" if v in (-1, 1) else f"{v:.2f}"))
    cbar.ax.tick_params(labelsize=11)
    cbar.set_label("Posterior − Prior (mm/day)", fontsize=11)

    fig.suptitle("Posterior − Prior Difference of Precipitation Variability to R95 Intensity Index",
                 fontsize=15, fontweight='normal', y=0.98)

    fig.text(0.01, 0.99, '(c)', fontsize=18, fontweight='normal',
             transform=fig.transFigure, ha='left', va='top')

    fig.savefig(out_path, dpi=400, bbox_inches="tight")
    print(f"  单面板 (c) 已渲染: {out_path}")
    plt.close(fig)


# ============================================================
# ④ 成品组图：3 行（诊断量）× 3 列（情景），并落盘统计 CSV
# ============================================================
ROW_TITLES = [
    "Correlation between Precipitation Variability and R95 Intensity",
    "Uncertainty Reduction of Precipitation Variability to R95 Intensity",
    "Posterior − Prior Difference of Precipitation Variability to R95 Intensity",
]


def render_composite(datasets, cn_geoms, extent) -> None:
    """Fig5.jpg + data/fig5_stats.csv：不拼接 JPG，直接用 nc 数据重绘 3×3 组图。"""
    # ---- 计算全局色带边界 ----
    all_delta = np.concatenate([
        (datasets[s]["posterior_mean"] - datasets[s]["prior_mean"]).values.ravel()
        for s in SCENARIOS])
    all_valid_delta = all_delta[np.isfinite(all_delta)]
    global_min = float(all_valid_delta.min()) if len(all_valid_delta) > 0 else -1.0
    global_max = float(all_valid_delta.max()) if len(all_valid_delta) > 0 else 1.0

    # ---- (a) 相关系数：显著区（p<0.05 且 r>=0.5）三情景并集的实际极值 ----
    _r_vals = []
    for _s in SCENARIOS:
        _r = datasets[_s]["r"].values
        _p = datasets[_s]["p_value"].values
        _m = np.isfinite(_r) & np.isfinite(_p) & (_p < 0.05) & (_r >= 0.5)
        _r_vals.append(_r[_m])
    all_r = np.concatenate(_r_vals)
    corr_min, corr_max = float(all_r.min()), float(all_r.max())
    # 组图分级：按显著区实际极值重算（与单面板固定 0.5–1.0 不同，勿统一）
    contour_levels = np.linspace(corr_min, corr_max, 6)
    print(f"  (a) 相关系数实际极值: {corr_min:.4f} ~ {corr_max:.4f}")
    print(f"  (c) 调整量实际极值  : {global_min:.4f} ~ {global_max:.4f}")

    # ---- (c) 调整量：对称 ±max(|min|,|max|)，近 0 密、两端疏 ----
    delta_half = max(abs(global_min), abs(global_max))
    delta_bounds = _diverging_bounds(delta_half)
    # 5 档（±1、±6 + 两端实际极值），颜色按原 5 个锚点插值采样，保持同一色系
    _delta_cont = LinearSegmentedColormap.from_list("delta_cont", DELTA_ANCHOR_COLORS)
    delta_colors = [_delta_cont(_t) for _t in np.linspace(0, 1, len(delta_bounds) - 1)]
    # 刻度只标首尾、±1 与 ±6/±16 等关键边界，避免刻度挤在一起
    delta_ticks = sorted({delta_bounds[0], delta_bounds[-1], -1.0, 1.0}
                         | {b for b in delta_bounds[1:-1] if abs(b) in (6.0, 16.0)})

    delta_cmap = ListedColormap(delta_colors)
    delta_norm = BoundaryNorm(delta_bounds, len(delta_colors), clip=True)

    # ============================================================
    # 绘图：3 行 × 3 列
    # ============================================================
    fig_w_cm, fig_h_cm = 14, 22
    fig = plt.figure(figsize=(fig_w_cm / 2.54, fig_h_cm / 2.54))

    def R(l, b, w, h):
        return (l / fig_w_cm, b / fig_h_cm, w / fig_w_cm, h / fig_h_cm)

    pw, ph = 3.7, 4.8    # 地图面板宽高 (cm)
    pgx = 0.9
    lmar = 0.55
    row_h = 6.2           # 每行总高度
    y_gap = 0.4           # 行间距

    row_first_axes = []
    mid_axes = []

    # ---- 统计数据累加器（落盘为 CSV）----
    fig5_stats = []

    for row_idx in range(3):
        y_bot = fig_h_cm - (row_idx + 1) * row_h - row_idx * y_gap
        x_start = lmar
        mid_ax = None

        for c in range(3):
            scenario = SCENARIOS[c]
            ds = datasets[scenario]
            lon = ds["lon"].values.astype(np.float64)
            lat = ds["lat"].values.astype(np.float64)
            Lon, Lat_grid = np.meshgrid(lon, lat)
            w2d = np.cos(np.deg2rad(lat))[:, np.newaxis]

            x_pos = x_start + c * (pw + pgx)
            ax = fig.add_axes(R(x_pos, y_bot, pw, ph), projection=PROJ)
            if c == 0:
                row_first_axes.append(ax)
            if c == 1:
                mid_ax = ax
            ax.set_extent(extent, crs=PROJ)

            # ---- 按行选择数据 ----
            if row_idx == 0:
                # 相关
                r_vals = ds["r"].values
                p_map = ds["p_value"].values
                mask = (np.isfinite(p_map) & (p_map >= 0.05)) | (np.isfinite(r_vals) & (r_vals < 0.5))
                cmap_use = CORR_CMAP
                levels_use = contour_levels
                vmin, vmax = corr_min, corr_max

                valid = np.isfinite(p_map) & np.isfinite(r_vals)
                colored_pct = ((~mask) & valid).sum() / valid.sum() * 100 if valid.sum() > 0 else 0

                ax.contourf(Lon[::2, ::2], Lat_grid[::2, ::2], r_vals[::2, ::2],
                            levels=levels_use, cmap=cmap_use, extend='both', transform=PROJ)
                if np.any(mask):
                    ax.contourf(Lon[::2, ::2], Lat_grid[::2, ::2],
                                mask.astype(float)[::2, ::2],
                                levels=[0.5, 1.5], colors=["grey"], alpha=0.55, transform=PROJ)
                ax_pos = ax.get_position()
                fig.text((ax_pos.x0 + ax_pos.x1) / 2, ax_pos.y0 - 0.025,
                         f"p < 0.05 and r >= 0.5: {colored_pct:.1f}%",
                         ha="center", va="top", fontsize=8)

                # Mean 只统计显著格点（图上着色部分），与灰色掩膜互补
                _w = np.broadcast_to(w2d, r_vals.shape)
                _sel = (~mask) & np.isfinite(r_vals)
                wm = float(np.nansum(r_vals[_sel] * _w[_sel]) / np.nansum(_w[_sel]))
                fig5_stats.append({'panel': 'a_correlation', 'scenario': SCENARIO_LABELS[scenario], 'field': 'r', 'mean_area_weighted': float(wm), 'pct_p_lt_005_and_r_ge_05': float(colored_pct)})
                ax_pos = ax.get_position()
                fig.text((ax_pos.x0 + ax_pos.x1) / 2, ax_pos.y1 + 0.012,
                         f"Mean: {wm:.3f}", ha="center", va="bottom",
                         fontsize=8)


            elif row_idx == 1:
                # 不确定性缩减
                reduction = ds["reduction"].values
                p_map = ds["p_value"].values
                r_vals = ds["r"].values
                # 有效格点判据：p<0.05 且 r>=0.5（与 (a) 行一致，同论文正文口径）
                mask = (np.isfinite(p_map) & (p_map >= 0.05)) | (np.isfinite(r_vals) & (r_vals < 0.5))

                all_vals = np.concatenate([datasets[s]["reduction"].values.ravel() for s in SCENARIOS])
                all_valid = all_vals[np.isfinite(all_vals)]
                r_min = float(all_valid.min()) if len(all_valid) > 0 else 0.0
                r_max = float(all_valid.max()) if len(all_valid) > 0 else 1.0

                # 首尾取实际极值（r_min/r_max 已在上方按三情景并集算出），档数维持 5 档
                bounds = np.linspace(r_min, r_max, 6)
                colors_use = CLASS_COLORS[:len(bounds) - 1]
                cmap_use = ListedColormap(colors_use)
                class_norm = BoundaryNorm(bounds, cmap_use.N, clip=True)

                ax.contourf(Lon[::2, ::2], Lat_grid[::2, ::2], reduction[::2, ::2],
                            levels=bounds, colors=colors_use, extend='both', transform=PROJ)
                if np.any(mask):
                    ax.contourf(Lon[::2, ::2], Lat_grid[::2, ::2],
                                mask.astype(float)[::2, ::2],
                                levels=[0.5, 1.5], colors=["grey"], alpha=0.55, transform=PROJ)

                # Mean 只统计显著格点（图上着色部分），与灰色掩膜互补
                _w = np.broadcast_to(w2d, reduction.shape)
                _sel = (~mask) & np.isfinite(reduction)
                wm = float(np.nansum(reduction[_sel] * _w[_sel]) / np.nansum(_w[_sel]))
                fig5_stats.append({'panel': 'b_reduction', 'scenario': SCENARIO_LABELS[scenario], 'field': 'reduction_sigma_caliber_significant_only', 'mean_area_weighted': float(wm)})
                ax_pos = ax.get_position()
                fig.text((ax_pos.x0 + ax_pos.x1) / 2, ax_pos.y1 + 0.012,
                         f"Mean: {wm:.3f}", ha="center", va="bottom",
                         fontsize=8)

                levels_use = bounds

            else:
                # 后验-先验差值
                posterior = ds["posterior_mean"].values
                prior = ds["prior_mean"].values
                delta = posterior - prior
                p_map = ds["p_value"].values
                r_vals = ds["r"].values
                # 有效格点判据：p<0.05 且 r>=0.5（与 (a) 行一致，同论文正文口径）
                mask = (np.isfinite(p_map) & (p_map >= 0.05)) | (np.isfinite(r_vals) & (r_vals < 0.5))

                cmap_use = delta_cmap
                levels_use = delta_bounds

                ax.contourf(Lon[::2, ::2], Lat_grid[::2, ::2], delta[::2, ::2],
                            levels=delta_bounds, colors=delta_colors, extend='both', transform=PROJ)
                if np.any(mask):
                    ax.contourf(Lon[::2, ::2], Lat_grid[::2, ::2],
                                mask.astype(float)[::2, ::2],
                                levels=[0.5, 1.5], colors=["grey"], alpha=0.55, transform=PROJ)
                ax.contour(Lon[::2, ::2], Lat_grid[::2, ::2], delta[::2, ::2],
                           levels=delta_bounds, transform=PROJ, colors="black", linewidths=0.3)

                # Mean 只统计显著格点（图上着色部分），与灰色掩膜互补
                _w = np.broadcast_to(w2d, delta.shape)
                _sel = (~mask) & np.isfinite(delta)
                wm = float(np.nansum(delta[_sel] * _w[_sel]) / np.nansum(_w[_sel]))
                fig5_stats.append({'panel': 'c_posterior_minus_prior', 'scenario': SCENARIO_LABELS[scenario], 'field': 'posterior_mean - prior_mean', 'mean_area_weighted': float(wm)})
                ax_pos = ax.get_position()
                fig.text((ax_pos.x0 + ax_pos.x1) / 2, ax_pos.y1 + 0.012,
                         f"Mean: {wm:.2f}", ha="center", va="bottom",
                         fontsize=8)


            # ---- 通用地图元素 ----
            ax.add_geometries(cn_geoms, crs=ccrs.PlateCarree(), facecolor='none',
                              edgecolor='#999999', linewidth=0.5)


            ax_title_pos = ax.get_position()
            fig.text((ax_title_pos.x0 + ax_title_pos.x1) / 2, ax_title_pos.y1 + 0.025,
                         SCENARIO_LABELS[scenario], ha="center", va="bottom",
                         fontsize=11, fontweight="normal")

            gl = ax.gridlines(draw_labels=True, linewidth=0.2, alpha=0.4, linestyle='--',
                              xlocs=[80, 90, 110, 130], ylocs=[10, 20, 30, 40, 50])
            gl.top_labels = False
            gl.right_labels = False
            gl.xlabel_style = {"size": 9}
            gl.ylabel_style = {"size": 9}
            try:
                ax.spines["geo"].set_visible(False)
            except Exception:
                pass


        # ---- 每行色带 ----
        if mid_ax is not None:
            x0, x1, y0 = mid_ax.get_position().x0, mid_ax.get_position().x1, mid_ax.get_position().y0
            cbar_w = (x1 - x0) * 1.80
            cx = (x0 + x1) / 2
            cbar_offset = 0.048 if row_idx == 0 else 0.035
            cax = fig.add_axes((cx - cbar_w / 2, y0 - cbar_offset, cbar_w, 0.007))

            if row_idx == 0:
                sm = plt.cm.ScalarMappable(norm=Normalize(corr_min, corr_max), cmap=CORR_CMAP)
                sm.set_array([])
                cbar = fig.colorbar(sm, cax=cax, orientation="horizontal",
                                    extend="both", extendfrac=0.04, ticks=contour_levels)
                cbar.ax.xaxis.set_major_formatter(FuncFormatter(_fmt_tick))
                cbar.ax.tick_params(labelsize=10)
                cbar.set_label("Correlation r", fontsize=10)

            elif row_idx == 1:
                sm = plt.cm.ScalarMappable(norm=class_norm, cmap=cmap_use)
                sm.set_array([])
                cbar = fig.colorbar(sm, cax=cax, orientation="horizontal",
                                    extend="both", extendfrac=0.04, ticks=bounds)
                cbar.ax.xaxis.set_major_formatter(FuncFormatter(lambda v, _: _fmt_tick(v * 100) + "%"))
                cbar.ax.tick_params(labelsize=10)
                cbar.set_label("Uncertainty Reduction (σ)", fontsize=10)
            else:
                sm = plt.cm.ScalarMappable(norm=delta_norm, cmap=delta_cmap)
                sm.set_array([])
                cbar = fig.colorbar(sm, cax=cax, orientation="horizontal",
                                    extend="both", extendfrac=0.04, ticks=delta_ticks)
                cbar.ax.xaxis.set_major_formatter(FuncFormatter(_fmt_tick))
                cbar.ax.tick_params(labelsize=10)
                cbar.set_label("Posterior − Prior (mm/day)", fontsize=10)

            # 灰色掩膜图例：仅画在 (a) 行（三行的灰色含义相同，见图注说明）。
            # 左边界取本行首面板左缘、竖直自色带中线向下挂。
            if row_idx == 0:
                _cb = cax.get_position()
                fig.legend(handles=[Patch(facecolor="grey", alpha=0.55, edgecolor="none",
                                          label="p >= 0.05 or r < 0.5")],
                           loc="upper left",
                           bbox_to_anchor=(row_first_axes[row_idx].get_position().x0 - 0.02,
                                           # 相对首面板左缘再左移 0.02（figure 比例）
                                           _cb.y0 + _cb.height / 2.0),
                           bbox_transform=fig.transFigure,
                           fontsize=8, framealpha=0.9, borderpad=0.4, handlelength=1.2)

        if mid_ax is not None:
            mid_axes.append(mid_ax)

    # ---- 行标签 (a)(b)(c) ----
    for row_idx, first_ax in enumerate(row_first_axes):
        pos = first_ax.get_position()
        fig.text(pos.x0 - 0.02, pos.y1 + 0.05,
                 f"({chr(ord('a') + row_idx)})",
                 fontsize=15, ha="right", va="bottom", fontweight="normal")

    # ---- 行标题（每行中间子图上方）----
    for row_idx, mid_ax in enumerate(mid_axes):
        pos = mid_ax.get_position()
        fig.text((pos.x0 + pos.x1) / 2, pos.y1 + 0.05,
                 ROW_TITLES[row_idx], ha="center", va="bottom",
                 fontsize=13, fontweight="normal")

    fig.savefig(OUTPUT_DIR / "Fig5.jpg", dpi=400, bbox_inches="tight")
    print(f'\n图形已保存至: {OUTPUT_DIR / "Fig5.jpg"}')

    # ---- 统计数据落盘为 CSV ----
    _stats_path = ROOT / "data" / "fig5_stats.csv"
    _stats_path.parent.mkdir(parents=True, exist_ok=True)
    pd.DataFrame(fig5_stats).to_csv(_stats_path, index=False, encoding="utf-8-sig")
    print(f"统计数据已保存至: {_stats_path}")
    plt.close(fig)


# ============================================================
# 命令行入口：默认按原顺序依次渲染 a → b → c → 组图
# ============================================================
PIPELINE_ORDER = ("a", "b", "c", "composite")

_PANEL_ALIASES = {
    "a": "a", "fig5a": "a", "fig5a.py": "a",
    "b": "b", "fig5b": "b", "fig5b.py": "b",
    "c": "c", "fig5c": "c", "fig5c.py": "c",
    "composite": "composite", "fig5": "composite", "fig5.py": "composite", "all": "all",
}


def _resolve_selection(only: str):
    """把 --only 的取值解析为按流水线顺序排列的待渲染阶段元组。"""
    tokens = [t.strip().lower() for t in str(only).split(",") if t.strip()]
    if not tokens or "all" in tokens:
        return PIPELINE_ORDER
    unknown = [t for t in tokens if t not in _PANEL_ALIASES]
    if unknown:
        raise SystemExit(f"未知的面板名: {', '.join(unknown)}；可选 a / b / c / composite / all")
    chosen = {_PANEL_ALIASES[t] for t in tokens}
    return tuple(stage for stage in PIPELINE_ORDER if stage in chosen)


def parse_args(argv=None):
    parser = argparse.ArgumentParser(
        prog="Fig5.py",
        description="Fig. 5 单文件流水线：fig5a/b/c.jpg 单面板渲染 + Fig5.jpg 组图与 data/fig5_stats.csv",
        epilog="渲染顺序固定为 a → b → c → composite，与 --only 中的书写顺序无关。")
    parser.add_argument("-o", "--only", default="all", metavar="PANELS",
                        help="只渲染指定面板：a / b / c / composite 的逗号组合，或 all（默认全部）。")
    return parser.parse_args(argv)


_TMP_DIR_BASES = (REPO_ROOT.parent, Path(tempfile.gettempdir()))


def _open_panel_tmpdir():
    """建一个承载单面板 JPG 的运行期临时目录（模块目录之外），返回 (目录 Path, 清理函数)。

    一律用 `os.makedirs()` 的**默认权限**建目录；**不要**改用 `tempfile.TemporaryDirectory()` /
    `mkdtemp()` —— 它们在 Windows 上以 mode=0o700 建目录（只授权属主、去掉继承），在受限令牌 /
    沙箱下会连创建进程自己都无法写入，chmod 与删除也会被拒，留下永久锁死的空目录。
    清理统一交给 `shutil.rmtree(..., ignore_errors=True)`，在 main() 的 finally 中执行。
    """
    name = f"_tmp_fig5_{uuid.uuid4().hex[:8]}"
    last_err = None
    for base in _TMP_DIR_BASES:
        d = base / name
        try:
            os.makedirs(d)             # 默认权限，绝不传 mode=0o700
            _probe = d / ".write_probe"
            _probe.write_bytes(b"")
            _probe.unlink()
        except OSError as exc:
            last_err = exc
            shutil.rmtree(d, ignore_errors=True)
            continue
        return d, lambda: shutil.rmtree(d, ignore_errors=True)

    raise RuntimeError(
        f"无法创建单面板临时目录（已尝试 {[str(b) for b in _TMP_DIR_BASES]}）：{last_err}")


def main(argv=None) -> None:
    selected = _resolve_selection(parse_args(argv).only)
    print(f"待渲染阶段: {', '.join(selected)}")

    print('=' * 60)
    print('Fig. 5: 加载数据')
    print('=' * 60)
    cn_geoms, extent = load_china_geoms()
    datasets = load_datasets()

    # ①②③ 单面板图写到运行期临时目录：用完（finally）即整体删除，
    # 模块根只保留 ④ 的成品 Fig5.jpg 与 data/fig5_stats.csv。
    if any(stage in selected for stage in ("a", "b", "c")):
        tmp_dir, _cleanup_tmp = _open_panel_tmpdir()
        try:
            print(f"单面板临时输出目录: {tmp_dir}（本次运行结束自动清理）")
            if "a" in selected:
                print("(a) 相关系数单面板 → 临时 fig5a.jpg")
                render_panel_a(datasets, cn_geoms, extent, tmp_dir / "fig5a.jpg")
            if "b" in selected:
                print("(b) 不确定性缩减单面板 → 临时 fig5b.jpg")
                render_panel_b(datasets, cn_geoms, extent, tmp_dir / "fig5b.jpg")
            if "c" in selected:
                print("(c) 后验−先验差值单面板 → 临时 fig5c.jpg")
                render_panel_c(datasets, cn_geoms, extent, tmp_dir / "fig5c.jpg")
        finally:
            _cleanup_tmp()

    if "composite" in selected:
        print("(a)(b)(c) 3×3 成品组图 → Fig5.jpg + data/fig5_stats.csv")
        render_composite(datasets, cn_geoms, extent)


if __name__ == "__main__":
    main()
