#!/usr/bin/env python3
"""スクリーナーを実行するCLIスクリプト.

Usage:
    python scripts/run_screener.py --list
    python scripts/run_screener.py --name eps_growth
    python scripts/run_screener.py --name revenue_growth --years 5
    python scripts/run_screener.py --name profit_margin --min-margin 0.15
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.analytics import auto_discover, get_screener, list_screeners  # noqa: E402
from src.query.repositories.company import CompanyRepository  # noqa: E402
from src.query.timeseries import get_financial_history  # noqa: E402


def load_company_data(ticker: str, years: int = 5, dsn: str | None = None) -> dict[str, Any]:
    """会社の財務データを取得してスクリーナー用の辞書を構築.

    Args:
        ticker: 証券コード
        years: 取得する年数
        dsn: PostgreSQL 接続文字列

    Returns:
        スクリーナー用の会社データ辞書
    """
    company_repo = CompanyRepository(dsn)
    company = company_repo.find_by_ticker(ticker)

    if not company:
        return {}

    history = get_financial_history(ticker, years=years, dsn=dsn)

    if not history:
        return {
            "ticker": ticker,
            "name": company.name_jp,
        }

    # 最新のデータ
    latest = history[0]

    # 履歴データ（古い順）
    sorted_history = sorted(history, key=lambda x: (x.fiscal_year or 0, x.period_end or ""))

    return {
        "ticker": ticker,
        "name": company.name_jp,
        "net_sales": latest.net_sales,
        "operating_income": latest.operating_income,
        "net_income": latest.net_income,
        "eps": latest.eps,
        "eps_history": [h.eps for h in sorted_history],
        "net_sales_history": [h.net_sales for h in sorted_history],
        "operating_income_history": [h.operating_income for h in sorted_history],
    }


def main(argv: list[str] | None = None) -> int:
    """メイン関数.

    Args:
        argv: コマンドライン引数（テスト用）

    Returns:
        終了コード
    """
    parser = argparse.ArgumentParser(
        description="スクリーナーを実行して銘柄を評価する",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
例:
  python scripts/run_screener.py --list
  python scripts/run_screener.py --name eps_growth --ticker 7203
  python scripts/run_screener.py --name revenue_growth --ticker 7203 --years 5
  python scripts/run_screener.py --name profit_margin --ticker 7203 --min-margin 0.15
        """,
    )
    parser.add_argument(
        "--list",
        "-l",
        action="store_true",
        help="利用可能なスクリーナー一覧を表示",
    )
    parser.add_argument(
        "--name",
        "-n",
        help="スクリーナー名",
    )
    parser.add_argument(
        "--ticker",
        "-t",
        help="評価する証券コード",
    )
    parser.add_argument(
        "--years",
        "-y",
        type=int,
        default=5,
        help="取得する年数 (デフォルト: 5)",
    )
    parser.add_argument(
        "--min-growth",
        type=float,
        default=0.15,
        help="最低成長率 (デフォルト: 0.15 = 15%%)",
    )
    parser.add_argument(
        "--min-margin",
        type=float,
        default=0.10,
        help="最低利益率 (デフォルト: 0.10 = 10%%)",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="結果をJSON形式で出力",
    )

    args = parser.parse_args(argv)

    # スクリーナーを自動発見
    auto_discover()

    # 一覧表示
    if args.list:
        print("利用可能なスクリーナー:")
        for name in list_screeners():
            screener_cls = get_screener(name)
            screener = screener_cls()
            print(f"  {name}: {screener.description}")
        return 0

    # スクリーナー名が必須
    if not args.name:
        parser.error("--name または --list を指定してください")

    # ticker が必須
    if not args.ticker:
        parser.error("--ticker を指定してください")

    try:
        screener_cls = get_screener(args.name)

        # スクリーナーの種類に応じてパラメータを渡す
        if args.name in ("eps_growth", "revenue_growth"):
            screener = screener_cls(min_growth_rate=args.min_growth, years=args.years)
        elif args.name == "profit_margin":
            screener = screener_cls(min_margin=args.min_margin)
        else:
            screener = screener_cls()

        # 会社データを取得
        company_data = load_company_data(args.ticker, years=args.years + 1)

        if not company_data:
            print(f"エラー: 証券コード {args.ticker} が見つかりません", file=sys.stderr)
            return 1

        # 評価実行
        result = screener.evaluate(company_data)

        # 結果出力
        if args.json:
            output = {
                "ticker": args.ticker,
                "name": company_data.get("name", ""),
                "screener": args.name,
                "passed": result.passed,
                "score": result.score,
                "details": result.details,
            }
            print(json.dumps(output, ensure_ascii=False, indent=2))
        else:
            status = "✓ 合格" if result.passed else "✗ 不合格"
            print(f"=== {company_data.get('name', args.ticker)} ({args.ticker}) ===")
            print(f"スクリーナー: {screener.name}")
            print(f"条件: {screener.description}")
            print(f"結果: {status}")
            if result.score is not None:
                print(f"スコア: {result.score:.2%}")
            if result.details:
                print("詳細:")
                for key, value in result.details.items():
                    if isinstance(value, float):
                        print(f"  {key}: {value:,.2f}")
                    else:
                        print(f"  {key}: {value}")

        return 0

    except KeyError as e:
        print(f"エラー: {e}", file=sys.stderr)
        return 1
    except Exception as e:
        print(f"エラー: {e}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
