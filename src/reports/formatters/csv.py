"""CSV出力用フォーマッター."""

from __future__ import annotations

import csv
import io
from typing import TYPE_CHECKING

from ._base import BaseFormatter

if TYPE_CHECKING:
    from src.query.timeseries import FinancialTimePoint


class CsvFormatter(BaseFormatter):
    """CSV形式のフォーマッター."""

    @property
    def name(self) -> str:
        return "csv"

    def format(self, data: list[FinancialTimePoint], company_name: str = "") -> str:
        """財務時系列データをCSV形式でフォーマット.

        Args:
            data: 財務時系列データのリスト
            company_name: 会社名（CSVには含めない）

        Returns:
            CSV形式の文字列
        """
        if not data:
            return ""

        output = io.StringIO()
        writer = csv.writer(output)

        # ヘッダー行
        writer.writerow(
            [
                "fiscal_year",
                "fiscal_period",
                "period_end",
                "net_sales",
                "operating_income",
                "ordinary_income",
                "net_income",
                "eps",
            ]
        )

        # データ行（古い順に並べ替え）
        sorted_data = sorted(
            data, key=lambda x: (x.fiscal_year or 0, x.period_end or "")
        )
        for point in sorted_data:
            writer.writerow(
                [
                    point.fiscal_year or "",
                    point.fiscal_period or "",
                    point.period_end.isoformat() if point.period_end else "",
                    point.net_sales if point.net_sales is not None else "",
                    point.operating_income
                    if point.operating_income is not None
                    else "",
                    point.ordinary_income if point.ordinary_income is not None else "",
                    point.net_income if point.net_income is not None else "",
                    point.eps if point.eps is not None else "",
                ]
            )

        return output.getvalue()



