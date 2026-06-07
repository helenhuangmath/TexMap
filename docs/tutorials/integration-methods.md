# Integration methods & TexBench

## Choosing a method

In **Project your data → Integration method**, pick one of:

`scVI` (default) · `scANVI` · `scGPT zero-shot` · `scGPT fine-tune` · `Harmony` · `Seurat` ·
`TexMap axis projection`.

TexMap checks whether each backend library is importable. If the chosen backend is not
installed, it transparently falls back to the dependency-free axis-space engine and reports this
in the result `note`. The axis-space engine performs the actual mapping today; the heavy backends
are adapters that activate when their library is present.

```python
from texmap import integration
integration.methods_payload()["methods"]   # [{key, label, requires, available}, ...]
```

## TexBench

Click **TexBench** (top bar) for a dashboard that aggregates:

- **Cell-state projection accuracy** (leave-one-out kNN label recovery).
- **Clinical metrics** (AUROC and hazard ratio for the Exhaustion axis).
- **Integration-method availability** — which backends are installed.

![TexBench](../figures/screenshot_texbench.png)

```bash
curl http://127.0.0.1:8000/api/texbench
```

See also: [Clinical translation](clinical-translation.md).
