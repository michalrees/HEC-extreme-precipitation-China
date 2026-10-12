# -*- coding: utf-8 -*-
"""
@Author: Haoran Yu
@Desc: 计算单个模式在多个情景下的强度指标与降水变率（PrecipVar）
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path
from typing import Callable, Dict, Optional, Tuple

import numpy as np
import xarray as xr
from tqdm import tqdm


THIS_DIR = Path(__file__).resolve().parent
# 仓库根：向上找到同时含 src/ 与 Doc/ 的目录（本脚本位于 src/pipeline/）
PROJECT_ROOT = next(p for p in Path(__file__).resolve().parents if (p / "src").is_dir() and (p / "Doc").is_dir())
if str(PROJECT_ROOT) not in sys.path:
    sys.path.append(str(PROJECT_ROOT))
# 公共模块（ETCCDI / precip_variability_netcdf / hec_grid_interpolate）位于 src/lib/
LIB_DIR = PROJECT_ROOT / "src" / "lib"
if str(LIB_DIR) not in sys.path:
    sys.path.append(str(LIB_DIR))

import ETCCDI
from precip_variability_netcdf import compute_precip_variability_split


CMIP_PREFIX = "HiCPC_pr"
DEFAULT_MODE = "ACCESS-CM2"
DEFAULT_SCENARIOS = ["ssp126", "ssp245", "ssp585"]

BASELINE_YEARS: Tuple[int, int] = (1981, 2010)
TARGET_YEARS: Tuple[int, int] = (1979, 2100)
SPLIT_YEAR = 2015
LAT_RANGE: Optional[Tuple[float, float]] = (14, 56)
LON_RANGE: Optional[Tuple[float, float]] = (69, 141)

# 数据根目录：src/、Output/、Data/ 现均在论文文件夹内（与 Doc/ 同级）
DATA_ROOT = PROJECT_ROOT / "Data" / "Mode"
OUTPUT_ROOT = PROJECT_ROOT / "Output" / "Mode" / "indices"
OUTPUT_NAME_TEMPLATE = "{mode}-{scenario}-IntensityAndPrecipVar-{start}-{end}.nc"

INDICATORS: Dict[str, Callable] = {
    "R10mm_intensity": ETCCDI.R10mm_intensity,
    "R20mm_intensity": ETCCDI.R20mm_intensity,
    "R25mm_intensity": ETCCDI.R25mm_intensity,
    "R50mm_intensity": ETCCDI.R50mm_intensity,
    "R90mm_intensity": lambda pr, b: ETCCDI.R90mm_intensity(pr, b, baseline_years=BASELINE_YEARS),
    "R95mm_intensity": lambda pr, b: ETCCDI.R95mm_intensity(pr, b, baseline_years=BASELINE_YEARS),
    "R99mm_intensity": lambda pr, b: ETCCDI.R99mm_intensity(pr, b, baseline_years=BASELINE_YEARS),
}

BASELINE_REQUIRED_INDICATORS = {
    "R90mm_intensity",
    "R95mm_intensity",
    "R99mm_intensity",
}


def detect_precipitation_var(ds: xr.Dataset) -> str:
    """识别降水变量名。

    参数:
        ds: 输入数据集，包含候选降水变量。

    返回:
        降水变量名。
    """
    candidates = ["pr", "pre", "precipitation", "tp", "rain", "precip"]
    lower_map = {str(v).lower(): str(v) for v in ds.data_vars}
    for name in candidates:
        if name in lower_map:
            return lower_map[name]
    raise ValueError(f"未找到降水变量，当前变量: {list(ds.data_vars)}")


def normalize_spatial_dims(pr: xr.DataArray) -> xr.DataArray:
    """统一空间维度命名为 lat/lon。

    参数:
        pr: 输入降水数据，维度名可能不是 lat/lon。

    返回:
        维度标准化后的降水数据。
    """
    rename_map = {}
    for dim in pr.dims:
        low = str(dim).lower()
        if "lat" in low and dim != "lat":
            rename_map[dim] = "lat"
        elif "lon" in low and dim != "lon":
            rename_map[dim] = "lon"
    if rename_map:
        pr = pr.rename(rename_map)
    return pr


def ensure_ascending_lat_lon(pr: xr.DataArray) -> xr.DataArray:
    """确保 lat/lon 升序，保证切片与插值行为稳定。

    参数:
        pr: 输入降水数据。

    返回:
        坐标升序后的降水数据。
    """
    if "lat" in pr.coords and pr["lat"].size > 1 and float(pr["lat"][1] - pr["lat"][0]) < 0:
        pr = pr.sortby("lat")
    if "lon" in pr.coords and pr["lon"].size > 1 and float(pr["lon"][1] - pr["lon"][0]) < 0:
        pr = pr.sortby("lon")
    return pr


def slice_optional_region(
    pr: xr.DataArray,
    lat_range: Optional[Tuple[float, float]],
    lon_range: Optional[Tuple[float, float]],
) -> xr.DataArray:
    """按可选经纬度范围裁剪数据。

    参数:
        pr: 输入降水数据。
        lat_range: 纬度范围 (min_lat, max_lat)，None 表示不裁剪。
        lon_range: 经度范围 (min_lon, max_lon)，None 表示不裁剪。

    返回:
        裁剪后的降水数据。
    """
    if lat_range is not None:
        pr = pr.sel(lat=slice(min(lat_range), max(lat_range)))
    if lon_range is not None:
        pr = pr.sel(lon=slice(min(lon_range), max(lon_range)))
    return pr


def select_target_years(pr: xr.DataArray, target_years: Tuple[int, int]) -> xr.DataArray:
    """按照目标年份裁剪数据，并自动与可用年份取交集。

    参数:
        pr: 输入降水数据。
        target_years: 目标年份范围 (start_year, end_year)。

    返回:
        年份裁剪后的降水数据。
    """
    years = pr.time.dt.year
    data_start = int(years.min())
    data_end = int(years.max())

    start_year = max(target_years[0], data_start)
    end_year = min(target_years[1], data_end)
    if start_year > end_year:
        raise ValueError(
            f"目标年份 {target_years[0]}-{target_years[1]} 与数据年份 {data_start}-{data_end} 无交集。"
        )

    return pr.sel(time=slice(f"{start_year}-01-01", f"{end_year}-12-31"))


def build_baseline(pr: xr.DataArray, baseline_years: Tuple[int, int]) -> xr.DataArray:
    """提取百分位强度指标所需的基准期数据。

    参数:
        pr: 输入降水数据。
        baseline_years: 基准期范围 (start_year, end_year)。

    返回:
        基准期降水数据。
    """
    y = pr.time.dt.year
    baseline = pr.where((y >= baseline_years[0]) & (y <= baseline_years[1]), drop=True)
    if baseline.sizes.get("time", 0) == 0:
        raise ValueError(
            f"基准期 {baseline_years[0]}-{baseline_years[1]} 在当前数据中为空，请检查年份设置。"
        )
    return baseline


def to_int_year(da: xr.DataArray) -> xr.DataArray:
    """统一 year 坐标为 int32。

    参数:
        da: 输入数据，可能使用 time 或 datetime64 year。

    返回:
        year 坐标为 int32 的数据。
    """
    if "year" not in da.coords and "time" in da.coords:
        da = da.rename({"time": "year"})
    if "year" in da.coords and np.issubdtype(da["year"].dtype, np.datetime64):
        da = da.assign_coords(year=da["year"].dt.year.astype("int32"))
    return da


def build_precip_var_dataset(pr: xr.DataArray, split_year: int) -> xr.Dataset:
    """计算 PrecipVar 并输出为数据集。

    参数:
        pr: 输入降水数据，维度需包含 time/lat/lon。
        split_year: 分段年份，< split_year 为历史段，>= split_year 为后段。

    返回:
        仅包含变量 PrecipVar 的 xr.Dataset。
    """
    ds_for_var = pr.to_dataset(name=str(pr.name) if pr.name else "pr")
    hist_var, hist_years, fut_var, fut_years = compute_precip_variability_split(
        ds_for_var,
        split_year=split_year,
    )

    if len(hist_years) > 0 and len(fut_years) > 0:
        all_var = xr.concat([hist_var, fut_var], dim="year")
    elif len(hist_years) > 0:
        all_var = hist_var
    elif len(fut_years) > 0:
        all_var = fut_var
    else:
        raise RuntimeError("PrecipVar 计算失败：历史段与后段均为空。")

    all_var = all_var.sortby("year")
    return all_var.to_dataset(name="PrecipVar")


def compute_for_one_scenario(
    mode: str,
    scenario: str,
    baseline_years: Tuple[int, int],
    target_years: Tuple[int, int],
    split_year: int,
    lat_range: Optional[Tuple[float, float]],
    lon_range: Optional[Tuple[float, float]],
) -> Path:
    """计算单个模式单个情景的强度指标和降水变率。

    参数:
        mode: 模式名称。
        scenario: 情景名称，如 ssp126。
        baseline_years: 百分位强度指标基准期 (start_year, end_year)。
        target_years: 目标年份范围 (start_year, end_year)。
        split_year: PrecipVar 分段年份。
        lat_range: 纬度范围 (min_lat, max_lat)，None 表示不裁剪。
        lon_range: 经度范围 (min_lon, max_lon)，None 表示不裁剪。

    返回:
        输出文件路径。
    """
    input_file = DATA_ROOT / mode / f"{CMIP_PREFIX}_{mode}_{scenario}.nc"
    if not input_file.exists():
        raise FileNotFoundError(f"输入文件不存在: {input_file}")

    ds = xr.open_dataset(input_file)
    try:
        pr_var = detect_precipitation_var(ds)
        pr = normalize_spatial_dims(ds[pr_var])
        pr = ensure_ascending_lat_lon(pr)
        pr = slice_optional_region(pr, lat_range=lat_range, lon_range=lon_range)
        pr = select_target_years(pr, target_years=target_years)
        pr = pr.load()

        baseline = build_baseline(pr, baseline_years=baseline_years)
        results = []

        for ind_name, func in tqdm(INDICATORS.items(), desc=f"{mode}-{scenario} 指标"):
            try:
                if ind_name in BASELINE_REQUIRED_INDICATORS:
                    res = func(pr, baseline)
                else:
                    res = func(pr)
            except Exception as exc:
                print(f"[WARN] {mode}-{scenario} 指标 {ind_name} 计算失败，已跳过: {exc}")
                continue

            if res is None:
                print(f"[WARN] {mode}-{scenario} 指标 {ind_name} 返回 None，已跳过")
                continue

            res = to_int_year(res)
            results.append(res.to_dataset(name=ind_name))

        precip_var_ds = build_precip_var_dataset(pr=pr, split_year=split_year)
        results.append(precip_var_ds)

        if not results:
            raise RuntimeError(f"{mode}-{scenario} 没有成功计算的指标，未生成输出文件。")

        combined = xr.merge(results, compat="override", combine_attrs="override", join="outer")
        combined = combined.sortby("year")

        years = combined["year"].values.astype(int)
        out_start = int(np.min(years))
        out_end = int(np.max(years))

        combined.attrs["mode"] = mode
        combined.attrs["scenario"] = scenario
        combined.attrs["source_file"] = str(input_file)
        combined.attrs["baseline_years"] = f"{baseline_years[0]}-{baseline_years[1]}"
        combined.attrs["year_range"] = f"{out_start}-{out_end}"

        output_dir = OUTPUT_ROOT / mode / scenario
        output_dir.mkdir(parents=True, exist_ok=True)
        output_file = output_dir / OUTPUT_NAME_TEMPLATE.format(
            mode=mode,
            scenario=scenario,
            start=out_start,
            end=out_end,
        )

        encoding = {var: {"zlib": True, "complevel": 4} for var in combined.data_vars}
        combined.to_netcdf(output_file, encoding=encoding)

        print(f"[DONE] 已输出: {output_file}")
        return output_file
    finally:
        ds.close()


def parse_args() -> argparse.Namespace:
    """解析命令行参数。

    参数:
        无。

    返回:
        argparse.Namespace，包含 mode 与 scenarios。
    """
    parser = argparse.ArgumentParser(description="计算模式强度指标与降水变率")
    parser.add_argument("--mode", default=DEFAULT_MODE, help="模式名称")
    parser.add_argument(
        "--scenarios",
        nargs="+",
        default=DEFAULT_SCENARIOS,
        help="情景列表，例如: --scenarios ssp126 ssp245 ssp585",
    )
    return parser.parse_args()


def main() -> None:
    """主流程入口。

    参数:
        无。

    返回:
        无。
    """
    args = parse_args()
    mode = args.mode
    scenarios = args.scenarios

    print(f"模式: {mode}")
    print(f"情景: {scenarios}")
    print(f"输入目录: {DATA_ROOT}")
    print(f"输出目录: {OUTPUT_ROOT}")

    failed = []
    for scenario in scenarios:
        print(f"\n===== 开始处理 {mode}-{scenario} =====")
        try:
            compute_for_one_scenario(
                mode=mode,
                scenario=scenario,
                baseline_years=BASELINE_YEARS,
                target_years=TARGET_YEARS,
                split_year=SPLIT_YEAR,
                lat_range=LAT_RANGE,
                lon_range=LON_RANGE,
            )
        except Exception as exc:
            print(f"[ERROR] {mode}-{scenario} 处理失败: {exc}")
            failed.append(scenario)

    if failed:
        print("\n以下情景处理失败:")
        for s in failed:
            print(f"- {s}")
        raise SystemExit(1)

    print("\n全部情景处理完成")


if __name__ == "__main__":
    main()
