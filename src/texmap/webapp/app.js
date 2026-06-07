"use strict";

// ----------------------------------------------------------------- state
const state = {
  config: null,
  atlas: [],          // reference cells: {cell,x,y,<axes>,<categoricals>}
  query: [],          // projected cells: {cell,UMAP1,UMAP2,source,<axes>,...}
  queryPathways: {},  // cell -> {pathway: score}
  axes: [],
  markerGenes: [],
  colorBy: "tex_state",
  activePathway: null,
  geneColor: null,        // gene name to color by, or null
  showRef: true,
  showQuery: true,
  view: { scale: 1, ox: 0, oy: 0, fitted: false },
  hover: null,
  selection: new Set(),   // selected cell ids
  selBox: null,           // {x0,y0,x1,y1} screen coords while drawing
};

// cellxgene-style categorical palette (d3 category10/20-like, scientific)
const CAT_PALETTE = ["#1f77b4", "#ff7f0e", "#2ca02c", "#d62728", "#9467bd",
  "#8c564b", "#e377c2", "#7f7f7f", "#bcbd22", "#17becf",
  "#aec7e8", "#ffbb78", "#98df8a", "#ff9896", "#c5b0d5"];
const catColors = {};
function colorForCategory(v) {
  if (!(v in catColors)) catColors[v] = CAT_PALETTE[Object.keys(catColors).length % CAT_PALETTE.length];
  return catColors[v];
}
// Viridis continuous color scale (cellxgene's default for continuous variables).
const VIRIDIS = [[68,1,84],[59,82,139],[33,144,141],[93,201,99],[253,231,37]];
function gradient(t) {
  t = Math.max(0, Math.min(1, t));
  const seg = t * (VIRIDIS.length - 1);
  const i = Math.min(VIRIDIS.length - 2, Math.floor(seg));
  const f = seg - i;
  const a = VIRIDIS[i], b = VIRIDIS[i + 1];
  const mix = (x, y) => Math.round(x + (y - x) * f);
  return `rgb(${mix(a[0],b[0])},${mix(a[1],b[1])},${mix(a[2],b[2])})`;
}
const DIM = "rgba(200,205,211,0.45)";   // light-grey for dimmed / no-value cells

const canvas = document.getElementById("scatter");
const ctx = canvas.getContext("2d");

// ----------------------------------------------------------------- boot
async function boot() {
  state.config = await (await fetch("/api/config")).json();
  state.axes = state.config.axes;
  document.getElementById("agentBackend").textContent = state.config.agent_backend;

  const atlas = await (await fetch("/api/atlas")).json();
  document.getElementById("projectName").textContent = atlas.project;
  state.atlas = atlas.cells;
  state.markerGenes = atlas.markerGenes || [];

  buildColorByOptions(atlas);
  buildPathwayList(atlas.pathways);
  buildGeneList();
  wireCellxgene();
  wireNetwork();
  wireBenchmarks();
  await wireIntegration();
  wireTexBench();
  wireTexApi();
  resize();
  fitView();
  draw();
  agentSay("agent", "Hi — I'm TexAgent. Ask me about exhaustion markers, what programs drive a gene, or upload a dataset and I'll summarize where it lands.");
}

function buildColorByOptions(atlas) {
  const sel = document.getElementById("colorBy");
  const groups = [
    ["Cell metadata", atlas.categorical],
    ["Exhaustion axes (continuous)", state.axes],
  ];
  for (const [label, items] of groups) {
    const og = document.createElement("optgroup"); og.label = label;
    for (const it of items) {
      const o = document.createElement("option"); o.value = it; o.textContent = it; og.appendChild(o);
    }
    sel.appendChild(og);
  }
  sel.value = atlas.categorical.includes("tex_state") ? "tex_state" : atlas.categorical[0] || state.axes[0];
  state.colorBy = sel.value;
  sel.addEventListener("change", () => {
    state.colorBy = sel.value; state.activePathway = null; state.geneColor = null;
    document.getElementById("geneSelect").value = "";
    renderPathwayActive(); buildLegend(); draw();
  });
  buildLegend();
}

function buildPathwayList(pathways) {
  const ul = document.getElementById("pathwayList");
  ul.innerHTML = "";
  for (const p of pathways) {
    const li = document.createElement("li"); li.textContent = p; li.dataset.pw = p;
    li.addEventListener("click", () => {
      state.activePathway = state.activePathway === p ? null : p;
      renderPathwayActive(); buildLegend(); draw();
    });
    ul.appendChild(li);
  }
}
function renderPathwayActive() {
  document.querySelectorAll("#pathwayList li").forEach(li =>
    li.classList.toggle("active", li.dataset.pw === state.activePathway));
}

