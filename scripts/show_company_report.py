#!/usr/bin/env python3
"""銘柄のレポートを表示するCLIスクリプト.

Usage:
    python scripts/show_company_report.py 7203
    python scripts/show_company_report.py 7203 --format markdown
    python scripts/show_company_report.py 7203 --format csv --years 10
    python scripts/show_company_report.py --edinet E12345 --format console
"""

from __future__ import annotations

import argparse
import sys
from typing import Optional

from src.reports.formatters.console import ConsoleFormatter
from src.reports.formatters.csv import CsvFormatter
from src.reports.formatters.markdown import MarkdownFormatter
from src.reports.generators.company import CompanyReportGenerator

FORMATTERS = {
    "console": ConsoleFormatter,
    "csv": CsvFormatter,
    "markdown": MarkdownFormatter,
}


def main(argv: Optional[list[str]] = None) -> int:
    """メイン関数.

    Args:
        argv: コマンドライン引数（テスト用）

    Returns:
        終了コード（0: 成功, 1: エラー）
    """
    parser = argparse.ArgumentParser(
        description="銘柄の財務推移レポートを表示する",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
例:
  python scripts/show_company_report.py 7203
  python scripts/show_company_report.py 7203 --format markdown
  python scripts/show_company_report.py 7203 --format csv --years 10
  python scripts/show_company_report.py --edinet E12345
        """,
    )
    parser.add_argument(
        "ticker",
        nargs="?",
        help="証券コード (例: 7203)",
    )
    parser.add_argument(
        "--edinet",
        metavar="CODE",
        help="EDINETコードで検索 (例: E12345)",
    )
    parser.add_argument(
        "--format",
        "-f",
        default="console",
        choices=FORMATTERS.keys(),
        help="出力フォーマット (デフォルト: console)",
    )
    parser.add_argument(
        "--years",
        "-y",
        type=int,
        default=5,
        help="取得する年数 (デフォルト: 5)",
    )

    args = parser.parse_args(argv)

    # ticker または --edinet のどちらかが必須
    if not args.ticker and not args.edinet:
        parser.error("証券コードまたは --edinet オプションを指定してください")

    try:
        formatter = FORMATTERS[args.format]()
        generator = CompanyReportGenerator(formatter)

        if args.edinet:
            report = generator.generate_by_edinet_code(args.edinet, years=args.years)
        else:
            report = generator.generate(args.ticker, years=args.years)

        print(report)
        return 0

    except Exception as e:
        print(f"エラー: {e}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
