# Figure 5: Hierarchical emergent-constraint diagnostics

[English](README.md) | [中文](README_zh.md)

## Run

Run from the project root:

```bash
conda activate MET
python "src/Pic/Fig5_EmergentConstraint/Fig5.py"
```

## Description

Plot correlation, uncertainty reduction and posterior-minus-prior adjustments. Statistics use valid input-domain cells with p < 0.05 and r ≥ 0.5 and cosine-of-latitude weights. Reduction is 1 − posterior_std/prior_std; HEC standard deviations use ddof=1.

## Inputs

Paths are relative to the project root.

| Data path  |  Role |
|---|---|
| `Output/EC/China/HEC_ssp126_PrecipVar_to_R95mm_intensity.nc`  |  HEC input |
| `Output/EC/China/HEC_ssp245_PrecipVar_to_R95mm_intensity.nc`  |  HEC input |
| `Output/EC/China/HEC_ssp585_PrecipVar_to_R95mm_intensity.nc`  |  HEC input |
| `Data/China/cnmap.shp`  |  Geographic input |

## Outputs

- `src/Pic/Fig5_EmergentConstraint/data/fig5_stats.csv`

Image: `src/Pic/Fig5_EmergentConstraint/Fig5.jpg`.
