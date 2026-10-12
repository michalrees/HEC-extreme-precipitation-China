from __future__ import annotations
from pathlib import Path
from typing import Any, Dict, Tuple, cast
import os
import subprocess
import sys
import matplotlib.pyplot as plt
import numpy as np
import rioxarray
import xarray as xr
from scipy.stats import linregress

# =========================
# 参数
# =========================
HIST_PERIOD_RANGE: Tuple[int, int] = (1981, 2010)
FUTURE_PERIOD_RANGE: Tuple[int, int] = (2021, 2050)

SCENARIOS: Tuple[str, ...] = ("ssp126", "ssp245", "ssp585")
SCENARIO_ENV = os.getenv("SCENARIO")

# 仓库根：向上找到同时含 src/ 与 Doc/ 的目录（本脚本位于 src/pipeline/）
REPO_ROOT = next(p for p in Path(__file__).resolve().parents if (p / "src").is_dir() and (p / "Doc").is_dir())
# 数据根目录：src/、Output/、Data/ 现均在论文文件夹内（与 Doc/ 同级），
# 且此处为绝对路径——批处理用 cwd=REPO_ROOT 起子进程，相对路径会失效。
DATA_ROOT = REPO_ROOT / "Data"

if SCENARIO_ENV is None:
    script_path = Path(__file__).resolve()
    workspace_root_for_batch = REPO_ROOT
    print(f"[INFO] 批量运行情景: {list(SCENARIOS)}")
    for one_scenario in SCENARIOS:
        print(f"\n===== 开始处理 {one_scenario} =====")
        env = os.environ.copy()
        env["SCENARIO"] = one_scenario
        subprocess.run(
            [sys.executable, str(script_path)],
            cwd=str(workspace_root_for_batch),
            env=env,
            check=True,
        )
    print("\n[DONE] 三个情景均处理完成")
    raise SystemExit(0)

SCENARIO = SCENARIO_ENV.strip().lower()
if SCENARIO not in SCENARIOS:
    raise ValueError(f"不支持的情景: {SCENARIO}，仅支持 {list(SCENARIOS)}")

MODE_SCENARIO_MERGED_FILE = Path("Output") / "Mode" / "indices"/"Scenariomerged" / f"MULTI_MODEL-{SCENARIO}-ALL_INDICES.nc"
CN05_HIST_FILE = Path("Output") / "Obs" / "indices" / "CN05-OBS-IntensityAndPrecipVar-1961-2023.nc"

HIST_INDICATOR = "PrecipVar"
FUTURE_INDICATOR = "R95mm_intensity"
# 观测误差项 observational error term（固定，无开关）：σ_o = 产品间标准差 / √N。
# 依据：四套观测产品可视为同一真值的独立估计，代入回归的是它们的均值，故 σ_o 取产品间标准差除以 √N。
# 2026-10-09 起移除原口径开关（另一支"产品间离散度 σ_raw"不再支持）。

CHINA_ROOT = REPO_ROOT / "Output" / "EC" / "China"
# 三个情景的 nc 统一平铺在 China 根目录下（2026-10-09 起取消 <scenario>/data 嵌套层）
DATA_ROOT = CHINA_ROOT

OBS_PRODUCT_FILES: Dict[str, Path] = {
    "CN05": CN05_HIST_FILE,
    "CPC": Path("Output") / "Obs" / "indices" / "CPC-OBS-IntensityAndPrecipVar-1979-2025.nc",
    "CHM_PRE_V2": Path("Output") / "Obs" / "indices" / "CHM_PRE_V2-OBS-IntensityAndPrecipVar-1961-2024.nc",
    "HGCDC": Path("Output") / "Obs" / "indices" / "HGCDC-OBS-IntensityAndPrecipVar-1961-2022.nc",
}

# =========================
# 基础准备
# =========================
workspace_root = REPO_ROOT
mode_file = workspace_root / MODE_SCENARIO_MERGED_FILE
cn05_file = workspace_root / CN05_HIST_FILE

if not mode_file.exists():
    raise FileNotFoundError(f"模式文件不存在: {mode_file}")
if not cn05_file.exists():
    raise FileNotFoundError(f"CN05 文件不存在: {cn05_file}")

DATA_ROOT.mkdir(parents=True, exist_ok=True)

