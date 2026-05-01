"""EDINET API documents.json のメタデータを edinet_documents に保存する."""

from __future__ import annotations

from collections.abc import Iterable
from datetime import datetime
from typing import Any

from psycopg2.extras import execute_values

from src.db import get_connection


def _parse_date(value: Any) -> str | None:
    """EDINETの日付値を 'YYYY-MM-DD' 文字列として返す（不正値は None）。"""
    if value in (None, ""):
        return None
    candidate = str(value)
    try:
        datetime.fromisoformat(candidate)
    except ValueError:
        return None
    return candidate


def _build_rows(docs: Iterable[dict[str, Any]]) -> list[tuple]:
    """edinet_documents テーブル向けの行タプルを生成する.

    同じ doc_id が複数回出現した場合は後のものを優先する（重複排除）。
    """
    rows_by_doc_id: dict[str, tuple] = {}
    for doc in docs:
        doc_id = doc.get("docID")
        if not doc_id:
            continue
        sec_code = doc.get("secCode") or None
        filer_name = doc.get("filerName") or None
        doc_type_code = doc.get("docTypeCode") or None
        period_start = _parse_date(doc.get("periodStart"))
        period_end = _parse_date(doc.get("periodEnd"))
        submit_date = _parse_date(doc.get("submitDate"))

        rows_by_doc_id[doc_id] = (
            doc_id,
            sec_code,
            filer_name,
            doc_type_code,
            period_start,
            period_end,
            submit_date,
        )
    return list(rows_by_doc_id.values())


def upsert_edinet_documents(
    docs: Iterable[dict[str, Any]],
    dsn: str | None = None,
) -> None:
    """EDINETメタデータ(docs)を edinet_documents に upsert する."""
    rows = _build_rows(docs)
    if not rows:
        return

    with get_connection(dsn) as conn:
        conn.autocommit = False
        with conn.cursor() as cur:
            execute_values(
                cur,
                """
                INSERT INTO edinet_documents (
                    doc_id,
                    sec_code,
                    filer_name,
                    doc_type_code,
                    period_start,
                    period_end,
                    submit_date
                )
                VALUES %s
                ON CONFLICT (doc_id) DO UPDATE
                SET
                    sec_code = EXCLUDED.sec_code,
                    filer_name = EXCLUDED.filer_name,
                    doc_type_code = EXCLUDED.doc_type_code,
                    period_start = EXCLUDED.period_start,
                    period_end = EXCLUDED.period_end,
                    submit_date = EXCLUDED.submit_date
                """,
                rows,
            )
        conn.commit()
