import time
import zipfile
from pathlib import Path

import matplotlib.pyplot as plt
import cartopy.crs as ccrs
import shapefile
from shapely.geometry import shape as shapely_shape, Point
from shapely.ops import unary_union
import numpy as np
import pandas as pd
from matplotlib.lines import Line2D
from mpl_toolkits.axes_grid1.inset_locator import inset_axes

plt.rcParams["font.family"] = "Times New Roman"
plt.rcParams["mathtext.fontset"] = "cm"
plt.rcParams["axes.unicode_minus"] = False

ROOT = Path(__file__).resolve().parent
REPO_ROOT = next(p for p in Path(__file__).resolve().parents if (p / "src").is_dir())


DATA_ROOT = Path(__file__).resolve().parent / "data" / "geography"
SHP_PATH = DATA_ROOT / "China" / "cnmap.shp"
OUTPUT_DIR = ROOT
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

# 本模块的唯一数据文件（统计步骤写出、绘图步骤读取）
CSV_PATH = ROOT / "data" / "fig4_regional_stats.csv"

# ============================================================
# 区域定义
# ============================================================
# 标准七大地理分区（范围与 Fig7/Fig8/Fig9 完全一致，互不重叠）
REGIONS = [
    ("NorthChina", 35, 42, 110, 118),
    ("Northeast", 38, 54, 118, 135),
    ("Northwest", 35, 50, 73, 105),
    ("Southwest", 21, 35, 95, 108),
    ("EastChina", 27, 35, 115, 123),
    ("SouthChina", 18, 26, 108, 120),
    ("CentralChina", 26, 34, 108, 115),
]

# 中国全域参考行（不掩膜）：只参与统计，并在柱状图中置于最左侧
CHINA_REGION = ("China", -90, 90, -180, 360)

REGION_LABELS = {
    "NorthChina": "North China",
    "Northeast": "Northeast",
    "Northwest": "Northwest",
    "Southwest": "Southwest",
    "EastChina": "East China",
    "SouthChina": "South China",
    "CentralChina": "Central China",
    "YellowRiver": "Yellow River Basin",
    "YangtzeRiver": "Yangtze Basin",
    "PearlRiver": "Pearl Basin",
}

# 情景：SCENARIO_KEYS 为 Fig3 npz 中的变量前缀，SCENARIOS 为论文中的显示名
SCENARIO_KEYS = ["ssp126", "ssp245", "ssp585"]
SCENARIOS = ["SSP1-2.6", "SSP2-4.5", "SSP5-8.5"]
SCENARIO_COLORS = ["#4C9AC9", "#F3A161", "#D64736"]

# ============================================================
# 河流流域多边形定义（统计步骤构建格点掩膜，绘图步骤画边界）
# ============================================================
river_dir = DATA_ROOT / "River"
# 注意：第一个多边形文件名仍是 HuanghaiRiver_polygon.shp，但其范围
# （95.88-119.88E, 32.38-42.62N）为黄河流域，故显示名统一为 Yellow River。
RIVER_FILES = [
    ("YellowRiver", river_dir / "HuanghaiRiver_polygon.shp"),
    ("PearlRiver", river_dir / "PearlRiver_polygon.shp"),
    ("YangtzeRiver", river_dir / "YangtzeRiver_polygon.shp"),
]
RIVER_COLORS = {"YellowRiver": "#1f77b4", "PearlRiver": "#d62728", "YangtzeRiver": "#2ca02c"}

# ============================================================
# 上游输入（只读）：兄弟模块 Fig3 的 npz
# ============================================================
FIG3_DATA_DIR = ROOT / "data"
FIG3_NPZ = FIG3_DATA_DIR / "fig3_data.npz"
# 本模块只用 lon/lat 与各情景的 _mean/_std（同文件中的 *_var 未使用）
FIG3_KEYS = ["lon", "lat"] + [f"{s}_{stat}" for s in SCENARIO_KEYS for stat in ("mean", "std")]


