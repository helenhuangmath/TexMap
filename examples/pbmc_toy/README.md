# PBMC Toy Example

This folder contains a small runnable TexMap example.

## Toy Input Data

- `counts.csv`: toy query count matrix with cells as rows and genes as columns.
- `metadata.csv`: sample and condition metadata for query cells.
- `metadata.csv` also includes `expected_label` so the benchmark harness can score predictions.
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
expected_outputs/agent/
  request_schema.json
  run_result.json
  interpretation.json
expected_outputs/ml_ready/
  features.csv
  labels.csv
  splits.csv
  manifest.json
expected_outputs/foundation_models/
  adapter_manifest.json
expected_outputs/benchmark/
  predictions.csv
  metrics.json
expected_outputs/scalability/
  projection_plan.json
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
outputs/pbmc_toy/agent/
outputs/pbmc_toy/ml_ready/
outputs/pbmc_toy/foundation_models/
outputs/pbmc_toy/benchmark/
outputs/pbmc_toy/scalability/
outputs/pbmc_toy/web/index.html
```
