[English](README.md) | [简体中文](README_zh.md)

# Figure 2: Historical model evaluation

## Run

Run from the project root:

```bash
conda activate MET
python "src/Pic/Fig2_ModelEvaluation/Fig2.py"
```

## Description

Evaluate spatial correlation and bias for 19 models during 1981–2010. Model fields are remapped to the observational grid using area weights. Correlations use cosine-of-latitude weights; bias is observation minus model.

## Inputs

Paths are relative to the project root.

| Data path  |  Role |
|---|---|
| `src/Pic/Fig2_ModelEvaluation/data/MULTI_MODEL-historical-1981-2010.nc`  |  Historical input |
| `src/Pic/Fig2_ModelEvaluation/data/CN05-OBS-1981-2010.nc`  |  Historical input |
| `Data/China/cnmap.shp`  |  Geographic input |

## Outputs

- `src/Pic/Fig2_ModelEvaluation/data/fig2a_stats.csv`
- `src/Pic/Fig2_ModelEvaluation/data/fig2_per_model.csv`
- `src/Pic/Fig2_ModelEvaluation/data/fig2b_stats.csv`

Image: `src/Pic/Fig2_ModelEvaluation/Fig2.jpg`.
