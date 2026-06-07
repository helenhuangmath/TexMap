"""Generate a self-contained demo Tex reference atlas + example query inputs.

`texmap demo` writes a synthetic-but-biologically-styled CD8 T-cell exhaustion atlas
(naive/memory -> effector -> progenitor-exhausted -> intermediate -> terminal, plus a
proliferating branch) across mouse and human, single-cell and bulk and ATAC modalities.

It is generated deterministically (fixed seed) so the web app, tests, and screenshots
are reproducible. This stands in for the real Module-1 atlas described in note.txt,
which would aggregate 100+ public studies.
"""
from __future__ import annotations

import math
import random
from pathlib import Path
from typing import Dict, List

from texmap.io import write_table
from texmap.pathways import compute_pathway_scores  # noqa: F401  (kept for API parity)
from texmap.projection import normalize
from texmap.tex_axes import marker_expression, marker_panel, score_tex_axes

# State programs: genes that are highly expressed in each state. score_tex_axes turns
# these into the continuous coordinates, so we only need plausible relative levels.
STATE_PROGRAMS: Dict[str, Dict[str, float]] = {
    "Naive/Memory": {"TCF7": 9, "SELL": 9, "IL7R": 8, "CCR7": 8, "LEF1": 7, "BACH2": 6, "SLAMF6": 5},
    "Effector": {"GZMK": 8, "GZMB": 7, "IFNG": 6, "NKG7": 7, "KLRD1": 6, "CX3CR1": 5, "TBX21": 6, "PRF1": 6},
    "Tpex (progenitor exhausted)": {"TCF7": 7, "SLAMF6": 7, "PDCD1": 6, "TOX": 5, "IL7R": 5, "LAG3": 4, "BACH2": 5},
    "Tex-intermediate": {"PDCD1": 7, "TOX": 7, "LAG3": 6, "TIGIT": 6, "GZMK": 5, "ENTPD1": 5, "NR4A2": 5},
    "Tex-terminal": {"PDCD1": 9, "HAVCR2": 9, "LAG3": 8, "TIGIT": 7, "TOX": 8, "ENTPD1": 8, "GZMB": 7, "PRF1": 6,
                     "PRDM1": 6, "CD160": 6, "NR4A1": 6, "NR4A3": 6, "EGR2": 5, "IKZF2": 5},
    "Tex-proliferating": {"MKI67": 9, "TOP2A": 8, "PCNA": 7, "BIRC5": 6, "CDK1": 6, "STMN1": 6,
                          "PDCD1": 6, "TOX": 6, "LAG3": 5, "GZMB": 5},
}

FILLER_GENES = ["ACTB", "GAPDH", "B2M", "RPL13", "MALAT1", "CD8A", "CD8B", "CD3D", "CD3E", "TRAC", "PTPRC"]

# Roughly how many cells per state, and per (species) split.
STATE_ABUNDANCE = {
    "Naive/Memory": 240,
    "Effector": 200,
    "Tpex (progenitor exhausted)": 170,
    "Tex-intermediate": 220,
    "Tex-terminal": 260,
    "Tex-proliferating": 110,
}

STUDIES = ["LCMV_chronic_2023", "B16_tumor_2022", "HCC_human_2024", "CART_relapse_2024", "Melanoma_ICB_2023"]


def _all_genes() -> List[str]:
    genes = set(FILLER_GENES)
    for prog in STATE_PROGRAMS.values():
        genes.update(prog)
    # ensure every axis marker exists so scoring is well defined
    from texmap.tex_axes import TEX_AXES
    for axis in TEX_AXES.values():
        for direction in axis.values():
            genes.update(direction)
    return sorted(genes)


def _gen_cell(rng: random.Random, program: Dict[str, float], genes: List[str]) -> Dict[str, float]:
    counts = {}
    depth = rng.uniform(0.7, 1.4)
    for g in genes:
        base = program.get(g, 0.4)  # low background for non-program genes
        # Poisson-ish count via gamma noise
        lam = max(0.0, base * depth * rng.uniform(0.6, 1.4))
        counts[g] = float(round(lam * rng.uniform(0.8, 1.2) * 6))
    # a few housekeeping genes are always on
    for g in ("ACTB", "GAPDH", "B2M", "CD8A", "CD3D"):
        counts[g] = float(round(rng.uniform(20, 60)))
    return counts


