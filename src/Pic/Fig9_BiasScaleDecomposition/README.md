[English](README.md) | [简体中文](README_zh.md)

# Figure 9: Spectral analysis and scale decomposition of constraint adjustments

## Run

Run from the project root:

```bash
conda activate MET
python "src/Pic/Fig9_BiasScaleDecomposition/Fig9.py"
```

## Description

Apply a two-dimensional DCT to the SSP2-4.5 adjustment field, separating three bands at approximately 1409 and 4898 km. National and seven-region statistics use the Chinese land mask. Net adjustments are signed area-weighted means; variance shares divide each band’s regional spatial variance by the sum across three bands. Components below 200 km remain in the small-scale band. With nonzero covariance, shares do not exactly partition the original field’s total variance.

## Inputs

Paths are relative to the project root.

| Data path  |  Role |
|---|---|
| `Output/EC/China/HEC_ssp245_PrecipVar_to_R95mm_intensity.nc`  |  HEC input |
| `Data/China/cnmap.shp`  |  Geographic input |
| `Data/River/HuanghaiRiver_polygon.shp`  |  Geographic input |
| `Data/River/PearlRiver_polygon.shp`  |  Geographic input |
| `Data/River/YangtzeRiver_polygon.shp`  |  Geographic input |

## Outputs

- `src/Pic/Fig9_BiasScaleDecomposition/data/bias_spectrum.csv`
- `src/Pic/Fig9_BiasScaleDecomposition/data/bias_slope.csv`
- `src/Pic/Fig9_BiasScaleDecomposition/data/breakpoint.json`
- `src/Pic/Fig9_BiasScaleDecomposition/data/band_1_le1409_km.npy`
- `src/Pic/Fig9_BiasScaleDecomposition/data/band_2_1409-4898_km.npy`
- `src/Pic/Fig9_BiasScaleDecomposition/data/band_3_ge_4898_km.npy`
- `src/Pic/Fig9_BiasScaleDecomposition/data/scale_variance.csv`
- `src/Pic/Fig9_BiasScaleDecomposition/data/region_band_sign_stats.csv`

Image: `src/Pic/Fig9_BiasScaleDecomposition/Fig9.jpg`.
