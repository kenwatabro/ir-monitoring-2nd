"""EDINET XBRL ZIP から PostgreSQL にデータをロードするローダー."""

from __future__ import annotations

import logging
from datetime import date
from pathlib import Path

from src.db import get_connection
from src.ingest._base import BaseLoader
from src.ingest.edinet.writer import (
    ensure_company,
    find_existing_filing_id,
    get_existing_doc_ids,
    insert_filing,
    insert_statements_and_items,
    update_filing_meta,
)
from src.parser.configs import load_edinet_config
from src.parser.edinet import utils as xbrl_utils
from src.parser.edinet.utils import extract_zip_metadata
from src.parser.edinet.xbrl_parser import (
    BalanceSheetSummary,
    CashFlowSummary,
    FinancialSummary,
)

logger = logging.getLogger(__name__)


def _infer_fiscal_info(period_start: str, period_end: str) -> tuple[int | None, str | None]:
    """期間の長さから決算年度と期（FY, Q1〜Q3）を推定する.

    >= 330日 → FY / >= 240日 → Q3 / >= 150日 → Q2 / それ以下 → Q1
    月のみで判断する旧ロジックは 12月決算企業の本決算を Q3 に誤分類していた。
    """
    if not period_end:
        return None, None
    try:
        end_date = date.fromisoformat(period_end)
    except ValueError:
        return None, None

    fiscal_year = end_date.year

    if period_start:
        try:
            start_date = date.fromisoformat(period_start)
            days = (end_date - start_date).days
            if days >= 330:
                return fiscal_year, "FY"
            if days >= 240:
                return fiscal_year, "Q3"
            if days >= 150:
                return fiscal_year, "Q2"
            return fiscal_year, "Q1"
        except ValueError:
            pass

    return fiscal_year, None


def _infer_document_type(fiscal_period: str | None) -> str | None:
    if fiscal_period == "FY":
        return "yuho"
    if fiscal_period in ("Q1", "Q2", "Q3"):
        return "shihanki"
    return None


class EdinetLoader(BaseLoader):
    """EDINET XBRLファイルをDBにロードするローダー."""

    def load_directory(self, source_dir: Path | str, max_files: int | None = None) -> None:
        load_edinet_directory(source_dir, dsn=self.dsn, max_files=max_files)


def load_edinet_directory(
    edinet_dir: Path | str,
    dsn: str | None = None,
    max_files: int | None = None,
) -> None:
    """data/raw/edinet 配下の ZIP 群を DB にロードする."""
    base_path = Path(edinet_dir)
    cfg = load_edinet_config()

    zip_paths: list[Path] = sorted(base_path.glob("*.zip"))
    if max_files is not None:
        zip_paths = zip_paths[:max_files]

    if not zip_paths:
        logger.info("no ZIP files found under %s", base_path)
        return

    with get_connection(dsn) as conn:
        conn.autocommit = False
        with conn.cursor() as cur:
            existing_doc_ids = get_existing_doc_ids(cur)
            logger.info(
                "Found %d existing filings in DB, %d ZIP files to check",
                len(existing_doc_ids),
                len(zip_paths),
            )

            skipped_existing = skipped_no_xbrl = skipped_no_edinet_code = 0
            loaded_count = error_count = 0

            for idx, zip_path in enumerate(zip_paths, start=1):
                edinet_doc_id = zip_path.stem

                if edinet_doc_id in existing_doc_ids:
                    skipped_existing += 1
                    continue

                logger.info("[%s/%s] processing %s", idx, len(zip_paths), edinet_doc_id)

                try:
                    meta = extract_zip_metadata(zip_path)
                    meta["source_zip_path"] = str(zip_path)
                    edinet_code = meta.get("edinet_code") or ""

                    if not edinet_code:
                        logger.warning("Skipping %s: edinet_code not found", edinet_doc_id)
                        skipped_no_edinet_code += 1
                        continue

                    company_id = ensure_company(
                        cur,
                        edinet_code,
                        meta.get("company_name", ""),
                        meta.get("security_code", ""),
                    )
                    fiscal_year, fiscal_period = _infer_fiscal_info(
                        meta.get("period_start") or "",
                        meta.get("period_end") or "",
                    )

                    existing_id = find_existing_filing_id(cur, company_id, edinet_doc_id)
                    if existing_id is not None:
                        logger.info("Already loaded, updating meta: %s", edinet_doc_id)
                        update_filing_meta(cur, existing_id, meta, fiscal_year, fiscal_period)
                        conn.commit()
                        continue

                    facts = xbrl_utils.collect_facts_from_zip(zip_path)
                    df = xbrl_utils.facts_to_dataframe(facts)
                    df = xbrl_utils.add_local_name_column(df)

                    fs = FinancialSummary.from_dataframe(df)
                    cf = CashFlowSummary.from_dataframe(df)
                    bs = BalanceSheetSummary.from_dataframe(df)

                    filing_id = insert_filing(
                        cur,
                        company_id,
                        edinet_doc_id,
                        meta,
                        fiscal_year,
                        fiscal_period,
                        _infer_document_type(fiscal_period),
                    )
                    insert_statements_and_items(cur, filing_id, cfg, fs, cf, bs)

                    conn.commit()
                    loaded_count += 1

                except FileNotFoundError:
                    skipped_no_xbrl += 1
                    conn.rollback()
                except Exception:  # noqa: BLE001
                    logger.exception("failed to load %s; rolling back", zip_path)
                    error_count += 1
                    conn.rollback()

            print(
                f"=== Load Summary: {loaded_count} loaded, "
                f"{skipped_existing} skipped (existing), "
                f"{skipped_no_xbrl} skipped (no xbrl), "
                f"{skipped_no_edinet_code} skipped (no edinet_code), "
                f"{error_count} errors ==="
            )
