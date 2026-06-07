# TexMap: Open Infrastructure for Mapping T Cell Exhaustion Across Single-Cell, Bulk, Multiomic, and Epigenetic Data

## Short Summary

T cell exhaustion is a fundamental immune differentiation state that shapes outcomes in chronic infection, cancer, immunotherapy, autoimmunity, and adoptive cell therapies. Exhausted T cells exist along a continuum ranging from stem-like progenitor states with therapeutic potential to terminally differentiated and epigenetically fixed dysfunctional states. Although hundreds of studies have generated transcriptomic, epigenomic, and perturbational datasets describing exhaustion, the field still lacks a shared framework for comparing exhaustion states across datasets, species, disease contexts, and experimental systems.

Current studies frequently use different preprocessing methods, annotations, markers, and definitions of exhaustion, making it difficult for researchers to determine whether newly generated data resemble previously described biological states. Existing reference-mapping tools provide valuable foundations for cell annotation, but they are not designed to create a unified coordinate system for exhaustion biology or to integrate transcriptomic, epigenetic, perturbational, and bulk RNA-seq data into a common framework.

TexMap addresses this gap by establishing an open-source computational infrastructure for T cell exhaustion mapping. The long-term vision is to create a universal coordinate system that allows researchers to determine where cells, patient samples, and perturbations fall within the global landscape of T cell exhaustion.

Rather than assigning cells only to discrete labels such as progenitor, intermediate, or terminal exhausted T cells, TexMap represents exhaustion as a continuous biological landscape defined by interpretable dimensions including stemness, terminal differentiation, proliferative capacity, dysfunction, chromatin fixation, and therapeutic responsiveness.

TexMap integrates single-cell RNA-seq, scATAC-seq, multiome, perturbation, epigenetic, and bulk transcriptomic data into a unified framework. Researchers can project new datasets into the TexMap reference space, quantify similarity to known exhaustion programs, identify regulatory mechanisms driving state transitions, and generate reproducible biological interpretations through both an interactive web interface and AI-assisted, tool-using workflows.

By creating a shared coordinate system for exhaustion biology, TexMap transforms fragmented public datasets into a reusable scientific resource and provides open infrastructure for immunologists, computational biologists, and future AI systems.

---

## Work Already Established

We have developed a working, end-to-end alpha of TexMap that already implements the core of this vision as runnable, tested software. It is delivered as an open-source Python package with a dependency-free core, an interactive web application, a programmatic API, and an automated test suite. The current release demonstrates, in functional form, every major capability described in the aims below; the proposed work scales these from a demonstrator built on a reproducible reference into robust, real-data, benchmarked, community-maintained infrastructure.

**Continuous exhaustion coordinate system.** TexMap scores every cell on six continuous, interpretable axes — Exhaustion, Stemness, Terminality, Cytotoxicity, Proliferation, and a Chromatin-fixation proxy — from curated marker programs, plus a derived discrete state for convenience. These coordinates are model-agnostic by design, so the axis basis can later be replaced by foundation-model latent dimensions without changing the rest of the stack.

**Reference projection and query modes.** A one-command projection engine harmonizes an arbitrary query (single-cell, bulk, or ATAC-derived) and places it into the shared coordinate system via k-nearest-neighbour transfer in axis space. Supported query modes include: project a new dataset to the atlas, integrate all datasets, label transfer, find nearest exhaustion states, and compare conditions. Each projection returns a state-composition breakdown, mean axes, and a per-cell projection-confidence score.

**Selectable integration engine.** Users choose an integration method — scVI (default), scANVI, scGPT (zero-shot and fine-tune), Harmony, or Seurat — through a unified interface. TexMap detects whether each backend library is installed and transparently falls back to its dependency-free axis-space engine, reporting which engine was used. This makes the platform a neutral substrate for benchmarking integration methods.

**Multimodal, cross-species, and bulk mapping.** scATAC-seq peaks are collapsed to gene activity and projected onto the shared map; bulk RNA-seq samples are normalized and projected as well; and because projection operates in interpretable axis space, mouse and human datasets harmonize into a common representation. Example inputs for each modality are bundled.

**Regulatory-network recovery.** TexMap recovers a transcription-factor → target regulatory network from reference co-expression (a GENIE3/SCENIC-style approach), signs each edge as activation or repression, and groups edges into exhaustion programs by axis. On the bundled atlas it recovers biologically sensible logic — for example, TOX driving the inhibitory-receptor program (PDCD1, LAG3, TIGIT, ENTPD1) and T-bet repressing TOX — visualized as an interactive network graph.