// ---- color by gene (cellxgene-style dropdown) ----
function buildGeneList() {
  const sel = document.getElementById("geneSelect");
  for (const g of state.markerGenes) { const o = document.createElement("option"); o.value = g; o.textContent = g; sel.appendChild(o); }
  sel.addEventListener("change", () => setGene(sel.value || null));
}
function setGene(gene) {
  if (gene && !state.markerGenes.includes(gene)) {
    document.getElementById("projectStatus").textContent = `Gene "${gene}" not in marker panel.`;
    return;
  }
  state.geneColor = gene || null;
  const sel = document.getElementById("geneSelect");
  if (sel.value !== (gene || "")) sel.value = gene || "";   // keep dropdown in sync (e.g. agent action)
  state.activePathway = null; renderPathwayActive();
  computeGeneRange(); buildLegend(); draw();
}
let geneRange = [0, 1];
function computeGeneRange() {
  if (!state.geneColor) return;
  const vals = [];
  for (const p of state.atlas) if (p.expr && p.expr[state.geneColor] != null) vals.push(p.expr[state.geneColor]);
  for (const q of state.query) if (q.expr && q.expr[state.geneColor] != null) vals.push(q.expr[state.geneColor]);
  geneRange = vals.length ? [Math.min(...vals), Math.max(...vals)] : [0, 1];
}

// ---- CELLxGENE Discover query ----
function wireCellxgene() {
  const run = async () => {
    const q = document.getElementById("cxgQuery").value.trim();
    const src = document.getElementById("cxgSource");
    src.textContent = "Searching CELLxGENE Discover…";
    try {
      const data = await (await fetch("/api/cellxgene/search?q=" + encodeURIComponent(q))).json();
      src.textContent = `${data.n_results} result(s) · ${data.source}`;
      renderCxgResults(data.results);
    } catch (e) { src.className = "status err"; src.textContent = "Search failed: " + e.message; }
  };
  document.getElementById("cxgSearch").addEventListener("click", run);
  document.getElementById("cxgQuery").addEventListener("keydown", e => { if (e.key === "Enter") run(); });
}
function renderCxgResults(results) {
  const ul = document.getElementById("cxgResults"); ul.innerHTML = "";
  for (const r of results) {
    const li = document.createElement("li");
    const cells = r.cell_count ? `${Number(r.cell_count).toLocaleString()} cells · ` : "";
    const paper = r.paper_url ? ` · <a href="${r.paper_url}" target="_blank" rel="noopener">Paper</a>` : "";
    li.innerHTML = `<div class="t">${escapeHtml(r.title)}</div>` +
      `<div class="m">${cells}${escapeHtml(r.organism || "")} · ${escapeHtml(r.tissue || "")} · ${escapeHtml(r.disease || "")}</div>` +
      `<a href="${r.explorer_url}" target="_blank" rel="noopener">Open in CELLxGENE →</a>${paper}`;
    ul.appendChild(li);
  }
}

// ---- regulatory network (SVG graph) ----
let currentNet = null;
async function loadFullNetwork() {
  const net = await (await fetch("/api/regulatory")).json();
  renderNetwork(net); document.getElementById("netOverlay").hidden = false;
}
function wireNetwork() {
  document.getElementById("showNetwork").addEventListener("click", loadFullNetwork);
  document.getElementById("closeNet").addEventListener("click", () => {
    document.getElementById("netOverlay").hidden = true;
  });
  const focus = async () => {
    const g = document.getElementById("netFocus").value.trim().toUpperCase();
    if (!g) return;
    const net = await (await fetch("/api/regulatory?gene=" + encodeURIComponent(g))).json();
    renderNetwork(net, g);
  };
  document.getElementById("netFocusBtn").addEventListener("click", focus);
  document.getElementById("netFocus").addEventListener("keydown", e => { if (e.key === "Enter") focus(); });
  document.getElementById("netReset").addEventListener("click", loadFullNetwork);
  document.getElementById("netExportJson").addEventListener("click", exportNetJson);
  document.getElementById("netExportPng").addEventListener("click", exportNetPng);
}
function exportNetJson() {
  if (!currentNet) return;
  const blob = new Blob([JSON.stringify(currentNet, null, 2)], { type: "application/json" });
  const a = document.createElement("a");
  a.href = URL.createObjectURL(blob); a.download = "texmap_regulatory_network.json"; a.click();
  URL.revokeObjectURL(a.href);
}
function exportNetPng() {
  const svg = document.getElementById("netSvg");
  const xml = new XMLSerializer().serializeToString(svg);
  const img = new Image();
  img.onload = () => {
    const c = document.createElement("canvas");
    c.width = svg.width.baseVal.value; c.height = svg.height.baseVal.value;
    const cx = c.getContext("2d"); cx.fillStyle = "#fff"; cx.fillRect(0, 0, c.width, c.height);
    cx.drawImage(img, 0, 0);
    const a = document.createElement("a"); a.href = c.toDataURL("image/png");
    a.download = "texmap_regulatory_network.png"; a.click();
  };
  img.src = "data:image/svg+xml;base64," + btoa(unescape(encodeURIComponent(xml)));
}
// ---- integration engine (method + query mode selectors) ----
async function wireIntegration() {
  const data = await (await fetch("/api/methods")).json();
  const ms = document.getElementById("methodSelect");
  for (const m of data.methods) {
    const o = document.createElement("option"); o.value = m.key;
    o.textContent = m.label + (m.available ? "" : (m.requires ? `  (install ${m.requires})` : ""));
    ms.appendChild(o);
  }
  ms.value = data.default_method;
  const md = document.getElementById("modeSelect");
  for (const m of data.modes) { const o = document.createElement("option"); o.value = m.key; o.textContent = m.label; md.appendChild(o); }
  md.value = data.default_mode;
}

