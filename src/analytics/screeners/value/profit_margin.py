"""利益率スクリーナー."""

from __future__ import annotations

from typing import Any

from src.analytics.registry import register
from src.analytics.screeners._base import BaseScreener, ScreenerResult


@register("profit_margin")
class ProfitMarginScreener(BaseScreener):
    """営業利益率でフィルタリング.

    営業利益率が指定した閾値以上の銘柄を抽出する。

    Example:
        >>> screener = ProfitMarginScreener(min_margin=0.10)
        >>> result = screener.evaluate({
        ...     "operating_income": 100_000_000,
        ...     "net_sales": 1_000_000_000
        ... })
        >>> result.passed
        True
    """

    def __init__(
        self,
        min_margin: float = 0.10,
    ):
        """Initialize screener.

        Args:
            min_margin: 最低営業利益率（0.10 = 10%）
        """
        self.min_margin = min_margin

    @property
    def name(self) -> str:
        return "営業利益率"

    @property
    def description(self) -> str:
        return f"営業利益率が{self.min_margin:.0%}以上"

    def evaluate(self, company_data: dict[str, Any]) -> ScreenerResult:
        """営業利益率を評価.

        Args:
            company_data: operating_income と net_sales を含む辞書

        Returns:
            評価結果
        """
        operating_income = company_data.get("operating_income")
        net_sales = company_data.get("net_sales")

        if operating_income is None or net_sales is None:
            return ScreenerResult(passed=False, details={"reason": "データ不足"})

        if net_sales <= 0:
            return ScreenerResult(
                passed=False,
                details={"reason": "売上高が0以下", "net_sales": net_sales},
            )

        margin = operating_income / net_sales
        passed = margin >= self.min_margin

        return ScreenerResult(
            passed=passed,
            score=margin,
            details={
                "margin": margin,
                "operating_income": operating_income,
                "net_sales": net_sales,
            },
        )

