"""EPS成長率スクリーナー."""

from __future__ import annotations

from typing import Any

from src.analytics.registry import register
from src.analytics.screeners._base import BaseScreener, ScreenerResult


@register("eps_growth")
class EPSGrowthScreener(BaseScreener):
    """EPS成長率でフィルタリング.

    過去N年間のEPS成長率が指定した閾値以上の銘柄を抽出する。

    Example:
        >>> screener = EPSGrowthScreener(min_growth_rate=0.15, years=3)
        >>> result = screener.evaluate({"eps_history": [100, 110, 121, 133]})
        >>> result.passed
        True
    """

    def __init__(
        self,
        min_growth_rate: float = 0.15,
        years: int = 3,
    ):
        """Initialize screener.

        Args:
            min_growth_rate: 最低成長率（0.15 = 15%）
            years: 評価期間（年数）
        """
        self.min_growth_rate = min_growth_rate
        self.years = years

    @property
    def name(self) -> str:
        return "EPS成長率"

    @property
    def description(self) -> str:
        return f"過去{self.years}年のEPS成長率が{self.min_growth_rate:.0%}以上"

    def evaluate(self, company_data: dict[str, Any]) -> ScreenerResult:
        """EPS成長率を評価.

        Args:
            company_data: eps_history キーに EPS のリストを含む辞書

        Returns:
            評価結果
        """
        eps_history = company_data.get("eps_history", [])

        if len(eps_history) < self.years + 1:
            return ScreenerResult(
                passed=False,
                details={
                    "reason": "データ不足",
                    "required": self.years + 1,
                    "actual": len(eps_history),
                },
            )

        old_eps = eps_history[-(self.years + 1)]
        new_eps = eps_history[-1]

        if old_eps is None or new_eps is None:
            return ScreenerResult(passed=False, details={"reason": "EPS値がNone"})

        if old_eps <= 0:
            return ScreenerResult(
                passed=False, details={"reason": "基準年EPSが0以下", "old_eps": old_eps}
            )

        growth_rate = (new_eps - old_eps) / old_eps
        passed = growth_rate >= self.min_growth_rate

        return ScreenerResult(
            passed=passed,
            score=growth_rate,
            details={
                "growth_rate": growth_rate,
                "old_eps": old_eps,
                "new_eps": new_eps,
                "years": self.years,
            },
        )
