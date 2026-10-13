from __future__ import annotations

import argparse
import contextlib
import os
import shutil
import tempfile
from pathlib import Path

import cartopy.crs as ccrs
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import pyproj
import shapefile
import xarray as xr
from matplotlib.colors import BoundaryNorm, ListedColormap, LinearSegmentedColormap
from matplotlib.lines import Line2D
from matplotlib.patches import Patch, Rectangle
from matplotlib.ticker import FuncFormatter
from PIL import Image
from scipy import ndimage
from shapely.geometry import mapping
from shapely.geometry import shape as shapely_shape
from shapely.ops import transform

plt.rcParams["font.family"] = ["Times New Roman", "DejaVu Sans"]   # 圈号 ①②… Times 缺字形，回退 DejaVu
plt.rcParams["mathtext.fontset"] = "cm"
plt.rcParams["axes.unicode_minus"] = False


ROOT = Path(__file__).resolve().parent          # src/Pic/Fig9_MountainAdjustment（脚本与图件同级）
DATA_DIR = ROOT / "data"                        # 山脉矢量与统计 CSV 的落盘目录
                                                # （8 张单面板 JPG 不再落盘：render_panels() 写入运行期临时目录）
OUT_JPG = ROOT / "Fig9.jpg"                     # 论文成品组图（原 compose_fig9.py 写作
                                                # REPO_ROOT/"src"/"Pic"/"Fig9_MountainAdjustment"/"Fig9.jpg"，与 ROOT 等价）
REPO_ROOT = next(p for p in Path(__file__).resolve().parents if (p / "src").is_dir() and (p / "Doc").is_dir())


DATA_ROOT = REPO_ROOT / "Data"
SHP_PATH = DATA_ROOT / "China" / "cnmap.shp"
MTN_PATH = DATA_DIR / "CN_MountainRanges_WGS84.shp"

# 山脉矢量重投影（一次性预处理，见 reproject_mountains_to_wgs84()）
# 注意：SRC_SHP 在当前仓库中已不存在，故该步骤默认不执行。
SRC_SHP = DATA_ROOT / "山脉走势数据" / "中国主要山脉【山脉数据】" / "CN_MountainRanges" / "CN_MountainRanges.shp"
MTN_OUT_DIR = DATA_DIR
MTN_OUT_SHP = MTN_OUT_DIR / "CN_MountainRanges_WGS84.shp"

SCENARIO = "ssp245"
DPI = 400
PROJ = ccrs.PlateCarree()
SCENARIOS = ("ssp126", "ssp245", "ssp585")


# 分区标号：直接采用对应子图的字母 (b)-(h)，(a) 图上的标注与左侧图例都用它
PANEL_LETTERS = "bcdefgh"
# 七大地理分区 (lon_min, lon_max, lat_min, lat_max)
REGIONS = [
    {"key": "NorthChina",      "label": "North China",       "mtn": "Taihang", "en": "Taihang Mountains",     "extent": [110, 118, 35, 42],  "color": "#E76254"},
    {"key": "Northeast",       "label": "Northeast",          "mtn": "Changbai", "en": "Changbai Mountain",    "extent": [118, 135, 38, 54],  "color": "#EF8A47"},
    {"key": "Northwest",       "label": "Northwest",          "mtn": "Tianshan", "en": "Tianshan Mountains",    "extent": [73, 105, 35, 50],   "color": "#FFD06F"},
    {"key": "Southwest",       "label": "Southwest",          "mtn": "Hengduan", "en": "Hengduan Mountains",    "extent": [95, 108, 21, 35],   "color": "#AADCE0"},
    {"key": "EastChina",       "label": "East China",         "mtn": "Wuyi", "en": "Wuyi Mountains",        "extent": [115, 123, 27, 35],  "color": "#72BCD5"},
    {"key": "SouthChina",      "label": "South China",        "mtn": "Wuzhi", "en": "Wuzhi Mountain",       "extent": [108, 120, 18, 26],  "color": "#528FAD"},
    {"key": "CentralChina",    "label": "Central China",      "mtn": "Wuling", "en": "Wuling Mountains",      "extent": [108, 115, 26, 34],  "color": "#376795"},
]

