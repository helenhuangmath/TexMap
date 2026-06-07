# TexMap

**A universal coordinate system for T-cell exhaustion** — an open-source reference atlas and
computational framework for projection, interpretation, and mechanistic discovery across
single-cell, bulk, multiomic, and cross-species data.

![TexMap explorer](figures/screenshot_explorer.png)

Instead of forcing every dataset into incompatible discrete cluster labels, TexMap places
every cell on continuous, interpretable biological axes — **Exhaustion, Stemness, Terminality,
Cytotoxicity, Proliferation, and a Chromatin-fixation proxy** — and projects any new dataset
into that shared space.

## What you can do

- **Explore** an integrated exhaustion atlas in an interactive, cellxgene-style web app.
- **Project** your own single-cell, bulk, or scATAC data into the shared coordinate system.
- **Recover regulatory networks** (TF→target) grouped into exhaustion programs.
- **Benchmark** cell-state projection accuracy and clinical associations (AUROC, C-index, hazard ratio).
- **Choose integration methods** (scVI, scANVI, scGPT, Harmony, Seurat) with transparent fallback.
- **Query CELLxGENE** Discover for public datasets.
- **Ask a tool-using AI agent** (Gemini / OpenAI) that drives the interface.
- **Script everything** through TexAPI (Python + REST).

## Get started

```bash
pip install -e .
texmap demo
texmap serve --config examples/tex_atlas/config.yaml   # open http://127.0.0.1:8000
```

See [Installation](installation.md), the [Quick start](quickstart.md), and the
[Tutorials](tutorials/index.md).
