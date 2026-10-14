from pathlib import Path

import numpy as np
import pandas as pd
import xarray as xr
import shapefile
from shapely.geometry import shape as shapely_shape, Point
from shapely.ops import unary_union
import matplotlib.pyplot as plt
from matplotlib.cm import ScalarMappable
from matplotlib.colors import Normalize
from matplotlib.ticker import FuncFormatter, MultipleLocator

# ============================================================
# 路径
# ============================================================
# 本文件即模块根目录下的 Fig7.py，模块内的 data/ 与 Fig7.jpg 均相对此处定位
MODULE_DIR = Path(__file__).resolve().parent

REPO_ROOT = next(p for p in Path(__file__).resolve().parents if (p / "src").is_dir() and (p / "Doc").is_dir())


DATA_ROOT = REPO_ROOT / "Data"
HEC_DIR = REPO_ROOT / "Output" / "EC" / "China"   # 脚本 6 的规范输出（2021-2050）

# ============================================================
# 区域定义
# ============================================================
REGIONS = [
    ("China", -90, 90, -180, 360),  # 全格点（不掩膜）
    ("NorthChina", 35, 42, 110, 118),
    ("Northeast", 38, 54, 118, 135),
    ("Northwest", 35, 50, 73, 105),
    ("Southwest", 21, 35, 95, 108),
    ("EastChina", 27, 35, 115, 123),
    ("SouthChina", 18, 26, 108, 120),
    ("CentralChina", 26, 34, 108, 115),
]

# ============================================================
# 河流流域多边形
# ============================================================
river_dir = DATA_ROOT / "River"
# 多边形文件名仍为 HuanghaiRiver_polygon.shp，但其范围为黄河流域，显示名统一为 Yellow River
RIVER_BASINS = [
    ("YellowRiver", river_dir / "HuanghaiRiver_polygon.shp"),
    ("PearlRiver", river_dir / "PearlRiver_polygon.shp"),
    ("YangtzeRiver", river_dir / "YangtzeRiver_polygon.shp"),
]

scenarios = ['ssp126', 'ssp245', 'ssp585']
scenario_labels = ['SSP1-2.6', 'SSP2-4.5', 'SSP5-8.5']


# ============================================================
# 工具函数：河流流域掩膜
# ============================================================
def build_river_mask(shp_path, lon_2d, lat_2d):
    rsf = shapefile.Reader(str(shp_path))
    polys = [shapely_shape(s.__geo_interface__) for s in rsf.shapes()]
    merged = unary_union(polys)
    minx, miny, maxx, maxy = merged.bounds
    pre_mask = (lon_2d >= minx) & (lon_2d <= maxx) & \
               (lat_2d >= miny) & (lat_2d <= maxy)
    mask = np.zeros(lon_2d.shape, dtype=bool)
    candidates = np.where(pre_mask)
    for i, j in zip(*candidates):
        if merged.contains(Point(lon_2d[i, j], lat_2d[i, j])):
            mask[i, j] = True
    return mask


# ============================================================
# 区域加权统计工具
# ============================================================
def weighted_stats(field, mask, weights):
    valid = mask & np.isfinite(field)
    if valid.sum() == 0:
        return np.nan, np.nan
    w_mean = np.nansum(field * weights * valid) / np.nansum(weights * valid)
    w_var  = np.nansum((field - w_mean)**2 * weights * valid) / np.nansum(weights * valid)
    w_std  = np.sqrt(w_var) if w_var > 0 else 0.0
    return float(w_mean), float(w_std)