# 各区域推荐的 graticule 刻度
GRATICULES = {
    "NorthChina":      ([112, 114, 116, 118, 120], [36, 38, 40, 42]),
    "Northeast":       ([120, 125, 130, 135],       [40, 45, 50]),
    "Northwest":       ([75, 85, 95, 105],          [35, 40, 45, 50]),
    "Southwest":       ([98, 102, 106],             [22, 26, 30, 34]),
    "EastChina":       ([116, 118, 120, 122],       [28, 30, 32, 34]),
    "SouthChina":      ([108, 112, 116, 120],       [18, 20, 22, 24, 26]),
    "CentralChina":    ([108, 112, 116],            [26, 28, 30, 32, 34]),
}

# ---- 组图版式（原 compose_fig9.py）----
# 画布固定尺寸；面板锚点一律不动。
CANVAS = (2660, 1916)
# 原因：面板标题由「山名」改为「地区 + 山名」（如 (b) North China Taihang Mountains）后，
# 右侧 (b)(c) 的单行标题右缘实测到 2642 px，原 2525 px 画布会把末几字裁掉。
# 面板锚点一律不动——左移面板会压住 (a) 面板右下角的 "Bias>0" 标框（已实测），故只加宽画布。

# 作者原组图中各面板「地图框」的位置 (x0, y0, x1, y1)——由原图检测得到
TARGETS = {
    "Fig9a_China":    (823, 189, 1873, 801),
    "Fig9b_Taihang":  (2060, 726, 2492, 1029),
    "Fig9c_Changbai": (2102, 147, 2483, 505),
    "Fig9d_Tianshan": (130, 179, 562, 384),
    "Fig9e_Hengduan": (193, 635, 526, 993),
    "Fig9f_Wuyi":     (1913, 1469, 2272, 1827),
    "Fig9g_Wuzhi":    (425, 1473, 857, 1763),
    "Fig9h_Wuling":   (1212, 1451, 1570, 1809),
}


def _fmt_tick(v, _pos=None):
    """刻度标签：整数不带小数，非整数保留 1 位小数（全图统一口径）。"""
    return f"{v:.0f}" if abs(v - round(v)) < 1e-9 else f"{v:.1f}"


def _diverging_bounds(half, inner=(1.0, 6.0)):
    """以 0 为中心、近 0 密两端疏的分级边界，首尾恰为 ±half（实际极值）。"""
    pos = [v for v in inner if v < half] + [half]
    return np.array([-p for p in reversed(pos)] + pos)

def _load_mountain_geoms() -> list:
    """加载 WGS84 山脉数据，返回 (geom, length_m) 列表。长度使用测地线计算（米）。"""
    sf = shapefile.Reader(str(MTN_PATH))
    geod = pyproj.Geod(ellps="WGS84")
    result = []
    for i in range(len(sf.records())):
        geom = shapely_shape(sf.shape(i).__geo_interface__)
        # 计算几何的测地线长度（处理 LineString / MultiLineString / Polygon / MultiPolygon）
        length_m = 0.0
        geom_type = geom.geom_type
        if geom_type == "LineString":
            xs, ys = geom.xy
            if len(xs) >= 2:
                for a, b in zip(range(len(xs) - 1), range(1, len(xs))):
                    lon1, lat1 = xs[a], ys[a]
                    lon2, lat2 = xs[b], ys[b]
                    _, _, dist = geod.inv(lon1, lat1, lon2, lat2)
                    length_m += dist
        elif geom_type == "MultiLineString":
            for part in geom.geoms:
                xs, ys = part.xy
                for a, b in zip(range(len(xs) - 1), range(1, len(xs))):
                    lon1, lat1 = xs[a], ys[a]
                    lon2, lat2 = xs[b], ys[b]
                    _, _, dist = geod.inv(lon1, lat1, lon2, lat2)
                    length_m += dist
        elif geom_type == "Polygon":
            xs, ys = geom.exterior.xy
            for a, b in zip(range(len(xs) - 1), range(1, len(xs))):
                lon1, lat1 = xs[a], ys[a]
                lon2, lat2 = xs[b], ys[b]
                _, _, dist = geod.inv(lon1, lat1, lon2, lat2)
                length_m += dist
        elif geom_type == "MultiPolygon":
            for poly in geom.geoms:
                xs, ys = poly.exterior.xy
                for a, b in zip(range(len(xs) - 1), range(1, len(xs))):
                    lon1, lat1 = xs[a], ys[a]
                    lon2, lat2 = xs[b], ys[b]
                    _, _, dist = geod.inv(lon1, lat1, lon2, lat2)
                    length_m += dist
        else:
            try:
                length_m = geom.length
            except Exception:
                length_m = 0.0
        result.append((geom, float(length_m)))
    return result


