"""Reference projection engine.

This is TexMap Module 2 (`texmap.project(data)` in note.txt). It harmonizes an
arbitrary query (single-cell counts, bulk pseudo-profiles, or ATAC gene-activity),
scores it on the continuous Tex axes, and places every cell/sample into the shared
reference coordinate system using k-nearest-neighbour transfer in axis space.

Keeping projection in the interpretable Tex-axis space (rather than raw PCA) is what
makes the same engine work across modalities and species: anything that can be turned
into a cell x gene-ish matrix can be scored and projected.
"""
from __future__ import annotations

import math
from dataclasses import dataclass, field
from typing import Dict, List, Optional

from texmap.io import Matrix
from texmap.pathways import compute_pathway_scores
from texmap.tex_axes import axis_names, marker_expression, marker_panel, score_tex_axes


@dataclass
class ReferenceAtlas:
    """In-memory reference map: UMAP coords + Tex axes + labels per reference cell."""

    cells: List[str]
    coords: Dict[str, tuple]          # cell -> (UMAP1, UMAP2)
    axes: Dict[str, Dict[str, float]]  # cell -> {axis: value}
    labels: Dict[str, str]            # cell -> cell_type / state label
    meta: Dict[str, Dict[str, str]] = field(default_factory=dict)

    @classmethod
    def from_rows(
        cls,
        embedding_rows: List[dict],
        metadata_rows: Optional[List[dict]] = None,
        label_column: str = "cell_type",
    ) -> "ReferenceAtlas":
        meta = {}
        if metadata_rows:
            key = metadata_rows[0].get("cell") and "cell" or list(metadata_rows[0].keys())[0]
            meta = {str(r[key]): {k: v for k, v in r.items() if k != key} for r in metadata_rows}
        cells, coords, axes, labels = [], {}, {}, {}
        names = axis_names()
        for row in embedding_rows:
            cell = str(row.get("cell"))
            cells.append(cell)
            coords[cell] = (_f(row.get("UMAP1")), _f(row.get("UMAP2")))
            axes[cell] = {a: _f(row.get(a)) for a in names if row.get(a) not in (None, "")}
            labels[cell] = str(meta.get(cell, {}).get(label_column) or row.get(label_column) or "reference")
        return cls(cells=cells, coords=coords, axes=axes, labels=labels, meta=meta)

    @property
    def has_axes(self) -> bool:
        return any(self.axes.get(c) for c in self.cells)


def normalize(counts: Matrix, target_sum: float = 10_000.0) -> Matrix:
    out: Matrix = {}
    for cell, vals in counts.items():
        total = sum(vals.values()) or 1.0
        out[cell] = {g: math.log1p(v / total * target_sum) for g, v in vals.items()}
    return out


def _f(value) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return 0.0


def _knn_transfer(query_axes: Dict[str, float], atlas: ReferenceAtlas, k: int = 8):
    """Return (umap1, umap2, predicted_label, confidence, neighbours)."""
    names = axis_names()
    dists = []
    for cell in atlas.cells:
        ra = atlas.axes.get(cell, {})
        d = sum((query_axes.get(a, 0.0) - ra.get(a, 0.0)) ** 2 for a in names)
        dists.append((d, cell))
    dists.sort(key=lambda t: t[0])
    nearest = dists[: max(1, min(k, len(dists)))]

    # Distance-weighted UMAP placement + soft-voted label.
    wsum = x = y = 0.0
    votes: Dict[str, float] = {}
    for d, cell in nearest:
        w = 1.0 / (1.0 + math.sqrt(d))
        cx, cy = atlas.coords[cell]
        x += w * cx
        y += w * cy
        wsum += w
        votes[atlas.labels[cell]] = votes.get(atlas.labels[cell], 0.0) + w
    x /= wsum or 1.0
    y /= wsum or 1.0
    label = max(votes, key=votes.get) if votes else "reference"
    confidence = round(votes.get(label, 0.0) / (wsum or 1.0), 3)
    return x, y, label, confidence, [c for _, c in nearest]


def project(
    counts: Matrix,
    atlas: ReferenceAtlas,
    pathway_sets=None,
    source: str = "query",
    k: int = 8,
) -> Dict[str, object]:
    """Project a query matrix into the reference. Returns a JSON-serialisable dict."""
    normalized = normalize(counts)
    axes = score_tex_axes(normalized)
    pathways = compute_pathway_scores(normalized, pathway_sets)
    panel = marker_panel()
    expr = marker_expression(normalized, panel)

    rows: List[dict] = []
    for cell in normalized:
        cell_axes = {a: axes[cell][a] for a in axis_names()}
        if atlas.has_axes:
            u1, u2, label, conf, neighbours = _knn_transfer(cell_axes, atlas, k=k)
        else:
            u1 = u2 = 0.0
            label, conf, neighbours = "reference", 0.0, []
        row = {
            "cell": cell,
            "UMAP1": round(u1, 4),
            "UMAP2": round(u2, 4),
            "source": source,
            "predicted_label": label,
            "tex_state": axes[cell].get("tex_state", ""),
            "projection_confidence": conf,
            "n_genes": sum(1 for v in counts[cell].values() if v > 0),
            "total_counts": round(sum(counts[cell].values()), 2),
        }
        row.update({a: cell_axes[a] for a in axis_names()})
        row["expr"] = expr.get(cell, {})
        row["_neighbours"] = neighbours
        rows.append(row)

    return {
        "source": source,
        "n_cells": len(rows),
        "axes": axis_names(),
        "markerGenes": panel,
        "cells": rows,
        "pathways": {cell: pathways.get(cell, {}) for cell in normalized},
        "summary": _summary(rows),
    }


def _summary(rows: List[dict]) -> Dict[str, object]:
    if not rows:
        return {}
    state_counts: Dict[str, int] = {}
    for r in rows:
        state_counts[r["tex_state"]] = state_counts.get(r["tex_state"], 0) + 1
    n = len(rows)
    composition = {s: round(100.0 * c / n, 1) for s, c in sorted(state_counts.items(), key=lambda t: -t[1])}
    mean_axes = {
        a: round(sum(r[a] for r in rows) / n, 3)
        for a in axis_names()
    }
    return {
        "composition_percent": composition,
        "mean_axes": mean_axes,
        "mean_confidence": round(sum(r["projection_confidence"] for r in rows) / n, 3),
    }
