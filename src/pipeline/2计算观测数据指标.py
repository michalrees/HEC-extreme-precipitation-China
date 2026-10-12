"""计算多个观测数据的极端降水指标，并按数据源分别输出。

说明：
1. 每个输入观测数据会独立计算 ETCCDI 指标。
2. 百分位类指标使用统一基准期（可配置）。
3. 计算 PrecipVar（变率）。
"""

from __future__ import annotations

from pathlib import Path
from typing import Callable, Dict, List, Optional, Tuple

import numpy as np
import xarray as xr
from tqdm import tqdm
import sys

REPO_ROOT = next(p for p in Path(__file__).resolve().parents if (p / "src").is_dir() and (p / "Doc").is_dir())
sys.path.append(str(REPO_ROOT))
# 公共模块（ETCCDI / precip_variability_netcdf / hec_grid_interpolate）已移至 src/lib/
sys.path.append(str(REPO_ROOT / "src" / "lib"))
import ETCCDI

from precip_variability_netcdf import (
	compute_precip_variability_split,
)


INPUT_FILES: Dict[str, Path] = {
	"CHM_PRE_V2": REPO_ROOT / "Output" / "Obs" / "CHM_PRE_V2_daily_1960-2024_0.25-0.25.nc",
	"CN05": REPO_ROOT / "Output" / "Obs" / "CN05.1_1961-2023_0.25-0.25.nc",
	"CPC": REPO_ROOT / "Output" / "Obs" / "CPC_1979-2025_0.25-0.25.nc",
	"HGCDC": REPO_ROOT / "Output" / "Obs" / "HGCDC_1961-2022_0.25-0.25.nc",
}

OUTPUT_DIR = REPO_ROOT / "Output" / "Obs" / "indices"
OUTPUT_NAME_TEMPLATE = "{source}-OBS-IntensityAndPrecipVar-{start}-{end}.nc"

BASELINE_YEARS: Tuple[int, int] = (1981, 2010)
TARGET_YEARS: Tuple[int, int] = (1961, 2025)
SPLIT_YEAR = 2015

LAT_RANGE: Optional[Tuple[float, float]] = None
LON_RANGE: Optional[Tuple[float, float]] = None


INDICATORS: Dict[str, Callable] = {
	"R90mm_intensity": lambda pr, b: ETCCDI.R90mm_intensity(pr, b, baseline_years=BASELINE_YEARS),
	"R95mm_intensity": lambda pr, b: ETCCDI.R95mm_intensity(pr, b, baseline_years=BASELINE_YEARS),
	"R99mm_intensity": lambda pr, b: ETCCDI.R99mm_intensity(pr, b, baseline_years=BASELINE_YEARS),
}

