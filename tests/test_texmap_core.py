import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

from texmap.config import load_config
from texmap.demo import build_atlas
from texmap.io import read_counts, read_table
from texmap.projection import ReferenceAtlas, project
from texmap.tex_axes import axis_names, score_tex_axes
from texmap import texagent


class TexAxesTest(unittest.TestCase):
    def test_axes_scaled_and_directional(self):
        # naive-like cell (high stem markers) vs terminal-like (high inhibitory)
        expr = {
            "naive": {"TCF7": 5.0, "SELL": 5.0, "IL7R": 5.0, "PDCD1": 0.0, "HAVCR2": 0.0, "TOX": 0.0},
            "terminal": {"TCF7": 0.0, "SELL": 0.0, "IL7R": 0.0, "PDCD1": 5.0, "HAVCR2": 5.0, "TOX": 5.0},
        }
        axes = score_tex_axes(expr)
        self.assertGreater(axes["terminal"]["Exhaustion"], axes["naive"]["Exhaustion"])
        self.assertGreater(axes["naive"]["Stemness"], axes["terminal"]["Stemness"])
        for cell in expr:
            for a in axis_names():
                self.assertGreaterEqual(axes[cell][a], 0.0)
                self.assertLessEqual(axes[cell][a], 1.0)
            self.assertIn("tex_state", axes[cell])


class ProjectionTest(unittest.TestCase):
    def test_demo_projection_lands_terminal_cells(self):
        with TemporaryDirectory() as tmp:
            out = Path(tmp) / "atlas"
            build_atlas(out)
            atlas = ReferenceAtlas.from_rows(
                read_table(out / "reference_embedding.csv"),
                read_table(out / "reference_metadata.csv"),
                "cell_type",
            )
            self.assertTrue(atlas.has_axes)
            counts = read_counts(out / "query_counts.csv")
            res = project(counts, atlas, out / "tex_pathways.tsv", source="query")
            self.assertEqual(res["n_cells"], len(counts))
            meta = {r["cell"]: r for r in read_table(out / "query_metadata.csv")}
            matches = sum(1 for c in res["cells"]
                          if meta[c["cell"]]["expected_label"] == c["predicted_label"])
            # axis-space kNN transfer should get the clear majority right
            self.assertGreaterEqual(matches / res["n_cells"], 0.6)
            comp = res["summary"]["composition_percent"]
            self.assertTrue(any("Tex" in k for k in comp))


