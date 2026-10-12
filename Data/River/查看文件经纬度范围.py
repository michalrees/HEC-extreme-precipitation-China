from __future__ import annotations

import os
from pathlib import Path

import geopandas as gpd
import matplotlib.pyplot as plt
import numpy as np


# 对缺少 .prj 或 CRS 为空的 shp，可在这里按文件名指定原始坐标系。
CRS_HINTS: dict[str, str] = {
	"HaiheRiver.shp": "EPSG:4547",
	"haiheRiver.shp": "EPSG:4547",
	"HuanghaiRiver_polygon.shp": "EPSG:4326",
	"PearlRiver_polygon.shp": "EPSG:4326",
	"YangtzeRiver_polygon.shp": "EPSG:4326",
}


def read_shp_with_repair(shp_file: Path) -> gpd.GeoDataFrame:
	"""读取 shp，失败时尝试自动恢复 .shx 后重读。

	参数:
		shp_file: shp 文件路径。

	返回:
		读取成功的 GeoDataFrame。
	"""
	try:
		return gpd.read_file(shp_file)
	except Exception as exc:
		os.environ["SHAPE_RESTORE_SHX"] = "YES"
		try:
			print(f"[WARN] 读取失败，尝试 SHAPE_RESTORE_SHX=YES: {shp_file.name}")
			return gpd.read_file(shp_file)
		except Exception:
			raise exc


def read_shp_wgs84(shp_file: Path) -> gpd.GeoDataFrame:
	"""读取单个 shp 并转换到 WGS84。

	参数:
		shp_file: shp 文件路径。

	返回:
		转换到 EPSG:4326 后的 GeoDataFrame。
	"""
	gdf = read_shp_with_repair(shp_file)
	if gdf.empty:
		raise ValueError("图层为空")

	gdf = gdf[gdf.geometry.notna() & (~gdf.geometry.is_empty)].copy()
	if gdf.empty:
		raise ValueError("图层无有效几何")

	if gdf.crs is None:
		hint_crs = CRS_HINTS.get(shp_file.name)
		if hint_crs is None:
			raise ValueError(
				"文件 CRS 缺失。"
				"请在 CRS_HINTS 中配置该文件原始坐标系。"
			)
		gdf = gdf.set_crs(hint_crs)

	gdf = gdf.to_crs("EPSG:4326")
	gdf = gdf[gdf.geometry.notna() & (~gdf.geometry.is_empty)].copy()
	if gdf.empty:
		raise ValueError("转换后无有效几何")

	min_lon, min_lat, max_lon, max_lat = gdf.total_bounds
	if not np.isfinite([min_lon, min_lat, max_lon, max_lat]).all():
		raise ValueError("转换后范围包含 NaN/Inf，可能 CRS 配置不正确")
	if min_lon < -180 or max_lon > 180 or min_lat < -90 or max_lat > 90:
		raise ValueError("转换后范围超出经纬度合法区间，请检查 CRS_HINTS")
	return gdf


def plot_all_shp(shp_dir: Path, save_path: Path | None = None) -> None:
	"""绘制目录下全部 shp 的边界曲线并打印经纬度范围。

	参数:
		shp_dir: 存放 shp 的目录路径。
		save_path: 图像保存路径；为 None 时仅显示不保存。
	"""
	shp_files = sorted(shp_dir.glob("*.shp"))
	if not shp_files:
		raise FileNotFoundError(f"目录下未找到 shp 文件: {shp_dir}")

	layers: list[tuple[str, gpd.GeoDataFrame, float, float, float, float]] = []
	print("=== Shapefile 经纬度范围 (EPSG:4326) ===")
	for shp_file in shp_files:
		try:
			gdf = read_shp_wgs84(shp_file)
			min_lon, min_lat, max_lon, max_lat = [float(v) for v in gdf.total_bounds]
			layers.append((shp_file.name, gdf, min_lon, min_lat, max_lon, max_lat))
			print(
				f"{shp_file.name:<30} "
				f"lon:[{min_lon:.4f}, {max_lon:.4f}] "
				f"lat:[{min_lat:.4f}, {max_lat:.4f}]"
			)
		except Exception as exc:
			print(f"[WARN] 跳过 {shp_file.name}: {exc}")

	if not layers:
		print("[WARN] 没有可绘制的 shp 范围")
		return

	fig, ax = plt.subplots(figsize=(10, 8), dpi=150)
	cmap = plt.get_cmap("tab20")
	color_cycle = [cmap(v) for v in np.linspace(0.0, 1.0, 20)]
	for idx, (name, gdf, min_lon, min_lat, max_lon, max_lat) in enumerate(layers):
		color = color_cycle[idx % len(color_cycle)]
		gdf.boundary.plot(ax=ax, color=color, linewidth=1.6, aspect="auto")
		ax.text(
			min_lon,
			max_lat,
			name,
			fontsize=8,
			va="bottom",
			ha="left",
			color=color,
		)

	min_lon_all = min(item[2] for item in layers)
	min_lat_all = min(item[3] for item in layers)
	max_lon_all = max(item[4] for item in layers)
	max_lat_all = max(item[5] for item in layers)

	lon_pad = max((max_lon_all - min_lon_all) * 0.05, 0.1)
	lat_pad = max((max_lat_all - min_lat_all) * 0.05, 0.1)

	ax.set_xlim(min_lon_all - lon_pad, max_lon_all + lon_pad)
	ax.set_ylim(min_lat_all - lat_pad, max_lat_all + lat_pad)
	ax.set_xlabel("Longitude")
	ax.set_ylabel("Latitude")
	ax.set_title("All Shapefile Boundaries (WGS84)")
	ax.grid(True, linestyle="--", alpha=0.35)
	ax.set_aspect("equal", adjustable="box")

	if save_path is not None:
		save_path.parent.mkdir(parents=True, exist_ok=True)
		fig.savefig(save_path, bbox_inches="tight")
		print(f"\n[DONE] 图已保存: {save_path}")

	plt.show()


if __name__ == "__main__":
	current_dir = Path(__file__).resolve().parent
	output_png = current_dir / "all_shp_bounds.png"
	plot_all_shp(shp_dir=current_dir, save_path=output_png)
