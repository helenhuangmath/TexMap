from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

from texmap.config import load_config
from texmap.pipeline import run


class PipelineSmokeTest(unittest.TestCase):
    def test_toy_pipeline_runs(self):
        config = load_config(Path("examples/pbmc_toy/config.yaml"))
        with TemporaryDirectory() as tmp:
            config.output.directory = Path(tmp) / "pbmc_toy"
            report = run(config)
            self.assertTrue(report.exists())
            self.assertTrue((config.output.directory / "tables" / "integrated_embedding.csv").exists())
            self.assertTrue((config.output.directory / "tables" / "pathway_scores.csv").exists())
            self.assertTrue((config.output.directory / "figures" / "integrated_umap.svg").exists())
            self.assertTrue((config.output.directory / "figures" / "pathway_heatmap.svg").exists())
            self.assertTrue((config.output.directory / "agent" / "run_result.json").exists())
            self.assertTrue((config.output.directory / "agent" / "interpretation.json").exists())
            self.assertTrue((config.output.directory / "ml_ready" / "features.csv").exists())
            self.assertTrue((config.output.directory / "foundation_models" / "adapter_manifest.json").exists())
            self.assertTrue((config.output.directory / "benchmark" / "metrics.json").exists())
            self.assertTrue((config.output.directory / "scalability" / "projection_plan.json").exists())
            html = report.read_text(encoding="utf-8")
            self.assertIn("../figures/integrated_umap.svg", html)
            self.assertIn("../figures/pathway_heatmap.svg", html)
            self.assertIn("Agentic Workflow", html)
            self.assertIn("Foundation Models", html)


if __name__ == "__main__":
    unittest.main()
