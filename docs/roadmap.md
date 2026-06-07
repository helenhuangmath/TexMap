# TexMap Roadmap

TexMap is designed as a modular reference-mapping platform. This roadmap records the larger
goals and what is implemented today.

## Implemented now

- **Continuous exhaustion axes** (`texmap.tex_axes`) — Exhaustion, Stemness, Terminality,
  Cytotoxicity, Proliferation, ChromatinFixation, scored from curated marker programs.
- **Reference projection engine** (`texmap.projection`) — axis-space kNN transfer that places
  any query (sc / bulk / ATAC-derived) into the shared coordinate system with confidence and
  state composition. This is Module 2 from the project notes.
- **Interactive web explorer** (`texmap serve`) — pan/zoom atlas, color by axis / metadata /
  pathway, upload-and-project, per-cell detail, and a natural-language agent.
- **TexAgent** (`texmap.texagent`) — grounded offline NL engine with optional live LLM
  backend when a supported provider key is present.
- **Demo atlas generator** (`texmap demo`) — 1,200-cell synthetic-but-biologically-styled CD8
  exhaustion atlas across mouse/human, single-cell and bulk, so the explorer runs immediately.
- **Multimodal projection** (`texmap.multimodal`) — scATAC peak→gene-activity and bulk RNA
  projected onto the shared map.

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
