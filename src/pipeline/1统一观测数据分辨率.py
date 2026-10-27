"""统一观测降水数据到 CN05.1 网格。

处理规则：
1. 目标网格固定为 CN05.1_1961-2023.nc 的 lat/lon（位置与间隔不变）。
2. CPC_1979-2025.nc（0.5°较粗）使用双线性插值细化到 CN05 网格。
3. CHM_PRE_V2_daily_1960-2024.nc 与 HGCDC_1961-2022.nc（约0.1°较细）
   使用面积加权平均聚合到 CN05 网格。
"""

from __future__ import annotations
from pathlib import Path
from typing import Iterable
import numpy as np
import xarray as xr


REPO_ROOT = next(p for p in Path(__file__).resolve().parents if (p / "src").is_dir() and (p / "Doc").is_dir())

# ---- 数据根目录 ----------------
DATA_ROOT = REPO_ROOT / "Data"
OBS_DIR = DATA_ROOT / "Obs"
TARGET_FILE = OBS_DIR / "CN05.1_1961-2023.nc"
OUTPUT_DIR = REPO_ROOT / "Output" / "Obs" / "Regridded"

INPUT_RULES = {
    "CPC_1979-2025.nc": "bilinear",
    "CHM_PRE_V2_daily_1960-2024.nc": "area_weighted",
    "HGCDC_1961-2022.nc": "area_weighted",
}


def _find_coord_name(ds: xr.Dataset, candidates: Iterable[str]) -> str:
    """根据候选名在数据集中查找坐标名。

    参数:
        ds: 输入的 xarray Dataset。
        candidates: 候选坐标名列表（忽略大小写）。

    返回:
        匹配到的真实坐标名。
    """
    lower_map = {str(name).lower(): str(name) for name in ds.coords}
    for name in candidates:
        if name.lower() in lower_map:
            return lower_map[name.lower()]
    raise ValueError(f"未找到坐标 {list(candidates)}，现有坐标为 {list(ds.coords)}")


def _ensure_ascending(ds: xr.Dataset, lat_name: str, lon_name: str) -> xr.Dataset:
    """确保纬度和经度坐标升序排列。

    参数:
        ds: 输入数据集。
        lat_name: 纬度坐标名。
        lon_name: 经度坐标名。

    返回:
        坐标升序后的数据集。
    """
    if ds[lat_name].size > 1 and float(ds[lat_name][1] - ds[lat_name][0]) < 0:
        ds = ds.sortby(lat_name)
    if ds[lon_name].size > 1 and float(ds[lon_name][1] - ds[lon_name][0]) < 0:
        ds = ds.sortby(lon_name)
    return ds


def _lon_to_180(ds: xr.Dataset, lon_name: str) -> xr.Dataset:
    """将经度从 [0, 360) 转到 [-180, 180)，并按经度排序。

    参数:
        ds: 输入数据集。
        lon_name: 经度坐标名。

    返回:
        经度转换后的数据集。
    """
    lon = ds[lon_name]
    if float(lon.max()) > 180.0:
        lon_new = ((lon + 180.0) % 360.0) - 180.0
        ds = ds.assign_coords({lon_name: lon_new}).sortby(lon_name)
    return ds


def _infer_bounds_from_centers(centers: np.ndarray) -> np.ndarray:
    """从规则网格中心点推断网格边界。

    参数:
        centers: 一维网格中心点数组，要求升序。

    返回:
        一维边界数组，长度为 len(centers)+1。
    """
    if centers.ndim != 1:
        raise ValueError("centers 必须是一维数组")
    if centers.size < 2:
        raise ValueError("至少需要两个中心点来推断边界")

    deltas = np.diff(centers)
    edges = np.empty(centers.size + 1, dtype=np.float64)
    edges[1:-1] = 0.5 * (centers[:-1] + centers[1:])
    edges[0] = centers[0] - 0.5 * deltas[0]
    edges[-1] = centers[-1] + 0.5 * deltas[-1]
    return edges


