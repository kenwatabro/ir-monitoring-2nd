#!/usr/bin/env python3
"""欠損原因の特定スクリプト.

Phase 1: DBクエリで欠損パターン（重複・年別・項目間の重なり）を分析する。
Phase 2: 欠損filingのZIPを直接スキャンして、実際に存在するXBRLタグを確認する。
         現在のYAML定義に漏れているタグを発見するために使用。

Usage:
    python scripts/maintenance/diagnose_missing_items.py           # Phase 1のみ
    python scripts/maintenance/diagnose_missing_items.py --phase 2 # Phase 1+2
    python scripts/maintenance/diagnose_missing_items.py --phase 2 --sample 50
"""

from __future__ import annotations

import argparse
import random
import sys
import xml.etree.ElementTree as ET
import zipfile
from collections import Counter
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.db import get_connection  # noqa: E402

# ── IFRS / 業種別タクソノミーの判定 ────────────────────────────────────────

# namespace URI のキーワードで分類
_TAXONOMY_LABELS = [
    ("jpifrs", "IFRS（EDINET jpifrs）"),
    ("ifrs-full", "IFRS（ifrs-full）"),
    ("jpbpfrs", "銀行業（jpbpfrs）"),
    ("jpins", "保険業（jpins）"),
    ("jppfrs", "非営利（jppfrs）"),
    ("jppfs", "J-GAAP（jppfs）"),
    ("jpfrs", "J-GAAP旧（jpfrs）"),
]

# 利益系・売上系に関連しそうなキーワード
_INCOME_KEYWORDS = (
    "Income",
    "Profit",
    "Loss",
    "Sales",
    "Revenue",
    "Earnings",
    "NetIncome",
    "OrdinaryIncome",
    "OperatingIncome",
)


def _detect_taxonomy(namespaces: set[str]) -> str:
    """namespace URI セットから分類ラベルを返す。"""
    for kw, label in _TAXONOMY_LABELS:
        if any(kw in ns for ns in namespaces):
            return label
    return "不明"


def _extract_namespaces_and_tags(zip_path: str) -> tuple[set[str], list[str]]:
    """ZIPから namespace URI セットと全ローカル名リストを抽出する。"""
    namespaces: set[str] = set()
    local_names: list[str] = []
    try:
        with zipfile.ZipFile(zip_path) as zf:
            xbrl_file = next((n for n in zf.namelist() if n.lower().endswith(".xbrl")), None)
            if not xbrl_file:
                return namespaces, local_names
            with zf.open(xbrl_file) as fh:
                tree = ET.parse(fh)
        for elem in tree.getroot().iter():
            tag = elem.tag
            if tag.startswith("{"):
                ns, local = tag[1:].split("}", 1)
                namespaces.add(ns)
                local_names.append(local)
    except Exception:  # noqa: BLE001
        pass
    return namespaces, local_names


# ── Phase 1: DB分析 ──────────────────────────────────────────────────────────


def _section(title: str) -> None:
    print()
    print("=" * 70)
    print(title)
    print("=" * 70)


