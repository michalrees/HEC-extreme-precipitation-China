"""
Fig. 3 —— 历史时期（1981–2010）HiCPC 多模式集合平均（MME）与 CN05.1 观测
在极端降水强度（R95 Intensity）和降水变率（PrecipVar）上的偏差空间分布
（Bias = OBS − MME）。

本模块为**单文件流水线**（原 `extract_bias.py` + `Fig3.py` 合并为一个脚本）：
  第 1 步 数据准备（原 extract_bias.py）：
      读取兄弟模块 `../Fig2_ModelEvaluation/data/` 下的
      `MULTI_MODEL-historical-1981-2010.nc` 与 `CN05-OBS-1981-2010.nc`，
      取共同年份（限定 1981–2010），把各模式指标场以面积重叠权重 × cos(lat)
      重映射到观测网格，再计算 `bias = CN05 气候态 − HiCPC MME 气候态`，
      与两套气候态一起写入本模块 `data/` 下的 3 个 NetCDF。
  第 2 步 绘图（原 Fig3.py）：
      读取 `data/Bias_*.nc`，绘制 1 行 × 2 列的偏差空间分布图
      (a) R95 Intensity、(b) PrecipVar：等值线填色叠加中国矢量边界，
      色带以 0 为中心对称分级，蓝色表示 MME 高估（负偏差），红色表示 MME 低估（正偏差），
      各面板左下角嵌入 PDF 直方图展示偏差值的分布特征，
      色带上方标注面积加权区域平均偏差值，色标单位 mm/day；
      同时把每个面板的统计量落盘为 txt 与 CSV。

运行一次 `python Fig3.py` 即可完整复现 `Fig3.jpg`、`data/Bias_historical.nc`、
`data/CN05_clim_historical.nc`、`data/MME_clim_historical.nc`、
`data/图3_统计数据.txt`、`data/fig3_stats.csv`。
"""

from __future__ import annotations
from pathlib import Path
from typing import Any, Dict, List

import numpy as np
import pandas as pd
import xarray as xr
import matplotlib.pyplot as plt
import cartopy.crs as ccrs
import shapefile
from shapely.geometry import shape as shapely_shape
from matplotlib.ticker import FuncFormatter
from matplotlib.colors import BoundaryNorm, LinearSegmentedColormap
import warnings

warnings.filterwarnings("ignore")


# ==================== 路径配置 ====================
MODULE_DIR = Path(__file__).resolve().parent
# 本模块 data/：数据准备的写盘目录，也是绘图的数据读取目录
# （原 extract_bias.py 的 OUTPUT_DIR、原 Fig3.py 的 BIAS_DIR 统一到这里）
DATA_DIR = MODULE_DIR / "data"
# 兄弟模块 Fig2 的 data/：一级向上引用，数据准备阶段的只读输入
FIG2_DATA_DIR = MODULE_DIR.parent / "Fig2_ModelEvaluation" / "data"
MODEL_FILE = FIG2_DATA_DIR / "MULTI_MODEL-historical-1981-2010.nc"
OBS_FILE = FIG2_DATA_DIR / "CN05-OBS-1981-2010.nc"
# 图片与统计量的输出目录（模块根）
OUTPUT_DIR = MODULE_DIR

REPO_ROOT = next(p for p in Path(__file__).resolve().parents if (p / "src").is_dir() and (p / "Doc").is_dir())

# ---- 数据根目录 ----------------
# src/、Output/、Data/ 现均在论文文件夹内（与 Doc/ 同级），故直接取 REPO_ROOT/Data；
# 若将来数据被移到别处，再恢复向上搜索的兜底逻辑。
DATA_ROOT = REPO_ROOT / "Data"
SHP_PATH = DATA_ROOT / "China" / "cnmap.shp"

# 面板 label → 观测文件中的变量名（用于计算偏差的相对幅度）
OBS_VAR_BY_LABEL = {"R95 Intensity": "R95mm_intensity", "PrecipVar": "PrecipVar"}

# ==================== 评估配置 ====================
EVAL_START_YEAR = 1981
EVAL_END_YEAR = 2010

TARGET_METRICS = {
    "R95mm_intensity": {"label": "R95 Intensity", "unit": "mm/day"},
    "PrecipVar": {"label": "Precip Var index", "unit": "(same as input)"},
}


