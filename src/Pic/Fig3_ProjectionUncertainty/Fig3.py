import argparse
import os
from pathlib import Path

import numpy as np
import pandas as pd
import xarray as xr
import matplotlib.pyplot as plt
from matplotlib.colors import LinearSegmentedColormap, ListedColormap, BoundaryNorm
import cartopy.crs as ccrs
import shapefile
from shapely.geometry import shape as shapely_shape
from mpl_toolkits.axes_grid1.inset_locator import inset_axes
from matplotlib.ticker import FuncFormatter
import warnings
warnings.filterwarnings('ignore')

plt.rcParams["font.family"] = "Times New Roman"
plt.rcParams["mathtext.fontset"] = "cm"
plt.rcParams["axes.unicode_minus"] = False

# ---- 自定义色带 ----
mean_colors = ["#4C9AC9", "#C8E0EF", "#E7F2F6", "#FEE8DD", "#F5B99E", "#E2745E"]
mean_cmap = LinearSegmentedColormap.from_list("mean_custom", mean_colors, N=256)
std_colors = ["#72ABC9", "#FFD0A2", "#F2A07D", "#DE7C55", "#E77B54", "#E65B50"]
std_cmap = ListedColormap(std_colors, "std_custom")


REPO_ROOT = next(p for p in Path(__file__).resolve().parents if (p / "src").is_dir())


output_dir = Path(__file__).parent
data_dir = Path(__file__).parent / 'data'
output_dir.mkdir(parents=True, exist_ok=True)
data_dir.mkdir(parents=True, exist_ok=True)

# 预处理输入：三情景多模式指数文件
base_path = REPO_ROOT / "Output" / "Mode" / "indices" / "Scenariomerged"


DATA_ROOT = Path(__file__).resolve().parent / "data" / "geography"
shp_path = DATA_ROOT / "China" / "cnmap.shp"

scenarios = ['ssp126', 'ssp245', 'ssp585']
scenario_labels = ['SSP1-2.6', 'SSP2-4.5', 'SSP5-8.5']
future_period = slice(2021, 2050)

# 预处理产物：本模块的中间数据，也是兄弟模块 Fig4_RegionalStatistics 的上游输入
npz_path = data_dir / 'fig3_data.npz'


def prepare_data() -> Path:
    """读三情景 R95mm_intensity → 集合平均/模式间方差与标准差 → 原子写入 data/fig3_data.npz。

    返回:
        写入完成的 npz 路径。
    """
    print('=' * 60)
    print('Fig3 数据预处理')
    print('=' * 60)

    all_data = {}
    lon = None
    lat = None

    for s, label in zip(scenarios, scenario_labels):
        print(f'\n处理 {label} ...')
        fp = base_path / f'MULTI_MODEL-{s}-ALL_INDICES.nc'
        if not fp.exists():
            raise FileNotFoundError(f'未找到模式数据: {fp}')
        ds = xr.open_dataset(fp)

        models = ds['Mode'].values.tolist()
        r95 = ds['R95mm_intensity']

        if s == scenarios[0]:
            lat = ds['lat'].values
            lon = ds['lon'].values
            print(f'  网格: {len(lat)} lat × {len(lon)} lon')

        print(f'  模型数: {len(models)}')

        # 逐个模型计算未来时期的时间平均
        model_means = []
        for i, m in enumerate(models):
            model_data = r95.isel(Mode=i).sel(year=future_period)
            time_mean = model_data.mean(dim='year', skipna=True)
            model_means.append(time_mean.values)
            print(f'  [{i+1}/{len(models)}] {m} done')

        model_means = np.array(model_means)  # (n_models, lat, lon)

        # 多模式集合统计
        ens_mean = np.nanmean(model_means, axis=0)
        ens_std = np.nanstd(model_means, axis=0)   # 模式间标准差
        ens_var = ens_std ** 2                     # 模式间方差（留档；全文统一按 σ 报告）

        all_data[s] = {'mean': ens_mean, 'var': ens_var, 'std': ens_std}

        ds.close()
        del model_means, ens_mean, ens_std, ens_var

    # ---------------- 保存 ----------------
    save_dict = {
        'lon': lon,
        'lat': lat,
    }
    for s in scenarios:
        save_dict[f'{s}_mean'] = all_data[s]['mean']
        save_dict[f'{s}_var'] = all_data[s]['var']   # 模式间方差 (mm/day)^2（留档）
        save_dict[f'{s}_std'] = all_data[s]['std']   # 模式间标准差 mm/day（绘图主口径）

    # 原子写入：先写同目录临时文件（np.savez_compressed 会给不带 .npz 后缀的名字自动补后缀，
    # 故临时名也以 .npz 结尾），再用 os.replace 一步切换到最终名。
    # 兄弟模块 Fig4_RegionalStatistics 会并发 np.load 这个文件，原子替换可避免它读到半成品。
    tmp_path = data_dir / f'fig3_data.tmp{os.getpid()}.npz'
    try:
        np.savez_compressed(tmp_path, **save_dict)
        os.replace(tmp_path, npz_path)
    except BaseException:
        tmp_path.unlink(missing_ok=True)
        raise

    print(f'\n数据已保存至: {npz_path}')
    print(f'  变量: {list(save_dict.keys())}')
    print('完成！')
    return npz_path


