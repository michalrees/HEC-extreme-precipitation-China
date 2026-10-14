from __future__ import annotations

import os
import json
from pathlib import Path

import matplotlib.pyplot as plt
import cartopy.crs as ccrs
import numpy as np
import pandas as pd
import shapefile
import xarray as xr
from matplotlib.ticker import FuncFormatter
from cartopy.mpl.ticker import LongitudeFormatter, LatitudeFormatter
from scipy.fft import dctn, idctn
from shapely.geometry import Point, shape as shapely_shape
from shapely.ops import polygonize, unary_union
from shapely.prepared import prep

plt.rcParams.update({
    "font.family": "Times New Roman",
    "mathtext.fontset": "stix",
    "font.size": 13,
    "axes.labelsize": 16,
    "axes.titlesize": 17,
    "xtick.labelsize": 16,
    "ytick.labelsize": 16,
})


REPO_ROOT = next(
    p for p in Path(__file__).resolve().parents
    if (p / "src").is_dir() and (p / "Doc").is_dir()
)
DATA_ROOT = REPO_ROOT / "Data"
# 统一使用 pipeline 脚本 6 的规范输出（2021–2050 预估），不读 src/Pic 下的手工拷贝
NC_PATH = REPO_ROOT / "Output" / "EC" / "China" / "HEC_ssp245_PrecipVar_to_R95mm_intensity.nc"
SHP_PATH = DATA_ROOT / "China" / "cnmap.shp"
DATA_DIR = Path(__file__).resolve().parent / "data"
FIG_DIR = Path(__file__).resolve().parent

# ── 常数 ─────────────────────────────────────────────────
DECOMP_LOWER_KM = 200.0      # 断点候选的网格尺度下限，也是第 1 档包含的最短波长阈值
EARTH_RADIUS_KM = 6371.0
BREAKPOINT_THRESHOLD = 1.0   # 斜率二阶差分的峰值阈值
LOG_WAVELENGTH_TOL = 0.4     # 相邻候选断点所需的最小 Δlog₁₀λ

# 七个分区（与图 3 / 图 5 的区域体系一致）
REGIONS = [
    {"key": "NorthChina",   "label": "North China",   "extent": [110, 118, 35, 42]},
    {"key": "Northeast",    "label": "Northeast",     "extent": [118, 135, 38, 54]},
    {"key": "Northwest",    "label": "Northwest",     "extent": [73, 105, 35, 50]},
    {"key": "Southwest",    "label": "Southwest",     "extent": [95, 108, 21, 35]},
    {"key": "EastChina",    "label": "East China",    "extent": [115, 123, 27, 35]},
    {"key": "SouthChina",   "label": "South China",   "extent": [108, 120, 18, 26]},
    {"key": "CentralChina", "label": "Central China", "extent": [108, 115, 26, 34]},
]

# 三个流域（黄河多边形文件名仍为 HuanghaiRiver_polygon.shp，范围为黄河流域）
RIVER_BASINS = [
    ("YellowRiver", DATA_ROOT / "River" / "HuanghaiRiver_polygon.shp"),
    ("PearlRiver", DATA_ROOT / "River" / "PearlRiver_polygon.shp"),
    ("YangtzeRiver", DATA_ROOT / "River" / "YangtzeRiver_polygon.shp"),
]

# 区域显示名（与图 3 / 图 5 一致）
REGION_LABELS = {
    "China": "China", "NorthChina": "North China", "Northeast": "Northeast",
    "Northwest": "Northwest", "Southwest": "Southwest", "EastChina": "East China",
    "SouthChina": "South China", "CentralChina": "Central China",
    "YellowRiver": "Yellow River Basin", "PearlRiver": "Pearl Basin",
    "YangtzeRiver": "Yangtze Basin",
}

BAND_COLORS = ["#4C72B0", "#DD8452", "#55A868"]


GAP_MAP_CBAR = 0.52     # 地图下边缘 → 色带（含地图经度标签与色带标题）
GAP_CBAR_C = 0.10       # 色带刻度标签下边缘 → (c) 面板外的图例上边缘
GAP_C_D = 0.08          # (c) 区域名标签下边缘 → (d) 上框线


# ── 面积加权（cos φ）工具 ─────────────────────────────────
def _lat_weights(lat: np.ndarray) -> np.ndarray:
    """cos φ 面积权重（负值截断为 0）。"""
    return np.clip(np.cos(np.deg2rad(lat)), 0.0, None)


def _wmean(field: np.ndarray, mask: np.ndarray, latw: np.ndarray) -> float:
    """区域平均（cos φ 面积加权，保留符号）。"""
    w = np.broadcast_to(latw[:, None], field.shape)
    m = mask & np.isfinite(field)
    den = float(np.nansum(w[m]))
    return float("nan") if den <= 0 else float(np.nansum(field[m] * w[m]) / den)


def _wmean_abs(field: np.ndarray, mask: np.ndarray, latw: np.ndarray) -> float:
    """区域平均绝对值（cos φ 面积加权）。"""
    w = np.broadcast_to(latw[:, None], field.shape)
    m = mask & np.isfinite(field)
    den = float(np.nansum(w[m]))
    return float("nan") if den <= 0 else float(np.nansum(np.abs(field[m]) * w[m]) / den)


def _wvar(field: np.ndarray, mask: np.ndarray, latw: np.ndarray) -> float:
    """区域方差（cos φ 面积加权，总体方差 ddof=0）。"""
    w = np.broadcast_to(latw[:, None], field.shape)
    m = mask & np.isfinite(field)
    den = float(np.nansum(w[m]))
    if den <= 0:
        return float("nan")
    mu = float(np.nansum(field[m] * w[m]) / den)
    return float(np.nansum((field[m] - mu) ** 2 * w[m]) / den)