// ---- TexAPI reference overlay ----
function wireTexApi() {
  document.getElementById("openTexApi").addEventListener("click", () => {
    renderTexApi(); document.getElementById("apiOverlay").hidden = false;
  });
  document.getElementById("closeApi").addEventListener("click", () =>
    document.getElementById("apiOverlay").hidden = true);
}
function renderTexApi() {
  const base = window.location.origin;
  const ep = [
    ["GET", "/api/atlas", "reference cells: coords, axes, metadata, marker expression"],
    ["GET", "/api/config", "project name, axes, pathways, agent backend"],
    ["POST", "/api/project", "body = counts CSV; headers X-Method, X-Mode → projection"],
    ["GET", "/api/methods", "integration methods + query modes (with availability)"],
    ["GET", "/api/regulatory?gene=", "TF→target regulatory network (or a gene's sub-network)"],
    ["GET", "/api/accuracy", "cell-state projection accuracy (leave-one-out)"],
    ["GET", "/api/clinical?predictor=", "AUROC / concordance index / hazard ratio"],
    ["GET", "/api/cellxgene/search?q=", "search CZ CELLxGENE Discover"],
    ["GET", "/api/texbench", "TexBench dashboard data"],
    ["POST", "/api/agent", "body {question} → tool-using agent answer + actions"],
  ];
  let rows = ep.map(([m, p, d]) => `<tr><td><code>${m}</code></td><td><code>${p}</code></td><td>${d}</td></tr>`).join("");
  const py = `# Python — in-process (no server)\nfrom texmap import TexMap\ntm = TexMap.from_config("examples/tex_atlas/config.yaml")\ntm.project({"c1": {"PDCD1": 12, "TOX": 8, "TCF7": 0}})\ntm.regulators_of("TOX"); tm.clinical_benchmark(cohort, "Stemness")\n\n# Python — talk to this running server\nfrom texmap import TexAPIClient\napi = TexAPIClient("${base}")\napi.cellxgene_search("CD8 exhaustion melanoma")\napi.clinical(predictor="Exhaustion")`;
  const curl = `curl "${base}/api/clinical?predictor=Exhaustion"\ncurl -X POST "${base}/api/project" -H "X-Method: scVI" --data-binary @counts.csv`;
  document.getElementById("apiBody").innerHTML =
    `<div class="api-doc"><p class="hint">TexMap is scriptable. Use the in-process Python API, the HTTP client, or raw REST — base URL <code>${base}</code>.</p>` +
    `<h4>REST endpoints</h4><table><tr><th>Method</th><th>Path</th><th>Returns</th></tr>${rows}</table>` +
    `<h4>Python (TexAPI)</h4><pre>${escapeHtml(py)}</pre>` +
    `<h4>cURL</h4><pre>${escapeHtml(curl)}</pre></div>`;
}

// ---- TexBench overlay ----
function wireTexBench() {
  document.getElementById("openTexBench").addEventListener("click", async () => {
    const b = await (await fetch("/api/texbench")).json();
    renderTexBench(b);
    document.getElementById("benchOverlay").hidden = false;
  });
  document.getElementById("closeBench").addEventListener("click", () =>
    document.getElementById("benchOverlay").hidden = true);
}
function renderTexBench(b) {
  const clin = b.clinical_exhaustion || {};
  const card = (num, cap) => `<div class="card"><div class="num">${num == null ? "—" : num}</div><div class="cap">${cap}</div></div>`;
  let html = `<div class="bench-cards">` +
    card(b.n_reference_cells, "reference cells") +
    card(b.projection_accuracy != null ? (b.projection_accuracy * 100).toFixed(1) + "%" : "—", "cell-state projection accuracy") +
    card(clin.auroc, "ICB-response AUROC (Exhaustion)") +
    card(clin.hazard_ratio, "survival hazard ratio") +
    `</div>`;
  html += `<table class="bench-table"><tr><th>Integration method</th><th>Backend</th><th>Status</th></tr>`;
  for (const m of b.methods) {
    html += `<tr><td>${m.label}</td><td>${m.requires || "—"}</td>` +
      `<td class="${m.available ? "yes" : "no"}">${m.available ? "available" : "not installed → axis-projection fallback"}</td></tr>`;
  }
  html += `</table><p class="hint" style="max-width:640px">Query modes: integrate all · project query · label transfer · nearest Tex states · compare conditions. The axis-space engine runs today; heavy backends are adapters that activate when their library is installed.</p>`;
  document.getElementById("benchBody").innerHTML = html;
}

