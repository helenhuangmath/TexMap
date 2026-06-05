from __future__ import annotations

from pathlib import Path

from texmap.io import Matrix


DEFAULT_PATHWAYS = {
    "T_cell_activation": ["CD3D", "CD3E", "IL7R", "CCR7", "TRAC"],
    "Cytotoxicity": ["NKG7", "GNLY", "GZMB", "PRF1", "IFNG"],
    "Interferon_response": ["ISG15", "IFIT1", "IFIT3", "MX1", "STAT1"],
    "Myeloid_inflammation": ["LYZ", "S100A8", "S100A9", "IL1B", "FCGR3A"],
    "B_cell_program": ["MS4A1", "CD79A", "CD79B", "BANK1", "IGHM"],
}


def load_gene_sets(path: str | Path | None) -> dict[str, list[str]]:
    if path is None:
        return DEFAULT_PATHWAYS

    gene_sets: dict[str, list[str]] = {}
    with Path(path).open("r", encoding="utf-8") as handle:
        for line in handle:
            parts = line.strip().replace(",", "\t").split("\t")
            parts = [part for part in parts if part]
            if len(parts) >= 2:
                gene_sets[parts[0]] = parts[1:]
    return gene_sets or DEFAULT_PATHWAYS


def compute_pathway_scores(expression: Matrix, gene_set_path: str | Path | None = None) -> Matrix:
    gene_sets = load_gene_sets(gene_set_path)
    upper_columns = {gene.upper(): gene for values in expression.values() for gene in values}
    scores: Matrix = {}
    for cell, values in expression.items():
        scores[cell] = {}
        for name, genes in gene_sets.items():
            matched = [upper_columns[gene.upper()] for gene in genes if gene.upper() in upper_columns]
            scores[cell][name] = _mean(values.get(gene, 0.0) for gene in matched) if matched else 0.0
    return scores


def _mean(values) -> float:
    vals = list(values)
    return sum(vals) / len(vals) if vals else 0.0