# =========================
# 读取 CN05 网格
# =========================
with xr.open_dataset(cn05_file) as cn05_ds:
    coord_map = {str(name).lower(): str(name) for name in cn05_ds.coords}
    cn05_lat_name = coord_map.get("lat") or coord_map.get("latitude") or coord_map.get("y")
    cn05_lon_name = coord_map.get("lon") or coord_map.get("longitude") or coord_map.get("x")
    if cn05_lat_name is None or cn05_lon_name is None:
        raise ValueError(f"CN05 文件缺少经纬度坐标: {list(cn05_ds.coords)}")
    target_lat = cn05_ds[cn05_lat_name].values.astype(np.float64)
    target_lon = cn05_ds[cn05_lon_name].values.astype(np.float64)

if target_lat.size < 2 or target_lon.size < 2:
    raise ValueError("CN05 网格太小，无法进行面积加权重映射")
if target_lat[1] < target_lat[0]:
    target_lat = target_lat[::-1]
if target_lon[1] < target_lon[0]:
    target_lon = target_lon[::-1]

print(f"目标网格: lat={target_lat.size}, lon={target_lon.size}")
print(
    f"CN05范围: lat=[{float(target_lat.min()):.3f}, {float(target_lat.max()):.3f}], "
    f"lon=[{float(target_lon.min()):.3f}, {float(target_lon.max()):.3f}]"
)

# =========================
# 观测产品处理流程：
# 1. 逐个读取四套观测产品的历史指标逐年数据
# 2. 截取历史时段，并对年序列求年段平均
# 3. 输入文件已在前面的预处理中统一到 CN05 分辨率与格网，这里不再做重映射
# 4. 不做流域 shp 裁剪，直接全中国区域分析
# =========================
obs_fields = []
obs_source_names = []

for product_name, data_file in OBS_PRODUCT_FILES.items():
    selected_file = workspace_root / data_file
    if not selected_file.exists():
        raise FileNotFoundError(f"未找到观测文件: {product_name}, 路径={selected_file}")

    with xr.open_dataset(selected_file) as ds:
        if HIST_INDICATOR not in ds.data_vars:
            raise ValueError(f"观测文件缺少指标 {HIST_INDICATOR}: {selected_file}")

        da = ds[HIST_INDICATOR]
        if "year" not in da.dims and "time" in da.dims:
            da = da.rename({"time": "year"})
        if "year" in da.coords and np.issubdtype(da["year"].dtype, np.datetime64):
            da = da.assign_coords(year=da["year"].dt.year.astype("int32"))
        if "year" in da.coords and not np.issubdtype(da["year"].dtype, np.integer):
            da = da.assign_coords(year=da["year"].astype("int32"))

        da_sel = da.sel(year=slice(HIST_PERIOD_RANGE[0], HIST_PERIOD_RANGE[1]))
        if da_sel.sizes.get("year", 0) == 0:
            raise ValueError(f"{product_name} 在历史时段没有有效数据")
        da_mean = da_sel.mean(dim="year", skipna=True)

        coord_map = {str(name).lower(): str(name) for name in da_mean.coords}
        lat_name = coord_map.get("lat") or coord_map.get("latitude") or coord_map.get("y")
        lon_name = coord_map.get("lon") or coord_map.get("longitude") or coord_map.get("x")
        if lat_name is None or lon_name is None:
            raise ValueError(f"{product_name} 缺少经纬度坐标")

        if lat_name != "lat":
            da_mean = da_mean.rename({lat_name: "lat"})
            lat_name = "lat"
        if lon_name != "lon":
            da_mean = da_mean.rename({lon_name: "lon"})
            lon_name = "lon"

        if float(da_mean[lon_name].max()) > 180.0:
            lon_new = ((da_mean[lon_name] + 180.0) % 360.0) - 180.0
            da_mean = da_mean.assign_coords({lon_name: lon_new}).sortby(lon_name)
        if da_mean[lat_name].size > 1 and float(da_mean[lat_name][1] - da_mean[lat_name][0]) < 0:
            da_mean = da_mean.sortby(lat_name)
        if da_mean[lon_name].size > 1 and float(da_mean[lon_name][1] - da_mean[lon_name][0]) < 0:
            da_mean = da_mean.sortby(lon_name)
        if da_mean.sizes.get(lat_name, 0) != target_lat.size or da_mean.sizes.get(lon_name, 0) != target_lon.size:
            raise ValueError(
                f"{product_name} 已统一后的网格尺寸与 CN05 不一致: "
                f"lat={da_mean.sizes.get(lat_name, 0)} vs {target_lat.size}, "
                f"lon={da_mean.sizes.get(lon_name, 0)} vs {target_lon.size}"
            )

        da_regrid = xr.DataArray(
            da_mean.transpose(lat_name, lon_name).values.astype(np.float32),
            dims=("lat", "lon"),
            coords={"lat": target_lat, "lon": target_lon},
            name=product_name,
            attrs=dict(da_mean.attrs),
        )

        obs_fields.append(da_regrid)
        obs_source_names.append(product_name)