# ── DCT / 谱分析 ─────────────────────────────────────────
def _wavelength_map(ny: int, nx: int, lat: np.ndarray, lon: np.ndarray) -> np.ndarray:
    """与 DCT 系数一一对应的 2D 波长场 (ny, nx)。"""
    dlat = float(np.mean(np.abs(np.diff(lat))))
    dlon = float(np.mean(np.abs(np.diff(lon))))
    dy = np.deg2rad(dlat) * EARTH_RADIUS_KM
    dx = np.deg2rad(dlon) * EARTH_RADIUS_KM * float(np.mean(np.cos(np.deg2rad(lat))))
    ly, lx = dy * (ny - 1), dx * (nx - 1)

    ky, kx = np.arange(ny, dtype=float), np.arange(nx, dtype=float)
    wl_y = np.full(ny, np.inf)
    wl_y[1:] = 2.0 * ly / ky[1:]
    wl_x = np.full(nx, np.inf)
    wl_x[1:] = 2.0 * lx / kx[1:]

    inv = np.sqrt((1.0 / wl_y[:, None]) ** 2 + (1.0 / wl_x[None, :]) ** 2)
    wl = np.divide(1.0, inv, out=np.full_like(inv, np.inf), where=inv > 0)
    wl[0, 0] = np.inf
    return wl


def dct_filter_bands(field: np.ndarray, wavelength: np.ndarray,
                     breakpoints: list[float]) -> list[np.ndarray]:
    """DCT → 按断点分段掩膜 → iDCT，返回各尺度段的重构场。

    第 1 档取 `0 < λ ≤ 断点1`（含 200 km 以下的网格尺度分量），中间档取半开区间，
    末档取 `λ ≥ 断点2`（承接零频项，即全国共同的那份调整）。
    """
    coeff = dctn(field, type=2, norm="ortho")
    limits = [0.0] + list(breakpoints) + [np.inf]
    bands = []
    for lo, hi in zip(limits[:-1], limits[1:]):
        if lo == 0.0:
            mask = (wavelength > 0) & (wavelength <= hi)
        elif np.isinf(hi):
            mask = wavelength >= lo
        else:
            mask = (wavelength >= lo) & (wavelength < hi)
        bands.append(idctn(coeff * mask.astype(float), type=2, norm="ortho"))
    return bands


def compute_spectrum(field: np.ndarray, lat: np.ndarray, lon: np.ndarray) -> pd.DataFrame:
    """2D DCT 波长-方差谱（对数分箱内 power 求和，45 箱）。"""
    ny, nx = field.shape
    f = np.nan_to_num(field, nan=0.0, posinf=0.0, neginf=0.0)
    power = np.asarray(dctn(f, type=2, norm="ortho"), dtype=float) ** 2 / (nx * ny)
    wavelength = _wavelength_map(ny, nx, lat, lon)

    wl, pw = wavelength.ravel(), power.ravel()
    ok = np.isfinite(wl) & (wl > 0) & np.isfinite(pw)
    wl, pw = wl[ok], pw[ok]
    if wl.size == 0:
        return pd.DataFrame(columns=["wavelength_km", "variance"])

    bins = np.geomspace(float(np.min(wl)) * 0.9, float(np.max(wl)) * 1.1, 45)
    idx = np.digitize(wl, bins)
    rows = [(float(np.sqrt(bins[i - 1] * bins[i])), float(np.sum(pw[idx == i])))
            for i in range(1, len(bins)) if (idx == i).any()]
    if (idx == len(bins)).any():
        rows.append((float(np.sqrt(bins[-1] * float(np.max(wl)))),
                     float(np.sum(pw[idx == len(bins)]))))
    return pd.DataFrame(rows, columns=["wavelength_km", "variance"])


def sliding_slope(df: pd.DataFrame, window: int = 3) -> pd.DataFrame:
    """log–log 空间滑动窗口局部斜率。"""
    df = df.dropna(subset=["wavelength_km", "variance"])
    df = df[(df["wavelength_km"] > 0) & (df["variance"] > 0)].sort_values("wavelength_km")
    x, y = df["wavelength_km"].values.astype(float), df["variance"].values.astype(float)
    lx, ly_ = np.log(x), np.log(y)
    slopes = np.full(len(x), np.nan)
    half = window // 2
    for i in range(len(x)):
        i0, i1 = max(0, i - half), min(len(x), i + half + 1)
        if i1 - i0 < 2:
            continue
        A = np.column_stack([lx[i0:i1], np.ones(i1 - i0)])
        slopes[i] = np.linalg.lstsq(A, ly_[i0:i1], rcond=None)[0][0]
    out = df.copy()
    out["log_slope"] = slopes
    return out


def detect_breakpoints(slope_df: pd.DataFrame, threshold: float) -> list[tuple[float, float]]:
    """滑动斜率二阶差分的局部峰值（按峰值降序）。"""
    df = slope_df.dropna(subset=["log_slope"]).sort_values("wavelength_km")
    x, s = df["wavelength_km"].values, df["log_slope"].values
    d2 = np.concatenate([np.zeros(1), np.abs(np.diff(s, 2)), np.zeros(1)])
    peaks = [(x[i], d2[i]) for i in range(1, len(d2) - 1)
             if d2[i] > d2[i - 1] and d2[i] >= d2[i + 1] and d2[i] > threshold]
    peaks.sort(key=lambda v: v[1], reverse=True)
    return peaks