class AgentTest(unittest.TestCase):
    def setUp(self):
        with TemporaryDirectory() as tmp:
            out = Path(tmp) / "atlas"
            build_atlas(out)
            self.atlas = ReferenceAtlas.from_rows(
                read_table(out / "reference_embedding.csv"),
                read_table(out / "reference_metadata.csv"), "cell_type")
            self.gene_sets = {row[0]: row[1:] for row in
                              (l.split("\t") for l in (out / "tex_pathways.tsv").read_text().splitlines())}

    def test_axis_question(self):
        a = texagent.answer("genes for terminal exhaustion", self.atlas, self.gene_sets, {}, None)
        self.assertIn("axis", a["data"])

    def test_gene_question(self):
        a = texagent.answer("which programs drive TOX?", self.atlas, self.gene_sets, {}, None)
        self.assertIn("TOX", a["answer"])
        self.assertIn("Exhaustion_TFs", a["data"].get("gene_pathways", []))

    def test_atlas_summary(self):
        a = texagent.answer("describe the atlas", self.atlas, self.gene_sets, {}, None)
        self.assertIn("1200", a["answer"])

    def test_offline_actions(self):
        # offline (no LLM key) still drives the UI via synthesized actions
        a = texagent.answer("color terminal exhaustion", self.atlas, self.gene_sets, {}, None)
        self.assertTrue(any(act["type"] == "color_by" for act in a["actions"]))
        g = texagent.answer("which programs drive TOX", self.atlas, self.gene_sets, {}, None)
        self.assertTrue(any(act["type"] == "color_by_gene" for act in g["actions"]))

    def test_agent_tools_operate_on_real_data(self):
        ctx = {"atlas": self.atlas, "gene_sets": self.gene_sets, "network": None,
               "accuracy_fn": lambda: {"accuracy": 1.0}, "clinical_rows": [], "last_projection": None}
        comp, _ = texagent._execute_tool("atlas_composition", {}, ctx)
        self.assertEqual(sum(comp.values()), 1200)
        markers, action = texagent._execute_tool("axis_markers", {"axis": "Exhaustion"}, ctx)
        self.assertIn("up", markers)
        self.assertEqual(action["type"], "color_by")
        acc, _ = texagent._execute_tool("projection_accuracy", {}, ctx)
        self.assertEqual(acc["accuracy"], 1.0)

    def test_step_parser(self):
        self.assertEqual(texagent._parse_step('{"tool":"x","args":{}}')["tool"], "x")
        self.assertEqual(texagent._parse_step('```json\n{"final":"hi"}\n```')["final"], "hi")
        self.assertIsNone(texagent._parse_step("not json"))

    def test_runtime_provider_switch(self):
        import os
        keys = ("GEMINI_API_KEY", "GOOGLE_API_KEY", "OPENAI_API_KEY", "TEXMAP_AGENT_PROVIDER")
        saved = {k: os.environ.get(k) for k in keys}
        try:
            for k in keys:
                os.environ.pop(k, None)
            self.assertTrue(texagent.backend_name().startswith("offline"))
            os.environ["GEMINI_API_KEY"] = "test-key"
            os.environ["TEXMAP_AGENT_PROVIDER"] = "google"
            self.assertIn("google", texagent.backend_name())
        finally:
            for k, v in saved.items():
                if v is None:
                    os.environ.pop(k, None)
                else:
                    os.environ[k] = v


class ServerTest(unittest.TestCase):
    def test_endpoints(self):
        from texmap.server import AtlasState, _Handler
        with TemporaryDirectory() as tmp:
            out = Path(tmp) / "atlas"
            build_atlas(out)
            config = load_config(out / "config.yaml")
            state = AtlasState(config)

            payload = state.atlas_payload()
            self.assertEqual(payload["n_cells"], 1200)
            self.assertIn("Exhaustion", payload["axes"])
            self.assertTrue(all("x" in c and "y" in c for c in payload["cells"][:5]))

            # marker-gene panel is exposed for cellxgene-style color-by-gene
            self.assertTrue(payload["markerGenes"])
            self.assertIn("TOX", payload["markerGenes"])
            self.assertTrue(all("expr" in c for c in payload["cells"][:5]))

            csv_text = (out / "query_counts.csv").read_text()
            result = state.project_csv(csv_text)
            self.assertGreater(result["n_cells"], 0)
            self.assertIn("composition_percent", result["summary"])
            self.assertIn("expr", result["cells"][0])


class CellxgeneTest(unittest.TestCase):
    def test_search_returns_results_offline(self):
        from texmap import cellxgene
        # short timeout so offline environments fall back to the curated catalog quickly
        res = cellxgene.search_datasets("cd8 exhaustion melanoma", timeout=0.001)
        self.assertGreater(res["n_results"], 0)
        first = res["results"][0]
        self.assertIn("title", first)
        self.assertIn("explorer_url", first)

    def test_organism_filter(self):
        from texmap import cellxgene
        res = cellxgene.search_datasets("exhaustion", organism="Mus musculus", timeout=0.001)
        self.assertTrue(all("Mus musculus" in r["organism"] for r in res["results"]))