def _fmt_tick(v, _pos=None):
    """刻度标签：整数不带小数，非整数保留 1 位小数（全图统一口径）。"""
    return f"{v:.0f}" if abs(v - round(v)) < 1e-9 else f"{v:.1f}"


plt.rcParams["font.family"] = "Times New Roman"
plt.rcParams["mathtext.fontset"] = "cm"
plt.rcParams["axes.unicode_minus"] = False

MAP_PARAMS = {
    "font_title": 14,
    "font_tick": 10,
    "font_cbar": 11,
    "line_grid": 0.3,
    "line_boundary": 0.5,
    "line_contour": 0.4,
    "cbar_offset": 0.095,
    "cbar_w_ratio": 0.8,
    "cbar_h": 0.020,
    "font_stat": 12,        # 色带上方统计文字字号
    "stat_offset": 0.050,   # 统计文字距地图底边的偏移
}

# 自定义色带
R95_COLORS = ["#315484", "#568588", "#84B0D3", "#82D1DF", "#CCD7BC",
               "#FEF2B6", "#FDC780", "#F58A58", "#D64736", "#992323"]
VAR_COLORS = ["#7195DB", "#D0E8F8", "#90C0D8", "#708A98",
               "#F5F7F7", "#E2CCB2", "#E9AF99", "#D96E57"]

if "r95_cmap" not in plt.colormaps():
    plt.colormaps.register(LinearSegmentedColormap.from_list("r95_cmap", R95_COLORS))
if "precipvar_cmap" not in plt.colormaps():
    plt.colormaps.register(LinearSegmentedColormap.from_list("precipvar_cmap", VAR_COLORS))


# ==================== 第 1 步：偏差场提取（原 extract_bias.py） ====================
# ---- 复用 Fig2b 的数据加载 / 网格重映射逻辑 ----
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
            ds = ds.assign_coords({
                "case": ("case", np.asarray(case_vals, dtype=object)),
                "Mode": ("case", np.asarray(mode_vals, dtype=object)),
            })
        else:
            raise ValueError(f"文件缺少 case/Mode 维度: {fp}")
    elif "Mode" not in ds.coords:
        mode_vals = [str(v).split("-ssp")[0] for v in ds["case"].values]
        ds = ds.assign_coords({"Mode": ("case", np.asarray(mode_vals, dtype=object))})

    if "SSP" not in ds.coords:
        ds = ds.assign_coords({"SSP": ("case", np.array([file_ssp] * ds.sizes["case"], dtype=object))})
    if "source_file" not in ds.coords:
        ds = ds.assign_coords({"source_file": ("case", np.array([fp.name] * ds.sizes["case"], dtype=object))})
    ds = ds.assign_attrs({**ds.attrs, "model_source_file": str(fp)})
    return ds


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


def _cell_bounds_from_centers(coord_1d: np.ndarray):
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


def _area_weighted_remap_numpy(src_data, lat_overlap, lon_overlap, src_lat_cos):
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
        out_np,
        dims=lead_dims + ["lat", "lon"],
        coords={**lead_coords, "lat": obs_da["lat"], "lon": obs_da["lon"]},
        name=src.name,
        attrs=src.attrs,
    )


def remap_model_to_obs_grid(model_ds: xr.Dataset, obs_ds: xr.Dataset, metric_names: List[str]) -> xr.Dataset:
    remapped_vars: Dict[str, xr.DataArray] = {}
    for name in metric_names:
        remapped_vars[name] = area_weighted_remap_da_to_obs_grid(model_ds[name], obs_ds[name])
    out = xr.Dataset(remapped_vars)
    for coord_name in ["case", "Mode", "SSP", "source_file"]:
        if coord_name in model_ds.coords and coord_name not in out.coords:
            out = out.assign_coords({coord_name: model_ds.coords[coord_name]})
    out.attrs.update(model_ds.attrs)
    return out


