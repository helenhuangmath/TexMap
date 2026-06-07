"""TexMap interactive web server.

A dependency-free web application (Python stdlib ``http.server``) that serves the
TexMap atlas explorer and a small REST API:

    GET  /                      single-page explorer app
    GET  /api/config            project name, axes, color-by fields, pathway names
    GET  /api/atlas             reference cells: coords + axes + categorical metadata
    POST /api/project           upload a counts CSV -> project into the Tex coordinate map
    POST /api/agent             natural-language TexAgent question -> grounded answer

Run with ``texmap serve`` (auto-builds the demo atlas if none is configured).
"""
from __future__ import annotations

import csv
import io as _io
import json
import os
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Dict, List, Optional

from urllib.parse import parse_qs, urlparse

from texmap import cellxgene, clinical, evaluation, integration, regulatory, texagent
from texmap.config import TexMapConfig
from texmap.io import Matrix, read_table
from texmap.pathways import load_gene_sets
from texmap.projection import ReferenceAtlas, project
from texmap.tex_axes import axis_names

WEBAPP_DIR = Path(__file__).parent / "webapp"

CATEGORICAL_FIELDS = ["cell_type", "tex_state", "species", "modality", "study"]


class AtlasState:
    """Loaded reference atlas + gene sets shared across requests."""

    def __init__(self, config: TexMapConfig):
        self.config = config
        self.project_name = config.output.project_name
        embedding_rows = read_table(config.reference.embedding)
        metadata_rows = read_table(config.reference.metadata) if config.reference.metadata else []
        self.atlas = ReferenceAtlas.from_rows(
            embedding_rows, metadata_rows, config.reference.label_column
        )
        self.meta_by_cell = {str(r.get("cell")): r for r in metadata_rows}
        self.pathway_sets_path = config.analysis.pathway_sets
        self.gene_sets = load_gene_sets(self.pathway_sets_path)
        self.last_projection: Optional[dict] = None
        self._lock = threading.Lock()

        # optional marker-gene expression panel (cellxgene-style color-by-gene)
        self.marker_genes: List[str] = []
        self.marker_expr: Dict[str, Dict[str, float]] = {}
        markers_path = Path(config.reference.embedding).parent / "reference_markers.csv"
        if markers_path.exists():
            rows = read_table(markers_path)
            self.marker_genes = [c for c in rows[0].keys() if c != "cell"] if rows else []
            for r in rows:
                self.marker_expr[str(r["cell"])] = {
                    g: float(r.get(g) or 0.0) for g in self.marker_genes
                }

        # recover the regulatory network from reference co-expression (once, at startup)
        self.network = regulatory.recover_network(self.marker_expr) if self.marker_expr else {}

        # optional clinical cohort for the translation benchmark
        self.clinical_rows = []
        clin_path = Path(config.reference.embedding).parent / "clinical_cohort.csv"
        if clin_path.exists():
            self.clinical_rows = read_table(clin_path)
        self._accuracy_cache: Optional[dict] = None

    def accuracy(self) -> dict:
        if self._accuracy_cache is None:
            self._accuracy_cache = evaluation.crossval_atlas(self.atlas)
        return self._accuracy_cache

    def atlas_payload(self) -> dict:
        names = axis_names()
        cells = []
        for cell in self.atlas.cells:
            u1, u2 = self.atlas.coords[cell]
            row = {"cell": cell, "x": u1, "y": u2}
            row.update({a: self.atlas.axes.get(cell, {}).get(a, 0.0) for a in names})
            for field in CATEGORICAL_FIELDS:
                if cell in self.meta_by_cell and field in self.meta_by_cell[cell]:
                    row[field] = self.meta_by_cell[cell][field]
            if cell in self.marker_expr:
                row["expr"] = self.marker_expr[cell]
            cells.append(row)
        return {
            "project": self.project_name,
            "axes": names,
            "categorical": [f for f in CATEGORICAL_FIELDS if any(f in c for c in cells)],
            "pathways": list(self.gene_sets.keys()),
            "markerGenes": self.marker_genes,
            "states": sorted({c.get("tex_state", "") for c in cells if c.get("tex_state")}),
            "n_cells": len(cells),
            "cells": cells,
        }

    def project_csv(self, text: str, source: str = "query",
                    method: str = integration.DEFAULT_METHOD,
                    mode: str = integration.DEFAULT_MODE) -> dict:
        counts = _parse_counts_csv(text)
        if not counts:
            raise ValueError("Could not parse any cells from the uploaded CSV.")
        result = integration.run(mode, method, counts, self.atlas, self.pathway_sets_path)
        with self._lock:
            self.last_projection = result
        return result

    def texbench(self) -> dict:
        """TexBench: integration-method availability + headline benchmark metrics."""
        acc = self.accuracy()
        clin = (clinical.evaluate(self.clinical_rows, "Exhaustion") if self.clinical_rows else {})
        return {
            "project": self.project_name,
            "methods": integration.methods_payload()["methods"],
            "modes": integration.methods_payload()["modes"],
            "projection_accuracy": acc.get("accuracy"),
            "macro_f1": acc.get("macro_f1"),
            "n_reference_cells": len(self.atlas.cells),
            "clinical_exhaustion": {
                "auroc": clin.get("auroc"),
                "concordance_index": clin.get("concordance_index"),
                "hazard_ratio": (clin.get("cox") or {}).get("hazard_ratio"),
            },
        }