def _overlap_matrix(src_edges: np.ndarray, dst_edges: np.ndarray) -> np.ndarray:
    """计算目标网格与源网格的一维重叠长度矩阵。

    参数:
        src_edges: 源网格边界（一维，升序）。
        dst_edges: 目标网格边界（一维，升序）。

    返回:
        形状为 (n_dst, n_src) 的重叠长度矩阵。
    """
    src_l = src_edges[:-1][None, :]
    src_r = src_edges[1:][None, :]
    dst_l = dst_edges[:-1][:, None]
    dst_r = dst_edges[1:][:, None]
    return np.maximum(0.0, np.minimum(src_r, dst_r) - np.maximum(src_l, dst_l))


def _build_area_weights(
    src_lat: np.ndarray,
    src_lon: np.ndarray,
    dst_lat: np.ndarray,
    dst_lon: np.ndarray,
) -> tuple[np.ndarray, np.ndarray]:
    """构建面积加权重映射所需的纬向/经向权重矩阵。

    参数:
        src_lat: 源纬度中心点（升序）。
        src_lon: 源经度中心点（升序）。
        dst_lat: 目标纬度中心点（升序）。
        dst_lon: 目标经度中心点（升序）。

    返回:
        (w_lat, w_lon)
        - w_lat 形状 (n_dst_lat, n_src_lat)，按球面纬向面积比例归一。
        - w_lon 形状 (n_dst_lon, n_src_lon)，按经向长度比例归一。
    """
    src_lat_b = _infer_bounds_from_centers(src_lat)
    src_lon_b = _infer_bounds_from_centers(src_lon)
    dst_lat_b = _infer_bounds_from_centers(dst_lat)
    dst_lon_b = _infer_bounds_from_centers(dst_lon)

    src_lat_b_sin = np.sin(np.deg2rad(src_lat_b))
    dst_lat_b_sin = np.sin(np.deg2rad(dst_lat_b))

    lat_overlap = _overlap_matrix(src_lat_b_sin, dst_lat_b_sin)
    lon_overlap = _overlap_matrix(src_lon_b, dst_lon_b)

    dst_lat_extent = (dst_lat_b_sin[1:] - dst_lat_b_sin[:-1])[:, None]
    dst_lon_extent = (dst_lon_b[1:] - dst_lon_b[:-1])[:, None]

    with np.errstate(invalid="ignore", divide="ignore"):
        w_lat = lat_overlap / dst_lat_extent
        w_lon = lon_overlap / dst_lon_extent

    w_lat = np.where(np.isfinite(w_lat), w_lat, 0.0)
    w_lon = np.where(np.isfinite(w_lon), w_lon, 0.0)
    return w_lat.astype(np.float64), w_lon.astype(np.float64)


def _subset_to_target_extent(
    ds: xr.Dataset,
    lat_name: str,
    lon_name: str,
    target_lat: np.ndarray,
    target_lon: np.ndarray,
) -> xr.Dataset:
    """按目标网格经纬度范围裁剪源数据。

    参数:
        ds: 待裁剪的源数据集。
        lat_name: 源数据集中纬度坐标名。
        lon_name: 源数据集中经度坐标名。
        target_lat: 目标网格纬度数组（用于确定最小/最大纬度）。
        target_lon: 目标网格经度数组（用于确定最小/最大经度）。

    返回:
        仅保留目标经纬度范围后的数据集。
    """
    lat_min = float(np.min(target_lat))
    lat_max = float(np.max(target_lat))
    lon_min = float(np.min(target_lon))
    lon_max = float(np.max(target_lon))

    ds_sub = ds.sel(
        {
            lat_name: slice(lat_min, lat_max),
            lon_name: slice(lon_min, lon_max),
        }
    )

    if ds_sub.sizes.get(lat_name, 0) == 0 or ds_sub.sizes.get(lon_name, 0) == 0:
        raise ValueError(
            "源数据与 CN05.1 目标范围无重叠，无法继续重网格。"
        )

    return ds_sub


