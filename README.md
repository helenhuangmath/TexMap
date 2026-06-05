# TexMap

TexMap is an open, extensible toolkit for integrating user single-cell datasets into a reference map, producing interpretable biological summaries, and generating a lightweight web report where users can inspect where their cells land.

The current release is an alpha scaffold designed to be immediately runnable on toy data and straightforward to extend for production-scale scRNA-seq, scATAC-seq, scGPT embeddings, pathway analysis, epigenetic resources, and cross-species mapping.

## What TexMap Does

TexMap is organized around a practical reference-mapping workflow:

1. Harmonize user input data.
2. Run standard single-cell quality control, normalization, feature selection, and embedding.
3. Project or integrate user cells with a reference map.
4. Assign nearest reference labels to query cells.
5. Score pathway or gene-set activity.
6. Write tables and an interactive HTML report.

The command-line interface is stage-based, so each step can be run independently during development or chained end-to-end for routine jobs.

## Current Features

- CSV/TSV count matrix input with cells as rows and genes as columns.
- Optional cell metadata ingestion.
- QC summary tables.
- Normalization and highly variable gene selection.
- Lightweight PCA-based query embedding.
- Reference map overlay when a reference UMAP table is supplied.
- Nearest-reference label transfer.
- Pathway scoring from built-in immune gene sets or user-provided GMT-like TSV files.
- Self-contained HTML report with integrated coordinates, query/reference coloring, QC metrics, and top cells by pathway score.
- Toy PBMC example that runs without heavy single-cell dependencies.

## Planned Extensions

TexMap is intended to grow into a broader community platform. High-priority extension points include:

- `scanpy` and `anndata` loaders for `.h5ad`, 10x Matrix Market, and backed AnnData workflows.
- scGPT/scFoundation embedding adapters for reference-map projection.
- scATAC support with peak-by-cell matrices, gene activity scoring, motif enrichment, and co-embedding with scRNA-seq.
- Epigenetic-resource links to ENCODE, Roadmap Epigenomics, cCREs, motif databases, GWAS loci, and immune enhancer catalogs.
- AI-assisted biological interpretation that summarizes pathway scores, marker genes, and relevant epigenetic annotations.
- Cross-species mapping through ortholog tables, conserved marker programs, and species-aware reference maps.
- A richer web application for filtering, brushing, gene expression overlays, pathway overlays, and epigenetic track inspection.

## Installation

From the repository root:

```bash
python -m pip install -e .
```

For development and tests:

```bash
python -m pip install -e ".[dev]"
```

For future Scanpy-backed analysis workflows:

```bash
python -m pip install -e ".[analysis,web]"
```

## Quick Start

Run the included PBMC toy example:

```bash
texmap run --config examples/pbmc_toy/config.yaml
```

Open the generated report:

```bash
outputs/pbmc_toy/web/index.html
```

You can also run each stage separately:

```bash
texmap prepare --config examples/pbmc_toy/config.yaml
texmap analyze --config examples/pbmc_toy/config.yaml
texmap integrate --config examples/pbmc_toy/config.yaml
texmap pathways --config examples/pbmc_toy/config.yaml
texmap report --config examples/pbmc_toy/config.yaml
```

## Input Format

The simplest input is a count matrix with one row per cell and one column per gene.

Example:

```csv
cell,CD3D,CD3E,NKG7,LYZ,MS4A1
query_T_1,18,16,1,0,0
query_NK_1,1,1,20,0,0
query_Mono_1,0,0,1,16,0
query_B_1,0,0,0,0,18
```

Optional metadata can be supplied as CSV/TSV with the first column named `cell`, `cell_id`, or `barcode`.

Reference embedding files should contain:

```csv
cell,UMAP1,UMAP2
ref_T_1,-4.0,1.2
ref_B_1,4.2,2.2
```

Reference metadata should include the label column named in the config:

```csv
cell,cell_type
ref_T_1,CD4 T cell
ref_B_1,B cell
```

## Configuration

TexMap uses YAML configuration files.