class RegulatoryTest(unittest.TestCase):
    def test_recovers_tox_inhibitory_program(self):
        from texmap import regulatory
        with TemporaryDirectory() as tmp:
            out = Path(tmp) / "atlas"
            build_atlas(out)
            rows = read_table(out / "reference_markers.csv")
            expr = {r["cell"]: {g: float(v) for g, v in r.items() if g != "cell"} for r in rows}
            net = regulatory.recover_network(expr)
            self.assertGreater(len(net["edges"]), 0)
            self.assertTrue(any(n["is_tf"] for n in net["nodes"]))
            # TOX should drive the inhibitory-receptor program
            tox = regulatory.focus(net, "TOX")
            tox_targets = {e["target"] for e in tox["targets"]}
            self.assertTrue({"PDCD1", "LAG3"} & tox_targets)


class ClinicalTest(unittest.TestCase):
    def test_metric_values(self):
        from texmap import clinical
        self.assertAlmostEqual(clinical.auroc([0.1, 0.4, 0.35, 0.8], [0, 0, 1, 1]), 0.75)
        self.assertEqual(clinical.concordance_index([4, 3, 2, 1], [1, 2, 3, 4], [1, 1, 1, 1]), 1.0)
        # overlapping (non-separable) cohort where group 1 has higher hazard → HR>1
        x = [1, 1, 1, 1, 1, 1, 1, 1, 0, 0, 0, 0, 0, 0, 0, 0]
        t = [5, 8, 3, 12, 6, 15, 9, 4, 20, 30, 14, 25, 40, 18, 22, 35]
        e = [1, 1, 1, 1, 1, 0, 1, 1, 1, 0, 1, 1, 0, 1, 1, 0]
        hr = clinical.cox_hazard_ratio(x, t, e)
        self.assertIsNotNone(hr["hazard_ratio"])
        self.assertGreater(hr["hazard_ratio"], 1.0)

    def test_cohort_directions(self):
        from texmap import clinical
        with TemporaryDirectory() as tmp:
            out = Path(tmp) / "atlas"; build_atlas(out)
            rows = read_table(out / "clinical_cohort.csv")
            stem = clinical.evaluate(rows, "Stemness")
            exh = clinical.evaluate(rows, "Exhaustion")
            self.assertIn("auroc", stem)
            self.assertIn("concordance_index", stem)
            # stemness protective (HR<1), exhaustion adverse (HR>1)
            self.assertLess(stem["cox"]["hazard_ratio"], 1.0)
            self.assertGreater(exh["cox"]["hazard_ratio"], 1.0)


class EvaluationTest(unittest.TestCase):
    def test_accuracy_report(self):
        from texmap import evaluation
        rep = evaluation.accuracy_report([("A", "A"), ("A", "B"), ("B", "B"), ("B", "B")])
        self.assertEqual(rep["n"], 4)
        self.assertAlmostEqual(rep["accuracy"], 0.75)
        self.assertIn("confusion", rep)

    def test_crossval_atlas(self):
        from texmap import evaluation
        from texmap.projection import ReferenceAtlas
        with TemporaryDirectory() as tmp:
            out = Path(tmp) / "atlas"; build_atlas(out)
            atlas = ReferenceAtlas.from_rows(read_table(out / "reference_embedding.csv"),
                                             read_table(out / "reference_metadata.csv"), "cell_type")
            rep = evaluation.crossval_atlas(atlas, k=15)
            self.assertGreaterEqual(rep["accuracy"], 0.0)
            self.assertLessEqual(rep["accuracy"], 1.0)


class TexApiTest(unittest.TestCase):
    def test_in_process_api(self):
        from texmap import TexMap
        from texmap.io import read_counts
        with TemporaryDirectory() as tmp:
            out = Path(tmp) / "atlas"; build_atlas(out)
            tm = TexMap.from_config(out / "config.yaml")
            res = tm.project(read_counts(out / "query_counts.csv"))
            self.assertGreater(res["n_cells"], 0)
            self.assertTrue(tm.regulatory_network()["edges"])
            self.assertLessEqual(tm.projection_accuracy()["accuracy"], 1.0)