// ---- benchmarks (projection accuracy + clinical translation) ----
function wireBenchmarks() {
  const sel = document.getElementById("clinPredictor");
  for (const a of state.axes) { const o = document.createElement("option"); o.value = a; o.textContent = a; sel.appendChild(o); }
  const out = document.getElementById("benchOut");
  document.getElementById("runAccuracy").addEventListener("click", async () => {
    out.textContent = "Computing leave-one-out accuracy…";
    const r = await (await fetch("/api/accuracy")).json();
    out.innerHTML = `<b>Cell-state projection accuracy</b><div class="lab"><span>accuracy</span><span>${(r.accuracy*100).toFixed(1)}%</span></div>` +
      `<div class="lab"><span>macro-F1</span><span>${r.macro_f1}</span></div>` +
      `<div class="lab" style="color:var(--muted)">${r.method}</div>`;
  });
  document.getElementById("runClinical").addEventListener("click", async () => {
    const p = sel.value; out.textContent = `Running clinical benchmark on ${p}…`;
    const r = await (await fetch("/api/clinical?predictor=" + encodeURIComponent(p))).json();
    if (r.error) { out.textContent = r.error; return; }
    const cox = r.cox || {};
    out.innerHTML = `<b>Clinical translation — predictor: ${p}</b>` +
      row("AUROC (ICB response)", r.auroc) +
      row("Concordance index (survival)", r.concordance_index) +
      row("Hazard ratio", cox.hazard_ratio) +
      row("HR p-value", cox.p) +
      `<div class="lab" style="color:var(--muted)">n=${r.n_samples} patients</div>`;
  });
  function row(k, v) { return `<div class="lab"><span>${k}</span><span>${v == null ? "—" : v}</span></div>`; }
}

const SVGNS = "http://www.w3.org/2000/svg";
function svgEl(tag, attrs) { const e = document.createElementNS(SVGNS, tag);
  for (const k in attrs) e.setAttribute(k, attrs[k]); return e; }
function renderNetwork(net, focusGene) {
  currentNet = net;
  const svg = document.getElementById("netSvg");
  svg.innerHTML = "";
  // focus sub-networks lack `programs`/meta — derive them so rendering is uniform
  const programsMap = net.programs || (() => {
    const m = {}; for (const n of net.nodes) (m[n.program] = m[n.program] || []).push(n.gene); return m;
  })();
  const nTfs = net.n_tfs != null ? net.n_tfs : net.nodes.filter(n => n.is_tf).length;
  const meta = focusGene
    ? `Focus: ${focusGene} · ${net.nodes.length} genes · ${net.edges.length} edges (regulators + targets)`
    : `${net.nodes.length} genes · ${net.edges.length} edges · ${nTfs} TFs · ${net.method || ""}`;
  document.getElementById("netMeta").textContent = meta;
  const W = 820, H = 560, cx = W / 2, cy = H / 2;
  const programs = Object.keys(programsMap);
  // cluster center per program, around a circle
  const centers = {};
  programs.forEach((p, i) => {
    const a = (i / programs.length) * 2 * Math.PI - Math.PI / 2;
    centers[p] = [cx + Math.cos(a) * 215, cy + Math.sin(a) * 175];
  });
  // node positions: ring around each program's center
  const pos = {}; const byProg = {};
  for (const n of net.nodes) (byProg[n.program] = byProg[n.program] || []).push(n);
  for (const p of programs) {
    const list = byProg[p]; const [ccx, ccy] = centers[p];
    list.forEach((n, j) => {
      const a = (j / Math.max(1, list.length)) * 2 * Math.PI;
      const rr = list.length > 1 ? 52 : 0;
      pos[n.gene] = [ccx + Math.cos(a) * rr, ccy + Math.sin(a) * rr];
    });
  }
  // edges
  for (const e of net.edges) {
    const s = pos[e.source], t = pos[e.target];
    if (!s || !t) continue;
    svg.appendChild(svgEl("line", { x1: s[0], y1: s[1], x2: t[0], y2: t[1],
      stroke: e.sign === "activation" ? "#2b95d6" : "#d62728",
      "stroke-width": Math.max(0.5, Math.abs(e.r) * 2.2),
      "stroke-opacity": Math.min(0.8, Math.abs(e.r) + 0.1) }));
  }
  // nodes
  for (const n of net.nodes) {
    const [x, y] = pos[n.gene];
    svg.appendChild(svgEl("circle", { cx: x, cy: y, r: n.is_tf ? 7 : 4,
      fill: colorForCategory(n.program), stroke: "#22272e", "stroke-width": n.is_tf ? 1.3 : 0.6 }));
    if (n.is_tf) {
      const txt = svgEl("text", { x: x + 9, y: y + 4, "font-size": 12, fill: "#1c2127", "font-weight": 600 });
      txt.textContent = n.gene; svg.appendChild(txt);
    }
  }
  // legend
  const leg = document.getElementById("netLegend"); leg.innerHTML = "";
  for (const p of programs) {
    const row = document.createElement("div"); row.className = "row";
    const sw = document.createElement("span"); sw.className = "swatch"; sw.style.background = colorForCategory(p);
    row.append(sw, document.createTextNode(p)); leg.appendChild(row);
  }
  const er = document.createElement("div"); er.className = "row";
  er.innerHTML = `<span class="swatch" style="background:#2b95d6"></span>activation &nbsp; <span class="swatch" style="background:#d62728"></span>repression &nbsp; (larger node = TF)`;
  leg.appendChild(er);
}

