"""Continuous T-cell exhaustion coordinate scoring.

This is TexMap's core idea (see note.txt): instead of forcing every dataset into
discrete cluster labels (Tpex / Tex-int / Tex-term), we place each cell on a small
set of continuous, interpretable biological axes. These axes are computed from
curated marker programs and are deliberately model-agnostic so they can later be
swapped for foundation-model latent dimensions without changing the rest of the
stack.

Axes (each scaled roughly 0..1 across the input):

* Exhaustion      Memory  <->  Exhaustion   (inhibitory receptor / TOX program)
* Stemness        Differentiated <-> Stem/progenitor (TCF7 / SELL / IL7R)
* Terminality     Plastic <-> Terminal     (terminal effector / co-inhibition load)
* Cytotoxicity    Quiescent <-> Cytotoxic  (GZMB / PRF1 / IFNG)
* Proliferation   Resting <-> Proliferative (MKI67 / TOP2A)
* ChromatinFixation Open <-> Locked         (epigenetic-fixation proxy; refined with ATAC)
"""
from __future__ import annotations

import math
from typing import Dict, List

from texmap.io import Matrix

# Curated, literature-derived marker programs for CD8 T-cell exhaustion biology.
# `up` genes push the score toward 1, `down` genes push it toward 0.
TEX_AXES: Dict[str, Dict[str, List[str]]] = {
    "Exhaustion": {
        "up": ["PDCD1", "HAVCR2", "LAG3", "TIGIT", "CTLA4", "TOX", "ENTPD1", "CD160", "BATF"],
        "down": ["IL7R", "CCR7", "TCF7", "SELL"],
    },
    "Stemness": {
        "up": ["TCF7", "SELL", "IL7R", "CCR7", "BACH2", "LEF1", "SLAMF6"],
        "down": ["GZMB", "HAVCR2", "ENTPD1", "PRDM1"],
    },
    "Terminality": {
        "up": ["GZMB", "PRF1", "HAVCR2", "ENTPD1", "KLRG1", "CX3CR1", "PRDM1", "TBX21"],
        "down": ["TCF7", "SLAMF6", "IL7R"],
    },
    "Cytotoxicity": {
        "up": ["GZMB", "GZMK", "PRF1", "GNLY", "NKG7", "IFNG", "KLRD1"],
        "down": [],
    },
    "Proliferation": {
        "up": ["MKI67", "TOP2A", "PCNA", "BIRC5", "CDK1", "STMN1"],
        "down": [],
    },
    "ChromatinFixation": {
        # RNA proxy for epigenetic fixation; refined when scATAC gene-activity is present.
        "up": ["TOX", "NR4A1", "NR4A2", "NR4A3", "EGR2", "IKZF2", "DNMT3A"],
        "down": ["TCF7", "BACH2"],
    },
}

# Discrete state names derived from axis coordinates, for users who still want a label.
def assign_tex_state(axes: Dict[str, float]) -> str:
    exhaustion = axes.get("Exhaustion", 0.0)
    stemness = axes.get("Stemness", 0.0)
    terminality = axes.get("Terminality", 0.0)
    proliferation = axes.get("Proliferation", 0.0)
    if exhaustion < 0.35:
        if stemness > 0.55:
            return "Naive/Memory"
        return "Effector"
    # exhausted compartment
    if stemness > 0.5 and terminality < 0.5:
        return "Tpex (progenitor exhausted)"
    if proliferation > 0.6 and terminality < 0.6:
        return "Tex-proliferating"
    if terminality > 0.6:
        return "Tex-terminal"
    return "Tex-intermediate"


def _zscore_columns(matrix: Matrix, genes: List[str]) -> Dict[str, Dict[str, float]]:
    """Per-gene z-scores across cells, returned as cell -> gene -> z."""
    cells = list(matrix.keys())
    stats: Dict[str, tuple] = {}
    for gene in genes:
        vals = [matrix[c].get(gene, 0.0) for c in cells]
        mean = sum(vals) / len(vals) if vals else 0.0
        var = sum((v - mean) ** 2 for v in vals) / len(vals) if vals else 0.0
        stats[gene] = (mean, math.sqrt(var) or 1.0)
    out: Dict[str, Dict[str, float]] = {}
    for cell in cells:
        out[cell] = {g: (matrix[cell].get(g, 0.0) - stats[g][0]) / stats[g][1] for g in genes}
    return out


def _resolve(genes: List[str], available_upper: Dict[str, str]) -> List[str]:
    return [available_upper[g.upper()] for g in genes if g.upper() in available_upper]


def score_tex_axes(expression: Matrix) -> Dict[str, Dict[str, float]]:
    """Score every cell on the continuous exhaustion axes.

    `expression` is a (log-)normalized cell x gene matrix. Returns cell -> {axis: score}
    with each axis min-max scaled to 0..1 across the provided cells, plus a derived
    discrete `tex_state` for convenience.
    """
    if not expression:
        return {}
    available_upper = {g.upper(): g for vals in expression.values() for g in vals}
    all_genes = sorted({
        gene
        for axis in TEX_AXES.values()
        for direction in axis.values()
        for gene in _resolve(direction, available_upper)
    })
    z = _zscore_columns(expression, all_genes)

    raw: Dict[str, Dict[str, float]] = {cell: {} for cell in expression}
    for axis_name, programs in TEX_AXES.items():
        up = _resolve(programs["up"], available_upper)
        down = _resolve(programs["down"], available_upper)
        for cell in expression:
            up_score = sum(z[cell][g] for g in up) / len(up) if up else 0.0
            down_score = sum(z[cell][g] for g in down) / len(down) if down else 0.0
            raw[cell][axis_name] = up_score - down_score

    # Min-max scale each axis to 0..1 for interpretable, comparable coordinates.
    scaled: Dict[str, Dict[str, float]] = {cell: {} for cell in expression}
    for axis_name in TEX_AXES:
        vals = [raw[cell][axis_name] for cell in expression]
        lo, hi = min(vals), max(vals)
        span = (hi - lo) or 1.0
        for cell in expression:
            scaled[cell][axis_name] = round((raw[cell][axis_name] - lo) / span, 4)

    for cell in expression:
        scaled[cell]["tex_state"] = assign_tex_state(scaled[cell])
    return scaled


def axis_names() -> List[str]:
    return list(TEX_AXES.keys())


def marker_panel() -> List[str]:
    """Curated CD8-exhaustion marker genes, for cellxgene-style color-by-gene."""
    genes = []
    for axis in TEX_AXES.values():
        for direction in axis.values():
            for g in direction:
                if g not in genes:
                    genes.append(g)
    return sorted(genes)


def marker_expression(normalized: Matrix, genes: List[str]) -> Dict[str, Dict[str, float]]:
    """Extract (rounded) normalized expression for a marker panel, per cell."""
    upper = {g.upper(): g for vals in normalized.values() for g in vals}
    out: Dict[str, Dict[str, float]] = {}
    for cell, vals in normalized.items():
        row = {}
        for g in genes:
            col = upper.get(g.upper())
            row[g] = round(vals.get(col, 0.0), 3) if col else 0.0
        out[cell] = row
    return out
