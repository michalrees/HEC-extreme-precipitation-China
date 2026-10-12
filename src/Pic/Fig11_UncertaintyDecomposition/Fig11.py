"""Fig.11 单文件流水线：先验 → 后验不确定性缩减率的尺度分解（单面板）+ 尺度谱对照。

本文件由原 `Fig11.py` / `尺度谱.py` / `_calc_cancellation.py` / `_calc_cross_check.py` /
`_trace_13_38_49.py` 五个脚本合并而成：全模块只有一个命名空间，不再有跨脚本 import
（原两个核算脚本的 `from Fig11 import compute_wavelength_map, dct_filter_bands` 已消失，
相关函数在本文件上方定义、供诊断函数直接调用）。

默认运行（一条命令复现全部产物）：
    python Fig11.py
流水线顺序（与原两脚本的先后一致）：
    ① run_fig11()     读 nc 的 σ 场 → 断点 → 全国一次 2D DCT 三档分解 → 掩膜 → 逐区域统计
                      → data/uncertainty_reduction.csv + Fig11.jpg
    ② run_spectrum()  同一条 nc 的三个场（先验 σ、后验 σ、方差缩减量）各算一条 2D DCT
                      波长-方差谱，并标注断点 → data/uncertainty_spectrum.csv；备用谱图
                      fig11a.jpg 只写到**模块之外**的运行期临时目录（见 `_spectrum_scratch()`，
                      退出 with 块即整目录删除），模块根因此恒为
                      Fig11.py / Fig11.jpg / data/ / README.md 四项

诊断开关（**默认一律不跑**；给出任一开关时只跑诊断、不重跑流水线）：
    python Fig11.py --cancellation   # 有符号区域平均 vs 区域平均绝对值（相消率），只打印，无产物
    python Fig11.py --cross-check    # 三种总缩减率口径交叉校验（20.7% / 20.6% / 19.2%），只打印
    python Fig11.py --trace          # 从 git HEAD 旧产物溯源已废弃的 13/38/49
                                     # 依赖 `git show HEAD:src/Pic/.../uncertainty_decomposition.csv`，
                                     # 该路径在当前 git HEAD 中已不存在，故此开关预期会失败并给出提示

口径（2026-10-12 定稿，作者指示只保留"三档缩减率"）：
    · 分解对象是**不确定性幅值场 σ 本身**（prior_std / posterior_std，nc 中即模式间标准差 σ），
      不是调整场；与 3.2 节（图 10，分解 Bias 场）互补。
    · 断点沿用图 10 由 Bias 谱检出的 1409 / 4898 km；三档 = 小（≤1409）、中（1409–4898）、
      大（≥4898，承接零频项）。全国只做一次 2D DCT，子区域自其带通结果按掩膜裁剪统计。
    · 统计量取**带通重构分量的区域平均绝对值** ⟨|σ_b|⟩（cos φ 面积加权）：恒为非负、三档之和
      与该区域全场平均 σ 严格一致（重建误差 ~1e-14），故不存在"有符号区域平均为负"的解释困难。
    · 不再输出各尺度对总缩减量的贡献份额——份额差异只是各档先验量级不同所致，
      "贡献大"不等于"压缩得多"，单列易被误读（见本目录 README.md「方法说明」第五节）。
    · 全国行用 cnmap 陆地掩膜；七个分区 = 经纬框 ∩ 陆地掩膜。三流域仅入 CSV、不出图。

输出：data/uncertainty_reduction.csv（全国 + 七分区 + 三流域：各档先验/后验幅值、缩减量、缩减率、总缩减率）
      Fig11.jpg
      data/uncertainty_spectrum.csv（谱对照步骤；其备用谱图 fig11a.jpg 只写模块外的运行期临时目录、不落盘）
运行：python Fig11.py（路径由 `Path(__file__).resolve()` 自下向上定位，无需修改）
"""
from __future__ import annotations

import argparse
import contextlib
import io
import json
import os
import shutil
import subprocess
import uuid
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import shapefile
import xarray as xr
from matplotlib.ticker import FuncFormatter
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

# ── 路径（原 Fig11.py 与 尺度谱.py 的定义逐字相同，此处统一一份） ──
REPO_ROOT = next(p for p in Path(__file__).resolve().parents
                 if (p / "src").is_dir() and (p / "Doc").is_dir())
DATA_ROOT = REPO_ROOT / "Data"
NC_PATH = REPO_ROOT / "Output" / "EC" / "China" / "HEC_ssp245_PrecipVar_to_R95mm_intensity.nc"
SHP_PATH = DATA_ROOT / "China" / "cnmap.shp"
BP_PATH = (Path(__file__).resolve().parent.parent
           / "Fig10_BiasScaleDecomposition" / "data" / "breakpoint.json")
DATA_DIR = Path(__file__).resolve().parent / "data"
FIG_DIR = Path(__file__).resolve().parent
# 原 尺度谱.py 的 OUT_DIR（= FIG_DIR）已取消：备用谱图 fig11a.jpg 改为写运行期临时目录，
# 不再落到模块根，见 run_spectrum() / main()。

