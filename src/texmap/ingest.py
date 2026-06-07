"""Build a TexMap reference atlas from REAL data.

`texmap build-reference` turns a real expression matrix (CSV, or .h5ad if anndata is
installed) into the files the explorer/pipeline need:

    reference_embedding.csv   (UMAP-like coords + continuous Tex axes)
    reference_markers.csv     (marker-panel expression, for color-by-gene + GRN)
    reference_metadata.csv    (passthrough cell metadata incl. the label column)
    tex_pathways.tsv          (default exhaustion programs)
    config.yaml               (ready to `texmap serve`)

This is how you replace the synthetic demo atlas with a real T-cell exhaustion dataset
(e.g. one found via the Query CELLxGENE panel). The 2-D layout is the interpretable
Terminality × Exhaustion plane (plus deterministic spread), which keeps it consistent with
TexMap's axis-space projection.
"""
from __future__ import annotations

import math
import random
from pathlib import Path
from typing import Optional

from texmap.io import Matrix, read_counts, read_metadata, write_table
from texmap.projection import normalize
from texmap.tex_axes import axis_names, marker_expression, marker_panel, score_tex_axes


def _load_counts(counts_path: str) -> Matrix:
    p = Path(counts_path)
    if p.suffix.lower() == ".h5ad":
        return _load_h5ad(p)
    fmt = "tsv" if p.suffix.lower() in {".tsv", ".txt"} else "csv"
    return read_counts(p, fmt)


def _load_h5ad(path: Path) -> Matrix:
    try:
        import anndata  # type: ignore
    except ImportError as exc:  # pragma: no cover - optional dependency
        raise SystemExit("Reading .h5ad requires `pip install anndata`. "
                         "Alternatively export your matrix to CSV (cells as rows).") from exc
    adata = anndata.read_h5ad(path)
    X = adata.X
    genes = list(adata.var_names)
    cells = list(adata.obs_names)
    matrix: Matrix = {}
    dense = X.toarray() if hasattr(X, "toarray") else X
    for i, cell in enumerate(cells):
        row = dense[i]
        matrix[str(cell)] = {genes[j]: float(row[j]) for j in range(len(genes)) if row[j] != 0}
    return matrix


def build_reference(counts_path: str, out_dir: Path,
                    metadata_path: Optional[str] = None,
                    label_column: str = "cell_type",
                    seed: int = 13) -> Path:
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    rng = random.Random(seed)

    counts = _load_counts(counts_path)
    if not counts:
        raise SystemExit("No cells parsed from the counts matrix.")
    normalized = normalize(counts)
    axes = score_tex_axes(normalized)
    metadata = read_metadata(metadata_path) if metadata_path else {}

    names = axis_names()
    embedding_rows = []
    meta_rows = []
    for cell in normalized:
        a = axes[cell]
        u1 = 9.0 * a["Terminality"] - 4.5 + rng.uniform(-0.4, 0.4)
        u2 = 6.0 * a["Exhaustion"] - 3.0 + (2.0 * a["Proliferation"]) + rng.uniform(-0.4, 0.4)
        embedding_rows.append({"cell": cell, "UMAP1": round(u1, 4), "UMAP2": round(u2, 4),
                               **{ax: a[ax] for ax in names}})
        meta = dict(metadata.get(cell, {}))
        meta.setdefault(label_column, a["tex_state"])  # fall back to derived state
        meta.setdefault("tex_state", a["tex_state"])
        meta_rows.append({"cell": cell, **meta})

    write_table(out_dir / "reference_embedding.csv", embedding_rows)
    write_table(out_dir / "reference_metadata.csv", meta_rows)

    panel = marker_panel()
    me = marker_expression(normalized, panel)
    write_table(out_dir / "reference_markers.csv", [{"cell": c, **me[c]} for c in normalized])

    _write_default_pathways(out_dir / "tex_pathways.tsv")
    _write_config(out_dir, label_column)
    return out_dir / "config.yaml"


def _write_default_pathways(path: Path) -> None:
    from texmap.demo import _write_pathways
    _write_pathways(path)


def _write_config(out_dir: Path, label_column: str) -> None:
    cfg = f"""# TexMap reference built from real data via `texmap build-reference`
input:
  counts: reference_embedding.csv   # placeholder; serve only needs the reference
  format: csv

reference:
  embedding: reference_embedding.csv
  metadata: reference_metadata.csv
  label_column: {label_column}

analysis:
  pathway_sets: tex_pathways.tsv

output:
  directory: ../../outputs/custom_reference
  project_name: TexMap custom reference
"""
    (out_dir / "config.yaml").write_text(cfg, encoding="utf-8")
