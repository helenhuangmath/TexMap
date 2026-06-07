"""TexAPI — programmatic access so other programs can build on TexMap.

Two entry points:

  * ``TexMap`` — an in-process Python API. Load a reference once, then project matrices,
    score axes, recover the regulatory network, and run benchmarks, all without a server::

        from texmap import TexMap
        tm = TexMap.from_config("examples/tex_atlas/config.yaml")
        result = tm.project({"cell1": {"PDCD1": 12, "TOX": 8, ...}})
        print(result["summary"]["composition_percent"])

  * ``TexAPIClient`` — a thin HTTP client for a running ``texmap serve`` instance, so
    programs in any language pattern (or a notebook) can hit the REST API::

        from texmap import TexAPIClient
        api = TexAPIClient("http://127.0.0.1:8000")
        api.project_csv(open("counts.csv").read())
        api.cellxgene_search("CD8 exhaustion melanoma")

The REST surface (the "TexAPI") is also language-agnostic JSON over HTTP — see README.
"""
from __future__ import annotations

import json
import urllib.parse
import urllib.request
from pathlib import Path
from typing import Dict, Optional

from texmap import cellxgene as _cellxgene
from texmap import clinical as _clinical
from texmap import evaluation as _evaluation
from texmap import regulatory as _regulatory
from texmap.config import TexMapConfig, load_config
from texmap.io import Matrix, read_table
from texmap.pathways import load_gene_sets
from texmap.projection import ReferenceAtlas, project
from texmap.tex_axes import marker_expression, marker_panel, score_tex_axes


class TexMap:
    """In-process TexMap reference: project data and run analyses without a server."""

    def __init__(self, atlas: ReferenceAtlas, pathway_sets=None, marker_expr=None):
        self.atlas = atlas
        self.pathway_sets = pathway_sets
        self._marker_expr = marker_expr or {}
        self._network = None

    @classmethod
    def from_config(cls, config) -> "TexMap":
        config = config if isinstance(config, TexMapConfig) else load_config(config)
        atlas = ReferenceAtlas.from_rows(
            read_table(config.reference.embedding),
            read_table(config.reference.metadata) if config.reference.metadata else [],
            config.reference.label_column,
        )
        markers_path = Path(config.reference.embedding).parent / "reference_markers.csv"
        marker_expr = {}
        if markers_path.exists():
            for r in read_table(markers_path):
                marker_expr[str(r["cell"])] = {k: float(v) for k, v in r.items() if k != "cell"}
        return cls(atlas, config.analysis.pathway_sets, marker_expr)

    # ---- core operations ----
    def score_axes(self, expression: Matrix) -> Dict[str, Dict[str, float]]:
        return score_tex_axes(expression)

    def project(self, counts: Matrix, source: str = "query", k: int = 8) -> dict:
        return project(counts, self.atlas, self.pathway_sets, source=source, k=k)

    def marker_expression(self, normalized: Matrix):
        return marker_expression(normalized, marker_panel())

    def regulatory_network(self) -> dict:
        if self._network is None:
            self._network = _regulatory.recover_network(self._marker_expr) if self._marker_expr else {}
        return self._network

    def regulators_of(self, gene: str) -> dict:
        return _regulatory.focus(self.regulatory_network(), gene)

    def projection_accuracy(self, k: int = 15) -> dict:
        return _evaluation.crossval_atlas(self.atlas, k=k)

    def clinical_benchmark(self, cohort, predictor: str) -> dict:
        rows = cohort if isinstance(cohort, list) else read_table(cohort)
        return _clinical.evaluate(rows, predictor)

    @staticmethod
    def search_cellxgene(query: str, **kw) -> dict:
        return _cellxgene.search_datasets(query, **kw)


class TexAPIClient:
    """HTTP client for a running ``texmap serve`` instance."""

    def __init__(self, base_url: str = "http://127.0.0.1:8000", timeout: float = 30.0):
        self.base = base_url.rstrip("/")
        self.timeout = timeout

    def _get(self, path: str, **params):
        url = self.base + path
        if params:
            url += "?" + urllib.parse.urlencode({k: v for k, v in params.items() if v is not None})
        with urllib.request.urlopen(url, timeout=self.timeout) as r:
            return json.loads(r.read())

    def _post(self, path: str, body: bytes, content_type: str):
        req = urllib.request.Request(self.base + path, data=body,
                                     headers={"Content-Type": content_type}, method="POST")
        with urllib.request.urlopen(req, timeout=self.timeout) as r:
            return json.loads(r.read())

    def config(self): return self._get("/api/config")
    def atlas(self): return self._get("/api/atlas")
    def accuracy(self): return self._get("/api/accuracy")
    def regulatory(self, gene: Optional[str] = None): return self._get("/api/regulatory", gene=gene)
    def clinical(self, predictor: str = "Exhaustion"): return self._get("/api/clinical", predictor=predictor)
    def cellxgene_search(self, query: str, organism: Optional[str] = None):
        return self._get("/api/cellxgene/search", q=query, organism=organism)

    def project_csv(self, csv_text: str) -> dict:
        return self._post("/api/project", csv_text.encode("utf-8"), "text/csv")

    def agent(self, question: str) -> dict:
        return self._post("/api/agent", json.dumps({"question": question}).encode("utf-8"),
                          "application/json")