**Clinical-translation benchmark.** TexMap evaluates whether a Tex-derived predictor (e.g., Stemness or Exhaustion) predicts clinical outcome, computing AUROC (immunotherapy response, infection severity, CAR-T persistence), a concordance index, and a single-covariate Cox hazard ratio with a Wald p-value — all implemented from first principles with no heavy dependencies. On the bundled cohort, stem-like signal is protective and terminal exhaustion is adverse, recapitulating the established biology.

**Projection-accuracy benchmarking and TexBench.** A leave-one-out cell-state recovery routine reports accuracy, macro-F1, per-class metrics, and a confusion matrix. A "TexBench" dashboard aggregates projection accuracy, clinical metrics, and integration-method availability into a single benchmark view.

**Open-data interoperability.** TexMap queries the CZ CELLxGENE Discover API for exhaustion-relevant public datasets and deep-links each result into the cellxgene Explorer, with an offline curated catalog as a fallback. A `build-reference` command ingests a real expression matrix (CSV or `.h5ad`) into a TexMap reference, so the demonstrator atlas can be replaced with real, multi-study data.

**AI agent layer.** TexAgent is a tool-using agent: with an LLM key (Google Gemini or OpenAI, auto-detected) it runs a reasoning-action loop, calling real TexMap tools (regulatory network, projection accuracy, clinical benchmark, dataset search, atlas composition, marker lookup) and driving the interface (recoloring by axis or gene, opening the network). Without a key it falls back to a grounded, atlas-only engine. The model can be connected at runtime from the web interface.

**Interactive web application and programmatic API.** A cellxgene-style explorer (pan/zoom, color by axis / metadata / gene / pathway, region selection with live composition, per-cell inspection, dataset upload and projection) runs locally with no build step. All capabilities are also exposed through TexAPI — an in-process Python API, an HTTP client, and a documented REST surface — so other programs and AI systems can build on TexMap.

The existing framework demonstrates the feasibility of one-step projection of user datasets into curated exhaustion references and provides a strong, tested foundation. The proposed work will transform TexMap from this functional alpha into a robust, real-data-backed, extensively benchmarked, and community-maintained scientific infrastructure platform.

---

## Aim 1. Establish a Universal Coordinate System for T Cell Exhaustion

The first objective is to mature TexMap's continuous coordinate system from a working demonstrator into a rigorously validated, real-data-backed reference for exhaustion biology.

TexMap already quantifies continuous exhaustion coordinates representing stemness, terminal differentiation, activation state, dysfunction, proliferative capacity, and chromatin fixation, providing a common language for comparing cells across studies, disease settings, species, and technologies. The proposed work will (i) construct the production reference by aggregating and harmonizing real public exhaustion datasets across chronic infection, cancer, checkpoint blockade, and CAR-T dysfunction; (ii) learn or calibrate the coordinate basis against this real corpus, including the option to anchor axes in foundation-model embeddings; and (iii) strengthen the projection framework with confidence scoring, uncertainty estimation, out-of-reference detection, and curated benchmark datasets.

A prototype of these diagnostics already exists: every projection reports state composition, mean axes, and per-cell confidence. We will extend this into **Placement Diagnostics** designed specifically for experimental immunologists. When a user uploads a dataset, TexMap will automatically quantify overlap with curated exhaustion regions derived from chronic infection, cancer, checkpoint blockade, CAR-T dysfunction, and other contexts, and generate biologically interpretable summaries such as:

* 92% of uploaded CD8+ T cells overlap with the Chronic Viral Exhaustion reference region.
* 23% of cells occupy transitional states between progenitor and terminal exhaustion.
* The dataset most closely resembles checkpoint-blockade responder populations.
* A substantial fraction of cells fall outside existing references and may represent novel states.

These diagnostics will provide immediate biological context and help researchers relate new experiments to published exhaustion biology, building directly on the projection, accuracy-benchmarking, and reporting components already implemented.

---

## Aim 2. Expand TexMap Across Bulk RNA, Multiomic, Epigenetic, Species, and Disease Contexts

The second objective is to deepen TexMap's already-functional multimodal framework into a comprehensive, mechanistically interpretable system spanning modalities, species, and disease contexts.

TexMap already supports scATAC-seq (via gene activity), bulk RNA-seq, and cross-species (mouse/human) projection into a common exhaustion representation, and already recovers transcription-factor → target regulatory networks grouped into exhaustion programs. The proposed work will turn these demonstrators into production capabilities backed by real data and richer methods.

The **Bulk RNA Mapping** module will advance from nearest-profile projection to pseudo-bulk reference matrices and deconvolution-based estimation, visualizing bulk samples as probability-density clouds across the single-cell exhaustion landscape and estimating exhaustion-state composition (progenitor, transitional, terminal, or disease-specific). Because thousands of immunology studies contain bulk RNA-seq but no single-cell data, this will substantially broaden TexMap's impact.

