"""EDINETのZIP群をPostgreSQLにロードするCLI."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.ingest import load_edinet_directory  # noqa: E402


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Load EDINET XBRL ZIP files into PostgreSQL.",
    )
    parser.add_argument(
        "--edinet-dir",
        type=Path,
        default=Path("data/raw/edinet"),
        help="Directory containing EDINET ZIP archives (default: data/raw/edinet).",
    )
    parser.add_argument(
        "--dsn",
        type=str,
        default=None,
        help="PostgreSQL DSN. If omitted, PGURL env var or default local DSN is used.",
    )
    parser.add_argument(
        "--max-files",
        type=int,
        default=None,
        help="Optional limit on number of ZIP files to process.",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    load_edinet_directory(
        edinet_dir=args.edinet_dir,
        dsn=args.dsn,
        max_files=args.max_files,
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())