def load_fig3_data(attempts=3, delay=2.0):
    """
    只读加载上游 fig3_data.npz，并把所需变量一次性读入内存。

    该文件由 Fig3 的 fig3data.py 生成，本模块**只读不写**；上游若正在重新生成，
    读取可能瞬时失败，故失败时重试 attempts 次（每次间隔 delay 秒）后再抛错。
    一次性 materialize 也保证不会在后续计算中被半截文件影响。
    """
    last_err = None
    for attempt in range(1, attempts + 1):
        try:
            with np.load(FIG3_NPZ) as npz:
                return {k: np.array(npz[k]) for k in FIG3_KEYS}
        except (OSError, EOFError, ValueError, zipfile.BadZipFile) as err:
            last_err = err
            if attempt < attempts:
                print(f"  读取 {FIG3_NPZ.name} 失败（第 {attempt}/{attempts} 次）: {err}，{delay:g}s 后重试")
                time.sleep(delay)
    raise RuntimeError(f"无法读取上游输入 {FIG3_NPZ}（已重试 {attempts} 次）") from last_err


# ============================================================
# 工具函数：为河流流域构建格点掩膜
# ============================================================
def build_river_mask(shp_path, lon_2d, lat_2d):
    """返回与 lon_2d 同形状的 bool 掩膜，标记落入河流多边形内的格点"""
    rsf = shapefile.Reader(str(shp_path))
    polys = [shapely_shape(s.__geo_interface__) for s in rsf.shapes()]


    merged = unary_union(polys)

    # 仅检查多边形边界框内的格点
    minx, miny, maxx, maxy = merged.bounds
    pre_mask = (lon_2d >= minx) & (lon_2d <= maxx) & \
               (lat_2d >= miny) & (lat_2d <= maxy)

    mask = np.zeros(lon_2d.shape, dtype=bool)
    # 对预筛选内的格点做精确点包含判断
    candidates = np.where(pre_mask)
    for i, j in zip(*candidates):
        if merged.contains(Point(lon_2d[i, j], lat_2d[i, j])):
            mask[i, j] = True

    return mask


def area_weighted_stats(mask, mean_field, std_field, weights):
    """
    对掩膜内的**有限值**格点做 cos(纬度) 面积加权平均（均值场与 σ 场各自用
    自己的有限值掩膜），返回 (加权均值, 加权 σ, 加权方差)。
    """
    m_valid = mask & np.isfinite(mean_field)
    s_valid = mask & np.isfinite(std_field)

    w_mean = np.nansum(mean_field * weights * m_valid) / np.nansum(weights * m_valid)
    w_std  = np.nansum(std_field  * weights * s_valid) / np.nansum(weights * s_valid)
    w_var  = np.nansum(std_field**2 * weights * s_valid) / np.nansum(weights * s_valid)

    return float(w_mean), float(w_std), float(w_var)


# ============================================================
# 第 1 步：区域统计（原 calc_regional_stats.py）
# ============================================================
def compute_regional_stats():
    """
    计算各子区域面积加权平均的极端降水强度（R95 Intensity）
    及其模式间标准差，结果保存为 CSV（3 情景 × 11 区域 = 33 行）。
    """
    data = load_fig3_data()

    lon = data['lon']
    lat = data['lat']
    lon_2d, lat_2d = np.meshgrid(lon, lat)

    weights = np.cos(np.deg2rad(lat))[:, np.newaxis]  # (lat, 1)

    # 预加载所有河流流域掩膜
    river_masks = {}
    for rname, rfp in RIVER_FILES:
        if rfp.exists():
            river_masks[rname] = build_river_mask(rfp, lon_2d, lat_2d)
            print(f'  加载河流流域 {rname}: {river_masks[rname].sum()} 个格点')

    results = []
    for s, slab in zip(SCENARIO_KEYS, SCENARIOS):
        mean_field = data[f'{s}_mean']
        std_field  = data[f'{s}_std']

        # --- 8 个子区域（经纬度框；首个 China 为全域参考行，不掩膜） ---
        for rname, lat_min, lat_max, lon_min, lon_max in [CHINA_REGION] + REGIONS:
            mask = (lat_2d >= lat_min) & (lat_2d <= lat_max) & \
                   (lon_2d >= lon_min) & (lon_2d <= lon_max)

            w_mean, w_std, w_var = area_weighted_stats(mask, mean_field, std_field, weights)

            results.append({
                'Scenario': slab,
                'Region': rname,
                'Weighted_Mean_Intensity': round(w_mean, 3),
                'Weighted_Std': round(w_std, 3),
                'Weighted_Variance': round(w_var, 3),
            })
            print(f'{slab:12s} | {rname:20s} | Mean={w_mean:7.3f} | Std={w_std:7.3f} | Var={w_var:7.3f}')

        # --- 3 个河流流域（多边形精确掩膜） ---
        for rname, mask in river_masks.items():
            w_mean, w_std, w_var = area_weighted_stats(mask, mean_field, std_field, weights)

            results.append({
                'Scenario': slab,
                'Region': rname,
                'Weighted_Mean_Intensity': round(w_mean, 3),
                'Weighted_Std': round(w_std, 3),
                'Weighted_Variance': round(w_var, 3),
            })
            print(f'{slab:12s} | {rname:20s} | Mean={w_mean:7.3f} | Std={w_std:7.3f} | Var={w_var:7.3f}')

    # ---- 保存 CSV ----
    df = pd.DataFrame(results)
    CSV_PATH.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(CSV_PATH, index=False, encoding='utf-8-sig')
    print(f'\n结果已保存至: {CSV_PATH}')
    print(f'共 {len(results)} 行（{len(SCENARIO_KEYS)} 个情景 × '
          f'{len(REGIONS) + 1 + len(river_masks)} 个区域）')
    return df


