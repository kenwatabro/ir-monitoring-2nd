#!/usr/bin/env python3
"""全 filing を再パースして statements / statement_items を最新パーサーで更新する.

ZIP が存在する全 filing を対象に、statements を削除して再生成する。
パーサーロジック（yaml タグ追加、context 優先度変更など）を全件に反映する際に使用。

デフォルトはドライラン。--execute で実行。

Usage:
    python scripts/reparse_all_filings.py               # ドライラン（件数確認）
    python scripts/reparse_all_filings.py --limit 20    # 20件だけ試す
    python scripts/reparse_all_filings.py --execute     # 全件実行
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

try:
    from dotenv import load_dotenv

    load_dotenv(PROJECT_ROOT / ".env")
except ImportError:
    pass

from src.db import get_connection  # noqa: E402
from src.ingest.edinet.writer import insert_statements_and_items  # noqa: E402
from src.parser.configs import load_edinet_config  # noqa: E402
from src.parser.edinet import utils as xbrl_utils  # noqa: E402
from src.parser.edinet.xbrl_parser import (  # noqa: E402
    BalanceSheetSummary,
    CashFlowSummary,
    FinancialSummary,
)

TARGET_SQL = """
SELECT id, source_zip_path
FROM filings
WHERE source_zip_path IS NOT NULL AND source_zip_path <> ''
ORDER BY id
"""


def _reparse_one(cur, filing_id: int, zip_path: Path, cfg: dict) -> dict:
    facts = xbrl_utils.collect_facts_from_zip(zip_path)
    df = xbrl_utils.facts_to_dataframe(facts)
    df = xbrl_utils.add_local_name_column(df)

    fs = FinancialSummary.from_dataframe(df)
    cf = CashFlowSummary.from_dataframe(df)
    bs = BalanceSheetSummary.from_dataframe(df)

    cur.execute("DELETE FROM statements WHERE filing_id = %s", (filing_id,))
    insert_statements_and_items(cur, filing_id, cfg, fs, cf, bs)
    return fs.to_dict()


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--execute", action="store_true", help="実際に更新する（省略時はドライラン）")
    ap.add_argument("--limit", type=int, default=None, help="処理件数の上限（動作確認用）")
    args = ap.parse_args()

    cfg = load_edinet_config()

    with get_connection() as conn:
        conn.autocommit = False
        with conn.cursor() as cur:
            cur.execute(TARGET_SQL)
            targets = cur.fetchall()
            total = len(targets)
            print(f"対象 filings: {total:,} 件")

            if args.limit:
                targets = targets[: args.limit]
                print(f"  --limit {args.limit} 指定、先頭 {len(targets)} 件を処理")

            if not args.execute and not args.limit:
                print("ドライラン（件数のみ）。--execute または --limit で実際に処理します。")
                return

            ok = zip_missing = errors = 0

            for i, (filing_id, zip_path_str) in enumerate(targets, 1):
                zip_path = Path(zip_path_str)
                if not zip_path.is_file():
                    zip_missing += 1
                    continue

                try:
                    _reparse_one(cur, filing_id, zip_path, cfg)
                    ok += 1
                    if args.execute:
                        conn.commit()
                    else:
                        conn.rollback()
                except Exception as e:  # noqa: BLE001
                    errors += 1
                    conn.rollback()
                    print(f"  [{filing_id}] error: {e}")

                if i % 1000 == 0:
                    print(f"  progress {i}/{len(targets)} | ok={ok} zip_missing={zip_missing} errors={errors}")

            print("\n=== 完了 ===")
            print(f"処理成功    : {ok:,}")
            print(f"ZIP欠損スキップ: {zip_missing:,}")
            print(f"エラー      : {errors:,}")
            if not args.execute:
                print("(ドライラン: ロールバック済み)")


if __name__ == "__main__":
    main()
