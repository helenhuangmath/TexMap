# Tutorials

Hands-on guides for every part of TexMap. Each tutorial is self-contained and runs against the
bundled demo atlas, so you can follow along without downloading data.

## Basics

| Tutorial | What you'll learn |
| --- | --- |
| [Getting started](getting-started.md) | Install, launch the explorer, and tour the interface |
| [Project your data](project-your-data.md) | Upload a matrix and map it; the five query modes |
| [Continuous exhaustion axes](continuous-axes.md) | The six Tex axes and how cells are scored |

## Integration & benchmarking

| Tutorial | What you'll learn |
| --- | --- |
| [Integration methods & TexBench](integration-methods.md) | Choose scVI / scANVI / scGPT / Harmony / Seurat; read TexBench |
| [Multiomic & cross-species](multiomic-crossspecies.md) | Map scATAC and bulk RNA; mouse↔human projection |
| [Clinical translation](clinical-translation.md) | AUROC, concordance index, hazard ratio |

## Mechanism & discovery

| Tutorial | What you'll learn |
| --- | --- |
| [Regulatory networks](regulatory-network.md) | Recover and explore TF→target programs (STRING-style) |
| [Query CELLxGENE](cellxgene.md) | Find public exhaustion datasets and open them in cellxgene |
| [TexAgent (AI agent)](texagent.md) | Connect an LLM and let the agent drive analyses |

## Build & integrate

| Tutorial | What you'll learn |
| --- | --- |
| [Build a reference from real data](build-reference.md) | Turn a CSV / `.h5ad` into a TexMap reference |
| [TexAPI (programmatic)](texapi.md) | Use TexMap from Python or over REST |

!!! tip
    Every tutorial assumes a running server (`texmap serve --config examples/tex_atlas/config.yaml`)
    or the package importable on the path (`pip install -e .`).
