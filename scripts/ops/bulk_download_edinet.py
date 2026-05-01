#!/usr/bin/env python3
"""EDINET の書類を指定期間分まとめてダウンロードし、PostgreSQL に登録するスクリプト。

バックグラウンド実行を想定。再実行すると自動でスキップ:
  - スキャン済み日付 (edinet_scanned_dates) は API を叩かない
  - ダウンロード済み ZIP ファイルは再取得しない
  - DB 登録済みの doc_id はロードをスキップ

Usage:
    # 2015年から今日まで全件取得（バックグラウンド）
    python scripts/bulk_download_edinet.py --start 2015-01-01 &

    # 特定期間
    python scripts/bulk_download_edinet.py --start 2020-04-01 --end 2021-03-31

    # ダウンロードのみ（DBロードなし）
    python scripts/bulk_download_edinet.py --start 2020-01-01 --download-only

    # DBロードのみ（既にZIPがある場合）
    python scripts/bulk_download_edinet.py --load-only
"""

from __future__ import annotations

import argparse
import logging
import sys
import time
from datetime import date, timedelta
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from dotenv import load_dotenv

from src.db import get_connection
from src.downloader.edinet.downloader import EdinetDownloader
from src.ingest.edinet.loader import load_edinet_directory
from src.ingest.edinet.metadata import upsert_edinet_documents

load_dotenv()

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger(__name__)

# EDINET API は厳しいレート制限があるため、メタデータ取得ごとに待機する
API_INTERVAL_SECS = 1.0


def get_scanned_dates(dsn: str | None) -> set[date]:
    """DB から取得済み日付セットを返す。"""
    try:
        with get_connection(dsn) as conn:
            with conn.cursor() as cur:
                cur.execute("SELECT scan_date FROM edinet_scanned_dates")
                return {row[0] for row in cur.fetchall()}
    except Exception as e:
        logger.warning("edinet_scanned_dates の読み込みに失敗: %s (テーブル未作成の可能性)", e)
        return set()


def mark_date_scanned(dsn: str | None, scan_date: date, doc_count: int) -> None:
    """スキャン済み日付を DB に記録する。"""
    try:
        with get_connection(dsn) as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    INSERT INTO edinet_scanned_dates (scan_date, doc_count)
                    VALUES (%s, %s)
                    ON CONFLICT (scan_date) DO UPDATE
                        SET doc_count  = EXCLUDED.doc_count,
                            scanned_at = NOW()
                    """,
                    (scan_date, doc_count),
                )
            conn.commit()
    except Exception as e:
        logger.warning("スキャン日付の記録に失敗 %s: %s", scan_date, e)


def download_range(
    start: date,
    end: date,
    output_dir: Path,
    dsn: str | None,
    skip_scanned: bool = True,
) -> int:
    """start〜end の日付範囲で EDINET から ZIP をダウンロードし、メタデータを記録する。

    Returns:
        ダウンロードした書類の総数
    """
    scanned = get_scanned_dates(dsn) if skip_scanned else set()
    total_docs = 0
    current = start

    all_days = (end - start).days + 1
    done_days = 0

    while current <= end:
        done_days += 1

        if current in scanned:
            logger.debug("[%d/%d] %s はスキャン済み、スキップ", done_days, all_days, current)
            current += timedelta(days=1)
            continue

        logger.info("[%d/%d] %s のメタデータ取得中...", done_days, all_days, current)

        try:
            # 1日分だけダウンロード
            downloader = EdinetDownloader(start_date=current, end_date=current)
            docs = downloader.download(output_dir=output_dir)

            # メタデータを edinet_documents に保存
            if dsn and docs:
                upsert_edinet_documents(docs, dsn=dsn)

            # スキャン済みとしてマーク
            mark_date_scanned(dsn, current, len(docs))

            if docs:
                logger.info("  → %d 件取得", len(docs))
            total_docs += len(docs)

        except Exception:
            logger.exception("%s の処理中にエラー発生", current)

        time.sleep(API_INTERVAL_SECS)
        current += timedelta(days=1)

    return total_docs


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="EDINET 書類を一括ダウンロードして PostgreSQL に登録する",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    parser.add_argument(
        "--start",
        type=date.fromisoformat,
        default=date(2015, 1, 5),  # EDINET v2 APIの開始日付付近
        help="取得開始日 (YYYY-MM-DD, デフォルト: 2015-01-05)",
    )
    parser.add_argument(
        "--end",
        type=date.fromisoformat,
        default=date.today(),
        help="取得終了日 (YYYY-MM-DD, デフォルト: 今日)",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=Path("data/raw/edinet"),
        help="ZIP 保存先ディレクトリ (デフォルト: data/raw/edinet)",
    )
    parser.add_argument(
        "--dsn",
        default=None,
        help=(
            "PostgreSQL 接続文字列 (省略時は PGURL 環境変数 or デフォルト DSN)。"
            " 例: 'host=/var/run/postgresql dbname=ir_monitoring_test user=k'"
        ),
    )
    parser.add_argument(
        "--download-only",
        action="store_true",
        help="ZIP のダウンロードのみ行い、DB へのロードはしない",
    )
    parser.add_argument(
        "--load-only",
        action="store_true",
        help="DB へのロードのみ行う（ダウンロードはスキップ）",
    )
    parser.add_argument(
        "--no-skip-scanned",
        action="store_true",
        help="スキャン済み日付でも API を叩き直す（デバッグ用）",
    )
    parser.add_argument(
        "--log-level",
        default="INFO",
        choices=["DEBUG", "INFO", "WARNING", "ERROR"],
        help="ログレベル (デフォルト: INFO)",
    )
    args = parser.parse_args(argv)

    logging.getLogger().setLevel(args.log_level)

    output_dir = args.output_dir.resolve()
    output_dir.mkdir(parents=True, exist_ok=True)

    logger.info("=== EDINET 一括取得開始: %s 〜 %s ===", args.start, args.end)
    logger.info("ZIP 保存先: %s", output_dir)

    if not args.load_only:
        total = download_range(
            start=args.start,
            end=args.end,
            output_dir=output_dir,
            dsn=args.dsn,
            skip_scanned=not args.no_skip_scanned,
        )
        logger.info("=== ダウンロード完了: 合計 %d 件 ===", total)

    if not args.download_only:
        logger.info("=== DB ロード開始: %s ===", output_dir)
        load_edinet_directory(
            edinet_dir=output_dir,
            dsn=args.dsn,
        )

    logger.info("=== 全処理完了 ===")
    return 0


if __name__ == "__main__":
    sys.exit(main())