EARTH_RADIUS_KM = 6371.0
BAND_COLORS = ["#4C72B0", "#DD8452", "#55A868"]  # 小/中/大三档（图 11 柱色）
CANCEL_BREAKPOINTS = [1408.97, 4897.51]  # 原 _calc_cancellation.py 内硬编码的断点

REGIONS = [
    {"key": "NorthChina",   "extent": [110, 118, 35, 42]},
    {"key": "Northeast",    "extent": [118, 135, 38, 54]},
    {"key": "Northwest",    "extent": [73, 105, 35, 50]},
    {"key": "Southwest",    "extent": [95, 108, 21, 35]},
    {"key": "EastChina",    "extent": [115, 123, 27, 35]},
    {"key": "SouthChina",   "extent": [108, 120, 18, 26]},
    {"key": "CentralChina", "extent": [108, 115, 26, 34]},
]
REGION_LABELS = {
    "China": "China", "NorthChina": "North China", "Northeast": "Northeast",
    "Northwest": "Northwest", "Southwest": "Southwest", "EastChina": "East China",
    "SouthChina": "South China", "CentralChina": "Central China",
    "YellowRiver": "Yellow River Basin", "PearlRiver": "Pearl Basin",
    "YangtzeRiver": "Yangtze Basin",
}
RIVER_BASINS = [
    ("YellowRiver", DATA_ROOT / "River" / "HuanghaiRiver_polygon.shp"),
    ("PearlRiver", DATA_ROOT / "River" / "PearlRiver_polygon.shp"),
    ("YangtzeRiver", DATA_ROOT / "River" / "YangtzeRiver_polygon.shp"),
]


# ── 面积加权（cos φ）工具 ─────────────────────────────────
def _lat_weights(lat: np.ndarray) -> np.ndarray:
    return np.clip(np.cos(np.deg2rad(lat)), 0.0, None)


def _wmean_abs(field: np.ndarray, mask: np.ndarray, latw: np.ndarray) -> float:
    """区域平均绝对值（cos φ 面积加权）。"""
    w = np.broadcast_to(latw[:, None], field.shape)
    m = mask & np.isfinite(field)
    den = float(np.nansum(w[m]))
    return float("nan") if den <= 0 else float(np.nansum(np.abs(field[m]) * w[m]) / den)


def _wmean_signed(field: np.ndarray, mask: np.ndarray, latw: np.ndarray) -> float:
    """有符号区域平均（cos φ 面积加权）；仅诊断脚本使用（旧图 11a 口径）。"""
    w = np.broadcast_to(latw[:, None], field.shape)
    m = mask & np.isfinite(field)
    den = float(np.nansum(w[m]))
    return float("nan") if den <= 0 else float(np.nansum(field[m] * w[m]) / den)


# ── 2D DCT 带通分解（与 Fig10.py 同一口径） ─────────────────
def compute_wavelength_map(ny: int, nx: int, lat: np.ndarray, lon: np.ndarray) -> np.ndarray:
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
    with np.errstate(divide="ignore"):
        wl = np.where(inv > 0, 1.0 / inv, np.inf)
    wl[0, 0] = np.inf
    return wl


def dct_filter_bands(field: np.ndarray, wavelength: np.ndarray,
                     breakpoints: list[float]) -> list[np.ndarray]:
    """DCT → 按断点分段掩膜 → iDCT；末档承接零频（幅值场不去均值，三档之和 = 原场）。"""
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


# ── 掩膜 ─────────────────────────────────────────────────
def make_china_mask(lat: np.ndarray, lon: np.ndarray) -> np.ndarray:
    sf = shapefile.Reader(str(SHP_PATH))
    merged = unary_union([shapely_shape(s.__geo_interface__) for s in sf.shapes()])
    china = unary_union(list(polygonize(merged))).buffer(0)
    prepped = prep(china)
    mask = np.zeros((len(lat), len(lon)), dtype=bool)
    for i, lt in enumerate(lat):
        for j, ln in enumerate(lon):
            mask[i, j] = prepped.intersects(Point(float(ln), float(lt)))
    return mask


def region_masks(lat: np.ndarray, lon: np.ndarray,
                 land_mask: np.ndarray) -> dict[str, np.ndarray]:
    masks: dict[str, np.ndarray] = {"China": land_mask}
    for reg in REGIONS:
        x0, x1, y0, y1 = reg["extent"]
        m = ((lon[np.newaxis, :] >= x0) & (lon[np.newaxis, :] <= x1)
             & (lat[:, np.newaxis] >= y0) & (lat[:, np.newaxis] <= y1))
        masks[reg["key"]] = m & land_mask
    return masks