def extract_bias() -> None:
    """提取 CN05 − HiCPC MME 偏差场 (Bias) 并保存为 NetCDF。"""
    print("=" * 70)
    print("提取 CN05 − HiCPC MME 偏差场 (Bias)")
    print(f"模型文件: {MODEL_FILE}")
    print(f"观测文件: {OBS_FILE}")
    print("=" * 70)

    if not MODEL_FILE.exists():
        raise FileNotFoundError(f"模型文件不存在: {MODEL_FILE}")
    if not OBS_FILE.exists():
        raise FileNotFoundError(f"观测文件不存在: {OBS_FILE}")

    DATA_DIR.mkdir(parents=True, exist_ok=True)

    # 加载数据
    obs_ds = xr.open_dataset(OBS_FILE)
    model_ds = load_model_dataset_from_file(MODEL_FILE)

    # 筛选共同年份
    common_years = get_common_years(model_ds, obs_ds)
    model_sel = model_ds.sel(year=common_years)
    obs_sel = obs_ds.sel(year=common_years)

    # 重映射到观测网格
    model_sel = remap_model_to_obs_grid(model_sel, obs_sel, list(TARGET_METRICS.keys()))

    print(f"  共同年份: {int(common_years.min())}-{int(common_years.max())} ({common_years.size} 年)")
    print(f"  case 数量: {model_sel.sizes['case']}")

    scenario = get_scenario_from_filename(MODEL_FILE)

    # 逐指标计算 bias 并保存
    bias_vars: Dict[str, xr.DataArray] = {}
    for metric_name, meta in TARGET_METRICS.items():
        print(f"\n指标: {meta['label']} ({metric_name})")

        obs_mean = obs_sel[metric_name].mean(dim="year")          # CN05 气候态
        mme_mean = model_sel[metric_name].mean(dim="case").mean(dim="year")  # MME 气候态
        bias = obs_mean - mme_mean                                # CN05 − MME

        bias.name = f"{metric_name}_bias"
        bias.attrs = {
            "long_name": f"Bias (CN05 − HiCPC MME) of {meta['label']}",
            "units": meta["unit"],
            "scenario": scenario,
            "period": f"{int(common_years.min())}-{int(common_years.max())}",
        }
        bias_vars[metric_name] = bias

        print(f"  Bias 范围: {float(bias.min().values):.4f} ~ {float(bias.max().values):.4f} {meta['unit']}")

    # 同时保存观测和 MME 气候态，方便后续对比
    obs_vars = {}
    mme_vars = {}
    for metric_name in TARGET_METRICS:
        obs_mean = obs_sel[metric_name].mean(dim="year")
        obs_mean.name = metric_name
        obs_mean.attrs["long_name"] = f"CN05 {TARGET_METRICS[metric_name]['label']} climatology"
        obs_mean.attrs["units"] = TARGET_METRICS[metric_name]["unit"]
        obs_vars[metric_name] = obs_mean

        mme_mean = model_sel[metric_name].mean(dim="case").mean(dim="year")
        mme_mean.name = metric_name
        mme_mean.attrs["long_name"] = f"HiCPC MME {TARGET_METRICS[metric_name]['label']} climatology"
        mme_mean.attrs["units"] = TARGET_METRICS[metric_name]["unit"]
        mme_vars[metric_name] = mme_mean

    # 保存 Bias 数据集
    bias_ds = xr.Dataset(bias_vars, attrs={
        "title": "CN05 − HiCPC MME Bias",
        "scenario": scenario,
        "period": f"{int(common_years.min())}-{int(common_years.max())}",
        "description": "Bias = CN05 observation minus HiCPC multi-model ensemble mean",
    })
    bias_path = DATA_DIR / f"Bias_{scenario}.nc"
    bias_ds.to_netcdf(bias_path)
    print(f"\nBias 文件: {bias_path}")

    # 同时保存 CN05 和 MME 气候态，方便画图直接用
    obs_ds_out = xr.Dataset(obs_vars, attrs={
        "title": "CN05 climatology",
        "scenario": scenario,
        "period": f"{int(common_years.min())}-{int(common_years.max())}",
    })
    obs_path = DATA_DIR / f"CN05_clim_{scenario}.nc"
    obs_ds_out.to_netcdf(obs_path)
    print(f"CN05 气候态: {obs_path}")

    mme_ds_out = xr.Dataset(mme_vars, attrs={
        "title": "HiCPC MME climatology",
        "scenario": scenario,
        "period": f"{int(common_years.min())}-{int(common_years.max())}",
    })
    mme_path = DATA_DIR / f"MME_clim_{scenario}.nc"
    mme_ds_out.to_netcdf(mme_path)
    print(f"MME 气候态:  {mme_path}")

    print("\n提取完成。")


