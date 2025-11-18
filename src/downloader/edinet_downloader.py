"""Simplified EDINET downloader.

This module downloads filings for a single security code within a date range.
"""

from __future__ import annotations

import logging
import os
from datetime import date, timedelta
from pathlib import Path
from typing import Any, Dict, List

import requests

from ._base import BaseDownloader

logger = logging.getLogger(__name__)
DEFAULT_BASE_URL = "https://api.edinet-fsa.go.jp/api/v2"
METADATA_ENDPOINT = f"{DEFAULT_BASE_URL}/documents.json"
DOCUMENT_ENDPOINT = f"{DEFAULT_BASE_URL}/documents"
TARGET_DOC_TYPES = {"120", "130"}  # yuho + quarterly


class EdinetDownloader(BaseDownloader):
    """Fetches EDINET filings for a security within a date window."""

    def __init__(self, start_date: date, end_date: date) -> None:
        super().__init__(start_date=start_date, end_date=end_date)
        self.api_key = os.getenv("EDINET_API_KEY")
        self.session = requests.Session()

    def download(self, output_dir: Path | str) -> List[Dict[str, Any]]:
        output_path = Path(output_dir)
        output_path.mkdir(parents=True, exist_ok=True)
        downloaded_docs: List[Dict[str, Any]] = []
        current = self.start_date
        while current <= self.end_date:
            data = self._fetch_metadata(current)
            for doc in data.get("results", []):
                if doc.get("docTypeCode") in TARGET_DOC_TYPES:
                    archive_path = self._download_document(doc, output_path)
                    if archive_path:
                        enriched_doc = dict(doc)
                        enriched_doc["archive_path"] = archive_path
                        enriched_doc["download_date"] = current
                        downloaded_docs.append(enriched_doc)
            current += timedelta(days=1)
        return downloaded_docs
    
    def _fetch_metadata(self, current: date) -> dict:
        params = {
            "date": current.strftime("%Y-%m-%d"),
            "type": 2,  # 提出書類一覧+メタデータ
            "Subscription-Key": self.api_key,
        }
        resp = self.session.get(METADATA_ENDPOINT, params=params, timeout=30)
        resp.raise_for_status()
        data = resp.json()
        status = data.get("status")
        if status is not None and status.lower() != "success":
            message = data.get("message") or "EDINET API returned error"
            raise RuntimeError(message)
        return data

    def _download_document(self, doc: dict, output_dir: Path) -> Path | None:
        doc_id = doc.get("docID")
        if not doc_id:
            logger.warning("Skipping document without docID: %s", doc)
            return None

        params = {
            "type": 1,  # ZIP(XBRL一式)
            "Subscription-Key": self.api_key,
        }
        url = f"{DOCUMENT_ENDPOINT}/{doc_id}"
        resp = self.session.get(url, params=params, timeout=120, stream=True)
        if resp.status_code == 404:
            logger.warning("Document %s not found (404)", doc_id)
            return None
        resp.raise_for_status()

        filename = f"{doc_id}.zip"
        dest_path = output_dir / filename
        with open(dest_path, "wb") as fh:
            for chunk in resp.iter_content(chunk_size=1024 * 128):
                if chunk:
                    fh.write(chunk)
        return dest_path


           
