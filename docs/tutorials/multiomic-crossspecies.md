# Multiomic & cross-species mapping

## scATAC (multiome)

Peaks are collapsed to gene activity via a peak→gene link table, then projected onto the shared
map. Enable it in the config:

```yaml
scatac:
  enabled: true
  peaks: scatac_peaks.csv
  metadata: scatac_metadata.csv
  peak_gene_links: scatac_peak_gene_links.csv
```

Running `texmap run` writes `tables/scatac_projection.csv` and adds `scATAC_query` points to the
integrated embedding.

## Bulk RNA

```yaml
bulk_rna:
  enabled: true
  expression: bulk_expression.csv
```

Bulk samples are log-normalized and projected to their nearest reference profiles
(`tables/bulk_rna_projection.csv`), so legacy bulk datasets can be read in the exhaustion frame.

## Cross-species

Because projection happens in interpretable axis space, **mouse and human harmonize into a common
representation**. Markers are matched case-insensitively, so a mouse-cased query (e.g. `Tox`,
`Pdcd1`) maps onto the atlas:

```python
from texmap import TexMap
from texmap.io import read_counts
tm = TexMap.from_config("examples/tex_atlas/config.yaml")
tm.project(read_counts("examples/tex_atlas/crossspecies_mouse_query.csv"), source="mouse")
```

The bundled atlas carries a `species` field, so you can color the map by species to see conserved
vs. species-specific structure.