def select_breakpoints(peaks: list[tuple[float, float]]) -> tuple[list[float], dict[float, str]]:
    """剔除网格尺度（< DECOMP_LOWER_KM）与聚类冗余（Δlog₁₀λ < LOG_WAVELENGTH_TOL）。"""
    selected: list[float] = []
    rejected: dict[float, str] = {}
    for p, _ in peaks:
        if p < DECOMP_LOWER_KM:
            rejected[p] = "Grid scale (< 200 km)"
            continue
        if all(abs(np.log10(p) - np.log10(s)) >= LOG_WAVELENGTH_TOL for s in selected):
            selected.append(p)
        else:
            rejected[p] = "Clustered (Δlog < 0.4)"
    return sorted(selected), rejected


# ── 掩膜 ─────────────────────────────────────────────────
def make_china_mask(lat: np.ndarray, lon: np.ndarray) -> np.ndarray:
    """cnmap.shp → polygonize → 中国境内格点掩膜。"""
    sf = shapefile.Reader(str(SHP_PATH))
    china = unary_union(list(polygonize(unary_union(
        [shapely_shape(s.__geo_interface__) for s in sf.shapes()])))).buffer(0)
    prepped = prep(china)
    mask = np.zeros((len(lat), len(lon)), dtype=bool)
    for i, lt in enumerate(lat):
        for j, ln in enumerate(lon):
            mask[i, j] = prepped.intersects(Point(float(ln), float(lt)))
    return mask


def region_masks(lat: np.ndarray, lon: np.ndarray,
                 land_mask: np.ndarray) -> dict[str, np.ndarray]:
    """dict[str, 2D bool mask]：全国 + 七个分区。"""
    masks: dict[str, np.ndarray] = {"China": land_mask}
    for reg in REGIONS:
        x0, x1, y0, y1 = reg["extent"]
        m = ((lon[np.newaxis, :] >= x0) & (lon[np.newaxis, :] <= x1)
             & (lat[:, np.newaxis] >= y0) & (lat[:, np.newaxis] <= y1))
        masks[reg["key"]] = m & land_mask
    return masks


def build_river_mask(shp_path: Path, lon_2d: np.ndarray, lat_2d: np.ndarray) -> np.ndarray:
    """流域多边形掩膜（包围盒预筛 + 逐点 contains），与图 3 / 图 5 同一实现。"""
    rsf = shapefile.Reader(str(shp_path))
    merged = unary_union([shapely_shape(s.__geo_interface__) for s in rsf.shapes()])
    minx, miny, maxx, maxy = merged.bounds
    mask = np.zeros(lon_2d.shape, dtype=bool)
    ii, jj = np.where((lon_2d >= minx) & (lon_2d <= maxx)
                      & (lat_2d >= miny) & (lat_2d <= maxy))
    for i, j in zip(ii, jj):
        mask[i, j] = merged.contains(Point(lon_2d[i, j], lat_2d[i, j]))
    return mask


# ── 绘图 ─────────────────────────────────────────────────
def _plot_spectrum(ax, spectrum: pd.DataFrame, selected_bps: list[float]) -> None:
    """(a) 波长-方差谱 + 特征尺度断点竖线。"""
    ax.plot(spectrum["wavelength_km"], spectrum["variance"], color="#1f77b4", lw=2)
    ax.set_xscale("log")
    ax.set_yscale("log")
    ax.set_xticks([200, 500, 1000, 2000, 5000, 10000, 20000])
    ax.get_xaxis().set_major_formatter(FuncFormatter(lambda v, _: f"{v:.0f}"))


    ax.set_yticks([1e-6, 1e-4, 1e-2, 1e0])
    ax.set_ylabel("Variance", fontsize=16)
    ax.set_xlabel("Wavelength (km)", fontsize=16)
    ax.set_title("Wavelength-variance spectrum", fontsize=18, fontweight="normal")
    ax.grid(True, which="both", ls="--", alpha=0.3)
    ax.tick_params(labelsize=16)

    for bp in selected_bps:                       # 只标注保留的两个特征尺度
        ax.axvline(bp, color="gray", ls="-", lw=1.5, alpha=0.9)
        ax.text(bp * 1.03, 0.76, f"{bp:.0f} km", transform=ax.get_xaxis_transform(),
                rotation=90, va="top", ha="left", color="gray", fontsize=13)