class MultiomicCrossSpeciesTest(unittest.TestCase):
    def test_scatac_and_crossspecies_project(self):
        from texmap import TexMap
        from texmap.io import read_counts
        with TemporaryDirectory() as tmp:
            out = Path(tmp) / "atlas"; build_atlas(out)
            tm = TexMap.from_config(out / "config.yaml")
            # cross-species: mouse-cased symbols still project into Tex states
            mouse = read_counts(out / "crossspecies_mouse_query.csv")
            res = tm.project(mouse, source="mouse")
            self.assertTrue(any("Tex" in k or "Effector" in k or "Memory" in k
                                for k in res["summary"]["composition_percent"]))
            # multiomic example files exist for the pipeline path
            self.assertTrue((out / "scatac_peaks.csv").exists())
            self.assertTrue((out / "scatac_peak_gene_links.csv").exists())


class IntegrationEngineTest(unittest.TestCase):
    def test_methods_and_modes(self):
        from texmap import integration
        p = integration.methods_payload()
        keys = [m["key"] for m in p["methods"]]
        for k in ("scVI", "scANVI", "scgpt_zeroshot", "scgpt_finetune", "harmony", "seurat", "texmap_axis"):
            self.assertIn(k, keys)
        self.assertEqual(p["default_method"], "scVI")
        self.assertTrue(next(m for m in p["methods"] if m["key"] == "texmap_axis")["available"])

    def test_query_modes_run(self):
        from texmap import integration
        from texmap.projection import ReferenceAtlas
        from texmap.io import read_counts
        with TemporaryDirectory() as tmp:
            out = Path(tmp) / "atlas"; build_atlas(out)
            atlas = ReferenceAtlas.from_rows(read_table(out / "reference_embedding.csv"),
                                             read_table(out / "reference_metadata.csv"), "cell_type")
            counts = read_counts(out / "query_counts.csv")
            for mode, key in [("project_query", "cells"), ("integrate_all", "integrated"),
                              ("label_transfer", "label_transfer"), ("nearest_tex_states", "nearest"),
                              ("compare_conditions", "comparison")]:
                res = integration.run(mode, "scVI", counts, atlas, out / "tex_pathways.tsv")
                self.assertIn(key, res)
                # the axis-space engine always does the actual mapping (heavy backends are adapters)
                self.assertTrue(res["engine"].startswith("texmap-axis-projection"))
                self.assertIn(res["method_used"], ("scVI", "texmap_axis"))


class TexBenchServerTest(unittest.TestCase):
    def test_texbench_payload(self):
        from texmap.server import AtlasState
        with TemporaryDirectory() as tmp:
            out = Path(tmp) / "atlas"; build_atlas(out)
            state = AtlasState(load_config(out / "config.yaml"))
            b = state.texbench()
            self.assertIn("methods", b)
            self.assertIsNotNone(b["projection_accuracy"])
            self.assertIn("auroc", b["clinical_exhaustion"])


class IngestTest(unittest.TestCase):
    def test_build_reference_from_csv(self):
        from texmap.ingest import build_reference
        from texmap import TexMap
        with TemporaryDirectory() as tmp:
            out = Path(tmp) / "atlas"; build_atlas(out)
            ref = Path(tmp) / "custom"
            cfg = build_reference(str(out / "query_counts.csv"), ref,
                                  metadata_path=str(out / "query_metadata.csv"),
                                  label_column="expected_label")
            self.assertTrue(cfg.exists())
            self.assertTrue((ref / "reference_embedding.csv").exists())
            self.assertTrue((ref / "reference_markers.csv").exists())
            tm = TexMap.from_config(cfg)
            self.assertTrue(tm.atlas.has_axes)
            self.assertGreater(len(tm.atlas.cells), 0)


if __name__ == "__main__":
    unittest.main()
