from __future__ import annotations

import argparse
from pathlib import Path

from texmap.config import load_config
from texmap import pipeline

PIPELINE_STAGES = ["prepare", "analyze", "integrate", "pathways", "ai", "report", "run"]
DEFAULT_ATLAS_DIR = Path("examples/tex_atlas")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="texmap", description="TexMap: reference-map single-cell exhaustion analysis + web explorer.")
    sub = parser.add_subparsers(dest="command", required=True)

    for name in PIPELINE_STAGES:
        cmd = sub.add_parser(name, help=f"Run the {name} stage")
        cmd.add_argument("--config", required=True, help="Path to a TexMap YAML configuration.")

    demo = sub.add_parser("demo", help="Generate the demo Tex reference atlas + example inputs.")
    demo.add_argument("--out", default=str(DEFAULT_ATLAS_DIR), help="Output directory for the demo atlas.")

    build = sub.add_parser("build-reference", help="Build a TexMap reference from a REAL expression matrix (CSV/.h5ad).")
    build.add_argument("--counts", required=True, help="Counts matrix: CSV (cells as rows) or .h5ad.")
    build.add_argument("--metadata", help="Optional cell metadata CSV/TSV.")
    build.add_argument("--label-column", default="cell_type", help="Metadata column to use as the label.")
    build.add_argument("--out", required=True, help="Output directory for the reference.")

    serve = sub.add_parser("serve", help="Launch the interactive web explorer.")
    serve.add_argument("--config", help="Path to a TexMap YAML config (defaults to the demo atlas).")
    serve.add_argument("--host", default="127.0.0.1")
    serve.add_argument("--port", type=int, default=8000)
    return parser


def _ensure_demo_atlas(out: Path) -> Path:
    config_path = out / "config.yaml"
    if not config_path.exists():
        from texmap.demo import build_atlas
        print(f"Building demo Tex atlas in {out} …")
        build_atlas(out)
    return config_path


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    if args.command == "demo":
        from texmap.demo import build_atlas
        out = Path(args.out)
        build_atlas(out)
        print(f"TexMap demo atlas written to {out}")
        print(f"Explore it with: texmap serve --config {out / 'config.yaml'}")
        return 0

    if args.command == "build-reference":
        from texmap.ingest import build_reference
        cfg = build_reference(args.counts, Path(args.out), metadata_path=args.metadata,
                              label_column=args.label_column)
        print(f"TexMap reference built at {Path(args.out)}")
        print(f"Explore it with: texmap serve --config {cfg}")
        return 0

    if args.command == "serve":
        from texmap.server import serve
        config_path = Path(args.config) if args.config else _ensure_demo_atlas(DEFAULT_ATLAS_DIR)
        serve(load_config(config_path), host=args.host, port=args.port)
        return 0

    config = load_config(args.config)
    result = getattr(pipeline, args.command)(config)
    print(f"TexMap {args.command} complete: {Path(result)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