def build_river_mask(shp_path: Path, lon_2d: np.ndarray, lat_2d: np.ndarray) -> np.ndarray:
    rsf = shapefile.Reader(str(shp_path))
    merged = unary_union([shapely_shape(s.__geo_interface__) for s in rsf.shapes()])
    minx, miny, maxx, maxy = merged.bounds
    mask = np.zeros(lon_2d.shape, dtype=bool)
    ii, jj = np.where((lon_2d >= minx) & (lon_2d <= maxx)
                      & (lat_2d >= miny) & (lat_2d <= maxy))
    for i, j in zip(ii, jj):
        mask[i, j] = merged.contains(Point(lon_2d[i, j], lat_2d[i, j]))
    return mask


# ── 绘图（单面板） ────────────────────────────────────────
def _plot_rate(ax, df: pd.DataFrame, band_labels: list[str], ref: float) -> None:
    """各区域三档不确定性缩减率（%），分组柱 + 全国水平参考线。"""
    names = df["region"].values
    v = np.column_stack([df[f"rate_s{i+1}"].values.astype(float) for i in range(3)]) * 100.0
    n = v.shape[1]
    bar_w = 0.78 / n
    x = np.arange(len(df))
    vmax = float(np.nanmax(v)) * 1.38
    for i in range(n):
        off = (i - (n - 1) / 2) * bar_w
        ax.bar(x + off, v[:, i], bar_w * 0.9, color=BAND_COLORS[i], label=band_labels[i])
        for xi, vi in zip(x + off, v[:, i]):
            ax.text(xi, vi + 0.035 * vmax, f"{vi:.1f}", ha="center", va="bottom",
                    fontsize=10, fontweight="bold", color=BAND_COLORS[i])

    # 2026-10-12 按作者要求去掉面板内的全国水平参考线及其注记（"China mean 20.7%"）：
    # 全国总缩减率只在图注中说明，面板内不再画线。
    ax.set_ylim(0, vmax)
    ax.set_xticks(x)
    ax.set_xticklabels([REGION_LABELS.get(k, k) for k in names], rotation=30, ha="right")
    # 纵轴标题点明"是 σ（不确定性）的缩减率、且每档各自成率"，避免读成可加的总量
    ax.set_ylabel("Reduction rate of $\\sigma$\nper scale (%)", fontsize=15)
    ax.grid(axis="y", ls="--", alpha=0.3)
    ax.legend(loc="lower left", bbox_to_anchor=(0.0, 1.0), ncol=3, frameon=False,
              fontsize=12, handlelength=1.3, columnspacing=1.4, borderaxespad=0.2)
    print(f"  缩减率：{len(df)} 区域 × 3 档，{v.min():.1f}%–{v.max():.1f}%；"
          f"全国 {np.round(v[0], 1).tolist()}，图中参考线（全场口径）={ref:.1f}%")