def _filter_mountains_in_extent(mtn_list, extent):
    """筛选出质心落在 extent 内的山脉。输入为 (geom, length_m) 列表，返回同样结构的列表"""
    x0, x1, y0, y1 = extent
    out = []
    for geom, length_m in mtn_list:
        cx, cy = geom.centroid.x, geom.centroid.y
        if x0 <= cx <= x1 and y0 <= cy <= y1:
            out.append((geom, length_m))
    return out


def _draw_map(ax, extent, delta, mask, Lon, Lat_grid, bounds, colors,
              cn_geoms, title, xlocs, ylocs,
              mtn_geoms=None, add_rect=None, cmap=None, norm=None):
    ax.set_extent(extent, crs=PROJ)
    ax.contourf(Lon, Lat_grid, delta, levels=bounds,
                colors=colors, extend='both', transform=PROJ)
    if np.any(mask):
        ax.contourf(Lon, Lat_grid, mask.astype(float), levels=[0.5, 1.5],
                     colors=["grey"], alpha=0.55, transform=PROJ)
    ax.add_geometries(cn_geoms, crs=PROJ, facecolor='none',
                       edgecolor='black', linewidth=0.9)
    ax.set_title(title, fontsize=10, pad=6)
    ax.tick_params(labelsize=7)

    gl = ax.gridlines(draw_labels=True, linewidth=0.2, alpha=0.4, linestyle='--',
                       xlocs=xlocs, ylocs=ylocs)
    gl.top_labels = False
    gl.right_labels = False
    gl.xlabel_style = {"size": 7}
    gl.ylabel_style = {"size": 7}

    if add_rect:
        for r_ext, r_color in add_rect:
            rect = Rectangle(
                (r_ext[0], r_ext[2]),
                r_ext[1] - r_ext[0],
                r_ext[3] - r_ext[2],
                linewidth=1.5, edgecolor=r_color, facecolor="none", transform=PROJ, zorder=5
            )
            ax.add_patch(rect)

    if mtn_geoms:
        # mtn_geoms 为 (geom, length_m) 列表。按长度映射线宽：长度越大线越粗。
        lengths = [l for (_g, l) in mtn_geoms]
        min_len = min(lengths) if lengths else 0.0
        max_len = max(lengths) if lengths else 0.0
        min_w, max_w = 0.8, 3.0

        # 预计算一维 lon/lat 数组（假设 Lon, Lat_grid 为 meshgrid）
        try:
            lon_1d = Lon[0, :]
            lat_1d = Lat_grid[:, 0]
        except Exception:
            lon_1d = None
            lat_1d = None

        for geom, length_m in mtn_geoms:
            # 统一线宽为 1 磅（points）以满足要求
            lw = 1.0

            # 根据山体质心在 delta 网格上采样颜色
            edgecolor = "#8B7355"
            # 统一山脉颜色为用户指定的色值（更明显、风格一致）
            try:
                edgecolor = "#7e5b42"
            except Exception:
                edgecolor = "#7e5b42"

            ax.add_geometries([geom], crs=PROJ, linewidth=lw,
                               edgecolor=edgecolor, facecolor="none", alpha=0.9)

    return ax