def _area_weighted_regrid(
    da: xr.DataArray,
    src_lat_name: str,
    src_lon_name: str,
    dst_lat: np.ndarray,
    dst_lon: np.ndarray,
) -> xr.DataArray:
    """把二维经纬网格数据面积加权重映射到目标网格。

    参数:
        da: 输入数据变量（必须含有源纬度和源经度维）。
        src_lat_name: 输入数据的纬度维名。
        src_lon_name: 输入数据的经度维名。
        dst_lat: 目标纬度坐标值（一维升序）。
        dst_lon: 目标经度坐标值（一维升序）。

    返回:
        重映射后的 DataArray，输出纬度维名为 lat，经度维名为 lon。
    """
    src_lat = da[src_lat_name].values.astype(np.float64)
    src_lon = da[src_lon_name].values.astype(np.float64)
    w_lat, w_lon = _build_area_weights(src_lat, src_lon, dst_lat, dst_lon)

    out_lat_dim = "_out_lat"
    out_lon_dim = "_out_lon"

    def _block_func(x: np.ndarray) -> np.ndarray:
        x = x.astype(np.float64, copy=False)
        valid = np.isfinite(x)
        x0 = np.where(valid, x, 0.0)

        tmp_num = np.einsum("...ij,kj->...ik", x0, w_lon, optimize=True)
        num = np.einsum("li,...ik->...lk", w_lat, tmp_num, optimize=True)

        tmp_den = np.einsum("...ij,kj->...ik", valid.astype(np.float64), w_lon, optimize=True)
        den = np.einsum("li,...ik->...lk", w_lat, tmp_den, optimize=True)

        with np.errstate(invalid="ignore", divide="ignore"):
            out = num / den
        out[den <= 0.0] = np.nan
        return out.astype(np.float32)

    # 对 core 维度(lat/lon)合并为单块，避免 apply_ufunc(dask='parallelized') 报错。
    if getattr(da.data, "chunks", None) is not None:
        da = da.chunk({src_lat_name: -1, src_lon_name: -1})

    out = xr.apply_ufunc(
        _block_func,
        da,
        input_core_dims=[[src_lat_name, src_lon_name]],
        output_core_dims=[[out_lat_dim, out_lon_dim]],
        output_dtypes=[np.float32],
        dask="parallelized",
        dask_gufunc_kwargs={
            "output_sizes": {out_lat_dim: dst_lat.size, out_lon_dim: dst_lon.size},
            "allow_rechunk": True,
        },
    )

    out = out.rename({out_lat_dim: "lat", out_lon_dim: "lon"})
    out = out.assign_coords(lat=dst_lat, lon=dst_lon)
    return out


