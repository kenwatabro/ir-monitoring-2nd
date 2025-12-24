"""Markdown出力用フォーマッター."""

from __future__ import annotations

from typing import TYPE_CHECKING

from ._base import BaseFormatter

if TYPE_CHECKING:
    from src.query.timeseries import FinancialTimePoint


class MarkdownFormatter(BaseFormatter):
    """Markdown形式のテーブルフォーマッター."""

    @property
    def name(self) -> str:
        return "markdown"

    def format(self, data: list[FinancialTimePoint], company_name: str = "") -> str:
        """財務時系列データをMarkdownテーブルとしてフォーマット.

        Args:
            data: 財務時系列データのリスト
            company_name: 会社名

        Returns:
            Markdownテーブル形式の文字列
        """
        if not data:
            return "データがありません"

        lines: list[str] = []

        # タイトル
        if company_name:
            lines.append(f"## {company_name} 財務推移")
            lines.append("")

        # テーブルヘッダー
        lines.append("| 決算期 | 売上高 | 営業利益 | 経常利益 | 純利益 | EPS |")
        lines.append("|--------|-------:|--------:|--------:|------:|----:|")

        # データ行（古い順に並べ替え）
        sorted_data = sorted(
            data, key=lambda x: (x.fiscal_year or 0, x.period_end or "")
        )
        for point in sorted_data:
            fiscal = f"{point.fiscal_year or '-'} {point.fiscal_period or ''}"
            row = (
                f"| {fiscal} "
                f"| {self._format_number(point.net_sales)} "
                f"| {self._format_number(point.operating_income)} "
                f"| {self._format_number(point.ordinary_income)} "
                f"| {self._format_number(point.net_income)} "
                f"| {self._format_eps(point.eps)} |"
            )
            lines.append(row)

        lines.append("")
        lines.append("*金額は百万円単位*")

        return "\n".join(lines)
