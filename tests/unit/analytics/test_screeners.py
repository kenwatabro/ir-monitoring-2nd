"""Screener 実装のテスト."""

from __future__ import annotations


from src.analytics.screeners.growth.eps_growth import EPSGrowthScreener
from src.analytics.screeners.growth.revenue_growth import RevenueGrowthScreener
from src.analytics.screeners.value.profit_margin import ProfitMarginScreener


class TestEPSGrowthScreener:
    """EPSGrowthScreener のテスト."""

    def test_name_and_description(self) -> None:
        screener = EPSGrowthScreener(min_growth_rate=0.15, years=3)
        assert screener.name == "EPS成長率"
        assert "3年" in screener.description
        assert "15%" in screener.description

    def test_passes_when_growth_exceeds_threshold(self) -> None:
        """成長率が閾値以上なら合格."""
        screener = EPSGrowthScreener(min_growth_rate=0.15, years=3)
        data = {"eps_history": [100, 110, 121, 133]}  # 33% 成長

        result = screener.evaluate(data)

        assert result.passed is True
        assert result.score is not None
        assert result.score >= 0.15

    def test_fails_when_growth_below_threshold(self) -> None:
        """成長率が閾値未満なら不合格."""
        screener = EPSGrowthScreener(min_growth_rate=0.20, years=3)
        data = {"eps_history": [100, 105, 110, 115]}  # 15% 成長

        result = screener.evaluate(data)

        assert result.passed is False
        assert result.score is not None
        assert result.score < 0.20

    def test_fails_when_insufficient_data(self) -> None:
        """データ不足なら不合格."""
        screener = EPSGrowthScreener(years=5)
        data = {"eps_history": [100, 110, 121]}  # 3年分しかない

        result = screener.evaluate(data)

        assert result.passed is False
        assert result.details.get("reason") == "データ不足"

    def test_fails_when_base_eps_is_zero_or_negative(self) -> None:
        """基準年EPSが0以下なら不合格."""
        screener = EPSGrowthScreener(years=2)
        data = {"eps_history": [-10, 50, 100]}

        result = screener.evaluate(data)

        assert result.passed is False
        assert "0以下" in result.details.get("reason", "")


class TestRevenueGrowthScreener:
    """RevenueGrowthScreener のテスト."""

    def test_name_and_description(self) -> None:
        screener = RevenueGrowthScreener(min_growth_rate=0.10, years=3)
        assert screener.name == "売上高成長率"
        assert "3年" in screener.description

    def test_passes_when_growth_exceeds_threshold(self) -> None:
        """成長率が閾値以上なら合格."""
        screener = RevenueGrowthScreener(min_growth_rate=0.10, years=3)
        data = {"net_sales_history": [1000, 1100, 1210, 1331]}  # 33% 成長

        result = screener.evaluate(data)

        assert result.passed is True
        assert result.score is not None
        assert result.score >= 0.10

    def test_fails_when_insufficient_data(self) -> None:
        """データ不足なら不合格."""
        screener = RevenueGrowthScreener(years=5)
        data = {"net_sales_history": [1000, 1100]}

        result = screener.evaluate(data)

        assert result.passed is False


class TestProfitMarginScreener:
    """ProfitMarginScreener のテスト."""

    def test_name_and_description(self) -> None:
        screener = ProfitMarginScreener(min_margin=0.10)
        assert screener.name == "営業利益率"
        assert "10%" in screener.description

    def test_passes_when_margin_exceeds_threshold(self) -> None:
        """利益率が閾値以上なら合格."""
        screener = ProfitMarginScreener(min_margin=0.10)
        data = {
            "operating_income": 150_000_000,
            "net_sales": 1_000_000_000,
        }  # 15%

        result = screener.evaluate(data)

        assert result.passed is True
        assert result.score is not None
        assert abs(result.score - 0.15) < 0.001

    def test_fails_when_margin_below_threshold(self) -> None:
        """利益率が閾値未満なら不合格."""
        screener = ProfitMarginScreener(min_margin=0.15)
        data = {
            "operating_income": 100_000_000,
            "net_sales": 1_000_000_000,
        }  # 10%

        result = screener.evaluate(data)

        assert result.passed is False

    def test_fails_when_data_missing(self) -> None:
        """データがない場合は不合格."""
        screener = ProfitMarginScreener()
        data = {}

        result = screener.evaluate(data)

        assert result.passed is False
        assert result.details.get("reason") == "データ不足"


class TestBaseScreenerMethods:
    """BaseScreener の共通メソッドのテスト."""

    def test_filter_returns_passing_companies(self) -> None:
        """filter は合格した銘柄のみ返す."""
        screener = EPSGrowthScreener(min_growth_rate=0.10, years=2)
        companies = [
            {"ticker": "A", "eps_history": [100, 110, 121]},  # 21% → 合格
            {"ticker": "B", "eps_history": [100, 101, 102]},  # 2% → 不合格
            {"ticker": "C", "eps_history": [100, 120, 144]},  # 44% → 合格
        ]

        result = screener.filter(companies)

        tickers = [c["ticker"] for c in result]
        assert tickers == ["A", "C"]

    def test_rank_returns_sorted_by_score(self) -> None:
        """rank はスコア降順でソートする."""
        screener = EPSGrowthScreener(min_growth_rate=0.05, years=2)
        companies = [
            {"ticker": "A", "eps_history": [100, 110, 121]},  # 21%
            {"ticker": "B", "eps_history": [100, 120, 144]},  # 44%
            {"ticker": "C", "eps_history": [100, 105, 110]},  # 10%
        ]

        result = screener.rank(companies)

        tickers = [c["ticker"] for c, _ in result]
        assert tickers == ["B", "A", "C"]  # 44%, 21%, 10% の順



