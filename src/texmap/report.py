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
    predictions = _typed_records(read_table(paths["benchmark"] / "predictions.csv")) if (paths["benchmark"] / "predictions.csv").exists() else []
    scatac_projection = _typed_records(read_table(paths["tables"] / "scatac_projection.csv")) if (paths["tables"] / "scatac_projection.csv").exists() else []
    bulk_rna_projection = _typed_records(read_table(paths["tables"] / "bulk_rna_projection.csv")) if (paths["tables"] / "bulk_rna_projection.csv").exists() else []
    figures = _figure_records(paths)
    interpretation = _load_json(paths["agent"] / "interpretation.json")
    agent_result = _load_json(paths["agent"] / "run_result.json")
    ml_manifest = _load_json(paths["feature_matrix"] / "manifest.json")
    fm_manifest = _load_json(paths["foundation_models"] / "adapter_manifest.json")
    benchmark_metrics = _load_json(paths["benchmark"] / "metrics.json")
    scalability_plan = _load_json(paths["scalability"] / "projection_plan.json")
    multimodal_summary = _load_json(paths["multimodal"] / "projection_summary.json")

    payload = {
        "project": config.output.project_name,
        "embedding": embedding,
        "pathwayColumns": [key for key in pathways[0].keys() if key != "cell"] if pathways else [],
        "pathways": pathways,
        "predictions": predictions,
        "scatacProjection": scatac_projection,
        "bulkRnaProjection": bulk_rna_projection,
        "sourceCounts": _source_counts(embedding),
        "qcSummary": _qc_summary(qc),
        "figures": figures,
        "interpretation": interpretation,
        "agentResult": agent_result,
        "mlManifest": ml_manifest,
        "foundationModelManifest": fm_manifest,
        "benchmarkMetrics": benchmark_metrics,
        "scalabilityPlan": scalability_plan,
        "multimodalSummary": multimodal_summary,
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


def _source_counts(embedding: list[dict[str, object]]) -> dict[str, int]:
    counts: dict[str, int] = {}
    for row in embedding:
        source = str(row.get("source") or "unknown")
        counts[source] = counts.get(source, 0) + 1
    return counts


def _median(values: list[float]) -> float | None:
    if not values:
        return None
    mid = len(values) // 2
    if len(values) % 2:
        return values[mid]
    return (values[mid - 1] + values[mid]) / 2


def _figure_records(paths: dict[str, Path]) -> list[dict[str, str]]:
    figure_dir = paths["figures"]
    names = {
        "integrated_umap.svg": ("Integrated UMAP", "Reference and query cells in shared map coordinates."),
        "pathway_heatmap.svg": ("Pathway Heatmap", "Pathway activity scores across query cells."),
    }
    records = []
    for path in sorted(figure_dir.glob("*")):
        if path.suffix.lower() not in {".svg", ".png", ".jpg", ".jpeg"}:
            continue
        title, caption = names.get(path.name, (_title_from_name(path.stem), "Generated TexMap figure."))
        records.append({"src": f"../figures/{path.name}", "title": title, "caption": caption})
    return records


def _title_from_name(name: str) -> str:
    return name.replace("_", " ").replace("-", " ").title()


def _load_json(path: Path) -> dict[str, object]:
    if not path.exists():
        return {}
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return {}


def _html(payload: dict[str, object]) -> str:
    title = html.escape(str(payload["project"]))
    template = """<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>__TITLE__ | TexMap</title>
  <style>
    :root { color-scheme: light; --ink: #1d2433; --muted: #5f6b7a; --line: #d8dee8; --soft: #f7f8fa; --query: #d94c36; --ref: #32746d; --accent: #255f85; }
    * { box-sizing: border-box; }
    body { margin: 0; font-family: Arial; color: var(--ink); background: var(--soft); }
    header { display: flex; justify-content: space-between; gap: 18px; align-items: flex-start; padding: 18px 24px 14px; background: #ffffff; border-bottom: 1px solid var(--line); }
    h1 { margin: 0 0 4px; font-size: 26px; letter-spacing: 0; }
    h2 { margin: 0; font-size: 16px; letter-spacing: 0; }
    button, select, input { font: inherit; }
    button { min-height: 34px; border: 1px solid var(--line); border-radius: 6px; background: #ffffff; color: var(--ink); padding: 6px 10px; cursor: pointer; }
    button:hover { border-color: var(--accent); }
    main { padding: 14px 18px 28px; }
    .muted { color: var(--muted); font-size: 13px; }
    .metrics { display: grid; grid-template-columns: repeat(3, 132px); gap: 8px; }
    .metric { border: 1px solid var(--line); border-radius: 6px; padding: 8px 10px; background: #fbfcfd; }
    .metric strong { display: block; font-size: 19px; }
    .explorer { display: grid; grid-template-columns: 260px minmax(520px, 1fr) 320px; gap: 14px; min-height: 720px; }
    .panel, .feature, .figure-card, .result-card { background: #ffffff; border: 1px solid var(--line); border-radius: 8px; }
    .panel { padding: 14px; }
    .panel h2 { margin-bottom: 12px; }
    label { display: block; font-size: 12px; color: var(--muted); margin: 12px 0 5px; }
    select, input[type="search"] { width: 100%; min-height: 34px; border: 1px solid var(--line); border-radius: 6px; padding: 6px 8px; background: white; }
    .check-row { display: flex; align-items: center; gap: 8px; margin: 8px 0; font-size: 13px; }
    .button-row { display: grid; grid-template-columns: 1fr 1fr; gap: 8px; margin-top: 12px; }
    .legend-list { display: grid; gap: 6px; margin-top: 8px; max-height: 180px; overflow: auto; }
    .legend-item { display: flex; align-items: center; gap: 8px; font-size: 12px; color: var(--muted); }
    .swatch { width: 11px; height: 11px; border-radius: 50%; border: 1px solid rgba(0,0,0,0.12); flex: 0 0 auto; }
    .canvas-panel { display: grid; grid-template-rows: auto 1fr auto; min-height: 720px; overflow: hidden; }
    .toolbar { display: flex; justify-content: space-between; align-items: center; gap: 10px; padding: 12px 14px; border-bottom: 1px solid var(--line); }
    .toolbar-left, .toolbar-right { display: flex; flex-wrap: wrap; align-items: center; gap: 8px; }
    .viewport { position: relative; min-height: 560px; background: #fbfcfd; }
    canvas { width: 100%; height: 100%; min-height: 560px; display: block; }
    .tooltip { position: absolute; pointer-events: none; z-index: 4; display: none; min-width: 160px; max-width: 260px; padding: 8px 10px; background: rgba(29,36,51,0.94); color: white; border-radius: 6px; font-size: 12px; line-height: 1.35; }
    .status-bar { display: flex; justify-content: space-between; gap: 12px; padding: 9px 14px; border-top: 1px solid var(--line); color: var(--muted); font-size: 12px; }
    .inspector dl { display: grid; grid-template-columns: 104px minmax(0, 1fr); gap: 7px 10px; margin: 0; font-size: 13px; }
    .inspector dt { color: var(--muted); }
    .inspector dd { margin: 0; overflow-wrap: anywhere; }
    table { width: 100%; border-collapse: collapse; font-size: 12px; margin-top: 10px; }
    th, td { text-align: left; border-bottom: 1px solid var(--line); padding: 6px 4px; }
    .tabs { display: flex; gap: 8px; margin: 14px 0 0; }
    .tabs button.active { border-color: var(--accent); background: #eaf3f7; }
    .tab-section { display: none; }
    .tab-section.active { display: block; }
    .feature-grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(260px, 1fr)); gap: 12px; margin-top: 14px; }
    .feature { padding: 14px 16px; }
    .feature h2 { margin-bottom: 8px; }
    .feature p { margin: 0 0 10px; color: var(--muted); line-height: 1.35; font-size: 13px; }
    .feature a { color: var(--accent); font-size: 13px; text-decoration: none; }
    .feature strong { font-size: 22px; display: block; margin-bottom: 4px; }
    .result-grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(320px, 1fr)); gap: 12px; margin-top: 14px; }
    .result-card { padding: 14px 16px; overflow: hidden; }
    .result-card h2 { margin-bottom: 8px; }
    .result-card p { margin: 0 0 10px; color: var(--muted); line-height: 1.4; font-size: 13px; }
    .result-stat { display: grid; grid-template-columns: repeat(auto-fit, minmax(116px, 1fr)); gap: 8px; margin-top: 10px; }
    .result-stat div { border: 1px solid var(--line); border-radius: 6px; padding: 8px; background: #fbfcfd; }
    .result-stat strong { display: block; font-size: 18px; }
    .table-wrap { overflow: auto; max-height: 360px; border: 1px solid var(--line); border-radius: 6px; margin-top: 10px; }
    .table-wrap table { margin: 0; min-width: 620px; }
    .download-link { display: inline-block; margin-top: 10px; color: var(--accent); font-size: 13px; text-decoration: none; }
    .gallery { display: grid; grid-template-columns: repeat(auto-fit, minmax(420px, 1fr)); gap: 14px; margin-top: 14px; }
    .figure-card { overflow: hidden; }
    .figure-card h2 { padding: 14px 16px 4px; }
    .figure-card p { margin: 0; padding: 0 16px 12px; color: var(--muted); font-size: 13px; }
    .figure-card a { display: block; color: inherit; text-decoration: none; }
    .figure-card img { display: block; width: 100%; height: auto; border-top: 1px solid var(--line); background: #ffffff; }
    @media (max-width: 1050px) { header { display: block; } .metrics { margin-top: 12px; grid-template-columns: repeat(3, 1fr); } .explorer { grid-template-columns: 1fr; } .canvas-panel { min-height: 620px; } }
  </style>
</head>
<body>
  <header>
    <div>
      <h1>__TITLE__</h1>
      <div class="muted">TexMap interactive explorer</div>
    </div>
    <div class="metrics" id="metrics"></div>
  </header>
  <main>
    <section class="explorer" aria-label="Interactive cell explorer">
      <aside class="panel">
        <h2>Explore</h2>
        <label for="search">Cell search</label>
        <input id="search" type="search" placeholder="source, label, point ID">
        <label for="colorMode">Color by</label>
        <select id="colorMode">
          <option value="source">source</option>
          <option value="label">predicted label</option>
          <option value="pathway">pathway score</option>
        </select>
        <label for="pathway">Pathway</label>
        <select id="pathway"></select>
        <label for="labelFilter">Label filter</label>
        <select id="labelFilter"><option value="all">all labels</option></select>
        <label for="sourceFilter">Source filter</label>
        <select id="sourceFilter"><option value="all">all sources</option></select>
        <div class="check-row"><input id="showReference" type="checkbox" checked><span>reference cells</span></div>
        <div class="check-row"><input id="showQuery" type="checkbox" checked><span>query and projected cells</span></div>
        <div class="button-row">
          <button id="resetView">Reset view</button>
          <button id="downloadSelection">Download selected</button>
        </div>
        <label>Legend</label>
        <div class="legend-list" id="legend"></div>
        <p class="muted">Wheel to zoom, drag to pan, click a point to inspect it.</p>
      </aside>
      <section class="canvas-panel">
        <div class="toolbar">
          <div class="toolbar-left">
            <strong>Integrated map</strong>
            <span class="muted" id="visibleCount"></span>
          </div>
          <div class="toolbar-right">
            <button id="zoomIn">+</button>
            <button id="zoomOut">-</button>
            <button id="copyCell">Copy point ID</button>
          </div>
        </div>
        <div class="viewport" id="viewport">
          <canvas id="plot" width="1200" height="760"></canvas>
          <div class="tooltip" id="tooltip"></div>
        </div>
        <div class="status-bar">
          <span id="hoverStatus">Hover over a point</span>
          <span id="viewStatus">zoom 1.00x</span>
        </div>
      </section>
      <aside class="panel inspector">
        <h2>Cell inspector</h2>
        <dl id="cellDetails"></dl>
        <table>
          <thead><tr><th>Point</th><th>Label</th><th>Score</th></tr></thead>
          <tbody id="topCells"></tbody>
        </table>
      </aside>
    </section>
    <div class="tabs">
      <button class="active" data-tab="summary">Summary</button>
      <button data-tab="benchmark">Benchmark</button>
      <button data-tab="multimodal">Multimodal</button>
      <button data-tab="pathwayResults">Pathways</button>
      <button data-tab="figures">Figures</button>
    </div>
    <section id="summary" class="tab-section active">__SUMMARY_RESULTS__</section>
    <section id="benchmark" class="tab-section">__BENCHMARK_RESULTS__</section>
    <section id="multimodal" class="tab-section">__MULTIMODAL_RESULTS__</section>
    <section id="pathwayResults" class="tab-section">__PATHWAY_RESULTS__</section>
    <section id="figures" class="tab-section"><div class="gallery">__FIGURE_CARDS__</div></section>
  </main>
  <script>
    const TEXMAP = __DATA__;
    const canvas = document.getElementById('plot');
    const ctx = canvas.getContext('2d');
    const viewport = document.getElementById('viewport');
    const tooltip = document.getElementById('tooltip');
    const pathwaySelect = document.getElementById('pathway');
    const colorMode = document.getElementById('colorMode');
    const labelFilter = document.getElementById('labelFilter');
    const sourceFilter = document.getElementById('sourceFilter');
    const search = document.getElementById('search');
    const showReference = document.getElementById('showReference');
    const showQuery = document.getElementById('showQuery');
    const selected = new Set();
    let activeCell = null;
    let dragging = false;
    let startPointer = null;
    let lastPointer = null;
    let view = { scale: 1, tx: 0, ty: 0 };
    const palette = ['#32746d','#d94c36','#255f85','#8a5a44','#7c6a0a','#7a4e9d','#218380','#d9822b','#6979f8','#c44569'];
    const pathwayByPoint = new Map(TEXMAP.pathways.map(d => [d.point_id, d]));
    const points = TEXMAP.embedding
      .filter(d => Number.isFinite(d.UMAP1) && Number.isFinite(d.UMAP2))
      .map(d => ({...d, x: d.UMAP1, y: d.UMAP2, screenX: 0, screenY: 0}));
    const sources = [...new Set(points.map(d => d.source || 'unknown'))].sort();
    const labels = [...new Set(points.map(d => d.predicted_label || (d.source === 'reference' ? 'reference' : 'unassigned')))].sort();
    const labelColors = new Map(labels.map((label, i) => [label, palette[i % palette.length]]));
    const sourceColors = new Map(sources.map((source, i) => [source, palette[i % palette.length]]));
    for (const col of TEXMAP.pathwayColumns) {
      const opt = document.createElement('option');
      opt.value = col; opt.textContent = col; pathwaySelect.appendChild(opt);
    }
    for (const label of labels.filter(l => l !== 'reference')) {
      const opt = document.createElement('option');
      opt.value = label; opt.textContent = label; labelFilter.appendChild(opt);
    }
    for (const source of sources) {
      const opt = document.createElement('option');
      opt.value = source; opt.textContent = source; sourceFilter.appendChild(opt);
    }
    function metric(label, value) {
      return `<div class="metric"><strong>${value ?? 'NA'}</strong><span>${label}</span></div>`;
    }
    document.getElementById('metrics').innerHTML = [
      metric('map points', TEXMAP.embedding.length),
      metric('scRNA cells', TEXMAP.qcSummary.n_cells ?? 0),
      metric('median counts', Math.round(TEXMAP.qcSummary.median_counts ?? 0)),
    ].join('');
    function resizeCanvas() {
      const rect = viewport.getBoundingClientRect();
      const ratio = window.devicePixelRatio || 1;
      canvas.width = Math.max(640, Math.floor(rect.width * ratio));
      canvas.height = Math.max(420, Math.floor(rect.height * ratio));
      ctx.setTransform(ratio, 0, 0, ratio, 0, 0);
      draw();
    }
    function filteredPoints() {
      const term = search.value.trim().toLowerCase();
      return points.filter(p => {
        if (p.source === 'reference' && !showReference.checked) return false;
        if (p.source !== 'reference' && !showQuery.checked) return false;
        if (sourceFilter.value !== 'all' && (p.source || '') !== sourceFilter.value) return false;
        if (labelFilter.value !== 'all' && (p.predicted_label || '') !== labelFilter.value) return false;
        if (term) {
          const hay = `${p.point_id} ${p.source} ${p.predicted_label || ''}`.toLowerCase();
          if (!hay.includes(term)) return false;
        }
        return true;
      });
    }
    const extent = (() => {
      const xs = points.map(d => d.x), ys = points.map(d => d.y);
      return { minX: Math.min(...xs), maxX: Math.max(...xs), minY: Math.min(...ys), maxY: Math.max(...ys) };
    })();
    function baseScale() {
      const rect = canvas.getBoundingClientRect();
      const sx = (rect.width - 96) / ((extent.maxX - extent.minX) || 1);
      const sy = (rect.height - 96) / ((extent.maxY - extent.minY) || 1);
      return Math.min(sx, sy);
    }
    function project(p) {
      const rect = canvas.getBoundingClientRect();
      const s = baseScale() * view.scale;
      const cx = (extent.minX + extent.maxX) / 2;
      const cy = (extent.minY + extent.maxY) / 2;
      return { x: rect.width / 2 + (p.x - cx) * s + view.tx, y: rect.height / 2 - (p.y - cy) * s + view.ty };
    }
    function colorFor(p) {
      if (colorMode.value === 'pathway') {
        const score = Number(pathwayByPoint.get(p.point_id)?.[pathwaySelect.value] ?? 0);
        const values = TEXMAP.pathways.map(d => Number(d[pathwaySelect.value] ?? 0));
        const max = Math.max(1, ...values);
        const t = Math.max(0, Math.min(1, score / max));
        const r = Math.round(237 + (217 - 237) * t);
        const g = Math.round(242 + (76 - 242) * t);
        const b = Math.round(247 + (54 - 247) * t);
        return `rgb(${r},${g},${b})`;
      }
      if (colorMode.value === 'label') return labelColors.get(p.predicted_label || (p.source === 'reference' ? 'reference' : 'unassigned')) || '#5f6b7a';
      return sourceColors.get(p.source || 'unknown') || '#5f6b7a';
    }
    function drawLegend() {
      const legend = document.getElementById('legend');
      if (colorMode.value === 'pathway') {
        legend.innerHTML = `<div class="legend-item"><span class="swatch" style="background:#edf2f7"></span>low ${pathwaySelect.value}</div><div class="legend-item"><span class="swatch" style="background:#d94c36"></span>high ${pathwaySelect.value}</div>`;
        return;
      }
      const items = colorMode.value === 'source'
        ? sources.map(source => [source, sourceColors.get(source)])
        : labels.map(label => [label, labelColors.get(label)]);
      legend.innerHTML = items.map(([label, color]) => `<div class="legend-item"><span class="swatch" style="background:${color}"></span>${label}</div>`).join('');
    }
    function draw() {
      const rect = canvas.getBoundingClientRect();
      ctx.clearRect(0, 0, rect.width, rect.height);
      ctx.fillStyle = '#fbfcfd';
      ctx.fillRect(0, 0, rect.width, rect.height);
      ctx.strokeStyle = '#e3e8ef';
      ctx.lineWidth = 1;
      for (let x = 60; x < rect.width; x += 80) { ctx.beginPath(); ctx.moveTo(x, 0); ctx.lineTo(x, rect.height); ctx.stroke(); }
      for (let y = 60; y < rect.height; y += 80) { ctx.beginPath(); ctx.moveTo(0, y); ctx.lineTo(rect.width, y); ctx.stroke(); }
      const pts = filteredPoints();
      for (const p of pts) {
        const xy = project(p);
        p.screenX = xy.x; p.screenY = xy.y;
        ctx.beginPath();
        ctx.arc(xy.x, xy.y, selected.has(p.point_id) || activeCell?.point_id === p.point_id ? 8 : (p.source === 'reference' ? 4 : 6), 0, Math.PI * 2);
        ctx.fillStyle = colorFor(p);
        ctx.globalAlpha = p.source === 'reference' ? 0.52 : 0.9;
        ctx.fill();
        if (selected.has(p.point_id) || activeCell?.point_id === p.point_id) {
          ctx.globalAlpha = 1;
          ctx.strokeStyle = '#1d2433';
          ctx.lineWidth = 2;
          ctx.stroke();
        }
      }
      ctx.globalAlpha = 1;
      document.getElementById('visibleCount').textContent = `${pts.length} visible / ${points.length} points`;
      document.getElementById('viewStatus').textContent = `zoom ${view.scale.toFixed(2)}x`;
      drawLegend();
    }
    function nearestCell(event) {
      const rect = canvas.getBoundingClientRect();
      const x = event.clientX - rect.left;
      const y = event.clientY - rect.top;
      let best = null, bestD = 16 * 16;
      for (const p of filteredPoints()) {
        const d = (p.screenX - x) ** 2 + (p.screenY - y) ** 2;
        if (d < bestD) { best = p; bestD = d; }
      }
      return best;
    }
    function setActiveCell(cell) {
      activeCell = cell;
      if (cell) selected.add(cell.point_id);
      const details = document.getElementById('cellDetails');
      if (!cell) {
        details.innerHTML = '<dt>Status</dt><dd>No point selected</dd>';
        return;
      }
      const scores = pathwayByPoint.get(cell.point_id) || {};
      details.innerHTML = [
        ['Point', cell.point_id],
        ['Source', cell.source],
        ['Label', cell.predicted_label || ''],
        ['Confidence', cell.projection_confidence ? Number(cell.projection_confidence).toFixed(3) : ''],
        ['UMAP1', Number(cell.UMAP1).toFixed(3)],
        ['UMAP2', Number(cell.UMAP2).toFixed(3)],
        [pathwaySelect.value, Number(scores[pathwaySelect.value] ?? 0).toFixed(3)]
      ].map(([k,v]) => `<dt>${k}</dt><dd>${v}</dd>`).join('');
      draw();
    }
    function showTooltip(event, cell) {
      if (!cell) {
        tooltip.style.display = 'none';
        document.getElementById('hoverStatus').textContent = 'Hover over a point';
        return;
      }
      const score = Number(pathwayByPoint.get(cell.point_id)?.[pathwaySelect.value] ?? 0).toFixed(3);
      tooltip.innerHTML = `<strong>Point ${cell.point_id}</strong><br>${cell.source}<br>${cell.predicted_label || ''}<br>${pathwaySelect.value}: ${score}`;
      tooltip.style.left = `${event.clientX - viewport.getBoundingClientRect().left + 12}px`;
      tooltip.style.top = `${event.clientY - viewport.getBoundingClientRect().top + 12}px`;
      tooltip.style.display = 'block';
      document.getElementById('hoverStatus').textContent = `Point ${cell.point_id} ${cell.predicted_label || ''}`;
    }
    function updateTable() {
      const col = pathwaySelect.value;
      const rows = points
        .filter(d => d.source !== 'reference')
        .map(d => ({...d, score: pathwayByPoint.get(d.point_id)?.[col] ?? 0}))
        .sort((a, b) => b.score - a.score)
        .slice(0, 12);
      document.getElementById('topCells').innerHTML = rows.map(r =>
        `<tr><td>${r.point_id}</td><td>${r.predicted_label ?? ''}</td><td>${Number(r.score).toFixed(3)}</td></tr>`
      ).join('');
    }
    function zoom(mult, origin) {
      const before = view.scale;
      view.scale = Math.max(0.35, Math.min(12, view.scale * mult));
      if (origin) {
        view.tx = origin.x - (origin.x - view.tx) * (view.scale / before);
        view.ty = origin.y - (origin.y - view.ty) * (view.scale / before);
      }
      draw();
    }
    canvas.addEventListener('wheel', event => {
      event.preventDefault();
      const rect = canvas.getBoundingClientRect();
      zoom(event.deltaY < 0 ? 1.16 : 0.86, { x: event.clientX - rect.left, y: event.clientY - rect.top });
    });
    canvas.addEventListener('pointerdown', event => { dragging = true; startPointer = { x: event.clientX, y: event.clientY }; lastPointer = startPointer; canvas.setPointerCapture(event.pointerId); });
    canvas.addEventListener('pointermove', event => {
      if (dragging && lastPointer) {
        view.tx += event.clientX - lastPointer.x;
        view.ty += event.clientY - lastPointer.y;
        lastPointer = { x: event.clientX, y: event.clientY };
        draw();
      } else {
        showTooltip(event, nearestCell(event));
      }
    });
    canvas.addEventListener('pointerup', event => {
      const moved = startPointer ? Math.abs(event.clientX - startPointer.x) + Math.abs(event.clientY - startPointer.y) : 0;
      dragging = false; lastPointer = null; startPointer = null;
      if (moved < 6) setActiveCell(nearestCell(event));
    });
    canvas.addEventListener('mouseleave', event => { dragging = false; lastPointer = null; startPointer = null; showTooltip(event, null); });
    document.getElementById('zoomIn').addEventListener('click', () => zoom(1.25));
    document.getElementById('zoomOut').addEventListener('click', () => zoom(0.8));
    document.getElementById('resetView').addEventListener('click', () => { view = { scale: 1, tx: 0, ty: 0 }; selected.clear(); setActiveCell(null); draw(); });
    document.getElementById('copyCell').addEventListener('click', async () => { if (activeCell && navigator.clipboard) await navigator.clipboard.writeText(String(activeCell.point_id)); });
    document.getElementById('downloadSelection').addEventListener('click', () => {
      const rows = points.filter(p => selected.has(p.point_id));
      const csv = ['point_id,source,predicted_label,UMAP1,UMAP2', ...rows.map(p => `${p.point_id},${p.source},${p.predicted_label || ''},${p.UMAP1},${p.UMAP2}`)].join('\\n');
      const a = document.createElement('a');
      a.href = URL.createObjectURL(new Blob([csv], { type: 'text/csv' }));
      a.download = 'texmap_selected_points.csv';
      a.click();
      URL.revokeObjectURL(a.href);
    });
    for (const el of [pathwaySelect, colorMode, labelFilter, sourceFilter, search, showReference, showQuery]) {
      el.addEventListener('input', () => { updateTable(); draw(); if (activeCell) setActiveCell(activeCell); });
    }
    document.querySelectorAll('.tabs button').forEach(btn => btn.addEventListener('click', () => {
      document.querySelectorAll('.tabs button').forEach(b => b.classList.remove('active'));
      document.querySelectorAll('.tab-section').forEach(s => s.classList.remove('active'));
      btn.classList.add('active');
      document.getElementById(btn.dataset.tab).classList.add('active');
    }));
    window.addEventListener('resize', resizeCanvas);
    resizeCanvas();
    setActiveCell(null);
    updateTable();
  </script>
</body>
</html>
"""
    return (
        template
        .replace("__TITLE__", title)
        .replace("__DATA__", json.dumps(_browser_payload(payload)))
        .replace("__SUMMARY_RESULTS__", _summary_results(payload))
        .replace("__BENCHMARK_RESULTS__", _benchmark_results(payload))
        .replace("__MULTIMODAL_RESULTS__", _multimodal_results(payload))
        .replace("__PATHWAY_RESULTS__", _pathway_results(payload))
        .replace("__FIGURE_CARDS__", _figure_cards(payload.get("figures", [])))
    )


def _summary_results(payload: dict[str, object]) -> str:
    interpretation = payload.get("interpretation") if isinstance(payload.get("interpretation"), dict) else {}
    source_counts = payload.get("sourceCounts") if isinstance(payload.get("sourceCounts"), dict) else {}
    qc = payload.get("qcSummary") if isinstance(payload.get("qcSummary"), dict) else {}
    benchmark = payload.get("benchmarkMetrics") if isinstance(payload.get("benchmarkMetrics"), dict) else {}
    labels = interpretation.get("label_counts", {}) if isinstance(interpretation.get("label_counts"), dict) else {}
    top_pathways = interpretation.get("top_pathways", []) if isinstance(interpretation.get("top_pathways"), list) else []
    accuracy = benchmark.get("accuracy")
    accuracy_text = "NA" if accuracy is None else f"{float(accuracy) * 100:.1f}%"

    source_rows = [{"source": key, "n_points": value} for key, value in source_counts.items()]
    label_rows = [{"label": key, "n_cells": value} for key, value in labels.items()]
    pathway_rows = [{"rank": i + 1, "pathway": pathway} for i, pathway in enumerate(top_pathways)]

    summary = html.escape(str(interpretation.get("plain_language_summary", "No interpretation was generated.")))
    return f"""<div class="result-grid">
      <section class="result-card">
        <h2>Run Summary</h2>
        <p>{summary}</p>
        <div class="result-stat">
          <div><strong>{len(payload.get("embedding", []))}</strong><span>map points</span></div>
          <div><strong>{qc.get("n_cells", "NA")}</strong><span>scRNA cells</span></div>
          <div><strong>{accuracy_text}</strong><span>benchmark accuracy</span></div>
        </div>
      </section>
      <section class="result-card">
        <h2>Map Sources</h2>
        {_html_table(source_rows, ["source", "n_points"])}
      </section>
      <section class="result-card">
        <h2>Transferred Labels</h2>
        {_html_table(label_rows, ["label", "n_cells"])}
      </section>
      <section class="result-card">
        <h2>Top Pathway Programs</h2>
        {_html_table(pathway_rows, ["rank", "pathway"])}
      </section>
    </div>"""


def _browser_payload(payload: dict[str, object]) -> dict[str, object]:
    """Return the compact payload used by the interactive UMAP.

    Large reports should not duplicate every barcode inside the JavaScript plot
    data. Detailed cell IDs remain in downloadable tables and small server-rendered
    previews, while the browser plot uses numeric point IDs.
    """
    embedding = [row for row in payload.get("embedding", []) if isinstance(row, dict)]
    cell_to_point: dict[str, int] = {}
    compact_embedding = []
    for index, row in enumerate(embedding, start=1):
        cell = str(row.get("cell") or "")
        if cell:
            cell_to_point[cell] = index
        compact_embedding.append({
            "point_id": index,
            "UMAP1": row.get("UMAP1"),
            "UMAP2": row.get("UMAP2"),
            "source": row.get("source"),
            "predicted_label": row.get("predicted_label"),
            "projection_confidence": row.get("projection_confidence"),
        })

    compact_pathways = []
    for row in payload.get("pathways", []):
        if not isinstance(row, dict):
            continue
        point_id = cell_to_point.get(str(row.get("cell") or ""))
        if point_id is None:
            continue
        compact_row = {"point_id": point_id}
        compact_row.update({key: value for key, value in row.items() if key != "cell"})
        compact_pathways.append(compact_row)

    return {
        "project": payload.get("project"),
        "embedding": compact_embedding,
        "pathwayColumns": payload.get("pathwayColumns", []),
        "pathways": compact_pathways,
        "qcSummary": payload.get("qcSummary", {}),
    }


def _benchmark_results(payload: dict[str, object]) -> str:
    benchmark = payload.get("benchmarkMetrics") if isinstance(payload.get("benchmarkMetrics"), dict) else {}
    predictions = payload.get("predictions") if isinstance(payload.get("predictions"), list) else []
    accuracy = benchmark.get("accuracy")
    accuracy_text = "NA" if accuracy is None else f"{float(accuracy) * 100:.1f}%"
    correct = sum(1 for row in predictions if isinstance(row, dict) and str(row.get("correct")) == "True")
    rows = [row for row in predictions if isinstance(row, dict)]
    columns = ["cell", "expected_label", "predicted_label", "correct"]
    return f"""<div class="result-grid">
      <section class="result-card">
        <h2>Benchmark Metrics</h2>
        <div class="result-stat">
          <div><strong>{benchmark.get("n_evaluated", "NA")}</strong><span>evaluated cells</span></div>
          <div><strong>{correct}</strong><span>correct predictions</span></div>
          <div><strong>{accuracy_text}</strong><span>accuracy</span></div>
        </div>
        <p>{html.escape(str(benchmark.get("scoring_harness", "")))}</p>
      </section>
      <section class="result-card">
        <h2>Prediction Results</h2>
        {_html_table(rows, columns, limit=40)}
        <a class="download-link" href="../benchmark/predictions.csv">Download predictions.csv</a>
      </section>
    </div>"""


def _multimodal_results(payload: dict[str, object]) -> str:
    summary = payload.get("multimodalSummary") if isinstance(payload.get("multimodalSummary"), dict) else {}
    modalities = summary.get("modalities", []) if isinstance(summary.get("modalities"), list) else []
    scatac = [row for row in payload.get("scatacProjection", []) if isinstance(row, dict)]
    bulk = [row for row in payload.get("bulkRnaProjection", []) if isinstance(row, dict)]
    modality_rows = [
        {
            "modality": item.get("modality", ""),
            "n_items": item.get("n_cells", item.get("n_samples", "")),
            "features": item.get("n_gene_activity_features", item.get("n_genes", "")),
            "method": item.get("method", ""),
        }
        for item in modalities
        if isinstance(item, dict)
    ]
    projection_columns = [
        "cell",
        "source",
        "predicted_label",
        "matched_scRNA_cell",
        "shared_features",
        "projection_confidence",
    ]
    return f"""<div class="result-grid">
      <section class="result-card">
        <h2>Projection Summary</h2>
        {_html_table(modality_rows, ["modality", "n_items", "features", "method"])}
      </section>
      <section class="result-card">
        <h2>scATAC Projected Cells</h2>
        {_html_table(scatac, projection_columns, limit=40)}
        <a class="download-link" href="../tables/scatac_projection.csv">Download scatac_projection.csv</a>
      </section>
      <section class="result-card">
        <h2>Bulk RNA Projected Samples</h2>
        {_html_table(bulk, projection_columns, limit=40)}
        <a class="download-link" href="../tables/bulk_rna_projection.csv">Download bulk_rna_projection.csv</a>
      </section>
    </div>"""


def _pathway_results(payload: dict[str, object]) -> str:
    pathways = [row for row in payload.get("pathways", []) if isinstance(row, dict)]
    pathway_columns = [str(col) for col in payload.get("pathwayColumns", [])]
    top_rows = []
    for pathway in pathway_columns:
        ranked = sorted(
            pathways,
            key=lambda row: float(row.get(pathway) or 0),
            reverse=True,
        )
        for row in ranked[:3]:
            top_rows.append({
                "pathway": pathway,
                "cell": row.get("cell", ""),
                "score": f"{float(row.get(pathway) or 0):.3f}",
            })
    preview_columns = ["cell", *pathway_columns[:6]]
    return f"""<div class="result-grid">
      <section class="result-card">
        <h2>Top Cells By Pathway</h2>
        {_html_table(top_rows, ["pathway", "cell", "score"], limit=60)}
      </section>
      <section class="result-card">
        <h2>Pathway Score Matrix</h2>
        {_html_table(pathways, preview_columns, limit=40)}
        <a class="download-link" href="../tables/pathway_scores.csv">Download pathway_scores.csv</a>
      </section>
    </div>"""


def _figure_cards(figures: object) -> str:
    if not isinstance(figures, list) or not figures:
        return """<section class="figure-card"><h2>No Static Figures Yet</h2><p>Run the report after figure generation to populate this gallery.</p></section>"""
    cards = []
    for figure in figures:
        if not isinstance(figure, dict):
            continue
        src = html.escape(str(figure.get("src", "")))
        title = html.escape(str(figure.get("title", "")))
        caption = html.escape(str(figure.get("caption", "")))
        cards.append(
            f"""<section class="figure-card">
        <h2>{title}</h2>
        <p>{caption}</p>
        <a href="{src}" download><img src="{src}" alt="{title}"></a>
      </section>"""
        )
    return "\n      ".join(cards)


def _html_table(rows: list[dict[str, object]], columns: list[str], limit: int = 20) -> str:
    if not rows:
        return '<p class="muted">No rows available.</p>'
    limited = rows[:limit]
    head = "".join(f"<th>{html.escape(str(column))}</th>" for column in columns)
    body_rows = []
    for row in limited:
        cells = []
        for column in columns:
            value = row.get(column, "")
            if isinstance(value, float):
                value = f"{value:.4g}"
            cells.append(f"<td>{html.escape(str(value if value is not None else ''))}</td>")
        body_rows.append(f"<tr>{''.join(cells)}</tr>")
    more = ""
    if len(rows) > limit:
        more = f'<p class="muted">Showing {limit} of {len(rows)} rows.</p>'
    return f'<div class="table-wrap"><table><thead><tr>{head}</tr></thead><tbody>{"".join(body_rows)}</tbody></table></div>{more}'


def _feature_cards(payload: dict[str, object]) -> str:
    interpretation = payload.get("interpretation") if isinstance(payload.get("interpretation"), dict) else {}
    agent = payload.get("agentResult") if isinstance(payload.get("agentResult"), dict) else {}
    ml = payload.get("mlManifest") if isinstance(payload.get("mlManifest"), dict) else {}
    fm = payload.get("foundationModelManifest") if isinstance(payload.get("foundationModelManifest"), dict) else {}
    benchmark = payload.get("benchmarkMetrics") if isinstance(payload.get("benchmarkMetrics"), dict) else {}
    scalability = payload.get("scalabilityPlan") if isinstance(payload.get("scalabilityPlan"), dict) else {}
    multimodal = payload.get("multimodalSummary") if isinstance(payload.get("multimodalSummary"), dict) else {}

    summary = html.escape(str(interpretation.get("plain_language_summary", "AI-assisted interpretation will appear after analysis.")))
    accuracy = benchmark.get("accuracy")
    accuracy_text = "NA" if accuracy is None else f"{float(accuracy) * 100:.1f}%"
    backbone_count = len(fm.get("supported_backbones", [])) if isinstance(fm.get("supported_backbones"), list) else 0
    modalities = multimodal.get("modalities", []) if isinstance(multimodal.get("modalities"), list) else []
    modality_text = ", ".join(str(item.get("modality", "")) for item in modalities if isinstance(item, dict)) or "not enabled"
    cells = scalability.get("observed_cells", "NA")
    mode = html.escape(str(scalability.get("execution_mode", "not planned")))
    agent_status = html.escape(str(agent.get("status", "pending")))
    split_policy = html.escape(str(ml.get("split_policy", "not exported")))

    cards = [
        ("AI Interpretation", summary, "../agent/interpretation.json", ""),
        ("Agentic Workflow", f"Structured run result is {agent_status}; outputs are self-describing for downstream agents.", "../agent/run_result.json", ""),
        ("Feature Matrix Export", f"Reference-aligned features, labels, and train/val/test splits. Split policy: {split_policy}.", "../feature_matrix/manifest.json", ""),
        ("Foundation Models", f"{backbone_count} optional adapter stubs: scGPT, Geneformer, scFoundation, and UCE.", "../foundation_models/adapter_manifest.json", ""),
        ("Multimodal Projection", f"Projected modalities: {html.escape(modality_text)}.", "../multimodal/projection_summary.json", ""),
        ("Benchmark", "Held-out label scoring harness for exhaustion-state annotation.", "../benchmark/metrics.json", accuracy_text),
        ("Scalability", f"{cells} observed cells. Recommended mode: {mode}.", "../scalability/projection_plan.json", ""),
    ]
    html_cards = []
    for title, body, href, stat in cards:
        stat_html = f"<strong>{html.escape(stat)}</strong>" if stat else ""
        html_cards.append(
            f"""<section class="feature">
        <h2>{html.escape(title)}</h2>
        {stat_html}
        <p>{body}</p>
        <a href="{html.escape(href)}">Open artifact</a>
      </section>"""
        )
    return "\n      ".join(html_cards)
