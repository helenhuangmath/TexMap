"""End-to-end test: boot the real TexMap web server and drive it over HTTP."""
import json
import os
import socket
import unittest
import urllib.error
import urllib.request
from pathlib import Path
from tempfile import TemporaryDirectory
from threading import Thread

from texmap import cellxgene
from texmap.config import load_config
from texmap.demo import build_atlas
from texmap.server import make_server


# generous timeout: some endpoints (e.g. CELLxGENE search) call a live upstream API
def _get(url, timeout=30):
    with urllib.request.urlopen(url, timeout=timeout) as r:
        return r.status, r.read()


def _post(url, body, content_type, timeout=30):
    req = urllib.request.Request(url, data=body.encode("utf-8"),
                                 headers={"Content-Type": content_type}, method="POST")
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return r.status, json.loads(r.read())


def _online() -> bool:
    try:
        socket.create_connection(("api.cellxgene.cziscience.com", 443), timeout=3).close()
        return True
    except OSError:
        return False


class ServerHTTPIntegrationTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls._tmp = TemporaryDirectory()
        out = Path(cls._tmp.name) / "atlas"
        build_atlas(out)
        cls.out = out
        config = load_config(out / "config.yaml")
        cls.httpd, cls.state = make_server(config, host="127.0.0.1", port=0)
        cls.port = cls.httpd.server_address[1]
        cls.base = f"http://127.0.0.1:{cls.port}"
        cls.thread = Thread(target=cls.httpd.serve_forever, daemon=True)
        cls.thread.start()

    @classmethod
    def tearDownClass(cls):
        cls.httpd.shutdown()
        cls._tmp.cleanup()

    def test_static_app_served(self):
        status, body = _get(self.base + "/")
        self.assertEqual(status, 200)
        self.assertIn(b"TexMap", body)
        self.assertEqual(_get(self.base + "/app.js")[0], 200)
        self.assertEqual(_get(self.base + "/styles.css")[0], 200)

    def test_config_and_atlas(self):
        _, cfg = _get(self.base + "/api/config")
        cfg = json.loads(cfg)
        self.assertIn("Exhaustion", cfg["axes"])

        _, atlas = _get(self.base + "/api/atlas")
        atlas = json.loads(atlas)
        self.assertEqual(atlas["n_cells"], 1200)
        self.assertIn("TOX", atlas["markerGenes"])
        self.assertTrue(all(k in atlas["cells"][0] for k in ("x", "y", "expr")))

    def test_project_endpoint(self):
        csv_text = (self.out / "query_counts.csv").read_text()
        status, data = _post(self.base + "/api/project", csv_text, "text/csv")
        self.assertEqual(status, 200)
        self.assertGreater(data["n_cells"], 0)
        self.assertIn("composition_percent", data["summary"])
        self.assertTrue(any("Tex" in k for k in data["summary"]["composition_percent"]))

    def test_agent_endpoint(self):
        _, data = _post(self.base + "/api/agent", json.dumps({"question": "genes for terminal exhaustion"}),
                        "application/json")
        self.assertIn("answer", data)
        self.assertTrue(data["answer"])

    def test_cellxgene_search_endpoint(self):
        status, body = _get(self.base + "/api/cellxgene/search?q=cd8%20exhaustion%20melanoma")
        self.assertEqual(status, 200)
        data = json.loads(body)
        self.assertGreater(data["n_results"], 0)
        self.assertIn("explorer_url", data["results"][0])

    def test_unknown_route_404(self):
        with self.assertRaises(urllib.error.HTTPError) as cm:
            _get(self.base + "/api/does-not-exist")
        self.assertEqual(cm.exception.code, 404)


@unittest.skipUnless(_online(), "CELLxGENE Discover API not reachable; skipping live query test")
class LiveCellxgeneTest(unittest.TestCase):
    def test_live_discover_search(self):
        res = cellxgene.search_datasets("CD8 T cell tumor", limit=5, timeout=15)
        self.assertTrue(res["source"].startswith("live"))
        self.assertGreater(res["n_results"], 0)
        # if any live dataset came back it carries a real id + .cxg deep link
        live = [r for r in res["results"] if r.get("dataset_id")]
        if live:
            self.assertIn(".cxg", live[0]["explorer_url"])


if __name__ == "__main__":
    unittest.main()
