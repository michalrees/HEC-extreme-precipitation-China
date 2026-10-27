# Scale-dependent adjustments to near-future extreme precipitation intensity over China under hierarchical emergent constraints

This repository contains the Python analysis and plotting code for the study. Data and figure outputs are distributed separately through Zenodo.

## Data

- Zenodo record: [Processed data and analysis results](https://zenodo.org/records/23682272).
- Reserved DOI: [10.5281/zenodo.23682272](https://doi.org/10.5281/zenodo.23682272).

**Status:** Data upload is in progress. The record has not yet been published, and the reserved DOI will become active upon publication.

The data record includes the data-access guide, file manifest and checksums. Original precipitation inputs are obtained from the providers listed in that guide. Original precipitation inputs are obtained separately from their providers.

## Code

- `src/pipeline/`: regridding, precipitation indices, model merging and hierarchical emergent constraints.
- `src/lib/`: shared precipitation-index calculations.
- `src/Pic/Fig*/FigN.py`: plotting and diagnostics for Figures 1–10.

Extract the corresponding Zenodo archives into the project root to restore their relative paths. The geographic_inputs.zip archive restores the boundary, basin and mountain vectors used by the plotting scripts. The source code alone does not include the data needed to run the analysis or reproduce the maps.

Python dependencies include numpy, pandas, xarray, netCDF4, scipy, matplotlib, cartopy, pyshp, shapely, pyproj, dask, tqdm and rioxarray. Paths and analysis settings are configured in the scripts.