def build_atlas(out_dir: Path, seed: int = 13) -> Path:
    rng = random.Random(seed)
    genes = _all_genes()

    raw_counts: Dict[str, Dict[str, float]] = {}
    meta_rows: List[dict] = []
    cell_idx = 0
    for state, n in STATE_ABUNDANCE.items():
        program = STATE_PROGRAMS[state]
        for _ in range(n):
            species = "human" if rng.random() < 0.5 else "mouse"
            study = rng.choice(STUDIES)
            cell = f"ref_{cell_idx:05d}"
            raw_counts[cell] = _gen_cell(rng, program, genes)
            meta_rows.append({
                "cell": cell,
                "cell_type": state,
                "tex_state": state,
                "species": species,
                "modality": "scRNA",
                "study": study,
            })
            cell_idx += 1

    normalized = normalize(raw_counts)
    axes = score_tex_axes(normalized)

    # Lay out a 2D map whose geometry tracks the exhaustion trajectory, so axis-space
    # projection lands query cells in a biologically sensible place.
    embedding_rows: List[dict] = []
    for row in meta_rows:
        cell = row["cell"]
        a = axes[cell]
        branch = 4.5 if row["tex_state"] == "Tex-proliferating" else 0.0
        u1 = 9.0 * a["Terminality"] - 4.5 + rng.uniform(-0.6, 0.6)
        u2 = 6.0 * a["Exhaustion"] - 3.0 + branch + rng.uniform(-0.6, 0.6)
        erow = {"cell": cell, "UMAP1": round(u1, 4), "UMAP2": round(u2, 4)}
        for axis in ("Exhaustion", "Stemness", "Terminality", "Cytotoxicity", "Proliferation", "ChromatinFixation"):
            erow[axis] = a[axis]
        embedding_rows.append(erow)

    out_dir.mkdir(parents=True, exist_ok=True)
    write_table(out_dir / "reference_embedding.csv", embedding_rows)
    write_table(out_dir / "reference_metadata.csv", meta_rows)

    # marker-gene expression panel for cellxgene-style color-by-gene
    panel = marker_panel()
    marker_expr = marker_expression(normalized, panel)
    write_table(out_dir / "reference_markers.csv",
                [{"cell": c, **marker_expr[c]} for c in raw_counts])

    _write_pathways(out_dir / "tex_pathways.tsv")
    _write_query_examples(out_dir, genes, rng)
    _write_multiomic_example(out_dir, genes, rng)
    _write_crossspecies_example(out_dir, genes, rng)
    _write_clinical_cohort(out_dir, rng)
    _write_config(out_dir)
    return out_dir / "reference_embedding.csv"


def _write_multiomic_example(out_dir: Path, genes: List[str], rng: random.Random) -> None:
    """scATAC (multiome) example: a peak-by-cell matrix + peak→gene links + metadata.

    Peaks are named for the gene whose promoter/enhancer they tag, so peak→gene collapse
    yields gene-activity that projects onto the shared RNA map (multiomic mapping).
    """
    peak_genes = ["PDCD1", "HAVCR2", "LAG3", "TOX", "TCF7", "GZMB", "TBX21", "ENTPD1",
                  "IL7R", "SELL", "MKI67", "NR4A2"]
    peaks = [f"peak_{g}_{k}" for g in peak_genes for k in (1, 2)]
    links = [{"peak": p, "gene": p.split("_")[1]} for p in peaks]
    write_table(out_dir / "scatac_peak_gene_links.csv", links, index_name="peak")

    mix = (["Tex-terminal"] * 5 + ["Tpex (progenitor exhausted)"] * 3 + ["Effector"] * 2)
    rows = []
    for i, state in enumerate(mix):
        prog = STATE_PROGRAMS[state]
        row = {"cell": f"ATAC_{i:02d}"}
        for p in peaks:
            g = p.split("_")[1]
            base = prog.get(g, 0.4)
            row[p] = float(round(max(0.0, base * rng.uniform(0.4, 1.3))))
        rows.append(row)
    write_table(out_dir / "scatac_peaks.csv", rows)
    write_table(out_dir / "scatac_metadata.csv",
                [{"cell": f"ATAC_{i:02d}", "modality": "scATAC", "expected_label": s}
                 for i, s in enumerate(mix)])


def _write_crossspecies_example(out_dir: Path, genes: List[str], rng: random.Random) -> None:
    """Cross-species example: a MOUSE query using mouse gene casing (Tox, Pdcd1, …).

    TexMap matches markers case-insensitively, so mouse symbols harmonize onto the
    (human+mouse) atlas — demonstrating species-agnostic axis-space projection.
    """
    mix = ["Tex-terminal"] * 4 + ["Tpex (progenitor exhausted)"] * 3 + ["Effector"] * 3
    rows = []
    for i, state in enumerate(mix):
        counts = _gen_cell(rng, STATE_PROGRAMS[state], genes)
        # rename to mouse casing (Title-case) to mimic a mouse dataset
        mouse = {g.capitalize(): v for g, v in counts.items()}
        rows.append({"cell": f"mouse_TIL_{i:02d}", **mouse})
    write_table(out_dir / "crossspecies_mouse_query.csv", rows)
    write_table(out_dir / "crossspecies_metadata.csv",
                [{"cell": f"mouse_TIL_{i:02d}", "species": "mouse", "expected_label": s}
                 for i, s in enumerate(mix)])


