#!/usr/bin/env python3
"""net_sales が欠損している filing を再パースして statement_items を更新.

対象: net_sales の value_numeric が NULL の filing で source_zip_path が存在するもの。
パーサー修正（yaml に OperatingRevenue1/2 を追加、空値行スキップ）を反映するため、
PL/CF/BS サマリーを再計算し、既存の statement_items の value_numeric を UPDATE する。

デフォルトはドライラン。--execute で実行。

Usage:
    python scripts/reparse_missing_netsales.py                # ドライラン
    python scripts/reparse_missing_netsales.py --limit 10     # 10件だけ試す
    python scripts/reparse_missing_netsales.py --execute      # 全件実行
"""

from __future__ import annotations

import argparse
import os
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
from src.parser.edinet import utils as xbrl_utils  # noqa: E402
from src.parser.edinet.xbrl_parser import (  # noqa: E402
    BalanceSheetSummary,
    CashFlowSummary,
    FinancialSummary,
)


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


TARGET_FILINGS_SQL = """
SELECT f.id, f.source_zip_path
FROM filings f
WHERE f.source_zip_path IS NOT NULL AND f.source_zip_path <> ''
  AND NOT EXISTS (
    SELECT 1 FROM statements s
    JOIN statement_items si ON si.statement_id = s.id
    WHERE s.filing_id = f.id
      AND si.item_key = 'net_sales'
      AND si.value_numeric IS NOT NULL
  )
ORDER BY f.id
"""


def reparse_one(cur, filing_id: int, zip_path: Path) -> tuple[bool, dict]:
    """1件再パースしてDBを更新. (成功フラグ, 更新件数内訳) を返す."""
    if not zip_path.is_file():
        return False, {"reason": "zip_missing"}

    facts = xbrl_utils.collect_facts_from_zip(zip_path)
    df = xbrl_utils.facts_to_dataframe(facts)
    if df.empty:
        return False, {"reason": "empty_xbrl"}
    df = xbrl_utils.add_local_name_column(df)

    fs = FinancialSummary.from_dataframe(df).to_dict()
    cf = CashFlowSummary.from_dataframe(df).to_dict()
    bs = BalanceSheetSummary.from_dataframe(df).to_dict()

    updates = {**fs, **cf, **bs}

    n_updated = 0
    for item_key, value in updates.items():
        if value is None:
            continue
        cur.execute(
            """
            UPDATE statement_items si
            SET value_numeric = %s
            FROM statements s
            WHERE si.statement_id = s.id
              AND s.filing_id = %s
              AND si.item_key = %s
              AND si.value_numeric IS DISTINCT FROM %s
            """,
            (value, filing_id, item_key, value),
        )
        n_updated += cur.rowcount

    return True, {"items_updated": n_updated, "net_sales": fs.get("net_sales")}


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--execute", action="store_true")
    ap.add_argument("--limit", type=int, default=None)
    args = ap.parse_args()

    dsn = _resolve_dsn()
    with get_connection(dsn) as conn:
        conn.autocommit = False
        with conn.cursor() as cur:
            cur.execute(TARGET_FILINGS_SQL)
            targets = cur.fetchall()
            print(f"対象 filings: {len(targets):,} 件")

            if args.limit:
                targets = targets[: args.limit]
                print(f"  --limit {args.limit} 指定、先頭 {len(targets)} 件を処理")

            if not args.execute and not args.limit:
                print("ドライラン（件数のみ）。--execute または --limit で実際に処理します。")
                return

            ok = 0
            zip_missing = 0
            errors = 0
            net_sales_recovered = 0
            total_items_updated = 0

            for i, (filing_id, zp) in enumerate(targets, 1):
                try:
                    success, info = reparse_one(cur, filing_id, Path(zp))
                    if not success:
                        if info.get("reason") == "zip_missing":
                            zip_missing += 1
                        else:
                            errors += 1
                        conn.rollback()
                        continue

                    if info.get("net_sales") is not None:
                        net_sales_recovered += 1
                    total_items_updated += info.get("items_updated", 0)
                    ok += 1

                    if args.execute:
                        conn.commit()
                    else:
                        conn.rollback()
                except Exception as e:  # noqa: BLE001
                    errors += 1
                    conn.rollback()
                    print(f"  [{filing_id}] error: {e}")

                if i % 500 == 0:
                    print(
                        f"  progress {i}/{len(targets)} | ok={ok} net_sales_recovered={net_sales_recovered} errors={errors}"
                    )

            print("\n=== 完了 ===")
            print(f"処理成功             : {ok:,}")
            print(f"net_sales 回復件数    : {net_sales_recovered:,}")
            print(f"statement_items 更新 : {total_items_updated:,}")
            print(f"ZIP欠損でスキップ     : {zip_missing:,}")
            print(f"エラー                : {errors:,}")
            if not args.execute:
                print("(ドライラン: ロールバック済み)")


if __name__ == "__main__":
    main()