# ── 流水线 ①：图 11 主流程（原 Fig11.py 的 main） ─────────────
def run_fig11() -> None:
    """读 σ 场 → 三档 DCT 分解 → 区域统计 → data/uncertainty_reduction.csv + Fig11.jpg。"""
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    FIG_DIR.mkdir(parents=True, exist_ok=True)

    # 1. 读 σ 场（nc 中 prior_std / posterior_std 即模式间标准差 σ）
    with xr.open_dataset(NC_PATH) as ds:
        ds = ds.load()
    lat = np.asarray(ds.lat.values, dtype=float)
    lon = np.asarray(ds.lon.values, dtype=float)
    prior_sigma = np.asarray(ds["prior_std"].values, dtype=float)
    post_sigma = np.asarray(ds["posterior_std"].values, dtype=float)
    print(f"σ fields: prior {prior_sigma.shape}, posterior {post_sigma.shape}")

    # 2. 断点（沿用图 10 从 Bias 谱检出的特征尺度）
    with open(BP_PATH) as f:
        bps = sorted(json.load(f).get("selected_breakpoints", []))
    bps = [b for b in bps if b >= 200][:2]
    limits = [0.0] + bps + [np.inf]
    band_labels = []
    for lo, hi in zip(limits[:-1], limits[1:]):
        if np.isinf(hi):
            band_labels.append(f"\u2265 {lo:.0f} km")
        elif lo == 0.0:
            band_labels.append(f"\u2264{hi:.0f} km")
        else:
            band_labels.append(f"{lo:.0f}\u2013{hi:.0f} km")
    print(f"Breakpoints: {bps} → bands {band_labels}")

    # 3. 尺度分解（幅值场不去均值；三档之和 = 原 σ 场）
    wl = compute_wavelength_map(*prior_sigma.shape, lat, lon)
    f_prior = np.nan_to_num(prior_sigma, nan=0.0, posinf=0.0, neginf=0.0)
    f_post = np.nan_to_num(post_sigma, nan=0.0, posinf=0.0, neginf=0.0)
    bands_prior = dct_filter_bands(f_prior, wl, bps)
    bands_post = dct_filter_bands(f_post, wl, bps)
    print(f"重建误差 max|Σσ_b − σ| = {np.nanmax(np.abs(sum(bands_prior) - f_prior)):.2e}（先验）")

    # 4. 掩膜
    land_mask = make_china_mask(lat, lon) & np.isfinite(prior_sigma)
    rmasks = region_masks(lat, lon, land_mask)
    lon_2d, lat_2d = np.meshgrid(lon, lat)
    for rname, rfp in RIVER_BASINS:
        if rfp.exists():
            rmasks[rname] = build_river_mask(rfp, lon_2d, lat_2d)
    print(f"全国陆地格点 {int(land_mask.sum())}")

    # 5. 逐区域统计
    latw = _lat_weights(lat)
    rows = []
    for rkey, rm in rmasks.items():
        if rm.sum() == 0:
            continue
        a_pri = np.array([_wmean_abs(f, rm, latw) for f in bands_prior])
        a_pos = np.array([_wmean_abs(f, rm, latw) for f in bands_post])
        red = a_pri - a_pos
        row = {"region": rkey, "n_grid": int(rm.sum()),
               "sigma_prior": float(a_pri.sum()), "sigma_post": float(a_pos.sum()),
               "total_reduction": float(red.sum()),
               "r_total": float(red.sum() / a_pri.sum())}
        for i in range(len(bps) + 1):
            row[f"mag_prior_s{i+1}"] = float(a_pri[i])
            row[f"mag_post_s{i+1}"] = float(a_pos[i])
            row[f"reduction_s{i+1}"] = float(red[i])
            row[f"rate_s{i+1}"] = float(red[i] / a_pri[i])
        rows.append(row)

    df = pd.DataFrame(rows)
    df.to_csv(DATA_DIR / "uncertainty_reduction.csv", index=False)
    print(f"\nSaved: {DATA_DIR / 'uncertainty_reduction.csv'}")
    show = df[["region", "sigma_prior", "sigma_post", "r_total",
               "rate_s1", "rate_s2", "rate_s3"]].copy()
    for c in show.columns[1:]:
        show[c] = show[c].round(4)
    print(show.to_string(index=False))

    # 6. 出图（单面板：各区域三档缩减率）
    df_plot = df[~df["region"].isin([b[0] for b in RIVER_BASINS])].reset_index(drop=True)
    # 参考线口径：不经分档，直接用**原场**的先验/后验区域平均（cos φ 加权）相除，
    # 全国 20.7%，与摘要一致。注意它与逐区域 r_total（= 1 − Σ_b⟨|σ_post,b|⟩/Σ_b⟨|σ_prior,b|⟩，
    # 全国 20.6%）虽都出自同一批数据，但基线不同：原场平均 σ_prior = 2.002 对分档求和 2.377
    # （差额 = 小尺度档在区域平均时被抵消掉的那部分），见 README.md「方法说明」第五节。
    ref = (1.0 - _wmean_abs(post_sigma, rmasks["China"], latw)
           / _wmean_abs(prior_sigma, rmasks["China"], latw)) * 100.0

    fig, ax = plt.subplots(figsize=(7.874, 4.3))
    _plot_rate(ax, df_plot, band_labels, ref)

    fig.subplots_adjust(left=0.115, right=0.985, top=0.885, bottom=0.215)
    out = FIG_DIR / "Fig11.jpg"
    fig.savefig(out, dpi=400)
    plt.close(fig)
    print(f"Saved: {out}")


# ── 流水线 ②：尺度谱对照（原 尺度谱.py） ─────────────────────
def compute_spectrum(field: np.ndarray, lat: np.ndarray,
                     lon: np.ndarray) -> pd.DataFrame:
    """对二维场计算 2D DCT 波长-方差谱（对数分箱内 power 求和）。"""
    ny, nx = field.shape

    f = np.nan_to_num(field, nan=0.0, posinf=0.0, neginf=0.0)
    coeff = np.asarray(dctn(f, type=2, norm="ortho"), dtype=float)
    power = coeff ** 2 / (nx * ny)

    dlat = float(np.mean(np.abs(np.diff(lat))))
    dlon = float(np.mean(np.abs(np.diff(lon))))
    dy = np.deg2rad(dlat) * EARTH_RADIUS_KM
    lat_cos = float(np.mean(np.cos(np.deg2rad(lat))))
    dx = np.deg2rad(dlon) * EARTH_RADIUS_KM * lat_cos

    ly = dy * (ny - 1)
    lx = dx * (nx - 1)

    ky = np.arange(ny, dtype=float)
    kx = np.arange(nx, dtype=float)
    wl_y = np.full(ny, np.inf)
    wl_y[1:] = 2.0 * ly / ky[1:]
    wl_x = np.full(nx, np.inf)
    wl_x[1:] = 2.0 * lx / kx[1:]

    inv = np.sqrt((1.0 / wl_y[:, None]) ** 2 + (1.0 / wl_x[None, :]) ** 2)
    wavelength = np.where(inv > 0, 1.0 / inv, np.inf)

    pw = power.ravel()
    wl = wavelength.ravel()
    ok = np.isfinite(wl) & (wl > 0) & np.isfinite(pw)
    wl, pw = wl[ok], pw[ok]

    if wl.size == 0:
        return pd.DataFrame(columns=["wavelength_km", "variance"])

    wl_min = float(np.min(wl))
    wl_max = float(np.max(wl))
    n_bins = 45
    bins = np.geomspace(wl_min * 0.9, wl_max * 1.1, n_bins)

    idx = np.digitize(wl, bins)
    rows = []
    for i in range(1, len(bins)):
        mask = idx == i
        if mask.any():
            center = np.sqrt(bins[i - 1] * bins[i])
            rows.append((center, float(np.sum(pw[mask]))))

    mask_last = idx == len(bins)
    if mask_last.any():
        center = np.sqrt(bins[-1] * wl_max)
        rows.append((center, float(np.sum(pw[mask_last]))))

    return pd.DataFrame(rows, columns=["wavelength_km", "variance"])


