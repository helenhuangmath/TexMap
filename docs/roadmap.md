# TexMap Roadmap

TexMap is designed as a modular reference-mapping platform. The current repository contains the minimal runnable core; this roadmap records the larger goals.

## scRNA-seq

- Add AnnData/Scanpy-native I/O.
- Support 10x Matrix Market folders and `.h5ad` files.
- Add batch-aware normalization and integration options.
- Add scVI, scArches, Geneformer, and scGPT adapters.

## scATAC-seq

- Add peak-by-cell matrix loading.
- Compute gene activity scores.
- Add motif enrichment and TF activity modules.
- Link peaks to genes using distance, co-accessibility, and public enhancer resources.
- Display peak accessibility and gene activity in the web report.

## Epigenetic Knowledge Links

- ENCODE candidate cis-regulatory elements.
- Roadmap Epigenomics chromatin states.
- JASPAR/HOCOMOCO motif catalogs.
- GWAS Catalog and fine-mapped loci.
- Immune enhancer and disease-associated regulatory atlases.

## AI-Assisted Interpretation

- Summarize marker genes, pathway scores, and transferred labels.
- Generate conservative biological hypotheses with explicit evidence tables.
- Flag weak evidence, missing genes, and out-of-reference cell states.
- Export a collaborator-ready interpretation report.

## Cross-Species

- Add ortholog table ingestion.
- Track one-to-many and many-to-many ortholog mappings.
- Preserve species-specific genes instead of silently dropping them.
- Compare conserved and divergent pathway activity across species.