# ============================================================
# 第 1 步：分区域统计，写出 data/fig7_regional_stats.csv
# ============================================================
def calc_regional_stats():
    """逐情景统计 11 个区域的面积加权均值/标准差，返回 DataFrame 并写出 CSV。"""
    # 从第一个文件获取坐标
    ref_nc = HEC_DIR / f"HEC_{scenarios[0]}_PrecipVar_to_R95mm_intensity.nc"
    with xr.open_dataset(ref_nc) as ds_ref:
        lon = ds_ref['lon'].values.astype(np.float64)
        lat = ds_ref['lat'].values.astype(np.float64)
    lon_2d, lat_2d = np.meshgrid(lon, lat)

    weights = np.cos(np.deg2rad(lat))[:, np.newaxis]  # (lat, 1)

    # ---- 构造流域掩膜 ----
    river_masks = {}
    for rname, rfp in RIVER_BASINS:
        if rfp.exists():
            river_masks[rname] = build_river_mask(rfp, lon_2d, lat_2d)
            print(f'  加载河流流域 {rname}: {river_masks[rname].sum()} 个格点')

    # ---- 计算 ----
    results = []

    for s, slab in zip(scenarios, scenario_labels):
        nc_path = HEC_DIR / f"HEC_{s}_PrecipVar_to_R95mm_intensity.nc"
        with xr.open_dataset(nc_path) as ds:
            r_field = ds['r'].values
            reduction_field = ds['reduction'].values
            delta_field = ds['posterior_mean'].values - ds['prior_mean'].values
            p_field = ds['p_value'].values
            # 有效格点判据（与图5 面板 Mean 一致，同论文正文）：p<0.05 且 r>=0.5
            sig_mask = (np.isfinite(p_field) & np.isfinite(r_field)
                        & (p_field < 0.05) & (r_field >= 0.5))

        for reg in REGIONS:
            rname, lat_min, lat_max, lon_min, lon_max = reg
            mask = (lat_2d >= lat_min) & (lat_2d <= lat_max) & \
                   (lon_2d >= lon_min) & (lon_2d <= lon_max)

            # 统计域 = 区域掩膜 ∩ 有效格点（三个变量同域，便于跨列比较）
            mask = mask & sig_mask
            r_mean, r_std = weighted_stats(r_field, mask, weights)
            red_mean, red_std = weighted_stats(reduction_field, mask, weights)
            d_mean, d_std = weighted_stats(delta_field, mask, weights)

            results.append({
                'Scenario': slab, 'Region': rname,
                'r_mean': round(r_mean, 4), 'r_std': round(r_std, 4),
                'reduction_mean': round(red_mean, 4), 'reduction_std': round(red_std, 4),
                'delta_mean': round(d_mean, 4), 'delta_std': round(d_std, 4),
            })
            print(f'{slab:12s} | {rname:20s} | r={r_mean:7.4f} | reduction={red_mean:7.4f} | delta={d_mean:7.4f}')

        for rname, mask in river_masks.items():
            # 统计域 = 区域掩膜 ∩ 有效格点（三个变量同域，便于跨列比较）
            mask = mask & sig_mask
            r_mean, r_std = weighted_stats(r_field, mask, weights)
            red_mean, red_std = weighted_stats(reduction_field, mask, weights)
            d_mean, d_std = weighted_stats(delta_field, mask, weights)

            if np.isnan(r_mean):
                continue

            results.append({
                'Scenario': slab, 'Region': rname,
                'r_mean': round(r_mean, 4), 'r_std': round(r_std, 4),
                'reduction_mean': round(red_mean, 4), 'reduction_std': round(red_std, 4),
                'delta_mean': round(d_mean, 4), 'delta_std': round(d_std, 4),
            })
            print(f'{slab:12s} | {rname:20s} | r={r_mean:7.4f} | reduction={red_mean:7.4f} | delta={d_mean:7.4f}')

    # ---- 保存 CSV ----
    df = pd.DataFrame(results)
    csv_path = MODULE_DIR / 'data' / 'fig7_regional_stats.csv'
    csv_path.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(csv_path, index=False, encoding='utf-8-sig')
    print(f'\n结果已保存至: {csv_path}')
    print(f'共 {len(results)} 行（{len(scenarios)} 个情景 × {len(REGIONS) + len(river_masks)} 个区域）')
    return df


# ============================================================
# 第 2 步：绘制热力图，保存 Fig7.jpg
# ============================================================
# 绘图列序（与 scenario_labels 同序）
scenario_order = scenario_labels
region_order = ["China", "NorthChina", "Northeast", "Northwest",
                "Southwest", "EastChina", "SouthChina", "CentralChina",
                "YellowRiver", "PearlRiver", "YangtzeRiver"]
# 显示名与图 3 的 REGION_LABELS 保持一致（带词间隔；流域统一为 … Basin）
region_labels = ["China", "North China", "Northeast", "Northwest", "Southwest",
                 "East China", "South China", "Central China",
                 "Yellow River Basin", "Pearl Basin", "Yangtze Basin"]

# 三个变量的配置
var_configs = [
    # cbar_step：色带刻度的取整步长。色带上下限取实际极值（vmin/vmax = 数据 min/max），
    # 刻度位置另按量级取整，配合"非整数保留 1 位小数"的标签口径。
    {"key": "r",         "label": "Correlation r",             "fmt": ".3f", "cmap": "YlOrRd", "cbar_step": 0.1},
    {"key": "reduction", "label": "Uncertainty Reduction (σ)", "fmt": ".1%", "cmap": "OrRd",   "cbar_step": 2.5},
    {"key": "delta",     "label": "Adjustment",                      "fmt": ".1f", "cmap": "RdBu_r", "cbar_step": 2.0},
]