def run_spectrum(out_path: Path) -> None:
    """先验/后验 σ 与方差缩减量的波长-方差谱 → data/uncertainty_spectrum.csv。

    备用谱图 fig11a.jpg 写到 `out_path`：由 `main()` 传入 `_spectrum_scratch()` 提供的、
    **模块之外**的运行期临时目录，退出 with 块即整目录删除，模块根不留任何文件；
    绘图逻辑与原 `尺度谱.py` 完全一致。

    注：原 `尺度谱.py` 是独立脚本，运行时用的是 matplotlib **默认** rcParams；本文件为图 11
    在模块级改了 rcParams（Times New Roman 等）。为保持该步骤产出的谱图与合并前单独运行
    `尺度谱.py` 时一致，这里用 `plt.rc_context(plt.rcParamsDefault)` 局部还原默认值。
    """
    DATA_DIR.mkdir(parents=True, exist_ok=True)

    # ---------- 读取数据 ----------
    with xr.open_dataset(NC_PATH) as ds:
        ds = ds.load()
    lat = np.asarray(ds.lat.values, dtype=float)
    lon = np.asarray(ds.lon.values, dtype=float)

    prior_std = np.asarray(ds["prior_std"].values, dtype=float)
    posterior_std = np.asarray(ds["posterior_std"].values, dtype=float)
    prior_var = prior_std ** 2
    post_var = posterior_std ** 2
    var_reduction = prior_var - post_var

    print(f"prior_std: {prior_std.shape}, posterior_std: {posterior_std.shape}")

    # ---------- 计算三个场的 DCT 谱 ----------
    spec_prior = compute_spectrum(prior_std, lat, lon)
    spec_posterior = compute_spectrum(posterior_std, lat, lon)
    spec_reduction = compute_spectrum(var_reduction, lat, lon)

    # 合并保存
    merged = spec_prior.rename(
        columns={"variance": "prior_var"}
    ).merge(
        spec_posterior.rename(columns={"variance": "post_var"}),
        on="wavelength_km", how="outer"
    ).merge(
        spec_reduction.rename(columns={"variance": "reduction_var"}),
        on="wavelength_km", how="outer"
    ).sort_values("wavelength_km")

    merged.to_csv(DATA_DIR / "uncertainty_spectrum.csv", index=False)
    print(f"Spectra saved: {len(merged)} bins")

    # ---------- 读取断点 ----------
    with open(BP_PATH) as f:
        bp_info = json.load(f)
    selected_bps = sorted(bp_info.get("selected_breakpoints", []))
    all_bps_data = bp_info.get("multi_breakpoints", [])  # noqa: F841（备用，原脚本保留）

    print(f"Breakpoints: {selected_bps}")

    # ---------- 绘图 ----------
    with plt.rc_context(plt.rcParamsDefault):
        fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(14, 5.5))

        # ---- 左图: prior vs posterior std 谱对比 ----
        ax1.plot(spec_prior["wavelength_km"], spec_prior["variance"],
                 color="#1f77b4", lw=2, label="Prior std")
        ax1.plot(spec_posterior["wavelength_km"], spec_posterior["variance"],
                 color="#d62728", lw=2, label="Posterior std")
        ax1.set_xscale("log")
        ax1.set_yscale("log")
        ax1.set_xticks([200, 500, 1000, 2000, 5000, 10000, 20000])
        ax1.get_xaxis().set_major_formatter(FuncFormatter(lambda v, _: f"{v:.0f}"))
        ax1.set_ylabel("Variance [(mm/day)$^2$]")
        ax1.set_xlabel("Wavelength (km)")
        ax1.set_title("(a) Uncertainty std spectrum")
        ax1.legend(fontsize=9)
        ax1.grid(True, which="both", ls="--", alpha=0.3)
        ax1.tick_params(labelsize=9)

        # 标注 selected 断点
        for bp in selected_bps:
            ax1.axvline(bp, color="gray", ls="-", lw=1.5, alpha=0.7)
            ax1.text(bp, 0.95, f"  {bp:.0f} km",
                     transform=ax1.get_xaxis_transform(),
                     rotation=90, va="top", ha="left", color="gray", fontsize=8)

        # ---- 右图: 方差缩减谱 ----
        ax2.plot(spec_reduction["wavelength_km"], spec_reduction["variance"],
                 color="#2ca02c", lw=2, label="Var reduction\n(prior$^2$ − posterior$^2$)")
        ax2.set_xscale("log")
        ax2.set_yscale("log")
        ax2.set_xticks([200, 500, 1000, 2000, 5000, 10000, 20000])
        ax2.get_xaxis().set_major_formatter(FuncFormatter(lambda v, _: f"{v:.0f}"))
        ax2.set_ylabel("Variance [(mm/day)$^2$]")
        ax2.set_xlabel("Wavelength (km)")
        ax2.set_title("(b) Variance reduction spectrum")
        ax2.legend(fontsize=9)
        ax2.grid(True, which="both", ls="--", alpha=0.3)
        ax2.tick_params(labelsize=9)

        for bp in selected_bps:
            ax2.axvline(bp, color="gray", ls="-", lw=1.5, alpha=0.7)
            ax2.text(bp, 0.95, f"  {bp:.0f} km",
                     transform=ax2.get_xaxis_transform(),
                     rotation=90, va="top", ha="left", color="gray", fontsize=8)

        fig.tight_layout()
        fig.savefig(out_path, bbox_inches="tight", dpi=400)
        plt.close(fig)
    print(f"[DONE] 备用谱图（仅运行期临时文件，随之自动删除）：{out_path}")


