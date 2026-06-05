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

## agent/request_schema.json

Machine-readable schema for natural-language and structured agent requests.

## agent/run_result.json

Self-describing, chainable output record for downstream agents or workflow managers.

## agent/interpretation.json

Plain-language interpretation with label counts, top pathway programs, and suggested next steps.

## ml_ready/features.csv

Reference-aligned feature matrix for model training and evaluation.

## ml_ready/labels.csv

Cell labels transferred from the reference map.

## ml_ready/splits.csv

Deterministic train/validation/test split assignments.

## foundation_models/adapter_manifest.json

Contract for optional scGPT, Geneformer, scFoundation, and UCE embedding adapters.

## benchmark/predictions.csv

Per-cell expected versus predicted annotation table when expected labels are available.

## benchmark/metrics.json

Benchmark summary, including exact-match accuracy when `expected_label` is provided in metadata.

## scalability/projection_plan.json

Batching and acceleration plan for out-of-core and GPU-ready projection workflows.

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

HTML report with a cellxgene-like explorer, AI-enabled feature cards, embedded figure panels, QC metrics, pathway score controls, selected-cell CSV download, and links to downloadable static figures/artifacts. The explorer supports zoom, pan, hover tooltips, click-to-inspect cell details, cell search, source/label filters, color-by controls, and pathway overlays. It can be opened directly in a browser and shared with collaborators alongside the output tables and `figures/` folder.