def map_box(img: Image.Image, thr: int = 120):
    """检出面板图内的地图框：取「面积最大且填充率低（只有框线）」的暗色连通域。"""
    a = np.asarray(img.convert("L"))
    dark = a < thr
    lab, n = ndimage.label(dark)
    best = None
    for i, sl in enumerate(ndimage.find_objects(lab), 1):
        if sl is None:
            continue
        h = sl[0].stop - sl[0].start
        w = sl[1].stop - sl[1].start
        if w < 150 or h < 100:
            continue
        if (lab[sl] == i).sum() / (w * h) < 0.30 and (best is None or w * h > best[4]):
            best = (sl[1].start, sl[0].start, sl[1].stop, sl[0].stop, w * h)
    return best[:4] if best else None


def content_mask(im: Image.Image, thr: int = 250) -> Image.Image:
    """生成贴图掩膜：近白像素透明，只贴各面板的“实际内容”。

    背景：面板标题由「山名」改为「地区 + 山名」后，各面板 JPG 变宽，白边会盖住相邻
    面板的框线与标号（2026-10-11 实测：(b) 的白边压住 (a) 右侧框线 35 px、(d)/(e) 的
    白边压住 (a) 左缘 87/110 px）。实测这三处重叠区里被覆盖一侧的非白像素占 0.3%–10.9%，
    而覆盖一侧是纯白边（(b) 侧 0.0%），故把近白像素设为透明即可，内容一个不丢。
    """
    a = np.asarray(im.convert("L"))
    return Image.fromarray(np.where(a >= thr, 0, 255).astype(np.uint8), mode="L")


def reproject_mountains_to_wgs84() -> None:
    r"""
    一次性预处理：将山脉数据从 Albers 等面积投影重投影为 WGS84 (PlateCarree)
    输出保存到 src\Pic\Fig9_MountainAdjustment\data\
    （CN_MountainRanges_WGS84.shp / .shx / .dbf / .prj）

    ⚠ 本步骤默认**不执行**：源文件
    `Data/山脉走势数据/中国主要山脉【山脉数据】/CN_MountainRanges/CN_MountainRanges.shp`
    在当前仓库中已不存在，无法按原样重跑；`render_panels()` 实际消费的是 data/ 下已重投影好的
    派生文件，绘图流程不依赖源 shapefile。仅当重新拿到源 shapefile 时，才显式运行
    `python Fig9.py --reproject-mountains` 重建 data/ 下的山脉矢量。
    """
    MTN_OUT_DIR.mkdir(parents=True, exist_ok=True)

    # Albers Equal Area → WGS84
    src_crs = pyproj.CRS.from_wkt("""
PROJCS["CN_Albers_Equal_Area",
  GEOGCS["GCS_WGS_1984",
    DATUM["D_WGS_1984",SPHEROID["WGS_1984",6378137.0,298.257223563]],
    PRIMEM["Greenwich",0.0],UNIT["Degree",0.0174532925199433]],
  PROJECTION["Albers"],
  PARAMETER["False_Easting",0.0],PARAMETER["False_Northing",0.0],
  PARAMETER["Central_Meridian",105.0],
  PARAMETER["Standard_Parallel_1",30.0],PARAMETER["Standard_Parallel_2",40.0],
  PARAMETER["Latitude_Of_Origin",27.5],UNIT["Meter",1.0]]
""")
    dst_crs = pyproj.CRS.from_epsg(4326)  # WGS84

    transformer = pyproj.Transformer.from_crs(src_crs, dst_crs, always_xy=True)

    # 读取源文件
    sf = shapefile.Reader(str(SRC_SHP))
    records = sf.records()
    shapes = sf.shapes()
    fields = [f[0] for f in sf.fields if f[0] not in ("DeletionFlag",)]

    print(f"读取 {len(shapes)} 个要素，字段: {fields}")

    # 创建输出文件
    w = shapefile.Writer(str(MTN_OUT_SHP), shapeType=sf.shapeType)
    for fname in fields:
        field_info = [f for f in sf.fields if f[0] == fname][0]
        w.field(fname, field_info[1], size=field_info[2], decimal=field_info[3] if len(field_info) > 3 else 0)

    for i, (rec, shp) in enumerate(zip(records, shapes)):
        geom = shapely_shape(shp.__geo_interface__)
        geom_wgs84 = transform(transformer.transform, geom)
        w.record(*rec)
        w.shape(mapping(geom_wgs84))

    w.close()
    print(f"[DONE] 重投影完成: {MTN_OUT_SHP}")

    # 同时写入 .prj 文件
    prj_path = MTN_OUT_SHP.with_suffix(".prj")
    prj_path.write_text(dst_crs.to_wkt())
    print(f"[DONE] PRJ 文件: {prj_path}")