stack = xr.concat(obs_fields, dim="source")
stack = stack.assign_coords(source=obs_source_names)

obs_mean = stack.mean(dim="source", skipna=True)
obs_sigma = stack.std(dim="source", skipna=True, ddof=1)
obs_count = stack.count(dim="source")

# =========================
# 模式数据：逐年 -> 年段平均 -> 面积加权
# =========================
with xr.open_dataset(mode_file) as ds_mode_all:
    if "time" in ds_mode_all.coords and "year" not in ds_mode_all.coords:
        ds_mode_all = ds_mode_all.rename({"time": "year"})
    if "year" in ds_mode_all.coords and np.issubdtype(ds_mode_all["year"].dtype, np.datetime64):
        ds_mode_all = ds_mode_all.assign_coords(year=ds_mode_all["year"].dt.year.astype("int32"))
    if "year" in ds_mode_all.coords and not np.issubdtype(ds_mode_all["year"].dtype, np.integer):
        ds_mode_all = ds_mode_all.assign_coords(year=ds_mode_all["year"].astype("int32"))

    if "Mode" not in ds_mode_all.dims or "year" not in ds_mode_all.dims:
        raise ValueError("模式文件需要包含 Mode 与 year 维度")
    if HIST_INDICATOR not in ds_mode_all.data_vars:
        raise ValueError(f"模式文件缺少历史指标 {HIST_INDICATOR}")
    if FUTURE_INDICATOR not in ds_mode_all.data_vars:
        raise ValueError(f"模式文件缺少未来指标 {FUTURE_INDICATOR}")

    mode_names = [str(v) for v in ds_mode_all["Mode"].values.tolist()]
    x_fields = []
    y_fields = []

    for mode_name in mode_names:
        ds_mode = ds_mode_all.sel(Mode=mode_name)

        x_da = ds_mode[HIST_INDICATOR]
        if "time" in x_da.dims and "year" not in x_da.dims:
            x_da = x_da.rename({"time": "year"})
        if "year" in x_da.coords and np.issubdtype(x_da["year"].dtype, np.datetime64):
            x_da = x_da.assign_coords(year=x_da["year"].dt.year.astype("int32"))
        if "year" in x_da.coords and not np.issubdtype(x_da["year"].dtype, np.integer):
            x_da = x_da.assign_coords(year=x_da["year"].astype("int32"))
        x_sel = x_da.sel(year=slice(HIST_PERIOD_RANGE[0], HIST_PERIOD_RANGE[1]))
        if x_sel.sizes.get("year", 0) == 0:
            raise ValueError(f"{mode_name} 历史时段没有有效数据")
        x_mean = x_sel.mean(dim="year", skipna=True)

        y_da = ds_mode[FUTURE_INDICATOR]
        if "time" in y_da.dims and "year" not in y_da.dims:
            y_da = y_da.rename({"time": "year"})
        if "year" in y_da.coords and np.issubdtype(y_da["year"].dtype, np.datetime64):
            y_da = y_da.assign_coords(year=y_da["year"].dt.year.astype("int32"))
        if "year" in y_da.coords and not np.issubdtype(y_da["year"].dtype, np.integer):
            y_da = y_da.assign_coords(year=y_da["year"].astype("int32"))
        y_sel = y_da.sel(year=slice(FUTURE_PERIOD_RANGE[0], FUTURE_PERIOD_RANGE[1]))
        if y_sel.sizes.get("year", 0) == 0:
            raise ValueError(f"{mode_name} 未来时段没有有效数据")
        y_mean = y_sel.mean(dim="year", skipna=True)

        coord_map_x = {str(name).lower(): str(name) for name in x_mean.coords}
        coord_map_y = {str(name).lower(): str(name) for name in y_mean.coords}
        lat_name_x = coord_map_x.get("lat") or coord_map_x.get("latitude") or coord_map_x.get("y")
        lon_name_x = coord_map_x.get("lon") or coord_map_x.get("longitude") or coord_map_x.get("x")
        lat_name_y = coord_map_y.get("lat") or coord_map_y.get("latitude") or coord_map_y.get("y")
        lon_name_y = coord_map_y.get("lon") or coord_map_y.get("longitude") or coord_map_y.get("x")
        if lat_name_x is None or lon_name_x is None or lat_name_y is None or lon_name_y is None:
            raise ValueError(f"{mode_name} 缺少经纬度坐标")

        if lat_name_x != "lat":
            x_mean = x_mean.rename({lat_name_x: "lat"})
            lat_name_x = "lat"
        if lon_name_x != "lon":
            x_mean = x_mean.rename({lon_name_x: "lon"})
            lon_name_x = "lon"
        if lat_name_y != "lat":
            y_mean = y_mean.rename({lat_name_y: "lat"})
            lat_name_y = "lat"
        if lon_name_y != "lon":
            y_mean = y_mean.rename({lon_name_y: "lon"})
            lon_name_y = "lon"

        if float(x_mean[lon_name_x].max()) > 180.0:
            lon_new = ((x_mean[lon_name_x] + 180.0) % 360.0) - 180.0
            x_mean = x_mean.assign_coords({lon_name_x: lon_new}).sortby(lon_name_x)
        if float(y_mean[lon_name_y].max()) > 180.0:
            lon_new = ((y_mean[lon_name_y] + 180.0) % 360.0) - 180.0
            y_mean = y_mean.assign_coords({lon_name_y: lon_new}).sortby(lon_name_y)
        if x_mean[lat_name_x].size > 1 and float(x_mean[lat_name_x][1] - x_mean[lat_name_x][0]) < 0:
            x_mean = x_mean.sortby(lat_name_x)
        if x_mean[lon_name_x].size > 1 and float(x_mean[lon_name_x][1] - x_mean[lon_name_x][0]) < 0:
            x_mean = x_mean.sortby(lon_name_x)
        if y_mean[lat_name_y].size > 1 and float(y_mean[lat_name_y][1] - y_mean[lat_name_y][0]) < 0:
            y_mean = y_mean.sortby(lat_name_y)
        if y_mean[lon_name_y].size > 1 and float(y_mean[lon_name_y][1] - y_mean[lon_name_y][0]) < 0:
            y_mean = y_mean.sortby(lon_name_y)

        src_lat = x_mean[lat_name_x].values.astype(np.float64)
        src_lon = x_mean[lon_name_x].values.astype(np.float64)
        if src_lat.size < 2 or src_lon.size < 2:
            raise ValueError(f"{mode_name} 网格太小，无法重映射")

        src_lat_b = np.empty(src_lat.size + 1, dtype=np.float64)
        src_lon_b = np.empty(src_lon.size + 1, dtype=np.float64)
        src_lat_b[1:-1] = 0.5 * (src_lat[:-1] + src_lat[1:])
        src_lon_b[1:-1] = 0.5 * (src_lon[:-1] + src_lon[1:])
        src_lat_b[0] = src_lat[0] - 0.5 * (src_lat[1] - src_lat[0])
        src_lat_b[-1] = src_lat[-1] + 0.5 * (src_lat[-1] - src_lat[-2])
        src_lon_b[0] = src_lon[0] - 0.5 * (src_lon[1] - src_lon[0])
        src_lon_b[-1] = src_lon[-1] + 0.5 * (src_lon[-1] - src_lon[-2])

        dst_lat_b = np.empty(target_lat.size + 1, dtype=np.float64)
        dst_lon_b = np.empty(target_lon.size + 1, dtype=np.float64)
        dst_lat_b[1:-1] = 0.5 * (target_lat[:-1] + target_lat[1:])
        dst_lon_b[1:-1] = 0.5 * (target_lon[:-1] + target_lon[1:])
        dst_lat_b[0] = target_lat[0] - 0.5 * (target_lat[1] - target_lat[0])
        dst_lat_b[-1] = target_lat[-1] + 0.5 * (target_lat[-1] - target_lat[-2])
        dst_lon_b[0] = target_lon[0] - 0.5 * (target_lon[1] - target_lon[0])
        dst_lon_b[-1] = target_lon[-1] + 0.5 * (target_lon[-1] - target_lon[-2])

        src_lat_b_sin = np.sin(np.deg2rad(src_lat_b))
        dst_lat_b_sin = np.sin(np.deg2rad(dst_lat_b))

        lat_overlap = np.maximum(
            0.0,
            np.minimum(src_lat_b_sin[1:][None, :], dst_lat_b_sin[1:][:, None])
            - np.maximum(src_lat_b_sin[:-1][None, :], dst_lat_b_sin[:-1][:, None]),
        )
        lon_overlap = np.maximum(
            0.0,
            np.minimum(src_lon_b[1:][None, :], dst_lon_b[1:][:, None])
            - np.maximum(src_lon_b[:-1][None, :], dst_lon_b[:-1][:, None]),
        )
        dst_lat_extent = (dst_lat_b_sin[1:] - dst_lat_b_sin[:-1])[:, None]
        dst_lon_extent = (dst_lon_b[1:] - dst_lon_b[:-1])[:, None]
        with np.errstate(invalid="ignore", divide="ignore"):
            w_lat = lat_overlap / dst_lat_extent
            w_lon = lon_overlap / dst_lon_extent
        w_lat = np.where(np.isfinite(w_lat), w_lat, 0.0)
        w_lon = np.where(np.isfinite(w_lon), w_lon, 0.0)

        x = x_mean.transpose(lat_name_x, lon_name_x).values.astype(np.float64)
        valid = np.isfinite(x)
        x0 = np.where(valid, x, 0.0)
        tmp_num = np.einsum("ij,kj->ik", x0, w_lon, optimize=True)
        num = np.einsum("li,ik->lk", w_lat, tmp_num, optimize=True)
        tmp_den = np.einsum("ij,kj->ik", valid.astype(np.float64), w_lon, optimize=True)
        den = np.einsum("li,ik->lk", w_lat, tmp_den, optimize=True)
        with np.errstate(invalid="ignore", divide="ignore"):
            out = num / den
        out[den <= 0.0] = np.nan

        da_regrid = xr.DataArray(
            out.astype(np.float32),
            dims=("lat", "lon"),
            coords={"lat": target_lat, "lon": target_lon},
            name=mode_name,
            attrs=dict(x_mean.attrs),
        )
        x_fields.append(da_regrid)

        x = y_mean.transpose(lat_name_y, lon_name_y).values.astype(np.float64)
        valid = np.isfinite(x)
        x0 = np.where(valid, x, 0.0)
        tmp_num = np.einsum("ij,kj->ik", x0, w_lon, optimize=True)
        num = np.einsum("li,ik->lk", w_lat, tmp_num, optimize=True)
        tmp_den = np.einsum("ij,kj->ik", valid.astype(np.float64), w_lon, optimize=True)
        den = np.einsum("li,ik->lk", w_lat, tmp_den, optimize=True)
        with np.errstate(invalid="ignore", divide="ignore"):
            out = num / den
        out[den <= 0.0] = np.nan

        da_regrid = xr.DataArray(
            out.astype(np.float32),
            dims=("lat", "lon"),
            coords={"lat": target_lat, "lon": target_lon},
            name=mode_name,
            attrs=dict(y_mean.attrs),
        )
        y_fields.append(da_regrid)

