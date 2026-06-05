from __future__ import annotations

import json
from pathlib import Path

from texmap.config import TexMapConfig
from texmap.io import read_metadata, read_table, write_table


def score_benchmark(config: TexMapConfig, paths: dict[str, Path]) -> Path:
    embedding = read_table(paths["tables"] / "integrated_embedding.csv")
    metadata = read_metadata(config.input.metadata)
    rows = []
    correct = 0
    evaluated = 0
    for row in embedding:
        if row.get("source") != "query":
            continue
        cell = row["cell"]
        expected = metadata.get(cell, {}).get("expected_label", "")
        predicted = row.get("predicted_label", "")
        is_correct = bool(expected) and expected == predicted
        if expected:
            evaluated += 1
            correct += int(is_correct)
        rows.append({"cell": cell, "expected_label": expected, "predicted_label": predicted, "correct": is_correct})

    table_path = paths["benchmark"] / "predictions.csv"
    metrics_path = paths["benchmark"] / "metrics.json"
    write_table(table_path, rows)
    metrics = {
        "project": config.output.project_name,
        "task": "exhaustion_state_annotation",
        "n_evaluated": evaluated,
        "accuracy": correct / evaluated if evaluated else None,
        "scoring_harness": "exact label match when expected_label is present in metadata",
        "prediction_file": "predictions.csv",
    }
    metrics_path.write_text(json.dumps(metrics, indent=2) + "\n", encoding="utf-8")
    return metrics_path
