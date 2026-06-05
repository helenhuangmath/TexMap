# TexMap Output Schema

This document summarizes the files created by `texmap run`.

## tables/counts_filtered.csv

Filtered count matrix with cells as rows and retained genes as columns.

## tables/cell_qc.csv

Per-cell QC and metadata table.

| Column | Description |
| --- | --- |
| `total_counts` | Sum of counts across retained input genes before filtering. |
| `n_genes` | Number of detected genes per cell. |
| user metadata | Additional columns from the metadata file, joined by cell ID. |

## tables/highly_variable_genes.csv

One-column table listing selected genes.

## tables/normalized_hvg_expression.csv

Log-normalized expression matrix restricted to selected variable genes.

## tables/query_embedding.csv

Two-dimensional query embedding.

| Column | Description |
| --- | --- |
| `PC1` | First query coordinate. |
| `PC2` | Second query coordinate. |

## tables/integrated_embedding.csv

Combined reference and query coordinates for visualization.

| Column | Description |
| --- | --- |
| `UMAP1` | Horizontal map coordinate. |
| `UMAP2` | Vertical map coordinate. |
| `source` | `reference` or `query`. |
| `predicted_label` | Optional nearest-reference label assigned to query cells. |

## tables/pathway_scores.csv

Pathway activity table with cells as rows and pathways as columns.

## figures/integrated_umap.svg

Static SVG graph of reference and query cells in integrated map coordinates.

| Visual element | Description |
| --- | --- |
| green point | Reference cell. |
| red point | Query/input cell. |
| point title | Cell ID or transferred label when available. |

## figures/pathway_heatmap.svg

Static SVG heatmap of pathway scores.

| Visual element | Description |
| --- | --- |
| row | Query/input cell. |
| column | Pathway or gene set. |
| color intensity | Relative pathway score. |

## web/index.html

Self-contained HTML report. It can be opened directly in a browser and shared with collaborators alongside the output tables.
