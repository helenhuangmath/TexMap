# Getting started

## Launch

```bash
texmap demo
texmap serve --config examples/tex_atlas/config.yaml
```

Open <http://127.0.0.1:8000>. The demo atlas is ~1,200 CD8 T cells across naive/memory →
effector → progenitor-exhausted → terminal states, plus a proliferating branch, across mouse
and human.

## Tour of the interface

- **Top bar** — the `TexMap` wordmark, and the **TexAPI** and **TexBench** buttons.
- **Left sidebar**
    - *Color by* — a continuous axis, cell metadata, or pathway program.
    - *Color by gene* — a dropdown of marker genes (viridis scale).
    - *Filter source* — toggle reference vs. your projected cells.
    - *Project your data* — pick an integration method + query mode, then upload a CSV.
    - *Pathways & programs*, *Regulatory network*, *Benchmarks*, *Query CELLxGENE*.
- **Center** — the interactive UMAP. Wheel to zoom, drag to pan, hover for a tooltip, click a
  cell for details, **Shift-drag** to select a region.
- **Right sidebar** — **TexAgent** chat with a *Connect a model* control.

## Next

- [Project your data](project-your-data.md)
- [Continuous exhaustion axes](continuous-axes.md)