x_hist = xr.concat(x_fields, dim="Mode").assign_coords(Mode=mode_names)
y_future = xr.concat(y_fields, dim="Mode").assign_coords(Mode=mode_names)

# =========================
# HEC 统计
# =========================
valid = np.isfinite(x_hist.values) & np.isfinite(y_future.values)
valid &= np.isfinite(obs_mean.values)[None, :, :] & np.isfinite(obs_sigma.values)[None, :, :]

n = valid.sum(axis=0).astype(np.float64)
x = np.where(valid, x_hist.values.astype(np.float64), np.nan)
y = np.where(valid, y_future.values.astype(np.float64), np.nan)

x_sum = np.nansum(x, axis=0)
y_sum = np.nansum(y, axis=0)
x_mean = np.divide(x_sum, n, out=np.full_like(x_sum, np.nan), where=n > 0)
y_mean = np.divide(y_sum, n, out=np.full_like(y_sum, np.nan), where=n > 0)

sigma_x = np.nanstd(x, axis=0, ddof=1)
std_y = np.nanstd(y, axis=0, ddof=1)
var_x = sigma_x**2
var_y = std_y**2

r = np.full(x_mean.shape, np.nan, dtype=np.float64)
p_value = np.full(x_mean.shape, np.nan, dtype=np.float64)
for lat_idx in range(x_hist.shape[1]):
    for lon_idx in range(x_hist.shape[2]):
        mask = np.isfinite(x[:, lat_idx, lon_idx]) & np.isfinite(y[:, lat_idx, lon_idx])
        if mask.sum() < 3:
            continue
        x_sample = x[:, lat_idx, lon_idx][mask]
        y_sample = y[:, lat_idx, lon_idx][mask]
        if np.nanstd(x_sample, ddof=1) <= 0.0 or np.nanstd(y_sample, ddof=1) <= 0.0:
            continue
        reg_result = cast(Any, linregress(x_sample, y_sample))
        r[lat_idx, lon_idx] = float(reg_result.rvalue)
        p_value[lat_idx, lon_idx] = float(reg_result.pvalue)