def run_phase1(conn) -> None:
    with conn.cursor() as cur:
        # 1. 欠損の重なり（ordinary_income が欠損している filing で他項目も欠損か）
        _section("1. 欠損項目の重なり（FY / ordinary_income 欠損 8,850件を基準）")
        missing_items = ["net_sales", "operating_income", "ordinary_income", "net_income", "eps"]
        cur.execute("""
            SELECT f.id
            FROM filings f
            WHERE f.fiscal_period = 'FY'
              AND NOT EXISTS (
                SELECT 1 FROM statements s
                JOIN statement_items si ON si.statement_id = s.id
                WHERE s.filing_id = f.id
                  AND si.item_key = 'ordinary_income'
                  AND si.value_numeric IS NOT NULL
              )
        """)
        missing_oi_ids = {row[0] for row in cur.fetchall()}
        print(f"  ordinary_income 欠損 filings: {len(missing_oi_ids):,} 件")

        for item in missing_items:
            if item == "ordinary_income":
                continue
            cur.execute(
                """
                SELECT f.id
                FROM filings f
                WHERE f.fiscal_period = 'FY'
                  AND NOT EXISTS (
                    SELECT 1 FROM statements s
                    JOIN statement_items si ON si.statement_id = s.id
                    WHERE s.filing_id = f.id
                      AND si.item_key = %s
                      AND si.value_numeric IS NOT NULL
                  )
            """,
                (item,),
            )
            missing_ids = {row[0] for row in cur.fetchall()}
            overlap = len(missing_oi_ids & missing_ids)
            only_oi = len(missing_oi_ids - missing_ids)
            only_item = len(missing_ids - missing_oi_ids)
            print(f"\n  vs {item} ({len(missing_ids):,}件欠損):")
            print(f"    両方欠損      : {overlap:>7,} 件")
            print(f"    ordinary_incomeのみ欠損: {only_oi:>7,} 件")
            print(f"    {item}のみ欠損: {only_item:>7,} 件")

        # 2. 年別欠損率
        _section("2. 年別欠損率（FY / ordinary_income）")
        cur.execute("""
            SELECT
                EXTRACT(YEAR FROM f.period_end)::int AS yr,
                COUNT(*) AS total,
                COUNT(*) FILTER (WHERE NOT EXISTS (
                    SELECT 1 FROM statements s
                    JOIN statement_items si ON si.statement_id = s.id
                    WHERE s.filing_id = f.id
                      AND si.item_key = 'ordinary_income'
                      AND si.value_numeric IS NOT NULL
                )) AS missing
            FROM filings f
            WHERE f.fiscal_period = 'FY'
            GROUP BY yr
            ORDER BY yr
        """)
        rows = cur.fetchall()
        print(f"  {'年':>6}  {'total':>7}  {'欠損':>7}  {'欠損率':>7}")
        print(f"  {'─' * 6}  {'─' * 7}  {'─' * 7}  {'─' * 7}")
        for yr, total, missing in rows:
            pct = missing / total * 100 if total else 0
            print(f"  {yr:>6}  {total:>7,}  {missing:>7,}  {pct:>6.1f}%")

        # 3. net_sales 欠損の内訳（ordinary_income がある/ない で分ける）
        _section("3. net_sales 欠損の内訳（ordinary_income の有無で分類）")
        cur.execute("""
            SELECT
                has_oi,
                COUNT(*) AS cnt
            FROM (
                SELECT
                    f.id,
                    EXISTS (
                        SELECT 1 FROM statements s
                        JOIN statement_items si ON si.statement_id = s.id
                        WHERE s.filing_id = f.id
                          AND si.item_key = 'ordinary_income'
                          AND si.value_numeric IS NOT NULL
                    ) AS has_oi
                FROM filings f
                WHERE f.fiscal_period = 'FY'
                  AND NOT EXISTS (
                    SELECT 1 FROM statements s
                    JOIN statement_items si ON si.statement_id = s.id
                    WHERE s.filing_id = f.id
                      AND si.item_key = 'net_sales'
                      AND si.value_numeric IS NOT NULL
                  )
            ) sub
            GROUP BY has_oi
        """)
        for has_oi, cnt in cur.fetchall():
            label = "ordinary_income あり（J-GAAP系）" if has_oi else "ordinary_income なし（IFRS等）"
            print(f"  {label}: {cnt:>6,} 件")

        # 4. ZIP パスのサンプル取得（Phase 2 用）
        _section("4. Phase 2 用：欠損 filing の ZIP パスサンプル（最大 200 件）")
        cur.execute("""
            SELECT f.id, f.source_zip_path, f.period_end
            FROM filings f
            WHERE f.fiscal_period = 'FY'
              AND f.source_zip_path IS NOT NULL
              AND NOT EXISTS (
                SELECT 1 FROM statements s
                JOIN statement_items si ON si.statement_id = s.id
                WHERE s.filing_id = f.id
                  AND si.item_key = 'ordinary_income'
                  AND si.value_numeric IS NOT NULL
              )
            ORDER BY f.period_end DESC
            LIMIT 200
        """)
        rows = cur.fetchall()
        print(f"  取得件数: {len(rows)} 件（最大 200）")
        return [(r[0], r[1], r[2]) for r in rows]


