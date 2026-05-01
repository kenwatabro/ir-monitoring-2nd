"""Lightweight downloader primitives for the reset codebase."""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import date
from pathlib import Path


class BaseDownloader(ABC):
    """Common downloader contract managed by explicit date range."""

    def __init__(self, start_date: date, end_date: date) -> None:
        if end_date < start_date:
            raise ValueError("end_date must be on or after start_date")
        self.start_date = start_date
        self.end_date = end_date

    @abstractmethod
    def download(self, output_dir: Path) -> list[dict]:
        """Fetch documents for the configured date range into output_dir."""


@dataclass(slots=True)
class DownloadSummary:
    """Result of a download run."""

    requested_days: int
    downloaded_files: list[Path] = field(default_factory=list)
    documents: list[dict] = field(default_factory=list)  # doc metadata + path
    skipped_days: int = 0
    failed_days: int = 0

    def record_download(self, path: Path) -> None:
        self.downloaded_files.append(path)

    def __str__(self) -> str:  # pragma: no cover - helper for CLI prints
        return (
            f"Days={self.requested_days} downloaded={len(self.downloaded_files)} "
            f"skipped={self.skipped_days} failed={self.failed_days}"
        )