def render_panels(panel_dir: Path) -> None:
    """渲染 8 个面板 JPG（写入 panel_dir）与 data/fig9_stats.csv（原 Fig9.py 的 main()）。

    8 张单面板 JPG 只是拼合 `Fig9.jpg` 的**运行期中间产物**：panel_dir 由 main() 通过
    `_panel_temp_dir()` 提供（首选 tempfile.TemporaryDirectory()），运行结束即自动清理，
    模块根目录不再保留单面板。统计 CSV 是最终产物，仍落盘到模块 `data/` 下。
    """
    panel_dir.mkdir(parents=True, exist_ok=True)

    # ---- 中国边界 ----
    sf = shapefile.Reader(str(SHP_PATH))
    cn_geoms = [shapely_shape(s.__geo_interface__) for s in sf.shapes()]
    shp_bbox = sf.bbox
    china_extent = [float(shp_bbox[0]) - 1, float(shp_bbox[2]) + 1,
                    float(shp_bbox[1]) - 1, float(shp_bbox[3]) + 1]

    # ---- 全局色彩分级 ----
    HEC_DIR = REPO_ROOT / "Output" / "EC" / "China"   # 脚本 6 的规范输出（2021-2050）
    all_delta = []
    for s in SCENARIOS:
        with xr.open_dataset(HEC_DIR / f"HEC_{s}_PrecipVar_to_R95mm_intensity.nc") as ds:
            d = ds["posterior_mean"].values - ds["prior_mean"].values
            all_delta.append(d.ravel())
    all_delta = np.concatenate(all_delta)
    all_valid = all_delta[np.isfinite(all_delta)]
    global_min = float(all_valid.min()) if len(all_valid) > 0 else -1.0
    global_max = float(all_valid.max()) if len(all_valid) > 0 else 1.0


    DELTA_ANCHORS = ["#315484", "#84B0D3", "#E7F2F6", "#F58A58", "#992323"]

    if global_min < -1 and global_max > 1:
        half = max(abs(global_min), abs(global_max))
        bounds = list(_diverging_bounds(half))
        _cont = LinearSegmentedColormap.from_list("delta_cont", DELTA_ANCHORS)
        colors = [_cont(_t) for _t in np.linspace(0, 1, len(bounds) - 1)]
    else:
        bounds = list(np.linspace(global_min, global_max, 12))
        colors = DELTA_ANCHORS
    cmap = ListedColormap(colors)
    norm = BoundaryNorm(bounds, cmap.N, clip=True)

    # ---- 读取 SSP2-4.5 数据 ----
    nc_path = HEC_DIR / f"HEC_{SCENARIO}_PrecipVar_to_R95mm_intensity.nc"
    with xr.open_dataset(nc_path) as ds:
        ds = ds.load()
    posterior = ds["posterior_mean"].values
    prior = ds["prior_mean"].values
    p_map = ds["p_value"].values
    lon = ds["lon"].values.astype(np.float64)
    lat = ds["lat"].values.astype(np.float64)
    delta = posterior - prior
    Lon, Lat_grid = np.meshgrid(lon, lat)

    mask = np.isfinite(p_map) & (p_map >= 0.05)

    # ---- 预加载山脉几何 ----
    all_mountains = _load_mountain_geoms()
    per_region_mountains = {}
    for reg in REGIONS:
        per_region_mountains[reg["key"]] = _filter_mountains_in_extent(
            all_mountains, reg["extent"]
        )

    # ================================================================
    # Fig9a: 全中国（红框标注七大区域）
    # ================================================================

    rects = [(reg["extent"], reg["color"]) for reg in REGIONS]

    # 大图宽度设置为 10 cm -> 转换为英寸
    big_width_in = 10.0 / 2.54
    # 保持原始宽高比 (6.2 / 7)
    big_height_in = big_width_in * (6.2 / 7.0)
    fig_a = plt.figure(figsize=(big_width_in, big_height_in), dpi=DPI)
    fig_a.subplots_adjust(bottom=0.14)
    ax_a = fig_a.add_subplot(1, 1, 1, projection=PROJ)
    _draw_map(ax_a, china_extent, delta, mask, Lon, Lat_grid, bounds, colors,
              cn_geoms, "SSP2-4.5  Adjustment = Posterior − Prior",
              xlocs=[70, 90, 110, 130], ylocs=[20, 30, 40, 50],
              add_rect=rects, cmap=cmap, norm=norm)
    # 每个分区框中心标注圈号（与图例中的「① 山名」对应）
    for _i, _reg in enumerate(REGIONS):
        _lon0, _lon1, _lat0, _lat1 = _reg["extent"]
        ax_a.text((_lon0 + _lon1) / 2, (_lat0 + _lat1) / 2, f"({PANEL_LETTERS[_i]})",
                  transform=PROJ, fontsize=9, ha="center", va="center", zorder=6,
                  bbox=dict(boxstyle="round,pad=0.10", facecolor="white",
                            edgecolor="none", alpha=0.75))


    _v = np.isfinite(delta)
    _pos = (delta > 0) & _v
    _pos_pct = float(_pos.sum() / _v.sum() * 100) if _v.sum() > 0 else 0.0
    ax_a.text(0.97, 0.12,
              f"Adjustment>0: {_pos_pct:.1f}%",
              transform=ax_a.transAxes, fontsize=7, ha="right", va="bottom",
              bbox=dict(boxstyle="round,pad=0.3", facecolor="white", edgecolor="gray", alpha=0.8))
    fig_a.text(0.01, 0.99, "(a)", transform=fig_a.transFigure, fontsize=10,
               va="top", ha="left", bbox=dict(boxstyle="round,pad=0.15", facecolor="white", edgecolor="none", alpha=0.7))


    legend_handles = [Line2D([], [], linestyle="none",
                             label=f"({PANEL_LETTERS[i]}) {reg['label']} {reg['en']}")
                       for i, reg in enumerate(REGIONS)]
    leg = ax_a.legend(handles=legend_handles, loc="lower left", fontsize=5,
                       framealpha=0.85, edgecolor="gray", ncol=1,
                       handlelength=0, handletextpad=0.2,
                       bbox_to_anchor=(0.005, 0.015))
    leg.get_frame().set_linewidth(0.3)

    # 水平色带（底部）
    cax = fig_a.add_axes((0.12, 0.06, 0.76, 0.025))
    sm = plt.cm.ScalarMappable(norm=norm, cmap=cmap)
    sm.set_array([])
    # 显示关键标注：负端、-1、1、正端，参考 Fig7c.py 的格式化方式
    show_ticks = sorted(set([bounds[0], -1.0, 1.0, bounds[-1]])
                      | {b for b in list(bounds)[1:-1] if abs(b) in (6.0, 16.0)})
    cb = fig_a.colorbar(sm, cax=cax, orientation="horizontal",
                        extend='both', extendfrac=0.04, ticks=show_ticks)
    cb.ax.xaxis.set_major_formatter(FuncFormatter(_fmt_tick))
    cb.ax.tick_params(labelsize=7)
    cb.set_label("Adjustment (mm/day)", fontsize=8)

    fig_a.savefig(panel_dir / "Fig9a_China.jpg", dpi=DPI, bbox_inches="tight")   # 临时面板，供组图使用
    plt.close(fig_a)
    print(f"[DONE] Fig9a_China.jpg")


    fig9_stats = []
    letters = "bcdefgh"
    for reg, letter in zip(REGIONS, letters):
        ext = reg["extent"]
        key = reg["key"]
        xlocs, ylocs = GRATICULES[key]
        mtn_geoms = per_region_mountains[key]

        # 小图宽度设置为 4 cm -> 转换为英寸
        small_width_in = 4.0 / 2.54
        # 保持原始宽高比 (5 / 6)
        small_height_in = small_width_in * (5.0 / 6.0)
        fig = plt.figure(figsize=(small_width_in, small_height_in), dpi=DPI)
        ax = fig.add_subplot(1, 1, 1, projection=PROJ)
        _draw_map(ax, ext, delta, mask, Lon, Lat_grid, bounds, colors,
              cn_geoms, f"({letter}) {reg['label']} {reg['en']}",   # 标号 + 地区 + 山名
              xlocs=xlocs, ylocs=ylocs,
              mtn_geoms=mtn_geoms, cmap=cmap, norm=norm)

        mtn_name = reg["mtn"]
        out_name = panel_dir / f"Fig9{letter}_{mtn_name}.jpg"
        fig.savefig(out_name, dpi=DPI, bbox_inches="tight")   # 供组图使用
        plt.close(fig)
        print(f"[DONE] Fig9{letter}_{mtn_name}.jpg")


        _ext = reg["extent"]
        _rm = ((Lon >= _ext[0]) & (Lon <= _ext[1]) & (Lat_grid >= _ext[2]) & (Lat_grid <= _ext[3]))
        _dv = delta[_rm & np.isfinite(delta)]
        _dw = np.broadcast_to(np.cos(np.deg2rad(lat))[:, None], Lat_grid.shape)[_rm & np.isfinite(delta)]
        _mean_w = float(np.nansum(_dv * _dw) / _dw.sum()) if _dw.size and _dw.sum() > 0 else float("nan")
        _pct_pos = float((_dv > 0).sum() / _dv.size * 100) if _dv.size else float("nan")
        fig9_stats.append({"panel": letter, "region_key": key, "region_en": reg["en"], "mtn": mtn_name,
                           "n_grid": int(_dv.size), "mean_area_weighted": _mean_w,
                           "vmin": float(_dv.min()) if _dv.size else float("nan"),
                           "vmax": float(_dv.max()) if _dv.size else float("nan"),
                           "pct_bias_positive": _pct_pos})


    _sp = DATA_DIR / "fig9_stats.csv"
    _sp.parent.mkdir(parents=True, exist_ok=True)
    pd.DataFrame(fig9_stats).to_csv(_sp, index=False, encoding="utf-8-sig")
    print(f"[DONE] 统计数据: {_sp}")


