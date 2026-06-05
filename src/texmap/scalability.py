from __future__ import annotations

import json
from pathlib import Path

from texmap.config import TexMapConfig
from texmap.io import read_table


def write_scalability_plan(config: TexMapConfig, paths: dict[str, Path]) -> Path:
    qc = read_table(paths["tables"] / "cell_qc.csv")
    n_cells = len(qc)
    plan = {
        "project": config.output.project_name,
        "observed_cells": n_cells,
        "execution_mode": "single_process_core" if n_cells < 100_000 else "batch_projection_recommended",
        "planned_acceleration": [
            "chunked out-of-core count loading",
            "GPU embedding backbones when optional foundation-model adapters are enabled",
            "batched nearest-neighbor projection",
            "streaming report/table writers for million-cell cohorts",
        ],
        "batching_recommendation": {
            "target_cells_per_chunk": 100_000,
            "preserve_cell_order": True,
            "merge_outputs_by": "cell",
        },
    }
    out = paths["scalability"] / "projection_plan.json"
    out.write_text(json.dumps(plan, indent=2) + "\n", encoding="utf-8")
    return out
