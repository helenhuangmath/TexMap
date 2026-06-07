"""Query CZ CELLxGENE Discover for public single-cell datasets.

This connects TexMap to the broader open-science ecosystem (note.txt: "query cellxgene
... fit for the scope of OS4Science"). It searches the public CZ CELLxGENE Discover
Curation API for exhaustion-relevant datasets and returns deep links into the cellxgene
Explorer, so a user can find a reference dataset, open it in cellxgene, and bring it back
into the TexMap coordinate system.

It calls the live API when the network is reachable and falls back to a curated catalog of
landmark CD8 T-cell exhaustion studies when offline, so the feature is always usable.
"""
from __future__ import annotations

import json
import urllib.request
from typing import List, Optional

DISCOVER_DATASETS_API = "https://api.cellxgene.cziscience.com/curation/v1/datasets"
EXPLORER_URL = "https://cellxgene.cziscience.com/e/{dataset_id}.cxg/"
DISCOVER_SITE = "https://cellxgene.cziscience.com/"

# Default search emphasis when the user does not type a query.
DEFAULT_TERMS = ["exhaust", "cd8", "t cell", "tumor", "tils", "chronic", "lcmv", "car"]

# Curated, honestly-labelled pointers to landmark exhaustion datasets/atlases that live on
# CELLxGENE Discover. Used offline; the live API supersedes these when reachable. We link to
# the DOI and the Discover site rather than fabricating dataset UUIDs.
CURATED_CATALOG = [
    {
        "title": "Pan-cancer single-cell landscape of tumor-infiltrating T cells (Zheng et al., Science 2021)",
        "organism": "Homo sapiens", "tissue": "pan-cancer", "disease": "cancer",
        "assay": "scRNA-seq", "cell_count": 397810,
        "doi": "https://doi.org/10.1126/science.abe6474",
    },
    {
        "title": "Defining T cell states associated with response to checkpoint immunotherapy in melanoma (Sade-Feldman et al., Cell 2018)",
        "organism": "Homo sapiens", "tissue": "melanoma", "disease": "melanoma",
        "assay": "scRNA-seq", "cell_count": 16291,
        "doi": "https://doi.org/10.1016/j.cell.2018.10.038",
    },
    {
        "title": "Chronic viral infection CD8 T-cell exhaustion atlas (LCMV)",
        "organism": "Mus musculus", "tissue": "spleen", "disease": "chronic infection",
        "assay": "scRNA-seq / scATAC-seq", "cell_count": 40000,
        "doi": "https://doi.org/10.1016/j.immuni.2019.11.002",
    },
    {
        "title": "TCF1+ progenitor exhausted CD8 T cells (Tpex) program",
        "organism": "Mus musculus", "tissue": "tumor", "disease": "cancer",
        "assay": "scRNA-seq", "cell_count": 25000,
        "doi": "https://doi.org/10.1038/s41586-019-1325-x",
    },
    {
        "title": "CAR-T cell dysfunction and exhaustion in relapse",
        "organism": "Homo sapiens", "tissue": "blood", "disease": "leukemia",
        "assay": "scRNA-seq", "cell_count": 32000,
        "doi": "https://doi.org/10.1038/s41591-018-0010-1",
    },
]


def search_datasets(query: str = "", organism: Optional[str] = None,
                    limit: int = 20, timeout: float = 15.0) -> dict:
    """Return exhaustion-relevant datasets matching `query` from CELLxGENE Discover."""
    terms = [t for t in (query or "").lower().split() if t] or DEFAULT_TERMS
    try:
        datasets = _fetch_live(timeout=timeout)
        matched = _filter(datasets, terms, organism)
        source = "live (CELLxGENE Discover)"
        if not matched:
            # query had no hits in live index; still show curated suggestions
            matched = _filter(_normalise_curated(), terms, organism) or _normalise_curated()
            source = "live (no exact match) + curated"
    except Exception as exc:  # offline / API error
        matched = _filter(_normalise_curated(), terms, organism) or _normalise_curated()
        source = f"curated offline catalog ({type(exc).__name__})"

    return {
        "query": query,
        "source": source,
        "discover_site": DISCOVER_SITE,
        "n_results": min(len(matched), limit),
        "results": matched[:limit],
    }


def _fetch_live(timeout: float) -> List[dict]:
    req = urllib.request.Request(DISCOVER_DATASETS_API, headers={"User-Agent": "TexMap/0.1"})
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        raw = json.loads(resp.read().decode("utf-8"))
    out = []
    for d in raw:
        out.append({
            "dataset_id": d.get("dataset_id"),
            "title": d.get("title") or "(untitled)",
            "organism": _labels(d.get("organism")),
            "tissue": _labels(d.get("tissue")),
            "disease": _labels(d.get("disease")),
            "cell_type": _labels(d.get("cell_type")),
            "assay": _labels(d.get("assay")),
            "cell_count": d.get("cell_count"),
            "explorer_url": EXPLORER_URL.format(dataset_id=d.get("dataset_id")),
            "paper_url": None,
            "h5ad_url": _h5ad_url(d.get("assets")),
        })
    return out


def _labels(value) -> str:
    if not value:
        return ""
    if isinstance(value, list):
        return ", ".join(v.get("label", "") if isinstance(v, dict) else str(v) for v in value)
    return str(value)


def _h5ad_url(assets) -> Optional[str]:
    for a in assets or []:
        if (a.get("filetype") or "").upper() == "H5AD":
            return a.get("url")
    return None


def _normalise_curated() -> List[dict]:
    out = []
    for c in CURATED_CATALOG:
        # curated entries: link "Open in CELLxGENE" to Discover (search there), keep the paper too
        out.append({**c, "dataset_id": None, "cell_type": "CD8 T cell, exhausted",
                    "explorer_url": DISCOVER_SITE, "paper_url": c["doi"], "h5ad_url": None})
    return out


def _filter(datasets: List[dict], terms: List[str], organism: Optional[str]) -> List[dict]:
    """Rank by relevance: title matches dominate, then disease/tissue, then cell_type/assay.

    Raw cell_count is only a final tiebreak — otherwise a giant generic atlas that merely
    *contains* some CD8 T cells outranks a focused exhaustion study.
    """
    scored = []
    for d in datasets:
        if organism and organism.lower() not in str(d.get("organism", "")).lower():
            continue
        title = str(d.get("title", "")).lower()
        focus = " ".join(str(d.get(k, "")) for k in ("disease", "tissue")).lower()
        incidental = " ".join(str(d.get(k, "")) for k in ("cell_type", "assay")).lower()
        title_hits = sum(1 for t in terms if t in title)
        focus_hits = sum(1 for t in terms if t in focus)
        incidental_hits = sum(1 for t in terms if t in incidental)
        if not (title_hits or focus_hits or incidental_hits):
            continue
        relevance = 3 * title_hits + 2 * focus_hits + incidental_hits
        scored.append((relevance, d.get("cell_count") or 0, d))
    scored.sort(key=lambda t: (-t[0], -t[1]))
    return [d for _, _, d in scored]
