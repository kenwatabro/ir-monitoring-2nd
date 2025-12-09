"""EDINET XBRL ZIP から PostgreSQL にデータをロードするローダー."""

from __future__ import annotations

import logging
import zipfile
import xml.etree.ElementTree as ET
from datetime import date
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from psycopg2.extras import execute_values

from src.db import get_connection
from src.parser.configs import load_edinet_config
from src.parser.edinet.xbrl_parser import (
    BalanceSheetSummary,
    CashFlowSummary,
    FinancialSummary,
)
from src.parser.edinet.utils import find_instance_xbrl_name


logger = logging.getLogger(__name__)


def extract_basic_metadata_from_zip(zip_path: Path) -> Dict[str, str]:
    """XBRLインスタンスから会社コード・社名・期間などのメタ情報をざっくり抽出する."""
    meta: Dict[str, str] = {
        "edinet_code": "",
        "company_name": "",
        "security_code": "",
        "period_start": "",
        "period_end": "",
    }

    try:
        with zipfile.ZipFile(zip_path) as zf:
            xbrl_name = find_instance_xbrl_name(zf)
            with zf.open(xbrl_name) as fh:
                tree = ET.parse(fh)
    except Exception as exc:  # noqa: BLE001
        logger.warning("failed to extract metadata from %s: %s", zip_path, exc)
        return meta

    root = tree.getroot()

    contexts: List[ET.Element] = [
        elem for elem in root if elem.tag.lower().endswith("context")
    ]

    chosen_ctx: Optional[ET.Element] = None
    for ctx in contexts:
        ctx_id = ctx.attrib.get("id", "")
        if "CurrentYear" in ctx_id and ctx.find(".//{*}startDate") is not None:
            chosen_ctx = ctx
            break
    if chosen_ctx is None and contexts:
        chosen_ctx = contexts[0]

    if chosen_ctx is not None:
        ident = chosen_ctx.find(".//{*}identifier")
        if ident is not None and ident.text:
            meta["edinet_code"] = ident.text.strip()

        period = chosen_ctx.find(".//{*}period")
        if period is not None:
            start = period.find(".//{*}startDate")
            end = period.find(".//{*}endDate")
            instant = period.find(".//{*}instant")
            if start is not None and start.text:
                meta["period_start"] = start.text.strip()
            if end is not None and end.text:
                meta["period_end"] = end.text.strip()
            elif instant is not None and instant.text:
                meta["period_end"] = instant.text.strip()

    # 会社名・銘柄コードなど（存在すれば）を拾う
    def _local_name(tag: str) -> str:
        if "}" in tag:
            return tag.split("}", 1)[1]
        return tag

    for elem in root.iter():
        lname = _local_name(elem.tag)
        if not elem.text:
            continue
        text = elem.text.strip()

        if not meta["company_name"] and lname in ("CompanyNameCoverPage", "CompanyName"):
            meta["company_name"] = text
        if not meta["security_code"] and lname in ("SecurityCode", "SecurityCodeCoverPage"):
            meta["security_code"] = text

        if meta["company_name"] and meta["security_code"]:
            break

    return meta


def _infer_fiscal_info(period_start: str, period_end: str) -> Tuple[Optional[int], Optional[str]]:
    """期間からざっくりと決算年度と期（FY, Q1〜Q4）を推定する."""
    if not period_end:
        return None, None
    try:
        end_date = date.fromisoformat(period_end)
    except ValueError:
        return None, None

    # ざっくり: 期末年を fiscal_year とし、月から四半期を推定
    fiscal_year = end_date.year
    month = end_date.month

    fiscal_period: Optional[str]
    if month in (3, 4, 5):
        fiscal_period = "FY"  # 本決算とみなす
    elif month in (6, 7, 8):
        fiscal_period = "Q1"
    elif month in (9, 10, 11):
        fiscal_period = "Q2"
    else:
        fiscal_period = "Q3"

    return fiscal_year, fiscal_period


def _ensure_company(cur, edinet_code: str, company_name: str, security_code: str) -> int:
    """companies に会社をINSERT or 更新して company_id を返す."""
    cur.execute(
        """
        INSERT INTO companies (edinet_code, ticker, name_jp, name_en)
        VALUES (%s, %s, %s, %s)
        ON CONFLICT (edinet_code) DO UPDATE
        SET
            ticker = COALESCE(EXCLUDED.ticker, companies.ticker),
            name_jp = COALESCE(NULLIF(EXCLUDED.name_jp, ''), companies.name_jp),
            name_en = COALESCE(NULLIF(EXCLUDED.name_en, ''), companies.name_en)
        RETURNING id
        """,
        (edinet_code, security_code or None, company_name or "", ""),
    )
    company_id = cur.fetchone()[0]
    return company_id


def _find_existing_filing_id(cur, company_id: int, edinet_doc_id: str) -> Optional[int]:
    cur.execute(
        """
        SELECT id
        FROM filings
        WHERE company_id = %s AND edinet_doc_id = %s
        """,
        (company_id, edinet_doc_id),
    )
    row = cur.fetchone()
    return int(row[0]) if row else None