# ==================== 第 2 步：绘图 ====================
def _draw_panel(ax, field, levels, cmap, cn_geoms, region, params):
    """Draw a single spatial panel (contour + boundary + PDF)."""
    ax.set_extent([region["lon_min"], region["lon_max"],
                   region["lat_min"], region["lat_max"]])
    ax.contourf(field.lon, field.lat, field, levels=levels, cmap=cmap, extend="both")
    ax.contour(field.lon, field.lat, field, levels=levels, colors="black", linewidths=params["line_contour"])
    ax.add_geometries(cn_geoms, crs=ccrs.PlateCarree(), facecolor="none",
                      edgecolor="#888888", linewidth=params["line_boundary"])
    gl = ax.gridlines(draw_labels=True, linewidth=params["line_grid"], alpha=0.4, linestyle="--")
    gl.top_labels = False; gl.right_labels = False
    gl.xlabel_style = {"size": params["font_tick"]}; gl.ylabel_style = {"size": params["font_tick"]}
    try:
        ax.spines["geo"].set_visible(False)
    except Exception:
        pass

    # 内嵌 PDF 直方图
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
        for sp in hist_ax.spines.values():
            sp.set_linewidth(0.3)
        hist_ax.spines["top"].set_visible(False)
        hist_ax.spines["right"].set_visible(False)


