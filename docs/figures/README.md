# TexMap figures

This directory contains screenshots and reproducible example integration figures used by
the top-level `README.md` and documentation site.

| Filename | Figure |
| --- | --- |
| `integration_umap_by_study.png` | UMAP colored by study label in `examples/tex_atlas/reference_metadata.csv` |
| `integration_umap_by_sample.png` | UMAP colored by Tex state in `examples/tex_atlas/reference_metadata.csv` |
| `markers_naive.png` | UMAP — naive markers (SELL, CCR7, LEF1, TCF7, IL7R, BACH2) |
| `markers_memory.png` | UMAP — memory/stem markers (TCF7, IL7R, LEF1, SELL, SLAMF6, BACH2) |
| `markers_exhaustion.png` | UMAP — exhaustion markers (PDCD1, HAVCR2, LAG3, TOX, TIGIT, ENTPD1) |
| `markers_effector.png` | UMAP — effector markers (GZMB, PRF1, IFNG, KLRG1, CX3CR1, NKG7) |

The integration and marker figures are generated from the checked-in bundled atlas under
`examples/tex_atlas`, so they can be regenerated without external data access.
