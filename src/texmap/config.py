from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any


@dataclass
class InputConfig:
    counts: Path
    metadata: Path | None = None
    format: str = "csv"
    gene_column: str | None = None


@dataclass
class ReferenceConfig:
    embedding: Path | None = None
    metadata: Path | None = None
    label_column: str = "cell_type"


@dataclass
class AnalysisConfig:
    min_genes: int = 0
    min_cells: int = 0
    normalize_target_sum: float = 10_000.0
    n_hvg: int = 2_000
    n_pcs: int = 30
    n_neighbors: int = 15
    random_state: int = 13
    pathway_sets: Path | None = None


@dataclass
class OutputConfig:
    directory: Path = Path("outputs/texmap_run")
    project_name: str = "TexMap project"


@dataclass
class TexMapConfig:
    input: InputConfig
    reference: ReferenceConfig = field(default_factory=ReferenceConfig)
    analysis: AnalysisConfig = field(default_factory=AnalysisConfig)
    output: OutputConfig = field(default_factory=OutputConfig)


def _resolve(base: Path, value: Any) -> Any:
    if value is None or isinstance(value, (int, float, bool)):
        return value
    path = Path(value)
    return path if path.is_absolute() else (base / path).resolve()


def load_config(path: str | Path) -> TexMapConfig:
    """Load a TexMap YAML configuration and resolve relative paths."""
    config_path = Path(path).resolve()
    base = config_path.parent
    with config_path.open("r", encoding="utf-8") as handle:
        raw = _load_yaml(handle.read())

    input_raw = raw.get("input", {})
    if "counts" not in input_raw:
        raise ValueError("Config is missing required field input.counts")

    reference_raw = raw.get("reference", {})
    analysis_raw = raw.get("analysis", {})
    output_raw = raw.get("output", {})

    return TexMapConfig(
        input=InputConfig(
            counts=_resolve(base, input_raw["counts"]),
            metadata=_resolve(base, input_raw.get("metadata")),
            format=input_raw.get("format", "csv"),
            gene_column=input_raw.get("gene_column"),
        ),
        reference=ReferenceConfig(
            embedding=_resolve(base, reference_raw.get("embedding")),
            metadata=_resolve(base, reference_raw.get("metadata")),
            label_column=reference_raw.get("label_column", "cell_type"),
        ),
        analysis=AnalysisConfig(
            min_genes=int(analysis_raw.get("min_genes", 0)),
            min_cells=int(analysis_raw.get("min_cells", 0)),
            normalize_target_sum=float(analysis_raw.get("normalize_target_sum", 10_000.0)),
            n_hvg=int(analysis_raw.get("n_hvg", 2_000)),
            n_pcs=int(analysis_raw.get("n_pcs", 30)),
            n_neighbors=int(analysis_raw.get("n_neighbors", 15)),
            random_state=int(analysis_raw.get("random_state", 13)),
            pathway_sets=_resolve(base, analysis_raw.get("pathway_sets")),
        ),
        output=OutputConfig(
            directory=_resolve(base, output_raw.get("directory", "outputs/texmap_run")),
            project_name=output_raw.get("project_name", "TexMap project"),
        ),
    )


def _load_yaml(text: str) -> dict[str, Any]:
    try:
        import yaml  # type: ignore

        return yaml.safe_load(text) or {}
    except ModuleNotFoundError:
        return _load_simple_yaml(text)


def _load_simple_yaml(text: str) -> dict[str, Any]:
    """Parse the small nested key/value YAML subset used by TexMap examples."""
    root: dict[str, Any] = {}
    stack: list[tuple[int, dict[str, Any]]] = [(-1, root)]
    for raw_line in text.splitlines():
        if not raw_line.strip() or raw_line.lstrip().startswith("#"):
            continue
        indent = len(raw_line) - len(raw_line.lstrip(" "))
        key, _, value = raw_line.strip().partition(":")
        while stack and indent <= stack[-1][0]:
            stack.pop()
        parent = stack[-1][1]
        if value.strip() == "":
            child: dict[str, Any] = {}
            parent[key] = child
            stack.append((indent, child))
        else:
            parent[key] = _parse_scalar(value.strip())
    return root


def _parse_scalar(value: str) -> Any:
    value = value.strip("'\"")
    lowered = value.lower()
    if lowered in {"true", "false"}:
        return lowered == "true"
    try:
        return int(value)
    except ValueError:
        pass
    try:
        return float(value)
    except ValueError:
        return value
