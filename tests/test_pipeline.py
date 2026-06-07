from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

from texmap.config import load_config
from texmap.demo import build_atlas
from texmap.pipeline import run


class PipelineSmokeTest(unittest.TestCase):
    def test_tex_atlas_pipeline_runs(self):
        with TemporaryDirectory() as tmp:
            atlas_dir = Path(tmp) / "tex_atlas"
            build_atlas(atlas_dir)
            config = load_config(atlas_dir / "config.yaml")
            config.output.directory = Path(tmp) / "run"
            report = run(config)

            self.assertTrue(report.exists())
            tables = config.output.directory / "tables"
            for name in ("cell_qc.csv", "integrated_embedding.csv", "pathway_scores.csv",
                         "tex_axes.csv", "bulk_rna_projection.csv", "scatac_projection.csv"):
                self.assertTrue((tables / name).exists(), name)

            # tex axes are present and query cells carry exhaustion coordinates
            tex = (tables / "tex_axes.csv").read_text()
            self.assertIn("Exhaustion", tex)
            self.assertIn("tex_state", tex)
            embedding = (tables / "integrated_embedding.csv").read_text()
            self.assertIn("Tex-terminal", embedding)
            self.assertIn("bulkRNA_query", embedding)
            self.assertIn("scATAC_query", embedding)

            html = report.read_text(encoding="utf-8")
            self.assertIn("TexMap interactive explorer", html)


if __name__ == "__main__":
    unittest.main()
