# Installation

TexMap's core has **no required dependencies** (Python ≥ 3.9, standard library only).

## Install

```bash
git clone https://github.com/helenhuangmath/TexMap.git
cd TexMap
python -m pip install -e .
```

This makes the `texmap` command available. You can also run without installing by prefixing
commands with `PYTHONPATH=src python -m texmap.cli`.

## Optional extras

| Extra | Adds | Install |
| --- | --- | --- |
| `analysis` | numpy / pandas / scanpy / anndata / scikit-learn | `pip install -e ".[analysis]"` |
| `agent` | reserved for future TexAgent integrations | `pip install -e ".[agent]"` |
| `docs` | MkDocs Material (build this site) | `pip install -e ".[docs]"` |
| `dev` | pytest | `pip install -e ".[dev]"` |

!!! note "AI agent keys"
    TexAgent works offline by default. For a live tool-using agent, set one of
    `GEMINI_API_KEY` (free tier) or `OPENAI_API_KEY` — or connect a key
    from the web UI.

## Verify

```bash
python -m unittest discover -s tests
```
