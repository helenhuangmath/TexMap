from __future__ import annotations

import json
from pathlib import Path

from texmap.config import TexMapConfig
from texmap.io import read_table


def write_agent_outputs(config: TexMapConfig, paths: dict[str, Path]) -> list[Path]:
    schema = {
        "name": "TexMap agentic annotation request",
        "version": "0.1.0",
        "natural_language_examples": [
            "Annotate these cells and compare to terminal Tex.",
            "Project my query sample into the exhaustion reference and summarize out-of-reference cells.",
            "Export the reference-aligned feature matrix and run the benchmark scoring harness.",
        ],
        "orchestrated_steps": [
            "harmonize_input",
            "project_to_reference",
            "transfer_annotations",
            "score_pathways",
            "export_feature_matrix",
            "score_benchmark",
            "summarize_interpretation",
        ],
        "structured_request": {
            "task": "annotate_and_compare",
            "reference_state": "terminal Tex",
            "return": ["tables", "figures", "web_report", "json_summary"],
        },
    }
    result = {
        "project": config.output.project_name,
        "status": "complete",
        "request": schema["structured_request"],
        "outputs": {
            "web_report": "web/index.html",
            "integrated_embedding": "tables/integrated_embedding.csv",
            "pathway_scores": "tables/pathway_scores.csv",
            "feature_matrix_manifest": "feature_matrix/manifest.json",
            "benchmark_metrics": "benchmark/metrics.json",
        },
        "chainable_result": {
            "format": "texmap.result.v0",
            "primary_key": "cell",
            "coordinate_columns": ["UMAP1", "UMAP2"],
            "annotation_column": "predicted_label",
        },
    }
    paths["agent"].mkdir(parents=True, exist_ok=True)
    schema_path = paths["agent"] / "request_schema.json"
    result_path = paths["agent"] / "run_result.json"
    _write_json(schema_path, schema)
    _write_json(result_path, result)
    return [schema_path, result_path]


def write_interpretation(config: TexMapConfig, paths: dict[str, Path]) -> Path:
    embedding = read_table(paths["tables"] / "integrated_embedding.csv")
    pathways = read_table(paths["tables"] / "pathway_scores.csv")
    query = [row for row in embedding if row.get("source") == "query"]
    label_counts: dict[str, int] = {}
    for row in query:
        label = row.get("predicted_label") or "unassigned"
        label_counts[label] = label_counts.get(label, 0) + 1

    top_pathways = _top_pathways(pathways)
    dominant_label = max(label_counts, key=label_counts.get) if label_counts else "unassigned"
    summary = {
        "project": config.output.project_name,
        "plain_language_summary": (
            f"Most query cells map nearest to {dominant_label}. "
            f"The strongest pathway programs are {', '.join(top_pathways[:3]) or 'not available'}. "
            "Cells without confident reference matches should be reviewed as potential novel or transitional states."
        ),
        "label_counts": label_counts,
        "top_pathways": top_pathways,
        "suggested_next_steps": [
            "Review query cells with low pathway specificity or missing nearest-reference labels.",
            "Compare terminal Tex, memory, effector, and naive marker programs in the figure gallery.",
            "Use the feature-matrix export for downstream model training or independent validation.",
        ],
    }
    out = paths["agent"] / "interpretation.json"
    _write_json(out, summary)
    return out


def _top_pathways(rows: list[dict[str, str]]) -> list[str]:
    totals: dict[str, float] = {}
    for row in rows:
        for key, value in row.items():
            if key == "cell":
                continue
            totals[key] = totals.get(key, 0.0) + _float(value)
    return [name for name, _ in sorted(totals.items(), key=lambda item: item[1], reverse=True)]


def _float(value: object) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return 0.0


def _write_json(path: Path, payload: dict[str, object]) -> None:
    path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
