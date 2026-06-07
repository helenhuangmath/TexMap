# Quick start

## 1. Launch the explorer

```bash
texmap demo                                            # build the demo CD8 exhaustion atlas
texmap serve --config examples/tex_atlas/config.yaml   # open http://127.0.0.1:8000
```

`texmap serve` with no `--config` auto-builds and serves the demo atlas.

## 2. In the browser

- **Color by** a continuous axis, metadata, pathway, or an individual **gene**.
- **Project your data** — upload a counts CSV (cells × genes) or click *Use demo query*.
- **Shift-drag** to select a region and read its live state composition.
- Open the **regulatory network**, **TexBench**, and **TexAPI** panels from the top bar.
- Chat with **TexAgent**; connect a model to make it a live tool-using agent.

## 3. Batch pipeline (files on disk)

```bash
texmap run --config examples/tex_atlas/config.yaml
# outputs/tex_atlas/  → tables/, figures/, feature_matrix/, web/index.html
```

## 4. Your own data

```bash
texmap build-reference --counts my_counts.csv --metadata my_meta.csv \
  --label-column cell_type --out examples/my_atlas
texmap serve --config examples/my_atlas/config.yaml
```

Next: work through the [Tutorials](tutorials/index.md).