def _insert_filing(
    cur,
    company_id: int,
    edinet_doc_id: str,
    meta: Dict[str, str],
) -> int:
    fiscal_year, fiscal_period = _infer_fiscal_info(
        meta.get("period_start") or "",
        meta.get("period_end") or "",
    )

    cur.execute(
        """
        INSERT INTO filings (
            company_id,
            edinet_doc_id,
            period_start,
            period_end,
            fiscal_year,
            fiscal_period,
            is_consolidated,
            document_type,
            submitted_at,
            source_zip_path
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
            None,
            None,
            str(meta.get("source_zip_path") or ""),
        ),
    )
    filing_id = cur.fetchone()[0]
    return filing_id


def _insert_statements_and_items(
    cur,
    filing_id: int,
    cfg: Dict[str, Any],
    fs: FinancialSummary,
    cf: CashFlowSummary,
    bs: BalanceSheetSummary,
) -> None:
    sections: List[Tuple[str, str, Any]] = [
        ("PL", "financial", fs),
        ("CF", "cash_flow", cf),
        ("BS", "balance_sheet", bs),
    ]

    items_values: List[Tuple[int, str, str, Optional[float], int]] = []

    for statement_type, cfg_key, summary_obj in sections:
        # statements
        cur.execute(
            """
            INSERT INTO statements (
                filing_id,
                statement_type,
                currency,
                unit,
                role_uri,
                statement_label
            )
            VALUES (%s, %s, %s, %s, %s, %s)
            RETURNING id
            """,
            (filing_id, statement_type, None, None, None, None),
        )
        statement_id = int(cur.fetchone()[0])

        # items
        fields_cfg: Dict[str, Dict[str, Any]] = cfg.get(cfg_key, {}).get("fields", {})
        data: Dict[str, Any] = summary_obj.to_dict()

        order_index = 0
        for key, value in data.items():
            order_index += 1
            spec = fields_cfg.get(key, {})
            label_ja = spec.get("label_ja", key)
            items_values.append(
                (statement_id, key, label_ja, value, order_index),
            )

    if items_values:
        execute_values(
            cur,
            """
            INSERT INTO statement_items (
                statement_id,
                item_key,
                label_ja,
                value_numeric,
                order_index
            )
            VALUES %s
            """,
            items_values,
        )


def load_edinet_directory(
    edinet_dir: Path | str,
    dsn: Optional[str] = None,
    max_files: Optional[int] = None,
) -> None:
    """data/raw/edinet 配下のZIP群をDBにロードする."""
    base_path = Path(edinet_dir)
    cfg = load_edinet_config()

    zip_paths: List[Path] = sorted(base_path.glob("*.zip"))
    if max_files is not None:
        zip_paths = zip_paths[:max_files]

    if not zip_paths:
        logger.info("no ZIP files found under %s", base_path)
        return

    with get_connection(dsn) as conn:
        conn.autocommit = False
        with conn.cursor() as cur:
            for idx, zip_path in enumerate(zip_paths, start=1):
                edinet_doc_id = zip_path.stem
                logger.info("[%s/%s] processing %s", idx, len(zip_paths), edinet_doc_id)

                try:
                    meta = extract_basic_metadata_from_zip(zip_path)
                    meta["source_zip_path"] = str(zip_path)
                    edinet_code = meta.get("edinet_code") or "UNKNOWN"

                    company_id = _ensure_company(
                        cur,
                        edinet_code,
                        meta.get("company_name", ""),
                        meta.get("security_code", ""),
                    )

                    existing_filing_id = _find_existing_filing_id(cur, company_id, edinet_doc_id)
                    if existing_filing_id is not None:
                        # 既存filingについても、期間情報などは更新しておく
                        fiscal_year, fiscal_period = _infer_fiscal_info(
                            meta.get("period_start") or "",
                            meta.get("period_end") or "",
                        )
                        cur.execute(
                            """
                            UPDATE filings
                            SET
                                period_start = COALESCE(%s, period_start),
                                period_end = COALESCE(%s, period_end),
                                fiscal_year = COALESCE(%s, fiscal_year),
                                fiscal_period = COALESCE(%s, fiscal_period),
                                source_zip_path = COALESCE(%s, source_zip_path)
                            WHERE id = %s
                            """,
                            (
                                meta.get("period_start") or None,
                                meta.get("period_end") or None,
                                fiscal_year,
                                fiscal_period,
                                meta.get("source_zip_path") or None,
                                existing_filing_id,
                            ),
                        )
                        conn.commit()
                        continue

                    fs = FinancialSummary.parse_zip(zip_path)
                    cf = CashFlowSummary.parse_zip(zip_path)
                    bs = BalanceSheetSummary.parse_zip(zip_path)

                    filing_id = _insert_filing(cur, company_id, edinet_doc_id, meta)
                    _insert_statements_and_items(cur, filing_id, cfg, fs, cf, bs)

                    conn.commit()
                except FileNotFoundError:
                    # ZIP 内に .xbrl がない等
                    logger.warning("no .xbrl found in %s; skipping", zip_path)
                    conn.rollback()
                except Exception:  # noqa: BLE001
                    logger.exception("failed to load %s; rolling back", zip_path)
                    conn.rollback()



