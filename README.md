[English](README.md) | [简体中文](README_zh.md)

# Scale-dependent adjustments to near-future extreme precipitation intensity over China under hierarchical emergent constraints

This repository contains the Python analysis and plotting code for the study. Data and figure outputs are distributed separately through Zenodo.

## Data

- DOI: [10.5281/zenodo.23682272](https://doi.org/10.5281/zenodo.23682272).

The data record includes the data-access guide, file manifest and checksums. Original precipitation inputs are obtained from the providers listed in that guide.

## Code

- `src/pipeline/`: regridding, precipitation indices, model merging and hierarchical emergent constraints.
- `src/lib/`: shared precipitation-index calculations.
- `src/Pic/Fig*/FigN.py`: plotting and diagnostics for Figures 1–10.

Extract the Zenodo archives into the following locations, preserving their internal paths:

| Archive | Extract into |
|---|---|
| `MULTI_MODEL-ssp{126,245,585}-ALL_INDICES_<period>.zip` | `Output/Mode/indices/Scenariomerged/` |
| `MULTI_MODEL-historical-1981-2010_<period>.zip` | `src/Pic/Fig2_ModelEvaluation/data/` |
| `FigN_<name>.zip` | `src/Pic/` |
| `observation_indices.zip`, `hec_outputs.zip`, `geographic_inputs.zip` | Project root |

Before running scripts that read combined model data, concatenate each scenario's annual files along `year` into `MULTI_MODEL-<scenario>-ALL_INDICES.nc`, and the historical-evaluation files into `MULTI_MODEL-historical-1981-2010.nc`, in their respective directories. Restore the historical files' `year` coordinates from the filenames before concatenation. `geographic_inputs.zip` contains the boundary, basin and mountain vectors used by the plotting scripts.

Python dependencies include numpy, pandas, xarray, netCDF4, scipy, matplotlib, cartopy, pyshp, shapely, pyproj, dask, tqdm and rioxarray. Paths and analysis settings are configured in the scripts.
