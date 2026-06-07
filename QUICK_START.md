# TexMap Quick Start

TexMap is a software package that runs an interactive web app on your machine for exploring a T-cell exhaustion reference atlas, projecting your own data into a continuous exhaustion coordinate system, and running regulatory-network and clinical-translation analyses.

## 1. Install (or run without installing)

From the repository root:

```bash
python -m pip install -e .         # then the `texmap` command is available
```

Everything also runs with no install via the module entry point — prefix commands with
`PYTHONPATH=src python -m texmap.cli` instead of `texmap`. TexMap's core has **no required
dependencies** (Python standard library only).

## 2. Launch the interactive explorer

```bash
texmap demo                                            # build the demo CD8 exhaustion atlas
texmap serve --config examples/tex_atlas/config.yaml   # then open http://127.0.0.1:8000
```

`texmap serve` with no `--config` auto-builds and serves the demo atlas. In the browser you can:

- Pan/zoom the atlas; **Color by** a continuous exhaustion axis, cell metadata, pathway, or
  an individual **gene** (cellxgene-style, viridis scale).
- **Project your data**: upload a counts CSV (cells as rows, genes as columns), or click
  "Use demo query" — your cells land on the map with a state-composition breakdown.
- **Shift-drag** to select a region and read its live state composition.
- Open the **regulatory network** graph (TF→target edges grouped into programs).
- Run **Benchmarks**: cell-state projection accuracy, and clinical translation
  (AUROC / concordance index / hazard ratio).
- **Query CELLxGENE** Discover for public exhaustion datasets and open them in cellxgene.
- Chat with **TexAgent** (see §5).

## 3. Run the batch pipeline (files on disk)

For reproducible tables/figures and a static HTML report, no browser needed:

```bash
texmap run --config examples/tex_atlas/config.yaml
```

Key outputs under `outputs/tex_atlas/`:

```text
tables/tex_axes.csv              continuous exhaustion coordinates per cell
tables/integrated_embedding.csv  atlas + query coords, labels, axes (scRNA, scATAC, bulk)
tables/pathway_scores.csv        program activity per cell
tables/scatac_projection.csv     multiomic (scATAC gene-activity) projected onto the map
tables/bulk_rna_projection.csv   bulk RNA projected onto the map
figures/*.svg                    static UMAP + pathway heatmap
web/index.html                   self-contained static report
```

## 4. Use your own / real Tex data

Build a reference atlas from a **real** expression matrix (CSV with cells as rows, or `.h5ad`
if `anndata` is installed — e.g. a CD8-exhaustion dataset found via the Query CELLxGENE panel):

```bash
texmap build-reference --counts my_counts.csv --metadata my_meta.csv \
  --label-column cell_type --out examples/my_atlas
texmap serve --config examples/my_atlas/config.yaml
```

This scores the Tex axes, builds the layout + marker panel, and writes a ready-to-serve
reference. (The bundled `examples/tex_atlas` is synthetic-but-biologically-styled so the app
runs instantly; replace it with real data this way.)

## 5. Real-time AI agent (Gemini / OpenAI)

TexAgent works offline (grounded rule-based) by default. For real LLM answers, set ONE key
before `texmap serve` — Google Gemini has a free tier:

```bash
export GEMINI_API_KEY=...     # free key: https://aistudio.google.com/apikey
# or OPENAI_API_KEY=...
```

Force a provider with `TEXMAP_AGENT_PROVIDER=google|openai`.

## 6. Programmatic use (TexAPI)

In-process Python:

```python
from texmap import TexMap
tm = TexMap.from_config("examples/tex_atlas/config.yaml")
res = tm.project({"cell1": {"PDCD1": 12, "TOX": 8, "TCF7": 0}})
print(res["summary"]["composition_percent"])
tm.projection_accuracy(); tm.regulators_of("TOX"); tm.clinical_benchmark(cohort, "Stemness")
```

Or hit a running server from any program (the REST "TexAPI"):

```python
from texmap import TexAPIClient
api = TexAPIClient("http://127.0.0.1:8000")
api.cellxgene_search("CD8 exhaustion melanoma")
api.clinical(predictor="Exhaustion")
```

## 7. Individual pipeline stages

```bash
texmap prepare  --config examples/tex_atlas/config.yaml
texmap analyze  --config examples/tex_atlas/config.yaml
texmap integrate --config examples/tex_atlas/config.yaml
texmap pathways --config examples/tex_atlas/config.yaml
texmap ai       --config examples/tex_atlas/config.yaml
texmap report   --config examples/tex_atlas/config.yaml
```

## 8. Tests

```bash
python -m unittest discover -s tests
```
