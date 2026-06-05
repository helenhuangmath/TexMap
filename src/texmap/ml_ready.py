from __future__ import annotations

import json
from pathlib import Path

from texmap.config import TexMapConfig
from texmap.io import read_table, write_table


def export_ml_ready(config: TexMapConfig, paths: dict[str, Path]) -> list[Path]:
    embedding = read_table(paths["tables"] / "integrated_embedding.csv")
    expression = read_table(paths["tables"] / "normalized_hvg_expression.csv")
    query_embedding = [row for row in embedding if row.get("source") == "query"]
    expr_by_cell = {row["cell"]: row for row in expression}

    features = []
    labels = []
    for row in query_embedding:
        cell = row["cell"]
        feature_row: dict[str, object] = {
            "cell": cell,
            "UMAP1": row.get("UMAP1", ""),
            "UMAP2": row.get("UMAP2", ""),
        }
        feature_row.update({f"expr_{k}": v for k, v in expr_by_cell.get(cell, {}).items() if k != "cell"})
        features.append(feature_row)
        labels.append({"cell": cell, "label": row.get("predicted_label", "")})

    splits = _splits([row["cell"] for row in features])
    split_rows = [{"cell": cell, "split": split} for split, cells in splits.items() for cell in cells]

    feature_path = paths["ml_ready"] / "features.csv"
    label_path = paths["ml_ready"] / "labels.csv"
    split_path = paths["ml_ready"] / "splits.csv"
    manifest_path = paths["ml_ready"] / "manifest.json"
    write_table(feature_path, features)
    write_table(label_path, labels)
    write_table(split_path, split_rows)
    manifest = {
        "project": config.output.project_name,
        "feature_file": "features.csv",
        "label_file": "labels.csv",
        "split_file": "splits.csv",
        "feature_space": "reference_aligned_umap_plus_normalized_hvg_expression",
        "split_policy": "deterministic 60/20/20 by sorted cell id",
        "intended_use": "model training, validation, evaluation, and reference-aligned benchmarking",
    }
    manifest_path.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    return [feature_path, label_path, split_path, manifest_path]


def _splits(cells: list[str]) -> dict[str, list[str]]:
    cells = sorted(cells)
    n = len(cells)
    train_end = max(1, round(n * 0.6)) if n else 0
    val_end = max(train_end, round(n * 0.8))
    return {
        "train": cells[:train_end],
        "val": cells[train_end:val_end],
        "test": cells[val_end:],
    }
