from __future__ import annotations

import json
import math
from pathlib import Path

from texmap.config import TexMapConfig
from texmap.io import Matrix, read_counts, read_metadata, read_table, write_table


def append_multimodal_projections(
    config: TexMapConfig,
    paths: dict[str, Path],
    integrated_rows: list[dict[str, object]],
) -> list[dict[str, object]]:
    """Project optional non-scRNA inputs onto the current scRNA/reference map."""
    additions: list[dict[str, object]] = []
    summaries = []

    if config.scatac.enabled and config.scatac.peaks:
        scatac_rows, scatac_summary = project_scatac(config, paths, integrated_rows)
        additions.extend(scatac_rows)
        summaries.append(scatac_summary)

    if config.bulk_rna.enabled and config.bulk_rna.expression:
        bulk_rows, bulk_summary = project_bulk_rna(config, paths, integrated_rows)
        additions.extend(bulk_rows)
        summaries.append(bulk_summary)

    if summaries:
        summary_path = paths["multimodal"] / "projection_summary.json"
        summary_path.write_text(json.dumps({"modalities": summaries}, indent=2) + "\n", encoding="utf-8")

    return integrated_rows + additions


def project_scatac(
    config: TexMapConfig,
    paths: dict[str, Path],
    integrated_rows: list[dict[str, object]],
) -> tuple[list[dict[str, object]], dict[str, object]]:
    peaks = read_counts(config.scatac.peaks, config.scatac.format)
    metadata = read_metadata(config.scatac.metadata)
    links = _read_peak_gene_links(config.scatac.peak_gene_links)
    gene_activity = _peak_counts_to_gene_activity(peaks, links)

    qc_rows = []
    for cell, values in peaks.items():
        row: dict[str, object] = {
            "cell": cell,
            "total_fragments": sum(values.values()),
            "n_accessible_peaks": sum(1 for value in values.values() if value > 0),
            "n_gene_activity_features": len(gene_activity.get(cell, {})),
        }
        row.update(metadata.get(cell, {}))
        qc_rows.append(row)

    genes = sorted({gene for values in gene_activity.values() for gene in values})
    write_table(paths["tables"] / "scatac_qc.csv", qc_rows)
    write_table(paths["tables"] / "scatac_gene_activity.csv", _matrix_to_rows(gene_activity, genes))

    projected = _project_profiles_to_scrna_map(
        profiles=gene_activity,
        source="scATAC_query",
        paths=paths,
        integrated_rows=integrated_rows,
        metadata=metadata,
        method="nearest_scRNA_log_gene_activity",
    )
    write_table(paths["tables"] / "scatac_projection.csv", projected)

    return projected, {
        "modality": "scATAC",
        "input": str(config.scatac.peaks),
        "n_cells": len(peaks),
        "n_gene_activity_features": len(genes),
        "projection_file": "tables/scatac_projection.csv",
        "qc_file": "tables/scatac_qc.csv",
        "method": "Peak counts were collapsed to gene activity with peak_gene_links, then nearest scRNA profiles supplied UMAP coordinates and labels.",
    }


def project_bulk_rna(
    config: TexMapConfig,
    paths: dict[str, Path],
    integrated_rows: list[dict[str, object]],
) -> tuple[list[dict[str, object]], dict[str, object]]:
    expression = read_counts(config.bulk_rna.expression, config.bulk_rna.format)
    metadata = read_metadata(config.bulk_rna.metadata)

    qc_rows = []
    for sample, values in expression.items():
        row: dict[str, object] = {
            "cell": sample,
            "sample": sample,
            "total_expression": sum(values.values()),
            "n_detected_genes": sum(1 for value in values.values() if value > 0),
        }
        row.update(metadata.get(sample, {}))
        qc_rows.append(row)

    genes = sorted({gene for values in expression.values() for gene in values})
    write_table(paths["tables"] / "bulk_rna_qc.csv", qc_rows)

    projected = _project_profiles_to_scrna_map(
        profiles=expression,
        source="bulkRNA_query",
        paths=paths,
        integrated_rows=integrated_rows,
        metadata=metadata,
        method="nearest_scRNA_log_expression",
    )
    write_table(paths["tables"] / "bulk_rna_projection.csv", projected)

    return projected, {
        "modality": "bulkRNA",
        "input": str(config.bulk_rna.expression),
        "n_samples": len(expression),
        "n_genes": len(genes),
        "projection_file": "tables/bulk_rna_projection.csv",
        "qc_file": "tables/bulk_rna_qc.csv",
        "method": "Bulk profiles were log-normalized and projected to the nearest scRNA profiles to place samples on the existing UMAP.",
    }