valid_core = (n >= 3) & np.isfinite(r) & (var_x > 0) & (var_y > 0)
r = np.where(valid_core, r, np.nan)
p_value = np.where(valid_core, p_value, np.nan)
sigma_x = np.where(valid_core, sigma_x, np.nan)
std_y = np.where(valid_core, std_y, np.nan)
x_mean = np.where(valid_core, x_mean, np.nan)
y_mean = np.where(valid_core, y_mean, np.nan)

obs_mean_2d = np.where(np.isfinite(obs_mean.values), obs_mean.values, np.nan)
obs_sigma_raw_2d = np.where(np.isfinite(obs_sigma.values) & (obs_sigma.values > 0), obs_sigma.values, np.nan)
obs_count_2d = np.where(np.isfinite(obs_count.values) & (obs_count.values > 0), obs_count.values.astype(np.float64), np.nan)
obs_sigma_eff_2d = obs_sigma_raw_2d / np.sqrt(obs_count_2d)
obs_sigma_eff_2d = np.where(np.isfinite(obs_sigma_eff_2d) & (obs_sigma_eff_2d > 0), obs_sigma_eff_2d, np.nan)

with np.errstate(invalid="ignore", divide="ignore"):
    snr = sigma_x**2 / (obs_sigma_eff_2d**2)
    posterior_mean = y_mean + (r * std_y / sigma_x) * (obs_mean_2d - x_mean) / (sigma_x**2 + obs_sigma_eff_2d**2) * sigma_x**2
    posterior_std = np.sqrt((1.0 - r**2 / (1.0 + 1.0 / snr)) * std_y**2)