def compose_fig9(panel_dir: Path) -> None:
    """把 8 个面板按作者原版式拼合为 Fig9.jpg（原 compose_fig9.py 的 main()）。

    以「各面板在原图中的地图框」为锚点，把新渲染的面板按宽度缩放后精确对位粘贴；
    面板从 panel_dir（render_panels() 写入的临时目录）读取，必须先渲染再调用。
    只有成品 `Fig9.jpg` 落盘到模块根目录。
    """
    det, scales = {}, {}
    for name in TARGETS:
        im = Image.open(panel_dir / f"{name}.jpg").convert("RGB")
        mb = map_box(im)
        det[name] = (im, mb)
        if mb:
            tx0, _ty0, tx1, _ty1 = TARGETS[name]
            scales[name] = (tx1 - tx0) / (mb[2] - mb[0])
    med = float(np.median(list(scales.values()))) if scales else 1.0

    canvas = Image.new("RGB", CANVAS, "white")
    for name, (tx0, ty0, tx1, ty1) in TARGETS.items():
        im, mb = det[name]
        if mb:
            mx0, my0, _mx1, _my1 = mb
            s = scales[name]
            im2 = im.resize((round(im.width * s), round(im.height * s)), Image.LANCZOS)
            canvas.paste(im2, (round(tx0 - mx0 * s), round(ty0 - my0 * s)), content_mask(im2))
            print(f"  {name:14s} 精确对位  缩放 {s:.3f}")
        else:                                    # 框线检测失败：按其余面板的中位缩放居中放置
            s = med
            im2 = im.resize((round(im.width * s), round(im.height * s)), Image.LANCZOS)
            canvas.paste(im2, (round((tx0 + tx1) / 2 - im2.width / 2),
                               round((ty0 + ty1) / 2 - im2.height / 2)), content_mask(im2))
            print(f"  {name:14s} 中位缩放居中  缩放 {s:.3f}")

    # PIL 保存不会自动带 DPI 元数据，这里显式写入（与各面板的 400 dpi 一致）
    canvas.save(OUT_JPG, dpi=(400, 400))
    print(f"  已写 {OUT_JPG}  {canvas.size}")