def _project_profiles_to_scrna_map(
    profiles: Matrix,
    source: str,
    paths: dict[str, Path],
    integrated_rows: list[dict[str, object]],
    metadata: dict[str, dict[str, str]],
    method: str,
) -> list[dict[str, object]]:
    expression_path = paths["tables"] / "normalized_hvg_expression.csv"
    if not expression_path.exists() or not profiles:
        return []

    reference_profiles = _rows_to_matrix(read_table(expression_path))
    reference_profiles = {cell: values for cell, values in reference_profiles.items() if values}
    if not reference_profiles:
        return []

    embedding_by_cell = {
        str(row.get("cell")): row
        for row in integrated_rows
        if str(row.get("source")) == "query"
    }
    normalized_profiles = _normalize(profiles)
    projected = []

    for index, (cell, values) in enumerate(normalized_profiles.items()):
        nearest_cell, distance, shared = _nearest_profile(values, reference_profiles)
        if not nearest_cell:
            continue
        anchor = embedding_by_cell.get(nearest_cell, {})
        if not anchor:
            continue
        jitter_x, jitter_y = _deterministic_jitter(index, source)
        row: dict[str, object] = {
            "cell": cell,
            "UMAP1": _float(anchor.get("UMAP1")) + jitter_x,
            "UMAP2": _float(anchor.get("UMAP2")) + jitter_y,
            "source": source,
            "predicted_label": anchor.get("predicted_label", ""),
            "matched_scRNA_cell": nearest_cell,
            "shared_features": shared,
            "projection_distance": distance,
            "projection_confidence": 1.0 / (1.0 + math.sqrt(distance / max(1, shared))),
            "projection_method": method,
        }
        row.update({key: value for key, value in metadata.get(cell, {}).items() if key not in row})
        projected.append(row)
    return projected


def _read_peak_gene_links(path: Path | None) -> dict[str, str]:
    if path is None or not Path(path).exists():
        return {}
    rows = read_table(path)
    links = {}
    for row in rows:
        keys = list(row.keys())
        if not keys:
            continue
        peak_key = "peak" if "peak" in row else keys[0]
        gene_key = "gene" if "gene" in row else keys[min(1, len(keys) - 1)]
        peak = row.get(peak_key, "")
        gene = row.get(gene_key, "")
        if peak and gene:
            links[peak] = gene
    return links


def _peak_counts_to_gene_activity(peaks: Matrix, links: dict[str, str]) -> Matrix:
    activity: Matrix = {}
    for cell, values in peaks.items():
        row: dict[str, float] = {}
        for peak, value in values.items():
            gene = links.get(peak, peak)
            row[gene] = row.get(gene, 0.0) + value
        activity[cell] = row
    return activity


def _nearest_profile(values: dict[str, float], reference_profiles: Matrix) -> tuple[str | None, float, int]:
    best_cell = None
    best_distance = math.inf
    best_shared = 0
    value_genes = {gene for gene, value in values.items() if value > 0}
    for cell, ref in reference_profiles.items():
        shared = sorted(value_genes.intersection(ref))
        if not shared:
            continue
        distance = sum((values.get(gene, 0.0) - ref.get(gene, 0.0)) ** 2 for gene in shared)
        distance /= len(shared)
        if distance < best_distance:
            best_cell = cell
            best_distance = distance
            best_shared = len(shared)
    return best_cell, best_distance if math.isfinite(best_distance) else 0.0, best_shared


def _normalize(counts: Matrix, target_sum: float = 10_000.0) -> Matrix:
    normalized: Matrix = {}
    for cell, values in counts.items():
        total = sum(values.values()) or 1.0
        normalized[cell] = {gene: math.log1p(value / total * target_sum) for gene, value in values.items()}
    return normalized


def _rows_to_matrix(rows: list[dict[str, str]]) -> Matrix:
    matrix: Matrix = {}
    for row in rows:
        cell = row.get("cell", "")
        matrix[cell] = {key: _float(value) for key, value in row.items() if key != "cell"}
    return matrix


def _matrix_to_rows(matrix: Matrix, columns: list[str]) -> list[dict[str, object]]:
    return [{"cell": cell, **{column: values.get(column, 0.0) for column in columns}} for cell, values in matrix.items()]


def _deterministic_jitter(index: int, source: str) -> tuple[float, float]:
    radius = 0.08 if source == "scATAC_query" else 0.13
    angle = (index * 2.399963229728653) + (0.8 if source == "bulkRNA_query" else 0.0)
    return math.cos(angle) * radius, math.sin(angle) * radius


def _float(value: object) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return 0.0
