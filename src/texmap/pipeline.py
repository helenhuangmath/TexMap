from __future__ import annotations

import math
from pathlib import Path

from texmap.config import TexMapConfig
from texmap.io import Matrix, ensure_output_dirs, read_counts, read_metadata, read_table, write_table
from texmap.pathways import compute_pathway_scores
from texmap.report import write_report


def prepare(config: TexMapConfig) -> Path:
    paths = ensure_output_dirs(config)
    counts = read_counts(config.input.counts, config.input.format, config.input.gene_column)
    metadata = read_metadata(config.input.metadata)

    qc_rows = []
    keep_cells: list[str] = []
    for cell, values in counts.items():
        total_counts = sum(values.values())
        n_genes = sum(1 for value in values.values() if value > 0)
        row: dict[str, object] = {"cell": cell, "total_counts": total_counts, "n_genes": n_genes}
        row.update(metadata.get(cell, {}))
        qc_rows.append(row)
        if n_genes >= config.analysis.min_genes:
            keep_cells.append(cell)

    genes = sorted({gene for cell in keep_cells for gene, value in counts[cell].items() if value > 0})
    keep_genes = [
        gene for gene in genes
        if sum(1 for cell in keep_cells if counts[cell].get(gene, 0.0) > 0) >= config.analysis.min_cells
    ]
    count_rows = [
        {"cell": cell, **{gene: counts[cell].get(gene, 0.0) for gene in keep_genes}}
        for cell in keep_cells
    ]

    write_table(paths["tables"] / "counts_filtered.csv", count_rows)
    write_table(paths["tables"] / "cell_qc.csv", qc_rows)
    return paths["tables"] / "counts_filtered.csv"


def analyze(config: TexMapConfig) -> Path:
    paths = ensure_output_dirs(config)
    counts_path = paths["tables"] / "counts_filtered.csv"
    counts = _rows_to_matrix(read_table(counts_path)) if counts_path.exists() else read_counts(config.input.counts)

    normalized = _normalize(counts, config.analysis.normalize_target_sum)
    hvg = _top_variable_genes(normalized, config.analysis.n_hvg)
    embedding = _two_axis_embedding(normalized, hvg)

    write_table(paths["tables"] / "query_embedding.csv", embedding)
    write_table(paths["tables"] / "normalized_hvg_expression.csv", _matrix_to_rows(normalized, hvg))
    write_table(paths["tables"] / "highly_variable_genes.csv", [{"gene": gene} for gene in hvg], index_name="gene")
    return paths["tables"] / "query_embedding.csv"


def integrate(config: TexMapConfig) -> Path:
    paths = ensure_output_dirs(config)
    query_rows = read_table(paths["tables"] / "query_embedding.csv")
    query = [
        {"cell": row["cell"], "UMAP1": _float(row["PC1"]), "UMAP2": _float(row["PC2"]), "source": "query"}
        for row in query_rows
    ]

    reference = []
    if config.reference.embedding and Path(config.reference.embedding).exists():
        reference = [
            {"cell": row["cell"], "UMAP1": _float(row["UMAP1"]), "UMAP2": _float(row["UMAP2"]), "source": "reference"}
            for row in read_table(config.reference.embedding)
        ]

    labels = _nearest_reference_labels(query, reference, config)
    combined = reference + [{**row, **labels.get(str(row["cell"]), {})} for row in query]
    write_table(paths["tables"] / "integrated_embedding.csv", combined)
    return paths["tables"] / "integrated_embedding.csv"


def pathways(config: TexMapConfig) -> Path:
    paths = ensure_output_dirs(config)
    expr_path = paths["tables"] / "normalized_hvg_expression.csv"
    expr = _rows_to_matrix(read_table(expr_path)) if expr_path.exists() else read_counts(config.input.counts)
    scores = compute_pathway_scores(expr, config.analysis.pathway_sets)
    write_table(paths["tables"] / "pathway_scores.csv", _matrix_to_rows(scores, sorted(next(iter(scores.values()), {}).keys())))
    return paths["tables"] / "pathway_scores.csv"


def report(config: TexMapConfig) -> Path:
    paths = ensure_output_dirs(config)
    return write_report(config, paths)


def run(config: TexMapConfig) -> Path:
    prepare(config)
    analyze(config)
    integrate(config)
    pathways(config)
    return report(config)


def _normalize(counts: Matrix, target_sum: float) -> Matrix:
    normalized: Matrix = {}
    for cell, values in counts.items():
        total = sum(values.values()) or 1.0
        normalized[cell] = {gene: math.log1p(value / total * target_sum) for gene, value in values.items()}
    return normalized


def _top_variable_genes(matrix: Matrix, n: int) -> list[str]:
    genes = sorted({gene for values in matrix.values() for gene in values})
    variances = []
    for gene in genes:
        vals = [matrix[cell].get(gene, 0.0) for cell in matrix]
        mean = sum(vals) / len(vals) if vals else 0.0
        var = sum((value - mean) ** 2 for value in vals) / len(vals) if vals else 0.0
        variances.append((var, gene))
    variances.sort(reverse=True)
    return [gene for _, gene in variances[: min(n, len(variances))]]


def _two_axis_embedding(matrix: Matrix, genes: list[str]) -> list[dict[str, object]]:
    if not genes:
        return [{"cell": cell, "PC1": 0.0, "PC2": 0.0} for cell in matrix]

    split = max(1, len(genes) // 2)
    first, second = genes[:split], genes[split:] or genes[:split]
    rows = []
    for cell, values in matrix.items():
        pc1 = _mean(values.get(gene, 0.0) for gene in first)
        pc2 = _mean(values.get(gene, 0.0) for gene in second)
        rows.append({"cell": cell, "PC1": pc1, "PC2": pc2})
    return rows


def _nearest_reference_labels(
    query: list[dict[str, object]],
    reference: list[dict[str, object]],
    config: TexMapConfig,
) -> dict[str, dict[str, str]]:
    if not reference or not config.reference.metadata:
        return {}
    metadata_rows = read_table(config.reference.metadata)
    metadata = {row["cell"]: row for row in metadata_rows}
    labels: dict[str, dict[str, str]] = {}
    for query_row in query:
        qx, qy = _float(query_row["UMAP1"]), _float(query_row["UMAP2"])
        nearest = min(
            reference,
            key=lambda ref: (_float(ref["UMAP1"]) - qx) ** 2 + (_float(ref["UMAP2"]) - qy) ** 2,
        )
        ref_cell = str(nearest["cell"])
        label = metadata.get(ref_cell, {}).get(config.reference.label_column, "")
        labels[str(query_row["cell"])] = {"predicted_label": label}
    return labels


def _rows_to_matrix(rows: list[dict[str, str]]) -> Matrix:
    matrix: Matrix = {}
    for row in rows:
        cell = row.get("cell", "")
        matrix[cell] = {key: _float(value) for key, value in row.items() if key != "cell"}
    return matrix


def _matrix_to_rows(matrix: Matrix, columns: list[str]) -> list[dict[str, object]]:
    return [{"cell": cell, **{column: values.get(column, 0.0) for column in columns}} for cell, values in matrix.items()]


def _mean(values) -> float:
    vals = list(values)
    return sum(vals) / len(vals) if vals else 0.0


def _float(value: object) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return 0.0