def plot_bias_panels(
    bias_rows: List[Dict[str, Any]],
    save_path: Path | None = None,
) -> None:
    """1 行 x 2 列: Precip Var Bias | R95 Intensity Bias，只画偏差场。"""
    n_panels = len(bias_rows)
    if n_panels == 0:
        return

    sf = shapefile.Reader(str(SHP_PATH))
    cn_geoms = [shapely_shape(s.__geo_interface__) for s in sf.shapes()]
    shp_bbox = sf.bbox
    region = {
        "lon_min": float(shp_bbox[0]) - 1,
        "lon_max": float(shp_bbox[2]) + 1,
        "lat_min": float(shp_bbox[1]) - 1,
        "lat_max": float(shp_bbox[3]) + 1,
    }

    dlon = region["lon_max"] - region["lon_min"]
    dlat = region["lat_max"] - region["lat_min"]
    clat = np.deg2rad((region["lat_min"] + region["lat_max"]) / 2)
    map_aspect = (dlat / dlon) / np.cos(clat)

    # 对齐 Fig2 格式：20 cm 基准宽度，单幅地图宽 7 cm，列间距 1.6 cm
    fig_w_cm, fig_h_cm = 20.0, 14.0
    mw = 7.0
    mh = mw * map_aspect
    mgx = 1.6
    mx0 = 1.0
    my0 = max(1.0, (fig_h_cm - mh) / 2)

    fig = plt.figure(figsize=(fig_w_cm / 2.54, fig_h_cm / 2.54))
    axes = np.empty((1, n_panels), dtype=object)

    def R_b(l, b, w, h):
        return (l / fig_w_cm, b / fig_h_cm, w / fig_w_cm, h / fig_h_cm)

    for c in range(n_panels):
        mx = mx0 + c * (mw + mgx)
        axes[0, c] = fig.add_axes(R_b(mx, my0, mw, mh), projection=ccrs.PlateCarree())

    # ---- 观测气候态（面积加权区域平均），用于把偏差写成相对幅度 ----
    obs_mean_by_label: Dict[str, float] = {}
    if OBS_FILE.exists():
        with xr.open_dataset(OBS_FILE) as obs_ds:
            _lat = np.asarray(obs_ds["lat"].values, dtype=np.float64)
            _latw = np.clip(np.cos(np.deg2rad(_lat)), 0.0, None)
            for _lbl, _var in OBS_VAR_BY_LABEL.items():
                if _var not in obs_ds.data_vars:
                    continue
                _a = obs_ds[_var]
                if "year" in _a.dims:
                    _a = _a.sel(year=slice(1981, 2010)).mean(dim="year")
                _v = np.asarray(_a.values, dtype=np.float64)          # (lat, lon)
                _m = np.isfinite(_v)
                _w = np.broadcast_to(_latw[:, None], _v.shape)
                obs_mean_by_label[_lbl] = float((_v[_m] * _w[_m]).sum() / _w[_m].sum())
        print(f"  观测气候态（面积加权）: " + ", ".join(f"{k}={v:.4f}" for k, v in obs_mean_by_label.items()))
    else:
        print(f"  提示: 未找到 {OBS_FILE}，相对偏差将记为 NaN")

    stats_records: List[Dict[str, Any]] = []
    for c, row in enumerate(bias_rows):
        bias_map = row["bias_map"]
        cmap_main = str(row["cmap_main"])
        label = str(row["label"])

        bias_min = float(np.nanmin(bias_map.values))
        bias_max_data = float(np.nanmax(bias_map.values))
        n_intervals = 10 if cmap_main == "r95_cmap" else 8
        # 色带上下限完全取实际极值：以 0 为中心对称取 ±max(|min|, |max|)。
        # 不再做“整数步长”取整、也不设硬编码下限（原 min_half = 56/11 已移除），
        # 因此色带两端恰好等于数据极值，最外侧分级区间不再被放大。
        half_range = max(abs(bias_min), abs(bias_max_data))
        bias_levels = np.linspace(-half_range, half_range, n_intervals + 1)

        _draw_panel(axes[0, c], bias_map, bias_levels, cmap_main, cn_geoms, region, MAP_PARAMS)
        # 子图标签（轴外左上角）
        pos = axes[0, c].get_position()
        fig.text(pos.x0 - 0.02, pos.y1 + 0.02, f"({chr(ord('a') + c)})",
                 fontsize=13, ha="right", va="bottom", fontweight="normal")
        axes[0, c].axis("off")
        axes[0, c].set_title(label, fontsize=MAP_PARAMS["font_title"], fontweight="normal", pad=8)

        # 色带
        ax_pos = axes[0, c].get_position()
        cax_w = ax_pos.width * MAP_PARAMS["cbar_w_ratio"]
        cax_x = ax_pos.x0 + (ax_pos.width - cax_w) / 2
        cax = fig.add_axes((cax_x, ax_pos.y0 - MAP_PARAMS["cbar_offset"],
                    cax_w, MAP_PARAMS["cbar_h"]))
        norm_b = BoundaryNorm(bias_levels, ncolors=256, extend="both")
        n_all = len(bias_levels)
        # 取 5 个刻度并四舍五入到最近的 levels 下标，保证刻度以 0 为中心对称
        sel_idx = np.unique(np.round(np.linspace(0, n_all - 1, min(5, n_all))).astype(int))
        sel_ticks = bias_levels[sel_idx]
        fig.colorbar(plt.cm.ScalarMappable(norm=norm_b, cmap=row["cmap_main"]),
                     cax=cax, orientation="horizontal", extend="both",
                     extendfrac=0.04, ticks=sel_ticks)
        cax.xaxis.set_major_formatter(FuncFormatter(_fmt_tick))
        cax.set_xlabel(row["unit"], fontsize=MAP_PARAMS["font_cbar"], labelpad=0)
        cax.tick_params(labelsize=MAP_PARAMS["font_tick"])

        # 记录本面板的统计量（供 data/ 落盘）
        lat_w = np.clip(np.cos(np.deg2rad(np.asarray(bias_map["lat"].values, dtype=np.float64))), 0.0, None)
        w_map = np.broadcast_to(lat_w[:, None], bias_map.shape)
        ok_map = np.isfinite(bias_map.values)
        mean_w = float((bias_map.values[ok_map] * w_map[ok_map]).sum() / w_map[ok_map].sum())

        # ---- 偏差的派生指标（供正文引用）----
        # 相对偏差：|面积加权平均偏差| / 观测气候态（sign 保留，正=MME 低估）
        obs_mean_w = obs_mean_by_label.get(label, float("nan"))
        rel_bias_pct = (mean_w / obs_mean_w * 100.0) if np.isfinite(obs_mean_w) and obs_mean_w else float("nan")
        # 低估/高估的面积占比（面积加权）：bias = OBS − MME > 0 即 MME 低估
        _ww = w_map[ok_map]
        _pos = bias_map.values[ok_map] > 0
        pct_under = float(_ww[_pos].sum() / _ww.sum() * 100.0)
        median_abs_bias = float(np.nanmedian(np.abs(bias_map.values[ok_map])))

        # 色带上方标注面积加权区域平均偏差值
        fig.text(ax_pos.x0 + ax_pos.width / 2, ax_pos.y0 - MAP_PARAMS["stat_offset"],
                 f"Mean bias = {mean_w:+.2f} {str(row['unit']).split(' ')[0]}",
                 ha="center", va="center", fontsize=MAP_PARAMS["font_stat"], fontweight="normal")

        stats_records.append({
            "label": label,
            "unit": row["unit"],
            "vmin": float(bias_min),
            "vmax": float(bias_max_data),
            "mean_unweighted": float(np.nanmean(bias_map.values)),
            "mean_area_weighted": mean_w,
            "obs_mean_area_weighted": obs_mean_w,
            "mme_mean_area_weighted": (obs_mean_w - mean_w) if np.isfinite(obs_mean_w) else float("nan"),
            "rel_bias_pct": rel_bias_pct,
            "pct_area_underestimated": pct_under,
            "median_abs_bias": median_abs_bias,
            "levels": [float(v) for v in bias_levels],
            "ticks": [float(v) for v in sel_ticks],
        })

    # ---- 统计数据落盘（txt + CSV，均落在 data/）----
    stats_path = DATA_DIR / "图3_统计数据.txt"
    dump_bias_statistics(stats_records, stats_path)
    print(f"  统计数据: {stats_path}")

    stats_csv_path = DATA_DIR / "fig3_stats.csv"
    dump_bias_statistics_csv(stats_records, stats_csv_path)
    print(f"  统计数据(CSV): {stats_csv_path}")

    if save_path is not None:
        plt.savefig(save_path.with_suffix(".jpg"), format="jpg", dpi=400, bbox_inches="tight")
    plt.close(fig)


