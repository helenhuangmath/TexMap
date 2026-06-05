from __future__ import annotations

import html
import json
from pathlib import Path

from texmap.config import TexMapConfig
from texmap.io import read_table


def write_report(config: TexMapConfig, paths: dict[str, Path]) -> Path:
    embedding = _typed_records(read_table(paths["tables"] / "integrated_embedding.csv")) if (paths["tables"] / "integrated_embedding.csv").exists() else []
    pathways = _typed_records(read_table(paths["tables"] / "pathway_scores.csv")) if (paths["tables"] / "pathway_scores.csv").exists() else []
    qc = _typed_records(read_table(paths["tables"] / "cell_qc.csv")) if (paths["tables"] / "cell_qc.csv").exists() else []

    payload = {
        "project": config.output.project_name,
        "embedding": embedding,
        "pathwayColumns": [key for key in pathways[0].keys() if key != "cell"] if pathways else [],
        "pathways": pathways,
        "qcSummary": _qc_summary(qc),
    }

    out = paths["web"] / "index.html"
    out.write_text(_html(payload), encoding="utf-8")
    return out


def _typed_records(rows: list[dict[str, str]]) -> list[dict[str, object]]:
    return [{key: _typed(value) for key, value in row.items()} for row in rows]


def _typed(value: str) -> object:
    if value == "":
        return None
    try:
        return float(value)
    except ValueError:
        return value


def _qc_summary(qc: list[dict[str, object]]) -> dict[str, object]:
    if not qc:
        return {}
    counts = sorted(float(row.get("total_counts") or 0) for row in qc)
    genes = sorted(float(row.get("n_genes") or 0) for row in qc)
    return {"n_cells": len(qc), "median_counts": _median(counts), "median_genes": _median(genes)}


def _median(values: list[float]) -> float | None:
    if not values:
        return None
    mid = len(values) // 2
    if len(values) % 2:
        return values[mid]
    return (values[mid - 1] + values[mid]) / 2


