"""
图 1 —— 观测层：四套格点降水产品对约束因子与目标变量的气候态刻画

布局：两个指标块上下排列，每块 = 2×2 排列的四套产品（只画观测本身）。
      (a) PrecipVar（约束因子）、(b) R95 Intensity（目标变量）——每块只标一个指标编号。
时段：1981–2010 气候态（各产品取自身可获得年份与该时段的交集）
变更：2026-10-09 移除原第三列"Inter-observation Uncertainty (σ)"面板。产品间标准差 σ 仍在本脚本内计算，
      并写入 data/图1_统计数据.txt 与 data/fig1_stats.csv 留档（它是 HEC 观测层估计观测误差项 σ_o 的基础）。

用法：python Fig1.py
输出：Fig1.jpg、data/图1_统计数据.txt、data/fig1_stats.csv
"""
from __future__ import annotations

from pathlib import Path

import warnings

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import shapefile
import xarray as xr
from matplotlib.colors import BoundaryNorm
from matplotlib.ticker import FuncFormatter
from shapely.geometry import Point, shape as shapely_shape
from matplotlib.path import Path as MplPath
from shapely.ops import polygonize, unary_union

import cartopy.crs as ccrs

warnings.filterwarnings("ignore", message="Degrees of freedom <= 0")
plt.rcParams["font.family"] = ["Times New Roman", "DejaVu Sans"]
plt.rcParams["mathtext.fontset"] = "cm"
plt.rcParams["axes.unicode_minus"] = False

ROOT = Path(__file__).resolve().parent
REPO_ROOT = next(p for p in Path(__file__).resolve().parents if (p / "src").is_dir() and (p / "Doc").is_dir())

# ---- 数据根目录 ----------------
# src/、Output/、Data/ 现均在论文文件夹内（与 Doc/ 同级），故直接取 REPO_ROOT/Data；
# 若将来数据被移到别处，再恢复向上搜索的兜底逻辑。
DATA_ROOT = REPO_ROOT / "Data"
OBS_DIR = REPO_ROOT / "Output" / "Obs" / "indices"
SHP_PATH = DATA_ROOT / "China" / "cnmap.shp"
FIG_DIR = ROOT
DOC_DIR = ROOT / "data"
DATA_DIR = ROOT / "data"                     # CSV 统计落盘目录
FIG_DIR.mkdir(parents=True, exist_ok=True)
DOC_DIR.mkdir(parents=True, exist_ok=True)
DATA_DIR.mkdir(parents=True, exist_ok=True)

PROJ = ccrs.PlateCarree()
PERIOD = (1981, 2010)

# 四套观测产品（顺序：CN05.1、HGCDC、CHM PRE V2、CPC）
PRODUCTS = [
    ("CN05.1", "CN05-OBS-IntensityAndPrecipVar-1961-2023.nc"),
    ("HGCDC", "HGCDC-OBS-IntensityAndPrecipVar-1961-2022.nc"),
    ("CHM PRE V2", "CHM_PRE_V2-OBS-IntensityAndPrecipVar-1961-2024.nc"),
    ("CPC", "CPC-OBS-IntensityAndPrecipVar-1979-2025.nc"),
]
# 两行：约束因子与目标变量
ROWS = [
    ("PrecipVar", "Precip Var", "mm/day", "YlGnBu", 0.25),
    ("R95mm_intensity", "R95 Intensity", "mm/day", "YlOrRd", 2.5),
]
# 落盘 CSV 用的指标名（键为 ROWS 中的变量名）
METRIC_CSV = {
    "PrecipVar": "PrecipVar",
    "R95mm_intensity": "R95 Intensity",
}
MAX_LEVELS = 10

def _fmt_tick(v, _pos=None):
    """刻度标签：整数不带小数，非整数保留 1 位小数（全图统一口径）。"""
    return f"{v:.0f}" if abs(v - round(v)) < 1e-9 else f"{v:.1f}"


