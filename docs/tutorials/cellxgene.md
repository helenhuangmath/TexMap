# Query CELLxGENE

TexMap connects to the open-science ecosystem by searching the public
[CZ CELLxGENE Discover](https://cellxgene.cziscience.com/) catalog for exhaustion-relevant
datasets and deep-linking each result into the cellxgene Explorer.

## In the explorer

Use the **Query CELLxGENE** panel: type a query (e.g. `CD8 exhaustion melanoma`) and click
**Search Discover**. Each result shows organism / tissue / disease / cell count, an
**Open in CELLxGENE →** link (a dataset's `.cxg` Explorer page when live, or the Discover site as
fallback), and a **Paper** link.

## Programmatically / REST

```python
from texmap import TexMap
TexMap.search_cellxgene("CD8 exhaustion melanoma")
```

```bash
curl "http://127.0.0.1:8000/api/cellxgene/search?q=CD8%20exhaustion%20melanoma"
```

!!! note
    The live CZ Discover API is queried when reachable; offline, a curated catalog of landmark
    CD8-exhaustion studies is returned so the feature always works.

## From discovery to projection

A natural workflow: find a dataset here → download its `.h5ad` from CELLxGENE →
[build a TexMap reference](build-reference.md) from it, or project it as a query.
