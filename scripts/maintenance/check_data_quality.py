#!/usr/bin/env python3
"""取り込み済みデータの品質チェック.

DB接続情報は環境変数 PGURL または .env (POSTGRES_HOST/PORT/DB/USER/PASSWORD) から読む。

Usage:
    python scripts/check_data_quality.py
"""

from __future__ import annotations

import os
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


def section(title: str) -> None:
    print(f"\n{'=' * 70}\n{title}\n{'=' * 70}")


def main() -> None:
    dsn = _resolve_dsn()
    with get_connection(dsn) as conn:
        cur = conn.cursor(cursor_factory=DictCursor)

        section("1. テーブルごとの件数")
        for table in ["companies", "edinet_documents", "filings", "statements", "statement_items"]:
            cur.execute(f"SELECT COUNT(*) FROM {table}")
            print(f"  {table:20s}: {cur.fetchone()[0]:>10,}")

        section("2. filings: fiscal_period 分布")
        cur.execute("""
            SELECT fiscal_period, COUNT(*) AS n
            FROM filings GROUP BY fiscal_period ORDER BY n DESC
        """)
        for r in cur.fetchall():
            print(f"  {r['fiscal_period'] or '(NULL)':10s}: {r['n']:>8,}")

        section("3. 孤立・欠損チェック")
        cur.execute("""
            SELECT COUNT(*) FROM filings f
            LEFT JOIN companies c ON c.id = f.company_id
            WHERE c.id IS NULL
        """)
        print(f"  company なし filings        : {cur.fetchone()[0]:>8,}")

        cur.execute("""
            SELECT COUNT(*) FROM filings f
            LEFT JOIN statements s ON s.filing_id = f.id
            WHERE s.id IS NULL
        """)
        print(f"  statement なし filings      : {cur.fetchone()[0]:>8,}")

        cur.execute("""
            SELECT COUNT(*) FROM statements s
            LEFT JOIN statement_items si ON si.statement_id = s.id
            WHERE si.id IS NULL
        """)
        print(f"  item なし statements        : {cur.fetchone()[0]:>8,}")

        cur.execute("SELECT COUNT(*) FROM filings WHERE period_end IS NULL")
        print(f"  period_end NULL filings     : {cur.fetchone()[0]:>8,}")

        cur.execute("SELECT COUNT(*) FROM filings WHERE fiscal_year IS NULL")
        print(f"  fiscal_year NULL filings    : {cur.fetchone()[0]:>8,}")

        section("4. 重複チェック（同一会社×period_end×fiscal_period）")
        cur.execute("""
            SELECT COUNT(*) FROM (
                SELECT company_id, period_end, fiscal_period, COUNT(*) AS n
                FROM filings
                GROUP BY company_id, period_end, fiscal_period
                HAVING COUNT(*) > 1
            ) t
        """)
        print(f"  重複組み合わせ数            : {cur.fetchone()[0]:>8,}")

        section("5. 主要PL項目の欠損（FY filings のみ）")
        cur.execute("SELECT COUNT(*) FROM filings WHERE fiscal_period = 'FY'")
        total_fy = cur.fetchone()[0]
        for key in ["net_sales", "operating_income", "ordinary_income", "net_income", "eps"]:
            cur.execute(
                """
                SELECT COUNT(DISTINCT f.id)
                FROM filings f
                WHERE f.fiscal_period = 'FY'
                  AND NOT EXISTS (
                    SELECT 1 FROM statements s
                    JOIN statement_items si ON si.statement_id = s.id
                    WHERE s.filing_id = f.id AND si.item_key = %s AND si.value_numeric IS NOT NULL
                  )
                """,
                (key,),
            )
            missing = cur.fetchone()[0]
            pct = missing / total_fy * 100 if total_fy else 0
            print(f"  {key:20s}: {missing:>8,} / {total_fy:,} ({pct:5.1f}% 欠損)")

        section("6. 異常値チェック（FY / net_sales）")
        cur.execute("""
            SELECT COUNT(*) FROM statement_items si
            JOIN statements s ON s.id = si.statement_id
            JOIN filings f ON f.id = s.filing_id
            WHERE f.fiscal_period = 'FY' AND si.item_key = 'net_sales' AND si.value_numeric < 0
        """)
        print(f"  net_sales < 0               : {cur.fetchone()[0]:>8,}")

        cur.execute("""
            SELECT MIN(si.value_numeric), MAX(si.value_numeric),
                   percentile_cont(0.5) WITHIN GROUP (ORDER BY si.value_numeric)
            FROM statement_items si
            JOIN statements s ON s.id = si.statement_id
            JOIN filings f ON f.id = s.filing_id
            WHERE f.fiscal_period = 'FY' AND si.item_key = 'net_sales' AND si.value_numeric IS NOT NULL
        """)
        r = cur.fetchone()
        mn, mx, med = r[0], r[1], r[2]
        print(f"  net_sales min/median/max    : {mn:,.0f} / {med:,.0f} / {mx:,.0f}")

        section("7. period_end の年別分布")
        cur.execute("""
            SELECT EXTRACT(YEAR FROM period_end)::int AS y, COUNT(*) AS n
            FROM filings WHERE period_end IS NOT NULL
            GROUP BY y ORDER BY y
        """)
        for r in cur.fetchall():
            print(f"  {r['y']}: {r['n']:>6,}")

        section("8. 期間整合性（period_start > period_end）")
        cur.execute("""
            SELECT COUNT(*) FROM filings
            WHERE period_start IS NOT NULL AND period_end IS NOT NULL
              AND period_start > period_end
        """)
        print(f"  period_start > period_end   : {cur.fetchone()[0]:>8,}")

        section("9. 同一会社のedinet_code重複")
        cur.execute("""
            SELECT COUNT(*) FROM (
                SELECT edinet_code, COUNT(*) AS n
                FROM companies
                WHERE edinet_code IS NOT NULL
                GROUP BY edinet_code HAVING COUNT(*) > 1
            ) t
        """)
        print(f"  重複 edinet_code 数         : {cur.fetchone()[0]:>8,}")

    print("\n=== 完了 ===")


if __name__ == "__main__":
    main()