def _plot_band_maps(axes, lon, lat, bands, band_labels, land_mask, cn_geoms, extent):
    """(b) 三个尺度分量的带通重构场，共用对称发散色标；返回 (mesh, 色标刻度)。"""
    finite = np.concatenate([np.abs(np.where(land_mask, b, np.nan)).ravel() for b in bands])
    finite = finite[np.isfinite(finite)]
    vmax = float(np.ceil(np.percentile(finite, 99) * 10) / 10) if finite.size else 1.0
    step = 2.0 if vmax >= 4 else (1.0 if vmax >= 2 else 0.5)
    cb_ticks = np.arange(-int(np.floor(vmax / step)) * step,
                         int(np.floor(vmax / step)) * step + step / 2, step)

    mesh = None


    for j, (ax, fld, lbl) in enumerate(zip(axes, bands, band_labels)):
        z = np.ma.masked_where(~land_mask, fld)
        mesh = ax.pcolormesh(lon, lat, z, cmap="RdBu_r", vmin=-vmax, vmax=vmax,
                             shading="auto", rasterized=True, transform=ccrs.PlateCarree())
        ax.set_extent(extent, crs=ccrs.PlateCarree())
        ax.add_geometries(cn_geoms, crs=ccrs.PlateCarree(), facecolor="none",
                          edgecolor="#888888", linewidth=0.5)
        # 网格线只画不标（draw_labels=False）：默认刻度太密（80/90/110/130°E），
        # 在 1.5 in 宽的框里标注会换行并互相挤压；改为自己指定 20° 间隔的刻度、
        # 且只标左下两侧（与期刊地图惯例一致）。
        gl = ax.gridlines(draw_labels=False, linewidth=0.3, alpha=0.4, linestyle="--")
        xt = list(range(80, int(np.ceil(extent[1] / 10.0)) * 10, 20))
        yt = list(range(10, int(np.ceil(extent[3] / 10.0)) * 10, 20))
        ax.set_xticks(xt, crs=ccrs.PlateCarree())
        ax.set_yticks(yt, crs=ccrs.PlateCarree())
        ax.xaxis.set_major_formatter(LongitudeFormatter(number_format=".0f",
                                                        degree_symbol="°",
                                                        cardinal_labels={"east": "E"}))
        ax.yaxis.set_major_formatter(LatitudeFormatter(number_format=".0f",
                                                       degree_symbol="°",
                                                       cardinal_labels={"north": "N"}))
        ax.tick_params(axis="both", labelsize=9, length=2, pad=1.2)
        ax.set_title(lbl, fontsize=15)
    print(f"  (b) 色标范围 ±{vmax:.1f}，刻度 {np.round(cb_ticks, 2).tolist()}")
    return mesh, cb_ticks


def _plot_sign_split(ax, df: pd.DataFrame, band_labels: list[str]) -> None:
    """(d) 各区域各尺度分量的正值部分与负值部分（mm/day，cos φ 面积加权，分组柱）。

    每个区域 6 根柱：三个尺度分量各一对（正值部分向上、负值部分向下，负值柱同色斜线填充），
    故任一尺度任一符号的贡献可直接读柱高；同一尺度两根柱的代数和即该尺度在该区域的净调整量，
    全部六根之和等于该区域的平均调整量（与 (c) 的三档之和一致）。
    配色与 (c) 相同，便于两面板对照。
    """
    names = df["region"].values
    n_band = len(band_labels)
    x = np.arange(len(df))
    group_w = 0.82
    bar_w = group_w / (2 * n_band)

    pos = np.column_stack([df[f"pos_s{i+1}"].values.astype(float) for i in range(n_band)])
    neg = np.column_stack([df[f"neg_s{i+1}"].values.astype(float) for i in range(n_band)])

    vmax = float(np.nanmax(np.abs(np.concatenate([pos, neg]))))
    span = 2 * vmax
    for i in range(n_band):
        off = (i - (n_band - 1) / 2) * 2 * bar_w
        for vals, sign in ((pos[:, i], +1), (neg[:, i], -1)):
            ax.bar(x + off + sign * bar_w / 2, vals, bar_w * 0.92,
                   color=BAND_COLORS[i],
                   alpha=1.0 if sign > 0 else 0.55,
                   hatch="" if sign > 0 else "///",
                   edgecolor="white" if sign > 0 else BAND_COLORS[i],
                   linewidth=0.4 if sign > 0 else 0.5)

    ax.axhline(0, color="k", lw=0.8)
    ax.set_xticks(x)
    ax.set_xticklabels([REGION_LABELS.get(n_, n_) for n_ in names], rotation=30, ha="right")
    # (d) 面板高度仅约 0.7 in，长轴标题会越过面板上下端并与 (c) 的轴标题叠压，
    # 故只用单位作为轴标题；正的“正值部分/负值部分”含义由图注说明。
    ax.set_ylabel("Positive /\nnegative part", fontsize=12)
    ax.set_ylim(-0.62 * span, 0.62 * span)
    ax.grid(axis="y", ls="--", alpha=0.3)
    # 不设图例：配色与 (c) 完全一致（实色=正值部分、斜线=负值部分），由图注说明；
    # (d) 面板高度有限，图例也会与 (c) 的刻度标签叠压。
    print(f"  (d) 分组柱：正/负部分绝对值上限 {vmax:.3f} mm/day，"
          f"每区域 {2 * n_band} 根（实色=正、斜线=负）")


def _plot_band_means(ax, df: pd.DataFrame, band_labels: list[str]) -> None:
    """(c) 各区域三档净调整量（带通重构场的区域平均，mm/day）分组柱状图。

    每个区域 3 根柱（小、中、大尺度，配色与 (d)(e) 一致），柱高取自 mean_s1..3（保留正负号）；
    每组柱上方标注该区域三档之和，即该区域的平均调整量（与 (d) 中该区域六根柱的代数和相等）。
    图例置于坐标区外（面板上方横排三列），沿用旧版净调整量面板的版式。
    """
    names = df["region"].values
    v = np.column_stack([df[f"mean_s{i}"].values.astype(float) for i in (1, 2, 3)])
    n = v.shape[1]
    bar_w = 0.6 / n
    x = np.arange(len(df))
    for i in range(n):
        offset = (i - (n - 1) / 2) * bar_w
        ax.bar(x + offset, v[:, i], bar_w * 0.9, label=band_labels[i], color=BAND_COLORS[i])
    span = float(np.nanmax(v)) - float(np.nanmin(v))
    for j in range(len(df)):
        ax.text(j, float(np.nanmax(v[j])) + 0.05 * span, f"{np.nansum(v[j]):.2f}",
                ha="center", va="bottom", fontsize=10, fontweight="bold", color="0.25")
    ax.axhline(0, color="k", lw=0.8)
    ax.set_xticks(x)
    ax.set_xticklabels([REGION_LABELS.get(n_, n_) for n_ in names], rotation=30, ha="right")
    ax.set_ylabel("Mean adjustment", fontsize=15)   # 单位由图注承担（作者要求）
    ax.set_ylim(float(np.nanmin(v)) - 0.20 * span, float(np.nanmax(v)) + 0.30 * span)
    ax.grid(axis="y", ls="--", alpha=0.3)
    # 图例移到坐标区之外（面板上方、横排三列）：三档配色在此首次出现，(d)(e) 沿用
    ax.legend(loc="lower center", bbox_to_anchor=(0.5, 1.005), ncol=3,
              frameon=False, fontsize=11, handlelength=1.3, columnspacing=1.2)
    print(f"  (c) 净调整量分组柱：{len(df)} 个区域 × {n} 档，"
          f"柱高范围 {np.nanmin(v):+.3f} ~ {np.nanmax(v):+.3f} mm/day，"
          f"区域合计最大 {np.nanmax(v.sum(axis=1)):.2f} mm/day")