def _dir_writable(path: Path) -> bool:
    """实测目录能否写入（Windows 上 os.access 不反映真实权限，必须真写一个探针文件）。"""
    probe = path / ".fig9_write_probe"
    try:
        probe.write_bytes(b"")
        probe.unlink()
        return True
    except OSError:
        return False


@contextlib.contextmanager
def _panel_temp_dir():
    """提供存放 8 张单面板 JPG 的临时目录，退出时自动清理（模块根目录不留任何面板）。

    首选 `tempfile.TemporaryDirectory()`：正常环境下面板写在该目录里，`with` 退出即删除。
    个别受限环境（例如带文件沙箱的 Windows 会话）会拒绝写入 tempfile 以 0o700 私有权限
    新建的目录，甚至连它的清理也会被拒——此时退回系统临时根下用 `os.makedirs` 自建的同类
    目录，并在 finally 中删除。两条路径都只写系统临时区，绝不写模块目录。
    """
    _cm, _tmp, _usable = None, None, False
    try:
        _cm = tempfile.TemporaryDirectory(prefix="fig9_panels_", ignore_cleanup_errors=True)
        _tmp = Path(_cm.__enter__())
        _usable = _dir_writable(_tmp)
    except OSError:                      # 受限环境：建不出/进不去私有目录
        _cm, _tmp, _usable = None, None, False

    if _usable:
        try:
            yield _tmp
        finally:
            with contextlib.suppress(OSError):     # 清理失败也不影响主流程
                _cm.__exit__(None, None, None)
        return

    if _cm is not None:                  # 建了却不可写：尽力清掉，清不掉也不阻断流程
        with contextlib.suppress(OSError):
            _cm.__exit__(None, None, None)

    _fallback = Path(tempfile.gettempdir()) / f"fig9_panels_{os.getpid()}_{os.urandom(4).hex()}"
    _fallback.mkdir(parents=True, exist_ok=False)
    try:
        yield _fallback
    finally:
        shutil.rmtree(_fallback, ignore_errors=True)