# ==================== 统计数据落盘 ====================
def dump_bias_statistics(records, out_path) -> None:
    """把图 3 用到的偏差统计量写成纯文本（data/ 目录）。

    参数:
        records: 每个面板的 vmin / vmax / 均值 / 分级 / 色带刻度。
        out_path: 输出 txt 路径。
    """
    lines = [
        "Fig. 3 statistics - Bias (CN05 - HiCPC MME) spatial distribution",
        "script  : src/Pic/Fig3_BiasSpatialMaps/Fig3.py",
        "input   : data/Bias_historical.nc (produced by extract_bias.py)",
        "period  : 1981-2010",
        "modes   : 19",
        "weight  : area-weighted, w = cos(lat)",
        "",
    ]
    for rec in records:
        lines.append(f"[{rec['label']}]  unit: {rec['unit']}")
        lines.append(f"  min                  : {rec['vmin']:.4f}")
        lines.append(f"  max                  : {rec['vmax']:.4f}")
        lines.append(f"  mean (unweighted)    : {rec['mean_unweighted']:.4f}")
        lines.append(f"  mean (area-weighted) : {rec['mean_area_weighted']:+.4f}   <- 正文引用的偏差")
        lines.append(f"  obs mean (area-wtd)  : {rec['obs_mean_area_weighted']:.4f}")
        lines.append(f"  mme mean (area-wtd)  : {rec['mme_mean_area_weighted']:.4f}   (obs - bias)")
        lines.append(f"  rel bias vs obs      : {rec['rel_bias_pct']:+.2f} %")
        lines.append(f"  MME-underestimated   : {rec['pct_area_underestimated']:.1f} % of area")
        lines.append(f"  median |bias|        : {rec['median_abs_bias']:.4f}")
        lines.append(f"  levels               : {rec['levels']}")
        lines.append(f"  colorbar ticks       : {rec['ticks']}")
        lines.append("")
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def dump_bias_statistics_csv(records, out_path) -> None:
    """把图 2 用到的偏差统计量写成 CSV（data/ 目录）。

    字段: label, unit, vmin, vmax, mean_unweighted, mean_area_weighted,
          obs_mean_area_weighted, mme_mean_area_weighted, rel_bias_pct,
          pct_area_underestimated, median_abs_bias, levels, ticks
    levels / ticks 为列表，写成以 ";" 分隔的字符串（便于在 CSV 中同时保留
    完整分级信息，且不影响前 6 个标量字段的数值解析）。
    编码使用 utf-8-sig，便于 Excel 直接正确显示中文。

    参数:
        records: 每个面板的 vmin / vmax / 均值 / 分级 / 色带刻度。
        out_path: 输出 csv 路径。
    """
    rows = []
    for rec in records:
        rows.append({
            "label": rec["label"],
            "unit": rec["unit"],
            "vmin": rec["vmin"],
            "vmax": rec["vmax"],
            "mean_unweighted": rec["mean_unweighted"],
            "mean_area_weighted": rec["mean_area_weighted"],
            "obs_mean_area_weighted": rec["obs_mean_area_weighted"],
            "mme_mean_area_weighted": rec["mme_mean_area_weighted"],
            "rel_bias_pct": rec["rel_bias_pct"],
            "pct_area_underestimated": rec["pct_area_underestimated"],
            "median_abs_bias": rec["median_abs_bias"],
            "levels": ";".join(f"{v:g}" for v in rec["levels"]),
            "ticks": ";".join(f"{v:g}" for v in rec["ticks"]),
        })

    df = pd.DataFrame(rows, columns=[
        "label", "unit", "vmin", "vmax",
        "mean_unweighted", "mean_area_weighted",
        "obs_mean_area_weighted", "mme_mean_area_weighted", "rel_bias_pct",
        "pct_area_underestimated", "median_abs_bias",
        "levels", "ticks",
    ])
    out_path.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(out_path, index=False, encoding="utf-8-sig")