// ----------------------------------------------------------------- view transform
function dataBounds() {
  const pts = state.atlas.concat(state.query.map(q => ({ x: q.UMAP1, y: q.UMAP2 })));
  let minX = Infinity, maxX = -Infinity, minY = Infinity, maxY = -Infinity;
  for (const p of pts) { minX = Math.min(minX, p.x); maxX = Math.max(maxX, p.x); minY = Math.min(minY, p.y); maxY = Math.max(maxY, p.y); }
  if (!isFinite(minX)) return { minX: -1, maxX: 1, minY: -1, maxY: 1 };
  return { minX, maxX, minY, maxY };
}
function fitView() {
  const b = dataBounds();
  const pad = 40;
  const w = canvas.clientWidth, h = canvas.clientHeight;
  const sx = (w - 2 * pad) / ((b.maxX - b.minX) || 1);
  const sy = (h - 2 * pad) / ((b.maxY - b.minY) || 1);
  state.view.scale = Math.min(sx, sy);
  state.view.ox = pad - b.minX * state.view.scale + (w - 2 * pad - (b.maxX - b.minX) * state.view.scale) / 2;
  state.view.oy = h - pad + b.minY * state.view.scale - (h - 2 * pad - (b.maxY - b.minY) * state.view.scale) / 2;
  state.view.fitted = true;
}
function toScreen(x, y) { return [x * state.view.scale + state.view.ox, -y * state.view.scale + state.view.oy]; }
function toData(px, py) { return [(px - state.view.ox) / state.view.scale, -(py - state.view.oy) / state.view.scale]; }

// ----------------------------------------------------------------- color resolve
function colorOf(pt, isQuery) {
  if (state.geneColor) {
    const v = pt.expr ? pt.expr[state.geneColor] : undefined;
    if (v === undefined) return DIM;
    const [lo, hi] = geneRange;
    return gradient((v - lo) / ((hi - lo) || 1));
  }
  if (state.activePathway) {
    if (!isQuery) return DIM; // reference dimmed
    const sc = (state.queryPathways[pt.cell] || {})[state.activePathway];
    if (sc === undefined) return DIM;
    return gradient(normPathway(sc));
  }
  const key = state.colorBy;
  if (state.axes.includes(key)) {
    const v = isQuery ? pt[key] : pt[key];
    return gradient(typeof v === "number" ? v : 0);
  }
  // categorical
  const v = isQuery ? (pt.predicted_label || pt.tex_state) : pt[key];
  return colorForCategory(v == null ? "n/a" : v);
}
let pwRange = [0, 1];
function normPathway(v) { const [lo, hi] = pwRange; return (v - lo) / ((hi - lo) || 1); }
function computePwRange() {
  if (!state.activePathway) return;
  const vals = Object.values(state.queryPathways).map(d => d[state.activePathway]).filter(v => v !== undefined);
  pwRange = vals.length ? [Math.min(...vals), Math.max(...vals)] : [0, 1];
}