# ---- 中国国界 ----
sf = shapefile.Reader(str(SHP_PATH))
cn_geoms = [shapely_shape(s.__geo_interface__) for s in sf.shapes()]
bb = sf.bbox
EXTENT = [float(bb[0]) - 1, float(bb[2]) + 1, float(bb[1]) - 1, float(bb[3]) + 1]


def china_mask(lon: np.ndarray, lat: np.ndarray) -> np.ndarray:
    """中国陆域掩膜：cnmap.shp → polygonize → 向量化 Path（毫秒级），与图 8/图 9 同源。"""
    lines_geo = [shapely_shape(s.__geo_interface__) for s in shapefile.Reader(str(SHP_PATH)).shapes()]
    china = unary_union(list(polygonize(unary_union(lines_geo)))).buffer(0)
    verts, codes = [], []
    for poly in (china.geoms if china.geom_type == "MultiPolygon" else [china]):
        xy = np.asarray(poly.exterior.coords)
        if xy.shape[0] < 3:
            continue
        verts.append(xy)
        codes.append([MplPath.MOVETO] + [MplPath.LINETO] * (xy.shape[0] - 2) + [MplPath.CLOSEPOLY])
    path = MplPath(np.vstack(verts), np.concatenate(codes))
    # 平坦顺序须与 reshape(lat, lon) 一致：外层遍历 lat、内层遍历 lon
    pts = np.column_stack([np.tile(lon, lat.size), np.repeat(lat, lon.size)])
    m = path.contains_points(pts).reshape(lat.size, lon.size)
    print(f"  中国陆域掩膜：{int(m.sum())} / {m.size} 个格点")
    return m


def lat_weights(lat: np.ndarray) -> np.ndarray:
    return np.clip(np.cos(np.deg2rad(lat)), 0.0, None)


def wmean(field: np.ndarray, lat: np.ndarray) -> float:
    w = np.broadcast_to(lat_weights(lat)[:, None], field.shape)
    ok = np.isfinite(field)
    return float(np.nansum(np.where(ok, field, 0) * w) / np.nansum(w * ok)) if ok.any() else float("nan")


def levels_of(vmin: float, vmax: float, step_hint: float) -> np.ndarray:
    """按步长提示生成等距分级（档数不超过 MAX_LEVELS）。"""
    step = step_hint
    while (vmax - vmin) / step > MAX_LEVELS:
        step *= 2
    lo = np.floor(vmin / step) * step
    hi = np.ceil(vmax / step) * step
    return np.round(np.arange(lo, hi + step * 0.5, step), 4)


def load_field(fname: str, var: str):
    with xr.open_dataset(OBS_DIR / fname) as ds:
        da = ds[var].sel(year=slice(*PERIOD)).mean("year", skipna=True)
        lat = da["lat"].values.astype(float)
        lon = da["lon"].values.astype(float)
        fld = da.values.astype(float)
    if lat[0] > lat[-1]:                       # 统一为升序，便于 contourf
        lat, fld = lat[::-1], fld[::-1, :]
    return lon, lat, fld


