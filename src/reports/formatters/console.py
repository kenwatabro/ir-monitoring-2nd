"""コンソール出力用フォーマッター."""

from __future__ import annotations

from typing import TYPE_CHECKING

from ._base import BaseFormatter

if TYPE_CHECKING:
    from src.query.timeseries import FinancialTimePoint


class ConsoleFormatter(BaseFormatter):
    """コンソール表示用のテーブルフォーマッター."""

    @property
    def name(self) -> str:
        return "console"

    def format(self, data: list[FinancialTimePoint], company_name: str = "") -> str:
        """財務時系列データをコンソール用テーブルとしてフォーマット.

        Args:
            data: 財務時系列データのリスト
            company_name: 会社名

        Returns:
            テーブル形式の文字列
        """
        if not data:
            return "データがありません"

        lines: list[str] = []

        # ヘッダー
        if company_name:
            lines.append(f"=== {company_name} 財務推移 ===")
            lines.append("")

        # テーブルヘッダー
        header = f"{'決算期':<10} {'売上高':>15} {'営業利益':>15} {'経常利益':>15} {'純利益':>15} {'EPS':>10}"
        lines.append(header)
        lines.append("-" * len(header))

        # データ行（古い順に並べ替え）
        sorted_data = sorted(
            data, key=lambda x: (x.fiscal_year or 0, x.period_end or "")
        )
        for point in sorted_data:
            fiscal = f"{point.fiscal_year or '-'} {point.fiscal_period or ''}"
            row = (
                f"{fiscal:<10} "
                f"{self._format_number(point.net_sales):>15} "
                f"{self._format_number(point.operating_income):>15} "
                f"{self._format_number(point.ordinary_income):>15} "
                f"{self._format_number(point.net_income):>15} "
                f"{self._format_eps(point.eps):>10}"
            )
            lines.append(row)

        lines.append("")
        lines.append("※ 金額は百万円単位")

        return "\n".join(lines)