def _parse_counts_csv(text: str) -> Matrix:
    reader = csv.reader(_io.StringIO(text))
    rows = [r for r in reader if r]
    if len(rows) < 2:
        return {}
    header = rows[0]
    genes = header[1:]
    matrix: Matrix = {}
    for r in rows[1:]:
        if not r:
            continue
        cell = r[0]
        vals = {}
        for g, v in zip(genes, r[1:]):
            try:
                vals[g] = float(v)
            except ValueError:
                vals[g] = 0.0
        matrix[cell] = vals
    return matrix


class _Handler(BaseHTTPRequestHandler):
    state: AtlasState  # injected via partial

    def log_message(self, fmt, *args):  # quieter logging
        return

    # ---- helpers ----
    def _send_json(self, payload, status: int = 200):
        body = json.dumps(payload).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def _send_file(self, path: Path, content_type: str):
        body = path.read_bytes()
        self.send_response(200)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def _read_body(self) -> bytes:
        length = int(self.headers.get("Content-Length", 0))
        return self.rfile.read(length) if length else b""

    # ---- routes ----
    def do_GET(self):
        parsed = urlparse(self.path)
        path = parsed.path
        try:
            if path == "/api/cellxgene/search":
                params = parse_qs(parsed.query)
                q = (params.get("q", [""])[0])
                organism = params.get("organism", [None])[0]
                return self._send_json(cellxgene.search_datasets(q, organism=organism))
            if path == "/api/regulatory":
                gene = parse_qs(parsed.query).get("gene", [None])[0]
                if gene:
                    return self._send_json(regulatory.focus(self.state.network, gene))
                return self._send_json(self.state.network)
            if path == "/api/methods":
                return self._send_json(integration.methods_payload())
            if path == "/api/texbench":
                return self._send_json(self.state.texbench())
            if path == "/api/accuracy":
                return self._send_json(self.state.accuracy())
            if path == "/api/clinical":
                predictor = parse_qs(parsed.query).get("predictor", ["Exhaustion"])[0]
                if not self.state.clinical_rows:
                    return self._send_json({"error": "no clinical cohort loaded"}, 404)
                return self._send_json(clinical.evaluate(self.state.clinical_rows, predictor))
            if path in ("/", "/index.html"):
                return self._send_file(WEBAPP_DIR / "index.html", "text/html; charset=utf-8")
            if path == "/app.js":
                return self._send_file(WEBAPP_DIR / "app.js", "application/javascript; charset=utf-8")
            if path == "/styles.css":
                return self._send_file(WEBAPP_DIR / "styles.css", "text/css; charset=utf-8")
            if path == "/api/config":
                return self._send_json(self._config_payload())
            if path == "/api/atlas":
                return self._send_json(self.state.atlas_payload())
            if path == "/api/demo_query":
                counts = self.state.config.input.counts
                if counts and Path(counts).exists():
                    return self._send_file(Path(counts), "text/csv; charset=utf-8")
                return self._send_json({"error": "no demo query configured"}, 404)
            return self._send_json({"error": "not found", "path": path}, 404)
        except Exception as exc:  # pragma: no cover - defensive
            return self._send_json({"error": str(exc)}, 500)

    def do_POST(self):
        path = self.path.split("?", 1)[0]
        try:
            body = self._read_body()
            if path == "/api/project":
                text = self._extract_csv(body)
                source = self.headers.get("X-Source", "query")
                method = self.headers.get("X-Method", integration.DEFAULT_METHOD)
                mode = self.headers.get("X-Mode", integration.DEFAULT_MODE)
                return self._send_json(self.state.project_csv(text, source=source, method=method, mode=mode))
            if path == "/api/agent/config":
                data = json.loads(body or b"{}")
                provider = (data.get("provider") or "").strip().lower()
                key = (data.get("api_key") or "").strip()
                env = {"google": "GEMINI_API_KEY", "openai": "OPENAI_API_KEY"}
                if provider not in env or not key:
                    return self._send_json({"error": "provide provider (google|openai) and api_key"}, 400)
                os.environ[env[provider]] = key
                os.environ["TEXMAP_AGENT_PROVIDER"] = provider
                return self._send_json({"backend": texagent.backend_name(), "provider": provider})
            if path == "/api/agent":
                data = json.loads(body or b"{}")
                question = (data.get("question") or "").strip()
                answer = texagent.answer(
                    question,
                    self.state.atlas,
                    self.state.gene_sets,
                    self.state.meta_by_cell,
                    self.state.last_projection,
                    network=self.state.network,
                    accuracy_fn=self.state.accuracy,
                    clinical_rows=self.state.clinical_rows,
                )
                return self._send_json(answer)
            return self._send_json({"error": "not found", "path": path}, 404)
        except Exception as exc:
            return self._send_json({"error": str(exc)}, 400)

    def _extract_csv(self, body: bytes) -> str:
        ctype = self.headers.get("Content-Type", "")
        if ctype.startswith("application/json"):
            return json.loads(body or b"{}").get("csv", "")
        return body.decode("utf-8", errors="replace")

    def _config_payload(self) -> dict:
        return {
            "project": self.state.project_name,
            "axes": axis_names(),
            "categorical": [f for f in CATEGORICAL_FIELDS],
            "pathways": list(self.state.gene_sets.keys()),
            "agent_backend": texagent.backend_name(),
        }


def make_server(config: TexMapConfig, host: str = "127.0.0.1", port: int = 8000):
    """Build a ThreadingHTTPServer + its AtlasState without blocking. (Used by serve + tests.)"""
    state = AtlasState(config)

    # bind state onto a per-server handler subclass so multiple servers can coexist
    class BoundHandler(_Handler):
        pass

    BoundHandler.state = state  # type: ignore[attr-defined]
    httpd = ThreadingHTTPServer((host, port), BoundHandler)
    return httpd, state


def serve(config: TexMapConfig, host: str = "127.0.0.1", port: int = 8000) -> None:
    httpd, state = make_server(config, host, port)
    url = f"http://{host}:{port}"
    print(f"TexMap atlas explorer running at {url}")
    print(f"  project: {state.project_name}")
    print(f"  reference cells: {len(state.atlas.cells)}")
    print(f"  agent backend: {texagent.backend_name()}")
    print("Press Ctrl+C to stop.")
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        print("\nShutting down TexMap server.")
        httpd.shutdown()