# ── Phase 2: ZIP タグスキャン ─────────────────────────────────────────────────


def run_phase2(zip_samples: list[tuple], sample_n: int = 50) -> None:
    _section(f"5. ZIP タグスキャン（サンプル {sample_n} 件）")

    # ランダムサンプリング
    samples = random.sample(zip_samples, min(sample_n, len(zip_samples)))

    taxonomy_counter: Counter[str] = Counter()
    income_tag_counter: Counter[str] = Counter()
    sales_tag_counter: Counter[str] = Counter()
    error_count = 0

    for _filing_id, zip_path, _period_end in samples:
        if not zip_path or not Path(zip_path).is_file():
            error_count += 1
            continue

        namespaces, local_names = _extract_namespaces_and_tags(zip_path)
        taxonomy = _detect_taxonomy(namespaces)
        taxonomy_counter[taxonomy] += 1

        # 利益系・売上系タグを集計
        for ln in local_names:
            if any(kw.lower() in ln.lower() for kw in ("income", "profit", "loss", "earnings")):
                income_tag_counter[ln] += 1
            if any(kw.lower() in ln.lower() for kw in ("sales", "revenue", "netrevenue")):
                sales_tag_counter[ln] += 1

    print(f"\n  タクソノミー分布（{sample_n - error_count} 件スキャン / {error_count} 件エラー）:")
    for taxonomy, cnt in taxonomy_counter.most_common():
        print(f"    {taxonomy}: {cnt} 件")

    print("\n  利益系タグ TOP30（ordinary_income 欠損 filings に出現）:")
    for tag, cnt in income_tag_counter.most_common(30):
        print(f"    {cnt:>4}件  {tag}")

    print("\n  売上系タグ TOP20（ordinary_income 欠損 filings に出現）:")
    for tag, cnt in sales_tag_counter.most_common(20):
        print(f"    {cnt:>4}件  {tag}")

    # 現在のYAML に存在しないタグを強調
    from src.parser.configs import load_edinet_config

    cfg = load_edinet_config()
    existing_tags: set[str] = set()
    for section in cfg.values():
        for field in section.get("fields", {}).values():
            existing_tags.update(field.get("local_names", []))

    new_income = [(t, c) for t, c in income_tag_counter.most_common(30) if t not in existing_tags]
    new_sales = [(t, c) for t, c in sales_tag_counter.most_common(20) if t not in existing_tags]

    if new_income:
        print("\n  *** YAML未定義の利益系タグ（要検討）:")
        for tag, cnt in new_income[:20]:
            print(f"    {cnt:>4}件  {tag}")

    if new_sales:
        print("\n  *** YAML未定義の売上系タグ（要検討）:")
        for tag, cnt in new_sales[:15]:
            print(f"    {cnt:>4}件  {tag}")


# ── main ──────────────────────────────────────────────────────────────────────


def main() -> int:
    parser = argparse.ArgumentParser(description="欠損原因の特定")
    parser.add_argument(
        "--phase",
        type=int,
        default=1,
        help="1=DBのみ, 2=DB+ZIPスキャン（デフォルト: 1）",
    )
    parser.add_argument(
        "--sample",
        type=int,
        default=50,
        help="Phase 2 でスキャンするサンプル数（デフォルト: 50）",
    )
    args = parser.parse_args()

    with get_connection() as conn:
        conn.autocommit = True
        zip_samples = run_phase1(conn)

    if args.phase >= 2:
        run_phase2(zip_samples, sample_n=args.sample)

    print()
    print("=== 完了 ===")
    return 0


if __name__ == "__main__":
    sys.exit(main())
