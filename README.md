# HEC extreme precipitation China

Using hierarchical emergent constraints to reduce the uncertainty in future extreme precipitation projections over China.

This study combines four observational precipitation products with 19 HiCPC models to constrain near-future extreme precipitation intensity over China (2021–2050) using historical precipitation variability (1981–2010). The analysis covers SSP1-2.6, SSP2-4.5, and SSP5-8.5.

## Repository contents

| Path | Contents |
| --- | --- |
| `src/Pic/Fig*/FigN.py` | Plotting scripts for Figures 1–10 |
| `src/Pic/Fig*/FigN.jpg` | Manuscript figures |
| `src/Pic/Fig*/data/` | Compact inputs for each figure: two-dimensional fields, statistical tables, NPZ files, and geographic vectors |
| `src/pipeline/` | Scripts for the complete local analysis workflow |
| `src/lib/` | Shared functions for precipitation indices and related calculations |
| `data.md` | Download links for original datasets |

## Reproducing the figures

Each figure directory includes the inputs needed for its default plotting workflow. There is no need to download the original datasets or run the full analysis first. Install the dependencies and run the corresponding script, for example:

```bash
pip install numpy pandas xarray netCDF4 scipy matplotlib cartopy pyshp shapely pyproj pillow
python src/Pic/Fig1_ObservedProducts/Fig1.py
python src/Pic/Fig2_ModelEvaluation/Fig2.py
python src/Pic/Fig3_ProjectionUncertainty/Fig3.py
```

For the other figures, run `FigN.py` in the corresponding directory. Figure 2 uses full-precision correlation and bias statistics extracted from the historical indices. Figure 3 uses saved ensemble means and standard deviations. Figure 6 uses plotting statistics from the robustness experiments. The remaining figures read the required observational climatologies, constraint fields, and geographic files from their own directories.

## Complete local analysis

Original datasets in `Data/`, full analysis outputs in `Output/`, large evaluation inputs, and robustness calculation caches remain local and are excluded from the repository. Original data sources are listed in [data.md](data.md). To recompute the analysis, run the numbered scripts in `src/pipeline/` locally, then update the compact inputs for each figure. Figure reproduction uses the same statistical definitions as the full analysis. The compact inputs preserve the values needed for plotting without including the complete annual indices or original daily precipitation records.

If Times New Roman is unavailable, Matplotlib substitutes an available font, which may slightly change the appearance of the text.