posterior_mean = np.where(valid_core, posterior_mean, np.nan)
posterior_std = np.where(valid_core, posterior_std, np.nan)
reduction = np.where(valid_core & np.isfinite(std_y) & (std_y > 0), 1.0 - posterior_std / std_y, np.nan)

out = xr.Dataset(
    {
        "r": (("lat", "lon"), r.astype(np.float32)),
        "p_value": (("lat", "lon"), p_value.astype(np.float32)),
        "obs_sigma_raw": (("lat", "lon"), obs_sigma_raw_2d.astype(np.float32)),
        "obs_sigma_effective": (("lat", "lon"), obs_sigma_eff_2d.astype(np.float32)),
        "prior_mean": (("lat", "lon"), y_mean.astype(np.float32)),
        "prior_std": (("lat", "lon"), std_y.astype(np.float32)),
        "posterior_std": (("lat", "lon"), posterior_std.astype(np.float32)),
        "posterior_mean": (("lat", "lon"), posterior_mean.astype(np.float32)),
        "reduction": (("lat", "lon"), reduction.astype(np.float32)),
        "n": (("lat", "lon"), n.astype(np.float32)),
    },
    coords={"lat": obs_mean["lat"].values, "lon": obs_mean["lon"].values},
)
out.attrs["scenario"] = SCENARIO
out.attrs["history_indicator"] = HIST_INDICATOR
out.attrs["future_indicator"] = FUTURE_INDICATOR
out.attrs["history_period"] = f"{HIST_PERIOD_RANGE[0]}-{HIST_PERIOD_RANGE[1]}"
out.attrs["future_period"] = f"{FUTURE_PERIOD_RANGE[0]}-{FUTURE_PERIOD_RANGE[1]}"
# 观测误差项 observational error term：HEC 与传统涌现约束的差别就在于保留它（论文 §2.3 观测层）
out.attrs["observational_error_term"] = "sigma_raw / sqrt(N)"

output_file = DATA_ROOT / f"HEC_{SCENARIO}_{HIST_INDICATOR}_to_{FUTURE_INDICATOR}.nc"
out.to_netcdf(output_file)

print(f"[DONE] HEC 分层涌现约束完成: {SCENARIO}")
print(f"[DONE] 输出数据: {output_file}")
