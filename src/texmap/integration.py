"""Integration engine: selectable methods and query modes.

Users pick an integration **method** (scVI is the default) and a **query mode**. The methods
are registered with the heavy library they need; TexMap detects whether that library is
installed and, if not, transparently falls back to its dependency-free axis-space projection
adapter (and says so). The always-available ``texmap_axis`` engine performs the actual
reference mapping today; the scVI/scANVI/scGPT/Harmony/Seurat entries are adapters that
report availability and are wired to call the real backend when present (roadmap).

Methods:  scVI (default) | scANVI | scGPT zero-shot | scGPT fine-tune | Harmony | Seurat
Modes:    integrate_all | project_query | label_transfer | nearest_tex_states | compare_conditions
"""
from __future__ import annotations

import importlib.util
from typing import Dict, List, Optional

from texmap.io import Matrix
from texmap.projection import ReferenceAtlas, normalize, project
from texmap.tex_axes import axis_names, score_tex_axes

# method key -> (label, required python module for the real backend)
METHODS = [
    {"key": "scVI", "label": "scVI", "requires": "scvi", "default": True},
    {"key": "scANVI", "label": "scANVI (label-aware)", "requires": "scvi"},
    {"key": "scgpt_zeroshot", "label": "scGPT zero-shot", "requires": "scgpt"},
    {"key": "scgpt_finetune", "label": "scGPT fine-tune", "requires": "scgpt"},
    {"key": "harmony", "label": "Harmony", "requires": "harmonypy"},
    {"key": "seurat", "label": "Seurat (R)", "requires": "rpy2"},
    {"key": "texmap_axis", "label": "TexMap axis projection", "requires": None},
]
DEFAULT_METHOD = "scVI"

QUERY_MODES = [
    {"key": "project_query", "label": "Project new query to TexAtlas", "default": True},
    {"key": "integrate_all", "label": "Integrate all datasets"},
    {"key": "label_transfer", "label": "Label transfer"},
    {"key": "nearest_tex_states", "label": "Find nearest Tex states"},
    {"key": "compare_conditions", "label": "Compare conditions"},
]
DEFAULT_MODE = "project_query"


def _available(requires: Optional[str]) -> bool:
    if requires is None:
        return True
    return importlib.util.find_spec(requires) is not None


def methods_payload() -> dict:
    methods = [{**m, "available": _available(m["requires"])} for m in METHODS]
    return {
        "methods": methods,
        "modes": QUERY_MODES,
        "default_method": DEFAULT_METHOD,
        "default_mode": DEFAULT_MODE,
    }


def _resolve_method(method: str) -> dict:
    for m in METHODS:
        if m["key"] == method:
            available = _available(m["requires"])
            if available and m["key"] != "texmap_axis":
                # real backend present — adapter would call it here; we use the axis engine
                return {"method_used": m["key"], "engine": "texmap-axis-projection-adapter",
                        "backend_available": True,
                        "note": f"{m['label']} backend detected; using TexMap axis-space adapter."}
            if not available:
                return {"method_used": "texmap_axis", "engine": "texmap-axis-projection",
                        "backend_available": False, "requested": m["key"],
                        "note": f"{m['label']} not installed (`pip install {m['requires']}`); "
                                f"fell back to TexMap axis-space projection."}
            return {"method_used": "texmap_axis", "engine": "texmap-axis-projection",
                    "backend_available": True, "note": "TexMap axis-space projection."}
    return {"method_used": "texmap_axis", "engine": "texmap-axis-projection",
            "backend_available": True, "note": f"Unknown method '{method}'; used TexMap axis projection."}


def run(mode: str, method: str, counts: Matrix, atlas: ReferenceAtlas,
        pathway_sets=None, k: int = 8) -> dict:
    meta = _resolve_method(method or DEFAULT_METHOD)
    proj = project(counts, atlas, pathway_sets, source="query", k=k)
    result = {"mode": mode, **meta, **proj}

    if mode == "integrate_all":
        result["integrated"] = _integrate_all(proj, atlas)
    elif mode == "label_transfer":
        result["label_transfer"] = [{"cell": c["cell"], "predicted_label": c["predicted_label"],
                                     "confidence": c["projection_confidence"]} for c in proj["cells"]]
    elif mode == "nearest_tex_states":
        result["nearest"] = _nearest_states(proj, atlas)
    elif mode == "compare_conditions":
        result["comparison"] = _compare_to_atlas(proj, atlas)
    # project_query: the base projection is the answer
    return result


def _integrate_all(proj: dict, atlas: ReferenceAtlas) -> dict:
    names = axis_names()
    ref = [{"cell": c, "source": "reference", "UMAP1": atlas.coords[c][0], "UMAP2": atlas.coords[c][1],
            "label": atlas.labels.get(c)} for c in atlas.cells]
    return {"n_reference": len(ref), "n_query": proj["n_cells"],
            "n_total": len(ref) + proj["n_cells"], "axes": names}


def _nearest_states(proj: dict, atlas: ReferenceAtlas, top: int = 3) -> List[dict]:
    out = []
    for c in proj["cells"]:
        neigh = c.get("_neighbours", [])[:top]
        states = [atlas.labels.get(n, "?") for n in neigh]
        out.append({"cell": c["cell"], "nearest_states": states,
                    "predicted_label": c["predicted_label"]})
    return out


def _compare_to_atlas(proj: dict, atlas: ReferenceAtlas) -> dict:
    """Compare the query cohort's mean axes vs the reference atlas (condition = query vs atlas)."""
    names = axis_names()
    q_mean = {a: round(sum(c[a] for c in proj["cells"]) / max(1, proj["n_cells"]), 3) for a in names}
    r_mean = {a: round(sum(atlas.axes.get(c, {}).get(a, 0.0) for c in atlas.cells) / max(1, len(atlas.cells)), 3)
              for a in names}
    delta = {a: round(q_mean[a] - r_mean[a], 3) for a in names}
    return {"query_mean_axes": q_mean, "atlas_mean_axes": r_mean, "delta": delta}
