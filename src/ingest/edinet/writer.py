"""EDINET ingestion の DB 書き込み処理."""

from __future__ import annotations

from typing import Any

from psycopg2.extras import execute_values

from src.parser.edinet.xbrl_parser import BalanceSheetSummary, CashFlowSummary, FinancialSummary


def ensure_company(cur, edinet_code: str, company_name: str, security_code: str) -> int:
    """companies に会社を INSERT or 更新して company_id を返す."""
    cur.execute(
        """
        INSERT INTO companies (edinet_code, ticker, name_jp, name_en)
        VALUES (%s, %s, %s, %s)
        ON CONFLICT (edinet_code) DO UPDATE
        SET
            ticker  = COALESCE(EXCLUDED.ticker,  companies.ticker),
            name_jp = COALESCE(NULLIF(EXCLUDED.name_jp, ''), companies.name_jp),
            name_en = COALESCE(NULLIF(EXCLUDED.name_en, ''), companies.name_en)
        RETURNING id
        """,
        (edinet_code, security_code or None, company_name or "", ""),
    )
    return int(cur.fetchone()[0])


def get_existing_doc_ids(cur) -> set[str]:
    """DB に存在する全 edinet_doc_id を返す（早期スキップ用）."""
    cur.execute("SELECT edinet_doc_id FROM filings")
    return {row[0] for row in cur.fetchall()}


def find_existing_filing_id(cur, company_id: int, edinet_doc_id: str) -> int | None:
    """既存 filing の id を返す。なければ None。"""
    cur.execute(
        "SELECT id FROM filings WHERE company_id = %s AND edinet_doc_id = %s",
        (company_id, edinet_doc_id),
    )
    row = cur.fetchone()
    return int(row[0]) if row else None


def insert_filing(
    cur,
    company_id: int,
    edinet_doc_id: str,
    meta: dict[str, str],
    fiscal_year: int | None,
    fiscal_period: str | None,
    document_type: str | None,
) -> int:
    """filings に1件 INSERT して filing_id を返す."""
    cur.execute(
        """
        INSERT INTO filings (
            company_id, edinet_doc_id,
            period_start, period_end,
            fiscal_year, fiscal_period,
            is_consolidated, document_type,
            submitted_at, source_zip_path
        )
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        RETURNING id
        """,
        (
            company_id,
            edinet_doc_id,
            meta.get("period_start") or None,
            meta.get("period_end") or None,
            fiscal_year,
            fiscal_period,
            True,
            document_type,
            None,
            str(meta.get("source_zip_path") or ""),
        ),
    )
    return int(cur.fetchone()[0])


def update_filing_meta(
    cur,
    filing_id: int,
    meta: dict[str, str],
    fiscal_year: int | None,
    fiscal_period: str | None,
) -> None:
    """既存 filing のメタ情報を COALESCE で補完更新する."""
    cur.execute(
        """
        UPDATE filings
        SET
            period_start    = COALESCE(%s, period_start),
            period_end      = COALESCE(%s, period_end),
            fiscal_year     = COALESCE(%s, fiscal_year),
            fiscal_period   = COALESCE(%s, fiscal_period),
            source_zip_path = COALESCE(%s, source_zip_path)
        WHERE id = %s
        """,
        (
            meta.get("period_start") or None,
            meta.get("period_end") or None,
            fiscal_year,
            fiscal_period,
            meta.get("source_zip_path") or None,
            filing_id,
        ),
    )


def insert_statements_and_items(
    cur,
    filing_id: int,
    cfg: dict[str, Any],
    fs: FinancialSummary,
    cf: CashFlowSummary,
    bs: BalanceSheetSummary,
) -> None:
    """PL/CF/BS の statements と statement_items を一括 INSERT する."""
    sections: list[tuple[str, str, Any]] = [
        ("PL", "financial", fs),
        ("CF", "cash_flow", cf),
        ("BS", "balance_sheet", bs),
    ]

    items_values: list[tuple[int, str, str, float | None, int]] = []

    for statement_type, cfg_key, summary_obj in sections:
        cur.execute(
            """
            INSERT INTO statements (
                filing_id, statement_type,
                currency, unit, role_uri, statement_label
            )
            VALUES (%s, %s, %s, %s, %s, %s)
            ON CONFLICT (filing_id, statement_type)
                DO UPDATE SET statement_type = EXCLUDED.statement_type
            RETURNING id
            """,
            (filing_id, statement_type, None, None, None, None),
        )
        statement_id = int(cur.fetchone()[0])

        fields_cfg: dict[str, dict[str, Any]] = cfg.get(cfg_key, {}).get("fields", {})
        data: dict[str, Any] = summary_obj.to_dict()

        for order_index, (key, value) in enumerate(data.items(), start=1):
            label_ja = fields_cfg.get(key, {}).get("label_ja", key)
            items_values.append((statement_id, key, label_ja, value, order_index))

    if items_values:
        execute_values(
            cur,
            """
            INSERT INTO statement_items (
                statement_id, item_key, label_ja, value_numeric, order_index
            )
            VALUES %s
            ON CONFLICT (statement_id, item_key)
                DO UPDATE SET
                    value_numeric = EXCLUDED.value_numeric,
                    label_ja      = EXCLUDED.label_ja,
                    order_index   = EXCLUDED.order_index
            """,
            items_values,
        )
