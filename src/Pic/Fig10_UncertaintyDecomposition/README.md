[English](README.md) | [简体中文](README_zh.md)

# Figure 10: Scale decomposition of prior and posterior uncertainty

## Run

Run from the project root:

```bash
conda activate MET
python "src/Pic/Fig10_UncertaintyDecomposition/Fig10.py"
```

Run Figure 9 first to generate the required input.

## Description

Apply a two-dimensional DCT to the SSP2-4.5 prior and posterior standard-deviation fields using Figure 9 breakpoints, retaining field means. Band-specific reduction is 1 minus the ratio of regional mean absolute posterior to prior reconstructed amplitudes. r_total is the reduction in their sums across the three bands.

## Inputs

Paths are relative to the project root.

| Data path  |  Role |
|---|---|
| `Output/EC/China/HEC_ssp245_PrecipVar_to_R95mm_intensity.nc`  |  HEC input |
| `src/Pic/Fig9_BiasScaleDecomposition/data/breakpoint.json`  |  Input from another figure |
| `Data/China/cnmap.shp`  |  Geographic input |
| `Data/River/HuanghaiRiver_polygon.shp`  |  Geographic input |
| `Data/River/PearlRiver_polygon.shp`  |  Geographic input |
| `Data/River/YangtzeRiver_polygon.shp`  |  Geographic input |

## Outputs

- `src/Pic/Fig10_UncertaintyDecomposition/data/uncertainty_reduction.csv`
- `src/Pic/Fig10_UncertaintyDecomposition/data/uncertainty_spectrum.csv`

Image: `src/Pic/Fig10_UncertaintyDecomposition/Fig10.jpg`.