def main() -> None:
    print("=" * 60)
    print("Fig. 1: 观测层（四套观测产品）")
    print("=" * 60)

    fig_w_cm, fig_h_cm = 19.0, 18.8
    fig = plt.figure(figsize=(fig_w_cm / 2.54, fig_h_cm / 2.54))
    pw, ph = 3.55, 3.30
    pgx = 0.80                   # 2×2 块内列距（容下第二列的纬度标注）
    pgy_block = 0.78           # 2×2 块内行距（容纳上行经度标签 + 下行标题）
    cbar_h = 0.16
    lmar = 0.55
    # 两个指标块自下而上：r=0（Precip Var）在上，r=1（R95 Intensity）在下
    block_bottom = [9.63, 0.30]

    def R(l, b, w, h):
        return (l / fig_w_cm, b / fig_h_cm, w / fig_w_cm, h / fig_h_cm)

    mask = None
    stats: list[str] = []
    csv_rows: list[dict] = []           # data/fig1_stats.csv 的行记录
    letters = "ab"                      # 每块只标一个指标编号

    for r, (var, vlabel, unit, cmap, step_hint) in enumerate(ROWS):
        y_bot = block_bottom[r]
        y_top = block_bottom[r] + ph + pgy_block
        fields, lons, lats = [], None, None
        for name, fname in PRODUCTS:
            lon, lat, fld = load_field(fname, var)
            lons, lats = lon, lat
            if mask is None:
                mask = china_mask(lon, lat)
            fields.append(np.where(mask, fld, np.nan))
            print(f"  {vlabel:14s} {name:11s} 全域面积加权均值 = {wmean(fld, lat):8.3f}")
        stack = np.stack(fields)
        spread = np.nanstd(stack, axis=0, ddof=0)      # 产品间标准差 σ（统计文件留档；不再出图）
        variance = spread ** 2                          # 产品间方差（留档）
        finite = np.concatenate([f[np.isfinite(f)] for f in fields])
        # 色带上下限取实际极值（2026-09-22 统一口径）；档数沿用 levels_of 在原 1–99%
        # 参考范围下给出的档数，只把首尾拉到实际极值，避免向外取整造成"空档"。
        vmin, vmax = float(np.nanmin(finite)), float(np.nanmax(finite))
        _p1, _p99 = float(np.percentile(finite, 1)), float(np.percentile(finite, 99))
        n_bands = len(levels_of(_p1, _p99, step_hint)) - 1
        levels = np.round(np.linspace(vmin, vmax, n_bands + 1), 4)
        n_bins = len(levels) - 1
        # extend="both" 时两端延伸箭头各占一色 ⇒ 颜色数 = 档数 + 2
        cmap_obj = plt.get_cmap(cmap, n_bins + 2)
        norm = BoundaryNorm(levels, ncolors=n_bins + 2, extend="both")

        # 4 套产品 → 2×2（列 1–2；阅读顺序：左上、右上、左下、右下）
        for c, ((name, _), fld) in enumerate(zip(PRODUCTS, fields)):
            _x = lmar + (c % 2) * (pw + pgx)
            _y = y_top if c < 2 else y_bot
            ax = fig.add_axes(R(_x, _y, pw, ph), projection=PROJ)
            ax.set_extent(EXTENT, crs=PROJ)
            ax.contourf(lons, lats, fld, levels=levels, cmap=cmap_obj, norm=norm,
                        transform=PROJ, extend="both")
            ax.contour(lons, lats, fld, levels=levels[1:-1], colors="black",
                       linewidths=0.25, transform=PROJ)
            ax.add_geometries(cn_geoms, crs=PROJ, facecolor="none", edgecolor="#666666", linewidth=0.4)
            gl = ax.gridlines(draw_labels=True, linewidth=0.2, alpha=0.4, linestyle="--")
            gl.top_labels = False
            gl.right_labels = False
            gl.xlabel_style = {"size": 7}
            gl.ylabel_style = {"size": 7}
            ax.tick_params(labelsize=7)
            ax.set_title(f"{name}", fontsize=8.5, pad=4)
            ax.text(0.97, 0.03, f"Mean: {wmean(fld, lats):.2f}", transform=ax.transAxes,
                    fontsize=7, ha="right", va="bottom",
                    bbox=dict(boxstyle="round,pad=0.25", facecolor="white", edgecolor="none", alpha=0.8))
            if c == 0:      # 每块只标一个指标编号：(a) Precip Var / (b) R95 Intensity
                ax.text(0.015, 1.02, f"({letters[r]})", transform=ax.transAxes,
                        fontsize=9, ha="left", va="bottom")

        # 块内色带：四套产品共用（跨 2 列）
        cb_y = y_bot - 0.72
        cax = fig.add_axes(R(lmar, cb_y, pw * 2 + pgx, cbar_h))
        cb = fig.colorbar(plt.cm.ScalarMappable(norm=norm, cmap=cmap_obj), cax=cax,
                          orientation="horizontal", extend="both", extendfrac=0.03, ticks=levels)
        cb.ax.xaxis.set_major_formatter(FuncFormatter(_fmt_tick))
        cb.ax.tick_params(labelsize=7)
        cb.set_label(f"{vlabel} ({unit})", fontsize=8)

        # ---- 统计：既写入 txt，也逐行落盘 CSV ----
        metric = METRIC_CSV[var]
        var_wmean = wmean(variance, lats)
        var_max = float(np.nanmax(variance))
        std_wmean = wmean(spread, lats)
        std_max = float(np.nanmax(spread))

        stats.append(f"[{vlabel}]  unit: {unit}")
        for (name, _), fld in zip(PRODUCTS, fields):
            m = wmean(fld, lats)
            stats.append(f"  {name:12s} 面积加权均值 = {m:8.3f}")
            csv_rows.append({
                "metric": metric,
                "unit": unit,
                "product": name,
                "mean_area_weighted": round(m, 6),
                "note": f"单套产品的气候态面积加权均值（w=cos(lat)，中国陆域，{PERIOD[0]}-{PERIOD[1]}）；"
                        f"分级 levels={levels.tolist()}",
            })
        stats.append(f"  {'产品间方差':12s} 面积加权均值 = {var_wmean:8.3f}"
                     f"   最大 = {var_max:.3f}   (mm/day)^2   [留档]")
        stats.append(f"  {'产品间标准差':12s} 面积加权均值 = {std_wmean:8.3f}"
                     f"   最大 = {std_max:.3f}   (mm/day)   [留档，不再出图]")
        stats.append(f"  levels = {levels.tolist()}")
        stats.append("")

        csv_rows.append({
            "metric": metric,
            "unit": "(mm/day)^2",
            "product": "PRODUCT_SPREAD_VARIANCE",
            "mean_area_weighted": round(var_wmean, 6),
            "note": f"四套产品逐格点方差（ddof=0）的面积加权均值；空间最大 = {var_max:.3f}；【留档，不再出图】",
        })
        csv_rows.append({
            "metric": metric,
            "unit": "mm/day",
            "product": "PRODUCT_SPREAD_STD",
            "mean_area_weighted": round(std_wmean, 6),
            "note": f"产品间标准差 σ（= 方差平方根，ddof=0）的面积加权均值；空间最大 = {std_max:.3f}；"
                    f"HEC 观测层在此基础上除以 sqrt(n) 得到观测误差项 σ_o（observational error term）；本图不再绘制该场",
        })

    fig.savefig(FIG_DIR / "Fig1.jpg", dpi=400, bbox_inches="tight")
    print(f"\n图形已保存至: {FIG_DIR / 'Fig1.jpg'}")

    hdr = [
        "图 1 统计数据 —— 四套格点降水产品（观测层）",
        "script  : src/Pic/Fig1_ObservedProducts/Fig1.py",
        f"period  : {PERIOD[0]}-{PERIOD[1]}（各产品取自身年份与该时段交集）",
        "weight  : 面积加权, w = cos(lat)",
        "note    : 只画四套观测产品本身（原第三列 σ 面板已于 2026-10-09 移除）；产品间标准差 σ（ddof=0，"
        "单位 mm/day）仍在下文统计中留档，HEC 观测层在其基础上除以 sqrt(n) 得观测误差项 σ_o",
        "",
    ]
    (DOC_DIR / "图1_统计数据.txt").write_text("\n".join(hdr + stats), encoding="utf-8")
    print(f"统计已保存至: {DOC_DIR / '图1_统计数据.txt'}")

    csv_path = DATA_DIR / "fig1_stats.csv"
    pd.DataFrame(csv_rows, columns=["metric", "unit", "product", "mean_area_weighted", "note"]).to_csv(
        csv_path, index=False, encoding="utf-8-sig")
    print(f"统计 CSV 已保存至: {csv_path}")


if __name__ == "__main__":
    main()