```yaml
input:
  counts: counts.csv
  metadata: metadata.csv
  format: csv

reference:
  embedding: reference_embedding.csv
  metadata: reference_metadata.csv
  label_column: cell_type

analysis:
  min_genes: 1
  min_cells: 1
  normalize_target_sum: 10000
  n_hvg: 2000
  pathway_sets: pathways.tsv

output:
  directory: outputs/my_texmap_run
  project_name: My TexMap analysis
```

Paths are resolved relative to the YAML file.

## Pathway Files

Custom pathway files are tab-delimited or comma-delimited. Each row starts with a pathway name followed by genes:

```tsv
T_cell_activation	CD3D	CD3E	IL7R	CCR7	TRAC
Cytotoxicity	NKG7	GNLY	GZMB	PRF1	IFNG
```

If no pathway file is provided, TexMap uses a small built-in immune-focused set.

## Output Files

A full run writes:

```text
outputs/<run_name>/
  tables/
    counts_filtered.csv
    cell_qc.csv
    highly_variable_genes.csv
    normalized_hvg_expression.csv
    query_embedding.csv
    integrated_embedding.csv
    pathway_scores.csv
  figures/
    integrated_umap.svg
    pathway_heatmap.svg
  logs/
  web/
    index.html
```

### `cell_qc.csv`

Per-cell QC table. Current columns include:

- `total_counts`: total count depth for the cell.
- `n_genes`: number of detected genes.
- Any user metadata columns joined by cell ID.

### `integrated_embedding.csv`

Coordinates used in the web report. Current columns include:

- `UMAP1`, `UMAP2`: reference or query coordinates.
- `source`: `reference` or `query`.
- `predicted_label`: nearest reference label for query cells when reference metadata is supplied.

### `pathway_scores.csv`

Per-cell pathway activity matrix. Rows are query cells and columns are pathway names. Scores are currently simple mean normalized expression across matched genes in each pathway.

### `figures/integrated_umap.svg`

Static SVG graph of the integrated reference map. Reference cells are green and query cells are red. This file is suitable for GitHub previews, slides, and manuscript drafts.

### `figures/pathway_heatmap.svg`

Static SVG heatmap of query-cell pathway activity. Rows are query cells and columns are pathways.

### `web/index.html`

A self-contained browser report showing:

- Query cells overlaid with reference cells.
- QC summary metrics.
- Pathway selector.
- Top query cells ranked by selected pathway activity.
- Transferred nearest-reference labels when available.

## Example Data

The toy PBMC example in `examples/pbmc_toy` contains:

- Eight query cells across T, NK, monocyte, and B-cell-like programs.
- A small reference embedding.
- Reference cell-type labels.
- Immune pathway gene sets.
- Tracked expected figure outputs in `examples/pbmc_toy/expected_outputs/figures`.

It is intentionally small so contributors can verify the full workflow quickly.

Preview files:

- `examples/pbmc_toy/counts.csv`
- `examples/pbmc_toy/config.yaml`
- `examples/pbmc_toy/expected_outputs/figures/integrated_umap.svg`
- `examples/pbmc_toy/expected_outputs/figures/pathway_heatmap.svg`

## Development

Run tests:

```bash
python -m pytest
```

Run the package without installing:

```bash
PYTHONPATH=src python -m texmap.cli run --config examples/pbmc_toy/config.yaml
```

## Community Roadmap Ideas

TexMap can become especially useful to the broader single-cell community by supporting:

- Public reference-map recipes for common tissues and diseases.
- A plugin interface for model-based embeddings, including scGPT, Geneformer, scVI, and scArches.
- Reproducible report bundles that users can share with collaborators.
- Reference confidence scores and out-of-distribution flags.
- Cell-state programs, ligand-receptor inference, and perturbation-response summaries.
- scATAC peak-to-gene linking and motif/pathway interpretation beside scRNA labels.
- Cross-species ortholog mapping with transparent gene losses and many-to-many mappings.
- Local-first reports for protected patient data, with optional cloud deployment.
- Benchmark datasets that compare integration quality, label transfer accuracy, runtime, and memory.

## Repository Status

TexMap is alpha software. The current implementation is a clear, runnable foundation; production biological analysis should validate normalization, integration, label transfer, and pathway choices for the specific dataset and reference map.