def plot_bias_maps() -> None:
    """读取 data/Bias_*.nc，绘制偏差空间分布图并落盘统计量。"""
    print("=" * 70)
    print("CN05 − HiCPC MME Bias 空间分布图（仅偏差场）")
    print("=" * 70)

    bias_files = sorted(Path(DATA_DIR).glob("Bias_*.nc"))
    if not bias_files:
        raise FileNotFoundError(f"未找到 Bias_*.nc 文件，请先运行本脚本的数据提取步骤 ({DATA_DIR})")

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    for bias_fp in bias_files:
        scenario = bias_fp.stem.replace("Bias_", "")
        bias_ds = xr.open_dataset(bias_fp)
        metric_names = list(bias_ds.data_vars.keys())
        print(f"\n情景: {scenario}  指标: {metric_names}")

        bias_rows: List[Dict[str, Any]] = []
        for metric_name in metric_names:
            cmap_main = "r95_cmap" if ("r95" in metric_name.lower() or "R95" in metric_name) else "precipvar_cmap"

            bias_candidates = [metric_name, f"{metric_name}_bias"]
            bias_var = None
            for c in bias_candidates:
                if c in bias_ds.data_vars:
                    bias_var = c
                    break
            if bias_var is None:
                print(f"  跳过 {metric_name}: 未找到偏差变量")
                continue
            bias_map = bias_ds[bias_var]
            # 两幅图色标单位统一为 mm/day（R95 是强度之差；PrecipVar 是标准差之差，量纲同为 mm/day）
            unit = "mm/day"
            metric_label = str(metric_name).replace("R95mm_intensity", "R95 Intensity")

            bias_rows.append({
                "label": metric_label,
                "unit": unit,
                "bias_map": bias_map,
                "cmap_main": cmap_main,
            })

        if bias_rows:
            save_path = OUTPUT_DIR / f"Fig3"
            plot_bias_panels(bias_rows, save_path)
            print(f"  输出: {save_path}.jpg")

    print("\n绘图完成。")


# ==================== 主流程 ====================
def main() -> None:
    """单文件流水线：先提取偏差场，再绘图并落盘统计量。"""
    print("#" * 70)
    print("# Fig3 单文件流水线：偏差场提取 → 空间分布绘图")
    print("#" * 70)
    extract_bias()
    plot_bias_maps()


if __name__ == "__main__":
    main()