# ============================================================
# 第 2 步：绘图（原 Fig4.py）
# ============================================================
def plot_figure():
    """读取统计 CSV 与仓库矢量，绘制 (a) 区划图 + (b) 区域统计柱状图并保存 Fig4.jpg"""
    # ============================================================
    # 加载中国国界
    # ============================================================
    print("加载中国国界矢量...")
    sf = shapefile.Reader(str(SHP_PATH))
    cn_geoms = [shapely_shape(s.__geo_interface__) for s in sf.shapes()]
    shp_bbox = sf.bbox
    extent = [float(shp_bbox[0]) - 1, float(shp_bbox[2]) + 1,
              float(shp_bbox[1]) - 1, float(shp_bbox[3]) + 1]

    # ============================================================
    # 加载河流流域
    # ============================================================
    river_geoms = {}
    for rname, rfp in RIVER_FILES:
        if rfp.exists():
            rsf = shapefile.Reader(str(rfp))
            geoms = [shapely_shape(s.__geo_interface__) for s in rsf.shapes()]
            river_geoms[rname] = geoms
            print(f"  加载 {rname}: {len(geoms)} 个多边形")

    # ============================================================
    # 加载区域统计数据
    # ============================================================
    if CSV_PATH.exists():
        df = pd.read_csv(CSV_PATH)
        print(f"加载统计数据: {CSV_PATH}")
    else:
        print(f"未找到统计文件 {CSV_PATH}，请先运行本文件的 compute_regional_stats()")
        df = None

    # ============================================================
    # 绘图
    # ============================================================
    fig_w_cm, fig_h_cm = 12, 16
    fig = plt.figure(figsize=(fig_w_cm / 2.54, fig_h_cm / 2.54))


    def R(l, b, w, h):
        return (l / fig_w_cm, b / fig_h_cm, w / fig_w_cm, h / fig_h_cm)


    # ==================== (a) 地图 ====================
    proj = ccrs.PlateCarree()
    ax_map = fig.add_axes(R(0.6, 9.0, 11.2, 9), projection=proj)
    ax_map.set_extent(extent, crs=proj)

    ax_map.add_geometries(cn_geoms, crs=ccrs.PlateCarree(), facecolor="none",
                          edgecolor="black", linewidth=0.8)

    gl = ax_map.gridlines(draw_labels=True, linewidth=0.2, alpha=0.4, linestyle="--",
                          xlocs=[80, 90, 110, 130], ylocs=[10, 20, 30, 40, 50])
    gl.top_labels = False
    gl.right_labels = False
    gl.xlabel_style = {"size": 12}
    gl.ylabel_style = {"size": 12}

    # 绘制河流流域
    for rname, geoms in river_geoms.items():
        ax_map.add_geometries(geoms, crs=ccrs.PlateCarree(), facecolor="none",
                              edgecolor=RIVER_COLORS.get(rname, "blue"), linewidth=1.2)

    # 绘制子区域框 + 标注
    colors = plt.cm.Set2(np.linspace(0, 1, len(REGIONS)))
    region_handles = []
    river_handles = []

    for (rname, lat_min, lat_max, lon_min, lon_max), color in zip(REGIONS, colors):
        xs = [lon_min, lon_max, lon_max, lon_min, lon_min]
        ys = [lat_min, lat_min, lat_max, lat_max, lat_min]
        line = ax_map.plot(xs, ys, transform=ccrs.PlateCarree(), color=color, linewidth=1.5, label=rname)[0]
        region_handles.append(line)
        # 区域名称不在图面标注（框多且相邻，文字易拥挤），由左下角图例按颜色对应

    # 河流流域图例句柄
    for rname in RIVER_COLORS:
        river_handles.append(Line2D([], [], color=RIVER_COLORS[rname], linewidth=1.2,
                                    label=REGION_LABELS.get(rname, rname)))

    all_handles = region_handles + river_handles
    ax_map.legend(handles=all_handles, fontsize=7, loc="lower left", ncol=2,
                  framealpha=0.8)

    # (a) 标签
    pos_map = ax_map.get_position()
    fig.text(pos_map.x0 - 0.02, pos_map.y1 + 0.02, "(a)",
             fontsize=18, ha="right", va="bottom", fontweight="normal")

    # ==================== (b) 柱状图 ====================
    ax_bar = fig.add_axes(R(0.6, 0.8, 11.2, 6.5))

    if df is not None:
        # 选子区域（排除 China 全境）
        # 柱状图区域：中国全域作参考 + 七大地理分区 + 三大流域（行序与图 5 热力图一致）
        plot_regions = ["China"] + [r[0] for r in REGIONS] + list(RIVER_COLORS.keys())
        plot_labels = [REGION_LABELS.get(r, r) for r in plot_regions]

        x = np.arange(len(plot_regions))
        n_scenarios = len(SCENARIOS)
        bar_w = 0.22
        offsets = np.linspace(-bar_w, bar_w, n_scenarios)

        region_top = {}   # 各区域组的最高点（均值+误差棒），供子图锚点与水平箭头定位
        for i, scenario in enumerate(SCENARIOS):
            means = []
            stds = []
            for region in plot_regions:
                row = df[(df["Scenario"] == scenario) & (df["Region"] == region)]
                if not row.empty:
                    means.append(row["Weighted_Mean_Intensity"].values[0])
                    stds.append(row["Weighted_Std"].values[0])
                else:
                    means.append(0)
                    stds.append(0)
            for _k, (_m, _s) in enumerate(zip(means, stds)):
                region_top[_k] = max(region_top.get(_k, 0.0), float(_m) + float(_s))

            bars = ax_bar.bar(x + offsets[i], means, bar_w, yerr=stds,
                              color=SCENARIO_COLORS[i], edgecolor="black", linewidth=0.3,
                              capsize=2, label=scenario, alpha=0.9)

        ax_bar.set_xticks(x)
        ax_bar.set_xticklabels(plot_labels, rotation=30, ha="right", fontsize=11)
        ax_bar.set_ylabel("R95 Intensity (mm/day);\nerror bar = inter-model σ (mm/day)", fontsize=10)
        ax_bar.legend(fontsize=11, framealpha=0.8, ncol=3, loc="lower left",
                    bbox_to_anchor=(0.0, 1.01))   # 置于坐标区上方，避免遮挡高柱与误差棒
        ax_bar.set_ylim(0, 70)   # 误差棒为模式间 σ，上限按 σ 量级设置
        ax_bar.grid(axis="y", linestyle="--", alpha=0.3, linewidth=0.3)
        ax_bar.tick_params(labelsize=11)

        # ---- 华南地区放大子图 ----
        south_idx = plot_regions.index("SouthChina")
        sc_x = x[south_idx]
        sc_mean = []
        sc_std = []
        for scenario in SCENARIOS:
            row = df[(df["Scenario"] == scenario) & (df["Region"] == "SouthChina")]
            if not row.empty:
                sc_mean.append(row["Weighted_Mean_Intensity"].values[0])
                sc_std.append(row["Weighted_Std"].values[0])
            else:
                sc_mean.append(0)
                sc_std.append(0)

        # 嵌入子图（左上空白区）：x 锚点留出子图 y 轴刻度标签宽度（否则压主图刻度数字）；
        # y 锚点取「子图与华南柱之间最高柱（含误差棒）+ 0.8」之上，使水平箭头不穿柱。
        _ylim_top = ax_bar.get_ylim()[1]
        _axw_in = ax_bar.get_position().width * fig.get_figwidth()
        _axh_in = ax_bar.get_position().height * fig.get_figheight()
        _INSET_W_IN, _INSET_H_IN = 1.3, 0.55   # 子图固定尺寸（英寸）
        _inset_x = 0.14
        _inset_right_data = float(ax_bar.transData.inverted().transform(
            ax_bar.transAxes.transform((_inset_x + _INSET_W_IN / _axw_in, 0.0)))[0])
        _x_south_left = south_idx - bar_w * 1.5
        _barrier = max([v for k, v in region_top.items()
                        if _inset_right_data <= k <= _x_south_left] or [0.0])
        # 水平箭头高度：须高于区间内最高柱（否则穿过柱子）
        _arrow_y = _barrier + 0.6
        # 子图底边相对箭头「下沉」的量（mm/day）：只调这一个数即可控制子图高低
        _inset_sink = 5.0
        _h_frac = _INSET_H_IN / _axh_in
        INSET_ANCHOR = (_inset_x, (_arrow_y - _inset_sink) / _ylim_top)
        inset_ax = inset_axes(ax_bar, width=_INSET_W_IN, height=_INSET_H_IN,
                              bbox_to_anchor=INSET_ANCHOR,
                              bbox_transform=ax_bar.transAxes,
                              loc="lower left", borderpad=0)
        print(f"  子图锚点=({INSET_ANCHOR[0]:.2f}, {INSET_ANCHOR[1]:.3f})  高={_INSET_H_IN:.2f} in  "
              f"箭头 y={_arrow_y:.2f}（最高柱+误差棒={_barrier:.2f}）  子图底边 y={_arrow_y - _inset_sink:.2f}")

        x_inset = np.arange(n_scenarios)
        inset_ax.bar(x_inset, sc_mean, bar_w * 1.8,
                     color=SCENARIO_COLORS, edgecolor="black", linewidth=0.5,
                     alpha=0.9)
        inset_ax.set_xticks([])
        inset_ax.tick_params(labelsize=9)
        # y 轴范围由华南三情景数值推出：此前写死 49.9-50.6，华南数值改为约 49.1 后
        # 柱子落到范围之外，子图变成空框，故改为数据驱动并留 35% 边距突出差异
        _lo, _hi = min(sc_mean), max(sc_mean)
        _pad = max(0.02, (_hi - _lo) * 0.35)
        inset_ax.set_ylim(_lo - _pad, _hi + _pad)
        inset_ax.set_xlabel("South China", fontsize=9)   # 差异量已写入图注，图上不再叠标
        print(f"  华南子图 y 轴: {_lo - _pad:.3f} ~ {_hi + _pad:.3f}  (三情景 {_lo:.3f}~{_hi:.3f}, 极差 {_hi - _lo:.3f})")

        # 从华南柱组左缘「水平」指向嵌入子图右上角：两者等高，故不穿柱
        _inset_right = INSET_ANCHOR[0] + _INSET_W_IN / _axw_in
        x_end, y_end = ax_bar.transData.inverted().transform(
            ax_bar.transAxes.transform((_inset_right, _arrow_y / _ylim_top)))
        x_start = _x_south_left                    # 华南柱组左缘
        y_start = y_end                            # 等高 → 水平
        print(f"  水平箭头: ({x_start:.2f}, {y_start:.2f}) → ({x_end:.2f}, {y_end:.2f})")
        ax_bar.annotate("", xy=(x_end, y_end), xytext=(x_start, y_start),
                        xycoords=ax_bar.transData, textcoords=ax_bar.transData,
                        arrowprops=dict(arrowstyle="-|>", color="#555555", lw=0.8))

    # (b) 标签
    pos_bar = ax_bar.get_position()
    fig.text(pos_bar.x0 - 0.02, pos_bar.y1 + 0.02, "(b)",
             fontsize=18, ha="right", va="bottom", fontweight="normal")

    fig.savefig(OUTPUT_DIR / "Fig4.jpg", dpi=400, bbox_inches="tight")
    print(f"\n图形已保存至: {OUTPUT_DIR / 'Fig4.jpg'}")
    plt.close()


def main():
    """主流程：先统计（写 data/fig4_regional_stats.csv），再绘图（写 Fig4.jpg）"""
    compute_regional_stats()
    plot_figure()


if __name__ == "__main__":
    main()