The **Epigenetic Trajectory** module will extend the existing regulatory-network recovery by integrating chromatin accessibility, transcription-factor motif accessibility, enhancer activity, and histone-modification signatures. By combining expression with ATAC-seq footprinting and regulatory-program inference, TexMap will reconstruct continuous regulatory trajectories underlying exhaustion progression and let researchers visualize accessibility changes in key regulators such as TOX, TCF1, NR4A family members, BATF, AP-1 factors, and T-bet along the continuum. TexMap already generates interpretable TF–enhancer–target networks; we will link these to external epigenetic resources and chromatin states to characterize transitions from therapeutically reversible to terminally fixed dysfunction.

A long-term biological goal is to identify the regulatory "point of no return" at which exhausted cells become epigenetically committed to terminal dysfunction. TexMap will provide quantitative metrics and visualizations for investigating when these transitions occur and how they vary across diseases, species, and therapeutic interventions.

To maximize biological utility, TexMap will expand across disease contexts including chronic viral infection, cancer, CAR-T dysfunction, autoimmune disease, and immunotherapy-response cohorts, with cross-species references that reveal which exhaustion programs are conserved versus disease-specific. The selectable integration engine already in place (scVI, scANVI, scGPT, Harmony, Seurat, with transparent fallback) provides the substrate for benchmarking which methods best preserve exhaustion structure across these settings.

---

## Aim 3. Build an AI-Native Discovery Platform for Exhaustion Biology

The third objective is to mature TexMap's existing AI and API layers into a full AI-native discovery environment supporting both human researchers and automated reasoning systems.

TexMap already provides a tool-using agent that interacts directly with the reference atlas, projected datasets, regulatory networks, and benchmarks, and that drives the interface in response to natural-language requests. Researchers can already ask questions such as which programs drive a gene, how their cells are composed, or which datasets exist for a condition; the proposed work will broaden this to richer, multi-step scientific reasoning such as:

* Which chromatin programs distinguish responder and non-responder patients?
* Which transcription factors drive progression toward terminal exhaustion?
* Do my cells resemble chronic infection, tumor-associated exhaustion, or checkpoint-response states?
* Which regulatory programs emerge before epigenetic fixation occurs?

The agent already executes TexMap workflows, queries references and regulatory networks, and returns answers with a visible tool trace; we will extend it to retrieve external supporting evidence and generate reproducible reports with traceable provenance.

Beyond user interaction, TexMap already exposes projection coordinates, regulatory networks, pathway activities, confidence metrics, integration-method availability, and metadata through an open API (in-process Python, an HTTP client, and documented REST endpoints). We will extend this surface with standardized embeddings and biological knowledge graphs to support foundation-model development, AI-agent workflows, automated hypothesis generation, and downstream machine-learning applications.

We will also establish a self-improving reference ecosystem in which newly generated public datasets — discoverable today through the integrated CELLxGENE search and ingestible through the `build-reference` pipeline — can be evaluated, benchmarked, quality-controlled, and incorporated into future TexMap releases. Rather than a static atlas, TexMap will evolve alongside the field while preserving reproducibility through rigorous versioning, provenance tracking, and benchmarking.

The long-term vision is an open scientific infrastructure layer that enables both researchers and AI systems to reason over the global landscape of exhaustion biology.

---

## Expected Value

TexMap lowers the barrier for immunologists to interpret new datasets within the context of published exhaustion biology. Instead of manually reconciling cell labels, pathway scores, chromatin states, species differences, and modality-specific analyses across multiple tools, researchers obtain biologically interpretable exhaustion coordinates, regulatory-program summaries, confidence estimates, clinical-association metrics, and shareable reports through a single reproducible workflow — already demonstrated in the alpha.

For computational biologists, TexMap provides a transparent framework for benchmarking projection methods, integration approaches, regulatory-network inference, and cross-modality analyses, with a built-in benchmark dashboard. For immunologists, it provides a practical mechanism for determining where cells, patient samples, and perturbations fall within the broader exhaustion landscape, and whether those positions carry clinical meaning. For AI researchers, it provides structured, reference-aligned, machine-readable representations of exhaustion biology — served through an open API — suitable for foundation-model training and automated scientific reasoning.

By funding TexMap, OS4Science would support open-source scientific infrastructure that is already functional and tested, and would accelerate its expansion into a real-data-backed, community-maintained resource that transforms fragmented exhaustion datasets into a reusable, interpretable, and AI-ready resource for the broader immunology community.
