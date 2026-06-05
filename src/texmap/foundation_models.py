from __future__ import annotations

import json
from pathlib import Path

from texmap.config import TexMapConfig


SUPPORTED_BACKBONES = [
    {
        "name": "scGPT",
        "status": "adapter_stub",
        "role": "Optional embedding backbone for projection into TexMap references.",
        "expected_input": "AnnData or count matrix with gene symbols.",
    },
    {
        "name": "Geneformer",
        "status": "adapter_stub",
        "role": "Optional transformer-derived cell embedding provider.",
        "expected_input": "Tokenized ranked gene expression.",
    },
    {
        "name": "scFoundation",
        "status": "adapter_stub",
        "role": "Optional foundation-model feature extractor.",
        "expected_input": "Normalized expression matrix.",
    },
    {
        "name": "UCE",
        "status": "adapter_stub",
        "role": "Optional universal cell embedding provider.",
        "expected_input": "Species-aware expression matrix.",
    },
]


def write_foundation_model_manifest(config: TexMapConfig, paths: dict[str, Path]) -> Path:
    manifest = {
        "project": config.output.project_name,
        "mode": "consume_existing_foundation_models",
        "default_backbone": "texmap_core_lightweight",
        "supported_backbones": SUPPORTED_BACKBONES,
        "contract": {
            "input": "cell x feature matrix",
            "output": "cell x embedding matrix with stable cell ids",
            "required_columns": ["cell"],
            "recommended_metadata": ["species", "gene_id_space", "model_name", "model_version"],
        },
    }
    out = paths["foundation_models"] / "adapter_manifest.json"
    out.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    return out