def _plot_shares(ax, df: pd.DataFrame, band_labels: list[str]) -> None:
    """(e) 各区域三档方差份额分组柱状图（每区域合计 100%）。

    三档配色由图 (c) 的图例给出，本面板不再重复画图例（与 (d) 同处理）。
    """
    names = df["region"].values
    v = np.column_stack([df[f"var_s{i}"].values.astype(float) for i in (1, 2, 3)])
    share = v / v.sum(axis=1, keepdims=True) * 100.0
    n = share.shape[1]
    bar_w = 0.6 / n
    x = np.arange(len(df))
    for i in range(n):
        offset = (i - (n - 1) / 2) * bar_w
        ax.bar(x + offset, share[:, i], bar_w * 0.9, label=band_labels[i], color=BAND_COLORS[i])
        for j, val in enumerate(share[:, i]):
            ax.text(j + offset, val + 1.5, f"{val:.1f}", ha="center", va="bottom",
                    fontsize=10, fontweight="bold", color=BAND_COLORS[i], rotation=90)

    ax.set_xticks(x)
    ax.set_xticklabels([REGION_LABELS.get(n_, n_) for n_ in names], rotation=30, ha="right")
    ax.set_ylabel("Variance share (%)", fontsize=17)
    ax.set_ylim(0, 135)   # 抬高上限，避免竖排数值顶出坐标区
    ax.set_yticks([0, 25, 50, 75, 100])
    ax.grid(axis="y", ls="--", alpha=0.3)


def _finalize_layout(fig, ax_top, axes_maps, stack, cax, cb, map_extent) -> None:
    """布局收尾（2026-10-11 由 4 面板扩展为 5 面板后重排）：

    ① cartopy 的 GeoAxes 纵横比固定，会被 tight_layout 反复收缩（实测仅 1.14 in 宽，
       而网格单元 1.83 in），多余空白全落到色带一侧 —— 按网格单元宽度把三张地图放大；
    ② 色带上移到地图正下方，其标题放在色带上方，避免与 (c) 的内容叠压；
    ③ 色带以下的三个面板（stack = [(c) 净调整量、(d) 正负部分、(e) 方差份额]）自上而下
       依次定位：第一个让开色带刻度标签并为面板外图例留高，其后每个让开上一个面板的区域名
       标签（30° 旋转，实测外框下探约 0.89 in）；
    ④ 五个面板字母用图幅坐标绘制，横坐标统一取 (a) 的左外侧
       （(b) 的地图宽度与 (a)(c) 不同，轴内比例无法对齐）。
    """
    height, width = fig.get_figheight(), fig.get_figwidth()
    aspect = (map_extent[1] - map_extent[0]) / (map_extent[3] - map_extent[2])   # 地图宽/高

    top = ax_top.get_position().y0 - 0.118          # 让出 (a) 的 x 轴标题与地图标题
    map_bottom = None
    for ax in axes_maps:
        cell = ax.get_subplotspec().get_position(fig)
        w = cell.width
        h = (w * width) / aspect / height           # 英寸 → 图幅比例
        y0 = top - h                                # 顶部对齐
        ax.set_position([cell.x0, y0, w, h])
        map_bottom = y0 if map_bottom is None else min(map_bottom, y0)
    print(f"  (b) 地图尺寸 {w * width:.2f} × {h * height:.2f} in")

    cb_box = cax.get_position()
    cb_top = map_bottom - GAP_MAP_CBAR / height     # 含地图经纬度标签 + 色带标题占位
    cax.set_position([cb_box.x0, cb_top - cb_box.height, cb_box.width, cb_box.height])
    cb.set_label("Reconstructed adjustment component (mm/day)", fontsize=12)
    cb.ax.xaxis.set_label_position("top")
    print(f"  (b) 色带—地图间距 {(map_bottom - cb_top) * height:.2f} in")

    # ── 按实测文字外框定位 (c) 与 (d)：先画一次，拿到刻度标签/图例的真实高度 ──
    fig.canvas.draw()
    rend = fig.canvas.get_renderer()
    inv = fig.dpi_scale_trans.inverted()

    def _y0y1(artist):
        bb = artist.get_window_extent(rend).transformed(inv)
        return bb.y0, bb.y1

    cb_tick_bottom = min(_y0y1(t)[0] for t in cb.ax.get_xticklabels() if t.get_text())
    first = stack[0]
    legend = first.get_legend()
    legend_over = _y0y1(legend)[1] - first.get_position().y1 * height if legend is not None else 0.0
    prev_bottom = cb_tick_bottom - GAP_CBAR_C - legend_over
    letters = [("(a)", ax_top.get_position().y1 + 0.006),
               ("(b)", max(ax.get_position().y1 for ax in axes_maps) + 0.028)]
    heights_txt = []
    for k, ax in enumerate(stack):
        box = ax.get_position()
        ax.set_position([box.x0, prev_bottom / height - box.height, box.width, box.height])
        tag = f"({chr(ord('c') + k)})"
        letters.append((tag, ax.get_position().y1 + 0.006))
        heights_txt.append(f"{tag} {ax.get_position().height * height:.2f} in")
        fig.canvas.draw()
        xlab_bottom = min(_y0y1(t)[0] for t in ax.get_xticklabels() if t.get_text())
        prev_bottom = xlab_bottom - GAP_C_D
    print(f"  (c) 顶部让开色带刻度标签 {GAP_CBAR_C:.2f} in、图例高 {legend_over:.2f} in；"
          f"相邻堆叠面板间距 {GAP_C_D:.2f} in")

    lx = ax_top.get_position().x0 - 0.17 * ax_top.get_position().width
    for label, y in letters:
        fig.text(lx, y, label, fontsize=19, ha="left", va="bottom")
    print(f"  面板字母横坐标统一为图幅 x={lx:.3f}")
    print(f"  面板高度 (a) {ax_top.get_position().height * height:.2f} in、"
          + "、".join(heights_txt))


