"""按情景合并模式数据。"""

from __future__ import annotations

import re
from pathlib import Path
from typing import Dict, List, Tuple

import xarray as xr


REPO_ROOT = next(p for p in Path(__file__).resolve().parents if (p / "src").is_dir() and (p / "Doc").is_dir())
INPUT_ROOT = REPO_ROOT / "Output" / "Mode" / "indices"
OUTPUT_ROOT = REPO_ROOT / "Output" / "Mode" / "indices" / "Scenariomerged"

# 合并 ssp126、ssp245、ssp585。
INCLUDE_SCENARIOS = {"ssp126", "ssp245", "ssp585"}

FILE_PATTERN = re.compile(
	r"^(?P<model>.+)-(?P<scenario>ssp\d+)-IntensityAndPrecipVar-(?P<start>\d{4})-(?P<end>\d{4})\.nc$"
)


def parse_file_name(file_name: str) -> Tuple[str, str]:
	"""解析模式文件名中的模式名和情景名。

	参数:
		file_name: 文件名，示例：ACCESS-CM2-ssp126-IntensityAndPrecipVar-1979-2100.nc。

	返回:
		(model, scenario)。
	"""
	match = FILE_PATTERN.match(file_name)
	if not match:
		raise ValueError(f"文件名不符合预期格式: {file_name}")
	return match.group("model"), match.group("scenario")


def collect_files_by_scenario(input_root: Path) -> Dict[str, List[Path]]:
	"""按情景收集待合并的模式文件。

	参数:
		input_root: 模式数据根目录，通常为 Output/Mode/indices。

	返回:
		字典，key 为情景名，value 为该情景下的文件列表。
	"""
	if not input_root.exists():
		raise FileNotFoundError(f"输入目录不存在: {input_root}")

	groups: Dict[str, List[Path]] = {}
	for nc_file in sorted(input_root.glob("**/*.nc")):
		try:
			_, scenario = parse_file_name(nc_file.name)
		except ValueError:
			print(f"[WARN] 跳过命名不匹配文件: {nc_file}")
			continue

		if scenario not in INCLUDE_SCENARIOS:
			print(f"[SKIP] 排除情景 {scenario}: {nc_file.name}")
			continue

		groups.setdefault(scenario, []).append(nc_file)

	return groups


def merge_one_scenario(files: List[Path], scenario: str, output_root: Path) -> Path:
	"""将一个情景下多个模式的文件合并，并新增 Mode 维度。

	参数:
		files: 同一情景对应的所有模式文件路径。
		scenario: 情景名，例如 ssp126。
		output_root: 输出目录。

	返回:
		生成的 netCDF 文件路径。
	"""
	mode_datasets: List[xr.Dataset] = []
	for fp in sorted(files):
		model, _ = parse_file_name(fp.name)
		with xr.open_dataset(fp) as ds_in:
			ds = ds_in.load().expand_dims(Mode=[model])
		mode_datasets.append(ds)

	if not mode_datasets:
		raise ValueError(f"情景 {scenario} 没有可合并文件")

	merged = xr.concat(
		mode_datasets,
		dim="Mode",
		join="outer",
		compat="override",
		coords="minimal",
		combine_attrs="override",
	)
	merged = merged.sortby("Mode")
	merged.attrs["scenario"] = scenario
	merged.attrs["note"] = "Merged across models from batch outputs; added Mode dimension"

	output_root.mkdir(parents=True, exist_ok=True)
	save_path = output_root / f"MULTI_MODEL-{scenario}-ALL_INDICES.nc"
	encoding = {var: {"zlib": True, "complevel": 4} for var in merged.data_vars}
	merged.to_netcdf(save_path, encoding=encoding)
	return save_path


def main() -> None:
	"""主流程：按情景合并多个模式的提取结果文件。"""
	groups = collect_files_by_scenario(INPUT_ROOT)
	if not groups:
		print("[INFO] 未找到可合并的模式文件")
		return

	ok_count = 0
	for scenario, files in sorted(groups.items()):
		try:
			out_path = merge_one_scenario(files, scenario, OUTPUT_ROOT)
			ok_count += 1
			print(f"[OK] {scenario} -> {out_path}")
		except Exception as exc:
			print(f"[WARN] 跳过 {scenario}: {exc}")

	print(f"[DONE] 完成，成功生成 {ok_count}/{len(groups)} 个情景合并文件")


if __name__ == "__main__":
	main()
