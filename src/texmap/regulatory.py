"""Regulatory-network recovery (note.txt Module 4/5).

Recovers a transcription-factor -> target gene regulatory network from single-cell
co-expression across the reference atlas, then groups the edges into exhaustion
*regulatory programs* (one per continuous axis). This is a lightweight, dependency-free
GENIE3/SCENIC-style recovery: for each known TF among the marker panel, we score its
co-expression (Pearson r) with every other gene and keep the strongest edges.

Output is a graph (nodes + signed, weighted edges) plus a per-program grouping, suitable
for the gene -> enhancer -> TF -> chromatin-program reasoning the project notes describe
(the enhancer/chromatin layer is added when ATAC / CUT&Tag tracks are linked in).
"""
from __future__ import annotations

import math
from typing import Dict, List, Optional

from texmap.tex_axes import TEX_AXES

# Transcription factors / regulators we treat as potential network drivers.
KNOWN_TFS = {
    "TOX", "TBX21", "PRDM1", "TCF7", "BATF", "EGR2", "NR4A1", "NR4A2", "NR4A3",
    "IKZF2", "DNMT3A", "BACH2", "LEF1", "EOMES", "ID2", "ZEB2",
}


def gene_program(gene: str) -> str:
    """Map a gene to the exhaustion axis (program) whose markers contain it."""
    g = gene.upper()
    for axis, prog in TEX_AXES.items():
        if g in {x.upper() for x in prog.get("up", [])}:
            return axis
    for axis, prog in TEX_AXES.items():
        if g in {x.upper() for x in prog.get("down", [])}:
            return axis
    return "other"


def _pearson(a: List[float], b: List[float]) -> float:
    n = len(a)
    if n < 3:
        return 0.0
    ma = sum(a) / n
    mb = sum(b) / n
    va = sum((x - ma) ** 2 for x in a)
    vb = sum((x - mb) ** 2 for x in b)
    if va <= 0 or vb <= 0:
        return 0.0
    cov = sum((a[i] - ma) * (b[i] - mb) for i in range(n))
    return cov / math.sqrt(va * vb)


def recover_network(
    expr: Dict[str, Dict[str, float]],
    min_abs_r: float = 0.30,
    max_targets_per_tf: int = 8,
) -> dict:
    """Recover a TF->target regulatory network from a cell x gene expression matrix."""
    cells = list(expr.keys())
    if len(cells) < 3:
        return {"nodes": [], "edges": [], "programs": {}, "n_cells": len(cells),
                "method": "insufficient cells"}

    genes = sorted({g for c in cells for g in expr[c]})
    cols = {g: [expr[c].get(g, 0.0) for c in cells] for g in genes}
    tfs = [g for g in genes if g.upper() in KNOWN_TFS]

    edges: List[dict] = []
    degree: Dict[str, int] = {g: 0 for g in genes}
    for tf in tfs:
        cand = []
        for tgt in genes:
            if tgt == tf:
                continue
            r = _pearson(cols[tf], cols[tgt])
            if abs(r) >= min_abs_r:
                cand.append((abs(r), r, tgt))
        cand.sort(reverse=True)
        for _, r, tgt in cand[:max_targets_per_tf]:
            edges.append({
                "source": tf, "target": tgt,
                "r": round(r, 3),
                "sign": "activation" if r > 0 else "repression",
                "program": gene_program(tgt),
            })
            degree[tf] += 1
            degree[tgt] += 1

    used = {g for e in edges for g in (e["source"], e["target"])}
    nodes = [{
        "gene": g, "is_tf": g.upper() in KNOWN_TFS,
        "program": gene_program(g), "degree": degree[g],
    } for g in sorted(used)]

    programs: Dict[str, List[str]] = {}
    for n in nodes:
        programs.setdefault(n["program"], []).append(n["gene"])

    return {
        "n_cells": len(cells),
        "n_tfs": len(tfs),
        "nodes": nodes,
        "edges": edges,
        "programs": programs,
        "method": (f"Pearson co-expression across {len(cells)} reference cells; "
                   f"|r|>={min_abs_r}, top {max_targets_per_tf} targets per TF; "
                   "programs grouped by exhaustion axis."),
    }


def focus(network: dict, gene: str) -> dict:
    """Sub-network around one gene: its regulators (TFs -> gene) and targets (gene -> ...)."""
    g = gene.upper()
    regulators = [e for e in network["edges"] if e["target"].upper() == g]
    targets = [e for e in network["edges"] if e["source"].upper() == g]
    keep = {gene}
    for e in regulators:
        keep.add(e["source"])
    for e in targets:
        keep.add(e["target"])
    nodes = [n for n in network["nodes"] if n["gene"] in keep]
    return {
        "gene": gene,
        "regulators": sorted(regulators, key=lambda e: -abs(e["r"])),
        "targets": sorted(targets, key=lambda e: -abs(e["r"])),
        "nodes": nodes,
        "edges": regulators + targets,
    }