// ----------------------------------------------------------------- draw
function resize() {
  const dpr = window.devicePixelRatio || 1;
  canvas.width = canvas.clientWidth * dpr;
  canvas.height = canvas.clientHeight * dpr;
  ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
}
function draw() {
  computePwRange();
  ctx.clearRect(0, 0, canvas.clientWidth, canvas.clientHeight);
  const hasSel = state.selection.size > 0;
  // reference
  if (state.showRef) {
    for (const p of state.atlas) {
      const [sx, sy] = toScreen(p.x, p.y);
      const sel = state.selection.has(p.cell);
      ctx.globalAlpha = hasSel && !sel ? 0.15 : 1;
      ctx.fillStyle = colorOf(p, false);
      ctx.beginPath(); ctx.arc(sx, sy, sel ? 3.4 : 2.6, 0, 6.283); ctx.fill();
    }
  }
  // query (drawn larger, with ring)
  if (state.showQuery) {
    for (const q of state.query) {
      const [sx, sy] = toScreen(q.UMAP1, q.UMAP2);
      const sel = state.selection.has(q.cell);
      ctx.globalAlpha = hasSel && !sel ? 0.2 : 1;
      ctx.fillStyle = colorOf(q, true);
      ctx.beginPath(); ctx.arc(sx, sy, 5, 0, 6.283); ctx.fill();
      ctx.lineWidth = 1.4; ctx.strokeStyle = "#22272e"; ctx.stroke();
    }
  }
  ctx.globalAlpha = 1;
  // selection rectangle while dragging
  if (state.selBox) {
    const b = state.selBox;
    ctx.strokeStyle = "rgba(88,166,255,0.9)"; ctx.fillStyle = "rgba(88,166,255,0.12)";
    ctx.lineWidth = 1;
    const x = Math.min(b.x0, b.x1), y = Math.min(b.y0, b.y1);
    ctx.fillRect(x, y, Math.abs(b.x1 - b.x0), Math.abs(b.y1 - b.y0));
    ctx.strokeRect(x, y, Math.abs(b.x1 - b.x0), Math.abs(b.y1 - b.y0));
  }
  const label = state.geneColor ? `gene ${state.geneColor}` : (state.activePathway || state.colorBy);
  document.getElementById("axisHud").textContent =
    `${state.atlas.length} reference · ${state.query.length} query · color: ${label}`;
}

function buildLegend() {
  const el = document.getElementById("legend");
  el.innerHTML = "";
  const key = state.geneColor || state.activePathway || state.colorBy;
  if (state.geneColor || state.activePathway || state.axes.includes(state.colorBy)) {
    const wrap = document.createElement("div"); wrap.className = "grad-wrap";
    const lo = document.createElement("span"); lo.textContent = "low";
    const g = document.createElement("div"); g.className = "gradient";
    g.style.background = `linear-gradient(90deg, ${gradient(0)}, ${gradient(0.5)}, ${gradient(1)})`;
    const hi = document.createElement("span"); hi.textContent = "high";
    wrap.append(lo, g, hi); el.appendChild(wrap);
    return;
  }
  const vals = [...new Set(state.atlas.map(p => p[key]).filter(v => v != null))].sort();
  for (const v of vals) {
    const row = document.createElement("div"); row.className = "row";
    const sw = document.createElement("div"); sw.className = "swatch"; sw.style.background = colorForCategory(v);
    const lab = document.createElement("span"); lab.textContent = v;
    row.append(sw, lab); el.appendChild(row);
  }
}

// ----------------------------------------------------------------- interaction
let dragging = false, last = null;
canvas.addEventListener("mousedown", e => {
  if (e.shiftKey) { state.selBox = { x0: e.offsetX, y0: e.offsetY, x1: e.offsetX, y1: e.offsetY }; }
  else { dragging = true; last = [e.offsetX, e.offsetY]; }
});
window.addEventListener("mouseup", () => {
  if (state.selBox) { finalizeSelection(); state.selBox = null; draw(); }
  dragging = false;
});
canvas.addEventListener("mousemove", e => {
  if (state.selBox) { state.selBox.x1 = e.offsetX; state.selBox.y1 = e.offsetY; draw(); }
  else if (dragging) {
    state.view.ox += e.offsetX - last[0]; state.view.oy += e.offsetY - last[1];
    last = [e.offsetX, e.offsetY]; draw();
  } else { handleHover(e); }
});

function finalizeSelection() {
  const b = state.selBox;
  const x0 = Math.min(b.x0, b.x1), x1 = Math.max(b.x0, b.x1);
  const y0 = Math.min(b.y0, b.y1), y1 = Math.max(b.y0, b.y1);
  if (x1 - x0 < 3 && y1 - y0 < 3) { state.selection.clear(); renderSelectInfo(); return; }
  const sel = new Set();
  const scan = (arr, isQ) => {
    for (const p of arr) {
      const [sx, sy] = toScreen(isQ ? p.UMAP1 : p.x, isQ ? p.UMAP2 : p.y);
      if (sx >= x0 && sx <= x1 && sy >= y0 && sy <= y1) sel.add(p.cell);
    }
  };
  if (state.showRef) scan(state.atlas, false);
  if (state.showQuery) scan(state.query, true);
  state.selection = sel;
  renderSelectInfo();
}
function renderSelectInfo() {
  const box = document.getElementById("selectInfo");
  if (!state.selection.size) { box.hidden = true; return; }
  // composition of selected cells by tex_state / predicted_label
  const counts = {};
  const stateOf = p => p.tex_state || p.predicted_label || p.cell_type || "n/a";
  for (const p of state.atlas) if (state.selection.has(p.cell)) counts[stateOf(p)] = (counts[stateOf(p)] || 0) + 1;
  for (const q of state.query) if (state.selection.has(q.cell)) counts[stateOf(q)] = (counts[stateOf(q)] || 0) + 1;
  const n = state.selection.size;
  const sorted = Object.entries(counts).sort((a, b) => b[1] - a[1]);
  let html = `<h4>${n} cells selected</h4>`;
  for (const [k, c] of sorted) {
    const pct = Math.round(100 * c / n);
    html += `<div class="lab"><span>${escapeHtml(k)}</span><span>${pct}%</span></div><div class="bar" style="width:${pct}%"></div>`;
  }
  html += `<button class="clear" id="clearSel">Clear selection</button>`;
  box.innerHTML = html; box.hidden = false;
  document.getElementById("clearSel").addEventListener("click", () => {
    state.selection.clear(); renderSelectInfo(); draw();
  });
}
canvas.addEventListener("wheel", e => {
  e.preventDefault();
  const factor = e.deltaY < 0 ? 1.12 : 1 / 1.12;
  const [dx, dy] = toData(e.offsetX, e.offsetY);
  state.view.scale *= factor;
  const [nx, ny] = toScreen(dx, dy);
  state.view.ox += e.offsetX - nx; state.view.oy += e.offsetY - ny;
  draw();
}, { passive: false });

