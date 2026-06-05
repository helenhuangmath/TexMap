# PBMC Toy Example

This folder contains a small runnable TexMap example.

## Toy Input Data

- `counts.csv`: toy query count matrix with cells as rows and genes as columns.
- `metadata.csv`: sample and condition metadata for query cells.
- `reference_embedding.csv`: small reference map coordinates.
- `reference_metadata.csv`: reference cell-type labels.
- `pathways.tsv`: immune pathway gene sets.
- `config.yaml`: TexMap configuration for this example.

## Expected Figure Outputs

Example graph outputs are tracked in:

```text
expected_outputs/figures/
  integrated_umap.svg
  pathway_heatmap.svg
expected_outputs/web/
  index.html
```

Regenerate them with:

```bash
env PYTHONPATH=src python -m texmap.cli run --config examples/pbmc_toy/config.yaml
```

Fresh outputs will be written to:

```text
outputs/pbmc_toy/figures/
outputs/pbmc_toy/web/index.html
```