def _fmt_tick(v, _pos=None):
    """刻度标签：整数不带小数，非整数保留 1 位小数（全图统一口径）。"""
    return f"{v:.0f}" if abs(v - round(v)) < 1e-9 else f"{v:.1f}"


def plot_heatmap(csv_path=None):
    """读取分区域统计 CSV，绘制 11×3 三面板热力图并保存 Fig7.jpg。"""
    if csv_path is None:
        csv_path = MODULE_DIR / 'data' / 'fig7_regional_stats.csv'

    # ============================================================
    # 读取数据
    # ============================================================
    df = pd.read_csv(csv_path)

    # ============================================================
    # 绘图参数
    # ============================================================
    plt.rcParams["font.family"] = "Times New Roman"
    plt.rcParams["mathtext.fontset"] = "cm"
    plt.rcParams["axes.unicode_minus"] = False

    fig, axes = plt.subplots(1, 3, figsize=(20 / 2.54, 7 * 20 / (15 * 2.54)))

    for col, cfg in enumerate(var_configs):
        ax = axes[col]
        key = cfg["key"]
        mean_col = f"{key}_mean"

        # 构建 12×3 矩阵
        mat = np.zeros((len(region_order), len(scenario_order)))
        for i, reg in enumerate(region_order):
            for j, scen in enumerate(scenario_order):
                row = df[(df['Scenario'] == scen) & (df['Region'] == reg)].iloc[0]
                mat[i, j] = row[mean_col]

        if key == "reduction":
            # 显示为百分比
            display_mat = mat * 100
            fmt = ".1f"
            unit = "%"
        else:
            display_mat = mat
            fmt = cfg["fmt"]
            unit = ""

        # 颜色映射：热力图与色带统一用「显示量」（缩减率面板用百分数，
        # 否则会出现格内写 18.9% 而色带刻度写 0.16 的口径不一致）
        plot_mat = display_mat
        vmin, vmax = plot_mat.min(), plot_mat.max()
        norm = Normalize(vmin=vmin, vmax=vmax)
        cmap = cfg["cmap"]

        im = ax.imshow(plot_mat, aspect='auto', cmap=cmap, norm=norm)

        # 标注数值
        for i in range(len(region_order)):
            for j in range(len(scenario_order)):
                val = display_mat[i, j]
                text_color = 'white' if norm(display_mat[i, j]) > 0.6 else 'black'
                ax.text(j, i, f"{val:{fmt}}{unit}", ha='center', va='center',
                        fontsize=8, color=text_color, fontweight='bold')

        ax.set_xticks(range(len(scenario_order)))
        ax.set_xticklabels(scenario_order, fontsize=8, rotation=45, ha='right')
        ax.set_yticks(range(len(region_order)))
        ax.set_yticklabels(region_labels, fontsize=8)
        ax.set_title(f"({chr(97 + col)}) {cfg['label']}", fontsize=9.5, fontweight='normal', pad=10)

        # Colorbar (带箭头，长度为图的 3/4)
        sm = ScalarMappable(norm=norm, cmap=cmap)
        sm.set_array(np.array([vmin - 1, vmax + 1]))
        cbar = fig.colorbar(sm, ax=ax, extend='both', shrink=0.75,
                            extendfrac=0.06, fraction=0.14, pad=0.18)
        # 刻度：位置按本列量级取整步长，标签统一为"整数不带小数、非整数 1 位小数"。
        # (a) 列 r 的量程只有 0.15，若沿用 matplotlib 默认密度，标签在 1 位小数下会重复，
        # 故显式限定步长；其余两列同理。
        cbar.ax.yaxis.set_major_locator(MultipleLocator(cfg["cbar_step"]))
        cbar.ax.yaxis.set_major_formatter(FuncFormatter(_fmt_tick))
        cbar.ax.tick_params(labelsize=7.5)

    # 图内不设总标题（标题信息由论文图注给出）
    fig.subplots_adjust(left=0.08, right=0.95, top=0.93, bottom=0.06, wspace=0.60)

    out_path = MODULE_DIR / "Fig7.jpg"
    out_path.parent.mkdir(parents=True, exist_ok=True)
    plt.savefig(str(out_path), dpi=400, bbox_inches='tight')
    print(f'图形已保存至: {out_path}')
    plt.close()


def main():
    """完整流水线：先统计（写 CSV），再绘图（读 CSV 出图）。"""
    calc_regional_stats()
    plot_heatmap()


if __name__ == "__main__":
    main()
