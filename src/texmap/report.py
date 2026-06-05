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
    figures = _figure_records(paths)
    interpretation = _load_json(paths["agent"] / "interpretation.json")
    agent_result = _load_json(paths["agent"] / "run_result.json")
    ml_manifest = _load_json(paths["ml_ready"] / "manifest.json")
    fm_manifest = _load_json(paths["foundation_models"] / "adapter_manifest.json")
    benchmark_metrics = _load_json(paths["benchmark"] / "metrics.json")
    scalability_plan = _load_json(paths["scalability"] / "projection_plan.json")

    payload = {
        "project": config.output.project_name,
        "embedding": embedding,
        "pathwayColumns": [key for key in pathways[0].keys() if key != "cell"] if pathways else [],
        "pathways": pathways,
        "qcSummary": _qc_summary(qc),
        "figures": figures,
        "interpretation": interpretation,
        "agentResult": agent_result,
        "mlManifest": ml_manifest,
        "foundationModelManifest": fm_manifest,
        "benchmarkMetrics": benchmark_metrics,
        "scalabilityPlan": scalability_plan,
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
    body { margin: 0; font-family: Arial, Helvetica, sans-serif; color: var(--ink); background: var(--soft); }
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
    .panel, .feature, .figure-card { background: #ffffff; border: 1px solid var(--line); border-radius: 8px; }
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
        <input id="search" type="search" placeholder="query_T_1, NK, B cell">
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
        <div class="check-row"><input id="showReference" type="checkbox" checked><span>reference cells</span></div>
        <div class="check-row"><input id="showQuery" type="checkbox" checked><span>query cells</span></div>
        <div class="button-row">
          <button id="resetView">Reset view</button>
          <button id="downloadSelection">Download selected</button>
        </div>
        <label>Legend</label>
        <div class="legend-list" id="legend"></div>
        <p class="muted">Wheel to zoom, drag to pan, click a cell to inspect it.</p>
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
            <button id="copyCell">Copy cell ID</button>
          </div>
        </div>
        <div class="viewport" id="viewport">
          <canvas id="plot" width="1200" height="760"></canvas>
          <div class="tooltip" id="tooltip"></div>
        </div>
        <div class="status-bar">
          <span id="hoverStatus">Hover over a cell</span>
          <span id="viewStatus">zoom 1.00x</span>
        </div>
      </section>
      <aside class="panel inspector">
        <h2>Cell inspector</h2>
        <dl id="cellDetails"></dl>
        <table>
          <thead><tr><th>Cell</th><th>Label</th><th>Score</th></tr></thead>
          <tbody id="topCells"></tbody>
        </table>
      </aside>
    </section>
    <div class="tabs">
      <button class="active" data-tab="features">AI outputs</button>
      <button data-tab="figures">Static figures</button>
    </div>
    <section id="features" class="tab-section active"><div class="feature-grid">__FEATURE_CARDS__</div></section>
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
    const pathwayByCell = new Map(TEXMAP.pathways.map(d => [d.cell, d]));
    const points = TEXMAP.embedding
      .filter(d => Number.isFinite(d.UMAP1) && Number.isFinite(d.UMAP2))
      .map(d => ({...d, x: d.UMAP1, y: d.UMAP2, screenX: 0, screenY: 0}));
    const labels = [...new Set(points.map(d => d.predicted_label || (d.source === 'reference' ? 'reference' : 'unassigned')))].sort();
    const labelColors = new Map(labels.map((label, i) => [label, palette[i % palette.length]]));
    for (const col of TEXMAP.pathwayColumns) {
      const opt = document.createElement('option');
      opt.value = col; opt.textContent = col; pathwaySelect.appendChild(opt);
    }
    for (const label of labels.filter(l => l !== 'reference')) {
      const opt = document.createElement('option');
      opt.value = label; opt.textContent = label; labelFilter.appendChild(opt);
    }
    function metric(label, value) {
      return `<div class="metric"><strong>${value ?? 'NA'}</strong><span>${label}</span></div>`;
    }
    document.getElementById('metrics').innerHTML = [
      metric('cells', TEXMAP.qcSummary.n_cells ?? TEXMAP.embedding.length),
      metric('median counts', Math.round(TEXMAP.qcSummary.median_counts ?? 0)),
      metric('median genes', Math.round(TEXMAP.qcSummary.median_genes ?? 0))
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
        if (p.source === 'query' && !showQuery.checked) return false;
        if (labelFilter.value !== 'all' && (p.predicted_label || '') !== labelFilter.value) return false;
        if (term) {
          const hay = `${p.cell} ${p.source} ${p.predicted_label || ''}`.toLowerCase();
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
        const score = Number(pathwayByCell.get(p.cell)?.[pathwaySelect.value] ?? 0);
        const values = TEXMAP.pathways.map(d => Number(d[pathwaySelect.value] ?? 0));
        const max = Math.max(1, ...values);
        const t = Math.max(0, Math.min(1, score / max));
        const r = Math.round(237 + (217 - 237) * t);
        const g = Math.round(242 + (76 - 242) * t);
        const b = Math.round(247 + (54 - 247) * t);
        return `rgb(${r},${g},${b})`;
      }
      if (colorMode.value === 'label') return labelColors.get(p.predicted_label || (p.source === 'reference' ? 'reference' : 'unassigned')) || '#5f6b7a';
      return p.source === 'query' ? '#d94c36' : '#32746d';
    }
    function drawLegend() {
      const legend = document.getElementById('legend');
      if (colorMode.value === 'pathway') {
        legend.innerHTML = `<div class="legend-item"><span class="swatch" style="background:#edf2f7"></span>low ${pathwaySelect.value}</div><div class="legend-item"><span class="swatch" style="background:#d94c36"></span>high ${pathwaySelect.value}</div>`;
        return;
      }
      const items = colorMode.value === 'source'
        ? [['reference','#32746d'], ['query','#d94c36']]
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
        ctx.arc(xy.x, xy.y, selected.has(p.cell) || activeCell?.cell === p.cell ? 8 : (p.source === 'query' ? 6 : 4), 0, Math.PI * 2);
        ctx.fillStyle = colorFor(p);
        ctx.globalAlpha = p.source === 'query' ? 0.9 : 0.52;
        ctx.fill();
        if (selected.has(p.cell) || activeCell?.cell === p.cell) {
          ctx.globalAlpha = 1;
          ctx.strokeStyle = '#1d2433';
          ctx.lineWidth = 2;
          ctx.stroke();
        }
      }
      ctx.globalAlpha = 1;
      document.getElementById('visibleCount').textContent = `${pts.length} visible / ${points.length} cells`;
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
      if (cell) selected.add(cell.cell);
      const details = document.getElementById('cellDetails');
      if (!cell) {
        details.innerHTML = '<dt>Status</dt><dd>No cell selected</dd>';
        return;
      }
      const scores = pathwayByCell.get(cell.cell) || {};
      details.innerHTML = [
        ['Cell', cell.cell],
        ['Source', cell.source],
        ['Label', cell.predicted_label || ''],
        ['UMAP1', Number(cell.UMAP1).toFixed(3)],
        ['UMAP2', Number(cell.UMAP2).toFixed(3)],
        [pathwaySelect.value, Number(scores[pathwaySelect.value] ?? 0).toFixed(3)]
      ].map(([k,v]) => `<dt>${k}</dt><dd>${v}</dd>`).join('');
      draw();
    }
    function showTooltip(event, cell) {
      if (!cell) {
        tooltip.style.display = 'none';
        document.getElementById('hoverStatus').textContent = 'Hover over a cell';
        return;
      }
      const score = Number(pathwayByCell.get(cell.cell)?.[pathwaySelect.value] ?? 0).toFixed(3);
      tooltip.innerHTML = `<strong>${cell.cell}</strong><br>${cell.source}<br>${cell.predicted_label || ''}<br>${pathwaySelect.value}: ${score}`;
      tooltip.style.left = `${event.clientX - viewport.getBoundingClientRect().left + 12}px`;
      tooltip.style.top = `${event.clientY - viewport.getBoundingClientRect().top + 12}px`;
      tooltip.style.display = 'block';
      document.getElementById('hoverStatus').textContent = `${cell.cell} ${cell.predicted_label || ''}`;
    }
    function updateTable() {
      const col = pathwaySelect.value;
      const rows = points
        .filter(d => d.source === 'query')
        .map(d => ({...d, score: pathwayByCell.get(d.cell)?.[col] ?? 0}))
        .sort((a, b) => b.score - a.score)
        .slice(0, 12);
      document.getElementById('topCells').innerHTML = rows.map(r =>
        `<tr><td>${r.cell}</td><td>${r.predicted_label ?? ''}</td><td>${Number(r.score).toFixed(3)}</td></tr>`
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
    document.getElementById('copyCell').addEventListener('click', async () => { if (activeCell && navigator.clipboard) await navigator.clipboard.writeText(activeCell.cell); });
    document.getElementById('downloadSelection').addEventListener('click', () => {
      const rows = points.filter(p => selected.has(p.cell));
      const csv = ['cell,source,predicted_label,UMAP1,UMAP2', ...rows.map(p => `${p.cell},${p.source},${p.predicted_label || ''},${p.UMAP1},${p.UMAP2}`)].join('\\n');
      const a = document.createElement('a');
      a.href = URL.createObjectURL(new Blob([csv], { type: 'text/csv' }));
      a.download = 'texmap_selected_cells.csv';
      a.click();
      URL.revokeObjectURL(a.href);
    });
    for (const el of [pathwaySelect, colorMode, labelFilter, search, showReference, showQuery]) {
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
        .replace("__DATA__", json.dumps(payload))
        .replace("__FEATURE_CARDS__", _feature_cards(payload))
        .replace("__FIGURE_CARDS__", _figure_cards(payload.get("figures", [])))
    )


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


def _feature_cards(payload: dict[str, object]) -> str:
    interpretation = payload.get("interpretation") if isinstance(payload.get("interpretation"), dict) else {}
    agent = payload.get("agentResult") if isinstance(payload.get("agentResult"), dict) else {}
    ml = payload.get("mlManifest") if isinstance(payload.get("mlManifest"), dict) else {}
    fm = payload.get("foundationModelManifest") if isinstance(payload.get("foundationModelManifest"), dict) else {}
    benchmark = payload.get("benchmarkMetrics") if isinstance(payload.get("benchmarkMetrics"), dict) else {}
    scalability = payload.get("scalabilityPlan") if isinstance(payload.get("scalabilityPlan"), dict) else {}

    summary = html.escape(str(interpretation.get("plain_language_summary", "AI-assisted interpretation will appear after analysis.")))
    accuracy = benchmark.get("accuracy")
    accuracy_text = "NA" if accuracy is None else f"{float(accuracy) * 100:.1f}%"
    backbone_count = len(fm.get("supported_backbones", [])) if isinstance(fm.get("supported_backbones"), list) else 0
    cells = scalability.get("observed_cells", "NA")
    mode = html.escape(str(scalability.get("execution_mode", "not planned")))
    agent_status = html.escape(str(agent.get("status", "pending")))
    split_policy = html.escape(str(ml.get("split_policy", "not exported")))

    cards = [
        ("AI Interpretation", summary, "../agent/interpretation.json", ""),
        ("Agentic Workflow", f"Structured run result is {agent_status}; outputs are self-describing for downstream agents.", "../agent/run_result.json", ""),
        ("ML-Ready Export", f"Reference-aligned features, labels, and train/val/test splits. Split policy: {split_policy}.", "../ml_ready/manifest.json", ""),
        ("Foundation Models", f"{backbone_count} optional adapter stubs: scGPT, Geneformer, scFoundation, and UCE.", "../foundation_models/adapter_manifest.json", ""),
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