# ── 诊断 ①：有符号平均的相消率（原 _calc_cancellation.py） ──────
def run_cancellation() -> None:
    """辅助核算：有符号区域平均 vs 区域平均绝对值 —— 相消有多严重。

    对全国（cnmap 陆地掩膜）与华中的先验 σ 三档分量，比较
        ⟨σ_b⟩         有符号区域平均（旧图 11a 口径）
        ⟨|σ_b|⟩       区域平均绝对值（现行口径）
        相消率 = 1 − |⟨σ_b⟩| / ⟨|σ_b|⟩
    并在整矩形域（无掩膜）上给出 ∑σ_b 的全域平均，用于验证带通分量本身零均值。
    只读运行，无产物。（**非默认**：需 `--cancellation`）
    """
    with xr.open_dataset(NC_PATH) as ds:
        ds = ds.load()
    lat = np.asarray(ds.lat.values, float)
    lon = np.asarray(ds.lon.values, float)
    sp = np.asarray(ds["prior_std"].values, float)

    # 原脚本在此处内联重算 cnmap 掩膜，与 make_china_mask() 逐步等价，故直接复用
    LON, LAT = np.meshgrid(lon, lat)
    mask_cn = make_china_mask(lat, lon) & np.isfinite(sp)
    mask_cc = (LON >= 108) & (LON <= 115) & (LAT >= 26) & (LAT <= 34) & np.isfinite(sp)

    wl = compute_wavelength_map(*sp.shape, lat, lon)
    bands = dct_filter_bands(np.nan_to_num(sp, nan=0.0), wl, CANCEL_BREAKPOINTS)
    latw = _lat_weights(lat)
    LAB = ["≤1409 km", "1409–4898 km", "≥4898 km"]

    print("整矩形域（含海洋，无掩膜）逐档的域平均 —— 检验带通分量是否零均值")
    for i, f in enumerate(bands):
        print(f"  {LAB[i]:14s} ⟨σ_b⟩={f.mean():+.4f}   ⟨|σ_b|⟩={np.abs(f).mean():.4f}")

    for tag, m in (("全国（cnmap 陆地掩膜）", mask_cn), ("华中（经纬框 ∩ 陆地）", mask_cc)):
        print(f"\n[{tag}]")
        print(f"  {'档':14s} {'⟨σ_b⟩ 有符号':>14s} {'⟨|σ_b|⟩ 绝对值':>14s} {'相消率':>8s}")
        for i, f in enumerate(bands):
            s, a = _wmean_signed(f, m, latw), _wmean_abs(f, m, latw)
            print(f"  {LAB[i]:14s} {s:14.3f} {a:14.3f} {100 * (1 - abs(s) / a):7.1f}%")
        s_all = sum(_wmean_signed(f, m, latw) for f in bands)
        a_all = sum(_wmean_abs(f, m, latw) for f in bands)
        print(f"  {'三档合计':14s} {s_all:14.3f} {a_all:14.3f} "
              f"（全场直接算 ⟨σ⟩={_wmean_signed(sp, m, latw):.3f}，"
              f"绝对值 ⟨|σ|⟩={_wmean_abs(sp, m, latw):.3f}）")


