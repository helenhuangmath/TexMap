from __future__ import annotations

import html
import math
from pathlib import Path

from texmap.io import read_table


def write_figures(paths: dict[str, Path]) -> list[Path]:
    outputs = [
        write_integrated_umap(paths),
        write_pathway_heatmap(paths),
    ]
    return [path for path in outputs if path is not None]


def write_integrated_umap(paths: dict[str, Path]) -> Path | None:
    embedding_path = paths["tables"] / "integrated_embedding.csv"
    if not embedding_path.exists():
        return None

    rows = [_typed(row) for row in read_table(embedding_path)]
    points = [row for row in rows if _is_number(row.get("UMAP1")) and _is_number(row.get("UMAP2"))]
    if not points:
        return None

    width, height = 900, 680
    pad_left, pad_right, pad_top, pad_bottom = 76, 34, 62, 72
    xs = [float(row["UMAP1"]) for row in points]
    ys = [float(row["UMAP2"]) for row in points]
    min_x, max_x = min(xs), max(xs)
    min_y, max_y = min(ys), max(ys)

    def sx(value: object) -> float:
        return pad_left + (float(value) - min_x) / ((max_x - min_x) or 1.0) * (width - pad_left - pad_right)

    def sy(value: object) -> float:
        return height - pad_bottom - (float(value) - min_y) / ((max_y - min_y) or 1.0) * (height - pad_top - pad_bottom)

    palette = ["#32746d", "#d94c36", "#255f85", "#d9822b", "#7c6a0a", "#218380"]
    sources = sorted({str(row.get("source") or "unknown") for row in points})
    source_colors = {source: palette[i % len(palette)] for i, source in enumerate(sources)}
    if "reference" in source_colors:
        source_colors["reference"] = "#32746d"
    if "query" in source_colors:
        source_colors["query"] = "#d94c36"

    body = []
    for row in points:
        source = str(row.get("source") or "")
        color = source_colors.get(source, "#5f6b7a")
        radius = 5 if source == "reference" else 7
        opacity = 0.58 if source == "reference" else 0.92
        label = html.escape(str(row.get("predicted_label") or row.get("cell") or ""))
        body.append(
            f'<circle cx="{sx(row["UMAP1"]):.2f}" cy="{sy(row["UMAP2"]):.2f}" r="{radius}" '
            f'fill="{color}" fill-opacity="{opacity}"><title>{label}</title></circle>'
        )
    legend = []
    for i, source in enumerate(sources):
        x = width - 210
        y = 28 + i * 20
        color = source_colors.get(source, "#5f6b7a")
        legend.append(
            f'<circle cx="{x}" cy="{y}" r="5" fill="{color}" fill-opacity="0.88"/>'
            f'<text x="{x + 12}" y="{y + 5}" font-family="Arial" font-size="12" fill="#1d2433">{html.escape(source)}</text>'
        )

    svg = f"""<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}" role="img" aria-label="Integrated UMAP">
  <rect width="100%" height="100%" fill="#fbfcfd"/>
  <text x="{pad_left}" y="34" font-family="Arial" font-size="24" font-weight="700" fill="#1d2433">Integrated reference map</text>
  <text x="{pad_left}" y="56" font-family="Arial" font-size="14" fill="#5f6b7a">Query cells are overlaid on reference coordinates</text>
  <line x1="{pad_left}" y1="{height - pad_bottom}" x2="{width - pad_right}" y2="{height - pad_bottom}" stroke="#9aa6b2"/>
  <line x1="{pad_left}" y1="{pad_top}" x2="{pad_left}" y2="{height - pad_bottom}" stroke="#9aa6b2"/>
  <text x="{width / 2:.0f}" y="{height - 24}" font-family="Arial" font-size="14" fill="#5f6b7a">UMAP1</text>
  <text x="22" y="{height / 2:.0f}" transform="rotate(-90 22 {height / 2:.0f})" font-family="Arial" font-size="14" fill="#5f6b7a">UMAP2</text>
  {"".join(body)}
  {"".join(legend)}
</svg>
"""
    out = paths["figures"] / "integrated_umap.svg"
    out.write_text(svg, encoding="utf-8")
    return out


def write_pathway_heatmap(paths: dict[str, Path]) -> Path | None:
    pathway_path = paths["tables"] / "pathway_scores.csv"
    if not pathway_path.exists():
        return None

    rows = [_typed(row) for row in read_table(pathway_path)]
    if not rows:
        return None
    pathways = [key for key in rows[0] if key != "cell"]
    if not pathways:
        return None

    cell_w, cell_h = 132, 30
    label_w, top_h = 154, 122
    width = label_w + len(pathways) * cell_w + 34
    height = top_h + len(rows) * cell_h + 42
    values = [float(row[pathway]) for row in rows for pathway in pathways if _is_number(row.get(pathway))]
    min_v, max_v = (min(values), max(values)) if values else (0.0, 1.0)

    body = []
    for i, row in enumerate(rows):
        y = top_h + i * cell_h
        body.append(
            f'<text x="{label_w - 10}" y="{y + 20}" text-anchor="end" '
            f'font-family="Arial" font-size="12" fill="#1d2433">{html.escape(str(row.get("cell") or ""))}</text>'
        )
        for j, pathway in enumerate(pathways):
            x = label_w + j * cell_w
            value = float(row.get(pathway) or 0.0)
            body.append(
                f'<rect x="{x}" y="{y}" width="{cell_w}" height="{cell_h}" fill="{_heat_color(value, min_v, max_v)}" stroke="#ffffff"/>'
            )
            body.append(
                f'<text x="{x + cell_w / 2:.1f}" y="{y + 20}" text-anchor="middle" '
                f'font-family="Arial" font-size="11" fill="#1d2433">{value:.2f}</text>'
            )
    for j, pathway in enumerate(pathways):
        x = label_w + j * cell_w + cell_w / 2
        body.append(
            f'<text x="{x:.1f}" y="{top_h - 12}" transform="rotate(-36 {x:.1f} {top_h - 12})" '
            f'text-anchor="start" font-family="Arial" font-size="12" fill="#1d2433">{html.escape(pathway)}</text>'
        )

    svg = f"""<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}" role="img" aria-label="Pathway heatmap">
  <rect width="100%" height="100%" fill="#fbfcfd"/>
  <text x="24" y="34" font-family="Arial" font-size="24" font-weight="700" fill="#1d2433">Pathway activity heatmap</text>
  <text x="24" y="56" font-family="Arial" font-size="14" fill="#5f6b7a">Mean normalized expression across genes in each pathway</text>
  {"".join(body)}
</svg>
"""
    out = paths["figures"] / "pathway_heatmap.svg"
    out.write_text(svg, encoding="utf-8")
    return out


def _typed(row: dict[str, str]) -> dict[str, object]:
    return {key: _typed_value(value) for key, value in row.items()}


def _typed_value(value: str) -> object:
    if value == "":
        return None
    try:
        return float(value)
    except ValueError:
        return value


def _is_number(value: object) -> bool:
    return isinstance(value, (int, float)) and math.isfinite(float(value))


def _heat_color(value: float, min_v: float, max_v: float) -> str:
    t = (value - min_v) / ((max_v - min_v) or 1.0)
    t = max(0.0, min(1.0, t))
    low = (237, 242, 247)
    high = (217, 76, 54)
    rgb = [round(low[i] + (high[i] - low[i]) * t) for i in range(3)]
    return f"#{rgb[0]:02x}{rgb[1]:02x}{rgb[2]:02x}"
