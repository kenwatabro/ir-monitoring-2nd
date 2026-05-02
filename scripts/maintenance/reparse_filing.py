#!/usr/bin/env python3
"""指定した edinet_doc_id の filing を再パースして DB の PL/CF/BS 値を更新する.

statements / statement_items を一旦削除して再生成する。filings 行は更新のみ。

Usage:
    python scripts/maintenance/reparse_filing.py --doc-id S100W57J
    python scripts/maintenance/reparse_filing.py --doc-id S100W57J S100XXXX  # 複数指定
    python scripts/maintenance/reparse_filing.py --doc-id S100W57J --dry-run  # ロールバック確認
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

try:
    from dotenv import load_dotenv

    load_dotenv(PROJECT_ROOT / ".env")
except ImportError:
    pass

from src.db import get_connection  # noqa: E402
from src.ingest.edinet.reparse import reparse_one  # noqa: E402
from src.parser.configs import load_edinet_config  # noqa: E402


def main() -> None:
    ap = argparse.ArgumentParser(description="指定 filing を再パースして DB を更新")
    ap.add_argument("--doc-id", nargs="+", required=True, metavar="DOC_ID")
    ap.add_argument("--dry-run", action="store_true", help="ロールバックして結果だけ表示")
    args = ap.parse_args()

    cfg = load_edinet_config()

    with get_connection() as conn:
        conn.autocommit = False
        with conn.cursor() as cur:
            for doc_id in args.doc_id:
                cur.execute(
                    "SELECT id, source_zip_path FROM filings WHERE edinet_doc_id = %s",
                    (doc_id,),
                )
                row = cur.fetchone()
                if not row:
                    print(f"[{doc_id}] filings に存在しません。スキップ。")
                    continue

                filing_id, zip_path_str = row
                if not zip_path_str:
                    print(f"[{doc_id}] source_zip_path が未設定。スキップ。")
                    continue

                zip_path = Path(zip_path_str)
                if not zip_path.is_file():
                    print(f"[{doc_id}] ZIP が見つかりません: {zip_path}")
                    continue

                try:
                    new_fs = reparse_one(cur, filing_id, zip_path, cfg)
                    print(f"[{doc_id}] filing_id={filing_id}")
                    for k, v in new_fs.items():
                        print(f"  {k}: {v}")

                    if args.dry_run:
                        conn.rollback()
                        print("  → dry-run: ロールバック済み")
                    else:
                        conn.commit()
                        print("  → コミット完了")

                except Exception as e:  # noqa: BLE001
                    conn.rollback()
                    print(f"[{doc_id}] エラー: {e}")


if __name__ == "__main__":
    main()
