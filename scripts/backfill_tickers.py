#!/usr/bin/env python3
"""ticker (証券コード) が未設定の会社を ZIP から読み直して埋めるスクリプト。

SecurityCodeDEI タグへの対応前にロードされた会社は ticker が NULL になっている。
このスクリプトは companies.ticker IS NULL の会社に対応する ZIP を走査し、
ticker を埋める。

Usage:
    python scripts/backfill_tickers.py \
        --edinet-dir data/raw/edinet \
        --dsn "postgresql://ir_user:ir_password@192.168.0.100:5433/ir_monitoring"
"""

from __future__ import annotations

import argparse
import logging
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from dotenv import load_dotenv

from src.db import get_connection
from src.ingest.edinet.loader import extract_basic_metadata_from_zip

load_dotenv()

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(message)s",
)
logger = logging.getLogger(__name__)


def get_incomplete_edinet_codes(dsn: str | None) -> set[str]:
    """ticker または name_jp が未設定の会社の edinet_code 一覧を返す。"""
    with get_connection(dsn) as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT edinet_code FROM companies WHERE ticker IS NULL OR name_jp = ''")
            return {row[0] for row in cur.fetchall()}


def get_doc_ids_for_edinet_codes(dsn: str | None, edinet_codes: set[str]) -> dict[str, str]:
    """edinet_code → edinet_doc_id のマッピングを返す（各社1件）。"""
    if not edinet_codes:
        return {}
    with get_connection(dsn) as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT DISTINCT ON (c.edinet_code)
                    c.edinet_code, f.edinet_doc_id
                FROM companies c
                JOIN filings f ON f.company_id = c.id
                WHERE c.edinet_code = ANY(%s)
                ORDER BY c.edinet_code, f.period_end DESC
                """,
                (list(edinet_codes),),
            )
            return {row[0]: row[1] for row in cur.fetchall()}


def update_company(dsn: str | None, edinet_code: str, ticker: str, name_jp: str) -> None:
    with get_connection(dsn) as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                UPDATE companies
                SET
                    ticker  = CASE WHEN ticker  IS NULL AND %s <> '' THEN %s ELSE ticker  END,
                    name_jp = CASE WHEN name_jp =  ''   AND %s <> '' THEN %s ELSE name_jp END
                WHERE edinet_code = %s
                """,
                (ticker, ticker, name_jp, name_jp, edinet_code),
            )
        conn.commit()


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="ticker未設定の会社にZIPからtickerを設定する")
    parser.add_argument("--edinet-dir", type=Path, default=Path("data/raw/edinet"))
    parser.add_argument("--dsn", default=None)
    parser.add_argument("--dry-run", action="store_true", help="実際には更新しない")
    args = parser.parse_args(argv)

    edinet_dir = args.edinet_dir.resolve()

    logger.info("ticker=NULL または name_jp=空 の会社を取得中...")
    null_codes = get_incomplete_edinet_codes(args.dsn)
    logger.info("  %d 社が未設定", len(null_codes))

    if not null_codes:
        logger.info("対象なし。終了。")
        return 0

    logger.info("対象会社の doc_id を取得中...")
    code_to_doc = get_doc_ids_for_edinet_codes(args.dsn, null_codes)
    logger.info("  %d 社分の doc_id を取得", len(code_to_doc))

    # doc_id → ZIPパスのマッピングを構築
    doc_to_zip = {p.stem: p for p in edinet_dir.glob("*.zip")}

    updated = 0
    not_found = 0
    no_ticker = 0

    for edinet_code, doc_id in code_to_doc.items():
        zip_path = doc_to_zip.get(doc_id)
        if not zip_path:
            logger.debug("ZIP not found for %s (doc_id=%s)", edinet_code, doc_id)
            not_found += 1
            continue

        meta = extract_basic_metadata_from_zip(zip_path)
        ticker = meta.get("security_code", "")
        name_jp = meta.get("company_name", "")

        if not ticker and not name_jp:
            no_ticker += 1
            continue

        if args.dry_run:
            logger.info(
                "[DRY-RUN] %s → name=%s ticker=%s",
                edinet_code,
                name_jp or "(不変)",
                ticker or "(不変)",
            )
        else:
            update_company(args.dsn, edinet_code, ticker, name_jp)
            logger.info(
                "Updated: %s → name=%s ticker=%s",
                edinet_code,
                name_jp or "(不変)",
                ticker or "(不変)",
            )
        updated += 1

    logger.info(
        "=== 完了: %d件更新, %d件ZIPなし, %d件ticker取得不可 ===",
        updated,
        not_found,
        no_ticker,
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