def main(reproject_mountains: bool = False) -> None:
    """单文件主流程：渲染 8 个面板（临时目录）+ 统计 CSV，再拼合论文组图 Fig9.jpg。

    默认（reproject_mountains=False）先在 `_panel_temp_dir()`（首选
    `tempfile.TemporaryDirectory()`，受限环境见该函数的回退说明）里执行
    `render_panels(panel_dir)`，随即 `compose_fig9(panel_dir)` 拼合，一次运行复现
    `Fig9.jpg` 与 `data/fig9_stats.csv`；8 张单面板随临时目录自动清理，不落盘。

    reproject_mountains=True（命令行 `--reproject-mountains`）时只执行山脉矢量重投影这一次性
    预处理步骤后返回，不进入绘图流程——源 shapefile 已缺失，该分支默认不会被触发，
    详见 `reproject_mountains_to_wgs84()`。
    """
    if reproject_mountains:
        reproject_mountains_to_wgs84()
        return
    # 8 张单面板是运行期中间产物：写入临时目录，with 块退出（含异常）时自动清理，
    # 模块根目录只会留下最终产物 Fig9.jpg 与 data/fig9_stats.csv。
    with _panel_temp_dir() as panel_dir:
        render_panels(panel_dir)   # 必须先渲染面板……
        compose_fig9(panel_dir)    # ……再拼合组图（从同一个临时目录读取面板）


if __name__ == "__main__":
    _ap = argparse.ArgumentParser(
        description="Fig.9 山脉分区调整场：渲染 8 个面板并拼合为 Fig9.jpg（单文件版）")
    _ap.add_argument("--reproject-mountains", action="store_true",
                     help="一次性预处理：把山脉矢量从 Albers 等面积投影重投影为 WGS84"
                          "（源 shapefile 已缺失，默认不执行）")
    _args = _ap.parse_args()
    main(reproject_mountains=_args.reproject_mountains)