def _write_clinical_cohort(out_dir: Path, rng: random.Random) -> None:
    """A synthetic patient cohort for the clinical-translation benchmark.

    Biology baked in (a real finding): stem-like/progenitor-exhausted tumors respond better
    to checkpoint blockade and survive longer; terminally-exhausted tumors do worse. So
    Stemness is protective and Exhaustion/Terminality are adverse.
    """
    rows = []
    for i in range(80):
        stemness = round(rng.betavariate(2, 2), 3)
        exhaustion = round(1 - stemness + rng.uniform(-0.15, 0.15), 3)
        exhaustion = min(1.0, max(0.0, exhaustion))
        terminality = round(min(1.0, max(0.0, exhaustion + rng.uniform(-0.2, 0.2))), 3)
        # ICB response: more likely with high stemness (logistic)
        logit = 3.0 * (stemness - 0.5) - 1.2 * (terminality - 0.5)
        p = 1 / (1 + math.exp(-logit))
        response = 1 if rng.random() < p else 0
        # survival: hazard rises with exhaustion; responders live longer
        base = rng.expovariate(1.0)
        time = round(40 * base * math.exp(-1.4 * exhaustion) * (1.5 if response else 1.0) + 1, 1)
        event = 1 if rng.random() < (0.4 + 0.4 * exhaustion) else 0  # censoring
        rows.append({
            "patient": f"P{i:03d}",
            "Stemness": stemness, "Exhaustion": exhaustion, "Terminality": terminality,
            "response": response, "time": time, "event": event,
        })
    write_table(out_dir / "clinical_cohort.csv", rows)


def _write_pathways(path: Path) -> None:
    pathways = {
        "Inhibitory_receptors": ["PDCD1", "HAVCR2", "LAG3", "TIGIT", "CTLA4", "CD160", "ENTPD1"],
        "Exhaustion_TFs": ["TOX", "NR4A1", "NR4A2", "NR4A3", "EGR2", "PRDM1", "BATF"],
        "Stemness_memory": ["TCF7", "SELL", "IL7R", "CCR7", "LEF1", "BACH2", "SLAMF6"],
        "Cytotoxicity": ["GZMB", "GZMK", "PRF1", "GNLY", "NKG7", "IFNG", "KLRD1"],
        "Proliferation": ["MKI67", "TOP2A", "PCNA", "BIRC5", "CDK1", "STMN1"],
        "TCR_signaling": ["NR4A1", "EGR2", "CD3D", "CD3E", "TRAC", "BATF"],
    }
    lines = ["\t".join([name, *genes]) for name, genes in pathways.items()]
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def _write_query_examples(out_dir: Path, genes: List[str], rng: random.Random) -> None:
    # A small tumor-infiltrating-lymphocyte query skewed toward terminal exhaustion.
    query_rows = []
    mix = (["Tex-terminal"] * 6 + ["Tex-intermediate"] * 4 + ["Tpex (progenitor exhausted)"] * 3
           + ["Effector"] * 2 + ["Tex-proliferating"] * 2)
    for i, state in enumerate(mix):
        counts = _gen_cell(rng, STATE_PROGRAMS[state], genes)
        query_rows.append({"cell": f"TIL_{i:02d}", **counts})
    write_table(out_dir / "query_counts.csv", query_rows)

    meta = [{"cell": f"TIL_{i:02d}", "sample": "patient_TIL", "expected_label": s}
            for i, s in enumerate(mix)]
    write_table(out_dir / "query_metadata.csv", meta)

    # Bulk RNA pseudo-samples (Module: bulk mapping / deconvolution input).
    bulk_rows = []
    for name, state in [("bulk_chronic", "Tex-terminal"), ("bulk_acute", "Effector"),
                        ("bulk_responder", "Tpex (progenitor exhausted)")]:
        agg: Dict[str, float] = {g: 0.0 for g in genes}
        for _ in range(40):
            c = _gen_cell(rng, STATE_PROGRAMS[state], genes)
            for g in genes:
                agg[g] += c[g]
        bulk_rows.append({"cell": name, **{g: round(agg[g], 1) for g in genes}})
    write_table(out_dir / "bulk_expression.csv", bulk_rows)


def _write_config(out_dir: Path) -> None:
    config = f"""# TexMap demo atlas configuration
input:
  counts: query_counts.csv
  metadata: query_metadata.csv
  format: csv

reference:
  embedding: reference_embedding.csv
  metadata: reference_metadata.csv
  label_column: cell_type

analysis:
  min_genes: 1
  min_cells: 1
  n_hvg: 200
  pathway_sets: tex_pathways.tsv

scatac:
  enabled: true
  peaks: scatac_peaks.csv
  metadata: scatac_metadata.csv
  peak_gene_links: scatac_peak_gene_links.csv

bulk_rna:
  enabled: true
  expression: bulk_expression.csv

output:
  directory: ../../outputs/tex_atlas
  project_name: TexMap CD8 Exhaustion Atlas (demo)
"""
    (out_dir / "config.yaml").write_text(config, encoding="utf-8")