# ============================================================
# 统计数据落盘
# ============================================================


def dump_stats_csv(rows, stats_csv_path) -> None:
    """把逐面板统计数据写成 CSV（data/ 目录）。

    字段固定为: row, scenario, label, mean_area_weighted, vmin, vmax
    编码 utf-8-sig（带 BOM），便于 Excel 直接双击打开不乱码。

    参数:
        rows: 每个面板的统计 dict 列表（键同 dump_statistics）。
        stats_csv_path: 输出 CSV 路径。
    """
    df = pd.DataFrame(
        [
            {
                "row": r["row"],
                "scenario": r["scenario"],
                "label": r["label"],
                "mean_area_weighted": float(r["mean_w"]),
                "vmin": float(r["vmin"]),
                "vmax": float(r["vmax"]),
            }
            for r in rows
        ],
        columns=["row", "scenario", "label", "mean_area_weighted", "vmin", "vmax"],
    )
    stats_csv_path.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(stats_csv_path, index=False, encoding="utf-8-sig")


def dump_levels_csv(levels_map, levels_csv_path) -> None:
    """把色带分级写成独立 CSV（data/fig3_levels.csv，长表格式）。

    选择单独文件而非在同一 CSV 追加额外行：stats CSV 因此保持整齐的 6 列定长表，
    pandas.read_csv 不需要处理缺列/NaN 行；而色带分级每条是长度不定的边界数组，
    长表 (row, level_index, level_value) 更自然，也方便按 row 过滤。

    参数:
        levels_map: {"mean": array([...]), "std": array([...])}。
        levels_csv_path: 输出 CSV 路径。
    """
    records = []
    for row_key, lv in levels_map.items():
        for i, v in enumerate(np.asarray(lv).ravel()):
            records.append({"row": row_key, "level_index": i, "level_value": float(v)})
    df = pd.DataFrame(records, columns=["row", "level_index", "level_value"])
    levels_csv_path.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(levels_csv_path, index=False, encoding="utf-8-sig")


# ------------------------------------------------------------
# 色带分级：由数据推出（三情景合集），不再写死 5-35 / 0-8。
# 直方图沿用同一套分箱，因此不会出现「范围外数值被裁剪堆叠」。
# ------------------------------------------------------------
def data_driven_levels(lo, hi, n_target=6):
    """由数据范围推出整齐的分级边界。

    注意：当前分级已改为直接取数据极值等分（见 plot_figure 内的 LEVELS），
    本函数作为"整齐步长"方案的备选保留，暂未被调用。

    参数:
        lo, hi: 数据全局最小、最大值。
        n_target: 期望的区间数。

    返回:
        分级边界（含首尾），保证覆盖 [lo, hi]。
    """
    span = max(hi - lo, 1e-9)
    mag = 10.0 ** np.floor(np.log10(span / n_target))
    best = None
    for k in (0.1, 1.0, 10.0):
        for m in (1.0, 1.5, 2.0, 2.5, 3.0, 4.0, 5.0, 10.0):
            step = m * mag * k
            n = span / step
            if not 3.0 <= n <= 12.0:
                continue
            score = abs(n - n_target)
            if best is None or score < best[0]:
                best = (score, step)
    step = best[1] if best else span / n_target
    start = np.floor(lo / step) * step
    stop = np.ceil(hi / step) * step
    return np.round(np.arange(start, stop + step / 2.0, step), 6)