SIGN_BAND_LABELS = ["≤1409 km", "1409–4898 km", "≥4898 km"]


def sign_stats(field: np.ndarray, mask: np.ndarray, latw: np.ndarray) -> dict:
    """单个（场，区域）的正/负贡献统计，面积加权。"""
    mm = mask & np.isfinite(field)
    w = np.broadcast_to(latw[:, None], field.shape)[mm]
    v = field[mm]
    wsum = float(np.sum(w))
    pos, neg = v > 0, v < 0
    mu = float(np.sum(v * w) / wsum)
    return {
        "n_grid": int(mm.sum()),
        "mean": mu,
        "pos_part": float(np.sum(np.where(pos, v, 0.0) * w) / wsum),
        "neg_part": float(np.sum(np.where(neg, v, 0.0) * w) / wsum),
        "abs_mean": float(np.sum(np.abs(v) * w) / wsum),
        "pos_frac_pct": float(np.sum(w[pos]) / wsum * 100.0),
        "pos_amp": float(np.sum(v[pos] * w[pos]) / np.sum(w[pos])) if pos.any() else 0.0,
        "neg_amp": float(np.sum(v[neg] * w[neg]) / np.sum(w[neg])) if neg.any() else 0.0,
        "var": float(np.sum((v - mu) ** 2 * w) / wsum),
    }


def region_sign_stats(lat: np.ndarray, lon: np.ndarray, bands: list[np.ndarray],
                      land_mask: np.ndarray, latw: np.ndarray) -> pd.DataFrame:
    """区域 × 三档的格点正/负号长表 → data/region_band_sign_stats.csv（11 区域 × 4 行）。

    口径与依赖（全部沿用本文件上文的实现，不再跨脚本 import）：
        · 分解对象 Bias = Posterior − Prior（SSP2-4.5，2021–2050 vs 1981–2010）；
        · 三档重构场即 `bands`——本流程刚写入 data/band_{1,2,3}_*.npy 的那三份数组，三档严格可加；
        · 区域掩膜（region_masks）与 cos φ 面积加权（_lat_weights）直接复用；
        · 有效格点判据为有限值 ∧ 中国陆地（land_mask）；
        · 流域掩膜在此额外与陆地掩膜取交（沿原 region_stats.py 的口径，与上文 scale_variance
          统计所用的 rmasks 不同，故本函数自行构建掩膜而不复用 rmasks）；
        · 方差份额 share_pct 的分母为**三档带通场方差之和**（与图 9c 一致），不是调整场总方差。
    """
    field_sum = bands[0] + bands[1] + bands[2]

    masks = region_masks(lat, lon, land_mask)
    lon_2d, lat_2d = np.meshgrid(lon, lat)
    for name, shp in RIVER_BASINS:
        if shp.exists():
            masks[name] = build_river_mask(shp, lon_2d, lat_2d) & land_mask

    rows = []
    for region, m in masks.items():
        if m.sum() == 0:
            continue
        stats = [sign_stats(b, m, latw) for b in bands]
        vsum = sum(s["var"] for s in stats)
        for label, s in zip(SIGN_BAND_LABELS, stats):
            rows.append({
                "region": region, "band": label, **{k: round(v, 6) for k, v in s.items()},
                "share_pct": round(s["var"] / vsum * 100.0, 4),
                "residue_pct": round(abs(s["mean"]) / s["abs_mean"] * 100.0, 4),
            })
        # 全场行（band=total，仅 mean/pos/neg/abs 有意义）
        st = sign_stats(field_sum, m, latw)
        rows.append({
            "region": region, "band": "total", **{k: round(v, 6) for k, v in st.items()},
            "share_pct": 100.0,
            "residue_pct": round(abs(st["mean"]) / st["abs_mean"] * 100.0, 4),
        })

    df = pd.DataFrame(rows)
    out = DATA_DIR / "region_band_sign_stats.csv"
    df.to_csv(out, index=False)
    print(f"Saved: {out}  ({len(df)} 行)")

    nc_row = df[(df.region == "NorthChina") & (df.band != "total")]
    pd.set_option("display.width", 220)
    print("\n华北（NorthChina）三档：")
    print(nc_row[["band", "n_grid", "mean", "pos_part", "neg_part", "abs_mean",
                  "pos_frac_pct", "pos_amp", "neg_amp", "var", "share_pct",
                  "residue_pct"]].to_string(index=False))
    print("\n各区域小尺度档残留比（|净值|/平均绝对幅值，%，越小越相消）：")
    s1 = df[df.band == SIGN_BAND_LABELS[0]][["region", "mean", "abs_mean", "residue_pct"]]
    print(s1.sort_values("residue_pct").to_string(index=False))
    return df


