from __future__ import annotations

import argparse
from pathlib import Path

from texmap.config import load_config
from texmap import pipeline


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="texmap", description="Run TexMap single-cell integration workflows.")
    sub = parser.add_subparsers(dest="command", required=True)
    for name in ["prepare", "analyze", "integrate", "pathways", "ai", "report", "run"]:
        cmd = sub.add_parser(name, help=f"Run the {name} stage")
        cmd.add_argument("--config", required=True, help="Path to a TexMap YAML configuration.")
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    config = load_config(args.config)
    result = getattr(pipeline, args.command)(config)
    print(f"TexMap {args.command} complete: {Path(result)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