def _fmt_tick(v, _pos=None):
    """刻度标签：整数不带小数，非整数保留 1 位小数（全图统一口径）。"""
    return f"{v:.0f}" if abs(v - round(v)) < 1e-9 else f"{v:.1f}"


def row_data_range(data, key):
    """取某一行（mean/std）三情景合集的数值范围，供分级使用。"""
    vals = np.concatenate([data[f"{s}_{key}"].ravel() for s in scenarios])
    vals = vals[np.isfinite(vals)]
    return float(vals.min()), float(vals.max())


def make_band_colors(base_cmap, n):
    """把基色带转成线性色带后取 n 个离散颜色。

    地图分带、直方图柱与色带分段共用这一组颜色，保证颜色边界严格落在分级刻度上；
    离散色带（如 std_cmap）先转线性再采样，避免相邻分带取到同一颜色。
    """
    if isinstance(base_cmap, ListedColormap):
        base = LinearSegmentedColormap.from_list(f"{base_cmap.name}_lin", list(base_cmap.colors))
    else:
        base = base_cmap
    if n <= 1:
        return [base(0.5)]
    return [base(i / (n - 1)) for i in range(n)]


# ============================================================
# 第 2 步：绘图（原 Fig3.py）
# ============================================================
def plot_figure(npz_path: Path) -> None:
    """载入预处理结果并渲染 Fig3.jpg，同时落盘统计表与色带分级。"""
    print('=' * 60)
    print('Fig. 3: 加载预处理数据')
    print('=' * 60)

    data = np.load(npz_path)

    lon = data['lon']
    lat = data['lat']
    print(f'  网格: {len(lat)} lat × {len(lon)} lon')

    weights = np.cos(np.deg2rad(lat))
    weights_2d = weights[:, np.newaxis]

    LEVELS = {}
    for _key in ("mean", "std"):
        _lo, _hi = row_data_range(data, _key)


        LEVELS[_key] = np.linspace(_lo, _hi, 7)
        print(f"  色带分级[{_key}]: {LEVELS[_key].tolist()}   (数据 {_lo:.3f} ~ {_hi:.3f})")

    # ========================================================
    # 加载中国国界
    # ========================================================
    print('加载中国国界矢量...')
    sf = shapefile.Reader(str(shp_path))
    cn_geoms = [shapely_shape(s.__geo_interface__) for s in sf.shapes()]
    shp_bbox = sf.bbox
    extent = [float(shp_bbox[0]) - 1, float(shp_bbox[2]) + 1,
              float(shp_bbox[1]) - 1, float(shp_bbox[3]) + 1]

    proj = ccrs.PlateCarree()
    Lon, Lat_grid = np.meshgrid(lon, lat)

    # ========================================================
    # 绘图：2 行 × 3 列 (行=均值/模式间标准差 σ, 列=情景)
    # ========================================================
    fig_w_cm, fig_h_cm = 20, 15
    fig = plt.figure(figsize=(fig_w_cm / 2.54, fig_h_cm / 2.54))

    rows = [
        {
            "key": "mean",
            "cmap": mean_cmap,
            "levels": LEVELS["mean"],
            "vmin": float(LEVELS["mean"][0]), "vmax": float(LEVELS["mean"][-1]),
            "title": "R95 Intensity: Multi-Model Ensemble Mean (2021–2050)",
        },
        {
            "key": "std",
            "cmap": std_cmap,
            "levels": LEVELS["std"],
            "vmin": float(LEVELS["std"][0]), "vmax": float(LEVELS["std"][-1]),
            "title": r"R95 Intensity: Inter-model Uncertainty ($\sigma$) (2021–2050)",
        },
    ]

    row_first_axes = []

    def R(l, b, w, h):
        return (l / fig_w_cm, b / fig_h_cm, w / fig_w_cm, h / fig_h_cm)

    pw, ph = 5.4, 4.8     # 每个地图面板宽、高 (cm)
    pgx = 0.8              # 列间距
    lmar = 0.8             # 左边界
    row_h = 5.8            # 每行总高度 (含标注空间)
    y_gap = 3.0            # 两行之间的间距

    stats_rows = []

    for row_idx, row_cfg in enumerate(rows):
        y_bot = fig_h_cm - (row_idx + 1) * row_h - row_idx * y_gap
        x_start = lmar
        # 本行离散颜色：地图分带、柱色、色带分段共用
        n_bands = len(row_cfg["levels"]) - 1
        band = make_band_colors(row_cfg["cmap"], n_bands)

        row_first_ax = None
        mid_ax = None
        for c in range(3):
            field_data = data[f'{scenarios[c]}_{row_cfg["key"]}']
            x_pos = x_start + c * (pw + pgx)
            ax = fig.add_axes(R(x_pos, y_bot, pw, ph), projection=proj)
            if c == 0:
                row_first_axes.append(ax)
            if c == 1:
                mid_ax = ax
            ax.set_extent(extent, crs=proj)

            ax.contourf(Lon, Lat_grid, field_data, levels=row_cfg["levels"],
                        transform=proj, colors=band, extend='both')
            ax.contour(Lon, Lat_grid, field_data, levels=row_cfg["levels"],
                       transform=proj, colors='black', linewidths=0.3)

            ax.add_geometries(cn_geoms, crs=ccrs.PlateCarree(), facecolor='none',
                              edgecolor='#999999', linewidth=0.5)

            # 面积加权平均
            valid = np.isfinite(field_data)
            wm = np.nansum(field_data * weights_2d) / np.nansum(weights_2d * valid)
            stats_rows.append({
                "row": row_cfg["key"],
                "scenario": scenarios[c],
                "label": scenario_labels[c],
                "mean_w": float(wm),
                "vmin": float(np.nanmin(field_data)),
                "vmax": float(np.nanmax(field_data)),
            })
            ax.text(0.14, 0.26, f'Mean: {wm:.2f}',
                    transform=ax.transAxes, fontsize=9,
                    ha='left', va='bottom',
                    bbox=dict(boxstyle='round,pad=0.3', facecolor='white', edgecolor='gray', alpha=0.8))

            ax.set_title(scenario_labels[c], fontsize=14, fontweight='normal', pad=8)

            gl = ax.gridlines(draw_labels=True, linewidth=0.2, alpha=0.4, linestyle='--',
                              xlocs=[80, 90, 110, 130], ylocs=[10, 20, 30, 40, 50])
            gl.top_labels = False
            gl.right_labels = False
            gl.xlabel_style = {'size': 11}
            gl.ylabel_style = {'size': 11}

            # 直方图：分箱与色带分级一致（该分级已由数据推出、覆盖数据全域，故无需裁剪）
            fvals = field_data.ravel()
            fvals = fvals[np.isfinite(fvals)]
            if len(fvals) > 0:
                bins = row_cfg["levels"]
                counts, _ = np.histogram(fvals, bins=bins)
                n_int = len(bins) - 1
                bc = (bins[:-1] + bins[1:]) / 2
                bin_w = np.diff(bins)
                pdf = counts / (counts.sum() * bin_w)
                pdf_w = 0.40 if row_idx == 0 else 0.315
                hist_ax = inset_axes(ax, width=pdf_w, height=0.248,
                                     bbox_to_anchor=(0.18, 0.07),
                                     bbox_transform=ax.transAxes,
                                     loc='lower left', borderpad=0)
                cmap_obj = row_cfg["cmap"]
                for j in range(n_int):
                    hist_ax.bar(bc[j], pdf[j], width=bin_w[j] * 0.9,
                                color=band[j],
                                edgecolor='black', linewidth=0.3)
                hist_ax.set_xlim(bins[0], bins[-1])
                hist_ax.tick_params(axis='both', length=1.5, labelsize=9, width=0.3)
                hist_ax.set_ylabel('PDF', fontsize=9, fontweight='normal', labelpad=0)
                hist_ax.set_facecolor('none')
                hist_ax.patch.set_alpha(0)
                for sp in hist_ax.spines.values():
                    sp.set_linewidth(0.3)
                hist_ax.spines['top'].set_visible(False)
                hist_ax.spines['right'].set_visible(False)

            ax.spines['geo'].set_visible(False)

        # 色带（每行一个，以中间子图为中心）
        x0 = mid_ax.get_position().x0
        x1 = mid_ax.get_position().x1
        y0 = mid_ax.get_position().y0
        cbar_w = (x1 - x0) * 1.80
        cx = (x0 + x1) / 2
        cax = fig.add_axes((cx - cbar_w / 2, y0 - 0.09, cbar_w, 0.025))
        im = plt.cm.ScalarMappable(
            norm=BoundaryNorm(row_cfg["levels"], ncolors=n_bands),
            cmap=ListedColormap(band, f"{row_cfg['key']}_bands"),
        )
        im.set_array([])
        cbar = fig.colorbar(im, cax=cax, orientation='horizontal',
                            extend='both', extendfrac=0.04, ticks=row_cfg["levels"])
        # 刻度标签统一：整数不带小数，非整数保留 1 位小数
        cbar.ax.xaxis.set_major_formatter(FuncFormatter(_fmt_tick))
        cbar.ax.tick_params(labelsize=12)
        cbar.set_label('mm/day', fontsize=12)

        # 行标题（放在本行中间子图上方）
        mid_pos = mid_ax.get_position()
        fig.text((mid_pos.x0 + mid_pos.x1) / 2, mid_pos.y1 + 0.07,
                 row_cfg["title"], ha="center", va="bottom",
                 fontsize=15, fontweight="normal")

    # 行标签 (a)(b) 放在轴外左上角
    for r_idx, first_ax in enumerate(row_first_axes):
        pos = first_ax.get_position()
        fig.text(pos.x0 - 0.02, pos.y1 + 0.02, f"({chr(ord('a') + r_idx)})",
                 fontsize=15, ha="right", va="bottom", fontweight="normal")

    # 统计数据落盘为 CSV（utf-8-sig）：主表 fig3_stats.csv + 色带分级 fig3_levels.csv
    stats_csv_path = data_dir / "fig3_stats.csv"
    levels_csv_path = data_dir / "fig3_levels.csv"
    dump_stats_csv(stats_rows, stats_csv_path)
    dump_levels_csv(LEVELS, levels_csv_path)
    print(f'统计数据 CSV 已保存至: {stats_csv_path}')
    print(f'色带分级 CSV 已保存至: {levels_csv_path}')

    fig.savefig(output_dir / "Fig3.jpg", dpi=400, bbox_inches="tight")
    print(f'\n图形已保存至: {output_dir / "Fig3.jpg"}')
    plt.close(fig)


def main(argv=None) -> None:
    """单文件流水线入口：预处理 → 绘图。"""
    parser = argparse.ArgumentParser(
        description='Fig. 3 单文件流水线：数据预处理（写 data/fig3_data.npz）+ 绘图。'
    )
    parser.add_argument(
        '--reuse-npz', action='store_true',
        help='跳过预处理，复用已有的 data/fig3_data.npz，只执行绘图。'
             '预处理需读入约 15 GB 的 MULTI_MODEL-*-ALL_INDICES.nc，'
             '在只需重绘/复核图形时用本开关可省去这段时间。'
    )
    args = parser.parse_args(argv)

    if args.reuse_npz or npz_path.exists():
        if not npz_path.exists():
            raise FileNotFoundError(f'--reuse-npz 指定复用已有数据，但未找到: {npz_path}')
        print(f'[--reuse-npz] 跳过预处理，复用: {npz_path}')
    else:
        prepare_data()

    plot_figure(npz_path)


if __name__ == '__main__':
    main()
