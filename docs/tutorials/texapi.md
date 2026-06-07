# TexAPI (programmatic)

Use TexMap from other programs — in-process Python, an HTTP client, or raw REST.

## In-process Python

```python
from texmap import TexMap
tm = TexMap.from_config("examples/tex_atlas/config.yaml")

tm.project({"c1": {"PDCD1": 12, "TOX": 8, "TCF7": 0}})   # → coordinates + composition
tm.projection_accuracy()                                  # leave-one-out label recovery
tm.regulators_of("TOX")                                   # TF regulators / targets
tm.clinical_benchmark(cohort, "Stemness")                 # AUROC / C-index / hazard ratio
TexMap.search_cellxgene("CD8 exhaustion melanoma")
```

## HTTP client (talk to a running server)

```python
from texmap import TexAPIClient
api = TexAPIClient("http://127.0.0.1:8000")
api.atlas(); api.accuracy(); api.regulatory(gene="TOX")
api.clinical(predictor="Exhaustion")
api.project_csv(open("counts.csv").read())
api.agent("which programs drive TOX?")
```

## REST endpoints

| Method | Path | Returns |
| --- | --- | --- |
| GET | `/api/atlas` | reference cells: coords, axes, metadata, marker expression |
| GET | `/api/config` | project name, axes, pathways, agent backend |
| POST | `/api/project` | body = counts CSV; headers `X-Method`, `X-Mode` → projection |
| GET | `/api/methods` | integration methods + query modes (with availability) |
| GET | `/api/regulatory?gene=` | regulatory network (or a gene's sub-network) |
| GET | `/api/accuracy` | cell-state projection accuracy |
| GET | `/api/clinical?predictor=` | AUROC / concordance index / hazard ratio |
| GET | `/api/cellxgene/search?q=` | CELLxGENE Discover search |
| GET | `/api/texbench` | TexBench dashboard data |
| POST | `/api/agent` | `{question}` → tool-using agent answer + actions |

```bash
curl "http://127.0.0.1:8000/api/clinical?predictor=Exhaustion"
```

The same REST surface (the **TexAPI**) is documented in-app via the **TexAPI** button.