# 这三个指标都依赖基准期阈值，因此统一走 (pr, baseline) 调用分支。
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
		降水变量名字符串。
	"""
	candidates = ["pr", "pre", "precipitation", "tp", "rain", "prec"]
	lower_map = {str(v).lower(): str(v) for v in ds.data_vars}
	for c in candidates:
		if c in lower_map:
			return lower_map[c]
	raise ValueError(f"未找到降水变量，当前变量: {list(ds.data_vars)}")


def detect_lat_lon_coord_names(ds: xr.Dataset) -> Tuple[str, str]:
	"""识别数据集中的纬度和经度坐标名。

	参数:
		ds: 输入数据集，包含经纬度坐标。

	返回:
		(lat_name, lon_name)，分别为纬度和经度坐标名。
	"""
	coord_map = {str(c).lower(): str(c) for c in ds.coords}

	lat_name = None
	for name in ("lat", "latitude", "y"):
		if name in coord_map:
			lat_name = coord_map[name]
			break

	lon_name = None
	for name in ("lon", "longitude", "x"):
		if name in coord_map:
			lon_name = coord_map[name]
			break

	if lat_name is None or lon_name is None:
		raise ValueError(f"未找到经纬度坐标，当前坐标: {list(ds.coords)}")

	return lat_name, lon_name


def infer_cn05_lat_lon_range(cn05_file: Path) -> Tuple[Tuple[float, float], Tuple[float, float]]:
	"""读取 CN05 文件并推断经纬度范围。

	参数:
		cn05_file: CN05 数据文件路径。

	返回:
		(lat_range, lon_range)，范围格式均为 (min, max)。
	"""
	if not cn05_file.exists():
		raise FileNotFoundError(f"CN05 文件不存在: {cn05_file}")

	ds = xr.open_dataset(cn05_file)
	try:
		lat_name, lon_name = detect_lat_lon_coord_names(ds)
		lat_values = ds[lat_name].values.astype(np.float64)
		lon_values = ds[lon_name].values.astype(np.float64)

		lat_range = (float(np.min(lat_values)), float(np.max(lat_values)))
		lon_range = (float(np.min(lon_values)), float(np.max(lon_values)))
		return lat_range, lon_range
	finally:
		ds.close()


def normalize_spatial_dims(pr: xr.DataArray) -> xr.DataArray:
	"""统一经纬度维度名称为 lat/lon。

	参数:
		pr: 降水数据，可能包含不同命名风格的经纬度维度。

	返回:
		维度标准化后的降水数据。
	"""
	rename_map = {}
	for dim in pr.dims:
		name = str(dim).lower()
		if "lat" in name and dim != "lat":
			rename_map[dim] = "lat"
		elif "lon" in name and dim != "lon":
			rename_map[dim] = "lon"
	if rename_map:
		pr = pr.rename(rename_map)
	return pr


def ensure_ascending_lat_lon(pr: xr.DataArray) -> xr.DataArray:
	"""确保纬度和经度为升序，避免后续切片与计算异常。

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
		pr: 降水数据。
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
	"""按目标年份裁剪，并自动限制到数据可用年份。

	参数:
		pr: 降水数据。
		target_years: 目标年份范围 (start_year, end_year)，包含端点。

	返回:
		按实际可用年份裁剪后的降水数据。
	"""
	years = pr.time.dt.year
	data_start = int(years.min())
	data_end = int(years.max())

	start = max(target_years[0], data_start)
	end = min(target_years[1], data_end)
	if start > end:
		raise ValueError(
			f"目标年份 {target_years[0]}-{target_years[1]} 与数据年份 {data_start}-{data_end} 无交集。"
		)

	return pr.sel(time=slice(f"{start}-01-01", f"{end}-12-31"))


def build_baseline(pr: xr.DataArray, baseline_years: Tuple[int, int]) -> xr.DataArray:
	"""提取百分位指标所需的基准期数据。

	参数:
		pr: 已准备好的降水数据。
		baseline_years: 基准期年份范围 (start_year, end_year)，包含端点。

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
		da: 待处理数据，坐标中可能包含 year 或 time。

	返回:
		year 坐标标准化后的数据。
	"""
	if "year" not in da.coords and "time" in da.coords:
		da = da.rename({"time": "year"})
	if "year" in da.coords and np.issubdtype(da["year"].dtype, np.datetime64):
		da = da.assign_coords(year=da["year"].dt.year.astype("int32"))
	return da


def build_precip_var_dataset(
	pr: xr.DataArray,
	split_year: int,
) -> xr.Dataset:
	"""计算 PrecipVar（仅变率，不计算趋势）。

	参数:
		pr: 输入降水数据，维度需包含 time/lat/lon。
		split_year: 分段年份，< split_year 为历史段，>= split_year 为后段。

	返回:
		仅包含变量 PrecipVar 的数据集，维度为 (year, lat, lon)。
	"""
	pr_name = str(pr.name) if pr.name is not None else "pr"
	ds_for_var = pr.to_dataset(name=pr_name)

	hist_var, hist_years, fut_var, fut_years = compute_precip_variability_split(
		ds_for_var,
		split_year=split_year,
	)

	if len(hist_years) > 0 and len(fut_years) > 0:
		# 历史段与后段都存在时，拼接后统一排序，保证 year 连续可检索。
		all_var = xr.concat([hist_var, fut_var], dim="year")
		all_years = np.concatenate([hist_years, fut_years]).astype(np.int32)
	elif len(hist_years) > 0:
		all_var = hist_var
		all_years = hist_years.astype(np.int32)
	elif len(fut_years) > 0:
		all_var = fut_var
		all_years = fut_years.astype(np.int32)
	else:
		raise RuntimeError("PrecipVar 计算失败：历史段与后段均为空。")

	all_var = all_var.sortby("year")
	precip_var_ds = all_var.to_dataset(name="PrecipVar")

	return precip_var_ds