function nearestPoint(px, py) {
  let best = null, bestD = 81; // 9px radius
  const scan = (arr, isQ) => {
    for (const p of arr) {
      const [sx, sy] = toScreen(isQ ? p.UMAP1 : p.x, isQ ? p.UMAP2 : p.y);
      const d = (sx - px) ** 2 + (sy - py) ** 2;
      if (d < bestD) { bestD = d; best = { p, isQ }; }
    }
  };
  if (state.showQuery) scan(state.query, true);
  if (state.showRef) scan(state.atlas, false);
  return best;
}
function handleHover(e) {
  const hit = nearestPoint(e.offsetX, e.offsetY);
  const tip = document.getElementById("tooltip");
  if (!hit) { tip.hidden = true; return; }
  const p = hit.p;
  const lines = hit.isQ
    ? [`<b>${p.cell}</b> (query)`, `→ ${p.predicted_label}`, `state: ${p.tex_state}`,
       `conf: ${p.projection_confidence}`]
    : [`<b>${p.cell}</b>`, `${p.tex_state || p.cell_type || ""}`,
       p.species ? `${p.species} · ${p.study || ""}` : ""];
  for (const a of state.axes) lines.push(`${a}: ${(hit.isQ ? p[a] : p[a]).toFixed?.(2) ?? p[a]}`);
  tip.innerHTML = lines.filter(Boolean).join("<br>");
  tip.style.left = (e.offsetX + 14) + "px"; tip.style.top = (e.offsetY + 12) + "px";
  tip.hidden = false;
}
canvas.addEventListener("click", e => {
  const hit = nearestPoint(e.offsetX, e.offsetY);
  if (!hit) return;
  showDetail(hit.p, hit.isQ);
});
function showDetail(p, isQ) {
  const box = document.getElementById("cellDetail");
  document.getElementById("detailTitle").textContent = p.cell + (isQ ? " (query)" : " (reference)");
  const body = document.getElementById("detailBody");
  const kv = (k, v) => `<div class="kv"><span>${k}</span><span>${v}</span></div>`;
  let html = "";
  if (isQ) { html += kv("predicted label", p.predicted_label); html += kv("tex state", p.tex_state);
    html += kv("confidence", p.projection_confidence); }
  else { for (const f of ["cell_type", "tex_state", "species", "modality", "study"]) if (p[f]) html += kv(f, p[f]); }
  for (const a of state.axes) html += kv(a, (isQ ? p[a] : p[a]));
  if (isQ && state.queryPathways[p.cell]) {
    html += "<div class='kv'><span><b>pathways</b></span><span></span></div>";
    for (const [pw, sc] of Object.entries(state.queryPathways[p.cell])) html += kv(pw, sc.toFixed(2));
  }
  body.innerHTML = html; box.hidden = false;
}
document.getElementById("closeDetail").addEventListener("click", () => document.getElementById("cellDetail").hidden = true);

// ----------------------------------------------------------------- controls
document.getElementById("showReference").addEventListener("change", e => { state.showRef = e.target.checked; draw(); });
document.getElementById("showQuery").addEventListener("change", e => { state.showQuery = e.target.checked; draw(); });
document.getElementById("resetView").addEventListener("click", () => { fitView(); draw(); });
window.addEventListener("resize", () => { resize(); draw(); });

