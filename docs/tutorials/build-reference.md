# Build a reference from real data

The bundled `examples/tex_atlas` is a synthetic-but-biologically-styled demonstrator. Replace it
with a real reference using `build-reference`.

## From a CSV or .h5ad

```bash
texmap build-reference \
  --counts my_counts.csv \        # cells as rows, genes as columns (or .h5ad)
  --metadata my_meta.csv \        # optional; first column = cell id
  --label-column cell_type \      # metadata column to use as the label
  --out examples/my_atlas

texmap serve --config examples/my_atlas/config.yaml
```

`.h5ad` input requires `anndata` (`pip install anndata`). CSV input needs nothing beyond the core.

## What it produces

| File | Contents |
| --- | --- |
| `reference_embedding.csv` | UMAP-like coords (Terminality × Exhaustion plane) + the six axes |
| `reference_markers.csv` | marker-panel expression (color-by-gene + regulatory recovery) |
| `reference_metadata.csv` | passthrough metadata incl. the label column |
| `tex_pathways.tsv` | default exhaustion programs |
| `config.yaml` | ready to `texmap serve` |

## Tips

- Find a real CD8-exhaustion dataset via the [CELLxGENE tutorial](cellxgene.md), download its
  `.h5ad`, and point `--counts` at it.
- If a label column isn't supplied, TexMap falls back to the derived `tex_state`.