# ── 诊断 ②：三种总缩减率口径交叉校验（原 _calc_cross_check.py） ──
def run_cross_check() -> None:
    """核算（第二组）：用 cnmap 陆地掩膜直接算先验/后验 σ 的区域平均，交叉验证 20.5% 与 20.7%。

    对比三个口径：
      ① 全场直接算：⟨σ_prior⟩、⟨σ_post⟩ 与 1 − ⟨σ_post⟩/⟨σ_prior⟩
      ② 三档幅值之和：Σ_b⟨|σ_b|⟩ 与 Σ_b(⟨|σ_prior,b|⟩−⟨|σ_post,b|⟩)/Σ_b⟨|σ_prior,b|⟩
      ③ 逐格点缩减率的区域平均：⟨1 − σ_post/σ_prior⟩（图 6b 的面板口径）
    只读运行，无产物。（**非默认**：需 `--cross-check`）
    """
    with xr.open_dataset(NC_PATH) as ds:
        ds = ds.load()
    lat = np.asarray(ds.lat.values, float)
    lon = np.asarray(ds.lon.values, float)
    sp = np.asarray(ds["prior_std"].values, float)
    sq = np.asarray(ds["posterior_std"].values, float)

    cm = make_china_mask(lat, lon)
    land = cm & np.isfinite(sp)
    latw = _lat_weights(lat)
    finite = np.isfinite(sp)

    print(f"cnmap 掩膜格点数 {cm.sum()}；其中 σ 有效 {land.sum()}；"
          f"直接 finite 掩膜 {finite.sum()}")

    for tag, mask in (("cnmap 陆地掩膜", land), ("finite 掩膜（含海洋=NaN 已排除）", finite)):
        p, q = _wmean_abs(sp, mask, latw), _wmean_abs(sq, mask, latw)
        rate_pts = _wmean_signed(1.0 - sq / np.where(sp > 0, sp, np.nan), mask, latw)
        print(f"\n[{tag}]")
        print(f"  ① 直接：⟨σ_prior⟩={p:.3f}  ⟨σ_post⟩={q:.3f}  "
              f"1−后验/先验={100*(1-q/p):.1f}%")
        print(f"  ③ 逐格点缩减率区域平均 = {100*rate_pts:.1f}%")

    # 2026-10-12：改为在本脚本内直接做 DCT 分解，不再依赖 data/ 下的 *.npy 中间场
    # （那些 npy 由旧版 Fig11.py 写出、口径已变，已清理）。
    # 合并后断点直接读统一的 BP_PATH（与原 `ROOT/src/Pic/Fig10_.../breakpoint.json` 同一文件）。
    _rb = json.loads(BP_PATH.read_text(encoding="utf-8"))
    _bps = sorted(_rb["selected_breakpoints"])[:2]
    _wl = compute_wavelength_map(*sp.shape, lat, lon)
    pri = dct_filter_bands(np.nan_to_num(sp, nan=0.0), _wl, _bps)
    pos = dct_filter_bands(np.nan_to_num(sq, nan=0.0), _wl, _bps)
    print(f"\n[② 三档幅值之和]（断点 {[round(b) for b in _bps]} km，本脚本内重算）")
    for tag, mask in (("cnmap 陆地掩膜", land), ("finite 掩膜", finite)):
        a = np.array([_wmean_abs(f, mask, latw) for f in pri])
        b = np.array([_wmean_abs(f, mask, latw) for f in pos])
        print(f"  {tag}: Σ先验={a.sum():.3f} Σ后验={b.sum():.3f} "
              f"总缩减率={100*(a-b).sum()/a.sum():.1f}%  "
              f"三档幅值={np.round(a,3).tolist()}")


# ── 诊断 ③：13/38/49 溯源（原 _trace_13_38_49.py） ────────────
def run_trace() -> int:
    """核对：草稿摘要里的 13% / 38% / 49% 究竟出自哪一版口径。

    做法：从 git HEAD 取旧的 uncertainty_decomposition.csv（10-09 之前的产物），
    按几种可能定义各算一遍三档份额，看哪一种能复现 13/38/49。

    该脚本读的是 git HEAD 里的旧路径，而 `data/uncertainty_decomposition.csv` 在当前仓库
    HEAD 中已不存在，故 `git show` 会失败；这里捕获后给出明确提示并返回 1（不再抛栈）。
    （**非默认**：需 `--trace`）
    """
    REL = "src/Pic/Fig11_UncertaintyDecomposition/data/uncertainty_decomposition.csv"

    proc = subprocess.run(
        ["git", "show", f"HEAD:{REL}"],
        cwd=REPO_ROOT.parent, capture_output=True, text=True,
    )
    if proc.returncode != 0:
        print(f"[--trace] `git show HEAD:{REL}` 失败（该路径在当前 git HEAD 中已不存在）：")
        print((proc.stderr or "").strip() or "(git 未返回错误信息)")
        print("  该诊断用于历史溯源，当前仓库已无此旧产物，无法复算 13/38/49；"
              "如仍需核对，请从包含旧产物的历史 commit 取该 CSV。")
        return 1

    old = pd.read_csv(io.StringIO(proc.stdout))

    print("旧 CSV 的区域行：", len(old), "；列：", [c for c in old.columns][:8])
    print(f"\n{'region':13s} {'定义A: 三档幅值之和':>28s} {'定义B: 全场均值之比':>26s}")
    print(f"{'':13s} {'r_tot':>7s} {'份额(小/中/大)':>20s} {'r_tot':>7s} {'份额(小/中/大)':>20s}")
    for _, r in old.iterrows():
        p = [r["prior_mag1"], r["prior_mag2"], r["prior_mag3"]]
        q = [r["post_mag1"], r["post_mag2"], r["post_mag3"]]
        red = [p[i] - q[i] for i in range(3)]
        tot = sum(red)
        a_rate = tot / sum(p) * 100
        a_share = [x / tot * 100 for x in red]

        # 定义 B：用全场总量（prior_total_mag）作分母，但份额仍按各档缩减量占全局缩减量
        b_rate = (r["prior_total_mag"] - r["post_total_mag"]) / r["prior_total_mag"] * 100
        b_tot = r["prior_total_mag"] - r["post_total_mag"]
        b_share = [x / b_tot * 100 for x in red]

        print(f"{r['region']:13s} {a_rate:6.1f}% "
              f"{a_share[0]:6.1f}/{a_share[1]:5.1f}/{a_share[2]:5.1f}  "
              f"{b_rate:6.1f}% {b_share[0]:6.1f}/{b_share[1]:5.1f}/{b_share[2]:5.1f}")

        if r["region"] == "China":
            print(f"    旧全国 先验三档幅值={[round(v,3) for v in p]} 和={sum(p):.3f}；"
                  f"prior_total_mag={r['prior_total_mag']:.3f}，差额={sum(p) - r['prior_total_mag']:.3f}")
            print(f"    旧全国 后验三档幅值={[round(v,3) for v in q]} 和={sum(q):.3f}；"
                  f"post_total_mag={r['post_total_mag']:.3f}")
    return 0