// ----------------------------------------------------------------- projection
async function projectCSV(text) {
  const status = document.getElementById("projectStatus");
  status.className = "status"; status.textContent = "Projecting…";
  try {
    const method = document.getElementById("methodSelect").value;
    const mode = document.getElementById("modeSelect").value;
    const res = await fetch("/api/project", { method: "POST",
      headers: { "Content-Type": "text/csv", "X-Method": method, "X-Mode": mode }, body: text });
    const data = await res.json();
    if (data.error) throw new Error(data.error);
    state.query = data.cells;
    state.queryPathways = data.pathways;
    status.className = "status ok";
    status.textContent = `Projected ${data.n_cells} cells (${data.mode}). ${data.note || ""}`;
    renderSummary(data.summary);
    document.getElementById("showQuery").checked = true; state.showQuery = true;
    computeGeneRange();
    draw();
    agentSay("agent", summaryToText(data));
  } catch (err) {
    status.className = "status err"; status.textContent = "Error: " + err.message;
  }
}
function renderSummary(s) {
  const el = document.getElementById("projectSummary");
  if (!s || !s.composition_percent) { el.innerHTML = ""; return; }
  let html = "<b>Composition</b>";
  for (const [k, v] of Object.entries(s.composition_percent)) {
    html += `<div class="lab"><span>${k}</span><span>${v}%</span></div><div class="bar" style="width:${v}%"></div>`;
  }
  html += `<div class="lab" style="margin-top:6px"><span>mean confidence</span><span>${s.mean_confidence}</span></div>`;
  el.innerHTML = html;
}
function summaryToText(d) {
  const s = d.summary || {};
  const comp = Object.entries(s.composition_percent || {}).map(([k, v]) => `${v}% ${k}`).join(", ");
  return `Projected ${d.n_cells} cells. Composition: ${comp}. Mean confidence ${s.mean_confidence}. Color by an axis or a pathway to explore further.`;
}
document.getElementById("fileInput").addEventListener("change", e => {
  const f = e.target.files[0]; if (!f) return;
  const r = new FileReader(); r.onload = () => projectCSV(r.result); r.readAsText(f);
});
document.getElementById("loadDemoQuery").addEventListener("click", async () => {
  const res = await fetch("/api/demo_query");
  if (!res.ok) { document.getElementById("projectStatus").textContent = "No demo query configured."; return; }
  projectCSV(await res.text());
});

// ----------------------------------------------------------------- agent
function agentSay(role, text) {
  const log = document.getElementById("chatLog");
  const div = document.createElement("div"); div.className = "msg " + role;
  div.innerHTML = role === "agent" ? renderMarkdownish(text) : escapeHtml(text);
  log.appendChild(div); log.scrollTop = log.scrollHeight;
}
function escapeHtml(s) { return s.replace(/[&<>]/g, c => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;" }[c])); }
function renderMarkdownish(s) {
  return escapeHtml(s).replace(/\*\*(.+?)\*\*/g, "<strong>$1</strong>").replace(/\n/g, "<br>");
}
async function askAgent(q) {
  agentSay("user", q);
  const res = await fetch("/api/agent", { method: "POST", headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ question: q }) });
  const data = await res.json();
  // show the tool trace (what the agent actually did)
  for (const t of data.trace || []) agentSay("tool", `→ ${t.tool}(${JSON.stringify(t.args || {})})`);
  agentSay("agent", data.answer || data.error || "(no response)");
  applyAgentActions(data.actions || []);
}

async function applyAgentActions(actions) {
  for (const act of actions) {
    if (act.type === "color_by" && state.axes.concat(["tex_state", "cell_type", "species", "modality", "study"]).includes(act.field)) {
      const sel = document.getElementById("colorBy");
      sel.value = act.field; state.colorBy = act.field; state.activePathway = null; state.geneColor = null;
      document.getElementById("geneSearch").value = ""; renderPathwayActive(); computeGeneRange(); buildLegend(); draw();
    } else if (act.type === "color_by_gene" && act.gene) {
      setGene(String(act.gene).toUpperCase());
    } else if (act.type === "open_network") {
      const net = await (await fetch("/api/regulatory")).json();
      renderNetwork(net); document.getElementById("netOverlay").hidden = false;
    }
  }
}
document.getElementById("chatSend").addEventListener("click", sendChat);
document.getElementById("chatInput").addEventListener("keydown", e => { if (e.key === "Enter") sendChat(); });
function sendChat() {
  const inp = document.getElementById("chatInput"); const q = inp.value.trim();
  if (!q) return; inp.value = ""; askAgent(q);
}
document.querySelectorAll(".sug").forEach(b => b.addEventListener("click", () => askAgent(b.textContent)));

document.getElementById("llmConnect").addEventListener("click", async () => {
  const provider = document.getElementById("llmProvider").value;
  const api_key = document.getElementById("llmKey").value.trim();
  const st = document.getElementById("llmStatus");
  if (!api_key) { st.className = "status err"; st.textContent = "Paste an API key first."; return; }
  st.className = "status"; st.textContent = "Connecting…";
  const res = await fetch("/api/agent/config", { method: "POST", headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ provider, api_key }) });
  const data = await res.json();
  if (data.error) { st.className = "status err"; st.textContent = data.error; return; }
  document.getElementById("agentBackend").textContent = data.backend;
  document.getElementById("llmKey").value = "";
  st.className = "status ok"; st.textContent = "Connected — TexAgent is now a live tool-using agent.";
  agentSay("agent", "I'm now connected via " + data.backend + " and can plan with tools. Try: \"project the demo query, then tell me which programs drive its top state\".");
});

boot();
