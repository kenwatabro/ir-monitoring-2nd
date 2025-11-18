"""Minimal CLI to download EDINET filings for a date range and persist metadata."""

from __future__ import annotations

import argparse
from datetime import date
from pathlib import Path
from typing import Iterable
import xml.etree.ElementTree as ET
import zipfile

from dotenv import load_dotenv

from .downloader.edinet_downloader import EdinetDownloader


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Download EDINET filings within a date range."
    )
    parser.add_argument(
        "start_date",
        type=date.fromisoformat,
        help="Start date (YYYY-MM-DD)",
    )
    parser.add_argument(
        "end_date",
        type=date.fromisoformat,
        help="End date (YYYY-MM-DD)",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=Path("data/raw"),
        help="Directory to store downloaded archives.",
    )
    parser.add_argument(
        "--database-url",
        help="Optional PostgreSQL/Cockroach URL; omit to skip database writes",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    load_dotenv()
    parser = build_parser()
    args = parser.parse_args(argv)

    start_date = args.start_date
    end_date = args.end_date

    downloader = EdinetDownloader(start_date=start_date, end_date=end_date)
    args.output_dir.mkdir(parents=True, exist_ok=True)
    docs = downloader.download(output_dir=args.output_dir)

    print(f"Downloaded {len(docs)} document(s)")

if __name__ == "__main__":
    main()