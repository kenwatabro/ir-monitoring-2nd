"""売上高成長率スクリーナー."""

from __future__ import annotations

from typing import Any

from src.analytics.registry import register
from src.analytics.screeners._base import BaseScreener, ScreenerResult


@register("revenue_growth")
class RevenueGrowthScreener(BaseScreener):
    """売上高成長率でフィルタリング.

    過去N年間の売上高成長率が指定した閾値以上の銘柄を抽出する。

    Example:
        >>> screener = RevenueGrowthScreener(min_growth_rate=0.10, years=3)
        >>> result = screener.evaluate({"net_sales_history": [1000, 1100, 1210, 1331]})
        >>> result.passed
        True
    """

    def __init__(
        self,
        min_growth_rate: float = 0.10,
        years: int = 3,
    ):
        """Initialize screener.

        Args:
            min_growth_rate: 最低成長率（0.10 = 10%）
            years: 評価期間（年数）
        """
        self.min_growth_rate = min_growth_rate
        self.years = years

    @property
    def name(self) -> str:
        return "売上高成長率"

    @property
    def description(self) -> str:
        return f"過去{self.years}年の売上高成長率が{self.min_growth_rate:.0%}以上"

    def evaluate(self, company_data: dict[str, Any]) -> ScreenerResult:
        """売上高成長率を評価.

        Args:
            company_data: net_sales_history キーに売上高のリストを含む辞書

        Returns:
            評価結果
        """
        sales_history = company_data.get("net_sales_history", [])

        if len(sales_history) < self.years + 1:
            return ScreenerResult(
                passed=False,
                details={
                    "reason": "データ不足",
                    "required": self.years + 1,
                    "actual": len(sales_history),
                },
            )

        old_sales = sales_history[-(self.years + 1)]
        new_sales = sales_history[-1]

        if old_sales is None or new_sales is None:
            return ScreenerResult(passed=False, details={"reason": "売上高がNone"})

        if old_sales <= 0:
            return ScreenerResult(
                passed=False,
                details={"reason": "基準年売上高が0以下", "old_sales": old_sales},
            )

        growth_rate = (new_sales - old_sales) / old_sales
        passed = growth_rate >= self.min_growth_rate

        return ScreenerResult(
            passed=passed,
            score=growth_rate,
            details={
                "growth_rate": growth_rate,
                "old_sales": old_sales,
                "new_sales": new_sales,
                "years": self.years,
            },
        )

