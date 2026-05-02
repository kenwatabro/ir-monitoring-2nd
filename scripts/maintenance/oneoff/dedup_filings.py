#!/usr/bin/env python3
"""重複 filings のクリーンアップ.

同一 (company_id, period_end, fiscal_period) に複数 filing がある場合、
訂正版（edinet_documents.doc_type_code='140'=訂正有報, '150'=訂正四半期）を優先して残し、
次に最新の edinet_doc_id を残す。古い版を削除する。

EDINET doc_type_code:
  120=有報, 130=四半期報告書, 140=訂正有報, 150=訂正四半期報告書

デフォルトはドライラン。--execute で実行。

Usage:
    python scripts/maintenance/oneoff/dedup_filings.py            # ドライラン
    python scripts/maintenance/oneoff/dedup_filings.py --execute  # 実行
"""

from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[3]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

try:
    from dotenv import load_dotenv

    load_dotenv(PROJECT_ROOT / ".env")
except ImportError:
    pass

from psycopg2.extras import DictCursor  # noqa: E402

from src.db import get_connection  # noqa: E402


def _resolve_dsn() -> str | None:
    if os.getenv("PGURL"):
        return None
    host = os.getenv("POSTGRES_HOST")
    if not host:
        return None
    port = os.getenv("POSTGRES_PORT", "5432")
    db = os.getenv("POSTGRES_DB", "ir_monitoring")
    user = os.getenv("POSTGRES_USER", "ir_user")
    pw = os.getenv("POSTGRES_PASSWORD", "")
    return f"postgresql://{user}:{pw}@{host}:{port}/{db}"


# 同一 (company_id, period_end, fiscal_period) で残す filing を選ぶルール:
#   優先度1: 訂正版（140=訂正有報, 150=訂正四半期） > 通常版（120=有報, 130=四半期）
#   優先度2: 同じ type_code 内では edinet_doc_id の辞書順最大（= 提出が遅いほう）
# ※ 130 は四半期報告書であり訂正版ではないため旧コードは誤り
SELECT_DELETE_IDS_SQL = """
WITH ranked AS (
  SELECT
    f.id,
    f.company_id,
    f.period_end,
    f.fiscal_period,
    f.edinet_doc_id,
    ed.doc_type_code,
    ROW_NUMBER() OVER (
      PARTITION BY f.company_id, f.period_end, f.fiscal_period
      ORDER BY
        CASE ed.doc_type_code
          WHEN '140' THEN 0
          WHEN '150' THEN 1
          WHEN '120' THEN 2
          WHEN '130' THEN 3
          ELSE 4
        END,
        f.edinet_doc_id DESC
    ) AS rn
  FROM filings f
  LEFT JOIN edinet_documents ed ON ed.doc_id = f.edinet_doc_id
  WHERE (f.company_id, f.period_end, f.fiscal_period) IN (
    SELECT company_id, period_end, fiscal_period
    FROM filings
    GROUP BY company_id, period_end, fiscal_period
    HAVING COUNT(*) > 1
  )
)
SELECT id FROM ranked WHERE rn > 1
"""


def main() -> None:
    ap = argparse.ArgumentParser(description="重複 filings クリーンアップ")
    ap.add_argument("--execute", action="store_true", help="実際に削除する（指定しない場合ドライラン）")
    args = ap.parse_args()

    dsn = _resolve_dsn()
    with get_connection(dsn) as conn:
        cur = conn.cursor(cursor_factory=DictCursor)

        # 削除対象件数
        cur.execute(f"SELECT COUNT(*) FROM ({SELECT_DELETE_IDS_SQL}) t")
        n_targets = cur.fetchone()[0]
        print(f"削除対象 filings: {n_targets:,} 件")

        if n_targets == 0:
            print("何もすることがありません")
            return

        # 付随する statements / statement_items の件数
        cur.execute(f"""
            SELECT COUNT(*) FROM statements
            WHERE filing_id IN ({SELECT_DELETE_IDS_SQL})
        """)
        n_stmts = cur.fetchone()[0]
        print(f"付随 statements    : {n_stmts:,} 件")

        cur.execute(f"""
            SELECT COUNT(*) FROM statement_items si
            WHERE si.statement_id IN (
                SELECT id FROM statements WHERE filing_id IN ({SELECT_DELETE_IDS_SQL})
            )
        """)
        n_items = cur.fetchone()[0]
        print(f"付随 statement_items: {n_items:,} 件")

        # 残す側のサンプル表示
        print("\n-- サンプル（重複グループ5件分の『残す側』）")
        cur.execute("""
            WITH ranked AS (
              SELECT
                f.id, f.edinet_doc_id, ed.doc_type_code, c.ticker, c.name_jp,
                f.period_end, f.fiscal_period,
                ROW_NUMBER() OVER (
                  PARTITION BY f.company_id, f.period_end, f.fiscal_period
                  ORDER BY
                    CASE ed.doc_type_code WHEN '140' THEN 0 WHEN '150' THEN 1 WHEN '120' THEN 2 WHEN '130' THEN 3 ELSE 4 END,
                    f.edinet_doc_id DESC
                ) AS rn
              FROM filings f
              LEFT JOIN edinet_documents ed ON ed.doc_id = f.edinet_doc_id
              JOIN companies c ON c.id = f.company_id
              WHERE (f.company_id, f.period_end, f.fiscal_period) IN (
                SELECT company_id, period_end, fiscal_period
                FROM filings GROUP BY company_id, period_end, fiscal_period HAVING COUNT(*) > 1
              )
            )
            SELECT ticker, name_jp, period_end, fiscal_period, edinet_doc_id, doc_type_code
            FROM ranked WHERE rn = 1
            ORDER BY ticker LIMIT 5
        """)
        for r in cur.fetchall():
            print(
                f"  [{r['ticker']}] {r['name_jp']} | {r['period_end']} {r['fiscal_period']} "
                f"-> 残す: {r['edinet_doc_id']} (type={r['doc_type_code']})"
            )

        if not args.execute:
            print("\nドライラン。実行するには --execute を付けてください。")
            return

        print("\n=== 削除実行 ===")
        # statement_items -> statements -> filings の順で消す
        cur.execute(f"""
            DELETE FROM statement_items
            WHERE statement_id IN (
                SELECT id FROM statements WHERE filing_id IN ({SELECT_DELETE_IDS_SQL})
            )
        """)
        print(f"  statement_items 削除: {cur.rowcount:,} 件")

        cur.execute(f"""
            DELETE FROM statements WHERE filing_id IN ({SELECT_DELETE_IDS_SQL})
        """)
        print(f"  statements 削除     : {cur.rowcount:,} 件")

        cur.execute(f"DELETE FROM filings WHERE id IN ({SELECT_DELETE_IDS_SQL})")
        print(f"  filings 削除        : {cur.rowcount:,} 件")

        conn.commit()
        print("\nコミット完了")


if __name__ == "__main__":
    main()