def compute_obs_indices_for_one(
	source_name: str,
	input_file: Path,
	output_dir: Path,
	baseline_years: Tuple[int, int],
	target_years: Tuple[int, int],
	split_year: int = 2015,
	lat_range: Optional[Tuple[float, float]] = None,
	lon_range: Optional[Tuple[float, float]] = None,
) -> Path:
	"""对单个观测数据源计算全部极端降水指标并合并保存。

	参数:
		source_name: 数据源名称，用于日志和输出命名。
		input_file: 观测数据文件路径。
		output_dir: 输出目录路径。
		baseline_years: 百分位指标基准期 (start_year, end_year)。
		target_years: 目标输出年份范围 (start_year, end_year)。
		split_year: 分段年份，< split_year 为历史段，>= split_year 为后段。
		lat_range: 可选纬度范围 (min_lat, max_lat)，None 表示不裁剪。
		lon_range: 可选经度范围 (min_lon, max_lon)，None 表示不裁剪。

	返回:
		合并后输出文件的完整路径。
	"""
	if not input_file.exists():
		raise FileNotFoundError(f"输入文件不存在: {input_file}")

	ds = xr.open_dataset(input_file)
	try:
		# 统一预处理顺序：变量识别 -> 坐标标准化 -> 可选裁剪 -> 年份裁剪。
		pr_var = detect_precipitation_var(ds)
		pr = normalize_spatial_dims(ds[pr_var])
		pr = ensure_ascending_lat_lon(pr)
		pr = slice_optional_region(pr, lat_range=lat_range, lon_range=lon_range)
		pr = select_target_years(pr, target_years=target_years)
		pr = pr.load()

		baseline = build_baseline(pr, baseline_years=baseline_years)

		results = []
		for ind_name, func in tqdm(INDICATORS.items(), desc=f"计算指标: {source_name}"):
			try:
				if ind_name in BASELINE_REQUIRED_INDICATORS:
					res = func(pr, baseline)
				else:
					res = func(pr)
			except Exception as exc:
				print(f"[WARN] {source_name} 指标 {ind_name} 计算失败，已跳过: {exc}")
				continue

			if res is None:
				print(f"[WARN] {source_name} 指标 {ind_name} 返回 None，已跳过")
				continue

			res = to_int_year(res)
			results.append(res.to_dataset(name=ind_name))

		precip_var_ds = build_precip_var_dataset(
			pr=pr,
			split_year=split_year,
		)
		results.append(precip_var_ds)

		if not results:
			raise RuntimeError(f"{source_name} 没有成功计算的指标，未生成输出文件。")

		combined = xr.merge(results, compat="override", combine_attrs="override", join="outer")
		combined = combined.sortby("year")

		available_years = combined["year"].values.astype(int)
		out_start = int(np.min(available_years))
		out_end = int(np.max(available_years))

		combined.attrs["source"] = source_name
		combined.attrs["source_file"] = str(input_file)
		combined.attrs["baseline_years"] = f"{baseline_years[0]}-{baseline_years[1]}"
		combined.attrs["year_range"] = f"{out_start}-{out_end}"

		output_dir.mkdir(parents=True, exist_ok=True)
		output_file = output_dir / OUTPUT_NAME_TEMPLATE.format(source=source_name, start=out_start, end=out_end)

		encoding = {var: {"zlib": True, "complevel": 4} for var in combined.data_vars}
		# 所有变量统一压缩编码，兼顾体积与 IO 性能。
		combined.to_netcdf(output_file, encoding=encoding)

		print(f"[DONE] 已输出: {output_file}")
		print(f"[INFO] {source_name} 年份范围: {out_start}-{out_end}, 指标数量: {len(combined.data_vars)}")
		return output_file
	finally:
		ds.close()


