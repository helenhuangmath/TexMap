from __future__ import annotations

import csv
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from texmap.config import TexMapConfig


Matrix = dict[str, dict[str, float]]
Table = dict[str, dict[str, str]]


def read_counts(path: str | Path, fmt: str = "csv", gene_column: str | None = None) -> Matrix:
    """Read a counts matrix with cells as rows and genes as columns."""
    if gene_column:
        raise ValueError("gene_column transposed input requires pandas; provide cells as rows for the core workflow.")
    path = Path(path)
    delimiter = "," if fmt == "csv" else "\t"
    with path.open("r", encoding="utf-8", newline="") as handle:
        reader = csv.DictReader(handle, delimiter=delimiter)
        if not reader.fieldnames:
            return {}
        cell_col = reader.fieldnames[0]
        matrix: Matrix = {}
        for row in reader:
            cell = str(row[cell_col])
            matrix[cell] = {
                gene: _float(row.get(gene, "0"))
                for gene in reader.fieldnames[1:]
            }
    return matrix


def read_metadata(path: str | Path | None) -> Table:
    if path is None:
        return {}
    path = Path(path)
    delimiter = "\t" if path.suffix.lower() in {".tsv", ".txt"} else ","
    with path.open("r", encoding="utf-8", newline="") as handle:
        reader = csv.DictReader(handle, delimiter=delimiter)
        if not reader.fieldnames:
            return {}
        cell_col = reader.fieldnames[0]
        return {str(row[cell_col]): {k: v for k, v in row.items() if k != cell_col} for row in reader}


def ensure_output_dirs(config: "TexMapConfig") -> dict[str, Path]:
    root = Path(config.output.directory)
    paths = {
        "root": root,
        "tables": root / "tables",
        "figures": root / "figures",
        "web": root / "web",
        "logs": root / "logs",
        "agent": root / "agent",
        "ml_ready": root / "ml_ready",
        "foundation_models": root / "foundation_models",
        "benchmark": root / "benchmark",
        "scalability": root / "scalability",
    }
    for path in paths.values():
        path.mkdir(parents=True, exist_ok=True)
    return paths


def write_table(path: str | Path, rows: list[dict[str, object]], index_name: str = "cell") -> None:
    path = Path(path)
    fieldnames: list[str] = [index_name]
    for row in rows:
        for key in row:
            if key not in fieldnames:
                fieldnames.append(key)
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def read_table(path: str | Path) -> list[dict[str, str]]:
    with Path(path).open("r", encoding="utf-8", newline="") as handle:
        return list(csv.DictReader(handle))


def _float(value: str | None) -> float:
    try:
        return float(value or 0)
    except ValueError:
        return 0.0
