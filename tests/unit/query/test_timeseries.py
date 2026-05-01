"""timeseries モジュールの境界テスト."""

from __future__ import annotations

from datetime import date
from unittest.mock import MagicMock, patch

from src.query.repositories.company import CompanyInfo
from src.query.repositories.filing import FilingInfo
from src.query.timeseries import (
    FinancialTimePoint,
    get_financial_history,
    get_financial_history_by_edinet_code,
)


class TestGetFinancialHistory:
    """get_financial_history のテスト."""

    @patch("src.query.timeseries.StatementRepository")
    @patch("src.query.timeseries.FilingRepository")
    @patch("src.query.timeseries.CompanyRepository")
    def test_returns_empty_list_when_company_not_found(
        self,
        mock_company_repo_cls: MagicMock,
        mock_filing_repo_cls: MagicMock,
        mock_statement_repo_cls: MagicMock,
    ) -> None:
        """会社が見つからない場合は空リストを返す."""
        mock_company_repo = MagicMock()
        mock_company_repo.find_by_ticker.return_value = None
        mock_company_repo_cls.return_value = mock_company_repo

        result = get_financial_history("9999")

        assert result == []
        mock_company_repo.find_by_ticker.assert_called_once_with("9999")

    @patch("src.query.timeseries.StatementRepository")
    @patch("src.query.timeseries.FilingRepository")
    @patch("src.query.timeseries.CompanyRepository")
    def test_returns_empty_list_when_no_filings(
        self,
        mock_company_repo_cls: MagicMock,
        mock_filing_repo_cls: MagicMock,
        mock_statement_repo_cls: MagicMock,
    ) -> None:
        """Filing が見つからない場合は空リストを返す."""
        mock_company_repo = MagicMock()
        mock_company_repo.find_by_ticker.return_value = CompanyInfo(
            id=1,
            edinet_code="E12345",
            ticker="7203",
            name_jp="トヨタ自動車",
        )
        mock_company_repo_cls.return_value = mock_company_repo

        mock_filing_repo = MagicMock()
        mock_filing_repo.list_annual_filings.return_value = []
        mock_filing_repo_cls.return_value = mock_filing_repo

        result = get_financial_history("7203")

        assert result == []

    @patch("src.query.timeseries.StatementRepository")
    @patch("src.query.timeseries.FilingRepository")
    @patch("src.query.timeseries.CompanyRepository")
    def test_returns_financial_time_points(
        self,
        mock_company_repo_cls: MagicMock,
        mock_filing_repo_cls: MagicMock,
        mock_statement_repo_cls: MagicMock,
    ) -> None:
        """正常系: 財務時系列データを返す."""
        # Company mock
        mock_company_repo = MagicMock()
        mock_company_repo.find_by_ticker.return_value = CompanyInfo(
            id=1,
            edinet_code="E12345",
            ticker="7203",
            name_jp="トヨタ自動車",
        )
        mock_company_repo_cls.return_value = mock_company_repo

        # Filing mock
        mock_filing_repo = MagicMock()
        mock_filing_repo.list_annual_filings.return_value = [
            FilingInfo(
                id=100,
                company_id=1,
                edinet_doc_id="S100XXXX",
                period_start=date(2023, 4, 1),
                period_end=date(2024, 3, 31),
                fiscal_year=2024,
                fiscal_period="FY",
                is_consolidated=True,
            ),
            FilingInfo(
                id=99,
                company_id=1,
                edinet_doc_id="S100YYYY",
                period_start=date(2022, 4, 1),
                period_end=date(2023, 3, 31),
                fiscal_year=2023,
                fiscal_period="FY",
                is_consolidated=True,
            ),
        ]
        mock_filing_repo_cls.return_value = mock_filing_repo

        # Statement mock
        mock_statement_repo = MagicMock()
        mock_statement_repo.get_financial_summary.side_effect = [
            {
                "net_sales": 30000000000000,
                "operating_income": 2500000000000,
                "ordinary_income": 2800000000000,
                "net_income": 2000000000000,
                "eps": 200.5,
            },
            {
                "net_sales": 28000000000000,
                "operating_income": 2200000000000,
                "ordinary_income": 2500000000000,
                "net_income": 1800000000000,
                "eps": 180.0,
            },
        ]
        mock_statement_repo_cls.return_value = mock_statement_repo

        result = get_financial_history("7203", years=5)

        assert len(result) == 2
        assert result[0].fiscal_year == 2024
        assert result[0].net_sales == 30000000000000
        assert result[0].eps == 200.5
        assert result[1].fiscal_year == 2023
        assert result[1].net_sales == 28000000000000

    @patch("src.query.timeseries.StatementRepository")
    @patch("src.query.timeseries.FilingRepository")
    @patch("src.query.timeseries.CompanyRepository")
    def test_passes_dsn_to_repositories(
        self,
        mock_company_repo_cls: MagicMock,
        mock_filing_repo_cls: MagicMock,
        mock_statement_repo_cls: MagicMock,
    ) -> None:
        """DSN が各 Repository に渡される."""
        mock_company_repo = MagicMock()
        mock_company_repo.find_by_ticker.return_value = None
        mock_company_repo_cls.return_value = mock_company_repo

        custom_dsn = "postgresql://user:pass@localhost/test"
        get_financial_history("7203", dsn=custom_dsn)

        mock_company_repo_cls.assert_called_once_with(custom_dsn)
        mock_filing_repo_cls.assert_called_once_with(custom_dsn)
        mock_statement_repo_cls.assert_called_once_with(custom_dsn)


class TestGetFinancialHistoryByEdinetCode:
    """get_financial_history_by_edinet_code のテスト."""

    @patch("src.query.timeseries.StatementRepository")
    @patch("src.query.timeseries.FilingRepository")
    @patch("src.query.timeseries.CompanyRepository")
    def test_uses_edinet_code_for_lookup(
        self,
        mock_company_repo_cls: MagicMock,
        mock_filing_repo_cls: MagicMock,
        mock_statement_repo_cls: MagicMock,
    ) -> None:
        """EDINETコードで会社を検索する."""
        mock_company_repo = MagicMock()
        mock_company_repo.find_by_edinet_code.return_value = None
        mock_company_repo_cls.return_value = mock_company_repo

        result = get_financial_history_by_edinet_code("E12345")

        assert result == []
        mock_company_repo.find_by_edinet_code.assert_called_once_with("E12345")


class TestFinancialTimePoint:
    """FinancialTimePoint データクラスのテスト."""

    def test_dataclass_creation(self) -> None:
        """データクラスのインスタンス化."""
        point = FinancialTimePoint(
            fiscal_year=2024,
            fiscal_period="FY",
            period_end=date(2024, 3, 31),
            net_sales=1000000.0,
            operating_income=100000.0,
            ordinary_income=110000.0,
            net_income=80000.0,
            eps=100.0,
        )

        assert point.fiscal_year == 2024
        assert point.fiscal_period == "FY"
        assert point.net_sales == 1000000.0

    def test_allows_none_values(self) -> None:
        """None 値を許容する."""
        point = FinancialTimePoint(
            fiscal_year=2024,
            fiscal_period="FY",
            period_end=None,
            net_sales=None,
            operating_income=None,
            ordinary_income=None,
            net_income=None,
            eps=None,
        )

        assert point.net_sales is None
        assert point.eps is None