def _html(payload: dict[str, object]) -> str:
    title = html.escape(str(payload["project"]))
    data = json.dumps(payload)
    return f"""<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>{title} | TexMap</title>
  <style>
    :root {{ color-scheme: light; --ink: #1d2433; --muted: #5f6b7a; --line: #d8dee8; --query: #d94c36; --ref: #32746d; }}
    body {{ margin: 0; font-family: Arial, Helvetica, sans-serif; color: var(--ink); background: #f7f8fa; }}
    header {{ padding: 24px 32px 16px; background: #ffffff; border-bottom: 1px solid var(--line); }}
    h1 {{ margin: 0 0 6px; font-size: 28px; letter-spacing: 0; }}
    main {{ display: grid; grid-template-columns: minmax(360px, 1fr) 340px; gap: 18px; padding: 18px 32px 32px; }}
    section, aside {{ background: #ffffff; border: 1px solid var(--line); border-radius: 8px; }}
    .plot-wrap {{ padding: 16px; min-height: 620px; }}
    canvas {{ width: 100%; height: 560px; border: 1px solid var(--line); border-radius: 6px; background: #fbfcfd; }}
    aside {{ padding: 16px; }}
    .metrics {{ display: grid; grid-template-columns: repeat(3, 1fr); gap: 8px; margin-top: 12px; }}
    .metric {{ border: 1px solid var(--line); border-radius: 6px; padding: 10px; background: #fbfcfd; }}
    .metric strong {{ display: block; font-size: 20px; }}
    label {{ display: block; font-size: 13px; color: var(--muted); margin: 14px 0 6px; }}
    select {{ width: 100%; min-height: 36px; border: 1px solid var(--line); border-radius: 6px; padding: 6px 8px; background: white; }}
    table {{ width: 100%; border-collapse: collapse; font-size: 13px; margin-top: 12px; }}
    th, td {{ text-align: left; border-bottom: 1px solid var(--line); padding: 7px 4px; }}
    .legend {{ display: flex; gap: 16px; align-items: center; margin-top: 10px; color: var(--muted); font-size: 13px; }}
    .dot {{ width: 10px; height: 10px; border-radius: 50%; display: inline-block; margin-right: 6px; }}
    @media (max-width: 860px) {{ main {{ grid-template-columns: 1fr; padding: 12px; }} header {{ padding: 18px 12px; }} canvas {{ height: 420px; }} }}
  </style>
</head>
<body>
  <header>
    <h1>{title}</h1>
    <div>TexMap integration report</div>
    <div class="metrics" id="metrics"></div>
  </header>
  <main>
    <section class="plot-wrap">
      <canvas id="plot" width="1100" height="760"></canvas>
      <div class="legend"><span><i class="dot" style="background: var(--ref)"></i>reference</span><span><i class="dot" style="background: var(--query)"></i>query</span></div>
    </section>
    <aside>
      <label for="pathway">Pathway score</label>
      <select id="pathway"></select>
      <table>
        <thead><tr><th>Cell</th><th>Nearest label</th><th>Score</th></tr></thead>
        <tbody id="topCells"></tbody>
      </table>
    </aside>
  </main>
  <script>
    const TEXMAP = {data};
    const canvas = document.getElementById('plot');
    const ctx = canvas.getContext('2d');
    const pathwaySelect = document.getElementById('pathway');
    const pathwayByCell = new Map(TEXMAP.pathways.map(d => [d.cell, d]));
    for (const col of TEXMAP.pathwayColumns) {{
      const opt = document.createElement('option');
      opt.value = col; opt.textContent = col; pathwaySelect.appendChild(opt);
    }}
    function metric(label, value) {{
      return `<div class="metric"><strong>${{value ?? 'NA'}}</strong><span>${{label}}</span></div>`;
    }}
    document.getElementById('metrics').innerHTML = [
      metric('cells', TEXMAP.qcSummary.n_cells ?? TEXMAP.embedding.length),
      metric('median counts', Math.round(TEXMAP.qcSummary.median_counts ?? 0)),
      metric('median genes', Math.round(TEXMAP.qcSummary.median_genes ?? 0))
    ].join('');
    function draw() {{
      ctx.clearRect(0, 0, canvas.width, canvas.height);
      const pts = TEXMAP.embedding.filter(d => Number.isFinite(d.UMAP1) && Number.isFinite(d.UMAP2));
      if (!pts.length) return;
      const xs = pts.map(d => d.UMAP1), ys = pts.map(d => d.UMAP2);
      const minX = Math.min(...xs), maxX = Math.max(...xs), minY = Math.min(...ys), maxY = Math.max(...ys);
      const pad = 54;
      const scaleX = x => pad + (x - minX) / ((maxX - minX) || 1) * (canvas.width - pad * 2);
      const scaleY = y => canvas.height - pad - (y - minY) / ((maxY - minY) || 1) * (canvas.height - pad * 2);
      ctx.font = '18px Arial';
      ctx.fillStyle = '#1d2433';
      ctx.fillText('Integrated UMAP / projected query coordinates', pad, 32);
      for (const p of pts) {{
        ctx.beginPath();
        ctx.arc(scaleX(p.UMAP1), scaleY(p.UMAP2), p.source === 'query' ? 6 : 4, 0, Math.PI * 2);
        ctx.fillStyle = p.source === 'query' ? '#d94c36' : '#32746d';
        ctx.globalAlpha = p.source === 'query' ? 0.9 : 0.55;
        ctx.fill();
      }}
      ctx.globalAlpha = 1;
    }}
    function updateTable() {{
      const col = pathwaySelect.value;
      const rows = TEXMAP.embedding
        .filter(d => d.source === 'query')
        .map(d => ({{...d, score: pathwayByCell.get(d.cell)?.[col] ?? 0}}))
        .sort((a, b) => b.score - a.score)
        .slice(0, 12);
      document.getElementById('topCells').innerHTML = rows.map(r =>
        `<tr><td>${{r.cell}}</td><td>${{r.predicted_label ?? ''}}</td><td>${{Number(r.score).toFixed(3)}}</td></tr>`
      ).join('');
    }}
    pathwaySelect.addEventListener('change', updateTable);
    draw(); updateTable();
  </script>
</body>
</html>
"""