def _to_target_grid(
    src_file: Path,
    method: str,
    target_lat: np.ndarray,
    target_lon: np.ndarray,
) -> xr.Dataset:
    """把单个输入文件重映射到目标网格。

    参数:
        src_file: 输入 NetCDF 文件路径。
        method: 重映射方法，支持 "bilinear" 或 "area_weighted"。
        target_lat: 目标纬度数组（来自 CN05.1）。
        target_lon: 目标经度数组（来自 CN05.1）。

    返回:
        重映射后的 Dataset。
    """
    ds = xr.open_dataset(src_file, chunks={"time": 120})

    lat_name = _find_coord_name(ds, ["lat", "latitude", "y"])
    lon_name = _find_coord_name(ds, ["lon", "longitude", "x"])
    data_var = list(ds.data_vars)[0]

    ds = _lon_to_180(ds, lon_name)
    ds = _ensure_ascending(ds, lat_name, lon_name)
    ds = _subset_to_target_extent(ds, lat_name, lon_name, target_lat, target_lon)

    da = ds[data_var]

    def _regrid_single(da_part: xr.DataArray) -> xr.DataArray:
        """对单个时间片段执行重网格，并统一坐标名为 lat/lon。"""
        if method == "bilinear":
            part = da_part.interp(
                {lat_name: target_lat, lon_name: target_lon},
                method="linear",
            )
            rename_map = {}
            if lat_name != "lat":
                rename_map[lat_name] = "lat"
            if lon_name != "lon":
                rename_map[lon_name] = "lon"
            if rename_map:
                part = part.rename(rename_map)
            return part

        if method == "area_weighted":
            return _area_weighted_regrid(
                da=da_part,
                src_lat_name=lat_name,
                src_lon_name=lon_name,
                dst_lat=target_lat,
                dst_lon=target_lon,
            )

        raise ValueError(f"不支持的方法: {method}")

    if "time" in da.dims:
        years = np.unique(da["time"].dt.year.values.astype(np.int32))
        regridded_years: list[xr.DataArray] = []
        total_years = int(years.size)

        for idx, year in enumerate(years, start=1):
            da_year = da.sel(time=da["time"].dt.year == int(year))
            regridded_years.append(_regrid_single(da_year))
            print(f"  年度进度: {int(year)} ({idx}/{total_years}) 完成")

        out_da = xr.concat(regridded_years, dim="time").sortby("time")
    else:
        out_da = _regrid_single(da)

    out_da = out_da.assign_coords(lat=target_lat, lon=target_lon)
    # 统一输出变量名和单位
    out_da.name = "pr"
    out_da.attrs.update(da.attrs)
    out_da.attrs["units"] = "mm/day"
    out_ds = out_da.to_dataset(name="pr")
    for old_name, new_name in (("longitude", "lon"), ("latitude", "lat")):
        if old_name in out_ds.coords:
            out_ds = out_ds.rename({old_name: new_name})
    out_ds.attrs.update(ds.attrs)
    out_ds.attrs["regridded_to"] = "CN05.1_1961-2023.nc"
    out_ds.attrs["regrid_method"] = method
    return out_ds


def main() -> None:
    """执行观测文件统一网格流程。"""
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    target_ds = xr.open_dataset(TARGET_FILE)
    target_lat_name = _find_coord_name(target_ds, ["lat", "latitude", "y"])
    target_lon_name = _find_coord_name(target_ds, ["lon", "longitude", "x"])
    target_lat = target_ds[target_lat_name].values.astype(np.float64)
    target_lon = target_ds[target_lon_name].values.astype(np.float64)

    if target_lat.size > 1 and target_lat[1] < target_lat[0]:
        target_lat = target_lat[::-1]
    if target_lon.size > 1 and target_lon[1] < target_lon[0]:
        target_lon = target_lon[::-1]

    print(f"目标网格: lat={target_lat.size}, lon={target_lon.size}")
    print(
        f"CN05范围: lat=[{float(target_lat.min()):.3f}, {float(target_lat.max()):.3f}], "
        f"lon=[{float(target_lon.min()):.3f}, {float(target_lon.max()):.3f}]"
    )

    for filename, method in INPUT_RULES.items():
        src_file = OBS_DIR / filename
        out_file = OUTPUT_DIR / f"{src_file.stem}_0.25-0.25.nc"

        print(f"\n处理: {src_file.name} | 方法: {method}")
        out_ds = _to_target_grid(
            src_file=src_file,
            method=method,
            target_lat=target_lat,
            target_lon=target_lon,
        )

        encoding = {
            var: {"zlib": True, "complevel": 4, "dtype": "float32"}
            for var in out_ds.data_vars
        }
        out_ds.to_netcdf(out_file, encoding=encoding)
        out_ds.close()
        print(f"输出: {out_file}")

    target_ds.close()
    print("\n完成: 所有指定观测文件已统一到 CN05 网格。")


if __name__ == "__main__":
    main()