# ── 主流程 ───────────────────────────────────────────────
def _json_safe(obj):
    """把 NaN 递归替换成 None，便于写入 JSON。"""
    if isinstance(obj, dict):
        return {k: _json_safe(v) for k, v in obj.items()}
    if isinstance(obj, list):
        return [_json_safe(v) for v in obj]
    if isinstance(obj, float) and np.isnan(obj):
        return None
    return obj


def main() -> None:
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    FIG_DIR.mkdir(parents=True, exist_ok=True)

    # 1. 读入 Bias = Posterior − Prior
    with xr.open_dataset(NC_PATH) as ds:
        ds = ds.load()
    lat = np.asarray(ds.lat.values, dtype=float)
    lon = np.asarray(ds.lon.values, dtype=float)
    delta = np.asarray(ds["posterior_mean"].values, dtype=float) \
        - np.asarray(ds["prior_mean"].values, dtype=float)
    print(f"Bias field: {delta.shape}")

    # 2. 谱分析 + 断点检测
    spectrum = compute_spectrum(delta, lat, lon)
    spectrum.to_csv(DATA_DIR / "bias_spectrum.csv", index=False)
    slope_df = sliding_slope(spectrum, window=5)
    slope_df.to_csv(DATA_DIR / "bias_slope.csv", index=False)
    print(f"Spectrum: {len(spectrum)} bins")

    peaks = detect_breakpoints(slope_df, threshold=BREAKPOINT_THRESHOLD)
    selected_wls, rejected_wls = select_breakpoints(peaks)
    for p, r in peaks:
        note = f"  ── rejected: {rejected_wls[p]}" if p in rejected_wls else (
            "  ← selected" if p in selected_wls else "")
        print(f"  {p:.0f} km  (change_rate = {r:.4f}){note}")

    with open(DATA_DIR / "breakpoint.json", "w") as f:
        json.dump(_json_safe({
            "breakpoint_km": selected_wls[0] if selected_wls else np.nan,
            "r2": np.nan, "slope_before": np.nan, "slope_after": np.nan,
            "n_bins": len(spectrum), "scenario": "ssp245",
            "selected_breakpoints": selected_wls,
            "multi_breakpoints": [
                {"breakpoint_km": p, "change_rate": r, "r2": np.nan,
                 "slope_left": np.nan, "slope_right": np.nan}
                for p, r in sorted(peaks)
            ],
        }), f, indent=2)

    # 3. 尺度分解（不扣除全域均值；三档之和 = 区域平均调整量）
    bps = selected_wls[:2]
    limits = [0.0] + bps + [np.inf]
    band_labels = []
    for lo, hi in zip(limits[:-1], limits[1:]):
        if np.isinf(hi):
            band_labels.append(f"\u2265 {lo:.0f} km")
        elif lo == 0.0:
            band_labels.append(f"\u2264{hi:.0f} km")
        else:
            band_labels.append(f"{lo:.0f}\u2013{hi:.0f} km")
    print(f"Bands: {band_labels}")

    latw = _lat_weights(lat)
    china_mask = make_china_mask(lat, lon)
    land_mask = china_mask & np.isfinite(delta)
    print(f"China mask: {china_mask.sum()} → valid: {land_mask.sum()} grid points")
    domain_mean = _wmean(delta, land_mask, latw)
    print(f"Domain mean (area-weighted, land): {domain_mean:.4f} mm/day （诊断量，未扣除）")

    field = np.nan_to_num(delta, nan=0.0, posinf=0.0, neginf=0.0)
    wl = _wavelength_map(*delta.shape, lat, lon)
    bands = dct_filter_bands(field, wl, bps)
    for i, (fld, lbl) in enumerate(zip(bands, band_labels)):
        safe = (lbl.replace("\u2264", "le").replace("\u2265", "ge")
                   .replace(" ", "_").replace("\u2013", "-"))
        np.save(DATA_DIR / f"band_{i+1}_{safe}.npy", fld)

    # 4. 区域掩膜（全国 + 七分区 + 三流域，后者仅入 CSV）
    rmasks = region_masks(lat, lon, land_mask)
    lon_2d, lat_2d = np.meshgrid(lon, lat)
    for name, shp in RIVER_BASINS:
        if shp.exists():
            rmasks[name] = build_river_mask(shp, lon_2d, lat_2d)
            print(f"  basin {name}: {int(rmasks[name].sum())} grid points")

    # 5. 逐区域统计（面积加权为主口径，未加权以 unw_ 前缀留档）
    rows = []
    for rkey, rm in rmasks.items():
        if rm.sum() == 0:
            continue
        row: dict = {"region": rkey, "n_grid": int(rm.sum()), "domain_mean": domain_mean}

        # 三套口径（列顺序与历史版本一致，便于与旧 CSV 直接对照）
        row["total_var"] = _wvar(delta, rm, latw)
        row["unw_total_var"] = float(np.nanvar(delta[rm], ddof=0))
        for i, fld in enumerate(bands):
            row[f"var_s{i+1}"] = _wvar(fld, rm, latw)
            row[f"unw_var_s{i+1}"] = float(np.nanvar(fld[rm], ddof=0))

        # 三档方差份额（图 9c 柱高，%，三档合计 100）：直接由上面三列的各尺度方差归一化，
        # 使正文与摘要引用的份额（如全国 72.1%/22.1%/5.8%）在 data/ 内可直接查到、无需再手算。
        _vsum = sum(row[f"var_s{i+1}"] for i in range(len(bands)))
        for i in range(len(bands)):
            row[f"share_s{i+1}"] = row[f"var_s{i+1}"] / _vsum * 100.0

        row["total_mean"] = _wmean(delta, rm, latw)
        row["unw_total_mean"] = float(np.nanmean(delta[rm]))
        for i, fld in enumerate(bands):
            row[f"mean_s{i+1}"] = _wmean(fld, rm, latw)
            row[f"unw_mean_s{i+1}"] = float(np.nanmean(fld[rm]))

        row["total_abs"] = _wmean_abs(delta, rm, latw)
        row["unw_total_abs"] = float(np.nanmean(np.abs(delta[rm])))
        for i, fld in enumerate(bands):
            row[f"abs_s{i+1}"] = _wmean_abs(fld, rm, latw)
            row[f"unw_abs_s{i+1}"] = float(np.nanmean(np.abs(fld[rm])))

        # 正/负部分（图 9d）：max(Bias_b,0) 与 min(Bias_b,0) 的 cos φ 面积加权平均，
        # 两者之和恰等于该尺度分量的区域平均（即 (c) 的柱高）；原始格点求和以 *_raw_s* 留档。
        row["pos_total"] = _wmean(np.where(delta > 0, delta, 0.0), rm, latw)
        row["neg_total"] = _wmean(np.where(delta < 0, delta, 0.0), rm, latw)
        for i, fld in enumerate(bands):
            row[f"pos_s{i+1}"] = _wmean(np.where(fld > 0, fld, 0.0), rm, latw)
            row[f"neg_s{i+1}"] = _wmean(np.where(fld < 0, fld, 0.0), rm, latw)
            row[f"pos_raw_s{i+1}"] = float(np.nansum(np.where(fld[rm] > 0, fld[rm], 0.0)))
            row[f"neg_raw_s{i+1}"] = float(np.nansum(np.where(fld[rm] < 0, fld[rm], 0.0)))
        rows.append(row)

    df = pd.DataFrame(rows)
    csv_path = DATA_DIR / "scale_variance.csv"
    df.to_csv(csv_path, index=False)
    print(f"\nSaved: {csv_path}")
    print(df.to_string())

    # 6. 出图：(a) 谱 → (b) 三档重构场 + 色带 → (c) 方差份额
    sf = shapefile.Reader(str(SHP_PATH))
    cn_geoms = [shapely_shape(s.__geo_interface__) for s in sf.shapes()]
    bb = sf.bbox
    map_extent = [float(bb[0]) - 1, float(bb[2]) + 1, float(bb[1]) - 1, float(bb[3]) + 1]
    print(f"  (b) 地图范围（shapefile 外扩 1°）: {map_extent[0]:.1f}–{map_extent[1]:.1f}°E, "
          f"{map_extent[2]:.1f}–{map_extent[3]:.1f}°N；矢量要素 {len(cn_geoms)} 个")

    basins = ("YellowRiver", "PearlRiver", "YangtzeRiver")
    df_plot = df[~df["region"].isin(basins)].reset_index(drop=True)
    print(f"  (c) 统计区域数 {len(df_plot)}（不含三个流域；CSV 保留全部 {len(df)} 行）")


    fig = plt.figure(figsize=(7.874, 11.6))
    gs = fig.add_gridspec(6, 1, height_ratios=[5.4, 2.3, 0.16, 3.9, 4.6, 4.4])
    ax1 = fig.add_subplot(gs[0])
    gs_maps = gs[1].subgridspec(1, 3, wspace=0.26)


    axes_maps = [fig.add_subplot(gs_maps[0, j], projection=ccrs.PlateCarree()) for j in range(3)]
    cax = fig.add_subplot(gs[2])
    ax_net = fig.add_subplot(gs[3])       # (c) 净调整量
    ax_sign = fig.add_subplot(gs[4])      # (d) 正负部分
    ax_shares = fig.add_subplot(gs[5])    # (e) 方差份额

    _plot_spectrum(ax1, spectrum, selected_bps=selected_wls)
    mesh, cb_ticks = _plot_band_maps(axes_maps, lon, lat, bands, band_labels, land_mask,
                                     cn_geoms, map_extent)
    _plot_band_means(ax_net, df_plot, band_labels)
    _plot_sign_split(ax_sign, df_plot, band_labels)
    _plot_shares(ax_shares, df_plot, band_labels)

    cb = fig.colorbar(mesh, cax=cax, orientation="horizontal")
    cb.set_ticks(cb_ticks)
    cb.ax.tick_params(labelsize=12)
    fig.tight_layout(h_pad=0.5)
    _finalize_layout(fig, ax1, axes_maps, [ax_net, ax_sign, ax_shares], cax, cb, map_extent)


    jpg_path = FIG_DIR / "Fig9.jpg"
    fig.savefig(jpg_path, bbox_inches="tight", dpi=400)
    plt.close(fig)
    print(f"Saved: {jpg_path}")

    # 7. 区域级正/负贡献补充统计（原 region_stats.py，现与本流程同一命名空间）：
    #    复用上面已建好的 lat/lon、三档 band 数组、land_mask 与 cos φ 权重，故无需
    #    重新读 NC、重新建全国掩膜，也不再需要 sys.path + import Fig9 的脚手架。
    print("\n区域正/负贡献统计：")
    region_sign_stats(lat, lon, bands, land_mask, latw)


if __name__ == "__main__":
    main()