def compute_all_obs_indices(
	input_files: Dict[str, Path],
	output_dir: Path,
	baseline_years: Tuple[int, int],
	target_years: Tuple[int, int],
	split_year: int,
	lat_range: Optional[Tuple[float, float]] = None,
	lon_range: Optional[Tuple[float, float]] = None,
) -> Dict[str, Path]:
	"""批量计算多个观测数据源指标。

	参数:
		input_files: 数据源到文件路径的映射，键为 source_name，值为文件路径。
		output_dir: 合并指标输出目录。
		baseline_years: 百分位指标基准期 (start_year, end_year)。
		target_years: 目标年份范围 (start_year, end_year)。
		split_year: 分段年份，< split_year 为历史段，>= split_year 为后段。
		lat_range: 可选纬度范围 (min_lat, max_lat)，None 表示不裁剪。
		lon_range: 可选经度范围 (min_lon, max_lon)，None 表示不裁剪。

	返回:
		每个数据源对应的输出文件路径。
	"""
	outputs: Dict[str, Path] = {}

	for source_name, input_file in input_files.items():
		if not input_file.exists():
			print(f"[WARN] 跳过 {source_name}，文件不存在: {input_file}")
			continue

		print(f"\n===== 开始处理 {source_name} =====")
		out_file = compute_obs_indices_for_one(
			source_name=source_name,
			input_file=input_file,
			output_dir=output_dir,
			baseline_years=baseline_years,
			target_years=target_years,
			split_year=split_year,
			lat_range=lat_range,
			lon_range=lon_range,
		)
		outputs[source_name] = out_file

	return outputs


def resolve_input_files(
	source_file_patterns: Dict[str, List[str]],
	obs_dir: Path,
	obs_regrid_dir: Path,
) -> Dict[str, Path]:
	"""根据文件模式自动解析每个数据源的输入文件。

	参数:
		source_file_patterns: 数据源到候选文件模式列表的映射。
		obs_dir: 原始观测数据目录。
		obs_regrid_dir: 重网格后观测数据目录。

	返回:
		解析后的数据源输入文件映射。
	"""
	resolved: Dict[str, Path] = {}
	for source_name, patterns in source_file_patterns.items():
		search_dir = obs_dir if source_name == "CN05" else obs_regrid_dir
		selected: Optional[Path] = None

		for pattern in patterns:
			# 命中多个文件时取排序后的第一个，保证可重复性。
			hits = sorted(search_dir.glob(pattern))
			if hits:
				selected = hits[0]
				break

		if selected is None:
			print(f"[WARN] 未找到 {source_name} 输入文件，搜索目录: {search_dir}, 模式: {patterns}")
			continue

		resolved[source_name] = selected

	return resolved


if __name__ == "__main__":
	input_files = INPUT_FILES

	lat_range = LAT_RANGE
	lon_range = LON_RANGE
	if lat_range is None or lon_range is None:
		cn05_file = input_files.get("CN05")
		if cn05_file is None:
			raise FileNotFoundError("未找到 CN05 输入文件，无法自动推断处理范围。")

		auto_lat_range, auto_lon_range = infer_cn05_lat_lon_range(cn05_file)
		if lat_range is None:
			lat_range = auto_lat_range
		if lon_range is None:
			lon_range = auto_lon_range

	print(
		f"处理范围: lat=[{lat_range[0]:.3f}, {lat_range[1]:.3f}], "
		f"lon=[{lon_range[0]:.3f}, {lon_range[1]:.3f}]"
	)

	output_map = compute_all_obs_indices(
		input_files=input_files,
		output_dir=OUTPUT_DIR,
		baseline_years=BASELINE_YEARS,
		target_years=TARGET_YEARS,
		split_year=SPLIT_YEAR,
		lat_range=lat_range,
		lon_range=lon_range,
	)

	if output_map:
		print("\n全部完成，输出文件如下:")
		for source_name, file_path in output_map.items():
			print(f"- {source_name}: {file_path}")
	else:
		print("\n未生成任何输出文件，请检查输入路径配置。")