# ── 入口 ─────────────────────────────────────────────────
@contextlib.contextmanager
def _spectrum_scratch(name: str = "fig11a.jpg"):
    """给备用谱图一个"用完即删"的临时目录，yield 出该目录下的完整文件路径。

    目录建在**模块之外**（仓库目录的上一级，即工作区根：`_tmp_fig11_<随机 8 位>`），用
    `os.makedirs()` 的**默认权限**创建；退出 with 块时 `shutil.rmtree(..., ignore_errors=True)`
    整目录删除，因此模块根不会多出任何文件。

    为什么不用 `tempfile.TemporaryDirectory()` / `mkdtemp()`：它们固定以 `os.mkdir(path, 0o700)`
    建目录，在本机（Windows + 受限沙箱）该权限位会得到一个连本进程都读不了、写不进、也删不掉的
    目录（`PermissionError`，且事后无法清理），故这里显式使用默认权限。
    """
    scratch = REPO_ROOT.parent / f"_tmp_fig11_{uuid.uuid4().hex[:8]}"
    os.makedirs(scratch)
    try:
        yield scratch / name
    finally:
        shutil.rmtree(scratch, ignore_errors=True)


def main() -> int:
    parser = argparse.ArgumentParser(
        prog="Fig11.py",
        description="Fig.11 单文件流水线：先验/后验不确定性缩减的尺度分解 + 尺度谱对照。"
                    "不带参数时跑完整流水线；带诊断开关时只跑诊断。",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="示例：\n"
               "  python Fig11.py                 # 完整流水线（Fig11.jpg + 两份 CSV）\n"
               "  python Fig11.py --cancellation  # 有符号/绝对值区域平均的相消率\n"
               "  python Fig11.py --cross-check   # 三种总缩减率口径交叉校验\n"
               "  python Fig11.py --trace         # 13/38/49 溯源（依赖已不存在的 git HEAD 旧产物）\n",
    )
    parser.add_argument("--cross-check", action="store_true",
                        help="只跑诊断②：三种总缩减率口径交叉校验（默认不跑）")
    parser.add_argument("--cancellation", action="store_true",
                        help="只跑诊断①：有符号区域平均 vs 区域平均绝对值的相消率（默认不跑）")
    parser.add_argument("--trace", action="store_true",
                        help="只跑诊断③：从 git HEAD 旧产物溯源 13/38/49（默认不跑；预期失败）")
    args = parser.parse_args()

    # 诊断开关：显式给出时才跑，且不重跑流水线（避免无意中覆盖产物）
    if args.cross_check or args.cancellation or args.trace:
        rc = 0
        if args.cancellation:
            print("=" * 72, "\n[诊断①] 有符号区域平均 vs 区域平均绝对值（相消率）\n" + "=" * 72)
            run_cancellation()
        if args.cross_check:
            print("=" * 72, "\n[诊断②] 三种总缩减率口径交叉校验\n" + "=" * 72)
            run_cross_check()
        if args.trace:
            print("=" * 72, "\n[诊断③] 13/38/49 溯源\n" + "=" * 72)
            rc |= run_trace()
        return rc

    # 默认：完整流水线，顺序与原两脚本一致（先图 11，后尺度谱）
    run_fig11()
    # 谱对照步骤的备用谱图只写**模块之外**的运行期临时目录：退出 with 块即整目录删除，
    # 保证模块根下恒为 Fig11.py / Fig11.jpg / data/ / README.md 四项。
    with _spectrum_scratch() as scratch:
        run_spectrum(scratch)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
